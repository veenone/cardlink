"""Data models for Modem Controller.

This module defines all data classes and enumerations used throughout
the modem controller module.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enumerations
# =============================================================================


class ATResult(Enum):
    """AT command result codes."""

    OK = "OK"
    ERROR = "ERROR"
    CME_ERROR = "+CME ERROR"
    CMS_ERROR = "+CMS ERROR"
    TIMEOUT = "TIMEOUT"
    NO_RESPONSE = "NO_RESPONSE"


class RegistrationStatus(Enum):
    """Network registration status codes (from +CREG/+CEREG)."""

    NOT_REGISTERED = 0
    REGISTERED_HOME = 1
    SEARCHING = 2
    DENIED = 3
    UNKNOWN = 4
    REGISTERED_ROAMING = 5
    # EPS specific (from +CEREG)
    REGISTERED_SMS_ONLY_HOME = 6
    REGISTERED_SMS_ONLY_ROAMING = 7
    EMERGENCY_ONLY = 8
    REGISTERED_CSFB_NOT_PREFERRED_HOME = 9
    REGISTERED_CSFB_NOT_PREFERRED_ROAMING = 10


class NetworkType(Enum):
    """Network/Access Technology types."""

    GSM = "GSM"
    GPRS = "GPRS"
    EDGE = "EDGE"
    UMTS = "UMTS"
    HSDPA = "HSDPA"
    HSUPA = "HSUPA"
    HSPA = "HSPA"
    HSPA_PLUS = "HSPA+"
    LTE = "LTE"
    LTE_CA = "LTE-CA"
    NR5G_NSA = "NR5G-NSA"
    NR5G_SA = "NR5G-SA"
    UNKNOWN = "UNKNOWN"


class SIMStatus(Enum):
    """SIM card status codes (from +CPIN?)."""

    READY = "READY"
    SIM_PIN = "SIM PIN"
    SIM_PUK = "SIM PUK"
    SIM_PIN2 = "SIM PIN2"
    SIM_PUK2 = "SIM PUK2"
    PH_SIM_PIN = "PH-SIM PIN"
    PH_NET_PIN = "PH-NET PIN"
    PH_NET_PUK = "PH-NET PUK"
    PH_NETSUB_PIN = "PH-NETSUB PIN"
    PH_NETSUB_PUK = "PH-NETSUB PUK"
    PH_SP_PIN = "PH-SP PIN"
    PH_SP_PUK = "PH-SP PUK"
    PH_CORP_PIN = "PH-CORP PIN"
    PH_CORP_PUK = "PH-CORP PUK"
    NOT_INSERTED = "NOT INSERTED"
    NOT_READY = "NOT READY"
    ERROR = "ERROR"


class AuthType(Enum):
    """PDP context authentication type."""

    NONE = 0
    PAP = 1
    CHAP = 2
    PAP_OR_CHAP = 3


class URCType(Enum):
    """URC event types."""

    NETWORK_REGISTRATION = "network_registration"
    EPS_REGISTRATION = "eps_registration"
    SIM_STATUS = "sim_status"
    SIGNAL_CHANGE = "signal_change"
    SMS_RECEIVED = "sms_received"
    STK_EVENT = "stk_event"
    STK_PROACTIVE = "stk_proactive"
    INDICATION = "indication"
    CALL_STATUS = "call_status"
    RING = "ring"
    UNKNOWN = "unknown"


class BIPCommand(Enum):
    """STK BIP (Bearer Independent Protocol) command types."""

    OPEN_CHANNEL = 0x40
    CLOSE_CHANNEL = 0x41
    RECEIVE_DATA = 0x42
    SEND_DATA = 0x43
    GET_CHANNEL_STATUS = 0x44
    SERVICE_SEARCH = 0x45
    GET_SERVICE_INFORMATION = 0x46
    DECLARE_SERVICE = 0x47


class ModemVendor(Enum):
    """Known modem vendors."""

    QUECTEL = "Quectel"
    SIERRA = "Sierra Wireless"
    SIMCOM = "SIMCom"
    TELIT = "Telit"
    UBLOX = "u-blox"
    HUAWEI = "Huawei"
    ZTE = "ZTE"
    UNKNOWN = "Unknown"


# =============================================================================
# Serial Port Models
# =============================================================================


@dataclass
class PortInfo:
    """Information about a serial port."""

    port: str  # /dev/ttyUSB0 or COM3
    description: str = ""  # "Quectel USB AT Port"
    hwid: str = ""  # USB VID:PID
    manufacturer: str = ""  # "Quectel"
    product: str = ""  # "EG25-G"
    serial_number: str = ""  # Module serial
    vid: Optional[int] = None  # USB Vendor ID
    pid: Optional[int] = None  # USB Product ID
    location: str = ""  # USB location (bus-port)


# =============================================================================
# AT Command Models
# =============================================================================


@dataclass
class ATResponse:
    """Response from an AT command."""

    command: str
    raw_response: str
    result: ATResult
    data: List[str] = field(default_factory=list)  # Parsed response lines
    error_code: Optional[int] = None  # CME/CMS error code if applicable
    error_message: Optional[str] = None  # Human-readable error message

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.result == ATResult.OK

    def get_single_value(self) -> Optional[str]:
        """Get single value from response data (first line)."""
        return self.data[0] if self.data else None


# =============================================================================
# URC Models
# =============================================================================


@dataclass
class URCEvent:
    """Unsolicited Result Code event."""

    type: URCType
    timestamp: datetime
    raw_line: str
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls, urc_type: URCType, raw_line: str, data: Optional[Dict[str, Any]] = None
    ) -> "URCEvent":
        """Create a new URC event with current timestamp."""
        return cls(
            type=urc_type,
            timestamp=datetime.now(),
            raw_line=raw_line,
            data=data or {},
        )


@dataclass
class BIPEvent:
    """Bearer Independent Protocol event from STK notification."""

    command: BIPCommand
    timestamp: datetime
    raw_pdu: str
    channel_id: Optional[int] = None
    bearer_type: Optional[str] = None
    buffer_size: Optional[int] = None
    data_length: Optional[int] = None
    alpha_identifier: Optional[str] = None
    destination_address: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Modem Profile Models
# =============================================================================


@dataclass
class ModemProfile:
    """Modem hardware and firmware information."""

    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    imei: str = ""
    serial_number: str = ""
    module_type: str = ""
    supported_bands: List[str] = field(default_factory=list)
    vendor: ModemVendor = ModemVendor.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "imei": self.imei,
            "serial_number": self.serial_number,
            "module_type": self.module_type,
            "supported_bands": self.supported_bands,
            "vendor": self.vendor.value,
        }


@dataclass
class SIMProfile:
    """UICC/SIM card information."""

    status: SIMStatus = SIMStatus.NOT_READY
    iccid: Optional[str] = None
    imsi: Optional[str] = None
    msisdn: Optional[str] = None  # Phone number
    spn: Optional[str] = None  # Service Provider Name
    mcc: Optional[str] = None  # Mobile Country Code
    mnc: Optional[str] = None  # Mobile Network Code

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "iccid": self.iccid,
            "imsi": self.imsi,
            "msisdn": self.msisdn,
            "spn": self.spn,
            "mcc": self.mcc,
            "mnc": self.mnc,
        }

    @property
    def is_ready(self) -> bool:
        """Check if SIM is ready for operations."""
        return self.status == SIMStatus.READY


@dataclass
class NetworkProfile:
    """Network registration and signal information."""

    registration_status: RegistrationStatus = RegistrationStatus.NOT_REGISTERED
    eps_registration_status: Optional[RegistrationStatus] = None
    operator_name: str = ""
    operator_numeric: str = ""  # MCC+MNC numeric
    network_type: NetworkType = NetworkType.UNKNOWN
    rssi: Optional[int] = None  # Signal strength (dBm)
    rsrp: Optional[int] = None  # Reference Signal Received Power (dBm)
    rsrq: Optional[int] = None  # Reference Signal Received Quality (dB)
    sinr: Optional[int] = None  # Signal to Interference plus Noise Ratio (dB)
    cell_id: str = ""
    tac: str = ""  # Tracking Area Code
    lac: str = ""  # Location Area Code (2G/3G)
    apn: str = ""
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "registration_status": self.registration_status.value
            if isinstance(self.registration_status, RegistrationStatus)
            else self.registration_status,
            "eps_registration_status": self.eps_registration_status.value
            if self.eps_registration_status
            else None,
            "operator_name": self.operator_name,
            "operator_numeric": self.operator_numeric,
            "network_type": self.network_type.value,
            "rssi": self.rssi,
            "rsrp": self.rsrp,
            "rsrq": self.rsrq,
            "sinr": self.sinr,
            "cell_id": self.cell_id,
            "tac": self.tac,
            "lac": self.lac,
            "apn": self.apn,
            "ip_address": self.ip_address,
        }

    @property
    def is_registered(self) -> bool:
        """Check if registered to network."""
        return self.registration_status in (
            RegistrationStatus.REGISTERED_HOME,
            RegistrationStatus.REGISTERED_ROAMING,
        )


@dataclass
class FullModemProfile:
    """Complete modem profile including modem, SIM, and network info."""

    modem: ModemProfile
    sim: SIMProfile
    network: NetworkProfile
    timestamp: datetime = field(default_factory=datetime.now)
    port: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "modem": self.modem.to_dict(),
            "sim": self.sim.to_dict(),
            "network": self.network.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "port": self.port,
        }

    def to_json(self) -> str:
        """Export as JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# Network/Trigger Models
# =============================================================================


@dataclass
class PingResult:
    """Result from a ping command."""

    host: str
    sent: int = 0
    received: int = 0
    lost: int = 0
    min_time: Optional[float] = None  # ms
    max_time: Optional[float] = None  # ms
    avg_time: Optional[float] = None  # ms
    success: bool = False
    raw_response: str = ""

    @property
    def loss_percentage(self) -> float:
        """Calculate packet loss percentage."""
        if self.sent == 0:
            return 100.0
        return (self.lost / self.sent) * 100.0


@dataclass
class TriggerTemplate:
    """SMS trigger template for OTA operations."""

    name: str
    description: str = ""
    pdu_template: str = ""  # PDU hex template with placeholders
    parameters: List[str] = field(default_factory=list)  # Required parameters


@dataclass
class TriggerResult:
    """Result from sending an SMS trigger."""

    success: bool
    message_reference: Optional[int] = None  # +CMGS reference number
    raw_response: str = ""
    error: Optional[str] = None


# =============================================================================
# QXDM Models
# =============================================================================


@dataclass
class QXDMLogEntry:
    """QXDM diagnostic log entry."""

    timestamp: datetime
    log_code: int
    log_name: str = ""
    data: bytes = b""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# USB/Hardware Constants
# =============================================================================


# Quectel USB VID:PID mappings
QUECTEL_USB_IDS: Dict[str, str] = {
    "2c7c:0125": "EC25",
    "2c7c:0121": "EC21",
    "2c7c:0195": "EG25-G",
    "2c7c:0306": "EG06",
    "2c7c:0512": "EG12",
    "2c7c:0296": "BG96",
    "2c7c:0435": "AG35",
    "2c7c:0620": "EG20",
    "2c7c:0800": "RG500Q",
    "2c7c:0801": "RG520N",
}

# Sierra Wireless USB VID:PID mappings
SIERRA_USB_IDS: Dict[str, str] = {
    "1199:9071": "EM7455",
    "1199:9079": "EM7565",
    "1199:90b1": "EM7511",
}

# SIMCom USB VID:PID mappings
SIMCOM_USB_IDS: Dict[str, str] = {
    "1e0e:9001": "SIM7600",
    "1e0e:9011": "SIM7000",
}

# Combined USB ID to vendor mapping
USB_VENDOR_MAP: Dict[str, ModemVendor] = {
    **{vid_pid: ModemVendor.QUECTEL for vid_pid in QUECTEL_USB_IDS},
    **{vid_pid: ModemVendor.SIERRA for vid_pid in SIERRA_USB_IDS},
    **{vid_pid: ModemVendor.SIMCOM for vid_pid in SIMCOM_USB_IDS},
}

# Quectel port function mapping (by interface number)
QUECTEL_PORT_FUNCTIONS: Dict[int, str] = {
    0: "DM",  # Diagnostic/QXDM
    1: "NMEA",  # GPS NMEA
    2: "AT",  # AT commands
    3: "PPP",  # Data/PPP
}
