"""Event Types and Schemas for network simulator integration.

This module defines all event types and payload schemas for the
network simulator event system.

Event Types:
    - Simulator events: connection, disconnection, errors
    - UE events: registration, deregistration, state changes
    - Session events: establishment, modification, release
    - SMS events: send, receive, delivery status
    - Network events: cell changes, handover, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EventCategory(Enum):
    """Event categories for organization."""

    SIMULATOR = "simulator"
    UE = "ue"
    SESSION = "session"
    SMS = "sms"
    CELL = "cell"
    NETWORK = "network"
    TRIGGER = "trigger"


# =============================================================================
# Event Type Constants
# =============================================================================


class SimulatorEventType(str, Enum):
    """Simulator connection event types."""

    SIMULATOR_CONNECTED = "simulator_connected"
    SIMULATOR_DISCONNECTED = "simulator_disconnected"
    SIMULATOR_RECONNECTING = "simulator_reconnecting"
    SIMULATOR_ERROR = "simulator_error"
    SIMULATOR_AUTHENTICATED = "simulator_authenticated"


class UEEventType(str, Enum):
    """UE-related event types."""

    UE_REGISTERED = "ue_registered"
    UE_DEREGISTERED = "ue_deregistered"
    UE_STATE_CHANGED = "ue_state_changed"
    UE_CELL_CHANGED = "ue_cell_changed"
    UE_IP_ASSIGNED = "ue_ip_assigned"


class SessionEventType(str, Enum):
    """Data session event types."""

    SESSION_ESTABLISHED = "session_established"
    SESSION_MODIFIED = "session_modified"
    SESSION_RELEASED = "session_released"
    SESSION_QOS_CHANGED = "session_qos_changed"


class SMSEventType(str, Enum):
    """SMS-related event types."""

    SMS_SENT = "sms_sent"
    SMS_RECEIVED = "sms_received"
    SMS_DELIVERED = "sms_delivered"
    SMS_FAILED = "sms_failed"


class CellEventType(str, Enum):
    """Cell-related event types."""

    CELL_STARTED = "cell_started"
    CELL_STOPPED = "cell_stopped"
    CELL_CONFIGURED = "cell_configured"
    CELL_STATUS_CHANGED = "cell_status_changed"


class NetworkEventType(str, Enum):
    """Network event types."""

    HANDOVER_STARTED = "handover_started"
    HANDOVER_COMPLETED = "handover_completed"
    HANDOVER_FAILED = "handover_failed"
    PAGING_TRIGGERED = "paging_triggered"
    DETACH_TRIGGERED = "detach_triggered"
    CELL_OUTAGE = "cell_outage"
    RLF_TRIGGERED = "rlf_triggered"
    TAU_TRIGGERED = "tau_triggered"


class TriggerEventType(str, Enum):
    """Trigger execution event types."""

    TRIGGER_EXECUTED = "trigger_executed"
    TRIGGER_FAILED = "trigger_failed"


# =============================================================================
# Event Payload Schemas
# =============================================================================


@dataclass(frozen=True)
class SimulatorEventPayload:
    """Payload for simulator events.

    Attributes:
        url: Simulator URL.
        simulator_type: Type of simulator (amarisoft, generic).
        authenticated: Whether authentication succeeded.
        error: Error message if applicable.
        reconnect_attempt: Reconnection attempt number.
    """

    url: str
    simulator_type: str
    authenticated: bool = False
    error: Optional[str] = None
    reconnect_attempt: Optional[int] = None


@dataclass(frozen=True)
class UEEventPayload:
    """Payload for UE events.

    Attributes:
        imsi: IMSI of the UE.
        imei: IMEI of the UE (if available).
        status: UE status (registered, idle, etc.).
        cell_id: Cell ID where UE is attached.
        ip_address: Assigned IP address.
        previous_status: Previous status (for state changes).
        previous_cell_id: Previous cell ID (for cell changes).
    """

    imsi: str
    imei: Optional[str] = None
    status: Optional[str] = None
    cell_id: Optional[int] = None
    ip_address: Optional[str] = None
    previous_status: Optional[str] = None
    previous_cell_id: Optional[int] = None


@dataclass(frozen=True)
class SessionEventPayload:
    """Payload for session events.

    Attributes:
        session_id: Unique session identifier.
        imsi: IMSI of the UE.
        apn: Access Point Name.
        ip_address: Assigned IP address.
        qci: QoS Class Identifier.
        change_type: Type of change (established, modified, released).
        previous_qci: Previous QCI (for QoS changes).
    """

    session_id: str
    imsi: str
    apn: Optional[str] = None
    ip_address: Optional[str] = None
    qci: Optional[int] = None
    change_type: Optional[str] = None
    previous_qci: Optional[int] = None


@dataclass(frozen=True)
class SMSEventPayload:
    """Payload for SMS events.

    Attributes:
        message_id: Unique message identifier.
        imsi: IMSI of the UE.
        direction: SMS direction (mt, mo).
        pdu_hex: PDU data in hex.
        status: Delivery status.
        error: Error message if failed.
        is_ota: Whether this is an OTA message.
        tar: TAR value for OTA messages.
    """

    message_id: str
    imsi: str
    direction: str  # "mt" or "mo"
    pdu_hex: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    is_ota: bool = False
    tar: Optional[str] = None


@dataclass(frozen=True)
class CellEventPayload:
    """Payload for cell events.

    Attributes:
        cell_id: Cell identifier.
        status: Cell status (active, inactive).
        plmn: PLMN code.
        frequency: Cell frequency in MHz.
        bandwidth: Cell bandwidth in MHz.
        tx_power: Transmit power in dBm.
        previous_status: Previous status.
    """

    cell_id: Optional[int] = None
    status: Optional[str] = None
    plmn: Optional[str] = None
    frequency: Optional[int] = None
    bandwidth: Optional[int] = None
    tx_power: Optional[int] = None
    previous_status: Optional[str] = None


@dataclass(frozen=True)
class NetworkEventPayload:
    """Payload for network events.

    Attributes:
        event_type: Specific network event type.
        imsi: IMSI of affected UE (if applicable).
        source_cell_id: Source cell ID.
        target_cell_id: Target cell ID (for handover).
        cause: Event cause or reason.
        duration: Event duration (for outages).
        success: Whether event succeeded.
    """

    event_type: str
    imsi: Optional[str] = None
    source_cell_id: Optional[int] = None
    target_cell_id: Optional[int] = None
    cause: Optional[str] = None
    duration: Optional[float] = None
    success: bool = True


@dataclass(frozen=True)
class TriggerEventPayload:
    """Payload for trigger events.

    Attributes:
        trigger_type: Type of trigger (paging, handover, etc.).
        imsi: IMSI of target UE.
        params: Trigger parameters.
        success: Whether trigger succeeded.
        error: Error message if failed.
    """

    trigger_type: str
    imsi: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# Generic Event Container
# =============================================================================


@dataclass
class Event:
    """Generic event container.

    Provides a unified structure for all events with type, payload,
    and metadata.

    Attributes:
        event_type: The event type (from one of the type enums).
        category: Event category for filtering.
        payload: Event-specific payload data.
        timestamp: When the event occurred.
        correlation_id: ID for correlating related events.
        source: Source of the event (manager name).
    """

    event_type: str
    category: EventCategory
    payload: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    source: str = "netsim"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of the event.
        """
        payload_dict = {}
        if hasattr(self.payload, "__dict__"):
            payload_dict = {
                k: v for k, v in self.payload.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(self.payload, dict):
            payload_dict = self.payload

        return {
            "event_type": self.event_type,
            "category": self.category.value,
            "payload": payload_dict,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source": self.source,
        }


# =============================================================================
# Event Factory Functions
# =============================================================================


def create_simulator_event(
    event_type: SimulatorEventType,
    url: str,
    simulator_type: str,
    **kwargs,
) -> Event:
    """Create a simulator event.

    Args:
        event_type: The simulator event type.
        url: Simulator URL.
        simulator_type: Type of simulator.
        **kwargs: Additional payload fields.

    Returns:
        Event instance.
    """
    payload = SimulatorEventPayload(
        url=url,
        simulator_type=simulator_type,
        **kwargs,
    )
    return Event(
        event_type=event_type.value,
        category=EventCategory.SIMULATOR,
        payload=payload,
    )


def create_ue_event(
    event_type: UEEventType,
    imsi: str,
    **kwargs,
) -> Event:
    """Create a UE event.

    Args:
        event_type: The UE event type.
        imsi: IMSI of the UE.
        **kwargs: Additional payload fields.

    Returns:
        Event instance.
    """
    payload = UEEventPayload(imsi=imsi, **kwargs)
    return Event(
        event_type=event_type.value,
        category=EventCategory.UE,
        payload=payload,
    )


def create_session_event(
    event_type: SessionEventType,
    session_id: str,
    imsi: str,
    **kwargs,
) -> Event:
    """Create a session event.

    Args:
        event_type: The session event type.
        session_id: Session identifier.
        imsi: IMSI of the UE.
        **kwargs: Additional payload fields.

    Returns:
        Event instance.
    """
    payload = SessionEventPayload(
        session_id=session_id,
        imsi=imsi,
        **kwargs,
    )
    return Event(
        event_type=event_type.value,
        category=EventCategory.SESSION,
        payload=payload,
    )


def create_sms_event(
    event_type: SMSEventType,
    message_id: str,
    imsi: str,
    direction: str,
    **kwargs,
) -> Event:
    """Create an SMS event.

    Args:
        event_type: The SMS event type.
        message_id: Message identifier.
        imsi: IMSI of the UE.
        direction: SMS direction (mt/mo).
        **kwargs: Additional payload fields.

    Returns:
        Event instance.
    """
    payload = SMSEventPayload(
        message_id=message_id,
        imsi=imsi,
        direction=direction,
        **kwargs,
    )
    return Event(
        event_type=event_type.value,
        category=EventCategory.SMS,
        payload=payload,
    )


def create_cell_event(
    event_type: CellEventType,
    **kwargs,
) -> Event:
    """Create a cell event.

    Args:
        event_type: The cell event type.
        **kwargs: Payload fields.

    Returns:
        Event instance.
    """
    payload = CellEventPayload(**kwargs)
    return Event(
        event_type=event_type.value,
        category=EventCategory.CELL,
        payload=payload,
    )


def create_network_event(
    event_type: NetworkEventType,
    **kwargs,
) -> Event:
    """Create a network event.

    Args:
        event_type: The network event type.
        **kwargs: Payload fields.

    Returns:
        Event instance.
    """
    payload = NetworkEventPayload(
        event_type=event_type.value,
        **kwargs,
    )
    return Event(
        event_type=event_type.value,
        category=EventCategory.NETWORK,
        payload=payload,
    )


def create_trigger_event(
    event_type: TriggerEventType,
    trigger_type: str,
    **kwargs,
) -> Event:
    """Create a trigger event.

    Args:
        event_type: The trigger event type.
        trigger_type: Type of trigger executed.
        **kwargs: Additional payload fields.

    Returns:
        Event instance.
    """
    payload = TriggerEventPayload(
        trigger_type=trigger_type,
        **kwargs,
    )
    return Event(
        event_type=event_type.value,
        category=EventCategory.TRIGGER,
        payload=payload,
    )
