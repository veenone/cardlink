# Network Simulator Integration API Reference

## Overview

The Network Simulator Integration module provides a Python API for controlling and monitoring network simulators like Amarisoft Callbox. This reference documents all classes, methods, and events.

## Table of Contents

- [Quick Start](#quick-start)
- [SimulatorManager](#simulatormanager)
- [Sub-Managers](#sub-managers)
  - [UEManager](#uemanager)
  - [SessionManager](#sessionmanager)
  - [SMSManager](#smsmanager)
  - [CellManager](#cellmanager)
  - [EventManager](#eventmanager)
  - [ConfigManager](#configmanager)
- [TriggerManager](#triggermanager)
- [ScenarioRunner](#scenariorunner)
- [Connection Classes](#connection-classes)
- [Types and Enums](#types-and-enums)
- [Events](#events)
- [Exceptions](#exceptions)

## Quick Start

```python
import asyncio
from cardlink.netsim import SimulatorManager, SimulatorConfig, SimulatorType

async def main():
    # Create configuration
    config = SimulatorConfig(
        url="wss://callbox.local:9001",
        simulator_type=SimulatorType.AMARISOFT,
        api_key="your-api-key"
    )

    # Create manager and connect
    manager = SimulatorManager(config)
    await manager.connect()

    try:
        # Wait for UE registration
        ue = await manager.ue.wait_for_registration(
            "001010123456789",
            timeout=60
        )
        print(f"UE registered: {ue.imsi}, IP: {ue.ip_address}")

        # Send OTA trigger SMS
        msg_id = await manager.sms.send_ota_trigger(
            ue.imsi,
            tar=bytes.fromhex("000001")
        )
        print(f"Trigger sent: {msg_id}")

    finally:
        await manager.disconnect()

asyncio.run(main())
```

## SimulatorManager

The main entry point for all simulator operations.

### Constructor

```python
SimulatorManager(config: SimulatorConfig)
```

**Parameters:**
- `config` - Configuration object with connection details

### Methods

#### connect()

```python
async def connect() -> None
```

Establish connection to the simulator and authenticate if API key provided.

**Raises:**
- `ConnectionError` - If connection fails
- `AuthenticationError` - If authentication fails

**Example:**
```python
manager = SimulatorManager(config)
await manager.connect()
```

#### disconnect()

```python
async def disconnect() -> None
```

Gracefully disconnect from the simulator.

#### get_status()

```python
async def get_status() -> SimulatorStatus
```

Get comprehensive simulator status.

**Returns:** `SimulatorStatus` with connection state, cell info, UE count

**Example:**
```python
status = await manager.get_status()
print(f"Connected: {status.connected}")
print(f"Cell status: {status.cell_status}")
print(f"UE count: {status.ue_count}")
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_connected` | `bool` | Connection state |
| `ue` | `UEManager` | UE management interface |
| `sessions` | `SessionManager` | Session management interface |
| `sms` | `SMSManager` | SMS operations interface |
| `cell` | `CellManager` | Cell control interface |
| `events` | `EventManager` | Event tracking interface |
| `config` | `ConfigManager` | Configuration interface |
| `triggers` | `TriggerManager` | Network event triggers |

## Sub-Managers

### UEManager

Manages UE (User Equipment) registration and tracking.

#### list_ues()

```python
async def list_ues() -> list[UEInfo]
```

List all connected UEs.

**Returns:** List of `UEInfo` objects

**Example:**
```python
ues = await manager.ue.list_ues()
for ue in ues:
    print(f"IMSI: {ue.imsi}, Status: {ue.status}, IP: {ue.ip_address}")
```

#### get_ue()

```python
async def get_ue(imsi: str) -> Optional[UEInfo]
```

Get specific UE by IMSI.

**Parameters:**
- `imsi` - 15-digit IMSI

**Returns:** `UEInfo` or `None` if not found

#### wait_for_registration()

```python
async def wait_for_registration(
    imsi: str,
    timeout: float = 60.0
) -> Optional[UEInfo]
```

Wait for a UE to register.

**Parameters:**
- `imsi` - IMSI to wait for
- `timeout` - Maximum wait time in seconds

**Returns:** `UEInfo` when registered, `None` on timeout

**Example:**
```python
ue = await manager.ue.wait_for_registration(
    "001010123456789",
    timeout=120
)
if ue:
    print(f"UE registered with IP: {ue.ip_address}")
else:
    print("Registration timeout")
```

#### detach_ue()

```python
async def detach_ue(imsi: str) -> bool
```

Force detach a UE from the network.

**Parameters:**
- `imsi` - IMSI to detach

**Returns:** `True` if successful

### SessionManager

Manages data sessions (PDN connections).

#### list_sessions()

```python
async def list_sessions(imsi: Optional[str] = None) -> list[DataSession]
```

List data sessions, optionally filtered by IMSI.

**Parameters:**
- `imsi` - Optional IMSI filter

**Returns:** List of `DataSession` objects

#### get_session()

```python
async def get_session(session_id: str) -> Optional[DataSession]
```

Get specific session by ID.

#### wait_for_session()

```python
async def wait_for_session(
    imsi: str,
    timeout: float = 30.0
) -> Optional[DataSession]
```

Wait for a data session to be established.

#### release_session()

```python
async def release_session(session_id: str) -> bool
```

Release/tear down a data session.

### SMSManager

Manages SMS injection and OTA triggers.

#### send_mt_sms()

```python
async def send_mt_sms(imsi: str, pdu: bytes) -> str
```

Send Mobile-Terminated SMS with raw PDU.

**Parameters:**
- `imsi` - Target UE IMSI
- `pdu` - SMS PDU bytes

**Returns:** Message ID

**Example:**
```python
pdu = bytes.fromhex("0011000B911234567890F00000AA05C8329BFD06")
msg_id = await manager.sms.send_mt_sms("001010123456789", pdu)
```

#### send_ota_trigger()

```python
async def send_ota_trigger(
    imsi: str,
    tar: bytes,
    push_url: Optional[str] = None
) -> str
```

Send OTA trigger SMS to initiate admin session.

**Parameters:**
- `imsi` - Target UE IMSI
- `tar` - Toolkit Application Reference (3 bytes)
- `push_url` - Optional URL to push to UICC

**Returns:** Message ID

**Example:**
```python
msg_id = await manager.sms.send_ota_trigger(
    "001010123456789",
    tar=bytes.fromhex("B00000")
)
```

#### get_message_history()

```python
def get_message_history(limit: int = 100) -> list[SMSMessage]
```

Get recent SMS message history.

### CellManager

Controls the cell (eNB/gNB).

#### start()

```python
async def start() -> bool
```

Start the cell.

#### stop()

```python
async def stop() -> bool
```

Stop the cell.

#### get_status()

```python
async def get_status() -> CellInfo
```

Get current cell status.

**Returns:** `CellInfo` with status, PLMN, frequency, etc.

#### configure()

```python
async def configure(params: dict[str, Any]) -> bool
```

Configure cell parameters.

**Parameters:**
- `params` - Configuration dictionary

**Example:**
```python
await manager.cell.configure({
    "plmn": "310-150",
    "frequency": 1950,
    "bandwidth": 20,
    "tx_power": 23
})
```

### EventManager

Manages event tracking, correlation, and export.

#### subscribe()

```python
def subscribe(
    callback: Callable[[NetworkEvent], Awaitable[None]],
    event_type: Optional[NetworkEventType] = None
) -> Callable[[], None]
```

Subscribe to events.

**Parameters:**
- `callback` - Async function to call on events
- `event_type` - Optional filter by event type

**Returns:** Unsubscribe function

**Example:**
```python
async def on_ue_event(event):
    print(f"UE event: {event.event_type}, IMSI: {event.imsi}")

unsubscribe = manager.events.subscribe(
    on_ue_event,
    NetworkEventType.UE_ATTACHED
)

# Later: unsubscribe()
```

#### get_event_history()

```python
def get_event_history(
    limit: int = 100,
    event_type: Optional[NetworkEventType] = None,
    since: Optional[datetime] = None
) -> list[NetworkEvent]
```

Get event history with optional filtering.

#### start_correlation()

```python
async def start_correlation(name: Optional[str] = None) -> str
```

Start an event correlation session.

**Returns:** Correlation ID

**Example:**
```python
correlation_id = await manager.events.start_correlation("test_session")

# ... perform operations ...

events = await manager.events.end_correlation(correlation_id)
print(f"Captured {len(events)} events")
```

#### export_events()

```python
def export_events(
    format: str = "json",
    file_path: Optional[str] = None
) -> str
```

Export events to JSON or CSV.

**Parameters:**
- `format` - "json" or "csv"
- `file_path` - Optional file to write

**Returns:** Export data as string

### ConfigManager

Manages simulator configuration.

#### get()

```python
async def get(refresh: bool = False) -> dict[str, Any]
```

Get current configuration.

**Parameters:**
- `refresh` - Bypass cache if True

#### get_value()

```python
async def get_value(
    key: str,
    default: Any = None
) -> Any
```

Get specific config value using dot notation.

**Example:**
```python
plmn = await manager.config.get_value("cell.plmn")
frequency = await manager.config.get_value("cell.frequency", default=1950)
```

#### set()

```python
async def set(params: dict[str, Any]) -> bool
```

Update configuration.

#### load_from_file()

```python
async def load_from_file(file_path: str) -> bool
```

Load and apply configuration from YAML file.

#### save_to_file()

```python
def save_to_file(file_path: str) -> None
```

Save current configuration to YAML file.

## TriggerManager

Triggers network events programmatically.

### UE Triggers

#### trigger_paging()

```python
async def trigger_paging(
    imsi: str,
    paging_type: str = "ps"
) -> bool
```

Trigger paging for a UE.

**Parameters:**
- `imsi` - Target IMSI
- `paging_type` - "ps" or "cs"

#### trigger_detach()

```python
async def trigger_detach(
    imsi: str,
    cause: str = "reattach_required"
) -> bool
```

Trigger network-initiated detach.

#### trigger_service_request()

```python
async def trigger_service_request(
    imsi: str,
    service_type: str = "data"
) -> bool
```

Trigger service request procedure.

### Cell Triggers

#### trigger_handover()

```python
async def trigger_handover(
    imsi: str,
    target_cell: int,
    handover_type: str = "intra"
) -> bool
```

Trigger handover to target cell.

**Parameters:**
- `imsi` - UE to handover
- `target_cell` - Target cell ID
- `handover_type` - "intra", "inter", "x2", "s1"

#### trigger_cell_outage()

```python
async def trigger_cell_outage(
    duration: float = 10.0,
    cell_id: Optional[int] = None
) -> bool
```

Simulate cell outage.

#### trigger_rlf()

```python
async def trigger_rlf(imsi: str) -> bool
```

Trigger Radio Link Failure.

#### trigger_tau()

```python
async def trigger_tau(
    imsi: str,
    tau_type: str = "periodic"
) -> bool
```

Trigger Tracking Area Update.

### Custom Triggers

#### trigger_custom()

```python
async def trigger_custom(
    event_type: str,
    params: dict[str, Any]
) -> bool
```

Trigger custom network event.

## ScenarioRunner

Executes YAML-based test scenarios.

### Constructor

```python
ScenarioRunner(manager: SimulatorManager)
```

### Methods

#### run()

```python
async def run(
    scenario: Scenario,
    variables: Optional[dict[str, Any]] = None
) -> ScenarioResult
```

Execute a scenario.

**Parameters:**
- `scenario` - Scenario to execute
- `variables` - Additional variables to inject

**Returns:** `ScenarioResult` with pass/fail status and step results

**Example:**
```python
from cardlink.netsim import Scenario, ScenarioRunner

scenario = Scenario.from_file("test_scenario.yaml")
runner = ScenarioRunner(manager)
result = await runner.run(scenario, variables={"imsi": "001010123456789"})

if result.passed:
    print(f"Scenario passed in {result.duration_ms}ms")
else:
    for step in result.step_results:
        if step.status == StepStatus.FAILED:
            print(f"Step {step.step_name} failed: {step.error}")
```

#### register_action()

```python
def register_action(
    action_name: str,
    handler: Callable[[dict], Awaitable[Any]]
) -> None
```

Register custom action handler.

**Example:**
```python
async def custom_check(params):
    # Custom validation logic
    return {"valid": True}

runner.register_action("custom.check", custom_check)
```

### Scenario Class

```python
@dataclass
class Scenario:
    name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    setup: list[Step] = field(default_factory=list)
    teardown: list[Step] = field(default_factory=list)
```

#### from_yaml()

```python
@classmethod
def from_yaml(cls, yaml_content: str) -> Scenario
```

Parse scenario from YAML string.

#### from_file()

```python
@classmethod
def from_file(cls, file_path: str) -> Scenario
```

Load scenario from YAML file.

### Available Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `ue.list` | List all UEs | - |
| `ue.get` | Get UE by IMSI | `imsi` |
| `ue.wait_for_registration` | Wait for UE | `imsi`, `timeout` |
| `ue.detach` | Detach UE | `imsi` |
| `session.list` | List sessions | `imsi` (optional) |
| `session.get` | Get session | `session_id` |
| `session.release` | Release session | `session_id` |
| `sms.send` | Send SMS PDU | `imsi`, `pdu` |
| `sms.send_trigger` | Send OTA trigger | `imsi`, `tar` |
| `cell.start` | Start cell | - |
| `cell.stop` | Stop cell | - |
| `cell.status` | Get cell status | - |
| `cell.configure` | Configure cell | config params |
| `trigger.paging` | Trigger paging | `imsi`, `paging_type` |
| `trigger.handover` | Trigger handover | `imsi`, `target_cell` |
| `trigger.detach` | Trigger detach | `imsi`, `cause` |
| `wait` | Wait duration | `seconds` |
| `log` | Log message | `message`, `level` |
| `assert` | Assert condition | `condition`, `message` |

## Connection Classes

### create_connection()

```python
def create_connection(
    url: str,
    tls_config: Optional[TLSConfig] = None
) -> BaseConnection
```

Factory function to create appropriate connection.

**Supported schemes:**
- `ws://` - WebSocket
- `wss://` - WebSocket with TLS
- `tcp://` - TCP
- `tcps://` - TCP with TLS

### WSConnection

WebSocket connection for Amarisoft Remote API.

### TCPConnection

TCP connection with newline-delimited JSON.

### ReconnectManager

Handles automatic reconnection with exponential backoff.

```python
manager = ReconnectManager(
    initial_delay=1.0,
    max_delay=30.0,
    multiplier=2.0,
    max_attempts=10
)

success = await manager.reconnect(connection.connect)
```

## Types and Enums

### SimulatorType

```python
class SimulatorType(Enum):
    AMARISOFT = "amarisoft"
    GENERIC = "generic"
```

### SimulatorConfig

```python
@dataclass
class SimulatorConfig:
    url: str
    simulator_type: SimulatorType
    api_key: Optional[str] = None
    tls_config: Optional[TLSConfig] = None
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
```

### UEInfo

```python
@dataclass
class UEInfo:
    imsi: str
    status: UEStatus
    cell_id: Optional[int]
    ip_address: Optional[str]
    imei: Optional[str]
    registered_at: Optional[datetime]
```

### UEStatus

```python
class UEStatus(Enum):
    IDLE = "idle"
    REGISTERED = "registered"
    CONNECTED = "connected"
    DETACHED = "detached"
```

### DataSession

```python
@dataclass
class DataSession:
    session_id: str
    imsi: str
    apn: Optional[str]
    ip_address: Optional[str]
    qci: Optional[int]
    established_at: Optional[datetime]
```

### CellInfo

```python
@dataclass
class CellInfo:
    cell_id: int
    status: CellStatus
    plmn: Optional[str]
    frequency: Optional[int]
    bandwidth: Optional[int]
    tx_power: Optional[int]
```

### CellStatus

```python
class CellStatus(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
```

### SMSMessage

```python
@dataclass
class SMSMessage:
    message_id: str
    imsi: str
    direction: str  # "mt" or "mo"
    pdu: bytes
    status: str
    timestamp: datetime
```

### NetworkEvent

```python
@dataclass
class NetworkEvent:
    event_id: str
    event_type: NetworkEventType
    timestamp: datetime
    source: str
    data: dict[str, Any]
    imsi: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
```

## Events

### Event Types

| Event Type | Description | Payload Fields |
|------------|-------------|----------------|
| `UE_ATTACHED` | UE registered | imsi, cell_id, ip_address |
| `UE_DETACHED` | UE deregistered | imsi, cause |
| `SESSION_ESTABLISHED` | PDN connected | session_id, imsi, apn, ip |
| `SESSION_RELEASED` | PDN disconnected | session_id, imsi |
| `SMS_SENT` | SMS injected | message_id, imsi, pdu |
| `SMS_DELIVERED` | SMS delivered | message_id, imsi |
| `CELL_STARTED` | Cell activated | cell_id |
| `CELL_STOPPED` | Cell deactivated | cell_id |
| `HANDOVER_COMPLETED` | Handover done | imsi, source_cell, target_cell |

### Subscribing to Events

```python
async def handle_event(event: NetworkEvent):
    print(f"Event: {event.event_type}")
    print(f"Data: {event.data}")

# Subscribe to all events
unsubscribe = manager.events.subscribe(handle_event)

# Subscribe to specific type
unsubscribe = manager.events.subscribe(
    handle_event,
    NetworkEventType.UE_ATTACHED
)
```

## Exceptions

### Exception Hierarchy

```
NetworkSimulatorError (base)
├── ConnectionError
│   └── AuthenticationError
├── CommandError
│   └── TimeoutError
├── ConfigurationError
├── NotConnectedError
└── ResourceNotFoundError
```

### NetworkSimulatorError

Base exception for all simulator errors.

```python
class NetworkSimulatorError(Exception):
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
```

### ConnectionError

Connection-related failures.

```python
try:
    await manager.connect()
except ConnectionError as e:
    print(f"Connection failed: {e.message}")
```

### AuthenticationError

API key or credential failures.

### CommandError

Command execution failures.

### TimeoutError

Operation timeout.

### ConfigurationError

Invalid configuration.

### NotConnectedError

Operation attempted without connection.

### ResourceNotFoundError

Requested resource (UE, session) not found.
