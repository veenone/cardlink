# Design Document: Phone Controller

## Technical Approach

### Overview

The Phone Controller is implemented as a Python module that interfaces with Android devices via ADB (Android Debug Bridge). It provides device management, AT command execution, BIP event monitoring, and SMS-PP trigger capabilities through a layered architecture that separates low-level ADB communication from high-level device operations.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Phone Controller                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   CLI Entry     │───▶│ PhoneController │───▶│  EventEmitter   │         │
│  │   (Click)       │    │   (Main Class)  │    │  (Pub/Sub)      │         │
│  └─────────────────┘    └────────┬────────┘    └─────────────────┘         │
│                                  │                                          │
│              ┌───────────────────┼───────────────────┐                     │
│              │                   │                   │                     │
│              ▼                   ▼                   ▼                     │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │  DeviceManager  │ │   ATInterface   │ │  BIPMonitor     │             │
│   │  (Discovery)    │ │  (AT Commands)  │ │  (Logcat)       │             │
│   └────────┬────────┘ └────────┬────────┘ └────────┬────────┘             │
│            │                   │                   │                       │
│            │                   │                   │                       │
│            ▼                   ▼                   ▼                       │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │  DeviceInfo     │ │  SMSTrigger     │ │  LogcatParser   │             │
│   │  (Profiling)    │ │  (PDU Encode)   │ │  (Event Parse)  │             │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         ADBClient                                    │   │
│   │              (Low-level ADB Communication)                           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │  Android Device │
                            │   (via USB)     │
                            └─────────────────┘
```

### Key Design Decisions

1. **ADB as Primary Interface**: Use ADB for all device communication as it's the standard Android debugging interface, available without root for most operations.

2. **Subprocess-Based ADB**: Execute ADB commands via subprocess rather than using adb libraries to maintain compatibility and simplicity.

3. **Logcat Streaming**: Use continuous logcat streaming with filtering for real-time BIP event monitoring.

4. **AT Command Routing**: Route AT commands through multiple methods (service call, dialer codes, direct device node) based on device capabilities.

5. **Event-Driven Architecture**: All device events emit through EventEmitter for dashboard and test orchestrator integration.

6. **Profile-Based Configuration**: Store device profiles as JSON for reproducible test setups.

## Component Design

### Component 1: PhoneController

**Purpose**: Main orchestrator class that coordinates all phone control operations.

**Interface**:
```python
class PhoneController:
    """Main phone controller for Android device management."""

    def __init__(
        self,
        adb_path: str = "adb",
        event_emitter: Optional[EventEmitter] = None
    ):
        """Initialize controller with ADB path and optional event emitter."""

    async def discover_devices(self) -> List[DeviceInfo]:
        """Scan for connected ADB devices."""

    def get_device(self, serial: str) -> Optional[Device]:
        """Get device instance by serial number."""

    async def refresh_devices(self) -> None:
        """Refresh device list and status."""

    def on_device_connected(self, callback: Callable) -> None:
        """Register callback for device connection events."""

    def on_device_disconnected(self, callback: Callable) -> None:
        """Register callback for device disconnection events."""
```

**Key Behaviors**:
- Maintains registry of discovered devices
- Polls for device changes every 5 seconds
- Creates Device instances for each connected device
- Emits device_connected/disconnected events

### Component 2: ADBClient

**Purpose**: Low-level ADB command execution wrapper.

**Interface**:
```python
class ADBClient:
    """Low-level ADB command execution."""

    def __init__(self, adb_path: str = "adb"):
        """Initialize with path to ADB executable."""

    async def execute(
        self,
        command: List[str],
        serial: Optional[str] = None,
        timeout: float = 30.0
    ) -> ADBResult:
        """Execute ADB command and return result."""

    async def shell(
        self,
        command: str,
        serial: str,
        timeout: float = 30.0
    ) -> str:
        """Execute shell command on device."""

    async def get_devices(self) -> List[Dict[str, str]]:
        """List connected devices with status."""

    async def start_logcat(
        self,
        serial: str,
        filters: List[str]
    ) -> AsyncIterator[str]:
        """Start streaming logcat with filters."""

    def is_available(self) -> bool:
        """Check if ADB is available in PATH."""
```

**ADB Command Patterns**:
```python
# Device listing
adb devices -l

# Shell command
adb -s <serial> shell <command>

# Get property
adb -s <serial> shell getprop <property>

# Logcat streaming
adb -s <serial> logcat -v time <filters>

# Push/pull files
adb -s <serial> push <local> <remote>
adb -s <serial> pull <remote> <local>
```

**Key Behaviors**:
- Validates ADB availability on initialization
- Handles command timeouts
- Parses device list output
- Manages async subprocess execution

### Component 3: DeviceManager

**Purpose**: Manages device discovery, connection monitoring, and device lifecycle.

**Interface**:
```python
class DeviceManager:
    """Manages device discovery and connection state."""

    def __init__(
        self,
        adb_client: ADBClient,
        event_emitter: EventEmitter,
        poll_interval: float = 5.0
    ):
        """Initialize with ADB client and polling interval."""

    async def start_monitoring(self) -> None:
        """Start background device monitoring."""

    async def stop_monitoring(self) -> None:
        """Stop background device monitoring."""

    async def scan_devices(self) -> List[DeviceInfo]:
        """Perform one-time device scan."""

    def get_connected_devices(self) -> List[str]:
        """Get list of connected device serials."""

    def is_device_connected(self, serial: str) -> bool:
        """Check if specific device is connected."""
```

**Device States**:
```python
class DeviceState(Enum):
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"  # USB debugging not authorized
    OFFLINE = "offline"            # Device not responding
    CONNECTED = "connected"        # Ready for commands
```

**Key Behaviors**:
- Background polling thread for device changes
- Detects new connections within 5 seconds
- Detects disconnections within 5 seconds
- Emits events on state changes

### Component 4: DeviceInfo

**Purpose**: Retrieves and stores comprehensive device and UICC information.

**Interface**:
```python
class DeviceInfo:
    """Device information retrieval and profiling."""

    def __init__(self, adb_client: ADBClient, serial: str):
        """Initialize for specific device."""

    async def get_device_info(self) -> DeviceProfile:
        """Get device hardware/software information."""

    async def get_sim_info(self) -> SIMProfile:
        """Get UICC/SIM card information."""

    async def get_network_info(self) -> NetworkProfile:
        """Get network connection information."""

    async def get_full_profile(self) -> FullProfile:
        """Get complete device profile."""

    async def refresh(self) -> None:
        """Force refresh all cached information."""

    def export_json(self) -> str:
        """Export profile as JSON string."""

    @staticmethod
    def compare(profile1: FullProfile, profile2: FullProfile) -> ProfileDiff:
        """Compare two profiles and return differences."""
```

**Property Retrieval**:
```python
# Device properties (via getprop)
DEVICE_PROPS = {
    'model': 'ro.product.model',
    'manufacturer': 'ro.product.manufacturer',
    'android_version': 'ro.build.version.release',
    'api_level': 'ro.build.version.sdk',
    'build_number': 'ro.build.display.id',
    'serial': 'ro.serialno',
    'baseband': 'gsm.version.baseband',
    'kernel': 'ro.kernel.version',
}

# SIM properties (via service call or getprop)
SIM_PROPS = {
    'iccid': 'gsm.sim.iccid',
    'imsi': 'gsm.sim.imsi',  # May require root
    'operator': 'gsm.sim.operator.alpha',
    'mcc': 'gsm.sim.operator.numeric',  # MCCMNC combined
    'state': 'gsm.sim.state',
}

# IMEI retrieval methods
# Method 1: service call (most reliable)
# adb shell service call iphonesubinfo 1
# Method 2: dumpsys
# adb shell dumpsys telephony.registry | grep mDeviceId
```

**Data Models**:
```python
@dataclass
class DeviceProfile:
    model: str
    manufacturer: str
    android_version: str
    api_level: int
    build_number: str
    serial: str
    imei: str
    baseband_version: str
    kernel_version: str

@dataclass
class SIMProfile:
    status: str  # absent, locked, ready
    iccid: Optional[str]
    imsi: Optional[str]
    msisdn: Optional[str]
    spn: Optional[str]
    mcc: Optional[str]
    mnc: Optional[str]
    slot: int  # 0 or 1 for dual-SIM

@dataclass
class NetworkProfile:
    operator_name: str
    network_type: str  # LTE, 5G, etc.
    signal_strength: int  # dBm
    data_state: str  # connected, disconnected
    apn: str

@dataclass
class FullProfile:
    device: DeviceProfile
    sim: SIMProfile
    network: NetworkProfile
    timestamp: datetime
```

### Component 5: ATInterface

**Purpose**: Sends AT commands to the phone's modem and parses responses.

**Interface**:
```python
class ATInterface:
    """AT command interface for modem communication."""

    def __init__(self, adb_client: ADBClient, serial: str):
        """Initialize for specific device."""

    async def send_command(
        self,
        command: str,
        timeout: float = 5.0
    ) -> ATResponse:
        """Send AT command and return response."""

    async def check_sim_status(self) -> str:
        """Send AT+CPIN? and return status."""

    async def get_imsi(self) -> Optional[str]:
        """Send AT+CIMI and return IMSI."""

    async def get_iccid(self) -> Optional[str]:
        """Send AT+CCID and return ICCID."""

    async def send_csim(self, apdu_hex: str) -> str:
        """Send AT+CSIM command with APDU."""

    def is_available(self) -> bool:
        """Check if AT interface is accessible."""

    def requires_root(self) -> bool:
        """Check if AT access requires root."""
```

**AT Command Methods**:
```python
# Method 1: Via service call (requires permissions)
# adb shell service call phone 27 s16 "AT+CPIN?"

# Method 2: Via dialer code broadcast
# adb shell am broadcast -a android.provider.Telephony.SECRET_CODE -d android_secret_code://...

# Method 3: Direct device node (requires root)
# adb shell cat /dev/smd0
# adb shell echo "AT+CPIN?" > /dev/smd0

# Method 4: Via ril daemon
# adb shell radiooptions ...
```

**Response Parsing**:
```python
@dataclass
class ATResponse:
    command: str
    raw_response: str
    result: str  # OK, ERROR, +CME ERROR: xx
    data: Optional[str]  # Parsed response data
    success: bool
```

**Key Behaviors**:
- Tries multiple methods to find working AT interface
- Caches working method for subsequent calls
- Parses responses into structured data
- Handles timeouts and errors gracefully

### Component 6: BIPMonitor

**Purpose**: Monitors logcat for Bearer Independent Protocol events.

**Interface**:
```python
class BIPMonitor:
    """Monitors BIP (Bearer Independent Protocol) events via logcat."""

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
        event_emitter: EventEmitter
    ):
        """Initialize monitor for specific device."""

    async def start(self) -> None:
        """Start BIP event monitoring."""

    async def stop(self) -> None:
        """Stop BIP event monitoring."""

    def is_running(self) -> bool:
        """Check if monitor is active."""

    def on_event(self, callback: Callable[[BIPEvent], None]) -> None:
        """Register callback for BIP events."""
```

**Logcat Filters**:
```python
LOGCAT_FILTERS = [
    'CatService:V',      # CAT/STK events
    'StkAppService:V',   # STK application
    'BipChannel:V',      # BIP channel events
    'RIL:V',             # Radio interface layer
    'Telephony:V',       # General telephony
    'GsmCatHandler:V',   # GSM CAT handling
]

# Logcat command
# adb logcat -v time CatService:V BipChannel:V *:S
```

**BIP Event Types**:
```python
class BIPEventType(Enum):
    OPEN_CHANNEL = "open_channel"
    CLOSE_CHANNEL = "close_channel"
    SEND_DATA = "send_data"
    RECEIVE_DATA = "receive_data"
    GET_CHANNEL_STATUS = "get_channel_status"

@dataclass
class BIPEvent:
    type: BIPEventType
    timestamp: datetime
    channel_id: Optional[int]
    data: Optional[bytes]
    status: Optional[str]
    raw_log: str
```

**Key Behaviors**:
- Continuous logcat streaming with filtering
- Pattern matching to extract BIP events
- Emits parsed events to EventEmitter
- Handles logcat buffer overflow

### Component 7: LogcatParser

**Purpose**: Parses logcat lines into structured events.

**Interface**:
```python
class LogcatParser:
    """Parses logcat output into structured events."""

    def __init__(self):
        """Initialize parser with pattern matchers."""

    def parse_line(self, line: str) -> Optional[LogcatEvent]:
        """Parse single logcat line."""

    def is_bip_event(self, event: LogcatEvent) -> bool:
        """Check if event is BIP-related."""

    def extract_bip_event(self, event: LogcatEvent) -> Optional[BIPEvent]:
        """Extract BIP event details from logcat event."""
```

**Parsing Patterns**:
```python
# Logcat line format: MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: MESSAGE
LOGCAT_PATTERN = r'^(\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+)\s*:\s*(.*)$'

# BIP event patterns
BIP_PATTERNS = {
    'open_channel': r'OPEN CHANNEL.*bearer:(.*?)(?:,|$)',
    'close_channel': r'CLOSE CHANNEL.*channel:(\d+)',
    'send_data': r'SEND DATA.*channel:(\d+).*length:(\d+)',
    'receive_data': r'RECEIVE DATA.*channel:(\d+)',
}
```

### Component 8: SMSTrigger

**Purpose**: Sends SMS-PP trigger messages to initiate OTA sessions.

**Interface**:
```python
class SMSTrigger:
    """SMS-PP OTA trigger message sender."""

    def __init__(self, adb_client: ADBClient, serial: str):
        """Initialize for specific device."""

    async def send_trigger(
        self,
        template: TriggerTemplate,
        params: Dict[str, Any]
    ) -> TriggerResult:
        """Send OTA trigger using template."""

    async def send_raw_pdu(self, pdu: bytes) -> TriggerResult:
        """Send raw PDU bytes as SMS-PP."""

    def build_pdu(
        self,
        template: TriggerTemplate,
        params: Dict[str, Any]
    ) -> bytes:
        """Build PDU from template and parameters."""

    def get_templates(self) -> List[TriggerTemplate]:
        """List available trigger templates."""
```

**PDU Encoding**:
```python
@dataclass
class TriggerTemplate:
    name: str
    description: str
    pdu_template: bytes
    params: List[TemplateParam]

# SMS-PP PDU structure for OTA
# See 3GPP TS 23.040 and ETSI TS 102 225
PDU_STRUCTURE = {
    'smsc_length': 1,      # SMSC info length
    'pdu_type': 1,         # SMS-DELIVER or SMS-SUBMIT
    'oa_length': 1,        # Originating address length
    'oa_type': 1,          # Address type
    'oa_number': 'var',    # Address digits
    'pid': 1,              # Protocol identifier (0x7F for SIM Data Download)
    'dcs': 1,              # Data coding scheme
    'scts': 7,             # Service center timestamp
    'udl': 1,              # User data length
    'udh': 'var',          # User data header
    'ud': 'var',           # User data (command packet)
}
```

**Trigger Methods**:
```python
# Method 1: Via AT+CMGS (if AT interface available)
# AT+CMGS=<length>
# <PDU bytes>

# Method 2: Via content provider injection (requires root)
# adb shell content insert --uri content://sms/inbox ...

# Method 3: Via broadcast intent (limited)
# adb shell am broadcast -a android.intent.action.DATA_SMS_RECEIVED ...
```

**Key Behaviors**:
- Encodes OTA trigger as SMS-PP PDU
- Tries multiple injection methods
- Logs PDU bytes for debugging
- Returns delivery status

### Component 9: NetworkManager

**Purpose**: Manages phone network configuration.

**Interface**:
```python
class NetworkManager:
    """Manages phone network configuration."""

    def __init__(self, adb_client: ADBClient, serial: str):
        """Initialize for specific device."""

    async def enable_wifi(self) -> bool:
        """Enable WiFi radio."""

    async def disable_wifi(self) -> bool:
        """Disable WiFi radio."""

    async def connect_wifi(self, ssid: str, password: Optional[str] = None) -> bool:
        """Connect to WiFi network."""

    async def enable_mobile_data(self) -> bool:
        """Enable mobile data."""

    async def disable_mobile_data(self) -> bool:
        """Disable mobile data."""

    async def set_apn(self, apn_config: APNConfig) -> bool:
        """Configure APN settings."""

    async def set_proxy(self, host: str, port: int) -> bool:
        """Set HTTP proxy."""

    async def test_connectivity(self, url: str) -> ConnectivityResult:
        """Test connectivity to URL."""
```

**ADB Commands**:
```python
# WiFi control
# adb shell svc wifi enable
# adb shell svc wifi disable

# Mobile data control
# adb shell svc data enable
# adb shell svc data disable

# WiFi connection (requires WifiManager)
# adb shell cmd wifi connect-network <ssid> <security> <password>

# APN configuration
# adb shell content insert --uri content://telephony/carriers ...
```

### Component 10: ProfileManager

**Purpose**: Manages device configuration profiles.

**Interface**:
```python
class ProfileManager:
    """Manages device configuration profiles."""

    def __init__(self, storage_path: Path):
        """Initialize with profile storage location."""

    def save_profile(self, name: str, profile: FullProfile) -> None:
        """Save device profile to storage."""

    def load_profile(self, name: str) -> Optional[FullProfile]:
        """Load device profile from storage."""

    def list_profiles(self) -> List[str]:
        """List available profile names."""

    def delete_profile(self, name: str) -> bool:
        """Delete profile by name."""

    def compare_profiles(
        self,
        profile1: FullProfile,
        profile2: FullProfile
    ) -> ProfileDiff:
        """Compare two profiles and return differences."""

    def export_profile(self, name: str, format: str = 'json') -> str:
        """Export profile as JSON string."""

    def import_profile(self, name: str, data: str) -> None:
        """Import profile from JSON string."""
```

**Profile Storage Format**:
```json
{
    "name": "test-device-01",
    "created_at": "2024-01-15T10:30:00Z",
    "device": {
        "model": "Pixel 6",
        "manufacturer": "Google",
        "android_version": "14",
        "api_level": 34,
        "serial": "ABC123",
        "imei": "123456789012345"
    },
    "sim": {
        "status": "ready",
        "iccid": "89012345678901234567",
        "imsi": "310260123456789",
        "spn": "Test Operator"
    },
    "network": {
        "operator_name": "Test Network",
        "network_type": "LTE",
        "apn": "test.apn"
    }
}
```

## File Structure

```
src/cardlink/phone/
├── __init__.py                 # Public API exports
├── controller.py               # PhoneController main class
├── adb_client.py               # ADBClient low-level ADB wrapper
├── device_manager.py           # DeviceManager discovery/monitoring
├── device_info.py              # DeviceInfo profiling
├── at_interface.py             # ATInterface AT command handling
├── bip_monitor.py              # BIPMonitor logcat monitoring
├── logcat_parser.py            # LogcatParser event parsing
├── sms_trigger.py              # SMSTrigger PDU encoding/sending
├── network_manager.py          # NetworkManager network config
├── profile_manager.py          # ProfileManager profile storage
├── models.py                   # Data models and enums
└── exceptions.py               # Custom exceptions
```

## Dependencies

### Internal Dependencies

| Module | Depends On |
|--------|------------|
| `controller` | `device_manager`, `at_interface`, `bip_monitor`, `sms_trigger`, `network_manager` |
| `device_manager` | `adb_client`, `device_info` |
| `at_interface` | `adb_client` |
| `bip_monitor` | `adb_client`, `logcat_parser` |
| `sms_trigger` | `adb_client`, `at_interface` |
| `network_manager` | `adb_client` |

### External Dependencies

| Library | Purpose |
|---------|---------|
| `asyncio` | Async subprocess execution |
| `click` | CLI framework |

### System Dependencies

| Dependency | Purpose |
|------------|---------|
| ADB | Android Debug Bridge executable |
| USB drivers | Device connection |

## Error Handling

### Error Types

```python
class PhoneControllerError(Exception):
    """Base exception for phone controller errors."""

class ADBNotFoundError(PhoneControllerError):
    """ADB executable not found."""

class DeviceNotFoundError(PhoneControllerError):
    """Specified device not connected."""

class DeviceUnauthorizedError(PhoneControllerError):
    """Device requires USB debugging authorization."""

class ATCommandError(PhoneControllerError):
    """AT command execution failed."""

class RootRequiredError(PhoneControllerError):
    """Operation requires root access."""

class TimeoutError(PhoneControllerError):
    """Operation timed out."""
```

### Error Handling Strategy

```
Device Operation
       │
       ▼
┌──────────────┐
│ Check device │
│  connected   │
└──────┬───────┘
       │ No
       ├────────▶ Raise DeviceNotFoundError
       │ Yes
       ▼
┌──────────────┐
│Execute with  │
│   timeout    │
└──────┬───────┘
       │ Timeout
       ├────────▶ Raise TimeoutError
       │ Success
       ▼
┌──────────────┐
│Parse result  │
│              │
└──────┬───────┘
       │ Error
       ├────────▶ Raise appropriate error
       │ Success
       ▼
   Return result
```

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| `ADBClient` | Command execution, output parsing |
| `DeviceInfo` | Property retrieval, profile building |
| `ATInterface` | Command formatting, response parsing |
| `LogcatParser` | Pattern matching, event extraction |
| `SMSTrigger` | PDU encoding |
| `ProfileManager` | Save/load, comparison |

### Integration Tests

| Test | Description |
|------|-------------|
| Device discovery | Detect real connected device |
| AT command | Send AT+CPIN? and parse response |
| BIP monitoring | Capture BIP event from triggered session |
| Profile round-trip | Save profile, reload, verify identical |

### Mock Strategy

```python
class MockADBClient(ADBClient):
    """Mock ADB client for testing."""

    def __init__(self, responses: Dict[str, str]):
        self.responses = responses
        self.commands_executed = []

    async def execute(self, command, serial=None, timeout=30.0):
        self.commands_executed.append(command)
        key = ' '.join(command)
        return ADBResult(
            stdout=self.responses.get(key, ''),
            stderr='',
            return_code=0
        )
```

## Performance Considerations

1. **Async ADB Execution**: Use asyncio subprocess for non-blocking ADB commands.

2. **Logcat Buffering**: Buffer logcat lines and process in batches to reduce CPU usage.

3. **Property Caching**: Cache device properties with configurable TTL.

4. **Connection Pooling**: Reuse ADB connections where possible.

5. **Efficient Polling**: Use exponential backoff for device discovery when no devices connected.

## Security Considerations

1. **No Credential Storage**: Never store device PINs, passwords, or unlock patterns.

2. **Sensitive Data Logging**: Mask IMSI, IMEI in logs (show only last 4 digits).

3. **USB Authorization**: Require user to authorize USB debugging on device.

4. **Root Operations**: Clearly document which operations require root; don't escalate privileges silently.
