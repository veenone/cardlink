"""SMS-PP Trigger for OTA session initiation.

This module provides the SMSTrigger class for sending SMS-PP trigger
messages to initiate OTA sessions on Android devices.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Optional

from cardlink.phone.adb_client import ADBClient
from cardlink.phone.at_interface import ATInterface
from cardlink.phone.exceptions import SMSTriggerError
from cardlink.phone.models import TriggerResult, TriggerTemplate

logger = logging.getLogger(__name__)


# Pre-defined trigger templates
DEFAULT_TEMPLATES: Dict[str, TriggerTemplate] = {
    "ota_trigger": TriggerTemplate(
        name="ota_trigger",
        description="Standard OTA trigger for HTTPS admin session",
        pdu_template=(
            "0001000B91{smsc}0004{pid}00{ud_length}{ud}"
        ),
        parameters={
            "smsc": "SMSC address in semi-octet format",
            "pid": "Protocol Identifier (default: 7F for SIM Data Download)",
            "ud_length": "User Data length in hex",
            "ud": "User Data (trigger command)",
        },
    ),
    "ram_push": TriggerTemplate(
        name="ram_push",
        description="RAM Push trigger for applet installation",
        pdu_template=(
            "0001000B91{smsc}0004{pid}00{ud_length}{ud}"
        ),
        parameters={
            "smsc": "SMSC address",
            "pid": "Protocol Identifier",
            "ud_length": "User Data length",
            "ud": "RAM push command data",
        },
    ),
    "custom": TriggerTemplate(
        name="custom",
        description="Custom PDU trigger",
        pdu_template="{pdu}",
        parameters={
            "pdu": "Complete PDU in hex format",
        },
    ),
}


class SMSTrigger:
    """Sends SMS-PP trigger messages for OTA session initiation.

    This class supports sending SMS-PP (Point-to-Point) trigger messages
    to the UICC to initiate Over-The-Air sessions. It supports:
    - Pre-defined trigger templates
    - Custom PDU messages
    - Multiple delivery methods (AT+CMGS, content provider, ADB)

    SMS-PP Format (GSM 03.40):
    - Message Type Indicator: SMS-DELIVER (00) or SMS-SUBMIT (01)
    - Protocol Identifier: 7F for SIM Data Download
    - Data Coding Scheme: 16 for Class 2 (SIM specific)
    - User Data: Trigger command

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.
        at_interface: Optional ATInterface for AT command method.

    Example:
        ```python
        client = ADBClient()
        at = ATInterface(client, "device123")
        trigger = SMSTrigger(client, "device123", at)

        # Send using template
        result = await trigger.send_trigger("ota_trigger", {
            "smsc": "1234567890",
            "ud": "D0..."
        })

        # Send raw PDU
        result = await trigger.send_raw_pdu("0001000B91...")
        ```
    """

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
        at_interface: Optional[ATInterface] = None,
    ):
        """Initialize SMS trigger.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
            at_interface: Optional ATInterface for AT commands.
        """
        self._client = adb_client
        self._serial = serial
        self._at = at_interface

        # Custom templates
        self._templates: Dict[str, TriggerTemplate] = DEFAULT_TEMPLATES.copy()

    @property
    def templates(self) -> Dict[str, TriggerTemplate]:
        """Get available trigger templates."""
        return self._templates.copy()

    def add_template(self, template: TriggerTemplate) -> None:
        """Add a custom trigger template.

        Args:
            template: TriggerTemplate to add.
        """
        self._templates[template.name] = template

    def remove_template(self, name: str) -> bool:
        """Remove a custom template.

        Args:
            name: Template name to remove.

        Returns:
            True if template was removed.
        """
        if name in self._templates and name not in DEFAULT_TEMPLATES:
            del self._templates[name]
            return True
        return False

    def build_pdu(
        self,
        template_name: str,
        params: Dict[str, str],
    ) -> str:
        """Build SMS PDU from template.

        Args:
            template_name: Name of template to use.
            params: Template parameters.

        Returns:
            Hex-encoded PDU string.

        Raises:
            SMSTriggerError: If template not found or params missing.
        """
        template = self._templates.get(template_name)
        if template is None:
            raise SMSTriggerError(f"Template not found: {template_name}")

        try:
            pdu = template.pdu_template.format(**params)
        except KeyError as e:
            raise SMSTriggerError(f"Missing parameter: {e}")

        # Validate PDU format
        if not self._is_valid_hex(pdu):
            raise SMSTriggerError(f"Invalid PDU format: not valid hex")

        return pdu.upper()

    def build_ota_trigger_pdu(
        self,
        smsc: str,
        destination: str,
        command_data: bytes,
        protocol_id: int = 0x7F,
        data_coding: int = 0x16,
    ) -> str:
        """Build OTA trigger PDU according to GSM 03.40.

        Args:
            smsc: SMSC address (phone number).
            destination: Destination address (usually same as SMSC).
            command_data: Trigger command data.
            protocol_id: Protocol Identifier (0x7F for SIM Data Download).
            data_coding: Data Coding Scheme (0x16 for Class 2).

        Returns:
            Hex-encoded PDU string.
        """
        pdu_parts = []

        # SMSC Length and Address (0 if not included)
        pdu_parts.append("00")

        # First Octet: SMS-SUBMIT (01), no reply path, no validity period
        pdu_parts.append("11")

        # Message Reference (auto)
        pdu_parts.append("00")

        # Destination Address
        dest_encoded = self._encode_address(destination)
        pdu_parts.append(dest_encoded)

        # Protocol Identifier
        pdu_parts.append(f"{protocol_id:02X}")

        # Data Coding Scheme
        pdu_parts.append(f"{data_coding:02X}")

        # User Data Length
        ud_length = len(command_data)
        pdu_parts.append(f"{ud_length:02X}")

        # User Data
        pdu_parts.append(command_data.hex().upper())

        return "".join(pdu_parts)

    def _encode_address(self, number: str) -> str:
        """Encode phone number in GSM format.

        Args:
            number: Phone number string.

        Returns:
            Encoded address with length and type.
        """
        # Remove non-digit characters except '+'
        number = re.sub(r"[^\d+]", "", number)

        # Determine type of address
        if number.startswith("+"):
            type_byte = 0x91  # International format
            number = number[1:]
        else:
            type_byte = 0x81  # Unknown format

        # Length is number of digits
        length = len(number)

        # Pad with F if odd length
        if len(number) % 2:
            number += "F"

        # Swap nibbles (semi-octet encoding)
        swapped = ""
        for i in range(0, len(number), 2):
            swapped += number[i + 1] + number[i]

        return f"{length:02X}{type_byte:02X}{swapped}"

    async def send_trigger(
        self,
        template_name: str,
        params: Dict[str, str],
    ) -> TriggerResult:
        """Send SMS trigger using a template.

        Args:
            template_name: Name of template to use.
            params: Template parameters.

        Returns:
            TriggerResult with status.
        """
        try:
            pdu = self.build_pdu(template_name, params)
            return await self.send_raw_pdu(pdu)
        except SMSTriggerError as e:
            return TriggerResult(
                success=False,
                error_message=str(e),
                timestamp=datetime.now(),
            )

    async def send_raw_pdu(self, pdu: str) -> TriggerResult:
        """Send raw SMS PDU.

        Args:
            pdu: Hex-encoded PDU string.

        Returns:
            TriggerResult with status.
        """
        result = TriggerResult(
            success=False,
            pdu_sent=pdu,
            timestamp=datetime.now(),
        )

        # Try AT+CMGS method first
        if self._at and await self._at.is_available():
            try:
                at_result = await self._send_via_at(pdu)
                if at_result:
                    result.success = True
                    result.method_used = "AT+CMGS"
                    return result
            except Exception as e:
                logger.debug(f"AT method failed: {e}")

        # Try content provider method
        try:
            cp_result = await self._send_via_content_provider(pdu)
            if cp_result:
                result.success = True
                result.method_used = "content_provider"
                return result
        except Exception as e:
            logger.debug(f"Content provider method failed: {e}")

        # Try intent broadcast method
        try:
            intent_result = await self._send_via_intent(pdu)
            if intent_result:
                result.success = True
                result.method_used = "intent"
                return result
        except Exception as e:
            logger.debug(f"Intent method failed: {e}")

        result.error_message = "All trigger methods failed"
        return result

    async def _send_via_at(self, pdu: str) -> bool:
        """Send PDU via AT+CMGS command."""
        if self._at is None:
            return False

        # Set PDU mode
        response = await self._at.send_command("AT+CMGF=0")
        if not response.is_ok:
            logger.debug("Failed to set PDU mode")

        # Calculate TPDU length (PDU length minus SMSC info)
        # If SMSC length is 00, TPDU = full PDU - 2 chars (1 byte)
        smsc_len = int(pdu[0:2], 16)
        if smsc_len == 0:
            tpdu_len = (len(pdu) - 2) // 2
        else:
            tpdu_len = (len(pdu) - 2 - (smsc_len * 2 + 2)) // 2

        # Send AT+CMGS=length
        response = await self._at.send_command(f"AT+CMGS={tpdu_len}")

        # This should prompt for PDU input (> prompt)
        # In practice, we need to send PDU followed by Ctrl+Z (0x1A)

        # For now, try direct send
        full_cmd = f"AT+CMGS={tpdu_len}\r{pdu}\x1a"
        try:
            output = await self._client.shell(
                f'echo -e "{full_cmd}" > /dev/smd0',
                self._serial,
                check_error=False,
            )
            return "OK" in output or "+CMGS:" in output
        except Exception:
            return False

    async def _send_via_content_provider(self, pdu: str) -> bool:
        """Send PDU via Android content provider."""
        # Use SMS content provider
        # This requires appropriate permissions
        try:
            # Insert into raw SMS inbox to trigger processing
            cmd = (
                f"content insert --uri content://sms/inbox "
                f"--bind protocol:i:0 "
                f"--bind body:s:{pdu}"
            )
            output = await self._client.shell(cmd, self._serial, check_error=False)
            return "Row:" in output or "inserted" in output.lower()
        except Exception:
            return False

    async def _send_via_intent(self, pdu: str) -> bool:
        """Send PDU via Android intent broadcast."""
        # This simulates receiving an SMS
        # Requires system permissions on most devices
        try:
            cmd = (
                'am broadcast -a android.provider.Telephony.SMS_DELIVER '
                f'-n com.android.phone/.InboundSmsHandler '
                f'--es "pdu" "{pdu}"'
            )
            output = await self._client.shell(cmd, self._serial, check_error=False)
            return "Broadcast completed" in output
        except Exception:
            return False

    def _is_valid_hex(self, s: str) -> bool:
        """Check if string is valid hex."""
        try:
            bytes.fromhex(s.replace(" ", ""))
            return True
        except ValueError:
            return False

    # =========================================================================
    # Common OTA Trigger Helpers
    # =========================================================================

    async def send_https_admin_trigger(
        self,
        tar: str = "B0FF",
        counter: int = 0,
        padding_counter: int = 0,
    ) -> TriggerResult:
        """Send HTTPS Admin trigger for SCP81 session.

        Args:
            tar: Toolkit Application Reference (default B0FF).
            counter: Counter value.
            padding_counter: Padding counter.

        Returns:
            TriggerResult with status.

        Note:
            This is a simplified trigger. Real implementations need
            proper security (KIC, KID, cryptographic checksums).
        """
        # Build command packet header (simplified)
        # Real implementation needs SCP02/SCP03 security
        cmd_data = bytes.fromhex(tar)
        cmd_data += counter.to_bytes(3, "big")
        cmd_data += padding_counter.to_bytes(1, "big")

        # Build PDU
        pdu = self.build_ota_trigger_pdu(
            smsc="",
            destination="",
            command_data=cmd_data,
            protocol_id=0x7F,
            data_coding=0xF6,  # Class 2, 8-bit
        )

        return await self.send_raw_pdu(pdu)

    async def inject_sms(
        self,
        sender: str,
        body: str,
    ) -> bool:
        """Inject an SMS into the inbox.

        This is useful for testing SMS-based triggers without
        actually sending over the network.

        Args:
            sender: Sender phone number.
            body: Message body.

        Returns:
            True if injection successful.
        """
        try:
            cmd = (
                f'content insert --uri content://sms/inbox '
                f'--bind address:s:"{sender}" '
                f'--bind body:s:"{body}" '
                f'--bind read:i:0'
            )
            output = await self._client.shell(cmd, self._serial, check_error=False)
            return "Row:" in output
        except Exception as e:
            logger.error(f"SMS injection failed: {e}")
            return False
