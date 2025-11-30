"""Data models for Phone Controller.

This module defines all data classes and enumerations used throughout
the phone controller module for Android device management via ADB.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enumerations
# =============================================================================


class DeviceState(Enum):
    """ADB device connection states."""

    DEVICE = "device"  # Normal connected state
    OFFLINE = "offline"  # Device is offline
    UNAUTHORIZED = "unauthorized"  # USB debugging not authorized
    RECOVERY = "recovery"  # Device in recovery mode
    SIDELOAD = "sideload"  # Device in sideload mode
    BOOTLOADER = "bootloader"  # Device in bootloader/fastboot
    DISCONNECTED = "disconnected"  # Device not connected
    NO_PERMISSIONS = "no permissions"  # Insufficient permissions


class SIMStatus(Enum):
    """SIM card status values."""

    ABSENT = "ABSENT"
    PIN_REQUIRED = "PIN_REQUIRED"
    PUK_REQUIRED = "PUK_REQUIRED"
    NETWORK_LOCKED = "NETWORK_LOCKED"
    READY = "READY"
    NOT_READY = "NOT_READY"
    PERM_DISABLED = "PERM_DISABLED"
    CARD_IO_ERROR = "CARD_IO_ERROR"
    CARD_RESTRICTED = "CARD_RESTRICTED"
    LOADED = "LOADED"
    UNKNOWN = "UNKNOWN"


class NetworkType(Enum):
    """Mobile network types."""

    UNKNOWN = "UNKNOWN"
    GPRS = "GPRS"
    EDGE = "EDGE"
    UMTS = "UMTS"
    CDMA = "CDMA"
    EVDO_0 = "EVDO_0"
    EVDO_A = "EVDO_A"
    RTT = "1xRTT"
    HSDPA = "HSDPA"
    HSUPA = "HSUPA"
    HSPA = "HSPA"
    IDEN = "IDEN"
    EVDO_B = "EVDO_B"
    LTE = "LTE"
    EHRPD = "EHRPD"
    HSPAP = "HSPAP"
    GSM = "GSM"
    TD_SCDMA = "TD_SCDMA"
    IWLAN = "IWLAN"
    LTE_CA = "LTE_CA"
    NR = "NR"  # 5G NR


class DataConnectionState(Enum):
    """Mobile data connection states."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    SUSPENDED = "SUSPENDED"
    UNKNOWN = "UNKNOWN"


class BIPEventType(Enum):
    """Bearer Independent Protocol event types."""

    OPEN_CHANNEL = "OPEN_CHANNEL"
    CLOSE_CHANNEL = "CLOSE_CHANNEL"
    SEND_DATA = "SEND_DATA"
    RECEIVE_DATA = "RECEIVE_DATA"
    GET_CHANNEL_STATUS = "GET_CHANNEL_STATUS"
    DATA_AVAILABLE = "DATA_AVAILABLE"
    CHANNEL_STATUS = "CHANNEL_STATUS"
    UNKNOWN = "UNKNOWN"


class ATResult(Enum):
    """AT command result codes."""

    OK = "OK"
    ERROR = "ERROR"
    CME_ERROR = "+CME ERROR"
    CMS_ERROR = "+CMS ERROR"
    TIMEOUT = "TIMEOUT"
    NO_RESPONSE = "NO_RESPONSE"
    UNAVAILABLE = "UNAVAILABLE"


class ATMethod(Enum):
    """Methods for sending AT commands to Android devices."""

    SERVICE_CALL = "service_call"  # Via service call phone
    DIALER_CODE = "dialer_code"  # Via dialer special codes
    DEVICE_NODE = "device_node"  # Direct to /dev/smd* or similar
    RIL_REQUEST = "ril_request"  # Via RIL daemon
    UNAVAILABLE = "unavailable"


# =============================================================================
# Device Information Models
# =============================================================================


@dataclass
class DeviceProfile:
    """Device hardware and software information."""

    serial: str  # ADB serial number
    model: str = ""  # e.g., "Pixel 6"
    manufacturer: str = ""  # e.g., "Google"
    brand: str = ""  # e.g., "google"
    device: str = ""  # e.g., "oriole"
    product: str = ""  # e.g., "oriole"
    android_version: str = ""  # e.g., "14"
    api_level: int = 0  # e.g., 34
    build_number: str = ""  # e.g., "UP1A.231105.001"
    build_fingerprint: str = ""  # Full build fingerprint
    kernel_version: str = ""  # Kernel version
    baseband_version: str = ""  # Modem/baseband firmware
    security_patch: str = ""  # Security patch level date
    imei: str = ""  # IMEI (may require permissions)
    imei2: str = ""  # Secondary IMEI for dual-SIM
    hardware: str = ""  # Hardware name
    board: str = ""  # Board name
    abi: str = ""  # CPU ABI (e.g., "arm64-v8a")
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "serial": self.serial,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "brand": self.brand,
            "device": self.device,
            "product": self.product,
            "android_version": self.android_version,
            "api_level": self.api_level,
            "build_number": self.build_number,
            "build_fingerprint": self.build_fingerprint,
            "kernel_version": self.kernel_version,
            "baseband_version": self.baseband_version,
            "security_patch": self.security_patch,
            "imei": self.imei,
            "imei2": self.imei2,
            "hardware": self.hardware,
            "board": self.board,
            "abi": self.abi,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SIMProfile:
    """UICC/SIM card information."""

    slot: int = 0  # SIM slot index (0 or 1)
    status: SIMStatus = SIMStatus.UNKNOWN
    iccid: str = ""  # Integrated Circuit Card ID
    imsi: str = ""  # International Mobile Subscriber Identity
    msisdn: str = ""  # Phone number
    spn: str = ""  # Service Provider Name
    mcc: str = ""  # Mobile Country Code
    mnc: str = ""  # Mobile Network Code
    operator_name: str = ""  # Network operator name
    is_embedded: bool = False  # Is this an eSIM
    is_active: bool = False  # Is this the active SIM
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "slot": self.slot,
            "status": self.status.value,
            "iccid": self.iccid,
            "imsi": self.imsi,
            "msisdn": self.msisdn,
            "spn": self.spn,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "operator_name": self.operator_name,
            "is_embedded": self.is_embedded,
            "is_active": self.is_active,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class NetworkProfile:
    """Network connection information."""

    operator_name: str = ""  # Current network operator
    network_type: NetworkType = NetworkType.UNKNOWN
    data_state: DataConnectionState = DataConnectionState.UNKNOWN
    data_roaming: bool = False
    signal_strength_dbm: int = -999  # Signal strength in dBm
    signal_level: int = 0  # Signal level 0-4
    is_wifi_connected: bool = False
    wifi_ssid: str = ""  # Connected WiFi SSID
    wifi_ip: str = ""  # WiFi IP address
    mobile_ip: str = ""  # Mobile data IP address
    apn_name: str = ""  # Current APN name
    apn_type: str = ""  # APN type
    mcc: str = ""  # Current network MCC
    mnc: str = ""  # Current network MNC
    cell_id: str = ""  # Current cell ID
    lac: str = ""  # Location Area Code
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "operator_name": self.operator_name,
            "network_type": self.network_type.value,
            "data_state": self.data_state.value,
            "data_roaming": self.data_roaming,
            "signal_strength_dbm": self.signal_strength_dbm,
            "signal_level": self.signal_level,
            "is_wifi_connected": self.is_wifi_connected,
            "wifi_ssid": self.wifi_ssid,
            "wifi_ip": self.wifi_ip,
            "mobile_ip": self.mobile_ip,
            "apn_name": self.apn_name,
            "apn_type": self.apn_type,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "cell_id": self.cell_id,
            "lac": self.lac,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FullProfile:
    """Complete device profile combining device, SIM, and network info."""

    device: DeviceProfile
    sim_profiles: List[SIMProfile] = field(default_factory=list)
    network: Optional[NetworkProfile] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "device": self.device.to_dict(),
            "sim_profiles": [sim.to_dict() for sim in self.sim_profiles],
            "network": self.network.to_dict() if self.network else None,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# AT Command Models
# =============================================================================


@dataclass
class ATResponse:
    """Response from an AT command."""

    result: ATResult
    response_lines: List[str] = field(default_factory=list)
    error_code: Optional[int] = None
    error_message: str = ""
    raw_response: str = ""
    duration_ms: float = 0.0

    @property
    def is_ok(self) -> bool:
        """Check if command succeeded."""
        return self.result == ATResult.OK

    @property
    def data(self) -> str:
        """Get response data (excluding result code)."""
        return "\n".join(self.response_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result": self.result.value,
            "response_lines": self.response_lines,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "raw_response": self.raw_response,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# BIP Event Models
# =============================================================================


@dataclass
class BIPEvent:
    """Bearer Independent Protocol event from logcat."""

    event_type: BIPEventType
    timestamp: datetime
    channel_id: Optional[int] = None
    bearer_type: str = ""  # "GPRS", "DEFAULT", etc.
    address: str = ""  # Server address for OPEN_CHANNEL
    port: int = 0  # Server port
    data_length: int = 0  # Data length for SEND/RECEIVE
    data: bytes = b""  # Actual data (if captured)
    status: str = ""  # Status or result
    raw_log: str = ""  # Original log line
    session_id: str = ""  # For correlation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "channel_id": self.channel_id,
            "bearer_type": self.bearer_type,
            "address": self.address,
            "port": self.port,
            "data_length": self.data_length,
            "data": self.data.hex() if self.data else "",
            "status": self.status,
            "raw_log": self.raw_log,
            "session_id": self.session_id,
        }


# =============================================================================
# Logcat Models
# =============================================================================


@dataclass
class LogcatEntry:
    """Parsed logcat entry."""

    timestamp: datetime
    pid: int
    tid: int
    level: str  # V, D, I, W, E, F
    tag: str
    message: str
    raw_line: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pid": self.pid,
            "tid": self.tid,
            "level": self.level,
            "tag": self.tag,
            "message": self.message,
        }


# =============================================================================
# Device Info Models
# =============================================================================


@dataclass
class ADBDevice:
    """Information about a connected ADB device."""

    serial: str
    state: DeviceState
    product: str = ""
    model: str = ""
    device: str = ""
    transport_id: int = 0
    usb: str = ""  # USB port path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "serial": self.serial,
            "state": self.state.value,
            "product": self.product,
            "model": self.model,
            "device": self.device,
            "transport_id": self.transport_id,
            "usb": self.usb,
        }


# =============================================================================
# SMS/Trigger Models
# =============================================================================


@dataclass
class TriggerTemplate:
    """Template for OTA trigger SMS-PP message."""

    name: str
    description: str
    pdu_template: str  # PDU template with placeholders
    parameters: Dict[str, str] = field(default_factory=dict)  # Placeholder descriptions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "pdu_template": self.pdu_template,
            "parameters": self.parameters,
        }


@dataclass
class TriggerResult:
    """Result of sending an SMS-PP trigger."""

    success: bool
    message_reference: int = 0  # Reference number from +CMGS response
    pdu_sent: str = ""  # The PDU that was sent
    error_message: str = ""
    method_used: str = ""  # How the trigger was sent
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message_reference": self.message_reference,
            "pdu_sent": self.pdu_sent,
            "error_message": self.error_message,
            "method_used": self.method_used,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# APN Configuration Model
# =============================================================================


@dataclass
class APNConfig:
    """APN configuration settings."""

    name: str  # APN name/label
    apn: str  # APN string
    mcc: str = ""  # Mobile Country Code
    mnc: str = ""  # Mobile Network Code
    user: str = ""  # Username for authentication
    password: str = ""  # Password for authentication
    auth_type: int = 0  # 0=None, 1=PAP, 2=CHAP, 3=PAP or CHAP
    proxy: str = ""  # Proxy address
    port: str = ""  # Proxy port
    mmsc: str = ""  # MMS Center
    mmsproxy: str = ""  # MMS Proxy
    mmsport: str = ""  # MMS Port
    type: str = "default,supl"  # APN type
    protocol: str = "IPV4V6"  # IP protocol
    roaming_protocol: str = "IPV4V6"  # Roaming protocol

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "apn": self.apn,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "user": self.user,
            "password": self.password,
            "auth_type": self.auth_type,
            "proxy": self.proxy,
            "port": self.port,
            "mmsc": self.mmsc,
            "mmsproxy": self.mmsproxy,
            "mmsport": self.mmsport,
            "type": self.type,
            "protocol": self.protocol,
            "roaming_protocol": self.roaming_protocol,
        }
