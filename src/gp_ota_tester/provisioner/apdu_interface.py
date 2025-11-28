"""APDU Interface for smart card communication.

This module provides a high-level interface for constructing, sending,
and parsing APDU (Application Protocol Data Unit) commands.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from gp_ota_tester.provisioner.exceptions import APDUError, InvalidAPDUError
from gp_ota_tester.provisioner.models import APDUCommand, APDUResponse, INS

logger = logging.getLogger(__name__)


# =============================================================================
# Status Word Decoder
# =============================================================================


class SWDecoder:
    """Decoder for ISO 7816 and GlobalPlatform status words."""

    # Known status words and their meanings
    STATUS_WORDS: Dict[int, str] = {
        # Success
        0x9000: "Success",
        # Warnings (62xx)
        0x6200: "Warning: No information given",
        0x6281: "Warning: Part of returned data may be corrupted",
        0x6282: "Warning: End of file/record before Le bytes",
        0x6283: "Warning: Selected file invalidated",
        0x6284: "Warning: FCI not formatted correctly",
        0x6285: "Warning: Selected file in termination state",
        0x6286: "Warning: No input available from sensor",
        # Warnings (63xx)
        0x6300: "Warning: No information given",
        0x6381: "Warning: File filled up by last write",
        # Execution errors (64xx)
        0x6400: "Error: Execution error",
        0x6401: "Error: Immediate response required",
        # Checking errors (65xx)
        0x6500: "Error: No information given",
        0x6581: "Error: Memory failure",
        # Security errors (66xx)
        0x6600: "Error: Security-related issues",
        # Wrong length (67xx)
        0x6700: "Error: Wrong length",
        # CLA errors (68xx)
        0x6800: "Error: Functions in CLA not supported",
        0x6881: "Error: Logical channel not supported",
        0x6882: "Error: Secure messaging not supported",
        0x6883: "Error: Last command of chain expected",
        0x6884: "Error: Command chaining not supported",
        # Command not allowed (69xx)
        0x6900: "Error: Command not allowed",
        0x6981: "Error: Command incompatible with file structure",
        0x6982: "Error: Security status not satisfied",
        0x6983: "Error: Authentication method blocked",
        0x6984: "Error: Reference data not usable",
        0x6985: "Error: Conditions of use not satisfied",
        0x6986: "Error: Command not allowed (no current EF)",
        0x6987: "Error: Expected SM data objects missing",
        0x6988: "Error: Incorrect SM data objects",
        # Wrong parameters (6Axx)
        0x6A00: "Error: No information given",
        0x6A80: "Error: Incorrect parameters in data field",
        0x6A81: "Error: Function not supported",
        0x6A82: "Error: File or application not found",
        0x6A83: "Error: Record not found",
        0x6A84: "Error: Not enough memory space",
        0x6A85: "Error: Lc inconsistent with TLV structure",
        0x6A86: "Error: Incorrect parameters P1-P2",
        0x6A87: "Error: Lc inconsistent with P1-P2",
        0x6A88: "Error: Referenced data not found",
        0x6A89: "Error: File already exists",
        0x6A8A: "Error: DF name already exists",
        # Wrong P1-P2 (6Bxx)
        0x6B00: "Error: Wrong parameters P1-P2",
        # Wrong Le (6Cxx) - handled specially
        # INS not supported (6Dxx)
        0x6D00: "Error: Instruction not supported or invalid",
        # CLA not supported (6Exx)
        0x6E00: "Error: Class not supported",
        # Internal error (6Fxx)
        0x6F00: "Error: No precise diagnosis",
        # GlobalPlatform specific
        0x6283: "Warning: Card life cycle is CARD_LOCKED",
        0x6310: "More data available",
        0x6A80: "Error: Incorrect values in command data",
        0x6A81: "Error: Function not supported (e.g., card Life Cycle State)",
        0x6A84: "Error: Not enough memory space in the card",
        0x6A86: "Error: Incorrect P1 P2",
        0x6A88: "Error: Referenced data not found",
        0x6D00: "Error: Invalid instruction",
        0x6E00: "Error: Invalid class",
    }

    @classmethod
    def decode(cls, sw1: int, sw2: int) -> str:
        """Decode status word to human-readable message.

        Args:
            sw1: First status byte.
            sw2: Second status byte.

        Returns:
            Human-readable status message.
        """
        sw = (sw1 << 8) | sw2

        # Check for exact match
        if sw in cls.STATUS_WORDS:
            return cls.STATUS_WORDS[sw]

        # Handle special ranges
        if sw1 == 0x61:
            return f"More data available ({sw2} bytes)"

        if sw1 == 0x6C:
            return f"Wrong Le field ({sw2} bytes available)"

        if sw1 == 0x63 and (sw2 & 0xF0) == 0xC0:
            retries = sw2 & 0x0F
            return f"Verification failed ({retries} retries remaining)"

        if sw1 == 0x9F:
            return f"Success with {sw2} bytes available (SIM toolkit)"

        # Check for base status (xx00)
        base_sw = (sw1 << 8) | 0x00
        if base_sw in cls.STATUS_WORDS:
            return f"{cls.STATUS_WORDS[base_sw]} (SW2={sw2:02X})"

        return f"Unknown status: {sw:04X}"


# =============================================================================
# APDU Interface
# =============================================================================


# Type for transmit function
TransmitFunc = Callable[[bytes], APDUResponse]


class APDUInterface:
    """High-level interface for APDU operations.

    This class provides helper methods for common smart card operations
    and handles automatic GET RESPONSE for T=0 protocol.

    Example:
        ```python
        # Create interface with transmit function from PCSCClient
        interface = APDUInterface(client.transmit)

        # Select an application by AID
        response = interface.select_by_aid("A0000000041010")

        # Read a binary file
        data = interface.read_binary(0, 256)
        ```
    """

    def __init__(
        self,
        transmit_func: TransmitFunc,
        auto_get_response: bool = True,
    ):
        """Initialize APDU interface.

        Args:
            transmit_func: Function to transmit APDU and receive response.
            auto_get_response: Automatically handle GET RESPONSE (SW=61xx).
        """
        self._transmit = transmit_func
        self._auto_get_response = auto_get_response

    def send(self, command: APDUCommand) -> APDUResponse:
        """Send APDU command and receive response.

        Args:
            command: APDU command to send.

        Returns:
            APDU response.

        Raises:
            APDUError: If command fails with error status.
        """
        response = self._transmit(command.to_bytes())

        # Handle GET RESPONSE for T=0
        if self._auto_get_response and response.needs_get_response:
            response = self._get_response(response.sw2)

        # Handle wrong Le
        if response.wrong_length:
            # Retry with correct Le
            new_command = APDUCommand(
                cla=command.cla,
                ins=command.ins,
                p1=command.p1,
                p2=command.p2,
                data=command.data,
                le=response.sw2,
            )
            response = self._transmit(new_command.to_bytes())

            if self._auto_get_response and response.needs_get_response:
                response = self._get_response(response.sw2)

        return response

    def send_raw(self, apdu: Union[bytes, str]) -> APDUResponse:
        """Send raw APDU bytes or hex string.

        Args:
            apdu: APDU as bytes or hex string.

        Returns:
            APDU response.
        """
        if isinstance(apdu, str):
            try:
                apdu = bytes.fromhex(apdu.replace(" ", ""))
            except ValueError as e:
                raise InvalidAPDUError(f"Invalid hex string: {e}", apdu)

        if len(apdu) < 4:
            raise InvalidAPDUError("APDU too short (minimum 4 bytes)", apdu.hex())

        response = self._transmit(apdu)

        if self._auto_get_response and response.needs_get_response:
            response = self._get_response(response.sw2)

        return response

    def _get_response(self, length: int) -> APDUResponse:
        """Send GET RESPONSE command.

        Args:
            length: Number of bytes to retrieve.

        Returns:
            Response data.
        """
        command = APDUCommand(cla=0x00, ins=INS.GET_RESPONSE, p1=0x00, p2=0x00, le=length)
        return self._transmit(command.to_bytes())

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def select_by_aid(
        self,
        aid: Union[bytes, str],
        next_occurrence: bool = False,
    ) -> APDUResponse:
        """Select application by AID.

        Args:
            aid: Application Identifier as bytes or hex string.
            next_occurrence: Select next occurrence if True.

        Returns:
            SELECT response (FCI data).
        """
        if isinstance(aid, str):
            aid = bytes.fromhex(aid.replace(" ", ""))

        p2 = 0x02 if next_occurrence else 0x00  # Next occurrence or first

        command = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x04,  # Select by DF name
            p2=p2,
            data=aid,
            le=0,  # Request FCI
        )
        return self.send(command)

    def select_by_path(
        self,
        path: Union[bytes, str],
        from_mf: bool = True,
    ) -> APDUResponse:
        """Select file by path.

        Args:
            path: File path as bytes or hex string (e.g., "7F106F07").
            from_mf: Start from MF if True, else from current DF.

        Returns:
            SELECT response.
        """
        if isinstance(path, str):
            path = bytes.fromhex(path.replace(" ", ""))

        command = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x08 if from_mf else 0x09,  # Path from MF or current DF
            p2=0x04,  # Return FCP
            data=path,
            le=0,
        )
        return self.send(command)

    def select_by_file_id(self, file_id: int) -> APDUResponse:
        """Select file by file identifier.

        Args:
            file_id: 2-byte file identifier.

        Returns:
            SELECT response.
        """
        command = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x00,  # Select EF/DF by file identifier
            p2=0x04,  # Return FCP
            data=bytes([(file_id >> 8) & 0xFF, file_id & 0xFF]),
            le=0,
        )
        return self.send(command)

    def select_mf(self) -> APDUResponse:
        """Select Master File (MF).

        Returns:
            SELECT response.
        """
        command = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x00,
            p2=0x00,
            data=bytes([0x3F, 0x00]),  # MF file ID
            le=0,
        )
        return self.send(command)

    def read_binary(self, offset: int = 0, length: int = 0) -> APDUResponse:
        """Read binary data from current EF.

        Args:
            offset: Offset in file (max 32767).
            length: Number of bytes to read (0 = max available).

        Returns:
            READ BINARY response with data.
        """
        if offset > 0x7FFF:
            raise InvalidAPDUError(f"Offset too large: {offset}")

        # P1 contains high bits of offset, P2 contains low bits
        p1 = (offset >> 8) & 0x7F
        p2 = offset & 0xFF

        command = APDUCommand(
            cla=0x00,
            ins=INS.READ_BINARY,
            p1=p1,
            p2=p2,
            le=length if length <= 256 else 0,
        )
        return self.send(command)

    def read_record(
        self,
        record_number: int,
        mode: int = 0x04,  # Absolute/current mode
    ) -> APDUResponse:
        """Read record from current EF.

        Args:
            record_number: Record number (1-based).
            mode: Record selection mode (P2).

        Returns:
            READ RECORD response with data.
        """
        command = APDUCommand(
            cla=0x00,
            ins=INS.READ_RECORD,
            p1=record_number,
            p2=mode,
            le=0,
        )
        return self.send(command)

    def update_binary(
        self,
        data: Union[bytes, str],
        offset: int = 0,
    ) -> APDUResponse:
        """Update binary data in current EF.

        Args:
            data: Data to write.
            offset: Offset in file.

        Returns:
            UPDATE BINARY response.
        """
        if isinstance(data, str):
            data = bytes.fromhex(data.replace(" ", ""))

        if offset > 0x7FFF:
            raise InvalidAPDUError(f"Offset too large: {offset}")

        p1 = (offset >> 8) & 0x7F
        p2 = offset & 0xFF

        command = APDUCommand(
            cla=0x00,
            ins=INS.UPDATE_BINARY,
            p1=p1,
            p2=p2,
            data=data,
        )
        return self.send(command)

    def verify_pin(
        self,
        pin: Union[bytes, str],
        pin_ref: int = 0x01,
    ) -> APDUResponse:
        """Verify PIN.

        Args:
            pin: PIN value (bytes or ASCII string).
            pin_ref: PIN reference (P2), usually 0x01.

        Returns:
            VERIFY response.

        Note:
            PIN should be padded to 8 bytes with 0xFF if needed.
        """
        if isinstance(pin, str):
            pin = pin.encode("ascii")

        # Pad PIN to 8 bytes
        if len(pin) < 8:
            pin = pin + b"\xFF" * (8 - len(pin))

        command = APDUCommand(
            cla=0x00,
            ins=INS.VERIFY,
            p1=0x00,
            p2=pin_ref,
            data=pin,
        )
        return self.send(command)

    def get_remaining_pin_retries(self, pin_ref: int = 0x01) -> int:
        """Get remaining PIN retry count.

        Args:
            pin_ref: PIN reference.

        Returns:
            Number of remaining retries, or -1 if unknown.
        """
        # Send VERIFY with empty data to get retry count
        command = APDUCommand(
            cla=0x00,
            ins=INS.VERIFY,
            p1=0x00,
            p2=pin_ref,
        )
        response = self.send(command)

        if response.sw1 == 0x63 and (response.sw2 & 0xF0) == 0xC0:
            return response.sw2 & 0x0F
        elif response.is_success:
            return -1  # PIN already verified
        elif response.sw == 0x6983:
            return 0  # Blocked

        return -1

    def get_data(self, tag: int) -> APDUResponse:
        """Get data object by tag.

        Args:
            tag: Tag (1 or 2 bytes).

        Returns:
            GET DATA response.
        """
        if tag > 0xFF:
            p1 = (tag >> 8) & 0xFF
            p2 = tag & 0xFF
        else:
            p1 = 0x00
            p2 = tag

        command = APDUCommand(
            cla=0x00,
            ins=INS.GET_DATA,
            p1=p1,
            p2=p2,
            le=0,
        )
        return self.send(command)

    def get_response_sw(self, response: APDUResponse) -> str:
        """Get status word description for response.

        Args:
            response: APDU response.

        Returns:
            Human-readable status description.
        """
        return SWDecoder.decode(response.sw1, response.sw2)

    # =========================================================================
    # GlobalPlatform Commands
    # =========================================================================

    def get_status(
        self,
        p1: int = 0x80,  # ISD
        p2: int = 0x00,  # First or all
        aid_filter: Optional[bytes] = None,
    ) -> APDUResponse:
        """Get status of card registry (GlobalPlatform).

        Args:
            p1: Status type:
                0x80 = ISD
                0x40 = Applications and SSD
                0x20 = Executable Load Files
                0x10 = Executable Load Files and Modules
            p2: Response format:
                0x00 = First or all
                0x01 = Next occurrence
                0x02 = Get TLV data
            aid_filter: Optional AID filter (4F tag).

        Returns:
            GET STATUS response with registry data.
        """
        data = b""
        if aid_filter:
            data = bytes([0x4F, len(aid_filter)]) + aid_filter

        command = APDUCommand(
            cla=0x80,  # GlobalPlatform CLA
            ins=INS.GET_STATUS,
            p1=p1,
            p2=p2 | 0x02,  # Request TLV format
            data=data if data else bytes([0x4F, 0x00]),  # Empty filter for all
            le=0,
        )
        return self.send(command)


def check_response(
    response: APDUResponse,
    expected_sw: int = 0x9000,
    operation: str = "operation",
) -> None:
    """Check response and raise APDUError if not expected.

    Args:
        response: APDU response to check.
        expected_sw: Expected status word (default 9000).
        operation: Operation name for error message.

    Raises:
        APDUError: If status word doesn't match expected.
    """
    if response.sw != expected_sw:
        raise APDUError(
            sw1=response.sw1,
            sw2=response.sw2,
            command=None,
            status_message=SWDecoder.decode(response.sw1, response.sw2),
        )
