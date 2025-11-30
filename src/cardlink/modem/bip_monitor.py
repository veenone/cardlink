"""BIP Monitor for Modem Controller.

This module monitors Bearer Independent Protocol (BIP) events
via modem URCs and STK notifications.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from cardlink.modem.at_interface import ATInterface
from cardlink.modem.exceptions import ATCommandError, BIPMonitorError
from cardlink.modem.models import BIPCommand, BIPEvent

logger = logging.getLogger(__name__)

# STK proactive command TLV tags
STK_PROACTIVE_COMMAND_TAG = 0xD0
STK_COMMAND_DETAILS_TAG = 0x81
STK_DEVICE_IDENTITIES_TAG = 0x82
STK_ALPHA_IDENTIFIER_TAG = 0x85
STK_CHANNEL_DATA_TAG = 0xB6
STK_CHANNEL_DATA_LENGTH_TAG = 0xB7
STK_CHANNEL_STATUS_TAG = 0xB8
STK_BEARER_DESCRIPTION_TAG = 0xB5
STK_BUFFER_SIZE_TAG = 0xB9
STK_OTHER_ADDRESS_TAG = 0xBE

# BIP command type codes (from ETSI TS 102 223)
BIP_COMMAND_CODES = {
    0x40: BIPCommand.OPEN_CHANNEL,
    0x41: BIPCommand.CLOSE_CHANNEL,
    0x42: BIPCommand.RECEIVE_DATA,
    0x43: BIPCommand.SEND_DATA,
    0x44: BIPCommand.GET_CHANNEL_STATUS,
    0x45: BIPCommand.SERVICE_SEARCH,
    0x46: BIPCommand.GET_SERVICE_INFORMATION,
    0x47: BIPCommand.DECLARE_SERVICE,
}

# URC patterns for STK events
QSTK_PATTERN = re.compile(r'^\+QSTK:\s*"?([0-9A-Fa-f]+)"?')
STKPCI_PATTERN = re.compile(r'^\+STKPCI:\s*"?([0-9A-Fa-f]+)"?')


class BIPMonitor:
    """Monitors BIP events via modem URCs.

    Detects and parses STK proactive commands related to BIP
    (OPEN_CHANNEL, SEND_DATA, etc.) and emits events.

    Example:
        >>> monitor = BIPMonitor(at_interface)
        >>>
        >>> # Register event handler
        >>> def on_bip(event):
        ...     print(f"BIP event: {event.command}")
        >>> monitor.on_bip_event(on_bip)
        >>>
        >>> # Start monitoring
        >>> await monitor.start()
        >>>
        >>> # ... BIP events will be received ...
        >>>
        >>> await monitor.stop()
    """

    def __init__(self, at_interface: ATInterface):
        """Initialize BIP monitor.

        Args:
            at_interface: AT interface for communication.
        """
        self.at = at_interface
        self._running = False
        self._event_callbacks: List[Callable[[BIPEvent], Any]] = []

    @property
    def is_running(self) -> bool:
        """Check if monitor is active."""
        return self._running

    async def start(self) -> None:
        """Start BIP event monitoring.

        Enables STK notifications and registers URC handlers.

        Raises:
            BIPMonitorError: If monitoring cannot be started.
        """
        if self._running:
            return

        try:
            # Enable STK notifications
            await self.enable_stk_notifications()

            # Register URC handlers
            self._register_urc_handlers()

            # Start URC monitoring on AT interface
            await self.at.start_urc_monitoring()

            self._running = True
            logger.info("BIP monitoring started")

        except Exception as e:
            raise BIPMonitorError(f"Failed to start BIP monitoring: {e}")

    async def stop(self) -> None:
        """Stop BIP event monitoring."""
        if not self._running:
            return

        # Unregister handlers
        self._unregister_urc_handlers()

        self._running = False
        logger.info("BIP monitoring stopped")

    async def enable_stk_notifications(self) -> None:
        """Enable STK/USAT URC notifications.

        Sends appropriate commands to enable proactive command
        notifications (varies by vendor).
        """
        # Try Quectel command first
        try:
            response = await self.at.send_command("AT+QSTK=1", check_error=False)
            if response.success:
                logger.debug("Enabled STK notifications via AT+QSTK=1")
                return
        except ATCommandError:
            pass

        # Try generic STK enable
        try:
            response = await self.at.send_command("AT+STKTR=1", check_error=False)
            if response.success:
                logger.debug("Enabled STK notifications via AT+STKTR=1")
                return
        except ATCommandError:
            pass

        # Log warning but don't fail - some modems enable by default
        logger.warning("Could not enable STK notifications (may be enabled by default)")

    async def disable_stk_notifications(self) -> None:
        """Disable STK/USAT URC notifications."""
        try:
            await self.at.send_command("AT+QSTK=0", check_error=False)
        except ATCommandError:
            pass

    def _register_urc_handlers(self) -> None:
        """Register URC handlers for STK events."""
        # Quectel QSTK handler
        self.at.register_urc_handler(
            r"^\+QSTK:\s*",
            self._handle_qstk_urc,
            name="bip_qstk",
        )

        # Generic STKPCI handler
        self.at.register_urc_handler(
            r"^\+STKPCI:\s*",
            self._handle_stkpci_urc,
            name="bip_stkpci",
        )

    def _unregister_urc_handlers(self) -> None:
        """Unregister URC handlers."""
        self.at.unregister_urc_handlers("bip_qstk")
        self.at.unregister_urc_handlers("bip_stkpci")

    async def _handle_qstk_urc(self, line: str, match: re.Match) -> None:
        """Handle +QSTK URC."""
        qstk_match = QSTK_PATTERN.match(line)
        if qstk_match:
            pdu_hex = qstk_match.group(1)
            await self._process_stk_pdu(pdu_hex)

    async def _handle_stkpci_urc(self, line: str, match: re.Match) -> None:
        """Handle +STKPCI URC."""
        stkpci_match = STKPCI_PATTERN.match(line)
        if stkpci_match:
            pdu_hex = stkpci_match.group(1)
            await self._process_stk_pdu(pdu_hex)

    async def _process_stk_pdu(self, pdu_hex: str) -> None:
        """Process STK proactive command PDU.

        Args:
            pdu_hex: Hex-encoded proactive command PDU.
        """
        try:
            pdu_bytes = bytes.fromhex(pdu_hex)
            event = self._parse_proactive_command(pdu_bytes, pdu_hex)

            if event:
                logger.info("BIP event detected: %s", event.command.name)
                await self._emit_event(event)

        except ValueError as e:
            logger.warning("Invalid STK PDU: %s - %s", pdu_hex, e)
        except Exception as e:
            logger.error("Error processing STK PDU: %s", e)

    def _parse_proactive_command(
        self,
        pdu: bytes,
        pdu_hex: str,
    ) -> Optional[BIPEvent]:
        """Parse proactive command into BIPEvent.

        Args:
            pdu: PDU bytes.
            pdu_hex: Original hex string.

        Returns:
            BIPEvent if this is a BIP command, None otherwise.
        """
        if len(pdu) < 4:
            return None

        # Check for proactive command tag
        idx = 0
        if pdu[idx] == STK_PROACTIVE_COMMAND_TAG:
            idx += 1
            # Length (may be 1 or 2 bytes)
            if pdu[idx] == 0x81:
                idx += 2  # Two-byte length
            else:
                idx += 1

        # Parse TLV objects
        command_type = None
        channel_id = None
        buffer_size = None
        data_length = None
        alpha_id = None
        dest_address = None
        parameters: Dict[str, Any] = {}

        while idx < len(pdu) - 1:
            tag = pdu[idx]
            idx += 1

            # Get length (may be extended)
            if idx >= len(pdu):
                break
            length = pdu[idx]
            idx += 1

            if length == 0x81:
                if idx >= len(pdu):
                    break
                length = pdu[idx]
                idx += 1

            # Ensure we have enough data
            if idx + length > len(pdu):
                break

            value = pdu[idx : idx + length]
            idx += length

            # Parse based on tag
            if tag == STK_COMMAND_DETAILS_TAG and len(value) >= 3:
                # Command details: command number, type, qualifier
                command_type = value[1]  # Type of command
                parameters["command_number"] = value[0]
                parameters["command_qualifier"] = value[2]

            elif tag == STK_DEVICE_IDENTITIES_TAG and len(value) >= 2:
                parameters["source_device"] = value[0]
                parameters["dest_device"] = value[1]

            elif tag == STK_ALPHA_IDENTIFIER_TAG:
                # Alpha identifier (text)
                try:
                    alpha_id = value.decode("utf-8", errors="replace")
                except Exception:
                    alpha_id = value.hex()

            elif tag == STK_BUFFER_SIZE_TAG and len(value) >= 2:
                buffer_size = (value[0] << 8) | value[1]

            elif tag == STK_CHANNEL_DATA_TAG:
                parameters["channel_data"] = value.hex()

            elif tag == STK_CHANNEL_DATA_LENGTH_TAG and len(value) >= 1:
                data_length = value[0]
                if len(value) >= 2:
                    data_length = (value[0] << 8) | value[1]

            elif tag == STK_CHANNEL_STATUS_TAG and len(value) >= 2:
                channel_id = value[0] & 0x07  # Channel ID is bits 0-2
                parameters["channel_status"] = {
                    "channel_id": channel_id,
                    "link_established": bool(value[0] & 0x80),
                    "info": value[1] if len(value) > 1 else 0,
                }

            elif tag == STK_BEARER_DESCRIPTION_TAG and len(value) >= 1:
                bearer_type = value[0]
                parameters["bearer_type"] = bearer_type
                parameters["bearer_description"] = value.hex()

            elif tag == STK_OTHER_ADDRESS_TAG and len(value) >= 1:
                addr_type = value[0]
                if addr_type == 0x21 and len(value) >= 5:  # IPv4
                    dest_address = ".".join(str(b) for b in value[1:5])
                elif len(value) > 1:
                    dest_address = value[1:].hex()

        # Check if this is a BIP command
        if command_type is None or command_type not in BIP_COMMAND_CODES:
            return None

        bip_command = BIP_COMMAND_CODES[command_type]

        return BIPEvent(
            command=bip_command,
            timestamp=datetime.now(),
            raw_pdu=pdu_hex,
            channel_id=channel_id,
            buffer_size=buffer_size,
            data_length=data_length,
            alpha_identifier=alpha_id,
            destination_address=dest_address,
            parameters=parameters,
        )

    async def _emit_event(self, event: BIPEvent) -> None:
        """Emit BIP event to registered callbacks."""
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error("Error in BIP event callback: %s", e)

    def on_bip_event(self, callback: Callable[[BIPEvent], Any]) -> None:
        """Register callback for BIP events.

        Args:
            callback: Function to call when BIP event received.
        """
        self._event_callbacks.append(callback)

    def remove_bip_callback(self, callback: Callable[[BIPEvent], Any]) -> None:
        """Remove BIP event callback.

        Args:
            callback: Callback to remove.
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def clear_callbacks(self) -> None:
        """Remove all BIP event callbacks."""
        self._event_callbacks.clear()


# =============================================================================
# Utility Functions
# =============================================================================


def parse_bip_command(pdu_hex: str) -> Optional[BIPEvent]:
    """Parse BIP command from hex PDU string.

    Utility function for parsing BIP commands outside of monitor context.

    Args:
        pdu_hex: Hex-encoded proactive command PDU.

    Returns:
        BIPEvent if this is a BIP command, None otherwise.
    """
    try:
        pdu_bytes = bytes.fromhex(pdu_hex)
        monitor = BIPMonitor.__new__(BIPMonitor)
        return monitor._parse_proactive_command(pdu_bytes, pdu_hex)
    except Exception:
        return None


def get_bip_command_name(command_code: int) -> str:
    """Get BIP command name from code.

    Args:
        command_code: Command type byte.

    Returns:
        Command name string.
    """
    if command_code in BIP_COMMAND_CODES:
        return BIP_COMMAND_CODES[command_code].name
    return f"UNKNOWN_{command_code:02X}"
