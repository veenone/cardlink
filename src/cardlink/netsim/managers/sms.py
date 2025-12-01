"""SMS Manager for network simulator integration.

This module provides centralized SMS management with MT/MO tracking,
history, and SMS-PP PDU building for OTA triggers.

Classes:
    SMSManager: Manager for SMS injection and tracking
"""

import asyncio
import logging
import struct
from datetime import datetime
from typing import Any, Optional
import uuid

from cardlink.netsim.constants import (
    DEFAULT_SMS_HISTORY_SIZE,
    EVENT_SMS_DELIVERED,
    EVENT_SMS_EVENT,
    EVENT_SMS_FAILED,
    EVENT_SMS_RECEIVED,
    EVENT_SMS_SENT,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.types import (
    NetworkEvent,
    NetworkEventType,
    SMSDirection,
    SMSMessage,
    SMSStatus,
)

log = logging.getLogger(__name__)


class SMSManager:
    """Manager for SMS injection and tracking.

    Provides centralized SMS management with:
    - MT-SMS injection
    - SMS-PP PDU building for OTA triggers
    - Message history tracking
    - Delivery status monitoring
    - MO-SMS capture

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> sms_manager = SMSManager(adapter, event_emitter)
        >>> # Send OTA trigger
        >>> msg = await sms_manager.send_sms_pp_trigger(
        ...     "001010123456789",
        ...     command_data=bytes.fromhex("A0A40000")
        ... )
        >>> print(f"Message ID: {msg.message_id}")
    """

    # Protocol Identifier for SIM Data Download (TS 23.048)
    PID_SIM_DATA_DOWNLOAD = 0x7F

    # Data Coding Scheme for 8-bit data
    DCS_8BIT_DATA = 0xF6

    def __init__(
        self,
        adapter: SimulatorInterface,
        event_emitter: Any,
        max_history_size: int = DEFAULT_SMS_HISTORY_SIZE,
    ) -> None:
        """Initialize SMS Manager.

        Args:
            adapter: The simulator adapter for SMS operations.
            event_emitter: Event emitter for broadcasting SMS events.
            max_history_size: Maximum number of messages to keep in history.
        """
        self._adapter = adapter
        self._events = event_emitter
        self._max_history_size = max_history_size

        # Message tracking
        self._message_history: list[SMSMessage] = []
        self._pending_messages: dict[str, SMSMessage] = {}
        self._message_id_counter = 0

        # Subscribe to adapter events
        asyncio.create_task(self._subscribe_events())

    async def _subscribe_events(self) -> None:
        """Subscribe to SMS events from adapter."""
        try:
            await self._adapter.subscribe_events(self._handle_event)
        except Exception as e:
            log.error(f"Failed to subscribe to SMS events: {e}")

    async def _handle_event(self, event: NetworkEvent) -> None:
        """Handle incoming SMS events.

        Args:
            event: The network event.
        """
        if event.event_type == NetworkEventType.SMS_SENT:
            await self._handle_sent(event)
        elif event.event_type == NetworkEventType.SMS_RECEIVED:
            await self._handle_received(event)

    async def _handle_sent(self, event: NetworkEvent) -> None:
        """Handle SMS sent/delivered event.

        Args:
            event: The sent event.
        """
        message_id = event.data.get("message_id")
        status_str = event.data.get("status", "sent").lower()

        # Determine status
        if status_str == "delivered":
            status = SMSStatus.DELIVERED
            event_name = EVENT_SMS_DELIVERED
        elif status_str == "failed":
            status = SMSStatus.FAILED
            event_name = EVENT_SMS_FAILED
        else:
            status = SMSStatus.SENT
            event_name = EVENT_SMS_SENT

        log.info(f"SMS {message_id}: {status.value}")

        # Update pending message
        if message_id and message_id in self._pending_messages:
            msg = self._pending_messages[message_id]
            msg = SMSMessage(
                message_id=msg.message_id,
                imsi=msg.imsi,
                direction=msg.direction,
                pdu=msg.pdu,
                status=status,
                timestamp=msg.timestamp,
                error_cause=event.data.get("error_cause"),
                metadata=msg.metadata,
            )
            self._pending_messages[message_id] = msg

            # Move to history if final status
            if status in (SMSStatus.DELIVERED, SMSStatus.FAILED):
                self._add_to_history(msg)
                del self._pending_messages[message_id]

        # Emit event
        await self._events.emit(event_name, {
            "message_id": message_id,
            "status": status.value,
            "error_cause": event.data.get("error_cause"),
        })

    async def _handle_received(self, event: NetworkEvent) -> None:
        """Handle MO-SMS received event.

        Args:
            event: The received event.
        """
        imsi = event.imsi or event.data.get("imsi", "")
        pdu_hex = event.data.get("pdu", "")

        log.info(f"MO-SMS received from {imsi}")

        # Create message record
        msg = SMSMessage(
            message_id=str(uuid.uuid4()),
            imsi=imsi,
            direction=SMSDirection.MO,
            pdu=bytes.fromhex(pdu_hex) if pdu_hex else b"",
            status=SMSStatus.DELIVERED,
            timestamp=datetime.utcnow(),
            metadata=event.data,
        )

        # Add to history
        self._add_to_history(msg)

        # Emit event
        await self._events.emit(EVENT_SMS_RECEIVED, {
            "message_id": msg.message_id,
            "imsi": imsi,
            "pdu": pdu_hex,
        })
        await self._events.emit(EVENT_SMS_EVENT, {
            "direction": "MO",
            "imsi": imsi,
            "message": msg.to_dict(),
        })

    def _add_to_history(self, msg: SMSMessage) -> None:
        """Add message to history, maintaining size limit.

        Args:
            msg: Message to add.
        """
        self._message_history.append(msg)

        # Trim history if needed
        while len(self._message_history) > self._max_history_size:
            self._message_history.pop(0)

    def _generate_message_id(self) -> str:
        """Generate unique message ID.

        Returns:
            Unique message identifier.
        """
        self._message_id_counter += 1
        return f"msg_{self._message_id_counter:06d}"

    # =========================================================================
    # Send Operations
    # =========================================================================

    async def send_mt_sms(self, imsi: str, pdu: bytes) -> SMSMessage:
        """Send MT-SMS to a specific UE.

        Args:
            imsi: Target UE IMSI.
            pdu: Raw SMS PDU bytes.

        Returns:
            SMSMessage with tracking information.
        """
        # Send via adapter
        msg = await self._adapter.send_sms(imsi, pdu)

        # Track pending message
        self._pending_messages[msg.message_id] = msg

        # Emit event
        await self._events.emit(EVENT_SMS_EVENT, {
            "direction": "MT",
            "imsi": imsi,
            "message_id": msg.message_id,
            "status": msg.status.value,
        })

        return msg

    async def send_sms_pp_trigger(
        self,
        imsi: str,
        command_data: bytes,
        tar: bytes = b"\x00\x00\x00",
        originating_address: str = "000000",
    ) -> SMSMessage:
        """Send SMS-PP trigger for OTA operations.

        Builds a complete SMS-PP PDU with SIM Data Download protocol
        identifier and sends it to the specified UE.

        Args:
            imsi: Target UE IMSI.
            command_data: The OTA command data payload.
            tar: Toolkit Application Reference (3 bytes).
            originating_address: Originating address for the SMS.

        Returns:
            SMSMessage with tracking information.
        """
        # Build OTA command packet
        ota_packet = self._build_ota_command_packet(tar, command_data)

        # Build SMS-PP PDU
        pdu = self._build_sms_pp_pdu(originating_address, ota_packet)

        log.info(f"Sending SMS-PP trigger to {imsi} (TAR={tar.hex()})")

        return await self.send_mt_sms(imsi, pdu)

    # =========================================================================
    # PDU Building
    # =========================================================================

    def _build_sms_pp_pdu(
        self, originating_address: str, user_data: bytes
    ) -> bytes:
        """Build SMS-PP PDU for SIM Data Download.

        Args:
            originating_address: Originating phone number.
            user_data: User data payload (command packet).

        Returns:
            Complete SMS-PP PDU bytes.
        """
        pdu = bytearray()

        # SMSC length (0 = use default)
        pdu.append(0x00)

        # PDU Type: SMS-DELIVER (0x04) with UDHI if needed
        pdu_type = 0x04
        if len(user_data) > 0:
            pdu_type |= 0x40  # UDHI = 1
        pdu.append(pdu_type)

        # Originating Address
        oa_encoded = self._encode_address(originating_address)
        pdu.extend(oa_encoded)

        # Protocol Identifier - SIM Data Download
        pdu.append(self.PID_SIM_DATA_DOWNLOAD)

        # Data Coding Scheme - 8-bit data
        pdu.append(self.DCS_8BIT_DATA)

        # Service Centre Time Stamp (7 bytes)
        now = datetime.utcnow()
        pdu.extend(self._encode_timestamp(now))

        # User Data Length
        pdu.append(len(user_data))

        # User Data
        pdu.extend(user_data)

        return bytes(pdu)

    def _build_ota_command_packet(
        self, tar: bytes, command_data: bytes
    ) -> bytes:
        """Build OTA command packet per 3GPP TS 31.115.

        Args:
            tar: Toolkit Application Reference (3 bytes).
            command_data: Command payload.

        Returns:
            Complete OTA command packet.
        """
        packet = bytearray()

        # Command Packet Identifier (CPI)
        # Value 0x70 indicates Response Packet
        # Value 0x02 indicates Command Packet
        packet.append(0x02)

        # Command Header Identifier (CHI)
        packet.append(0x70)

        # Length of command header
        # SPI (2) + KIc (1) + KID (1) + TAR (3) + CNTR (5) + PCNTR (1) = 13
        # For unsecured: just TAR (3) = 3
        packet.append(0x03)

        # TAR - Toolkit Application Reference
        if len(tar) != 3:
            tar = tar[:3].ljust(3, b"\x00")
        packet.extend(tar)

        # Command data
        packet.extend(command_data)

        return bytes(packet)

    def _encode_address(self, phone_number: str) -> bytes:
        """Encode phone number in SMS address format.

        Args:
            phone_number: Phone number (may start with '+').

        Returns:
            Encoded address bytes.
        """
        # Strip non-digits except '+'
        digits = "".join(c for c in phone_number if c.isdigit() or c == "+")

        # Determine type of number
        if digits.startswith("+"):
            type_of_number = 0x91  # International
            digits = digits[1:]
        else:
            type_of_number = 0x81  # National/Unknown

        # Calculate address length (number of digits)
        addr_len = len(digits)

        # BCD encode digits (swap nibbles, pad with F if odd)
        bcd = bytearray()
        for i in range(0, len(digits), 2):
            if i + 1 < len(digits):
                # Two digits - swap nibbles
                bcd.append((int(digits[i + 1]) << 4) | int(digits[i]))
            else:
                # Odd digit - pad with F
                bcd.append(0xF0 | int(digits[i]))

        # Build address field
        result = bytearray()
        result.append(addr_len)
        result.append(type_of_number)
        result.extend(bcd)

        return bytes(result)

    def _encode_timestamp(self, dt: datetime) -> bytes:
        """Encode timestamp in SMS format.

        Args:
            dt: Datetime to encode.

        Returns:
            7-byte timestamp.
        """
        # Format: YY MM DD HH MM SS TZ (all BCD with nibbles swapped)
        def bcd_swap(val: int) -> int:
            tens = val // 10
            ones = val % 10
            return (ones << 4) | tens

        ts = bytearray()
        ts.append(bcd_swap(dt.year % 100))
        ts.append(bcd_swap(dt.month))
        ts.append(bcd_swap(dt.day))
        ts.append(bcd_swap(dt.hour))
        ts.append(bcd_swap(dt.minute))
        ts.append(bcd_swap(dt.second))
        ts.append(0x00)  # Timezone (0 = UTC)

        return bytes(ts)

    # =========================================================================
    # History Operations
    # =========================================================================

    def get_message_history(self, limit: int = 100) -> list[SMSMessage]:
        """Get message history.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            List of recent messages (newest last).
        """
        return self._message_history[-limit:]

    def get_message(self, message_id: str) -> Optional[SMSMessage]:
        """Get specific message by ID.

        Args:
            message_id: The message ID to find.

        Returns:
            SMSMessage if found, None otherwise.
        """
        # Check pending first
        if message_id in self._pending_messages:
            return self._pending_messages[message_id]

        # Search history
        for msg in self._message_history:
            if msg.message_id == message_id:
                return msg

        return None

    def get_pending_messages(self) -> list[SMSMessage]:
        """Get all pending messages awaiting delivery confirmation.

        Returns:
            List of pending SMSMessage objects.
        """
        return list(self._pending_messages.values())

    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
        self._pending_messages.clear()
        log.debug("SMS history cleared")

    @property
    def history_count(self) -> int:
        """Get number of messages in history."""
        return len(self._message_history)

    @property
    def pending_count(self) -> int:
        """Get number of pending messages."""
        return len(self._pending_messages)
