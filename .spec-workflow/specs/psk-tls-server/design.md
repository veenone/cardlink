# Design Document: PSK-TLS Admin Server

## Technical Approach

### Overview

The PSK-TLS Admin Server is implemented as a multi-threaded Python server that handles TLS 1.2 connections using Pre-Shared Key (PSK) authentication. The server implements the GlobalPlatform Amendment B HTTP Admin protocol for Remote Application Management (RAM) over HTTPS.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PSK-TLS Admin Server                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   CLI Entry     │───▶│   AdminServer   │───▶│  EventEmitter   │         │
│  │   (Click)       │    │   (Main Class)  │    │  (Pub/Sub)      │         │
│  └─────────────────┘    └────────┬────────┘    └─────────────────┘         │
│                                  │                                          │
│                    ┌─────────────┴─────────────┐                           │
│                    ▼                           ▼                           │
│         ┌─────────────────┐         ┌─────────────────┐                    │
│         │  TLSHandler     │         │ SessionManager  │                    │
│         │  (PSK-TLS 1.2)  │         │ (State Mgmt)    │                    │
│         └────────┬────────┘         └────────┬────────┘                    │
│                  │                           │                              │
│                  ▼                           ▼                              │
│         ┌─────────────────┐         ┌─────────────────┐                    │
│         │  HTTPHandler    │         │  KeyStore       │                    │
│         │  (GP Admin)     │         │  (PSK Keys)     │                    │
│         └────────┬────────┘         └─────────────────┘                    │
│                  │                                                          │
│                  ▼                                                          │
│         ┌─────────────────┐                                                │
│         │  GPCommandProc  │                                                │
│         │  (APDU Handler) │                                                │
│         └─────────────────┘                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          ┌─────────────────┐                 ┌─────────────────┐
          │  Error Handler  │                 │ Metrics Collector│
          │  (Negative Cases)│                 │ (Observability)  │
          └─────────────────┘                 └─────────────────┘
```

### Key Design Decisions

1. **Multi-threaded Connection Handling**: Each incoming TLS connection is handled in a separate thread to support concurrent connections (up to 10). ThreadPoolExecutor manages the thread pool.

2. **PSK Callback Architecture**: The sslpsk3 library requires a callback function to resolve PSK identities to keys. This callback is registered during SSL context creation.

3. **Configurable Cipher Suites**: Cipher suites are configured via YAML or CLI flags, with production-grade suites enabled by default and NULL suites disabled by default (require explicit opt-in).

4. **Session State Machine**: Sessions progress through states: `HANDSHAKING` → `CONNECTED` → `ACTIVE` → `CLOSED`. State transitions emit events for dashboard integration.

5. **Error Handler Chain**: Dedicated error handlers for connection interruption, PSK mismatch, and handshake failures. Each handler logs, emits events, and performs cleanup.

## Component Design

### Component 1: AdminServer

**Purpose**: Main server class that orchestrates all components and manages the server lifecycle.

**Interface**:
```python
class AdminServer:
    """PSK-TLS Admin Server for GP Amendment B RAM over HTTP."""

    def __init__(
        self,
        config: ServerConfig,
        key_store: KeyStore,
        event_emitter: EventEmitter,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize server with dependencies."""

    def start(self) -> None:
        """Start the server and begin accepting connections."""

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop the server, closing all sessions."""

    def get_active_sessions(self) -> List[Session]:
        """Return list of currently active sessions."""

    @property
    def is_running(self) -> bool:
        """Check if server is currently running."""
```

**Key Behaviors**:
- Creates SSL context with PSK support on initialization
- Binds to configured port and accepts connections in main thread
- Delegates connection handling to ThreadPoolExecutor
- Graceful shutdown closes all sessions within timeout
- Emits `server_started` and `server_stopped` events

### Component 2: TLSHandler

**Purpose**: Manages PSK-TLS connection establishment, cipher suite negotiation, and TLS-level error handling.

**Interface**:
```python
class TLSHandler:
    """Handles PSK-TLS 1.2 connection establishment."""

    def __init__(
        self,
        key_store: KeyStore,
        allowed_ciphers: List[str],
        handshake_timeout: float = 30.0
    ):
        """Initialize TLS handler with key store and cipher config."""

    def create_ssl_context(self) -> ssl.SSLContext:
        """Create configured SSL context with PSK support."""

    def wrap_socket(
        self,
        sock: socket.socket,
        client_addr: Tuple[str, int]
    ) -> Tuple[ssl.SSLSocket, TLSSessionInfo]:
        """Wrap socket with TLS, return wrapped socket and session info."""

    def handle_handshake_error(
        self,
        error: Exception,
        client_addr: Tuple[str, int],
        partial_state: Optional[HandshakeState]
    ) -> TLSAlert:
        """Process handshake error and return appropriate TLS alert."""
```

**Cipher Suite Configuration**:
```python
@dataclass
class CipherConfig:
    """Cipher suite configuration."""

    # Production-grade (enabled by default)
    production: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_AES_128_CBC_SHA256",
        "TLS_PSK_WITH_AES_256_CBC_SHA384"
    ])

    # Legacy compatibility (optional)
    legacy: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_AES_128_CBC_SHA",
        "TLS_PSK_WITH_AES_256_CBC_SHA"
    ])

    # Testing only - no encryption (disabled by default)
    testing: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_NULL_SHA",
        "TLS_PSK_WITH_NULL_SHA256"
    ])

    enable_legacy: bool = False
    enable_null_ciphers: bool = False  # DANGER: No encryption
```

**Key Behaviors**:
- PSK callback resolves identity to key via KeyStore
- Logs warning when NULL cipher suites are enabled
- Tracks partial handshake state for debugging interrupted handshakes
- Sends appropriate TLS alerts on errors before closing

### Component 3: HTTPHandler

**Purpose**: Parses HTTP requests according to GP Amendment B Admin protocol and routes to command processor.

**Interface**:
```python
class HTTPHandler:
    """Handles GP Amendment B HTTP Admin protocol."""

    CONTENT_TYPE = "application/vnd.globalplatform.card-content-mgt;version=1.0"

    def __init__(self, command_processor: GPCommandProcessor):
        """Initialize with GP command processor."""

    def handle_request(
        self,
        ssl_socket: ssl.SSLSocket,
        session: Session
    ) -> HTTPResponse:
        """Read HTTP request, process, and return response."""

    def parse_admin_request(
        self,
        raw_request: bytes
    ) -> AdminRequest:
        """Parse raw HTTP bytes into AdminRequest."""

    def build_admin_response(
        self,
        apdu_responses: List[APDUResponse]
    ) -> bytes:
        """Build GP Admin format response body."""
```

**Key Behaviors**:
- Validates Content-Type header (returns 415 if invalid)
- Extracts APDU commands from GP Admin request body
- Wraps APDU responses in GP Admin response format
- Handles HTTP keep-alive for session continuity

### Component 4: GPCommandProcessor

**Purpose**: Processes GlobalPlatform APDU commands and generates responses.

**Interface**:
```python
class GPCommandProcessor:
    """Processes GlobalPlatform card management commands."""

    def __init__(
        self,
        response_handlers: Dict[int, ResponseHandler],
        event_emitter: EventEmitter
    ):
        """Initialize with command-specific handlers."""

    def process_command(
        self,
        apdu: APDUCommand,
        session: Session
    ) -> APDUResponse:
        """Process APDU command and return response."""

    def register_handler(
        self,
        ins_code: int,
        handler: ResponseHandler
    ) -> None:
        """Register handler for specific INS code."""
```

**Supported Commands**:
| INS | Command | Handler |
|-----|---------|---------|
| 0xA4 | SELECT | SelectHandler |
| 0xE6 | INSTALL | InstallHandler |
| 0xE4 | DELETE | DeleteHandler |
| 0xF2 | GET STATUS | GetStatusHandler |
| 0x50 | INITIALIZE UPDATE | InitUpdateHandler |
| 0x82 | EXTERNAL AUTHENTICATE | ExtAuthHandler |

**Key Behaviors**:
- Logs command bytes, response bytes, status word, and timing
- Emits `apdu_received` and `apdu_sent` events
- Delegates to registered handlers by INS code
- Returns appropriate SW for unknown commands (6D00)

### Component 5: SessionManager

**Purpose**: Manages OTA session lifecycle, state tracking, and resource cleanup.

**Interface**:
```python
class SessionManager:
    """Manages OTA session lifecycle."""

    def __init__(
        self,
        session_timeout: float = 300.0,
        event_emitter: EventEmitter
    ):
        """Initialize with timeout configuration."""

    def create_session(
        self,
        psk_identity: str,
        client_addr: Tuple[str, int],
        cipher_suite: str
    ) -> Session:
        """Create new session with unique ID."""

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID."""

    def close_session(
        self,
        session_id: str,
        reason: CloseReason
    ) -> SessionSummary:
        """Close session and return summary."""

    def cleanup_expired(self) -> List[str]:
        """Close all expired sessions, return list of closed IDs."""
```

**Session State Machine**:
```
    ┌──────────────┐
    │  HANDSHAKING │
    └──────┬───────┘
           │ TLS handshake complete
           ▼
    ┌──────────────┐
    │  CONNECTED   │
    └──────┬───────┘
           │ First HTTP request
           ▼
    ┌──────────────┐
    │   ACTIVE     │◀──────┐
    └──────┬───────┘       │
           │               │ APDU exchange
           │               │
           └───────────────┘
           │
           │ Timeout / Close / Error
           ▼
    ┌──────────────┐
    │   CLOSED     │
    └──────────────┘
```

**Key Behaviors**:
- Generates UUID-based session IDs
- Background timer checks for expired sessions every 30s
- Tracks all APDU exchanges within session
- Emits `session_created`, `session_active`, `session_ended` events
- Cleanup releases all resources within 5 seconds

### Component 6: KeyStore

**Purpose**: Abstract interface for PSK key storage and retrieval.

**Interface**:
```python
class KeyStore(ABC):
    """Abstract interface for PSK key storage."""

    @abstractmethod
    def get_key(self, identity: str) -> Optional[bytes]:
        """Retrieve PSK key for given identity, None if not found."""

    @abstractmethod
    def identity_exists(self, identity: str) -> bool:
        """Check if PSK identity exists in store."""


class FileKeyStore(KeyStore):
    """File-based PSK key storage (YAML format)."""

    def __init__(self, key_file: Path):
        """Load keys from YAML file."""


class DatabaseKeyStore(KeyStore):
    """Database-backed PSK key storage."""

    def __init__(self, db_session: Session):
        """Initialize with database session."""
```

**Key File Format**:
```yaml
# psk_keys.yaml
keys:
  - identity: "UICC_001"
    key: "0123456789ABCDEF0123456789ABCDEF"  # Hex encoded
  - identity: "UICC_002"
    key: "FEDCBA9876543210FEDCBA9876543210"
```

**Key Behaviors**:
- Keys stored as hex strings, converted to bytes on load
- Database implementation uses Card repository
- Never logs key values in plaintext
- Supports hot-reload of key file (optional)

### Component 7: ErrorHandler

**Purpose**: Handles negative cases including connection interruption, PSK mismatch, and handshake failures.

**Interface**:
```python
class ErrorHandler:
    """Handles error conditions and negative cases."""

    def __init__(
        self,
        event_emitter: EventEmitter,
        metrics_collector: MetricsCollector,
        mismatch_threshold: int = 3,
        mismatch_window: float = 60.0
    ):
        """Initialize with event and metrics dependencies."""

    def handle_connection_interrupted(
        self,
        session: Session,
        last_command: Optional[APDUCommand]
    ) -> None:
        """Handle TCP connection interruption."""

    def handle_psk_mismatch(
        self,
        identity: str,
        client_addr: Tuple[str, int]
    ) -> TLSAlert:
        """Handle PSK key mismatch, return TLS alert to send."""

    def handle_handshake_interrupted(
        self,
        client_addr: Tuple[str, int],
        partial_state: HandshakeState,
        reason: str
    ) -> None:
        """Handle TLS handshake interruption."""

    def check_error_rate(self) -> bool:
        """Check if error rate exceeds threshold, emit alert if so."""
```

**PSK Mismatch Tracking**:
```python
@dataclass
class MismatchTracker:
    """Tracks PSK mismatches by source IP."""

    counts: Dict[str, List[float]] = field(default_factory=dict)

    def record(self, client_ip: str, timestamp: float) -> int:
        """Record mismatch, return count in window."""

    def check_threshold(
        self,
        client_ip: str,
        threshold: int,
        window: float
    ) -> bool:
        """Check if mismatches exceed threshold in window."""
```

**Key Behaviors**:
- Connection interruption detected via socket exception or timeout
- PSK mismatch triggers TLS alert 51 (decrypt_error)
- Tracks mismatch frequency per source IP for misconfiguration detection
- Handshake timeout logs partial state (last message type received)
- Error rate monitoring emits `high_error_rate` event when threshold exceeded

### Component 8: EventEmitter

**Purpose**: Pub/sub event system for dashboard integration and monitoring.

**Interface**:
```python
class EventEmitter:
    """Event publication for real-time updates."""

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event to all subscribers."""

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """Subscribe to event type, return subscription ID."""

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove subscription."""
```

**Event Types**:
| Event | Data Fields |
|-------|-------------|
| `server_started` | port, ciphers, timestamp |
| `server_stopped` | reason, timestamp |
| `tls_handshake_start` | client_addr, timestamp |
| `tls_handshake_complete` | session_id, psk_identity, cipher_suite, timestamp |
| `handshake_interrupted` | client_addr, reason, partial_state, timestamp |
| `apdu_received` | session_id, command_hex, timestamp |
| `apdu_sent` | session_id, response_hex, sw, timing_ms, timestamp |
| `session_ended` | session_id, duration, command_count, status, timestamp |
| `connection_interrupted` | session_id, last_command, timestamp |
| `psk_mismatch` | identity, client_addr, timestamp |
| `high_error_rate` | error_type, rate, threshold, timestamp |

## Data Models

### Configuration

```python
@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8443

    # TLS configuration
    cipher_config: CipherConfig = field(default_factory=CipherConfig)
    handshake_timeout: float = 30.0

    # Session configuration
    session_timeout: float = 300.0
    socket_timeout: float = 60.0

    # Key store configuration
    key_store_type: str = "file"  # "file" or "database"
    key_file_path: Optional[Path] = None

    # Threading
    max_connections: int = 10

    # Error handling
    psk_mismatch_threshold: int = 3
    psk_mismatch_window: float = 60.0
    error_rate_threshold: float = 0.5  # 50% error rate triggers alert


@dataclass
class TLSSessionInfo:
    """TLS session information."""

    psk_identity: str
    cipher_suite: str
    tls_version: str
    client_addr: Tuple[str, int]
    handshake_duration_ms: float


@dataclass
class Session:
    """OTA session state."""

    id: str
    psk_identity: str
    client_addr: Tuple[str, int]
    cipher_suite: str
    state: SessionState
    created_at: datetime
    last_activity: datetime
    command_count: int = 0
    commands: List[APDUExchange] = field(default_factory=list)


@dataclass
class APDUExchange:
    """Single APDU command/response exchange."""

    command: APDUCommand
    response: APDUResponse
    timestamp: datetime
    duration_ms: float


@dataclass
class SessionSummary:
    """Session summary for logging and events."""

    session_id: str
    psk_identity: str
    duration_seconds: float
    command_count: int
    final_status: str
    close_reason: CloseReason


class SessionState(Enum):
    """Session state machine states."""

    HANDSHAKING = "handshaking"
    CONNECTED = "connected"
    ACTIVE = "active"
    CLOSED = "closed"


class CloseReason(Enum):
    """Reason for session closure."""

    NORMAL = "normal"
    TIMEOUT = "timeout"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    SERVER_SHUTDOWN = "server_shutdown"


@dataclass
class HandshakeState:
    """Partial handshake state for debugging."""

    client_hello_received: bool = False
    server_hello_sent: bool = False
    client_key_exchange_received: bool = False
    finished_received: bool = False
    last_message_type: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
```

### TLS Alerts

```python
class TLSAlert(Enum):
    """TLS Alert codes."""

    CLOSE_NOTIFY = 0
    UNEXPECTED_MESSAGE = 10
    BAD_RECORD_MAC = 20
    HANDSHAKE_FAILURE = 40
    DECRYPT_ERROR = 51  # Used for PSK mismatch
    PROTOCOL_VERSION = 70
    INSUFFICIENT_SECURITY = 71
    INTERNAL_ERROR = 80
    USER_CANCELED = 90
```

## Error Handling Strategy

### Connection Interruption

```
TCP Connection Lost
        │
        ▼
┌───────────────────┐
│ Detect via socket │
│ exception/timeout │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Log: session_id,  │
│ last_cmd, timestamp│
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Emit: connection_ │
│ interrupted event │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Cleanup session   │
│ resources (<5s)   │
└───────────────────┘
```

### PSK Mismatch

```
PSK Callback Returns Wrong Key
              │
              ▼
    ┌───────────────────┐
    │ TLS MAC validation│
    │ fails             │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Log: identity,    │
    │ client_addr (NO   │
    │ key values!)      │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Track mismatch    │
    │ for this source   │
    └────────┬──────────┘
             │
    ┌────────┴────────┐
    │ Multiple in 60s?│
    └────────┬────────┘
       Yes   │   No
    ┌────────┴────────┐
    ▼                 ▼
┌─────────┐     ┌─────────┐
│Log warn:│     │ Normal  │
│misconfig│     │ handling│
└────┬────┘     └────┬────┘
     │               │
     └───────┬───────┘
             ▼
    ┌───────────────────┐
    │ Emit: psk_mismatch│
    │ event             │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Send TLS Alert 51 │
    │ (decrypt_error)   │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Close connection  │
    └───────────────────┘
```

### Handshake Interruption

```
Handshake Message Timeout/Lost
              │
              ▼
    ┌───────────────────┐
    │ Wait handshake    │
    │ timeout (30s)     │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Log: client_addr, │
    │ partial state,    │
    │ last msg type     │
    └────────┬──────────┘
             │
    ┌────────┴────────┐
    │ ClientHello only?│
    └────────┬────────┘
       Yes   │   No
    ┌────────┴────────┐
    ▼                 ▼
┌─────────┐     ┌─────────┐
│Log: pot-│     │Log: hand│
│ential   │     │shake    │
│network  │     │failure  │
│issue    │     │         │
└────┬────┘     └────┬────┘
     │               │
     └───────┬───────┘
             ▼
    ┌───────────────────┐
    │ Emit: handshake_  │
    │ interrupted event │
    └────────┬──────────┘
             │
             ▼
    ┌───────────────────┐
    │ Close socket      │
    │ (no TLS alert -   │
    │  handshake failed)│
    └───────────────────┘
```

## File Structure

```
src/cardlink/server/
├── __init__.py                 # Public API exports
├── admin_server.py             # AdminServer main class
├── tls_handler.py              # TLSHandler, CipherConfig
├── http_handler.py             # HTTPHandler, AdminRequest/Response
├── gp_command_processor.py     # GPCommandProcessor, handlers
├── session_manager.py          # SessionManager, Session, SessionState
├── key_store.py                # KeyStore ABC, FileKeyStore, DatabaseKeyStore
├── error_handler.py            # ErrorHandler, MismatchTracker
├── event_emitter.py            # EventEmitter
├── config.py                   # ServerConfig, all config dataclasses
└── models.py                   # Data models (TLSSessionInfo, APDUExchange, etc.)
```

## Dependencies

### Internal Dependencies

| Module | Depends On |
|--------|------------|
| `admin_server` | `tls_handler`, `http_handler`, `session_manager`, `key_store`, `event_emitter`, `error_handler` |
| `tls_handler` | `key_store`, `config` |
| `http_handler` | `gp_command_processor`, `session_manager` |
| `gp_command_processor` | `event_emitter`, protocol layer (`cardlink.protocol.apdu`) |
| `session_manager` | `event_emitter`, `config` |
| `error_handler` | `event_emitter`, observability layer (`cardlink.observability.metrics`) |

### External Dependencies

| Library | Purpose |
|---------|---------|
| `sslpsk3` | PSK-TLS support |
| `pyyaml` | YAML configuration parsing |
| `click` | CLI framework |

### Optional Dependencies

| Library | Purpose |
|---------|---------|
| `sqlalchemy` | Database key store backend |
| `prometheus-client` | Metrics export |

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| `TLSHandler` | Cipher configuration, PSK callback, error handling |
| `HTTPHandler` | Request parsing, content-type validation, response formatting |
| `GPCommandProcessor` | Command routing, handler dispatch, timing |
| `SessionManager` | State transitions, timeout handling, cleanup |
| `KeyStore` | Key retrieval, identity validation |
| `ErrorHandler` | Alert generation, mismatch tracking, rate detection |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_psk_handshake` | Full PSK-TLS handshake with valid key |
| `test_psk_mismatch` | Handshake failure with wrong key |
| `test_null_cipher` | Handshake with NULL cipher suite (when enabled) |
| `test_session_timeout` | Session expiration after timeout |
| `test_connection_interrupt` | Handling of TCP disconnect mid-session |
| `test_concurrent_sessions` | Multiple simultaneous connections |

### Mock Strategy

```python
# Mock key store for testing
class MockKeyStore(KeyStore):
    def __init__(self, keys: Dict[str, bytes]):
        self._keys = keys

    def get_key(self, identity: str) -> Optional[bytes]:
        return self._keys.get(identity)

    def identity_exists(self, identity: str) -> bool:
        return identity in self._keys


# Mock event emitter for testing
class MockEventEmitter(EventEmitter):
    def __init__(self):
        self.events: List[Tuple[str, Dict]] = []

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        self.events.append((event_type, data))
```

## Performance Considerations

1. **Thread Pool Sizing**: Default 10 threads matches max concurrent connection requirement. Configurable for different workloads.

2. **PSK Key Caching**: FileKeyStore caches keys in memory after initial load. Hot-reload support uses file modification time check.

3. **Session Cleanup Timer**: Background timer runs every 30 seconds to avoid constant expiration checking on every request.

4. **Event Queue**: EventEmitter uses asyncio queue for non-blocking event distribution to multiple subscribers.

5. **Socket Timeouts**: Configured socket timeout (60s) prevents indefinite blocking on slow clients.

## Security Considerations

1. **Key Protection**: PSK keys never logged in plaintext. Only identity logged on mismatch.

2. **NULL Cipher Warning**: Server logs prominent warning at startup when NULL ciphers enabled. Each NULL cipher connection logged.

3. **Session Isolation**: Each session has isolated state. No cross-session data access.

4. **Input Validation**: All HTTP input validated before processing. Invalid requests rejected immediately.

5. **TLS Alerts**: Proper TLS alerts sent before closing connections to indicate failure reason without exposing sensitive details.
