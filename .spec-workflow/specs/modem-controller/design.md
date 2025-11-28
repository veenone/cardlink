# Design Document: Modem Controller

## Technical Approach

### Overview

The Modem Controller is implemented as a Python module that interfaces with IoT cellular modems via serial/USB communication. It provides device management, AT command execution, BIP event monitoring via URCs, and optional QXDM diagnostic integration through a layered architecture.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Modem Controller                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   CLI Entry     │───▶│ ModemController │───▶│  EventEmitter   │         │
│  │   (Click)       │    │   (Main Class)  │    │  (Pub/Sub)      │         │
│  └─────────────────┘    └────────┬────────┘    └─────────────────┘         │
│                                  │                                          │
│              ┌───────────────────┼───────────────────┐                     │
│              │                   │                   │                     │
│              ▼                   ▼                   ▼                     │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │  ModemManager   │ │   ATInterface   │ │   BIPMonitor    │             │
│   │  (Discovery)    │ │  (AT Commands)  │ │  (URC Monitor)  │             │
│   └────────┬────────┘ └────────┬────────┘ └────────┬────────┘             │
│            │                   │                   │                       │
│            │                   │                   │                       │
│            ▼                   ▼                   ▼                       │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │   ModemInfo     │ │   SMSTrigger    │ │   URCParser     │             │
│   │  (Profiling)    │ │  (PDU Encode)   │ │  (Event Parse)  │             │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│                                                                              │
│   ┌─────────────────┐ ┌─────────────────────────────────────────────────┐   │
│   │  QXDMInterface  │ │              SerialClient                        │   │
│   │  (Diagnostics)  │ │         (Low-level Serial I/O)                   │   │
│   └─────────────────┘ └─────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          ┌─────────────────┐                 ┌─────────────────┐
          │   AT Port       │                 │   DM Port       │
          │ (Serial/USB)    │                 │ (QXDM Diag)     │
          └─────────────────┘                 └─────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                            ┌─────────────────┐
                            │   IoT Modem     │
                            │ (Quectel, etc.) │
                            └─────────────────┘
```

### Key Design Decisions

1. **Serial Port Communication**: Use pyserial for cross-platform serial communication with configurable baud rate and timeouts.

2. **Async AT Command Processing**: Use asyncio with serial port for non-blocking command/response handling.

3. **URC-Based Monitoring**: Monitor Unsolicited Result Codes (URCs) in separate read thread for real-time BIP event detection.

4. **Modem Vendor Abstraction**: Abstract interface to support multiple modem vendors with vendor-specific subclasses.

5. **QXDM Optional Integration**: QXDM diagnostics as optional feature that degrades gracefully when unavailable.

6. **Port Discovery**: Automatic serial port scanning with modem identification via ATI command.

## Component Design

### Component 1: ModemController

**Purpose**: Main orchestrator class that coordinates all modem control operations.

**Interface**:
```python
class ModemController:
    """Main modem controller for IoT cellular modem management."""

    def __init__(
        self,
        event_emitter: Optional[EventEmitter] = None
    ):
        """Initialize controller with optional event emitter."""

    async def discover_modems(self) -> List[ModemInfo]:
        """Scan for connected modems on serial ports."""

    def get_modem(self, port: str) -> Optional[Modem]:
        """Get modem instance by port name."""

    async def refresh_modems(self) -> None:
        """Refresh modem list and status."""

    def on_modem_connected(self, callback: Callable) -> None:
        """Register callback for modem connection events."""

    def on_modem_disconnected(self, callback: Callable) -> None:
        """Register callback for modem disconnection events."""
```

**Key Behaviors**:
- Maintains registry of discovered modems
- Polls for modem changes every 5 seconds
- Creates Modem instances for each detected modem
- Emits modem_connected/disconnected events

### Component 2: SerialClient

**Purpose**: Low-level serial port communication wrapper.

**Interface**:
```python
class SerialClient:
    """Low-level serial port communication."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0
    ):
        """Initialize serial connection."""

    async def open(self) -> None:
        """Open serial port."""

    async def close(self) -> None:
        """Close serial port."""

    async def write(self, data: bytes) -> int:
        """Write data to serial port."""

    async def read(self, size: int = 1024) -> bytes:
        """Read data from serial port."""

    async def read_line(self, timeout: float = None) -> str:
        """Read line from serial port."""

    async def read_until(self, terminator: bytes, timeout: float = None) -> bytes:
        """Read until terminator or timeout."""

    def is_open(self) -> bool:
        """Check if port is open."""

    @staticmethod
    def list_ports() -> List[PortInfo]:
        """List available serial ports."""
```

**Port Discovery**:
```python
@dataclass
class PortInfo:
    port: str           # /dev/ttyUSB0 or COM3
    description: str    # "Quectel USB AT Port"
    hwid: str          # USB VID:PID
    manufacturer: str   # "Quectel"
    product: str       # "EG25-G"
    serial_number: str  # Module serial

# Quectel USB VID:PID mappings
QUECTEL_USB_IDS = {
    '2c7c:0125': 'EC25',
    '2c7c:0121': 'EC21',
    '2c7c:0195': 'EG25-G',
    '2c7c:0800': 'RG500Q',
    '2c7c:0801': 'RG520N',
}
```

**Key Behaviors**:
- Uses pyserial for cross-platform support
- Configurable baud rate (default 115200)
- Timeout handling for read operations
- Thread-safe for concurrent reads/writes

### Component 3: ModemManager

**Purpose**: Manages modem discovery, connection monitoring, and modem lifecycle.

**Interface**:
```python
class ModemManager:
    """Manages modem discovery and connection state."""

    def __init__(
        self,
        event_emitter: EventEmitter,
        poll_interval: float = 5.0
    ):
        """Initialize with polling interval."""

    async def start_monitoring(self) -> None:
        """Start background modem monitoring."""

    async def stop_monitoring(self) -> None:
        """Stop background modem monitoring."""

    async def scan_modems(self) -> List[ModemInfo]:
        """Perform one-time modem scan."""

    def get_connected_modems(self) -> List[str]:
        """Get list of connected modem ports."""

    def is_modem_connected(self, port: str) -> bool:
        """Check if specific modem is connected."""
```

**Modem Detection Logic**:
```python
async def _identify_modem(self, port: str) -> Optional[ModemInfo]:
    """Identify modem on serial port."""
    try:
        serial = SerialClient(port, baudrate=115200, timeout=2.0)
        await serial.open()

        # Send ATI for identification
        await serial.write(b'ATI\r\n')
        response = await serial.read_until(b'OK', timeout=2.0)

        # Parse response to determine vendor/model
        if b'Quectel' in response:
            return self._parse_quectel_info(response, port)
        elif b'Sierra' in response:
            return self._parse_sierra_info(response, port)

        return None
    finally:
        await serial.close()
```

### Component 4: ModemInfo

**Purpose**: Retrieves and stores comprehensive modem and UICC information.

**Interface**:
```python
class ModemInfo:
    """Modem information retrieval and profiling."""

    def __init__(self, at_interface: ATInterface):
        """Initialize with AT interface."""

    async def get_modem_info(self) -> ModemProfile:
        """Get modem hardware/firmware information."""

    async def get_sim_info(self) -> SIMProfile:
        """Get UICC/SIM card information."""

    async def get_network_info(self) -> NetworkProfile:
        """Get network registration and signal information."""

    async def get_full_profile(self) -> FullModemProfile:
        """Get complete modem profile."""

    async def refresh(self) -> None:
        """Force refresh all cached information."""

    def export_json(self) -> str:
        """Export profile as JSON string."""
```

**AT Commands for Information**:
```python
MODEM_INFO_COMMANDS = {
    'manufacturer': 'AT+CGMI',
    'model': 'AT+CGMM',
    'firmware': 'AT+CGMR',
    'imei': 'AT+CGSN',
}

SIM_INFO_COMMANDS = {
    'status': 'AT+CPIN?',
    'iccid': 'AT+QCCID',      # Quectel specific
    'iccid_alt': 'AT+CCID',   # Standard
    'imsi': 'AT+CIMI',
    'msisdn': 'AT+CNUM',
}

NETWORK_INFO_COMMANDS = {
    'registration': 'AT+CREG?',
    'eps_registration': 'AT+CEREG?',
    'operator': 'AT+COPS?',
    'signal_csq': 'AT+CSQ',
    'signal_qcsq': 'AT+QCSQ',  # Quectel detailed
    'pdp_context': 'AT+CGDCONT?',
}
```

**Data Models**:
```python
@dataclass
class ModemProfile:
    manufacturer: str
    model: str
    firmware_version: str
    imei: str
    serial_number: str
    module_type: str
    supported_bands: List[str]

@dataclass
class SIMProfile:
    status: str  # READY, SIM PIN, etc.
    iccid: Optional[str]
    imsi: Optional[str]
    msisdn: Optional[str]
    spn: Optional[str]
    mcc: Optional[str]
    mnc: Optional[str]

@dataclass
class NetworkProfile:
    registration_status: str
    operator_name: str
    network_type: str  # LTE, NR5G
    rssi: int
    rsrp: Optional[int]
    rsrq: Optional[int]
    sinr: Optional[int]
    cell_id: str
    tac: str
    apn: str

@dataclass
class FullModemProfile:
    modem: ModemProfile
    sim: SIMProfile
    network: NetworkProfile
    timestamp: datetime
```

### Component 5: ATInterface

**Purpose**: Sends AT commands and parses responses with URC handling.

**Interface**:
```python
class ATInterface:
    """AT command interface for modem communication."""

    def __init__(
        self,
        serial_client: SerialClient,
        urc_callback: Optional[Callable] = None
    ):
        """Initialize with serial client and optional URC handler."""

    async def send_command(
        self,
        command: str,
        timeout: float = 5.0,
        expect_response: bool = True
    ) -> ATResponse:
        """Send AT command and return response."""

    async def send_raw(self, data: bytes) -> None:
        """Send raw bytes (for PDU mode)."""

    def register_urc_handler(
        self,
        pattern: str,
        callback: Callable
    ) -> None:
        """Register handler for specific URC pattern."""

    async def start_urc_monitoring(self) -> None:
        """Start background URC monitoring."""

    async def stop_urc_monitoring(self) -> None:
        """Stop background URC monitoring."""
```

**AT Response Parsing**:
```python
@dataclass
class ATResponse:
    command: str
    raw_response: str
    result: ATResult  # OK, ERROR, CME_ERROR, CMS_ERROR
    data: List[str]   # Parsed response lines
    error_code: Optional[int]
    success: bool

class ATResult(Enum):
    OK = "OK"
    ERROR = "ERROR"
    CME_ERROR = "+CME ERROR"
    CMS_ERROR = "+CMS ERROR"
    TIMEOUT = "TIMEOUT"
    NO_RESPONSE = "NO_RESPONSE"
```

**URC Handling**:
```python
# Common URCs to monitor
URC_PATTERNS = {
    r'\+CREG: (\d)': 'network_registration',
    r'\+CEREG: (\d)': 'eps_registration',
    r'\+CPIN: (.+)': 'sim_status',
    r'\+QSTK: (.+)': 'stk_event',      # Quectel STK
    r'\+STKPCI: (.+)': 'stk_proactive', # STK proactive command
    r'\+QIND: (.+)': 'indication',     # Quectel indication
}
```

**Key Behaviors**:
- Command/response synchronization with timeout
- Background thread for URC monitoring
- Queue URCs for processing
- Support for multi-line responses

### Component 6: BIPMonitor

**Purpose**: Monitors for BIP (Bearer Independent Protocol) events via URCs and STK notifications.

**Interface**:
```python
class BIPMonitor:
    """Monitors BIP events via modem URCs."""

    def __init__(
        self,
        at_interface: ATInterface,
        event_emitter: EventEmitter
    ):
        """Initialize monitor with AT interface."""

    async def start(self) -> None:
        """Start BIP event monitoring."""

    async def stop(self) -> None:
        """Stop BIP event monitoring."""

    def is_running(self) -> bool:
        """Check if monitor is active."""

    async def enable_stk_notifications(self) -> None:
        """Enable STK/USAT URC notifications."""
```

**STK Command Detection**:
```python
# Proactive commands related to BIP
STK_BIP_COMMANDS = {
    0x40: 'OPEN_CHANNEL',
    0x41: 'CLOSE_CHANNEL',
    0x42: 'RECEIVE_DATA',
    0x43: 'SEND_DATA',
    0x44: 'GET_CHANNEL_STATUS',
}

async def _process_stk_event(self, urc_data: str) -> Optional[BIPEvent]:
    """Parse STK URC into BIP event."""
    # Parse proactive command TLV
    # Extract command type and parameters
    # Return BIPEvent if BIP-related
```

**Key Behaviors**:
- Enable STK notifications via AT+QSTK=1 (Quectel)
- Parse proactive command TLVs
- Emit BIP events to EventEmitter
- Correlate with OTA sessions

### Component 7: URCParser

**Purpose**: Parses Unsolicited Result Codes into structured events.

**Interface**:
```python
class URCParser:
    """Parses modem URCs into structured events."""

    def __init__(self):
        """Initialize parser with pattern matchers."""

    def parse(self, line: str) -> Optional[URCEvent]:
        """Parse URC line into event."""

    def is_urc(self, line: str) -> bool:
        """Check if line is a URC."""

    def register_pattern(
        self,
        pattern: str,
        event_type: str,
        parser: Callable
    ) -> None:
        """Register custom URC pattern."""
```

**URC Event Types**:
```python
@dataclass
class URCEvent:
    type: str
    timestamp: datetime
    raw_line: str
    data: Dict[str, Any]

# Example events
# +CREG: 1,1 -> URCEvent(type='network_registration', data={'stat': 1, 'lac': None})
# +QSTK: "D0..."  -> URCEvent(type='stk_proactive', data={'pdu': 'D0...'})
```

### Component 8: SMSTrigger

**Purpose**: Sends SMS-PP trigger messages in PDU mode.

**Interface**:
```python
class SMSTrigger:
    """SMS-PP OTA trigger message sender."""

    def __init__(self, at_interface: ATInterface):
        """Initialize with AT interface."""

    async def send_trigger(
        self,
        template: TriggerTemplate,
        params: Dict[str, Any]
    ) -> TriggerResult:
        """Send OTA trigger using template."""

    async def send_raw_pdu(self, pdu: bytes) -> TriggerResult:
        """Send raw PDU bytes as SMS-PP."""

    async def configure_pdu_mode(self) -> bool:
        """Set modem to PDU mode (AT+CMGF=0)."""
```

**PDU Mode SMS Sending**:
```python
async def _send_pdu(self, pdu: bytes) -> TriggerResult:
    """Send SMS via AT+CMGS in PDU mode."""
    # Ensure PDU mode
    await self.at_interface.send_command('AT+CMGF=0')

    # Calculate TPDU length (excluding SMSC)
    tpdu_length = len(pdu) - 1 - pdu[0]  # Subtract SMSC length

    # Send AT+CMGS=<length>
    response = await self.at_interface.send_command(
        f'AT+CMGS={tpdu_length}',
        timeout=5.0,
        expect_response=False
    )

    # Wait for > prompt
    # Send PDU bytes + Ctrl+Z
    await self.at_interface.send_raw(pdu.hex().encode() + b'\x1a')

    # Wait for +CMGS: <mr> response
    result = await self.at_interface.read_response(timeout=60.0)

    return TriggerResult(
        success='+CMGS:' in result,
        message_reference=self._parse_mr(result),
        raw_response=result
    )
```

### Component 9: QXDMInterface

**Purpose**: Optional QXDM diagnostic integration for Qualcomm-based modems.

**Interface**:
```python
class QXDMInterface:
    """QXDM diagnostic interface for Qualcomm modems."""

    def __init__(self, dm_port: str):
        """Initialize with diagnostic port."""

    async def connect(self) -> bool:
        """Connect to DM port."""

    async def disconnect(self) -> None:
        """Disconnect from DM port."""

    def is_available(self) -> bool:
        """Check if QXDM interface is available."""

    async def start_logging(self, log_codes: List[int]) -> None:
        """Start diagnostic logging for specified codes."""

    async def stop_logging(self) -> None:
        """Stop diagnostic logging."""

    async def export_log(self, filepath: str, format: str = 'isf') -> None:
        """Export captured logs to file."""

    def get_dm_port(self) -> Optional[str]:
        """Find DM port for connected modem."""
```

**Diagnostic Port Detection**:
```python
# Quectel modems expose multiple USB interfaces:
# - AT port (ttyUSB2 typically)
# - DM port (ttyUSB0 typically)
# - NMEA port (ttyUSB1 typically)

QUECTEL_PORT_FUNCTIONS = {
    0: 'DM',     # Diagnostic/QXDM
    1: 'NMEA',   # GPS NMEA
    2: 'AT',     # AT commands
    3: 'PPP',    # Data/PPP
}
```

**Key Behaviors**:
- Auto-detect DM port from USB interface mapping
- Support common QXDM log codes for OTA/BIP debugging
- Export to ISF/DLF format for QXDM analysis
- Graceful degradation when QXDM unavailable

### Component 10: NetworkManager

**Purpose**: Manages modem network configuration and data connection.

**Interface**:
```python
class NetworkManager:
    """Manages modem network configuration."""

    def __init__(self, at_interface: ATInterface):
        """Initialize with AT interface."""

    async def configure_apn(
        self,
        apn: str,
        username: str = '',
        password: str = '',
        auth_type: str = 'NONE'
    ) -> bool:
        """Configure APN settings."""

    async def activate_pdp(self, cid: int = 1) -> bool:
        """Activate PDP context."""

    async def deactivate_pdp(self, cid: int = 1) -> bool:
        """Deactivate PDP context."""

    async def get_ip_address(self, cid: int = 1) -> Optional[str]:
        """Get assigned IP address."""

    async def check_registration(self) -> RegistrationStatus:
        """Check network registration status."""

    async def ping(self, host: str, count: int = 4) -> PingResult:
        """Ping host via modem (AT+QPING for Quectel)."""
```

**AT Commands**:
```python
# PDP Context configuration
# AT+CGDCONT=<cid>,"IP","<apn>"
# AT+CGAUTH=<cid>,<auth_type>,"<password>","<username>"

# PDP activation
# AT+CGACT=1,<cid>

# IP address query
# AT+CGPADDR=<cid>

# Quectel data activation
# AT+QIACT=<cid>

# Quectel ping
# AT+QPING=<cid>,"<host>"[,<timeout>][,<count>]
```

### Component 11: QuectelModem

**Purpose**: Quectel-specific modem implementation with vendor commands.

**Interface**:
```python
class QuectelModem(Modem):
    """Quectel-specific modem implementation."""

    async def get_detailed_signal(self) -> QuectelSignalInfo:
        """Get detailed signal info via AT+QCSQ."""

    async def configure_bands(self, bands: List[str]) -> bool:
        """Configure LTE bands via AT+QCFG='band'."""

    async def enable_stk(self) -> bool:
        """Enable STK via AT+QSTK=1."""

    async def get_qeng_info(self) -> QEngInfo:
        """Get engineering mode info via AT+QENG."""

    async def send_ussd(self, code: str) -> str:
        """Send USSD via AT+CUSD."""
```

**Quectel-Specific AT Commands**:
```python
QUECTEL_COMMANDS = {
    'signal_detail': 'AT+QCSQ',      # Detailed signal: RSSI, RSRP, SINR, RSRQ
    'engineering': 'AT+QENG="servingcell"',  # Serving cell info
    'band_config': 'AT+QCFG="band"', # Band configuration
    'stk_enable': 'AT+QSTK=1',       # Enable STK URCs
    'network_scan': 'AT+QSCAN=3',    # Network scan
    'gps_enable': 'AT+QGPS=1',       # Enable GPS
}
```

## File Structure

```
src/cardlink/modem/
├── __init__.py                 # Public API exports
├── controller.py               # ModemController main class
├── serial_client.py            # SerialClient low-level serial I/O
├── modem_manager.py            # ModemManager discovery/monitoring
├── modem_info.py               # ModemInfo profiling
├── at_interface.py             # ATInterface command handling
├── urc_parser.py               # URCParser event parsing
├── bip_monitor.py              # BIPMonitor URC-based monitoring
├── sms_trigger.py              # SMSTrigger PDU encoding/sending
├── network_manager.py          # NetworkManager network config
├── qxdm_interface.py           # QXDMInterface diagnostics
├── profile_manager.py          # ProfileManager profile storage
├── vendors/                    # Vendor-specific implementations
│   ├── __init__.py
│   ├── base.py                 # Base Modem class
│   ├── quectel.py              # QuectelModem
│   └── sierra.py               # SierraModem (future)
├── models.py                   # Data models and enums
└── exceptions.py               # Custom exceptions
```

## Dependencies

### Internal Dependencies

| Module | Depends On |
|--------|------------|
| `controller` | `modem_manager`, `at_interface`, `bip_monitor`, `network_manager` |
| `modem_manager` | `serial_client`, `modem_info`, `vendors` |
| `at_interface` | `serial_client`, `urc_parser` |
| `bip_monitor` | `at_interface`, `urc_parser` |
| `sms_trigger` | `at_interface` |
| `qxdm_interface` | `serial_client` |

### External Dependencies

| Library | Purpose |
|---------|---------|
| `pyserial` | Serial port communication |
| `asyncio` | Async I/O |
| `click` | CLI framework |

## Error Handling

### Error Types

```python
class ModemControllerError(Exception):
    """Base exception for modem controller errors."""

class ModemNotFoundError(ModemControllerError):
    """Specified modem not connected."""

class SerialPortError(ModemControllerError):
    """Serial port communication error."""

class ATCommandError(ModemControllerError):
    """AT command execution failed."""

class ATTimeoutError(ModemControllerError):
    """AT command timed out."""

class CMEError(ATCommandError):
    """+CME ERROR from modem."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

class CMSError(ATCommandError):
    """+CMS ERROR from modem."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
```

### CME/CMS Error Codes

```python
CME_ERRORS = {
    0: 'Phone failure',
    3: 'Operation not allowed',
    4: 'Operation not supported',
    5: 'PH-SIM PIN required',
    10: 'SIM not inserted',
    11: 'SIM PIN required',
    12: 'SIM PUK required',
    13: 'SIM failure',
    16: 'Incorrect password',
    30: 'No network service',
    100: 'Unknown error',
}

CMS_ERRORS = {
    301: 'SMS service reserved',
    302: 'Operation not allowed',
    303: 'Operation not supported',
    304: 'Invalid PDU mode parameter',
    305: 'Invalid text mode parameter',
    321: 'Invalid memory index',
    322: 'SIM memory full',
}
```

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| `SerialClient` | Port listing, read/write operations |
| `ATInterface` | Command formatting, response parsing, URC detection |
| `URCParser` | Pattern matching, event extraction |
| `SMSTrigger` | PDU encoding |
| `ModemInfo` | AT response parsing |

### Integration Tests

| Test | Description |
|------|-------------|
| Modem discovery | Detect real connected modem |
| AT command | Send ATI and parse response |
| SIM status | Query AT+CPIN? |
| Network registration | Monitor AT+CREG |

### Mock Strategy

```python
class MockSerialClient(SerialClient):
    """Mock serial client for testing."""

    def __init__(self, responses: Dict[str, str]):
        self.responses = responses
        self.written_data = []

    async def write(self, data: bytes) -> int:
        self.written_data.append(data)
        return len(data)

    async def read_until(self, terminator: bytes, timeout: float = None) -> bytes:
        command = self.written_data[-1].decode().strip()
        return self.responses.get(command, b'ERROR\r\n')
```

## Performance Considerations

1. **Serial Buffer Management**: Read serial data in chunks, buffer until complete response.

2. **URC Thread**: Dedicated thread for URC monitoring to avoid blocking main AT interface.

3. **Command Queuing**: Queue AT commands to prevent concurrent access to serial port.

4. **Timeout Tuning**: Different timeouts for different operations (quick: 2s, network: 180s).

5. **Port Caching**: Cache port information to avoid repeated scanning.

## Security Considerations

1. **No PIN Storage**: Never persist SIM PIN codes.

2. **Sensitive Data Logging**: Mask IMSI, IMEI in logs (show only last 4 digits).

3. **Port Permissions**: Document required permissions for serial port access (dialout group on Linux).

4. **QXDM Access**: Document QXDM license requirements for Qualcomm diagnostics.
