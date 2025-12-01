"""Protocol constants for network simulator integration.

This module defines constants used throughout the network simulator integration,
including timeouts, protocol parameters, and default values.
"""

# =============================================================================
# Connection Timeouts (seconds)
# =============================================================================

DEFAULT_CONNECT_TIMEOUT: float = 30.0
"""Default timeout for establishing a connection."""

DEFAULT_READ_TIMEOUT: float = 30.0
"""Default timeout for read operations."""

DEFAULT_COMMAND_TIMEOUT: float = 10.0
"""Default timeout for command responses."""

# =============================================================================
# WebSocket Configuration
# =============================================================================

DEFAULT_KEEPALIVE_INTERVAL: float = 30.0
"""Interval between WebSocket ping frames (seconds)."""

DEFAULT_PONG_TIMEOUT: float = 10.0
"""Timeout waiting for WebSocket pong response (seconds)."""

DEFAULT_MAX_MESSAGE_SIZE: int = 16 * 1024 * 1024  # 16 MB
"""Maximum WebSocket message size in bytes."""

# =============================================================================
# Reconnection Configuration
# =============================================================================

DEFAULT_RECONNECT_DELAY: float = 1.0
"""Initial delay before reconnection attempt (seconds)."""

DEFAULT_MAX_RECONNECT_DELAY: float = 60.0
"""Maximum delay between reconnection attempts (seconds)."""

DEFAULT_RECONNECT_MULTIPLIER: float = 2.0
"""Multiplier for exponential backoff."""

DEFAULT_MAX_RECONNECT_ATTEMPTS: int = 10
"""Maximum number of reconnection attempts (0 = unlimited)."""

# =============================================================================
# JSON-RPC Protocol
# =============================================================================

JSONRPC_VERSION: str = "2.0"
"""JSON-RPC protocol version."""

# JSON-RPC Error Codes (per specification)
JSONRPC_PARSE_ERROR: int = -32700
JSONRPC_INVALID_REQUEST: int = -32600
JSONRPC_METHOD_NOT_FOUND: int = -32601
JSONRPC_INVALID_PARAMS: int = -32602
JSONRPC_INTERNAL_ERROR: int = -32603

# Custom error codes (application-specific, -32000 to -32099)
ERROR_NOT_AUTHENTICATED: int = -32000
ERROR_OPERATION_FAILED: int = -32001
ERROR_INVALID_STATE: int = -32002
ERROR_RESOURCE_NOT_FOUND: int = -32003
ERROR_RATE_LIMITED: int = -32004

# =============================================================================
# Amarisoft Remote API Methods
# =============================================================================

# Authentication
METHOD_AUTHENTICATE: str = "authenticate"

# Cell operations (eNB/gNB)
METHOD_ENB_GET_STATUS: str = "enb.get_status"
METHOD_ENB_START: str = "enb.start"
METHOD_ENB_STOP: str = "enb.stop"
METHOD_ENB_CONFIGURE: str = "enb.configure"

# UE operations
METHOD_UE_LIST: str = "ue.list"
METHOD_UE_GET: str = "ue.get"
METHOD_UE_DETACH: str = "ue.detach"

# Session operations
METHOD_SESSION_LIST: str = "session.list"
METHOD_SESSION_RELEASE: str = "session.release"

# SMS operations
METHOD_SMS_SEND: str = "sms.send"

# Configuration operations
METHOD_CONFIG_GET: str = "config.get"
METHOD_CONFIG_SET: str = "config.set"

# =============================================================================
# Event Types
# =============================================================================

# Simulator connection events
EVENT_SIMULATOR_CONNECTED: str = "simulator_connected"
EVENT_SIMULATOR_DISCONNECTED: str = "simulator_disconnected"
EVENT_SIMULATOR_ERROR: str = "simulator_error"
EVENT_SIMULATOR_RECONNECTING: str = "simulator_reconnecting"

# UE events
EVENT_UE_ATTACHED: str = "ue_attached"
EVENT_UE_DETACHED: str = "ue_detached"
EVENT_UE_REGISTERED: str = "ue_registered"
EVENT_UE_DEREGISTERED: str = "ue_deregistered"

# Session events
EVENT_PDN_CONNECTED: str = "pdn_connected"
EVENT_PDN_DISCONNECTED: str = "pdn_disconnected"
EVENT_DATA_SESSION_ACTIVATED: str = "data_session_activated"
EVENT_DATA_SESSION_DEACTIVATED: str = "data_session_deactivated"

# SMS events
EVENT_SMS_SENT: str = "sms_sent"
EVENT_SMS_DELIVERED: str = "sms_delivered"
EVENT_SMS_FAILED: str = "sms_failed"
EVENT_SMS_RECEIVED: str = "sms_received"
EVENT_SMS_EVENT: str = "sms_event"

# Cell events
EVENT_CELL_STARTED: str = "cell_started"
EVENT_CELL_STOPPED: str = "cell_stopped"
EVENT_CELL_STARTING: str = "cell_starting"
EVENT_CELL_STOPPING: str = "cell_stopping"

# Network events (generic)
EVENT_NETWORK_EVENT: str = "network_event"

# =============================================================================
# Cache and History Limits
# =============================================================================

DEFAULT_UE_CACHE_SIZE: int = 1000
"""Maximum number of UEs to cache."""

DEFAULT_SESSION_CACHE_SIZE: int = 1000
"""Maximum number of sessions to cache."""

DEFAULT_EVENT_HISTORY_SIZE: int = 10000
"""Maximum number of events to keep in history."""

DEFAULT_SMS_HISTORY_SIZE: int = 1000
"""Maximum number of SMS messages to keep in history."""

# =============================================================================
# Protocol URLs
# =============================================================================

PROTOCOL_WS: str = "ws"
PROTOCOL_WSS: str = "wss"
PROTOCOL_TCP: str = "tcp"
PROTOCOL_TCPS: str = "tcps"

SUPPORTED_PROTOCOLS: tuple[str, ...] = (PROTOCOL_WS, PROTOCOL_WSS, PROTOCOL_TCP, PROTOCOL_TCPS)
"""Supported connection protocols."""
