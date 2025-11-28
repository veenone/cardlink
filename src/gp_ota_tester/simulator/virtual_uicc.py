"""Virtual UICC card simulation.

This module provides a virtual UICC implementation that processes
C-APDUs and generates R-APDUs according to ISO 7816-4 and GlobalPlatform
specifications.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .config import UICCProfile
from .models import VirtualApplet

logger = logging.getLogger(__name__)


# =============================================================================
# Status Words
# =============================================================================


class SW:
    """Common ISO 7816-4 Status Words."""

    SUCCESS = "9000"
    BYTES_REMAINING_00 = "6100"  # 61XX - bytes remaining
    WRONG_LENGTH = "6700"
    SECURITY_NOT_SATISFIED = "6982"
    AUTH_METHOD_BLOCKED = "6983"
    CONDITIONS_NOT_SATISFIED = "6985"
    COMMAND_NOT_ALLOWED = "6986"
    WRONG_DATA = "6A80"
    FUNC_NOT_SUPPORTED = "6A81"
    FILE_NOT_FOUND = "6A82"
    RECORD_NOT_FOUND = "6A83"
    INCORRECT_P1P2 = "6A86"
    WRONG_P1P2 = "6B00"
    WRONG_LE = "6C00"  # 6CXX - wrong Le
    INS_NOT_SUPPORTED = "6D00"
    CLA_NOT_SUPPORTED = "6E00"
    UNKNOWN_ERROR = "6F00"

    @staticmethod
    def bytes_remaining(count: int) -> str:
        """Generate 61XX status word."""
        return f"61{count:02X}"

    @staticmethod
    def wrong_le(correct_le: int) -> str:
        """Generate 6CXX status word."""
        return f"6C{correct_le:02X}"


# =============================================================================
# APDU Parser
# =============================================================================


@dataclass
class ParsedAPDU:
    """Parsed APDU command.

    Attributes:
        cla: Class byte.
        ins: Instruction byte.
        p1: Parameter 1.
        p2: Parameter 2.
        lc: Command data length.
        data: Command data bytes.
        le: Expected response length.
    """

    cla: int
    ins: int
    p1: int
    p2: int
    lc: int = 0
    data: bytes = b""
    le: Optional[int] = None

    @classmethod
    def parse(cls, apdu: bytes) -> "ParsedAPDU":
        """Parse APDU bytes into components.

        Supports Case 1-4 APDU formats.

        Args:
            apdu: Raw APDU bytes.

        Returns:
            ParsedAPDU instance.

        Raises:
            ValueError: If APDU format is invalid.
        """
        if len(apdu) < 4:
            raise ValueError(f"APDU too short: {len(apdu)} bytes")

        cla = apdu[0]
        ins = apdu[1]
        p1 = apdu[2]
        p2 = apdu[3]

        # Case 1: CLA INS P1 P2
        if len(apdu) == 4:
            return cls(cla=cla, ins=ins, p1=p1, p2=p2)

        # Case 2: CLA INS P1 P2 Le
        if len(apdu) == 5:
            le = apdu[4]
            if le == 0:
                le = 256
            return cls(cla=cla, ins=ins, p1=p1, p2=p2, le=le)

        # Case 3 or 4: CLA INS P1 P2 Lc Data [Le]
        lc = apdu[4]
        if lc == 0:
            # Extended length encoding (not supported yet)
            raise ValueError("Extended length APDUs not supported")

        data = apdu[5: 5 + lc]
        if len(data) != lc:
            raise ValueError(f"Data length mismatch: expected {lc}, got {len(data)}")

        # Check for Le
        remaining = len(apdu) - 5 - lc
        if remaining == 0:
            # Case 3: No Le
            return cls(cla=cla, ins=ins, p1=p1, p2=p2, lc=lc, data=data)
        elif remaining == 1:
            # Case 4: Le present
            le = apdu[5 + lc]
            if le == 0:
                le = 256
            return cls(cla=cla, ins=ins, p1=p1, p2=p2, lc=lc, data=data, le=le)
        else:
            raise ValueError(f"Invalid APDU length: {len(apdu)}")

    @property
    def ins_name(self) -> str:
        """Get human-readable INS name."""
        names = {
            0xA4: "SELECT",
            0xB0: "READ BINARY",
            0xB2: "READ RECORD",
            0xC0: "GET RESPONSE",
            0xCA: "GET DATA",
            0xD6: "UPDATE BINARY",
            0xDC: "UPDATE RECORD",
            0xE2: "STORE DATA",
            0xE4: "DELETE",
            0xE6: "INSTALL",
            0xE8: "LOAD",
            0xF2: "GET STATUS",
            0x50: "INITIALIZE UPDATE",
            0x82: "EXTERNAL AUTHENTICATE",
            0x84: "GET CHALLENGE",
            0xD8: "PUT KEY",
        }
        return names.get(self.ins, f"INS_{self.ins:02X}")


# =============================================================================
# Virtual UICC
# =============================================================================


class VirtualUICC:
    """Virtual UICC card simulation.

    Processes C-APDUs and generates R-APDUs according to ISO 7816-4
    and GlobalPlatform specifications.

    Attributes:
        profile: UICC profile configuration.

    Example:
        >>> uicc = VirtualUICC(UICCProfile())
        >>> r_apdu = uicc.process_apdu(bytes.fromhex("00A4040007A000000151000000"))
        >>> print(r_apdu.hex().upper())
    """

    def __init__(self, profile: UICCProfile):
        """Initialize with UICC profile.

        Args:
            profile: Virtual UICC profile configuration.
        """
        self.profile = profile

        # Card state
        self._selected_aid: Optional[bytes] = None
        self._security_level: int = 0
        self._challenge: Optional[bytes] = None

        # Command handlers
        self._handlers: Dict[int, Callable[[ParsedAPDU], bytes]] = {
            0xA4: self._handle_select,
            0xC0: self._handle_get_response,
            0xCA: self._handle_get_data,
            0xE2: self._handle_store_data,
            0xF2: self._handle_get_status,
            0x50: self._handle_initialize_update,
            0x82: self._handle_external_authenticate,
            0x84: self._handle_get_challenge,
        }

        # Pending response data (for GET RESPONSE)
        self._pending_response: bytes = b""

    @property
    def selected_aid(self) -> Optional[bytes]:
        """Get currently selected application AID."""
        return self._selected_aid

    @property
    def selected_aid_hex(self) -> Optional[str]:
        """Get currently selected application AID as hex string."""
        return self._selected_aid.hex().upper() if self._selected_aid else None

    def reset(self) -> None:
        """Reset card state."""
        self._selected_aid = None
        self._security_level = 0
        self._challenge = None
        self._pending_response = b""
        logger.debug("UICC state reset")

    def process_apdu(self, apdu: bytes) -> bytes:
        """Process C-APDU and return R-APDU.

        Args:
            apdu: C-APDU command bytes.

        Returns:
            R-APDU response bytes (data + SW).

        Example:
            >>> r_apdu = uicc.process_apdu(bytes.fromhex("00A4040007A000000151000000"))
        """
        try:
            parsed = ParsedAPDU.parse(apdu)
            logger.debug(
                f"Processing {parsed.ins_name} (CLA={parsed.cla:02X} INS={parsed.ins:02X} "
                f"P1={parsed.p1:02X} P2={parsed.p2:02X})"
            )

            # Find handler
            handler = self._handlers.get(parsed.ins)
            if handler:
                return handler(parsed)
            else:
                logger.warning(f"Unsupported instruction: INS={parsed.ins:02X}")
                return bytes.fromhex(SW.INS_NOT_SUPPORTED)

        except ValueError as e:
            logger.error(f"APDU parse error: {e}")
            return bytes.fromhex(SW.WRONG_LENGTH)
        except Exception as e:
            logger.error(f"APDU processing error: {e}")
            return bytes.fromhex(SW.UNKNOWN_ERROR)

    def _make_response(self, data: bytes, sw: str) -> bytes:
        """Build R-APDU response.

        Args:
            data: Response data.
            sw: Status word (4 hex chars).

        Returns:
            Complete R-APDU bytes.
        """
        return data + bytes.fromhex(sw)

    def _handle_select(self, apdu: ParsedAPDU) -> bytes:
        """Handle SELECT command (INS=A4).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # P1 values:
        # 00 = Select MF, DF, or EF by file identifier
        # 04 = Select by DF name (AID)
        # P2 values:
        # 00 = First or only occurrence, FCI template
        # 0C = First or only occurrence, no FCI

        if apdu.p1 == 0x04:
            # Select by AID
            aid = apdu.data
            aid_hex = aid.hex().upper()

            # Check if this is a known AID
            if aid_hex == self.profile.aid_isd.upper():
                # Selecting ISD
                self._selected_aid = aid
                logger.info(f"Selected ISD: {aid_hex}")

                # Build FCI response
                fci = self._build_fci(aid)
                return self._make_response(fci, SW.SUCCESS)

            # Check registered applets
            for applet in self.profile.applets:
                if applet.aid.upper() == aid_hex:
                    self._selected_aid = aid
                    logger.info(f"Selected applet: {applet.name} ({aid_hex})")
                    fci = self._build_fci(aid)
                    return self._make_response(fci, SW.SUCCESS)

            # Unknown AID - still select it (simulating successful selection)
            self._selected_aid = aid
            logger.info(f"Selected unknown AID: {aid_hex}")
            fci = self._build_fci(aid)
            return self._make_response(fci, SW.SUCCESS)

        elif apdu.p1 == 0x00:
            # Select by file ID
            if len(apdu.data) == 2:
                file_id = apdu.data.hex().upper()
                if file_id == "3F00":
                    # MF selected
                    self._selected_aid = None
                    logger.info("Selected MF")
                    return self._make_response(b"", SW.SUCCESS)

            return bytes.fromhex(SW.FILE_NOT_FOUND)

        else:
            return bytes.fromhex(SW.INCORRECT_P1P2)

    def _build_fci(self, aid: bytes) -> bytes:
        """Build FCI (File Control Information) response.

        Args:
            aid: Application Identifier.

        Returns:
            FCI TLV data.
        """
        # FCI Template (6F)
        # - DF Name (84): AID
        # - FCI Proprietary Template (A5)
        #   - Life Cycle State (9F6E): 01 (Loaded)
        #   - Security Domain Management Data (73): ...

        # Simple FCI response
        aid_tlv = bytes([0x84, len(aid)]) + aid
        lifecycle_tlv = bytes([0x9F, 0x6E, 0x01, 0x01])  # Loaded state

        a5_content = lifecycle_tlv
        a5_tlv = bytes([0xA5, len(a5_content)]) + a5_content

        fci_content = aid_tlv + a5_tlv
        fci = bytes([0x6F, len(fci_content)]) + fci_content

        return fci

    def _handle_get_response(self, apdu: ParsedAPDU) -> bytes:
        """Handle GET RESPONSE command (INS=C0).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        if not self._pending_response:
            return bytes.fromhex(SW.CONDITIONS_NOT_SATISFIED)

        le = apdu.le or 256
        data = self._pending_response[:le]
        self._pending_response = self._pending_response[le:]

        if self._pending_response:
            # More data available
            remaining = len(self._pending_response)
            sw = SW.bytes_remaining(min(remaining, 255))
        else:
            sw = SW.SUCCESS

        return self._make_response(data, sw)

    def _handle_get_data(self, apdu: ParsedAPDU) -> bytes:
        """Handle GET DATA command (INS=CA).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # Tag is P1P2
        tag = (apdu.p1 << 8) | apdu.p2

        # Common tags
        if tag == 0x9F7F:
            # Card Production Life Cycle Data (CPLC)
            cplc = bytes(42)  # Dummy CPLC
            return self._make_response(cplc, SW.SUCCESS)
        elif tag == 0x0066:
            # Card Data
            data = bytes([0x66, 0x04, 0x73, 0x02, 0x06, 0x00])
            return self._make_response(data, SW.SUCCESS)
        elif tag == 0x00E0:
            # Key Information Template
            data = bytes([0xE0, 0x00])  # Empty
            return self._make_response(data, SW.SUCCESS)
        else:
            logger.debug(f"GET DATA for unknown tag: {tag:04X}")
            return bytes.fromhex(SW.FILE_NOT_FOUND)

    def _handle_store_data(self, apdu: ParsedAPDU) -> bytes:
        """Handle STORE DATA command (INS=E2).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # Accept any STORE DATA (simulating successful storage)
        logger.debug(f"STORE DATA: {len(apdu.data)} bytes")
        return bytes.fromhex(SW.SUCCESS)

    def _handle_get_status(self, apdu: ParsedAPDU) -> bytes:
        """Handle GET STATUS command (INS=F2).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # P1: Status type
        # 40 = Issuer Security Domain
        # 20 = Executable Load Files
        # 10 = Executable Load Files and Modules
        # 80 = Application / Security Domains

        if apdu.p1 == 0x40:
            # ISD status
            aid = bytes.fromhex(self.profile.aid_isd)
            entry = self._build_status_entry(aid, lifecycle=0x01, privileges=0x00)
            return self._make_response(entry, SW.SUCCESS)

        elif apdu.p1 in (0x20, 0x10, 0x80):
            # Return registered applets
            if not self.profile.applets:
                return bytes.fromhex(SW.FILE_NOT_FOUND)

            entries = b""
            for applet in self.profile.applets:
                aid = bytes.fromhex(applet.aid)
                priv = int(applet.privileges, 16) if applet.privileges else 0
                entry = self._build_status_entry(aid, lifecycle=0x07, privileges=priv)
                entries += entry

            return self._make_response(entries, SW.SUCCESS)

        else:
            return bytes.fromhex(SW.INCORRECT_P1P2)

    def _build_status_entry(
        self, aid: bytes, lifecycle: int = 0x07, privileges: int = 0x00
    ) -> bytes:
        """Build GET STATUS entry.

        Args:
            aid: Application Identifier.
            lifecycle: Lifecycle state.
            privileges: Privileges byte.

        Returns:
            Status entry TLV.
        """
        # GP 2.2 format: AID length + AID + lifecycle + privileges
        return bytes([len(aid)]) + aid + bytes([lifecycle, privileges])

    def _handle_initialize_update(self, apdu: ParsedAPDU) -> bytes:
        """Handle INITIALIZE UPDATE command (INS=50).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # Host challenge is in data
        if len(apdu.data) != 8:
            return bytes.fromhex(SW.WRONG_LENGTH)

        host_challenge = apdu.data
        logger.debug(f"INITIALIZE UPDATE with host challenge: {host_challenge.hex().upper()}")

        # Generate card response (simulated)
        # Format: Key diversification data (10) + Key version (1) + SC Protocol (1) +
        #         Sequence counter (2) + Card challenge (6) + Card cryptogram (8)
        import os
        key_div = bytes([0x00] * 10)
        key_version = bytes([apdu.p1])
        scp_version = bytes([0x03])  # SCP03
        seq_counter = bytes([0x00, 0x01])
        card_challenge = os.urandom(6)
        card_cryptogram = os.urandom(8)  # Simulated

        response = key_div + key_version + scp_version + seq_counter + card_challenge + card_cryptogram
        return self._make_response(response, SW.SUCCESS)

    def _handle_external_authenticate(self, apdu: ParsedAPDU) -> bytes:
        """Handle EXTERNAL AUTHENTICATE command (INS=82).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        # Accept any authentication (simulated)
        logger.debug("EXTERNAL AUTHENTICATE (simulated success)")
        self._security_level = apdu.p1  # Security level from P1
        return bytes.fromhex(SW.SUCCESS)

    def _handle_get_challenge(self, apdu: ParsedAPDU) -> bytes:
        """Handle GET CHALLENGE command (INS=84).

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        import os
        length = apdu.le or 8
        self._challenge = os.urandom(length)
        logger.debug(f"GET CHALLENGE: {self._challenge.hex().upper()}")
        return self._make_response(self._challenge, SW.SUCCESS)
