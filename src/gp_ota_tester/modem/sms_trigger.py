"""SMS Trigger for Modem Controller.

This module provides SMS-PP trigger message sending in PDU mode
for OTA operations.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from gp_ota_tester.modem.at_interface import ATInterface
from gp_ota_tester.modem.exceptions import ATCommandError, ATTimeoutError, SMSTriggerError
from gp_ota_tester.modem.models import TriggerResult, TriggerTemplate

logger = logging.getLogger(__name__)

# Response patterns
CMGS_PATTERN = re.compile(r"\+CMGS:\s*(\d+)")

# Ctrl+Z to send SMS
CTRL_Z = b"\x1a"
ESC = b"\x1b"

# Default timeouts
SMS_SEND_TIMEOUT = 60.0
PROMPT_TIMEOUT = 5.0


@dataclass
class SMSTriggerConfig:
    """Configuration for SMS trigger operations."""

    smsc_address: str = ""  # Service center address (empty = default)
    send_timeout: float = SMS_SEND_TIMEOUT
    retry_count: int = 1
    retry_delay: float = 2.0


class SMSTrigger:
    """SMS-PP OTA trigger message sender.

    Sends SMS messages in PDU mode for OTA trigger operations.

    Example:
        >>> trigger = SMSTrigger(at_interface)
        >>>
        >>> # Configure PDU mode
        >>> await trigger.configure_pdu_mode()
        >>>
        >>> # Send raw PDU
        >>> result = await trigger.send_raw_pdu("00...")
        >>> print(f"Message ref: {result.message_reference}")
    """

    def __init__(
        self,
        at_interface: ATInterface,
        config: Optional[SMSTriggerConfig] = None,
    ):
        """Initialize SMS trigger.

        Args:
            at_interface: AT interface for communication.
            config: Optional configuration.
        """
        self.at = at_interface
        self.config = config or SMSTriggerConfig()
        self._pdu_mode_configured = False

    async def configure_pdu_mode(self) -> bool:
        """Configure modem for PDU mode SMS.

        Returns:
            True if successful.

        Raises:
            SMSTriggerError: If configuration fails.
        """
        try:
            # Set PDU mode (AT+CMGF=0)
            response = await self.at.send_command("AT+CMGF=0")
            if not response.success:
                raise SMSTriggerError("Failed to set PDU mode")

            self._pdu_mode_configured = True
            logger.debug("SMS PDU mode configured")
            return True

        except ATCommandError as e:
            raise SMSTriggerError(f"Failed to configure PDU mode: {e}")

    async def ensure_pdu_mode(self) -> None:
        """Ensure PDU mode is configured."""
        if not self._pdu_mode_configured:
            await self.configure_pdu_mode()

    async def send_raw_pdu(self, pdu_hex: str) -> TriggerResult:
        """Send raw PDU hex string as SMS.

        Args:
            pdu_hex: Hex-encoded PDU (including SMSC length).

        Returns:
            TriggerResult with send status.

        Raises:
            SMSTriggerError: If send fails.
        """
        await self.ensure_pdu_mode()

        # Clean and validate PDU
        pdu_hex = pdu_hex.replace(" ", "").upper()
        if not all(c in "0123456789ABCDEF" for c in pdu_hex):
            raise SMSTriggerError("Invalid PDU: contains non-hex characters", pdu_hex)

        if len(pdu_hex) < 4:
            raise SMSTriggerError("Invalid PDU: too short", pdu_hex)

        # Convert to bytes for length calculation
        try:
            pdu_bytes = bytes.fromhex(pdu_hex)
        except ValueError as e:
            raise SMSTriggerError(f"Invalid PDU hex: {e}", pdu_hex)

        # Calculate TPDU length (excluding SMSC)
        # First byte of PDU is SMSC length (in octets)
        smsc_len = pdu_bytes[0]
        tpdu_length = len(pdu_bytes) - 1 - smsc_len

        logger.debug("Sending SMS PDU: SMSC len=%d, TPDU len=%d", smsc_len, tpdu_length)

        # Retry logic
        last_error = None
        for attempt in range(self.config.retry_count + 1):
            try:
                result = await self._send_pdu_internal(pdu_hex, tpdu_length)
                return result
            except SMSTriggerError as e:
                last_error = e
                if attempt < self.config.retry_count:
                    logger.warning("SMS send failed (attempt %d), retrying...", attempt + 1)
                    await asyncio.sleep(self.config.retry_delay)

        raise last_error or SMSTriggerError("SMS send failed after retries")

    async def _send_pdu_internal(self, pdu_hex: str, tpdu_length: int) -> TriggerResult:
        """Internal PDU send implementation."""
        # Send AT+CMGS command with TPDU length
        try:
            # Clear any pending data
            await self.at.serial.read_available()

            # Send AT+CMGS=<length>
            cmd = f"AT+CMGS={tpdu_length}"
            await self.at.serial.write(f"{cmd}\r\n".encode())

            logger.debug("Sent: %s", cmd)

            # Wait for > prompt
            prompt_received = await self._wait_for_prompt()
            if not prompt_received:
                # Cancel with ESC
                await self.at.serial.write(ESC)
                raise SMSTriggerError("Did not receive SMS prompt")

            # Send PDU hex + Ctrl+Z
            await self.at.serial.write(pdu_hex.encode() + CTRL_Z)
            logger.debug("Sent PDU data (%d chars) + Ctrl+Z", len(pdu_hex))

            # Wait for response
            raw_response = await self._read_cmgs_response()

            # Parse response
            return self._parse_cmgs_response(raw_response, pdu_hex)

        except ATTimeoutError:
            raise SMSTriggerError("SMS send timed out", pdu_hex)

    async def _wait_for_prompt(self) -> bool:
        """Wait for > prompt.

        Returns:
            True if prompt received.
        """
        try:
            data = await self.at.serial.read_until(b">", timeout=PROMPT_TIMEOUT)
            return b">" in data
        except Exception:
            return False

    async def _read_cmgs_response(self) -> str:
        """Read +CMGS response or error.

        Returns:
            Raw response string.
        """
        response_data = bytearray()
        deadline = asyncio.get_event_loop().time() + self.config.send_timeout

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise ATTimeoutError("AT+CMGS", self.config.send_timeout)

            try:
                chunk = await asyncio.wait_for(
                    self.at.serial.read(1024),
                    timeout=min(remaining, 1.0),
                )
                if chunk:
                    response_data.extend(chunk)

                    text = response_data.decode("utf-8", errors="replace")

                    # Check for success
                    if "+CMGS:" in text and "OK" in text:
                        return text

                    # Check for error
                    if "ERROR" in text:
                        return text
                    if "+CMS ERROR:" in text:
                        return text

            except asyncio.TimeoutError:
                continue

    def _parse_cmgs_response(self, response: str, pdu_hex: str) -> TriggerResult:
        """Parse +CMGS response.

        Args:
            response: Raw response string.
            pdu_hex: Original PDU for error reporting.

        Returns:
            TriggerResult with status.
        """
        # Check for success
        match = CMGS_PATTERN.search(response)
        if match:
            message_ref = int(match.group(1))
            logger.info("SMS sent successfully, message reference: %d", message_ref)
            return TriggerResult(
                success=True,
                message_reference=message_ref,
                raw_response=response,
            )

        # Check for error
        if "+CMS ERROR:" in response:
            # Extract error code
            cms_match = re.search(r"\+CMS ERROR:\s*(\d+)", response)
            error_code = cms_match.group(1) if cms_match else "unknown"
            error = f"+CMS ERROR: {error_code}"
            logger.error("SMS send failed: %s", error)
            return TriggerResult(
                success=False,
                raw_response=response,
                error=error,
            )

        if "ERROR" in response:
            logger.error("SMS send failed: ERROR response")
            return TriggerResult(
                success=False,
                raw_response=response,
                error="ERROR",
            )

        # Unknown response
        logger.warning("Unknown SMS response: %s", response)
        return TriggerResult(
            success=False,
            raw_response=response,
            error="Unknown response",
        )

    async def send_trigger(
        self,
        template: TriggerTemplate,
        params: Dict[str, Any],
    ) -> TriggerResult:
        """Send OTA trigger using template.

        Args:
            template: Trigger template with PDU pattern.
            params: Parameters to substitute in template.

        Returns:
            TriggerResult with send status.
        """
        # Substitute parameters in PDU template
        pdu_hex = template.pdu_template
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in pdu_hex:
                pdu_hex = pdu_hex.replace(placeholder, str(value))

        # Check for unsubstituted placeholders
        if "{" in pdu_hex or "}" in pdu_hex:
            missing = re.findall(r"\{([^}]+)\}", pdu_hex)
            raise SMSTriggerError(f"Missing template parameters: {missing}")

        return await self.send_raw_pdu(pdu_hex)

    async def get_smsc_address(self) -> Optional[str]:
        """Get current SMSC address.

        Returns:
            SMSC address if set, None otherwise.
        """
        try:
            response = await self.at.send_command("AT+CSCA?", check_error=False)
            if response.success and response.data:
                # Parse +CSCA: "<number>",<type>
                match = re.search(r'\+CSCA:\s*"([^"]+)"', response.raw_response)
                if match:
                    return match.group(1)
        except ATCommandError:
            pass
        return None

    async def set_smsc_address(self, address: str, type_of_address: int = 145) -> bool:
        """Set SMSC address.

        Args:
            address: SMSC phone number.
            type_of_address: Type of address (145=international, 129=national).

        Returns:
            True if successful.
        """
        try:
            cmd = f'AT+CSCA="{address}",{type_of_address}'
            response = await self.at.send_command(cmd)
            return response.success
        except ATCommandError:
            return False


# =============================================================================
# PDU Building Utilities
# =============================================================================


def build_simple_pdu(
    destination: str,
    data: bytes,
    smsc: str = "",
    data_coding: int = 0x00,
    protocol_id: int = 0x00,
) -> str:
    """Build a simple SMS-SUBMIT PDU.

    This is a simplified PDU builder for basic SMS messages.
    For OTA triggers, use specific PDU formats from the spec.

    Args:
        destination: Destination phone number.
        data: User data bytes.
        smsc: SMSC address (empty = use default).
        data_coding: Data coding scheme.
        protocol_id: Protocol identifier.

    Returns:
        Hex-encoded PDU string.
    """
    pdu = bytearray()

    # SMSC information
    if smsc:
        smsc_bytes = _encode_address(smsc, international=True)
        pdu.append(len(smsc_bytes))
        pdu.extend(smsc_bytes)
    else:
        pdu.append(0x00)  # Use default SMSC

    # First octet of SMS-SUBMIT
    # Bits: TP-RP=0, TP-UDHI=0, TP-SRR=0, TP-VPF=00, TP-RD=0, TP-MTI=01
    first_octet = 0x01  # SMS-SUBMIT
    if len(data) > 140:
        first_octet |= 0x40  # Set UDHI for UDL > 140
    pdu.append(first_octet)

    # TP-Message-Reference (0 = let phone set it)
    pdu.append(0x00)

    # TP-Destination-Address
    dest_bytes = _encode_address(destination)
    pdu.append((len(destination) if destination[0] != "+" else len(destination) - 1))
    pdu.extend(dest_bytes)

    # TP-Protocol-Identifier
    pdu.append(protocol_id)

    # TP-Data-Coding-Scheme
    pdu.append(data_coding)

    # TP-Validity-Period (not present with VPF=00)

    # TP-User-Data-Length
    pdu.append(len(data))

    # TP-User-Data
    pdu.extend(data)

    return pdu.hex().upper()


def _encode_address(number: str, international: bool = None) -> bytes:
    """Encode phone number for PDU.

    Args:
        number: Phone number.
        international: True for international format.

    Returns:
        Encoded address bytes (type + BCD digits).
    """
    result = bytearray()

    # Determine type of address
    if number.startswith("+"):
        number = number[1:]
        toa = 0x91  # International
    elif international:
        toa = 0x91
    else:
        toa = 0x81  # National

    result.append(toa)

    # BCD encode digits (swapped nibbles)
    if len(number) % 2 == 1:
        number += "F"  # Pad with F

    for i in range(0, len(number), 2):
        high = int(number[i + 1], 16) if number[i + 1] != "F" else 0xF
        low = int(number[i], 16)
        result.append((high << 4) | low)

    return bytes(result)


# =============================================================================
# Predefined Templates
# =============================================================================

# Basic OTA trigger template (example)
OTA_TRIGGER_TEMPLATE = TriggerTemplate(
    name="ota_trigger",
    description="Basic OTA trigger SMS",
    pdu_template="",  # Would be filled with actual OTA PDU format
    parameters=["destination", "trigger_data"],
)
