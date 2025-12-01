"""Core data types and enums for network simulator integration.

This module defines all data structures used throughout the network simulator
integration, including enums for statuses and types, and dataclasses for
domain objects like UE information, sessions, and events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional


class SimulatorType(Enum):
    """Type of network simulator."""

    AMARISOFT = "amarisoft"
    """Amarisoft Callbox (LTE/5G)."""

    SRSRAN = "srsran"
    """srsRAN open-source simulator."""

    OPENAIRINTERFACE = "openairinterface"
    """OpenAirInterface simulator."""

    GENERIC = "generic"
    """Generic simulator with REST-like API."""


class CellStatus(Enum):
    """Status of a simulated cell (eNB/gNB)."""

    INACTIVE = "inactive"
    """Cell is not active."""

    STARTING = "starting"
    """Cell is starting up."""

    ACTIVE = "active"
    """Cell is active and operational."""

    STOPPING = "stopping"
    """Cell is shutting down."""

    ERROR = "error"
    """Cell is in error state."""


class UEStatus(Enum):
    """Status of a UE (User Equipment)."""

    DETACHED = "detached"
    """UE is not attached to the network."""

    ATTACHING = "attaching"
    """UE is in the process of attaching."""

    ATTACHED = "attached"
    """UE is attached to the network."""

    REGISTERED = "registered"
    """UE is registered (5G NR term)."""

    CONNECTED = "connected"
    """UE has an active RRC connection."""

    IDLE = "idle"
    """UE is in idle mode (attached but no active connection)."""


class SMSDirection(Enum):
    """Direction of an SMS message."""

    MT = "mt"
    """Mobile Terminated (to device)."""

    MO = "mo"
    """Mobile Originated (from device)."""


class SMSStatus(Enum):
    """Status of an SMS message."""

    PENDING = "pending"
    """SMS is pending delivery."""

    SENT = "sent"
    """SMS has been sent."""

    DELIVERED = "delivered"
    """SMS has been delivered."""

    FAILED = "failed"
    """SMS delivery failed."""


class NetworkEventType(Enum):
    """Type of network event."""

    UE_ATTACH = auto()
    UE_DETACH = auto()
    PDN_CONNECT = auto()
    PDN_DISCONNECT = auto()
    SMS_RECEIVED = auto()
    SMS_SENT = auto()
    HANDOVER = auto()
    PAGING = auto()
    TAU = auto()  # Tracking Area Update
    RAU = auto()  # Routing Area Update
    SERVICE_REQUEST = auto()
    RLF = auto()  # Radio Link Failure
    CELL_CHANGE = auto()
    CUSTOM = auto()


@dataclass
class TLSConfig:
    """TLS/SSL configuration for secure connections.

    Attributes:
        enabled: Whether TLS is enabled.
        verify_cert: Whether to verify server certificate.
        ca_cert: Path to CA certificate file.
        client_cert: Path to client certificate file.
        client_key: Path to client private key file.
    """

    enabled: bool = True
    verify_cert: bool = True
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None


@dataclass
class SimulatorConfig:
    """Configuration for connecting to a network simulator.

    Attributes:
        url: WebSocket or TCP URL (e.g., wss://callbox.local:9001).
        simulator_type: Type of simulator (Amarisoft, Generic, etc.).
        api_key: API key for authentication (optional).
        tls_config: TLS configuration for secure connections.
        connect_timeout: Connection timeout in seconds.
        read_timeout: Read timeout in seconds.
        auto_reconnect: Whether to automatically reconnect on disconnect.
        reconnect_delay: Initial delay between reconnection attempts.
        max_reconnect_attempts: Maximum reconnection attempts (0 = unlimited).

    Example:
        >>> config = SimulatorConfig(
        ...     url="wss://callbox.local:9001",
        ...     simulator_type=SimulatorType.AMARISOFT,
        ...     api_key="my-secret-key"
        ... )
    """

    url: str
    simulator_type: SimulatorType = SimulatorType.AMARISOFT
    api_key: Optional[str] = None
    tls_config: TLSConfig = field(default_factory=TLSConfig)
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
    auto_reconnect: bool = True
    reconnect_delay: float = 1.0
    max_reconnect_attempts: int = 10

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        from cardlink.netsim.exceptions import ConfigurationError

        if not self.url:
            raise ConfigurationError("URL is required")

        # Validate URL scheme
        valid_schemes = ("ws://", "wss://", "tcp://", "tcps://")
        if not any(self.url.startswith(scheme) for scheme in valid_schemes):
            raise ConfigurationError(
                f"Invalid URL scheme. Must start with one of: {valid_schemes}"
            )

        if self.connect_timeout <= 0:
            raise ConfigurationError("connect_timeout must be positive")

        if self.read_timeout <= 0:
            raise ConfigurationError("read_timeout must be positive")

        if self.reconnect_delay < 0:
            raise ConfigurationError("reconnect_delay cannot be negative")

        if self.max_reconnect_attempts < 0:
            raise ConfigurationError("max_reconnect_attempts cannot be negative")


@dataclass
class UEInfo:
    """Information about a connected UE (User Equipment).

    Attributes:
        imsi: International Mobile Subscriber Identity.
        imei: International Mobile Equipment Identity.
        status: Current UE status.
        cell_id: ID of the cell the UE is connected to.
        ip_address: Assigned IP address (if any).
        apn: Active APN (if any).
        rat_type: Radio Access Technology (LTE, NR, etc.).
        signal_strength: Signal strength indicator (e.g., RSRP).
        attached_at: Timestamp when UE attached.
        metadata: Additional UE-specific metadata.

    Example:
        >>> ue = UEInfo(
        ...     imsi="001010123456789",
        ...     imei="123456789012345",
        ...     status=UEStatus.CONNECTED
        ... )
    """

    imsi: str
    imei: Optional[str] = None
    status: UEStatus = UEStatus.DETACHED
    cell_id: Optional[int] = None
    ip_address: Optional[str] = None
    apn: Optional[str] = None
    rat_type: Optional[str] = None
    signal_strength: Optional[float] = None
    attached_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "imsi": self.imsi,
            "imei": self.imei,
            "status": self.status.value,
            "cell_id": self.cell_id,
            "ip_address": self.ip_address,
            "apn": self.apn,
            "rat_type": self.rat_type,
            "signal_strength": self.signal_strength,
            "attached_at": self.attached_at.isoformat() if self.attached_at else None,
            "metadata": self.metadata,
        }


@dataclass
class QoSParameters:
    """Quality of Service parameters for a data session.

    Attributes:
        qci: QoS Class Identifier (LTE) / 5QI (5G NR).
        arp: Allocation and Retention Priority.
        mbr_ul: Maximum Bit Rate uplink (kbps).
        mbr_dl: Maximum Bit Rate downlink (kbps).
        gbr_ul: Guaranteed Bit Rate uplink (kbps).
        gbr_dl: Guaranteed Bit Rate downlink (kbps).
    """

    qci: Optional[int] = None
    arp: Optional[int] = None
    mbr_ul: Optional[int] = None
    mbr_dl: Optional[int] = None
    gbr_ul: Optional[int] = None
    gbr_dl: Optional[int] = None


@dataclass
class DataSession:
    """Information about a data session (PDN/PDU context).

    Attributes:
        session_id: Unique session identifier.
        imsi: IMSI of the UE owning this session.
        apn: Access Point Name.
        ip_address: Assigned IP address.
        ipv6_address: Assigned IPv6 address (if any).
        qos: QoS parameters for the session.
        pdn_type: PDN type (IPv4, IPv6, IPv4v6).
        created_at: Session creation timestamp.
        metadata: Additional session-specific metadata.

    Example:
        >>> session = DataSession(
        ...     session_id="sess_001",
        ...     imsi="001010123456789",
        ...     apn="internet",
        ...     ip_address="10.0.0.1"
        ... )
    """

    session_id: str
    imsi: str
    apn: str
    ip_address: Optional[str] = None
    ipv6_address: Optional[str] = None
    qos: QoSParameters = field(default_factory=QoSParameters)
    pdn_type: str = "IPv4"
    created_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "session_id": self.session_id,
            "imsi": self.imsi,
            "apn": self.apn,
            "ip_address": self.ip_address,
            "ipv6_address": self.ipv6_address,
            "qos": {
                "qci": self.qos.qci,
                "arp": self.qos.arp,
                "mbr_ul": self.qos.mbr_ul,
                "mbr_dl": self.qos.mbr_dl,
                "gbr_ul": self.qos.gbr_ul,
                "gbr_dl": self.qos.gbr_dl,
            },
            "pdn_type": self.pdn_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


@dataclass
class CellInfo:
    """Information about a simulated cell (eNB/gNB).

    Attributes:
        cell_id: Cell identifier.
        status: Current cell status.
        rat_type: Radio Access Technology (LTE, NR).
        plmn: Public Land Mobile Network (MCC-MNC).
        frequency: Operating frequency (MHz).
        bandwidth: Channel bandwidth (MHz).
        tx_power: Transmit power (dBm).
        connected_ues: Number of connected UEs.
        metadata: Additional cell-specific metadata.

    Example:
        >>> cell = CellInfo(
        ...     cell_id=1,
        ...     status=CellStatus.ACTIVE,
        ...     rat_type="LTE"
        ... )
    """

    cell_id: int
    status: CellStatus = CellStatus.INACTIVE
    rat_type: str = "LTE"
    plmn: Optional[str] = None
    frequency: Optional[float] = None
    bandwidth: Optional[float] = None
    tx_power: Optional[float] = None
    connected_ues: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "cell_id": self.cell_id,
            "status": self.status.value,
            "rat_type": self.rat_type,
            "plmn": self.plmn,
            "frequency": self.frequency,
            "bandwidth": self.bandwidth,
            "tx_power": self.tx_power,
            "connected_ues": self.connected_ues,
            "metadata": self.metadata,
        }


@dataclass
class SMSMessage:
    """Information about an SMS message.

    Attributes:
        message_id: Unique message identifier.
        imsi: IMSI of the target/source UE.
        direction: Message direction (MT or MO).
        pdu: Raw PDU bytes.
        status: Message delivery status.
        timestamp: Message timestamp.
        metadata: Additional message-specific metadata.

    Example:
        >>> sms = SMSMessage(
        ...     message_id="msg_001",
        ...     imsi="001010123456789",
        ...     direction=SMSDirection.MT,
        ...     pdu=b"\\x00\\x04..."
        ... )
    """

    message_id: str
    imsi: str
    direction: SMSDirection
    pdu: bytes
    status: SMSStatus = SMSStatus.PENDING
    timestamp: Optional[datetime] = None
    error_cause: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "message_id": self.message_id,
            "imsi": self.imsi,
            "direction": self.direction.value,
            "pdu": self.pdu.hex(),
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "error_cause": self.error_cause,
            "metadata": self.metadata,
        }


@dataclass
class NetworkEvent:
    """A network event from the simulator.

    Attributes:
        event_id: Unique event identifier.
        event_type: Type of network event.
        timestamp: Event timestamp.
        source: Event source (e.g., "simulator", "adapter").
        data: Event-specific data.
        imsi: Associated IMSI (if applicable).
        session_id: Associated session ID (if applicable).
        correlation_id: ID for correlating related events.

    Example:
        >>> event = NetworkEvent(
        ...     event_id="evt_001",
        ...     event_type=NetworkEventType.UE_ATTACH,
        ...     data={"imsi": "001010123456789"}
        ... )
    """

    event_id: str
    event_type: NetworkEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "simulator"
    data: dict[str, Any] = field(default_factory=dict)
    imsi: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "imsi": self.imsi,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
        }


@dataclass
class SimulatorStatus:
    """Aggregated status of the network simulator.

    Attributes:
        connected: Whether connected to the simulator.
        authenticated: Whether authenticated with the simulator.
        cell: Cell status information.
        ue_count: Number of connected UEs.
        session_count: Number of active data sessions.
        error: Current error message (if any).
        last_updated: Timestamp of last status update.
    """

    connected: bool = False
    authenticated: bool = False
    cell: Optional[CellInfo] = None
    ue_count: int = 0
    session_count: int = 0
    error: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "connected": self.connected,
            "authenticated": self.authenticated,
            "cell": self.cell.to_dict() if self.cell else None,
            "ue_count": self.ue_count,
            "session_count": self.session_count,
            "error": self.error,
            "last_updated": self.last_updated.isoformat(),
        }
