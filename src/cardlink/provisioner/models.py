"""Data models for UICC Provisioner.

This module defines all data classes and enumerations used throughout
the provisioner module for smart card operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional


# =============================================================================
# Protocol and Card Enumerations
# =============================================================================


class Protocol(IntEnum):
    """Smart card communication protocols."""

    T0 = 1  # Character-oriented protocol
    T1 = 2  # Block-oriented protocol
    RAW = 4  # Raw protocol
    T15 = 8  # T=15 for PPS negotiation
    ANY = T0 | T1  # Accept any protocol


class Convention(Enum):
    """ATR convention types."""

    DIRECT = "direct"  # TS = 3B
    INVERSE = "inverse"  # TS = 3F


class CardType(Enum):
    """Smart card types detected from ATR."""

    UNKNOWN = "unknown"
    UICC = "uicc"
    USIM = "usim"
    ISIM = "isim"
    EUICC = "euicc"
    SIM = "sim"  # Legacy 2G SIM
    JAVACARD = "javacard"


class LifeCycleState(IntEnum):
    """GlobalPlatform application lifecycle states."""

    UNKNOWN = 0x00  # Unknown state

    OP_READY = 0x01  # OP_READY (ISD only)
    INITIALIZED = 0x07  # INITIALIZED (ISD only)
    SECURED = 0x0F  # SECURED (ISD only)
    CARD_LOCKED = 0x7F  # CARD_LOCKED (ISD only)
    TERMINATED = 0xFF  # TERMINATED (ISD only)

    # Application states
    INSTALLED = 0x03  # Installed
    SELECTABLE = 0x07  # Selectable
    PERSONALIZED = 0x0F  # Application specific
    BLOCKED = 0x83  # Blocked
    LOCKED = 0x8F  # Locked

    @classmethod
    def from_byte(cls, value: int) -> "LifeCycleState":
        """Parse lifecycle state from byte value."""
        try:
            return cls(value)
        except ValueError:
            # Return based on common patterns
            if value & 0x80:
                return cls.BLOCKED
            elif value & 0x0F == 0x0F:
                return cls.PERSONALIZED
            elif value & 0x07 == 0x07:
                return cls.SELECTABLE
            elif value & 0x03 == 0x03:
                return cls.INSTALLED
            return cls.UNKNOWN


class Privilege(Enum):
    """GlobalPlatform application privileges."""

    # First byte privileges (byte 0)
    SECURITY_DOMAIN = "security_domain"  # 0x80
    DAP_VERIFICATION = "dap_verification"  # 0x40
    DELEGATED_MANAGEMENT = "delegated_management"  # 0x20
    CARD_LOCK = "card_lock"  # 0x10
    CARD_TERMINATE = "card_terminate"  # 0x08
    CARD_RESET = "card_reset"  # 0x04
    CVM_MANAGEMENT = "cvm_management"  # 0x02
    MANDATED_DAP_VERIFICATION = "mandated_dap_verification"  # 0x01

    # Second byte privileges (byte 1)
    TRUSTED_PATH = "trusted_path"  # 0x80
    AUTHORIZED_MANAGEMENT = "authorized_management"  # 0x40
    TOKEN_VERIFICATION = "token_verification"  # 0x20
    GLOBAL_DELETE = "global_delete"  # 0x10
    GLOBAL_LOCK = "global_lock"  # 0x08
    GLOBAL_REGISTRY = "global_registry"  # 0x04
    FINAL_APPLICATION = "final_application"  # 0x02
    RECEIPT_GENERATION = "receipt_generation"  # 0x01

    # Third byte privileges (byte 2)
    CIPHERED_LOAD_FILE_DATA_BLOCK = "ciphered_load_file_data_block"  # 0x10
    CONTACTLESS_ACTIVATION = "contactless_activation"  # 0x08
    CONTACTLESS_SELF_ACTIVATION = "contactless_self_activation"  # 0x04


# =============================================================================
# Reader and Card Information
# =============================================================================


@dataclass
class ReaderInfo:
    """Information about a PC/SC reader.

    Attributes:
        name: Reader name as reported by PC/SC.
        index: Reader index in the list.
        has_card: Whether a card is present.
        atr: ATR of the inserted card (if present).
    """

    name: str
    index: int
    has_card: bool = False
    atr: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "index": self.index,
            "has_card": self.has_card,
            "atr": self.atr.hex() if self.atr else None,
        }


@dataclass
class CardInfo:
    """Information about an inserted smart card.

    Attributes:
        atr: Answer-To-Reset bytes.
        atr_info: Parsed ATR information (optional).
        protocol: Communication protocol (T=0 or T=1).
        reader_name: Name of the reader the card is in.
        card_type: Detected card type.
        convention: ATR convention (direct/inverse).
        historical_bytes: Historical bytes from ATR.
    """

    atr: bytes
    atr_info: Optional["ATRInfo"] = None
    protocol: Protocol = Protocol.T0
    reader_name: str = ""
    card_type: CardType = CardType.UNKNOWN
    convention: Convention = Convention.DIRECT
    historical_bytes: bytes = b""

    @property
    def atr_hex(self) -> str:
        """Get ATR as hex string."""
        return self.atr.hex().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "atr": self.atr.hex(),
            "atr_hex": self.atr_hex,
            "protocol": self.protocol.name,
            "reader_name": self.reader_name,
            "card_type": self.card_type.value,
            "convention": self.convention.value,
            "historical_bytes": self.historical_bytes.hex(),
        }


# =============================================================================
# ATR Components
# =============================================================================


@dataclass
class ATRInfo:
    """Parsed ATR (Answer-To-Reset) information.

    Attributes:
        raw: Raw ATR bytes.
        ts: Initial character (3B=direct, 3F=inverse).
        t0: Format byte.
        ta: TA interface bytes.
        tb: TB interface bytes.
        tc: TC interface bytes.
        td: TD interface bytes.
        historical_bytes: Historical bytes.
        tck: Check byte (if present).
        protocols: Supported protocols.
        convention: Direct or inverse convention.
        card_type: Detected card type.
    """

    raw: bytes
    ts: int = 0
    t0: int = 0
    ta: List[int] = field(default_factory=list)
    tb: List[int] = field(default_factory=list)
    tc: List[int] = field(default_factory=list)
    td: List[int] = field(default_factory=list)
    historical_bytes: bytes = b""
    tck: Optional[int] = None
    protocols: List[int] = field(default_factory=list)
    convention: Convention = Convention.DIRECT
    card_type: CardType = CardType.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "raw": self.raw.hex(),
            "ts": f"{self.ts:02X}",
            "t0": f"{self.t0:02X}",
            "ta": [f"{b:02X}" for b in self.ta],
            "tb": [f"{b:02X}" for b in self.tb],
            "tc": [f"{b:02X}" for b in self.tc],
            "td": [f"{b:02X}" for b in self.td],
            "historical_bytes": self.historical_bytes.hex(),
            "tck": f"{self.tck:02X}" if self.tck is not None else None,
            "protocols": self.protocols,
            "convention": self.convention.value,
            "card_type": self.card_type.value,
        }


# =============================================================================
# APDU Models
# =============================================================================


class INS(IntEnum):
    """Common ISO 7816 and GlobalPlatform instruction bytes."""

    # ISO 7816-4
    SELECT = 0xA4
    READ_BINARY = 0xB0
    READ_RECORD = 0xB2
    GET_RESPONSE = 0xC0
    UPDATE_BINARY = 0xD6
    UPDATE_RECORD = 0xDC
    VERIFY = 0x20
    CHANGE_PIN = 0x24
    UNBLOCK_PIN = 0x2C
    GET_DATA = 0xCA
    PUT_DATA = 0xDA
    INTERNAL_AUTH = 0x88
    EXTERNAL_AUTH = 0x82
    MANAGE_CHANNEL = 0x70

    # GlobalPlatform
    INITIALIZE_UPDATE = 0x50
    GET_STATUS = 0xF2
    SET_STATUS = 0xF0
    INSTALL = 0xE6
    LOAD = 0xE8
    DELETE = 0xE4
    PUT_KEY = 0xD8
    STORE_DATA = 0xE2


@dataclass
class APDUCommand:
    """APDU command structure.

    Attributes:
        cla: Class byte.
        ins: Instruction byte.
        p1: Parameter 1.
        p2: Parameter 2.
        data: Command data (Lc field will be computed).
        le: Expected response length (0 = 256, None = no Le).
    """

    cla: int
    ins: int
    p1: int
    p2: int
    data: bytes = b""
    le: Optional[int] = None

    def to_bytes(self) -> bytes:
        """Convert to byte array for transmission.

        Returns:
            APDU as bytes in correct format.
        """
        apdu = bytes([self.cla, self.ins, self.p1, self.p2])

        if self.data:
            # Case 3 or 4: has data
            apdu += bytes([len(self.data)]) + self.data

        if self.le is not None:
            # Case 2 or 4: expects response
            apdu += bytes([self.le])

        return apdu

    def to_hex(self) -> str:
        """Convert to hex string."""
        return self.to_bytes().hex().upper()

    @classmethod
    def from_bytes(cls, data: bytes) -> "APDUCommand":
        """Parse APDU from bytes.

        Args:
            data: APDU bytes (minimum 4 bytes).

        Returns:
            Parsed APDUCommand.
        """
        if len(data) < 4:
            raise ValueError("APDU too short (minimum 4 bytes)")

        cla, ins, p1, p2 = data[0], data[1], data[2], data[3]

        if len(data) == 4:
            # Case 1: no data, no Le
            return cls(cla, ins, p1, p2)

        if len(data) == 5:
            # Case 2: Le only
            return cls(cla, ins, p1, p2, le=data[4])

        # Has Lc
        lc = data[4]
        if len(data) == 5 + lc:
            # Case 3: data only
            return cls(cla, ins, p1, p2, data=data[5 : 5 + lc])

        if len(data) == 6 + lc:
            # Case 4: data and Le
            return cls(cla, ins, p1, p2, data=data[5 : 5 + lc], le=data[5 + lc])

        raise ValueError(f"Invalid APDU length: {len(data)}")

    @classmethod
    def from_hex(cls, hex_str: str) -> "APDUCommand":
        """Parse APDU from hex string."""
        return cls.from_bytes(bytes.fromhex(hex_str.replace(" ", "")))


@dataclass
class APDUResponse:
    """APDU response structure.

    Attributes:
        data: Response data.
        sw1: Status word byte 1.
        sw2: Status word byte 2.
        duration_ms: Command duration in milliseconds.
    """

    data: bytes
    sw1: int
    sw2: int
    duration_ms: float = 0.0

    @property
    def sw(self) -> int:
        """Get status word as 16-bit integer."""
        return (self.sw1 << 8) | self.sw2

    @property
    def is_success(self) -> bool:
        """Check if command succeeded (SW=9000)."""
        return self.sw == 0x9000

    @property
    def is_ok(self) -> bool:
        """Alias for is_success."""
        return self.is_success

    @property
    def needs_get_response(self) -> bool:
        """Check if GET RESPONSE is needed (SW=61xx)."""
        return self.sw1 == 0x61

    @property
    def wrong_length(self) -> bool:
        """Check if wrong Le was provided (SW=6Cxx)."""
        return self.sw1 == 0x6C

    def to_hex(self) -> str:
        """Convert response to hex string."""
        return (self.data + bytes([self.sw1, self.sw2])).hex().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data": self.data.hex(),
            "sw": f"{self.sw:04X}",
            "sw1": f"{self.sw1:02X}",
            "sw2": f"{self.sw2:02X}",
            "duration_ms": self.duration_ms,
            "is_success": self.is_success,
        }


# =============================================================================
# Security Domain Models
# =============================================================================


@dataclass
class SecurityDomainInfo:
    """Information about a GlobalPlatform Security Domain.

    Attributes:
        aid: Application identifier.
        lifecycle_state: Current lifecycle state.
        privileges: Security domain privileges.
        executable_load_file_aid: Associated executable load file AID.
        executable_module_aid: Associated executable module AID.
    """

    aid: bytes
    lifecycle_state: LifeCycleState
    privileges: List[Any] = field(default_factory=list)
    executable_load_file_aid: Optional[bytes] = None
    executable_module_aid: Optional[bytes] = None

    @property
    def aid_hex(self) -> str:
        """Get AID as hex string."""
        return self.aid.hex().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "aid": self.aid_hex,
            "lifecycle_state": self.lifecycle_state.name,
            "privileges": [p.name if hasattr(p, 'name') else str(p) for p in self.privileges],
            "executable_load_file_aid": self.executable_load_file_aid.hex().upper() if self.executable_load_file_aid else None,
            "executable_module_aid": self.executable_module_aid.hex().upper() if self.executable_module_aid else None,
        }


@dataclass
class ApplicationInfo:
    """Information about a GlobalPlatform application or load file.

    Attributes:
        aid: Application identifier.
        lifecycle_state: Current lifecycle state.
        privileges: Application privileges.
        associated_sd: Associated Security Domain AID.
        module_aids: List of module AIDs (for load files).
    """

    aid: bytes
    lifecycle_state: LifeCycleState
    privileges: int = 0
    associated_sd: Optional[bytes] = None
    module_aids: List[bytes] = field(default_factory=list)

    @property
    def aid_hex(self) -> str:
        """Get AID as hex string."""
        return self.aid.hex().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "aid": self.aid_hex,
            "lifecycle_state": self.lifecycle_state.name,
            "privileges": f"{self.privileges:02X}",
            "associated_sd": self.associated_sd.hex().upper() if self.associated_sd else None,
            "module_aids": [m.hex().upper() for m in self.module_aids],
        }


# =============================================================================
# SCP Key Models
# =============================================================================


@dataclass
class SCPKeys:
    """Secure Channel Protocol keys.

    Attributes:
        enc: Encryption key (S-ENC).
        mac: MAC key (S-MAC).
        dek: Data Encryption Key (DEK/KEK).
        version: Key version number.
    """

    enc: bytes
    mac: bytes
    dek: bytes
    version: int = 0

    @classmethod
    def default_test_keys(cls) -> "SCPKeys":
        """Get default GlobalPlatform test keys.

        These are the well-known test keys used for development.
        NEVER use these in production!
        """
        default_key = bytes.fromhex("404142434445464748494A4B4C4D4E4F")
        return cls(enc=default_key, mac=default_key, dek=default_key, version=0)

    def to_dict(self, include_keys: bool = False) -> Dict[str, Any]:
        """Convert to dictionary.

        Args:
            include_keys: Include actual key values (security risk).
        """
        if include_keys:
            return {
                "enc": self.enc.hex(),
                "mac": self.mac.hex(),
                "dek": self.dek.hex(),
                "version": self.version,
            }
        return {
            "enc": "****",
            "mac": "****",
            "dek": "****",
            "version": self.version,
        }


# =============================================================================
# Configuration Models
# =============================================================================


@dataclass
class PSKConfiguration:
    """Pre-Shared Key configuration.

    Attributes:
        identity: PSK identity string.
        key: PSK key bytes.
        key_size: Key size in bytes.
    """

    identity: str
    key: bytes
    key_size: int = 16

    @classmethod
    def generate(cls, identity: str, key_size: int = 16) -> "PSKConfiguration":
        """Generate a new PSK configuration with random key.

        Args:
            identity: PSK identity.
            key_size: Key size in bytes (default 16 for 128-bit).

        Returns:
            New PSKConfiguration with random key.
        """
        import secrets

        key = secrets.token_bytes(key_size)
        return cls(identity=identity, key=key, key_size=key_size)

    @classmethod
    def from_hex(cls, identity: str, key_hex: str) -> "PSKConfiguration":
        """Create PSK configuration from hex key.

        Args:
            identity: PSK identity.
            key_hex: Key as hex string.

        Returns:
            PSKConfiguration.
        """
        key = bytes.fromhex(key_hex.replace(" ", ""))
        return cls(identity=identity, key=key, key_size=len(key))

    def to_dict(self, include_key: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "identity": self.identity,
            "key_size": self.key_size,
        }
        if include_key:
            result["key"] = self.key.hex()
        return result


@dataclass
class URLConfiguration:
    """Remote server URL configuration.

    Attributes:
        url: Full URL string.
        scheme: URL scheme (https).
        host: Server hostname.
        port: Server port.
        path: URL path.
    """

    url: str
    scheme: str = "https"
    host: str = ""
    port: int = 443
    path: str = "/"

    @classmethod
    def from_url(cls, url: str) -> "URLConfiguration":
        """Parse URL string into configuration.

        Args:
            url: URL string to parse.

        Returns:
            URLConfiguration.
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return cls(
            url=url,
            scheme=parsed.scheme or "https",
            host=parsed.hostname or "",
            port=parsed.port or (443 if parsed.scheme == "https" else 80),
            path=parsed.path or "/",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "path": self.path,
        }

    def to_tlv(self) -> bytes:
        """Encode URL to TLV format for card storage.

        Returns:
            TLV-encoded URL bytes.
        """
        from cardlink.provisioner.tlv_parser import TLVParser

        url_bytes = self.url.encode("utf-8")
        return TLVParser.build(0x80, url_bytes)


# =============================================================================
# Trigger Configuration Models
# =============================================================================


class TriggerType(Enum):
    """OTA trigger types."""

    SMS = "sms"  # SMS-PP trigger
    POLL = "poll"  # Polling trigger
    PUSH = "push"  # Server push trigger


@dataclass
class SMSTriggerConfig:
    """SMS-PP trigger configuration.

    Attributes:
        tar: Toolkit Application Reference (3 bytes).
        originating_address: SMS originating address/phone number.
        kic: Key Identifier for Ciphering.
        kid: Key Identifier for RC/CC/DS.
        counter: Security counter (5 bytes).
    """

    tar: bytes  # 3 bytes
    originating_address: str = ""
    kic: bytes = b"\x00"  # No ciphering
    kid: bytes = b"\x00"  # No redundancy check
    counter: bytes = b"\x00\x00\x00\x00\x00"  # 5 bytes

    def __post_init__(self):
        """Validate field lengths."""
        if len(self.tar) != 3:
            raise ValueError(f"TAR must be 3 bytes, got {len(self.tar)}")
        if len(self.counter) != 5:
            raise ValueError(f"Counter must be 5 bytes, got {len(self.counter)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tar": self.tar.hex(),
            "originating_address": self.originating_address,
            "kic": self.kic.hex(),
            "kid": self.kid.hex(),
            "counter": self.counter.hex(),
        }


@dataclass
class PollTriggerConfig:
    """Polling trigger configuration.

    Attributes:
        interval: Polling interval in seconds.
        enabled: Whether polling is enabled.
    """

    interval: int = 3600  # Default: 1 hour
    enabled: bool = False

    def __post_init__(self):
        """Validate interval."""
        if self.interval < 60:
            raise ValueError("Polling interval must be at least 60 seconds")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "interval": self.interval,
            "enabled": self.enabled,
        }


@dataclass
class TriggerConfiguration:
    """Complete trigger configuration.

    Attributes:
        sms_trigger: SMS-PP trigger configuration.
        poll_trigger: Polling trigger configuration.
    """

    sms_trigger: Optional[SMSTriggerConfig] = None
    poll_trigger: Optional[PollTriggerConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sms_trigger": self.sms_trigger.to_dict() if self.sms_trigger else None,
            "poll_trigger": self.poll_trigger.to_dict() if self.poll_trigger else None,
        }


# =============================================================================
# BIP Configuration Models
# =============================================================================


class BearerType(IntEnum):
    """Bearer types for BIP (Bearer Independent Protocol)."""

    CSD = 0x01  # Circuit Switched Data
    GPRS = 0x02  # GPRS/EDGE
    DEFAULT = 0x03  # Default bearer
    LOCAL_LINK = 0x04  # Local link (Bluetooth, IrDA, etc.)
    UTRAN = 0x05  # UTRAN (3G)
    EUTRAN = 0x0B  # E-UTRAN (LTE)
    WIFI = 0x0C  # WiFi (TS 102 223 Rel-12+)


@dataclass
class BIPConfiguration:
    """Bearer Independent Protocol configuration.

    Attributes:
        bearer_type: Type of bearer to use.
        apn: Access Point Name (for packet-switched bearers).
        buffer_size: Channel buffer size in bytes.
        timeout: Connection timeout in seconds.
        user_login: Optional user login for APN.
        user_password: Optional user password for APN.
    """

    bearer_type: BearerType = BearerType.DEFAULT
    apn: str = ""
    buffer_size: int = 1400  # Default MTU-friendly size
    timeout: int = 30  # Default 30 seconds
    user_login: Optional[str] = None
    user_password: Optional[str] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.buffer_size < 1 or self.buffer_size > 65535:
            raise ValueError("Buffer size must be between 1 and 65535")
        if self.timeout < 1:
            raise ValueError("Timeout must be at least 1 second")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bearer_type": self.bearer_type.name,
            "apn": self.apn,
            "buffer_size": self.buffer_size,
            "timeout": self.timeout,
            "user_login": self.user_login,
            "user_password": "***" if self.user_password else None,
        }

    def to_tlv(self) -> bytes:
        """Encode BIP configuration to TLV format.

        Returns:
            TLV-encoded BIP configuration.
        """
        from cardlink.provisioner.tlv_parser import TLVParser

        # Build TLV structure
        tlv_data = b""

        # Bearer type (Tag 0x80)
        tlv_data += TLVParser.build(0x80, bytes([self.bearer_type]))

        # APN in DNS label format (Tag 0x81)
        if self.apn:
            apn_encoded = self._encode_apn(self.apn)
            tlv_data += TLVParser.build(0x81, apn_encoded)

        # Buffer size (Tag 0x82) - 2 bytes, big-endian
        buffer_bytes = self.buffer_size.to_bytes(2, byteorder="big")
        tlv_data += TLVParser.build(0x82, buffer_bytes)

        # Timeout (Tag 0x83) - 1 byte in seconds
        timeout_byte = min(self.timeout, 255).to_bytes(1, byteorder="big")
        tlv_data += TLVParser.build(0x83, timeout_byte)

        # User login (Tag 0x84) - optional
        if self.user_login:
            login_bytes = self.user_login.encode("utf-8")
            tlv_data += TLVParser.build(0x84, login_bytes)

        # User password (Tag 0x85) - optional
        if self.user_password:
            password_bytes = self.user_password.encode("utf-8")
            tlv_data += TLVParser.build(0x85, password_bytes)

        return tlv_data

    @staticmethod
    def _encode_apn(apn: str) -> bytes:
        """Encode APN in DNS label format per RFC 1035.

        DNS label format:
        - Each label is preceded by its length byte
        - Example: "internet.example.com" -> 0x08 "internet" 0x07 "example" 0x03 "com"

        Args:
            apn: APN string (e.g., "internet.example.com").

        Returns:
            DNS label encoded bytes.
        """
        if not apn:
            return b""

        labels = apn.split(".")
        encoded = b""
        for label in labels:
            if not label or len(label) > 63:
                raise ValueError(f"Invalid APN label: {label}")
            encoded += bytes([len(label)]) + label.encode("ascii")

        return encoded

    @staticmethod
    def _decode_apn(data: bytes) -> str:
        """Decode APN from DNS label format.

        Args:
            data: DNS label encoded bytes.

        Returns:
            APN string.
        """
        if not data:
            return ""

        labels = []
        i = 0
        while i < len(data):
            length = data[i]
            if length == 0:
                break
            i += 1
            if i + length > len(data):
                raise ValueError("Invalid DNS label encoding")
            label = data[i : i + length].decode("ascii")
            labels.append(label)
            i += length

        return ".".join(labels)


@dataclass
class CardProfile:
    """Complete UICC card profile.

    Captures all configurable parameters for a card including
    identification, PSK credentials, server URLs, triggers, and BIP settings.

    This allows saving/loading complete card configurations and
    applying them to multiple cards.

    Attributes:
        iccid: Integrated Circuit Card Identifier (unique card ID)
        atr: Answer To Reset bytes from card
        psk: PSK-TLS configuration (identity and key)
        url: Admin server URL configuration
        trigger: OTA trigger configuration
        bip: Bearer Independent Protocol configuration
    """

    iccid: str
    atr: bytes
    psk: Optional[PSKConfiguration] = None
    url: Optional[str] = None
    trigger: Optional[TriggerConfiguration] = None
    bip: Optional[BIPConfiguration] = None

    def to_dict(self, include_keys: bool = False) -> dict:
        """Convert profile to dictionary for JSON export.

        Args:
            include_keys: If True, include PSK key material in export.
                         If False, only include identity.

        Returns:
            Dictionary representation of profile
        """
        profile_dict = {
            "iccid": self.iccid,
            "atr": self.atr.hex(),
        }

        if self.psk:
            profile_dict["psk"] = {
                "identity": self.psk.identity,
            }
            if include_keys:
                profile_dict["psk"]["key"] = self.psk.key.hex()

        if self.url:
            profile_dict["url"] = self.url

        if self.trigger:
            trigger_dict = {}
            if self.trigger.sms_trigger:
                trigger_dict["sms"] = {
                    "tar": self.trigger.sms_trigger.tar.hex(),
                    "originating_address": self.trigger.sms_trigger.originating_address,
                    "kic": self.trigger.sms_trigger.kic.hex(),
                    "kid": self.trigger.sms_trigger.kid.hex(),
                    "counter": self.trigger.sms_trigger.counter.hex(),
                }
            if self.trigger.poll_trigger:
                trigger_dict["poll"] = {
                    "interval": self.trigger.poll_trigger.interval,
                    "enabled": self.trigger.poll_trigger.enabled,
                }
            profile_dict["trigger"] = trigger_dict

        if self.bip:
            profile_dict["bip"] = {
                "bearer_type": self.bip.bearer_type.value,
                "apn": self.bip.apn,
                "buffer_size": self.bip.buffer_size,
                "timeout": self.bip.timeout,
            }

        return profile_dict

    @classmethod
    def from_dict(cls, data: dict) -> "CardProfile":
        """Create profile from dictionary.

        Args:
            data: Profile dictionary (from JSON)

        Returns:
            CardProfile instance
        """
        # Parse PSK if present
        psk = None
        if "psk" in data:
            psk_data = data["psk"]
            key = None
            if "key" in psk_data:
                key = bytes.fromhex(psk_data["key"])
            psk = PSKConfiguration(
                identity=psk_data["identity"],
                key=key if key else b"",  # Placeholder if key not in export
            )

        # Parse trigger if present
        trigger = None
        if "trigger" in data:
            sms_trigger = None
            poll_trigger = None

            if "sms" in data["trigger"]:
                sms_data = data["trigger"]["sms"]
                sms_trigger = SMSTriggerConfig(
                    tar=bytes.fromhex(sms_data["tar"]),
                    originating_address=sms_data.get("originating_address", ""),
                    kic=bytes.fromhex(sms_data["kic"]),
                    kid=bytes.fromhex(sms_data["kid"]),
                    counter=bytes.fromhex(sms_data["counter"]),
                )

            if "poll" in data["trigger"]:
                poll_data = data["trigger"]["poll"]
                poll_trigger = PollTriggerConfig(
                    interval=poll_data["interval"],
                    enabled=poll_data["enabled"],
                )

            trigger = TriggerConfiguration(
                sms_trigger=sms_trigger,
                poll_trigger=poll_trigger,
            )

        # Parse BIP if present
        bip = None
        if "bip" in data:
            bip_data = data["bip"]
            bip = BIPConfiguration(
                bearer_type=BearerType(bip_data["bearer_type"]),
                apn=bip_data.get("apn"),
                buffer_size=bip_data.get("buffer_size", 1500),
                timeout=bip_data.get("timeout", 30),
            )

        return cls(
            iccid=data["iccid"],
            atr=bytes.fromhex(data["atr"]),
            psk=psk,
            url=data.get("url"),
            trigger=trigger,
            bip=bip,
        )


# =============================================================================
# Event Models
# =============================================================================


@dataclass
class ProvisionerEvent:
    """Event emitted during provisioner operations.

    Attributes:
        event_type: Type of event.
        timestamp: When the event occurred.
        data: Event-specific data.
    """

    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# =============================================================================
# APDU Log Models
# =============================================================================


@dataclass
class APDULogEntry:
    """Entry in the APDU log.

    Attributes:
        timestamp: When the exchange occurred.
        direction: "command" or "response".
        data: APDU bytes.
        decoded: Human-readable decoded representation.
        duration_ms: Duration in milliseconds (for responses).
    """

    timestamp: datetime
    direction: str  # "command" or "response"
    data: bytes
    decoded: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "data": self.data.hex(),
            "decoded": self.decoded,
            "duration_ms": self.duration_ms,
        }
