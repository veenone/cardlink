# Design Document: Mobile Simulator

## Technical Approach

### Overview

The Mobile Simulator is implemented as an asynchronous Python client that simulates UICC-initiated connections to a PSK-TLS Admin Server. It implements the GP Amendment B HTTP Admin protocol and provides configurable simulation behaviors for testing various scenarios.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TEST PC                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │  PSK-TLS Admin   │◄────────────►│ Mobile Simulator │            │
│  │     Server       │   TLS-PSK    │                  │            │
│  │                  │   HTTPS      │  ┌────────────┐  │            │
│  │  Port: 8443      │              │  │Virtual UICC│  │            │
│  │                  │              │  │ - PSK Keys │  │            │
│  │  ┌────────────┐  │              │  │ - Applets  │  │            │
│  │  │ Key Store  │  │              │  │ - State    │  │            │
│  │  └────────────┘  │              │  └────────────┘  │            │
│  └──────────────────┘              └──────────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Asynchronous Architecture**: Uses asyncio for non-blocking I/O, enabling concurrent simulator instances without thread overhead.

2. **State Machine Pattern**: Connection lifecycle managed through explicit state transitions with event emission on each transition.

3. **Virtual UICC Abstraction**: UICC simulation decoupled from connection handling, allowing different UICC profiles and behaviors.

4. **Configurable Behaviors**: Error injection and timeout simulation implemented via behavior plugins that can be enabled/disabled.

5. **CLI First**: Designed for command-line usage with YAML configuration files for complex scenarios.

## Component Design

### Component 1: MobileSimulator

**Purpose**: Main orchestrator class that manages the connection lifecycle and coordinates all components.

**Interface**:
```python
@dataclass
class SimulatorConfig:
    """Mobile simulator configuration."""
    server_host: str = "127.0.0.1"
    server_port: int = 8443
    psk_identity: str = "test_card"
    psk_key: bytes = b"\x00" * 16
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
    retry_count: int = 3
    retry_backoff: List[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])
    behavior_mode: str = "normal"  # normal, error, timeout
    response_delay_ms: int = 20
    error_rate: float = 0.0

class MobileSimulator:
    """Simulates mobile phone with UICC connecting to admin server."""

    def __init__(self, config: SimulatorConfig):
        """Initialize simulator with configuration."""

    async def connect(self) -> bool:
        """Establish PSK-TLS connection to server."""

    async def run_session(self) -> SessionResult:
        """Run complete admin session."""

    async def disconnect(self) -> None:
        """Close connection gracefully."""

    def get_statistics(self) -> SimulatorStats:
        """Get session statistics."""

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
```

**Key Behaviors**:
- Initializes VirtualUICC and PSKTLSClient components
- Manages state transitions with event emission
- Implements retry logic with exponential backoff
- Collects statistics for monitoring and debugging

### Component 2: PSKTLSClient

**Purpose**: Handles TLS-PSK connection establishment and low-level socket operations.

**Interface**:
```python
class PSKTLSClient:
    """TLS-PSK client for connecting to admin server."""

    def __init__(
        self,
        host: str,
        port: int,
        psk_identity: str,
        psk_key: bytes,
        timeout: float = 30.0,
    ):
        """Initialize TLS client with connection parameters."""

    async def connect(self) -> TLSConnectionInfo:
        """Establish TLS-PSK connection."""

    async def send(self, data: bytes) -> None:
        """Send data over TLS connection."""

    async def receive(self, max_bytes: int = 4096) -> bytes:
        """Receive data from TLS connection."""

    async def close(self) -> None:
        """Close TLS connection."""

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
```

**Key Behaviors**:
- Creates SSL context with PSK support using sslpsk3
- Configures allowed cipher suites (AES-128/256-CBC-SHA256)
- Tracks handshake timing for diagnostics
- Handles TLS alerts and connection errors

### Component 3: HTTPAdminClient

**Purpose**: Implements GP Amendment B HTTP Admin protocol over TLS connection.

**Interface**:
```python
class HTTPAdminClient:
    """HTTP Admin protocol client."""

    CONTENT_TYPE_REQUEST = "application/vnd.globalplatform.card-content-mgt-response;version=1.0"
    CONTENT_TYPE_RESPONSE = "application/vnd.globalplatform.card-content-mgt;version=1.0"

    def __init__(self, tls_client: PSKTLSClient):
        """Initialize with TLS client."""

    async def send_response(self, r_apdu: bytes) -> Optional[bytes]:
        """Send R-APDU and receive next C-APDU."""

    async def initial_request(self) -> bytes:
        """Send initial empty request, receive first C-APDU."""

    def build_request(self, body: bytes) -> bytes:
        """Build HTTP POST request."""

    def parse_response(self, response: bytes) -> Tuple[int, Dict, bytes]:
        """Parse HTTP response into status, headers, body."""
```

**Key Behaviors**:
- Builds GP Admin compliant HTTP POST requests
- Parses HTTP responses and extracts C-APDUs
- Handles session continuity via keep-alive
- Detects session completion (204 No Content)

### Component 4: VirtualUICC

**Purpose**: Simulates UICC card behavior including APDU processing and response generation.

**Interface**:
```python
@dataclass
class UICCProfile:
    """Virtual UICC profile configuration."""
    iccid: str = "8901234567890123456"
    imsi: str = "310150123456789"
    aid_isd: bytes = bytes.fromhex("A000000151000000")
    gp_version: str = "2.2.1"
    scp_version: str = "03"
    applets: List[VirtualApplet] = field(default_factory=list)

class VirtualUICC:
    """Virtual UICC card simulation."""

    def __init__(self, profile: UICCProfile):
        """Initialize with UICC profile."""

    def process_apdu(self, apdu: bytes) -> bytes:
        """Process C-APDU and return R-APDU."""

    def select_application(self, aid: bytes) -> bytes:
        """Handle SELECT command."""

    def get_status(self, scope: int, aid_filter: bytes) -> bytes:
        """Handle GET STATUS command."""

    def get_data(self, tag: int) -> bytes:
        """Handle GET DATA command."""

    @property
    def selected_aid(self) -> Optional[bytes]:
        """Get currently selected application AID."""
```

**Key Behaviors**:
- Parses ISO 7816-4 APDU format (CLA, INS, P1, P2, Lc, Data, Le)
- Routes commands to appropriate handlers based on INS byte
- Generates realistic status words (SW1 SW2)
- Tracks card state (selected application, security status)

### Component 5: GPCommandHandler

**Purpose**: Processes GlobalPlatform-specific APDU commands.

**Interface**:
```python
class GPCommandHandler:
    """Handles GlobalPlatform card management commands."""

    def handle_select(self, p1: int, p2: int, data: bytes) -> bytes:
        """Handle SELECT (INS=A4) command."""

    def handle_get_status(self, p1: int, p2: int, data: bytes) -> bytes:
        """Handle GET STATUS (INS=F2) command."""

    def handle_initialize_update(self, p1: int, p2: int, data: bytes) -> bytes:
        """Handle INITIALIZE UPDATE (INS=50) command."""

    def handle_external_authenticate(self, p1: int, p2: int, data: bytes) -> bytes:
        """Handle EXTERNAL AUTHENTICATE (INS=82) command."""

    def handle_get_data(self, p1: int, p2: int, data: bytes) -> bytes:
        """Handle GET DATA (INS=CA) command."""
```

**Supported Commands**:
| INS | Command | Description |
|-----|---------|-------------|
| 0xA4 | SELECT | Select application/file |
| 0xF2 | GET STATUS | Query card status |
| 0x50 | INITIALIZE UPDATE | Begin secure channel |
| 0x82 | EXTERNAL AUTHENTICATE | Complete secure channel |
| 0xCA | GET DATA | Retrieve data objects |
| 0xE6 | INSTALL | Install applet (simulated) |
| 0xE4 | DELETE | Delete package/applet (simulated) |
| 0xD8 | PUT KEY | Key management (simulated) |
| 0xE2 | STORE DATA | Store data objects |

### Component 6: BehaviorController

**Purpose**: Manages simulation behaviors including error injection and timeout simulation.

**Interface**:
```python
class BehaviorController:
    """Controls simulator behavior modes."""

    def __init__(self, config: BehaviorConfig):
        """Initialize with behavior configuration."""

    def should_inject_error(self) -> bool:
        """Determine if error should be injected."""

    def get_error_code(self) -> bytes:
        """Get error SW to inject."""

    def should_timeout(self) -> bool:
        """Determine if timeout should be simulated."""

    def get_timeout_delay(self) -> float:
        """Get delay in seconds for timeout simulation."""

    def get_response_delay(self) -> float:
        """Get normal response delay in seconds."""
```

**Behavior Modes**:
- **Normal**: Process commands correctly with minimal delay
- **Error**: Inject random SW errors at configured rate
- **Timeout**: Delay or drop responses at configured probability

## State Machine

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ connect()
                         ▼
                    ┌─────────┐
         ┌─────────│CONNECTING│─────────┐
         │ fail    └────┬────┘  timeout │
         ▼              │ success       ▼
    ┌─────────┐         ▼          ┌─────────┐
    │  ERROR  │    ┌─────────┐     │ TIMEOUT │
    └─────────┘    │CONNECTED│     └─────────┘
                   └────┬────┘
                        │ exchange()
                        ▼
                   ┌──────────┐
                   │EXCHANGING│◄──────┐
                   └────┬─────┘       │
                        │ more APDUs  │
                        └─────────────┘
                        │ 204 No Content
                        ▼
                   ┌─────────┐
                   │ CLOSING │
                   └────┬────┘
                        │
                        ▼
                   ┌─────────┐
                   │  IDLE   │
                   └─────────┘
```

## Protocol Flow

```
Mobile Simulator                              PSK-TLS Server
      │                                              │
      │───────── TLS ClientHello (PSK) ─────────────►│
      │                                              │
      │◄──────── TLS ServerHello (PSK) ─────────────│
      │                                              │
      │═══════ TLS-PSK Session Established ═════════│
      │                                              │
      │───── POST /admin (empty body) ──────────────►│
      │     Content-Type: GP-response                │
      │                                              │
      │◄──────── 200 OK ───────────────────────────│
      │         Content-Type: GP-request             │
      │         Body: C-APDU (SELECT ISD)            │
      │                                              │
      │      [VirtualUICC processes APDU]            │
      │                                              │
      │───── POST /admin ───────────────────────────►│
      │     Body: R-APDU (9000)                      │
      │                                              │
      │◄──────── 200 OK ───────────────────────────│
      │         Body: C-APDU (GET STATUS)            │
      │                                              │
      │      [VirtualUICC processes APDU]            │
      │                                              │
      │───── POST /admin ───────────────────────────►│
      │     Body: R-APDU (data + 9000)               │
      │                                              │
      │◄──────── 204 No Content ───────────────────│
      │         (Session Complete)                   │
      │                                              │
      │════════════ TLS Close ══════════════════════│
      │                                              │
```

## Data Models

### Configuration

```python
@dataclass
class SimulatorConfig:
    """Complete simulator configuration."""

    # Server connection
    server_host: str = "127.0.0.1"
    server_port: int = 8443
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
    retry_count: int = 3
    retry_backoff: List[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])

    # PSK credentials
    psk_identity: str = "test_card"
    psk_key: bytes = b"\x00" * 16

    # UICC profile
    uicc_profile: UICCProfile = field(default_factory=UICCProfile)

    # Behavior settings
    behavior_mode: str = "normal"
    response_delay_ms: int = 20
    error_rate: float = 0.0
    timeout_probability: float = 0.0
    connection_mode: str = "single"


@dataclass
class SessionResult:
    """Result of a completed simulation session."""

    success: bool
    session_id: str
    duration_seconds: float
    apdu_count: int
    final_sw: str
    commands: List[APDUExchange] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class APDUExchange:
    """Single APDU command/response exchange."""

    command: bytes
    response: bytes
    sw: str
    timestamp: datetime
    duration_ms: float
    ins: int
    description: str


@dataclass
class SimulatorStats:
    """Simulator session statistics."""

    # Connection stats
    connections_attempted: int = 0
    connections_succeeded: int = 0
    connections_failed: int = 0
    connection_errors: Dict[str, int] = field(default_factory=dict)

    # Session stats
    sessions_completed: int = 0
    sessions_failed: int = 0
    total_apdus_sent: int = 0
    total_apdus_received: int = 0

    # Timing stats
    avg_connection_time_ms: float = 0.0
    avg_session_duration_ms: float = 0.0
    avg_apdu_response_time_ms: float = 0.0

    # Error stats
    error_responses: Dict[str, int] = field(default_factory=dict)
    timeout_count: int = 0


class ConnectionState(Enum):
    """Simulator connection states."""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    EXCHANGING = "exchanging"
    CLOSING = "closing"
    ERROR = "error"
    TIMEOUT = "timeout"
```

## File Structure

```
src/gp_ota_tester/
└── simulator/
    ├── __init__.py           # Public API exports
    ├── client.py             # MobileSimulator main class
    ├── psk_tls_client.py     # PSK-TLS connection handling
    ├── http_client.py        # HTTP Admin protocol client
    ├── virtual_uicc.py       # UICC simulation logic
    ├── gp_commands.py        # GP command handlers
    ├── behavior.py           # Behavior controller
    ├── state_machine.py      # Connection state management
    ├── config.py             # Configuration dataclasses
    └── models.py             # Data models
```

## Configuration File Format

```yaml
# simulator.yaml
# Mobile Simulator Configuration

# Server connection settings
server:
  host: "127.0.0.1"
  port: 8443
  connect_timeout: 30.0
  read_timeout: 30.0
  retry_count: 3
  retry_backoff:
    - 1.0
    - 2.0
    - 4.0

# PSK-TLS credentials
psk:
  identity: "test_card_001"
  key: "0102030405060708090A0B0C0D0E0F10"

# Virtual UICC configuration
uicc:
  iccid: "8901234567890123456"
  imsi: "310150123456789"
  msisdn: "+14155551234"

  # GlobalPlatform settings
  gp:
    version: "2.2.1"
    scp_version: "03"
    isd_aid: "A000000151000000"

  # Pre-installed applets
  applets:
    - aid: "A0000001510001"
      name: "TestApplet"
      state: "SELECTABLE"
      privileges: "00"

# Simulation behavior
behavior:
  mode: "normal"  # normal, error, timeout
  response_delay_ms: 20

  error:
    rate: 0.1
    codes:
      - "6A82"
      - "6985"
      - "6D00"

  timeout:
    probability: 0.1
    delay_range:
      min: 1000
      max: 5000

  connection:
    mode: "single"  # single, per-command, batch, reconnect
    batch_size: 5
    reconnect_after: 3

# Logging
logging:
  level: "INFO"
  apdu_logging: true
  hex_dump: false

# Statistics collection
statistics:
  enabled: true
  report_interval: 60
```

## CLI Interface

```bash
# Start simulator with default config
gp-simulator run

# Run with specific PSK credentials
gp-simulator run \
  --server 192.168.1.100:8443 \
  --psk-identity "test_card_001" \
  --psk-key "0102030405060708090A0B0C0D0E0F10"

# Run with config file
gp-simulator run --config simulator.yaml

# Run in error injection mode
gp-simulator run --mode error --error-rate 0.1

# Run in timeout simulation mode
gp-simulator run --mode timeout --timeout-probability 0.2

# Run multiple simulated devices
gp-simulator run --count 10 --parallel

# Run continuous (loop) mode
gp-simulator run --loop --interval 5

# Show simulator status
gp-simulator status

# Generate sample config
gp-simulator config generate --output simulator.yaml
```

## Dependencies

### Required
- `sslpsk3` - PSK-TLS support
- `asyncio` - Async I/O
- `click` - CLI framework
- `pyyaml` - Configuration parsing
- `rich` - Terminal output

### Optional
- `pytest` - Testing
- `pytest-asyncio` - Async test support

## Integration with Test Framework

### Pytest Fixtures

```python
import pytest
from gp_ota_tester.simulator import MobileSimulator, SimulatorConfig

@pytest.fixture
async def simulator(admin_server):
    """Create simulator connected to test server."""
    config = SimulatorConfig(
        server_host="127.0.0.1",
        server_port=admin_server.port,
        psk_identity="test_card",
        psk_key=admin_server.test_psk_key,
    )
    sim = MobileSimulator(config)
    yield sim
    await sim.disconnect()

@pytest.fixture
async def connected_simulator(simulator):
    """Simulator with established connection."""
    await simulator.connect()
    return simulator
```

### Example Test

```python
import pytest

@pytest.mark.asyncio
async def test_basic_session(connected_simulator):
    """Test basic admin session completes successfully."""
    result = await connected_simulator.run_session()

    assert result.success
    assert result.apdu_count > 0
    assert result.final_sw == "9000"

@pytest.mark.asyncio
async def test_select_isd(connected_simulator):
    """Test SELECT ISD-R command processing."""
    result = await connected_simulator.run_session()

    # Verify SELECT was processed
    assert any(
        cmd.ins == 0xA4 and cmd.sw == "9000"
        for cmd in result.commands
    )

@pytest.mark.asyncio
async def test_error_recovery(simulator):
    """Test server handles UICC errors."""
    simulator.config.behavior_mode = "error"
    simulator.config.error_rate = 0.5

    await simulator.connect()
    result = await simulator.run_session()

    # Server should handle errors gracefully
    assert result.completed or result.error_handled
```

## Dashboard Integration

The simulator can emit events to the web dashboard:

```python
# Emit connection event
await dashboard.emit_event("simulator.connected", {
    "simulator_id": self.id,
    "server": f"{self.config.host}:{self.config.port}",
})

# Emit APDU event
await dashboard.emit_apdu(
    session_id=self.session_id,
    direction="response",  # Simulator sends R-APDUs
    data=r_apdu.hex(),
    sw=sw,
)
```
