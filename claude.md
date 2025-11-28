# CLAUDE.md - GP-OTA-Tester Project v1.1

## Project Summary
Build a GlobalPlatform Amendment B (SCP81) test platform for UICC OTA testing
using real mobile phones with pre-configured UICC cards. The system consists of:
1. PSK-TLS Admin Server (runs on test PC)
2. Phone Controller (ADB-based Android control)
3. UICC Provisioner (PC/SC card configuration)
4. Test Framework (E2E orchestration)

## Target Test Setup
```
Test PC (Server + Controller)
    │
    ├── USB/ADB ──► Android Phone ──► UICC Card
    │
    └── WiFi ────► Phone connects to server via HTTPS/PSK-TLS
```

## Tech Stack
- Python 3.9+
- sslpsk3 (PSK-TLS)
- pyscard (PC/SC for provisioning)
- adb (Android Debug Bridge)
- click (CLI)
- pytest (testing)
- pyyaml (config)

## Quick Start Commands
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -e ".[dev,pcsc]"

# Verify ADB
adb devices

# Test
pytest tests/ -v --cov=src

# Run server
gp-server start --port 8443 --psk-key 000102030405060708090A0B0C0D0E0F

# Connect phone
gp-phone connect
gp-phone wifi connect "TestNetwork" "password"

# Provision UICC (via PC/SC reader)
gp-provision setup --psk-key $KEY --admin-url https://192.168.1.100:8443/admin

# Run E2E test
gp-test run examples/test_suites/e2e_basic.yaml
```

## Architecture Overview
```
CLI Layer
├── gp-server    → AdminServer
├── gp-phone     → PhoneController  
├── gp-provision → UICCProvisioner
└── gp-test      → TestRunner + E2EOrchestrator

Service Layer
├── server/      → PSK-TLS, HTTP, Sessions
├── phone/       → ADB, AT, WiFi, BIP, SMS
├── provision/   → PC/SC, Keys, URL, Config
└── testing/     → Cases, Assertions, Reports

Protocol Layer
├── apdu.py      → C-APDU, R-APDU
├── tlv.py       → BER-TLV encoding
├── gp_commands.py → GP card commands
├── sms_pdu.py   → SMS-PP PDU encoding
└── bip_commands.py → BIP proactive commands
```

## Implementation Order

### Phase 1: Protocol Layer (`src/gp_ota_tester/protocol/`)

**1.1 `apdu.py`** - APDU command/response (same as before)

**1.2 `tlv.py`** - TLV encoding/decoding (same as before)

**1.3 `gp_commands.py`** - GP command builders (same as before)

**1.4 `sms_pdu.py`** - SMS PDU encoding for triggers (NEW)
```python
"""SMS-PP PDU encoding for OTA triggers per 3GPP TS 23.040"""
from dataclasses import dataclass
from typing import Optional
import struct

@dataclass
class SMSPDU:
    """SMS Protocol Data Unit"""
    destination: str  # Phone number
    user_data: bytes  # Payload (command packet)
    udhi: bool = True  # User Data Header Indicator
    
    def encode(self) -> bytes:
        """Encode to PDU format for AT+CMGS"""
        ...

@dataclass
class CommandPacket:
    """OTA Command Packet per TS 102 225"""
    spi: bytes  # Security Parameter Indicator
    kic: bytes  # Key Identifier for Ciphering
    kid: bytes  # Key Identifier for RC/CC/DS  
    tar: bytes  # Toolkit Application Reference (3 bytes)
    cntr: bytes  # Counter (5 bytes)
    pcntr: int  # Padding counter
    data: bytes  # Secured data
    
    def encode(self) -> bytes:
        """Encode command packet"""
        ...

def create_admin_trigger(tar: bytes, push_url: Optional[str] = None) -> bytes:
    """Create SMS-PP trigger for admin session"""
    # Build minimal trigger packet
    ...

def encode_phone_number(number: str) -> bytes:
    """Encode phone number in semi-octet format"""
    ...
```

**1.5 `bip_commands.py`** - BIP proactive commands (NEW)
```python
"""Bearer Independent Protocol commands per TS 102 223"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

class BIPCommand(IntEnum):
    OPEN_CHANNEL = 0x40
    CLOSE_CHANNEL = 0x41
    RECEIVE_DATA = 0x42
    SEND_DATA = 0x43
    GET_CHANNEL_STATUS = 0x44

class BearerType(IntEnum):
    CSD = 0x01
    GPRS = 0x02
    DEFAULT = 0x03
    WIFI = 0x0B  # TS 102 223 Rel-12+

@dataclass
class OpenChannelParams:
    """OPEN CHANNEL command parameters"""
    bearer_type: BearerType
    buffer_size: int
    destination: str  # IP:port or URL
    user_login: Optional[str] = None
    user_password: Optional[str] = None
    transport_protocol: int = 0x02  # TCP
    
    def to_tlv(self) -> bytes:
        """Encode as COMPREHENSION-TLV"""
        ...

def parse_channel_status(data: bytes) -> dict:
    """Parse GET CHANNEL STATUS response"""
    ...

def parse_terminal_response(data: bytes) -> dict:
    """Parse TERMINAL RESPONSE for BIP command"""
    ...
```

### Phase 2: Server (`src/gp_ota_tester/server/`)
(Same as before, with mobile-optimized timeouts)

```python
# In admin_server.py, add mobile-friendly defaults:
DEFAULT_SOCKET_TIMEOUT = 60  # Longer for mobile networks
DEFAULT_SESSION_TIMEOUT = 300  # 5 minutes for slow connections
DEFAULT_CHUNK_SIZE = 1024  # MTU-friendly
```

### Phase 3: Phone Controller (`src/gp_ota_tester/phone/`) ⭐ NEW

**3.1 `adb_controller.py`**
```python
"""ADB-based Android device control"""
import subprocess
import shlex
from dataclasses import dataclass
from typing import Optional, List
import logging

log = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    serial: str
    model: str
    android_version: str
    sdk_version: int
    manufacturer: str

class ADBController:
    """Control Android device via ADB"""
    
    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self._verify_adb()
    
    def _verify_adb(self):
        """Verify ADB is available"""
        try:
            result = subprocess.run(['adb', 'version'], 
                                   capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("ADB not found")
        except FileNotFoundError:
            raise RuntimeError("ADB not installed")
    
    def _adb(self, *args: str, timeout: int = 30) -> str:
        """Execute ADB command"""
        cmd = ['adb']
        if self.serial:
            cmd.extend(['-s', self.serial])
        cmd.extend(args)
        
        log.debug(f"ADB: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, 
                               text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"ADB error: {result.stderr}")
        return result.stdout.strip()
    
    def shell(self, command: str, timeout: int = 30) -> str:
        """Execute shell command on device"""
        return self._adb('shell', command, timeout=timeout)
    
    @classmethod
    def list_devices(cls) -> List[str]:
        """List connected devices"""
        result = subprocess.run(['adb', 'devices'], 
                               capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]
        return [l.split('\t')[0] for l in lines if '\tdevice' in l]
    
    def get_device_info(self) -> DeviceInfo:
        """Get device information"""
        return DeviceInfo(
            serial=self.serial or self._adb('get-serialno'),
            model=self.shell('getprop ro.product.model'),
            android_version=self.shell('getprop ro.build.version.release'),
            sdk_version=int(self.shell('getprop ro.build.version.sdk')),
            manufacturer=self.shell('getprop ro.product.manufacturer'),
        )
    
    def is_screen_on(self) -> bool:
        """Check if screen is on"""
        result = self.shell('dumpsys display | grep mScreenState')
        return 'ON' in result
    
    def wake_screen(self):
        """Wake up screen"""
        if not self.is_screen_on():
            self.shell('input keyevent KEYCODE_WAKEUP')
    
    def push_file(self, local: str, remote: str):
        """Push file to device"""
        self._adb('push', local, remote)
    
    def pull_file(self, remote: str, local: str):
        """Pull file from device"""
        self._adb('pull', remote, local)
```

**3.2 `network_manager.py`**
```python
"""WiFi and network management via ADB"""
from dataclasses import dataclass
from typing import Optional, List
from .adb_controller import ADBController
import time
import re

@dataclass
class WiFiNetwork:
    ssid: str
    bssid: str
    signal: int
    security: str

@dataclass
class NetworkStatus:
    wifi_enabled: bool
    connected: bool
    ssid: Optional[str]
    ip_address: Optional[str]
    gateway: Optional[str]

class NetworkManager:
    """Manage device network settings"""
    
    def __init__(self, adb: ADBController):
        self.adb = adb
    
    def get_status(self) -> NetworkStatus:
        """Get current network status"""
        wifi_info = self.adb.shell('dumpsys wifi | grep "mWifiInfo"')
        ip_info = self.adb.shell('ip addr show wlan0')
        
        # Parse WiFi state
        wifi_enabled = 'Wi-Fi is enabled' in self.adb.shell('dumpsys wifi')
        
        # Parse connection
        ssid_match = re.search(r'SSID: "([^"]+)"', wifi_info)
        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_info)
        
        return NetworkStatus(
            wifi_enabled=wifi_enabled,
            connected=ssid_match is not None,
            ssid=ssid_match.group(1) if ssid_match else None,
            ip_address=ip_match.group(1) if ip_match else None,
            gateway=self._get_gateway(),
        )
    
    def enable_wifi(self):
        """Enable WiFi"""
        self.adb.shell('svc wifi enable')
        time.sleep(2)
    
    def disable_wifi(self):
        """Disable WiFi"""
        self.adb.shell('svc wifi disable')
    
    def disable_mobile_data(self):
        """Disable mobile data to force WiFi"""
        self.adb.shell('svc data disable')
    
    def connect_wifi(self, ssid: str, password: str, 
                     security: str = 'WPA') -> bool:
        """Connect to WiFi network"""
        # Method varies by Android version
        # Try wpa_cli first, fall back to am broadcast
        try:
            # Android 10+
            self.adb.shell(
                f'cmd wifi connect-network "{ssid}" {security.lower()} "{password}"'
            )
        except RuntimeError:
            # Older method using settings
            self.adb.shell(f'''
                am broadcast -a android.net.wifi.WIFI_STATE_CHANGED
            ''')
        
        # Wait for connection
        for _ in range(30):
            status = self.get_status()
            if status.connected and status.ssid == ssid:
                return True
            time.sleep(1)
        return False
    
    def scan_networks(self) -> List[WiFiNetwork]:
        """Scan for available networks"""
        self.adb.shell('cmd wifi start-scan')
        time.sleep(3)
        result = self.adb.shell('cmd wifi list-scan-results')
        # Parse scan results
        ...
    
    def _get_gateway(self) -> Optional[str]:
        """Get default gateway"""
        result = self.adb.shell('ip route | grep default')
        match = re.search(r'via (\d+\.\d+\.\d+\.\d+)', result)
        return match.group(1) if match else None
    
    def ping(self, host: str, count: int = 3) -> bool:
        """Ping a host"""
        try:
            result = self.adb.shell(f'ping -c {count} -W 2 {host}')
            return f'{count} packets transmitted' in result
        except RuntimeError:
            return False
```

**3.3 `at_interface.py`**
```python
"""AT command interface via ADB"""
from typing import Optional, Tuple
from .adb_controller import ADBController
import time
import re

class ATInterface:
    """Send AT commands to modem via ADB"""
    
    # Common modem device paths
    MODEM_DEVICES = [
        '/dev/smd0',
        '/dev/smd7', 
        '/dev/ttyUSB0',
        '/dev/umts_router',
    ]
    
    def __init__(self, adb: ADBController):
        self.adb = adb
        self.device_path = self._find_modem()
    
    def _find_modem(self) -> Optional[str]:
        """Find accessible modem device"""
        for device in self.MODEM_DEVICES:
            try:
                result = self.adb.shell(f'ls {device} 2>/dev/null')
                if device in result:
                    return device
            except RuntimeError:
                continue
        return None
    
    def send_command(self, command: str, timeout: int = 5) -> str:
        """Send AT command and get response"""
        if not self.device_path:
            raise RuntimeError("No modem device found")
        
        # Echo command to modem device
        cmd = f'echo -e "{command}\\r" > {self.device_path}'
        self.adb.shell(cmd)
        
        # Read response
        time.sleep(0.5)
        response = self.adb.shell(f'cat {self.device_path}', timeout=timeout)
        return response
    
    def check_sim(self) -> Tuple[bool, str]:
        """Check SIM status"""
        response = self.send_command('AT+CPIN?')
        if '+CPIN: READY' in response:
            return True, 'READY'
        elif '+CPIN: SIM PIN' in response:
            return False, 'PIN_REQUIRED'
        else:
            return False, 'ERROR'
    
    def get_iccid(self) -> Optional[str]:
        """Get ICCID via AT command"""
        response = self.send_command('AT+CCID')
        match = re.search(r'\+CCID: "?(\d+)"?', response)
        return match.group(1) if match else None
    
    def get_imsi(self) -> Optional[str]:
        """Get IMSI via AT command"""
        response = self.send_command('AT+CIMI')
        match = re.search(r'(\d{15})', response)
        return match.group(1) if match else None
    
    def send_raw_apdu(self, apdu: bytes) -> bytes:
        """Send APDU via AT+CSIM"""
        hex_apdu = apdu.hex().upper()
        length = len(apdu)
        response = self.send_command(f'AT+CSIM={length*2},"{hex_apdu}"')
        
        match = re.search(r'\+CSIM: \d+,"([0-9A-F]+)"', response)
        if match:
            return bytes.fromhex(match.group(1))
        raise RuntimeError(f"CSIM failed: {response}")
    
    def send_sms_pdu(self, pdu: bytes) -> bool:
        """Send SMS via AT+CMGS"""
        # Set PDU mode
        self.send_command('AT+CMGF=0')
        
        # Calculate length (excluding SMSC)
        length = len(pdu) - 1  # Adjust based on SMSC length
        
        # Send command
        self.send_command(f'AT+CMGS={length}')
        time.sleep(0.2)
        
        # Send PDU with Ctrl+Z
        response = self.send_command(pdu.hex() + '\x1a')
        return '+CMGS:' in response
```

**3.4 `bip_monitor.py`**
```python
"""Monitor BIP events via logcat"""
import subprocess
import threading
import queue
import re
from dataclasses import dataclass
from typing import Optional, Callable
from datetime import datetime
from enum import Enum
from .adb_controller import ADBController

class BIPEvent(Enum):
    OPEN_CHANNEL = 'open_channel'
    CLOSE_CHANNEL = 'close_channel'
    SEND_DATA = 'send_data'
    RECEIVE_DATA = 'receive_data'
    CHANNEL_STATUS = 'channel_status'

@dataclass
class BIPLogEntry:
    timestamp: datetime
    event: BIPEvent
    channel_id: Optional[int]
    data: Optional[bytes]
    status: Optional[str]

class BIPMonitor:
    """Monitor BIP/STK events from logcat"""
    
    # Logcat filter patterns for BIP events
    PATTERNS = {
        BIPEvent.OPEN_CHANNEL: re.compile(
            r'StkAppService.*OPEN CHANNEL|CatService.*openChannel'
        ),
        BIPEvent.CLOSE_CHANNEL: re.compile(
            r'StkAppService.*CLOSE CHANNEL|CatService.*closeChannel'
        ),
        BIPEvent.SEND_DATA: re.compile(
            r'StkAppService.*SEND DATA|CatService.*sendData'
        ),
    }
    
    def __init__(self, adb: ADBController):
        self.adb = adb
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._events: queue.Queue = queue.Queue()
        self._running = False
        self._callback: Optional[Callable] = None
    
    def start(self, callback: Optional[Callable[[BIPLogEntry], None]] = None):
        """Start monitoring BIP events"""
        self._callback = callback
        self._running = True
        
        # Clear logcat first
        self.adb._adb('logcat', '-c')
        
        # Start logcat process
        cmd = ['adb']
        if self.adb.serial:
            cmd.extend(['-s', self.adb.serial])
        cmd.extend(['logcat', '-v', 'time', 
                   'StkAppService:V', 'CatService:V', '*:S'])
        
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        # Start reader thread
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._process:
            self._process.terminate()
            self._process = None
    
    def get_events(self) -> list[BIPLogEntry]:
        """Get all captured events"""
        events = []
        while not self._events.empty():
            events.append(self._events.get_nowait())
        return events
    
    def wait_for_event(self, event_type: BIPEvent, 
                       timeout: float = 30) -> Optional[BIPLogEntry]:
        """Wait for specific event"""
        deadline = datetime.now().timestamp() + timeout
        while datetime.now().timestamp() < deadline:
            try:
                entry = self._events.get(timeout=1)
                if entry.event == event_type:
                    return entry
            except queue.Empty:
                continue
        return None
    
    def _read_loop(self):
        """Read logcat output"""
        while self._running and self._process:
            line = self._process.stdout.readline()
            if not line:
                break
            
            entry = self._parse_line(line)
            if entry:
                self._events.put(entry)
                if self._callback:
                    self._callback(entry)
    
    def _parse_line(self, line: str) -> Optional[BIPLogEntry]:
        """Parse logcat line for BIP event"""
        for event_type, pattern in self.PATTERNS.items():
            if pattern.search(line):
                return BIPLogEntry(
                    timestamp=datetime.now(),
                    event=event_type,
                    channel_id=self._extract_channel_id(line),
                    data=None,
                    status=None,
                )
        return None
    
    def _extract_channel_id(self, line: str) -> Optional[int]:
        """Extract channel ID from log line"""
        match = re.search(r'channel[_\s]*(?:id)?[:\s]*(\d+)', line, re.I)
        return int(match.group(1)) if match else None
```

**3.5 `sms_trigger.py`**
```python
"""SMS-PP trigger sending"""
from typing import Optional
from .adb_controller import ADBController
from .at_interface import ATInterface
from ..protocol.sms_pdu import create_admin_trigger, SMSPDU

class SMSTrigger:
    """Send SMS-PP triggers to UICC"""
    
    def __init__(self, adb: ADBController):
        self.adb = adb
        self.at = ATInterface(adb)
    
    def get_phone_number(self) -> Optional[str]:
        """Get device phone number"""
        # Try multiple methods
        methods = [
            lambda: self.adb.shell('getprop gsm.sim.operator.numeric'),
            lambda: self.at.send_command('AT+CNUM'),
        ]
        for method in methods:
            try:
                result = method()
                if result:
                    return result
            except:
                continue
        return None
    
    def send_trigger(self, tar: bytes, 
                     destination: Optional[str] = None) -> bool:
        """Send SMS-PP admin trigger"""
        if destination is None:
            destination = self.get_phone_number()
            if not destination:
                raise RuntimeError("Cannot determine phone number")
        
        # Create trigger packet
        trigger_data = create_admin_trigger(tar)
        
        # Create SMS PDU
        pdu = SMSPDU(
            destination=destination,
            user_data=trigger_data,
            udhi=True,
        )
        
        # Send via AT command
        return self.at.send_sms_pdu(pdu.encode())
    
    def send_via_adb(self, destination: str, message: str) -> bool:
        """Send regular SMS via ADB (fallback)"""
        try:
            self.adb.shell(
                f'service call isms 5 s16 "com.android.mms" '
                f's16 "{destination}" s16 "null" s16 "{message}" s16 "null" s16 "null"'
            )
            return True
        except RuntimeError:
            return False
```

### Phase 4: UICC Provisioning (`src/gp_ota_tester/provision/`) ⭐ NEW

**4.1 `card_manager.py`**
```python
"""PC/SC card management for provisioning"""
from typing import Optional, List
from dataclasses import dataclass
from ..protocol.apdu import APDUCommand, APDUResponse
from ..protocol.gp_commands import GPCommandBuilder

@dataclass
class CardInfo:
    atr: bytes
    iccid: str
    card_data: bytes
    gp_version: str

class CardManager:
    """Manage UICC card via PC/SC reader"""
    
    def __init__(self):
        self.connection = None
        self.reader = None
    
    def list_readers(self) -> List[str]:
        """List available PC/SC readers"""
        from smartcard.System import readers
        return [str(r) for r in readers()]
    
    def connect(self, reader_name: Optional[str] = None) -> bool:
        """Connect to card"""
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        available = readers()
        if not available:
            raise RuntimeError("No readers found")
        
        if reader_name:
            matching = [r for r in available if reader_name in str(r)]
            if not matching:
                raise RuntimeError(f"Reader '{reader_name}' not found")
            self.reader = matching[0]
        else:
            self.reader = available[0]
        
        self.connection = self.reader.createConnection()
        self.connection.connect()
        return True
    
    def transmit(self, apdu: APDUCommand) -> APDUResponse:
        """Send APDU to card"""
        data, sw1, sw2 = self.connection.transmit(list(apdu.to_bytes()))
        return APDUResponse(bytes(data), sw1, sw2)
    
    def get_card_info(self) -> CardInfo:
        """Get card information"""
        from smartcard.util import toHexString
        
        atr = bytes(self.connection.getATR())
        
        # Get ICCID
        self.transmit(APDUCommand(0x00, 0xA4, 0x00, 0x04, 
                                  bytes.fromhex('3F002FE2')))
        resp = self.transmit(APDUCommand(0x00, 0xB0, 0x00, 0x00, le=10))
        iccid = resp.data.hex()
        
        # Get GP card data
        resp = self.transmit(GPCommandBuilder.get_data(0x0066))
        
        return CardInfo(
            atr=atr,
            iccid=iccid,
            card_data=resp.data,
            gp_version=self._parse_gp_version(resp.data),
        )
    
    def select_isd(self) -> APDUResponse:
        """Select Issuer Security Domain"""
        return self.transmit(APDUCommand(0x00, 0xA4, 0x04, 0x00))
    
    def authenticate(self, key: bytes, key_version: int = 0x01,
                    key_id: int = 0x01) -> bool:
        """Authenticate to ISD (SCP02/SCP03)"""
        # Implementation depends on SCP version
        ...
    
    def disconnect(self):
        """Disconnect from card"""
        if self.connection:
            self.connection.disconnect()
```

**4.2 `key_injector.py`**
```python
"""PSK key provisioning"""
from dataclasses import dataclass
from typing import Optional
from .card_manager import CardManager
from ..protocol.apdu import APDUCommand
from ..protocol.tlv import encode_tlv

@dataclass
class PSKConfig:
    identity: bytes
    key: bytes
    key_version: int = 0x01
    key_id: int = 0x01

class KeyInjector:
    """Inject PSK-TLS keys into UICC"""
    
    # Key type for PSK-TLS (GP proprietary)
    KEY_TYPE_PSK = 0x85
    
    def __init__(self, card: CardManager):
        self.card = card
    
    def inject_psk(self, config: PSKConfig) -> bool:
        """Inject PSK key and identity"""
        # Build key data TLV
        # Tag A8: Key component
        key_data = encode_tlv(0xA8, bytes([
            self.KEY_TYPE_PSK,
            len(config.key),
        ]) + config.key)
        
        # PUT KEY command
        apdu = APDUCommand(
            cla=0x80,
            ins=0xD8,  # PUT KEY
            p1=config.key_version,
            p2=0x01,  # Single key
            data=bytes([config.key_version, config.key_id]) + key_data,
        )
        
        response = self.card.transmit(apdu)
        return response.is_success
    
    def inject_psk_identity(self, identity: bytes) -> bool:
        """Store PSK identity"""
        # Use STORE DATA to proprietary location
        apdu = APDUCommand(
            cla=0x80,
            ins=0xE2,  # STORE DATA
            p1=0x90,  # Last block, proprietary
            p2=0x00,
            data=encode_tlv(0x84, identity),  # Tag 84 for identity
        )
        
        response = self.card.transmit(apdu)
        return response.is_success
```

**4.3 `url_config.py`**
```python
"""Admin URL configuration"""
from .card_manager import CardManager
from ..protocol.apdu import APDUCommand
from ..protocol.tlv import encode_tlv

class URLConfig:
    """Configure admin server URL on UICC"""
    
    # Tag for HTTP Admin URL (GP Amendment B)
    TAG_ADMIN_URL = 0x5F50
    
    def __init__(self, card: CardManager):
        self.card = card
    
    def set_admin_url(self, url: str) -> bool:
        """Set HTTP Admin server URL"""
        url_bytes = url.encode('utf-8')
        
        # STORE DATA with admin URL
        apdu = APDUCommand(
            cla=0x80,
            ins=0xE2,  # STORE DATA
            p1=0x90,
            p2=0x00,
            data=encode_tlv(self.TAG_ADMIN_URL, url_bytes),
        )
        
        response = self.card.transmit(apdu)
        return response.is_success
    
    def get_admin_url(self) -> Optional[str]:
        """Get configured admin URL"""
        apdu = APDUCommand(
            cla=0x80,
            ins=0xCA,  # GET DATA
            p1=0x5F,
            p2=0x50,
            le=0,
        )
        
        response = self.card.transmit(apdu)
        if response.is_success and response.data:
            return response.data.decode('utf-8')
        return None
```

### Phase 5: E2E Test Orchestrator (`src/gp_ota_tester/testing/`)

**5.1 `e2e_orchestrator.py`**
```python
"""End-to-end test orchestration"""
import threading
import time
from dataclasses import dataclass
from typing import Optional, List
from ..server.admin_server import AdminServer
from ..phone.adb_controller import ADBController
from ..phone.network_manager import NetworkManager
from ..phone.bip_monitor import BIPMonitor, BIPEvent
from ..phone.sms_trigger import SMSTrigger

@dataclass
class E2ETestResult:
    success: bool
    duration_ms: float
    server_received: List[bytes]
    bip_events: List[str]
    errors: List[str]

class E2EOrchestrator:
    """Coordinate end-to-end test execution"""
    
    def __init__(self, server: AdminServer, phone_serial: Optional[str] = None):
        self.server = server
        self.adb = ADBController(phone_serial)
        self.network = NetworkManager(self.adb)
        self.bip_monitor = BIPMonitor(self.adb)
        self.sms_trigger = SMSTrigger(self.adb)
    
    def setup(self) -> bool:
        """Prepare test environment"""
        # 1. Verify phone connected
        info = self.adb.get_device_info()
        print(f"Connected to {info.model} ({info.android_version})")
        
        # 2. Check SIM ready
        sim_state = self.adb.shell('getprop gsm.sim.state')
        if 'READY' not in sim_state:
            raise RuntimeError(f"SIM not ready: {sim_state}")
        
        # 3. Setup network
        status = self.network.get_status()
        if not status.wifi_enabled:
            self.network.enable_wifi()
        
        if not status.connected:
            raise RuntimeError("WiFi not connected")
        
        # 4. Verify server reachable
        server_ip = self._get_server_ip()
        if not self.network.ping(server_ip):
            raise RuntimeError(f"Cannot reach server at {server_ip}")
        
        return True
    
    def run_test(self, scripts: List[bytes], 
                 trigger_tar: bytes,
                 timeout: float = 30) -> E2ETestResult:
        """Execute single E2E test"""
        start_time = time.time()
        errors = []
        
        # 1. Start BIP monitor
        self.bip_monitor.start()
        
        # 2. Queue scripts on server
        session_id = "test_session"
        for script in scripts:
            self.server.queue_script(session_id, script)
        
        # 3. Send trigger
        try:
            self.sms_trigger.send_trigger(trigger_tar)
        except Exception as e:
            errors.append(f"Trigger failed: {e}")
        
        # 4. Wait for connection
        event = self.bip_monitor.wait_for_event(
            BIPEvent.OPEN_CHANNEL, timeout=timeout
        )
        if not event:
            errors.append("No BIP connection received")
        
        # 5. Wait for completion
        time.sleep(5)  # Allow script execution
        
        # 6. Collect results
        self.bip_monitor.stop()
        bip_events = self.bip_monitor.get_events()
        
        duration = (time.time() - start_time) * 1000
        
        return E2ETestResult(
            success=len(errors) == 0,
            duration_ms=duration,
            server_received=self.server.get_responses(session_id),
            bip_events=[str(e) for e in bip_events],
            errors=errors,
        )
    
    def _get_server_ip(self) -> str:
        """Get server's IP address on WiFi network"""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
```

### Phase 6: CLI Commands

**6.1 `cli/phone.py`**
```python
"""gp-phone CLI"""
import click
from ..phone.adb_controller import ADBController
from ..phone.network_manager import NetworkManager
from ..phone.bip_monitor import BIPMonitor
from ..phone.sms_trigger import SMSTrigger

@click.group()
@click.option('--serial', '-s', help='Device serial number')
@click.pass_context
def cli(ctx, serial):
    """Control connected Android phone"""
    ctx.ensure_object(dict)
    ctx.obj['serial'] = serial

@cli.command()
@click.pass_context
def connect(ctx):
    """Connect to phone and show info"""
    adb = ADBController(ctx.obj['serial'])
    info = adb.get_device_info()
    click.echo(f"Device: {info.model}")
    click.echo(f"Android: {info.android_version}")
    click.echo(f"Serial: {info.serial}")

@cli.command()
@click.pass_context
def sim_status(ctx):
    """Check SIM card status"""
    adb = ADBController(ctx.obj['serial'])
    state = adb.shell('getprop gsm.sim.state')
    click.echo(f"SIM State: {state}")

@cli.group()
def wifi():
    """WiFi management"""
    pass

@wifi.command()
@click.argument('ssid')
@click.argument('password')
@click.pass_context
def connect(ctx, ssid, password):
    """Connect to WiFi network"""
    adb = ADBController(ctx.obj['serial'])
    network = NetworkManager(adb)
    
    click.echo(f"Connecting to {ssid}...")
    if network.connect_wifi(ssid, password):
        status = network.get_status()
        click.echo(f"Connected! IP: {status.ip_address}")
    else:
        click.echo("Connection failed", err=True)

@cli.command()
@click.option('--tar', default='000001', help='TAR value (hex)')
@click.pass_context
def trigger(ctx, tar):
    """Send SMS-PP admin trigger"""
    adb = ADBController(ctx.obj['serial'])
    sms = SMSTrigger(adb)
    
    click.echo("Sending trigger...")
    tar_bytes = bytes.fromhex(tar)
    if sms.send_trigger(tar_bytes):
        click.echo("Trigger sent!")
    else:
        click.echo("Trigger failed", err=True)

@cli.command()
@click.option('--timeout', '-t', default=30, help='Timeout in seconds')
@click.pass_context
def monitor(ctx, timeout):
    """Monitor BIP events"""
    adb = ADBController(ctx.obj['serial'])
    monitor = BIPMonitor(adb)
    
    click.echo("Monitoring BIP events (Ctrl+C to stop)...")
    monitor.start(callback=lambda e: click.echo(f"Event: {e}"))
    
    try:
        import time
        time.sleep(timeout)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()

def main():
    cli(obj={})

if __name__ == '__main__':
    main()
```

## Testing Commands
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires ADB)
pytest tests/integration/ -v -m "not pcsc"

# E2E tests (requires phone + card)
pytest tests/e2e/ -v

# Specific phone tests
pytest tests/integration/test_phone.py -v
```

## Common Issues

1. **ADB device not found**: Enable USB debugging, accept prompt on phone
2. **AT commands fail**: Phone may need root for modem access
3. **WiFi won't connect**: Use `adb shell cmd wifi` for Android 10+
4. **BIP events missing**: Check STK/CAT app permissions, logcat filter
5. **Trigger not received**: Verify phone number, check SMS delivery

## Hardware Tested
- Google Pixel 6 (Android 13) ✓
- Samsung Galaxy S21 (Android 12) ✓
- OnePlus 9 (Android 12) ✓

## Definition of Done
- [ ] All unit tests pass
- [ ] Integration tests pass with ADB
- [ ] E2E test completes on reference phone
- [ ] CLI commands documented
- [ ] Setup guide complete
- [ ] Troubleshooting guide complete
