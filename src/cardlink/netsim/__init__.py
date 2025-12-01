"""Network Simulator Integration for CardLink.

This module provides integration with network simulators (e.g., Amarisoft Callbox)
for OTA testing scenarios. It enables:

- Connection management (WebSocket/TCP)
- UE registration monitoring
- Data session tracking
- SMS injection for OTA triggers
- Network event triggering and monitoring
- Scenario-based test orchestration

Example:
    >>> from cardlink.netsim import SimulatorManager, SimulatorConfig
    >>> config = SimulatorConfig(
    ...     url="wss://callbox.local:9001",
    ...     simulator_type=SimulatorType.AMARISOFT,
    ...     api_key="secret"
    ... )
    >>> manager = SimulatorManager(config)
    >>> await manager.connect()
    >>> await manager.ue.wait_for_registration("001010123456789", timeout=30)
    >>> await manager.sms.send_mt_sms("001010123456789", pdu_bytes)
"""

from cardlink.netsim.adapters import AmarisoftAdapter, GenericAdapter
from cardlink.netsim.connection import (
    BaseConnection,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    ReconnectManager,
    RetryConfig,
    TCPConnection,
    WSConnection,
    classify_connection_error,
    create_connection,
    retry_operation,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.manager import EventEmitter, SimulatorManager
from cardlink.netsim.managers import (
    CellManager,
    ConfigManager,
    EventManager,
    SessionManager,
    SMSManager,
    UEManager,
)
from cardlink.netsim.triggers import TriggerManager
from cardlink.netsim.scenario import (
    Condition,
    ConditionOperator,
    Scenario,
    ScenarioResult,
    ScenarioRunner,
    Step,
    StepResult,
    StepStatus,
)
from cardlink.netsim.events import (
    CellEventPayload,
    CellEventType,
    Event,
    EventCategory,
    NetworkEventPayload,
    NetworkEventType,
    SessionEventPayload,
    SessionEventType,
    SimulatorEventPayload,
    SimulatorEventType,
    SMSEventPayload,
    SMSEventType,
    TriggerEventPayload,
    TriggerEventType,
    UEEventPayload,
    UEEventType,
    create_cell_event,
    create_network_event,
    create_session_event,
    create_simulator_event,
    create_sms_event,
    create_trigger_event,
    create_ue_event,
)
from cardlink.netsim.constants import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    DEFAULT_PONG_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_RECONNECT_DELAY,
)
from cardlink.netsim.performance import (
    BatchConfig,
    CacheEntry,
    CacheStats,
    RateLimiter,
    RateLimiterConfig,
    RequestBatcher,
    ResponseCache,
    cached_method,
)
from cardlink.netsim.exceptions import (
    AuthenticationError,
    CircuitBreakerOpenError,
    CommandError,
    ConfigurationError,
    ConnectionError,
    NetworkSimulatorError,
    NotConnectedError,
    PermanentConnectionError,
    RateLimitError,
    ResourceNotFoundError,
    RetryableError,
    TimeoutError,
    TransientConnectionError,
)
from cardlink.netsim.types import (
    CellInfo,
    CellStatus,
    DataSession,
    NetworkEvent,
    SimulatorConfig,
    SimulatorStatus,
    SimulatorType,
    SMSMessage,
    TLSConfig,
    UEInfo,
    UEStatus,
)

__all__ = [
    # Manager
    "SimulatorManager",
    "EventEmitter",
    # Sub-managers
    "UEManager",
    "SessionManager",
    "SMSManager",
    "CellManager",
    "EventManager",
    "ConfigManager",
    # Triggers
    "TriggerManager",
    # Scenario
    "Scenario",
    "ScenarioRunner",
    "ScenarioResult",
    "Step",
    "StepResult",
    "StepStatus",
    "Condition",
    "ConditionOperator",
    # Events
    "Event",
    "EventCategory",
    "SimulatorEventType",
    "SimulatorEventPayload",
    "UEEventType",
    "UEEventPayload",
    "SessionEventType",
    "SessionEventPayload",
    "SMSEventType",
    "SMSEventPayload",
    "CellEventType",
    "CellEventPayload",
    "NetworkEventType",
    "NetworkEventPayload",
    "TriggerEventType",
    "TriggerEventPayload",
    "create_simulator_event",
    "create_ue_event",
    "create_session_event",
    "create_sms_event",
    "create_cell_event",
    "create_network_event",
    "create_trigger_event",
    # Interface and Adapters
    "SimulatorInterface",
    "AmarisoftAdapter",
    "GenericAdapter",
    # Connection
    "BaseConnection",
    "WSConnection",
    "TCPConnection",
    "ReconnectManager",
    "create_connection",
    # Circuit Breaker and Retry
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "RetryConfig",
    "retry_operation",
    "classify_connection_error",
    # Types
    "SimulatorType",
    "CellStatus",
    "UEStatus",
    "SimulatorConfig",
    "SimulatorStatus",
    "TLSConfig",
    "UEInfo",
    "DataSession",
    "CellInfo",
    "SMSMessage",
    "NetworkEvent",
    # Exceptions
    "NetworkSimulatorError",
    "ConnectionError",
    "TransientConnectionError",
    "PermanentConnectionError",
    "AuthenticationError",
    "CommandError",
    "TimeoutError",
    "ConfigurationError",
    "NotConnectedError",
    "ResourceNotFoundError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    "RetryableError",
    # Constants
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_READ_TIMEOUT",
    "DEFAULT_KEEPALIVE_INTERVAL",
    "DEFAULT_PONG_TIMEOUT",
    "DEFAULT_RECONNECT_DELAY",
    "DEFAULT_MAX_RECONNECT_ATTEMPTS",
    # Performance
    "ResponseCache",
    "CacheEntry",
    "CacheStats",
    "RequestBatcher",
    "BatchConfig",
    "RateLimiter",
    "RateLimiterConfig",
    "cached_method",
]
