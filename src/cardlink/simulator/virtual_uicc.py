"""Virtual UICC card simulation.

This module provides a virtual UICC implementation that processes
C-APDUs and generates R-APDUs according to ISO 7816-4 and GlobalPlatform
specifications.

Implements:
- ETSI TS 102.226 Remote APDU support
- GlobalPlatform RAM over HTTP v1.1.2 (Amendment B)
- SCP '81' (PSK-TLS) key management
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Any

from .config import UICCProfile
from .models import VirtualApplet

# Import protocol layer for RAM command support
try:
    from cardlink.protocol import (
        # RAM commands and types
        InstallType,
        KeyType,
        PSKKeyType,
        PSKCipherSuite,
        CIPHER_SUITE_IDS,
        compute_psk_kcv,
        get_supported_cipher_suites,
    )
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False
    # Define fallbacks for when protocol module isn't available
    class InstallType:
        LOAD = 0x02
        INSTALL = 0x04
        MAKE_SELECTABLE = 0x08
        INSTALL_FOR_LOAD = 0x02
        INSTALL_FOR_INSTALL = 0x0C
        INSTALL_FOR_PERSONALIZATION = 0x20

    class KeyType:
        DES = 0x80
        AES = 0x88
        PSK_TLS = 0x85

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
# PSK Key Storage (GP SCP81)
# =============================================================================


@dataclass
class PSKKeyEntry:
    """PSK-TLS key entry for SCP81.

    Attributes:
        key_id: Key identifier (1-127).
        key_version: Key version number.
        key_type: Key type (0x85 for PSK-TLS).
        key_data: Raw key bytes (16 or 32 bytes for AES-128/256).
        identity: PSK identity bytes (optional).
        cipher_suites: Supported cipher suite IDs.
        kcv: Key check value (first 3 bytes of encrypted zeros).
    """
    key_id: int
    key_version: int
    key_type: int = 0x85  # PSK-TLS
    key_data: bytes = b""
    identity: bytes = b""
    cipher_suites: List[int] = field(default_factory=list)
    kcv: bytes = b""

    def compute_kcv(self) -> bytes:
        """Compute Key Check Value."""
        if PROTOCOL_AVAILABLE and self.key_data:
            return compute_psk_kcv(self.key_data)
        # Simple fallback: first 3 bytes of key
        return self.key_data[:3] if len(self.key_data) >= 3 else b"\x00\x00\x00"


@dataclass
class LoadFileEntry:
    """Executable Load File entry.

    Attributes:
        aid: Load file AID.
        lifecycle: Lifecycle state (0x01=Loaded, 0x07=Ready).
        modules: List of module AIDs contained.
        data_blocks: Loaded data blocks.
    """
    aid: bytes
    lifecycle: int = 0x01
    modules: List[bytes] = field(default_factory=list)
    data_blocks: List[bytes] = field(default_factory=list)


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
            0xF0: "SET STATUS",
            0x50: "INITIALIZE UPDATE",
            0x82: "EXTERNAL AUTHENTICATE",
            0x84: "GET CHALLENGE",
            0xD8: "PUT KEY",
        }
        return names.get(self.ins, f"INS_{self.ins:02X}")

    @property
    def is_ram_command(self) -> bool:
        """Check if this is a RAM (Remote Application Management) command."""
        ram_ins = {0xE4, 0xE6, 0xE8, 0xF2, 0xF0, 0xD8, 0xE2}
        return self.ins in ram_ins


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

        # GP SCP81 PSK-TLS key storage
        self._psk_keys: Dict[Tuple[int, int], PSKKeyEntry] = {}  # (key_id, key_version) -> entry
        self._psk_identity: Optional[bytes] = None
        self._admin_url: Optional[str] = None

        # Load file storage for RAM operations
        self._load_files: Dict[str, LoadFileEntry] = {}  # AID hex -> entry
        self._current_load_file: Optional[LoadFileEntry] = None

        # Protocol statistics
        self._ram_command_count: int = 0
        self._delete_count: int = 0
        self._install_count: int = 0
        self._load_count: int = 0
        self._put_key_count: int = 0

        # Command handlers (including RAM commands)
        self._handlers: Dict[int, Callable[[ParsedAPDU], bytes]] = {
            # Standard commands
            0xA4: self._handle_select,
            0xC0: self._handle_get_response,
            0xCA: self._handle_get_data,
            0xE2: self._handle_store_data,
            0xF2: self._handle_get_status,
            0x50: self._handle_initialize_update,
            0x82: self._handle_external_authenticate,
            0x84: self._handle_get_challenge,
            # RAM commands (GP Amendment B)
            0xE4: self._handle_delete,
            0xE6: self._handle_install,
            0xE8: self._handle_load,
            0xD8: self._handle_put_key,
            0xF0: self._handle_set_status,
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
        # Clear PSK and load file storage on reset
        self._psk_keys.clear()
        self._psk_identity = None
        self._admin_url = None
        self._load_files.clear()
        self._current_load_file = None
        # Reset counters
        self._ram_command_count = 0
        self._delete_count = 0
        self._install_count = 0
        self._load_count = 0
        self._put_key_count = 0
        logger.debug("UICC state reset (including PSK keys and load files)")

    @property
    def psk_keys(self) -> Dict[Tuple[int, int], PSKKeyEntry]:
        """Get all stored PSK keys."""
        return self._psk_keys

    @property
    def psk_identity(self) -> Optional[bytes]:
        """Get configured PSK identity."""
        return self._psk_identity

    @property
    def admin_url(self) -> Optional[str]:
        """Get configured admin server URL."""
        return self._admin_url

    @property
    def load_files(self) -> Dict[str, LoadFileEntry]:
        """Get all loaded executable load files."""
        return self._load_files

    @property
    def protocol_stats(self) -> Dict[str, Any]:
        """Get protocol operation statistics."""
        return {
            "ram_command_count": self._ram_command_count,
            "delete_count": self._delete_count,
            "install_count": self._install_count,
            "load_count": self._load_count,
            "put_key_count": self._put_key_count,
            "psk_key_count": len(self._psk_keys),
            "load_file_count": len(self._load_files),
        }

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
        length = apdu.le or 8
        self._challenge = os.urandom(length)
        logger.debug(f"GET CHALLENGE: {self._challenge.hex().upper()}")
        return self._make_response(self._challenge, SW.SUCCESS)

    # =========================================================================
    # RAM Command Handlers (GP Amendment B / ETSI TS 102.226)
    # =========================================================================

    def _handle_delete(self, apdu: ParsedAPDU) -> bytes:
        """Handle DELETE command (INS=E4).

        Deletes an application or executable load file.

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        self._ram_command_count += 1
        self._delete_count += 1

        # Parse delete data - Tag 4F (AID to delete)
        if len(apdu.data) < 3:
            return bytes.fromhex(SW.WRONG_LENGTH)

        # Simple TLV parsing for AID
        tag = apdu.data[0]
        if tag != 0x4F:
            logger.warning(f"DELETE: Expected tag 4F, got {tag:02X}")
            return bytes.fromhex(SW.WRONG_DATA)

        aid_len = apdu.data[1]
        if len(apdu.data) < 2 + aid_len:
            return bytes.fromhex(SW.WRONG_LENGTH)

        aid = apdu.data[2:2 + aid_len]
        aid_hex = aid.hex().upper()

        logger.info(f"DELETE: Deleting AID {aid_hex}")

        # Check if it's a load file
        if aid_hex in self._load_files:
            del self._load_files[aid_hex]
            logger.debug(f"DELETE: Removed load file {aid_hex}")
            return bytes.fromhex(SW.SUCCESS)

        # Check if it's an applet in profile
        for i, applet in enumerate(self.profile.applets):
            if applet.aid.upper() == aid_hex:
                # Remove from profile (simulated)
                logger.debug(f"DELETE: Removed applet {applet.name}")
                return bytes.fromhex(SW.SUCCESS)

        # Not found but still return success (simulating card behavior)
        logger.debug(f"DELETE: AID {aid_hex} not found, returning success anyway")
        return bytes.fromhex(SW.SUCCESS)

    def _handle_install(self, apdu: ParsedAPDU) -> bytes:
        """Handle INSTALL command (INS=E6).

        Supports INSTALL [for load], INSTALL [for install], and
        INSTALL [for make selectable].

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        self._ram_command_count += 1
        self._install_count += 1

        # P1 determines install type
        install_type = apdu.p1

        if install_type == 0x02:
            # INSTALL [for load]
            return self._handle_install_for_load(apdu)
        elif install_type in (0x04, 0x0C):
            # INSTALL [for install] or [for install and make selectable]
            return self._handle_install_for_install(apdu)
        elif install_type == 0x08:
            # INSTALL [for make selectable]
            return self._handle_install_for_make_selectable(apdu)
        elif install_type == 0x20:
            # INSTALL [for personalization]
            return self._handle_install_for_personalization(apdu)
        else:
            logger.warning(f"INSTALL: Unsupported install type P1={install_type:02X}")
            return bytes.fromhex(SW.INCORRECT_P1P2)

    def _handle_install_for_load(self, apdu: ParsedAPDU) -> bytes:
        """Handle INSTALL [for load] command."""
        # Parse load file AID and security domain AID from data
        if len(apdu.data) < 2:
            return bytes.fromhex(SW.WRONG_LENGTH)

        offset = 0
        # Load file AID
        lf_aid_len = apdu.data[offset]
        offset += 1
        if offset + lf_aid_len > len(apdu.data):
            return bytes.fromhex(SW.WRONG_LENGTH)
        lf_aid = apdu.data[offset:offset + lf_aid_len]
        offset += lf_aid_len

        lf_aid_hex = lf_aid.hex().upper()
        logger.info(f"INSTALL [for load]: Load file AID = {lf_aid_hex}")

        # Create new load file entry
        self._current_load_file = LoadFileEntry(aid=lf_aid, lifecycle=0x01)
        self._load_files[lf_aid_hex] = self._current_load_file

        return bytes.fromhex(SW.SUCCESS)

    def _handle_install_for_install(self, apdu: ParsedAPDU) -> bytes:
        """Handle INSTALL [for install] command."""
        if len(apdu.data) < 6:
            return bytes.fromhex(SW.WRONG_LENGTH)

        offset = 0
        # Executable load file AID
        elf_aid_len = apdu.data[offset]
        offset += 1
        elf_aid = apdu.data[offset:offset + elf_aid_len] if elf_aid_len > 0 else b""
        offset += elf_aid_len

        # Executable module AID
        em_aid_len = apdu.data[offset]
        offset += 1
        em_aid = apdu.data[offset:offset + em_aid_len] if em_aid_len > 0 else b""
        offset += em_aid_len

        # Application AID
        app_aid_len = apdu.data[offset]
        offset += 1
        app_aid = apdu.data[offset:offset + app_aid_len] if app_aid_len > 0 else b""
        offset += app_aid_len

        app_aid_hex = app_aid.hex().upper() if app_aid else "N/A"
        logger.info(f"INSTALL [for install]: Application AID = {app_aid_hex}")

        # Simulated success - applet is now installed
        return bytes.fromhex(SW.SUCCESS)

    def _handle_install_for_make_selectable(self, apdu: ParsedAPDU) -> bytes:
        """Handle INSTALL [for make selectable] command."""
        logger.info("INSTALL [for make selectable]")
        return bytes.fromhex(SW.SUCCESS)

    def _handle_install_for_personalization(self, apdu: ParsedAPDU) -> bytes:
        """Handle INSTALL [for personalization] command."""
        logger.info("INSTALL [for personalization]")
        return bytes.fromhex(SW.SUCCESS)

    def _handle_load(self, apdu: ParsedAPDU) -> bytes:
        """Handle LOAD command (INS=E8).

        Receives executable load file data blocks.

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        self._ram_command_count += 1
        self._load_count += 1

        # P1 indicates block number (P1 & 0x80 = last block)
        is_last_block = (apdu.p1 & 0x80) != 0
        block_number = apdu.p1 & 0x7F

        logger.debug(f"LOAD: Block {block_number}, last={is_last_block}, size={len(apdu.data)}")

        # Store block in current load file
        if self._current_load_file:
            self._current_load_file.data_blocks.append(apdu.data)
            if is_last_block:
                self._current_load_file.lifecycle = 0x01  # Loaded
                total_size = sum(len(b) for b in self._current_load_file.data_blocks)
                logger.info(
                    f"LOAD: Complete - {len(self._current_load_file.data_blocks)} blocks, "
                    f"{total_size} bytes total"
                )
        else:
            logger.warning("LOAD: No current load file (missing INSTALL [for load])")

        return bytes.fromhex(SW.SUCCESS)

    def _handle_put_key(self, apdu: ParsedAPDU) -> bytes:
        """Handle PUT KEY command (INS=D8).

        Stores or updates cryptographic keys, including PSK-TLS keys for SCP81.

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        self._ram_command_count += 1
        self._put_key_count += 1

        # P1 = Key version number (or 0 for new key)
        # P2 = Key identifier (bits 0-6) + Key type info (bit 7)
        key_version = apdu.p1
        key_id = apdu.p2 & 0x7F
        multiple_keys = (apdu.p2 & 0x80) != 0

        logger.info(f"PUT KEY: version={key_version}, id={key_id}, multiple={multiple_keys}")

        if len(apdu.data) < 3:
            return bytes.fromhex(SW.WRONG_LENGTH)

        # Parse key data - format: key_version | key_id | key_data_TLV...
        offset = 0

        # New key version number
        new_key_version = apdu.data[offset]
        offset += 1

        # Parse key components (simplified)
        while offset < len(apdu.data):
            if offset + 2 > len(apdu.data):
                break

            # Key type tag (A8 = key data)
            tag = apdu.data[offset]
            offset += 1

            if tag == 0xA8:  # Key data
                key_len = apdu.data[offset]
                offset += 1

                if offset + key_len > len(apdu.data):
                    break

                key_data_block = apdu.data[offset:offset + key_len]
                offset += key_len

                # Parse key type and value
                if len(key_data_block) >= 2:
                    key_type = key_data_block[0]
                    key_value_len = key_data_block[1]
                    key_value = key_data_block[2:2 + key_value_len] if len(key_data_block) >= 2 + key_value_len else b""

                    # Check if this is a PSK-TLS key (type 0x85)
                    if key_type == 0x85:
                        logger.info(f"PUT KEY: Storing PSK-TLS key (id={key_id}, version={new_key_version})")

                        entry = PSKKeyEntry(
                            key_id=key_id,
                            key_version=new_key_version,
                            key_type=key_type,
                            key_data=key_value,
                        )
                        entry.kcv = entry.compute_kcv()
                        self._psk_keys[(key_id, new_key_version)] = entry
                    else:
                        logger.debug(f"PUT KEY: Storing key type {key_type:02X}")

        # Return KCV in response (optional)
        return bytes.fromhex(SW.SUCCESS)

    def _handle_set_status(self, apdu: ParsedAPDU) -> bytes:
        """Handle SET STATUS command (INS=F0).

        Changes the lifecycle state of the card, security domain, or application.

        Args:
            apdu: Parsed APDU.

        Returns:
            R-APDU response.
        """
        self._ram_command_count += 1

        # P1 = Status type
        # P2 = New lifecycle state
        status_type = apdu.p1
        new_state = apdu.p2

        logger.info(f"SET STATUS: type={status_type:02X}, new_state={new_state:02X}")

        # Simulated success
        return bytes.fromhex(SW.SUCCESS)

    # =========================================================================
    # PSK Key Management Methods
    # =========================================================================

    def add_psk_key(
        self,
        key_id: int,
        key_version: int,
        key_data: bytes,
        identity: Optional[bytes] = None,
        cipher_suites: Optional[List[int]] = None,
    ) -> PSKKeyEntry:
        """Add or update a PSK-TLS key.

        Args:
            key_id: Key identifier (1-127).
            key_version: Key version number.
            key_data: Raw PSK key bytes.
            identity: Optional PSK identity.
            cipher_suites: Optional list of supported cipher suite IDs.

        Returns:
            The created PSKKeyEntry.
        """
        entry = PSKKeyEntry(
            key_id=key_id,
            key_version=key_version,
            key_type=0x85,  # PSK-TLS
            key_data=key_data,
            identity=identity or b"",
            cipher_suites=cipher_suites or [],
        )
        entry.kcv = entry.compute_kcv()
        self._psk_keys[(key_id, key_version)] = entry

        if identity:
            self._psk_identity = identity

        logger.info(f"Added PSK key: id={key_id}, version={key_version}, kcv={entry.kcv.hex().upper()}")
        return entry

    def get_psk_key(self, key_id: int, key_version: int) -> Optional[PSKKeyEntry]:
        """Get a PSK key by ID and version.

        Args:
            key_id: Key identifier.
            key_version: Key version number.

        Returns:
            PSKKeyEntry if found, None otherwise.
        """
        return self._psk_keys.get((key_id, key_version))

    def set_admin_url(self, url: str) -> None:
        """Set the HTTP Admin server URL.

        Args:
            url: Admin server URL (e.g., "https://admin.example.com:8443/admin").
        """
        self._admin_url = url
        logger.info(f"Set admin URL: {url}")

    def set_psk_identity(self, identity: bytes) -> None:
        """Set the PSK identity.

        Args:
            identity: PSK identity bytes.
        """
        self._psk_identity = identity
        logger.info(f"Set PSK identity: {identity.hex().upper()}")
