# Design Document: Network Simulator Integration

## Introduction

This document describes the technical design for the Network Simulator Integration component of CardLink. The component provides connectivity to network simulators like Amarisoft Callbox via WebSocket/TCP APIs, enabling controlled network environment testing for SCP81 OTA validation.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CardLink Application                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Test Orchestrator                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │   │
│  │  │ScenarioRunner│ │ StepExecutor│ │EventCorrelator│                   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                    Network Simulator Manager                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │ │
│  │  │ UEManager   │ │SessionManager│ │ SMSManager  │ │EventManager │    │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │ │
│  │  ┌─────────────┐ ┌─────────────┐                                     │ │
│  │  │ CellManager │ │ConfigManager│                                     │ │
│  │  └─────────────┘ └─────────────┘                                     │ │
│  └─────────────────────────────────┬─────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                    Simulator Abstraction Layer                        │ │
│  │  ┌───────────────────────────────────────────────────────────────┐   │ │
│  │  │                    SimulatorInterface                          │   │ │
│  │  └───────────────────────────────────────────────────────────────┘   │ │
│  │          │                              │                             │ │
│  │  ┌───────┴───────┐              ┌───────┴───────┐                    │ │
│  │  │AmarisoftAdapter│              │ GenericAdapter │                    │ │
│  │  └───────────────┘              └───────────────┘                    │ │
│  └─────────────────────────────────┬─────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                      Connection Layer                                 │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                     │ │
│  │  │WSConnection │ │TCPConnection│ │ReconnectMgr │                     │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                     │ │
│  └─────────────────────────────────┬─────────────────────────────────────┘ │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Network Simulator                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Amarisoft Callbox                                 │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │   │
│  │  │   eNB     │ │   gNB     │ │   MME     │ │   AMF     │           │   │
│  │  │  (LTE)    │ │  (5G NR)  │ │   EPC     │ │   5GC     │           │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility |
|-----------|----------------|
| **SimulatorManager** | Central coordinator for all simulator operations |
| **SimulatorInterface** | Abstract interface for simulator adapters |
| **AmarisoftAdapter** | Amarisoft-specific API implementation |
| **WSConnection** | WebSocket connection management |
| **TCPConnection** | TCP fallback connection |
| **ReconnectManager** | Connection recovery with backoff |
| **UEManager** | UE registration tracking |
| **SessionManager** | Data session management |
| **SMSManager** | SMS injection and monitoring |
| **CellManager** | Cell control operations |
| **ConfigManager** | Network configuration management |
| **EventManager** | Event subscription and distribution |
| **ScenarioRunner** | Test scenario execution |
| **EventCorrelator** | Cross-component event correlation |

## Component Design

### 1. SimulatorManager

Central manager for network simulator operations.

```python
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio

class SimulatorType(Enum):
    AMARISOFT = 'amarisoft'
    GENERIC = 'generic'

@dataclass
class SimulatorConfig:
    """Network simulator configuration."""
    url: str
    simulator_type: SimulatorType = SimulatorType.AMARISOFT
    protocol: str = 'websocket'  # websocket or tcp
    api_key: Optional[str] = None
    tls_enabled: bool = False
    reconnect_enabled: bool = True
    reconnect_max_attempts: int = 10
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    command_timeout: float = 5.0

class SimulatorManager:
    """Central manager for network simulator integration."""

    def __init__(self, config: SimulatorConfig,
                 event_emitter: Optional['EventEmitter'] = None):
        self.config = config
        self._event_emitter = event_emitter
        self._adapter: Optional['SimulatorInterface'] = None
        self._connection: Optional['BaseConnection'] = None
        self._reconnect_manager: Optional['ReconnectManager'] = None
        self._connected = False

        # Sub-managers
        self._ue_manager: Optional['UEManager'] = None
        self._session_manager: Optional['SessionManager'] = None
        self._sms_manager: Optional['SMSManager'] = None
        self._cell_manager: Optional['CellManager'] = None
        self._config_manager: Optional['ConfigManager'] = None
        self._event_manager: Optional['EventManager'] = None

    async def connect(self) -> bool:
        """Connect to network simulator."""
        # Create connection based on protocol
        if self.config.protocol == 'websocket':
            self._connection = WSConnection(
                url=self.config.url,
                tls_enabled=self.config.tls_enabled
            )
        else:
            self._connection = TCPConnection(
                url=self.config.url,
                tls_enabled=self.config.tls_enabled
            )

        # Setup reconnection
        if self.config.reconnect_enabled:
            self._reconnect_manager = ReconnectManager(
                connection=self._connection,
                max_attempts=self.config.reconnect_max_attempts,
                base_delay=self.config.reconnect_base_delay,
                max_delay=self.config.reconnect_max_delay
            )

        # Connect
        try:
            await self._connection.connect()

            # Create adapter
            self._adapter = self._create_adapter()

            # Authenticate if required
            if self.config.api_key:
                await self._adapter.authenticate(self.config.api_key)

            # Initialize sub-managers
            self._init_managers()

            self._connected = True

            if self._event_emitter:
                self._event_emitter.emit('simulator_connected', {
                    'url': self.config.url,
                    'type': self.config.simulator_type.value
                })

            return True

        except Exception as e:
            if self._event_emitter:
                self._event_emitter.emit('simulator_error', {
                    'error': str(e),
                    'phase': 'connect'
                })
            return False

    async def disconnect(self) -> None:
        """Disconnect from network simulator."""
        if self._connection:
            await self._connection.disconnect()
            self._connected = False

            if self._event_emitter:
                self._event_emitter.emit('simulator_disconnected', {
                    'url': self.config.url
                })

    def _create_adapter(self) -> 'SimulatorInterface':
        """Create simulator adapter based on type."""
        if self.config.simulator_type == SimulatorType.AMARISOFT:
            return AmarisoftAdapter(self._connection)
        else:
            return GenericAdapter(self._connection)

    def _init_managers(self) -> None:
        """Initialize sub-managers."""
        self._ue_manager = UEManager(self._adapter, self._event_emitter)
        self._session_manager = SessionManager(self._adapter, self._event_emitter)
        self._sms_manager = SMSManager(self._adapter, self._event_emitter)
        self._cell_manager = CellManager(self._adapter, self._event_emitter)
        self._config_manager = ConfigManager(self._adapter)
        self._event_manager = EventManager(self._adapter, self._event_emitter)

        # Start event monitoring
        asyncio.create_task(self._event_manager.start_monitoring())

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def ue(self) -> 'UEManager':
        return self._ue_manager

    @property
    def sessions(self) -> 'SessionManager':
        return self._session_manager

    @property
    def sms(self) -> 'SMSManager':
        return self._sms_manager

    @property
    def cell(self) -> 'CellManager':
        return self._cell_manager

    @property
    def config(self) -> 'ConfigManager':
        return self._config_manager

    @property
    def events(self) -> 'EventManager':
        return self._event_manager

    async def get_status(self) -> Dict[str, Any]:
        """Get overall simulator status."""
        if not self._connected:
            return {'connected': False}

        status = {
            'connected': True,
            'url': self.config.url,
            'type': self.config.simulator_type.value
        }

        try:
            status['cell'] = await self._cell_manager.get_status()
            status['ue_count'] = len(await self._ue_manager.list_ues())
            status['session_count'] = len(await self._session_manager.list_sessions())
        except Exception as e:
            status['error'] = str(e)

        return status
```

### 2. Connection Layer

WebSocket and TCP connection implementations.

```python
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
import asyncio
import json
import websockets
import ssl

class BaseConnection(ABC):
    """Abstract base connection."""

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: dict) -> None:
        pass

    @abstractmethod
    async def receive(self) -> dict:
        pass

    @abstractmethod
    def on_message(self, callback: Callable[[dict], None]) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class WSConnection(BaseConnection):
    """WebSocket connection implementation."""

    def __init__(self, url: str, tls_enabled: bool = False):
        self.url = url
        self.tls_enabled = tls_enabled
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._message_callbacks: list = []
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        ssl_context = None
        if self.tls_enabled:
            ssl_context = ssl.create_default_context()

        self._ws = await websockets.connect(
            self.url,
            ssl=ssl_context,
            ping_interval=30,
            ping_timeout=10
        )

        # Start message receiver
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send(self, message: dict) -> None:
        """Send message over WebSocket."""
        if not self._ws:
            raise ConnectionError("Not connected")

        await self._ws.send(json.dumps(message))

    async def receive(self) -> dict:
        """Receive single message."""
        if not self._ws:
            raise ConnectionError("Not connected")

        data = await self._ws.recv()
        return json.loads(data)

    def on_message(self, callback: Callable[[dict], None]) -> None:
        """Register message callback."""
        self._message_callbacks.append(callback)

    def is_connected(self) -> bool:
        return self._ws is not None and self._ws.open

    async def _receive_loop(self) -> None:
        """Background message receiver."""
        try:
            async for message in self._ws:
                data = json.loads(message)
                for callback in self._message_callbacks:
                    try:
                        callback(data)
                    except Exception:
                        pass
        except websockets.ConnectionClosed:
            pass


class TCPConnection(BaseConnection):
    """TCP connection implementation."""

    def __init__(self, url: str, tls_enabled: bool = False):
        self.url = url
        self.tls_enabled = tls_enabled
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._message_callbacks: list = []
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish TCP connection."""
        # Parse URL for host and port
        parts = self.url.replace('tcp://', '').split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 9000

        ssl_context = None
        if self.tls_enabled:
            ssl_context = ssl.create_default_context()

        self._reader, self._writer = await asyncio.open_connection(
            host, port, ssl=ssl_context
        )

        self._receive_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self) -> None:
        """Close TCP connection."""
        if self._receive_task:
            self._receive_task.cancel()

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None

    async def send(self, message: dict) -> None:
        """Send message over TCP."""
        if not self._writer:
            raise ConnectionError("Not connected")

        data = json.dumps(message).encode() + b'\n'
        self._writer.write(data)
        await self._writer.drain()

    async def receive(self) -> dict:
        """Receive single message."""
        if not self._reader:
            raise ConnectionError("Not connected")

        line = await self._reader.readline()
        return json.loads(line.decode())

    def on_message(self, callback: Callable[[dict], None]) -> None:
        """Register message callback."""
        self._message_callbacks.append(callback)

    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def _receive_loop(self) -> None:
        """Background message receiver."""
        try:
            while True:
                line = await self._reader.readline()
                if not line:
                    break
                data = json.loads(line.decode())
                for callback in self._message_callbacks:
                    try:
                        callback(data)
                    except Exception:
                        pass
        except Exception:
            pass


class ReconnectManager:
    """Manages connection recovery with exponential backoff."""

    def __init__(self,
                 connection: BaseConnection,
                 max_attempts: int = 10,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0):
        self._connection = connection
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._attempts = 0
        self._reconnecting = False

    async def reconnect(self) -> bool:
        """Attempt reconnection with backoff."""
        if self._reconnecting:
            return False

        self._reconnecting = True
        self._attempts = 0

        while self._attempts < self._max_attempts:
            self._attempts += 1

            try:
                await self._connection.connect()
                self._reconnecting = False
                self._attempts = 0
                return True
            except Exception:
                delay = min(
                    self._base_delay * (2 ** (self._attempts - 1)),
                    self._max_delay
                )
                await asyncio.sleep(delay)

        self._reconnecting = False
        return False

    def reset(self) -> None:
        """Reset reconnection state."""
        self._attempts = 0
        self._reconnecting = False
```

### 3. Simulator Interface and Amarisoft Adapter

Abstract interface and Amarisoft implementation.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class CellStatus(Enum):
    INACTIVE = 'inactive'
    ACTIVE = 'active'
    STARTING = 'starting'
    STOPPING = 'stopping'

@dataclass
class UEInfo:
    """UE information."""
    imsi: str
    imei: Optional[str] = None
    msisdn: Optional[str] = None
    cell_id: Optional[int] = None
    registration_status: str = 'unknown'
    ip_address: Optional[str] = None
    last_activity: Optional[str] = None

@dataclass
class DataSession:
    """Data session information."""
    session_id: str
    imsi: str
    apn: str
    ip_address: str
    qos_class: Optional[int] = None
    bearer_id: Optional[int] = None
    status: str = 'active'

@dataclass
class CellInfo:
    """Cell information."""
    cell_id: int
    status: CellStatus
    plmn: str  # MCC-MNC
    tac: int
    earfcn: int
    bandwidth: int
    tx_power: float
    connected_ues: int = 0


class SimulatorInterface(ABC):
    """Abstract interface for network simulators."""

    @abstractmethod
    async def authenticate(self, api_key: str) -> bool:
        pass

    # Cell operations
    @abstractmethod
    async def get_cell_status(self) -> CellInfo:
        pass

    @abstractmethod
    async def start_cell(self) -> bool:
        pass

    @abstractmethod
    async def stop_cell(self) -> bool:
        pass

    @abstractmethod
    async def configure_cell(self, config: Dict[str, Any]) -> bool:
        pass

    # UE operations
    @abstractmethod
    async def list_ues(self) -> List[UEInfo]:
        pass

    @abstractmethod
    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        pass

    @abstractmethod
    async def detach_ue(self, imsi: str) -> bool:
        pass

    # Data session operations
    @abstractmethod
    async def list_sessions(self) -> List[DataSession]:
        pass

    @abstractmethod
    async def release_session(self, session_id: str) -> bool:
        pass

    # SMS operations
    @abstractmethod
    async def send_sms(self, imsi: str, pdu: bytes) -> bool:
        pass

    # Event operations
    @abstractmethod
    async def trigger_event(self, event_type: str, params: Dict[str, Any]) -> bool:
        pass

    # Configuration
    @abstractmethod
    async def get_config(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def set_config(self, config: Dict[str, Any]) -> bool:
        pass

    # Event subscription
    @abstractmethod
    def subscribe_events(self, callback: callable) -> None:
        pass


class AmarisoftAdapter(SimulatorInterface):
    """Amarisoft Callbox adapter."""

    def __init__(self, connection: BaseConnection):
        self._connection = connection
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._event_callbacks: List[callable] = []

        # Register message handler
        self._connection.on_message(self._handle_message)

    def _handle_message(self, message: dict) -> None:
        """Handle incoming message."""
        if 'id' in message and message['id'] in self._pending_requests:
            # Response to request
            future = self._pending_requests.pop(message['id'])
            if 'error' in message:
                future.set_exception(Exception(message['error']))
            else:
                future.set_result(message.get('result'))
        elif 'event' in message:
            # Event notification
            for callback in self._event_callbacks:
                try:
                    callback(message)
                except Exception:
                    pass

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Send request and wait for response."""
        self._request_id += 1
        request_id = self._request_id

        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method
        }
        if params:
            request['params'] = params

        future = asyncio.Future()
        self._pending_requests[request_id] = future

        await self._connection.send(request)

        try:
            result = await asyncio.wait_for(future, timeout=5.0)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request {method} timed out")

    async def authenticate(self, api_key: str) -> bool:
        """Authenticate with API key."""
        result = await self._send_request('auth', {'api_key': api_key})
        return result.get('success', False)

    async def get_cell_status(self) -> CellInfo:
        """Get cell status."""
        result = await self._send_request('enb.get_status')

        return CellInfo(
            cell_id=result.get('cell_id', 0),
            status=CellStatus(result.get('status', 'inactive')),
            plmn=f"{result.get('mcc', '001')}-{result.get('mnc', '01')}",
            tac=result.get('tac', 0),
            earfcn=result.get('earfcn', 0),
            bandwidth=result.get('bandwidth', 20),
            tx_power=result.get('tx_power', 0),
            connected_ues=result.get('ue_count', 0)
        )

    async def start_cell(self) -> bool:
        """Start cell."""
        result = await self._send_request('enb.start')
        return result.get('success', False)

    async def stop_cell(self) -> bool:
        """Stop cell."""
        result = await self._send_request('enb.stop')
        return result.get('success', False)

    async def configure_cell(self, config: Dict[str, Any]) -> bool:
        """Configure cell parameters."""
        result = await self._send_request('enb.configure', config)
        return result.get('success', False)

    async def list_ues(self) -> List[UEInfo]:
        """List connected UEs."""
        result = await self._send_request('ue.list')

        return [
            UEInfo(
                imsi=ue.get('imsi', ''),
                imei=ue.get('imei'),
                msisdn=ue.get('msisdn'),
                cell_id=ue.get('cell_id'),
                registration_status=ue.get('status', 'unknown'),
                ip_address=ue.get('ip_address'),
                last_activity=ue.get('last_activity')
            )
            for ue in result.get('ues', [])
        ]

    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get specific UE info."""
        result = await self._send_request('ue.get', {'imsi': imsi})

        if not result:
            return None

        return UEInfo(
            imsi=result.get('imsi', ''),
            imei=result.get('imei'),
            msisdn=result.get('msisdn'),
            cell_id=result.get('cell_id'),
            registration_status=result.get('status', 'unknown'),
            ip_address=result.get('ip_address'),
            last_activity=result.get('last_activity')
        )

    async def detach_ue(self, imsi: str) -> bool:
        """Detach UE from network."""
        result = await self._send_request('ue.detach', {'imsi': imsi})
        return result.get('success', False)

    async def list_sessions(self) -> List[DataSession]:
        """List active data sessions."""
        result = await self._send_request('session.list')

        return [
            DataSession(
                session_id=s.get('id', ''),
                imsi=s.get('imsi', ''),
                apn=s.get('apn', ''),
                ip_address=s.get('ip_address', ''),
                qos_class=s.get('qci'),
                bearer_id=s.get('bearer_id'),
                status=s.get('status', 'active')
            )
            for s in result.get('sessions', [])
        ]

    async def release_session(self, session_id: str) -> bool:
        """Release data session."""
        result = await self._send_request('session.release', {'id': session_id})
        return result.get('success', False)

    async def send_sms(self, imsi: str, pdu: bytes) -> bool:
        """Send MT-SMS."""
        result = await self._send_request('sms.send', {
            'imsi': imsi,
            'pdu': pdu.hex()
        })
        return result.get('success', False)

    async def trigger_event(self, event_type: str, params: Dict[str, Any]) -> bool:
        """Trigger network event."""
        result = await self._send_request(f'event.{event_type}', params)
        return result.get('success', False)

    async def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return await self._send_request('config.get')

    async def set_config(self, config: Dict[str, Any]) -> bool:
        """Set configuration."""
        result = await self._send_request('config.set', config)
        return result.get('success', False)

    def subscribe_events(self, callback: callable) -> None:
        """Subscribe to events."""
        self._event_callbacks.append(callback)
```

### 4. UE Manager

UE registration tracking.

```python
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

class UEManager:
    """Manages UE registration tracking."""

    def __init__(self, adapter: SimulatorInterface,
                 event_emitter: Optional['EventEmitter'] = None):
        self._adapter = adapter
        self._event_emitter = event_emitter
        self._ue_cache: Dict[str, UEInfo] = {}
        self._waiters: Dict[str, List[asyncio.Event]] = {}

        # Subscribe to UE events
        self._adapter.subscribe_events(self._handle_event)

    def _handle_event(self, event: dict) -> None:
        """Handle UE-related events."""
        event_type = event.get('event')

        if event_type == 'ue_attached':
            imsi = event.get('imsi')
            ue_info = UEInfo(
                imsi=imsi,
                imei=event.get('imei'),
                registration_status='attached',
                cell_id=event.get('cell_id')
            )
            self._ue_cache[imsi] = ue_info

            # Notify waiters
            if imsi in self._waiters:
                for waiter in self._waiters[imsi]:
                    waiter.set()

            if self._event_emitter:
                self._event_emitter.emit('ue_registered', {
                    'imsi': imsi,
                    'imei': event.get('imei'),
                    'cell_id': event.get('cell_id')
                })

        elif event_type == 'ue_detached':
            imsi = event.get('imsi')
            self._ue_cache.pop(imsi, None)

            if self._event_emitter:
                self._event_emitter.emit('ue_deregistered', {
                    'imsi': imsi,
                    'cause': event.get('cause')
                })

    async def list_ues(self) -> List[UEInfo]:
        """List all connected UEs."""
        ues = await self._adapter.list_ues()
        # Update cache
        self._ue_cache = {ue.imsi: ue for ue in ues}
        return ues

    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get specific UE info."""
        # Try cache first
        if imsi in self._ue_cache:
            return self._ue_cache[imsi]

        # Fetch from simulator
        return await self._adapter.get_ue(imsi)

    async def wait_for_registration(self, imsi: str,
                                    timeout: float = 60.0) -> bool:
        """Wait for specific IMSI to register."""
        # Check if already registered
        ue = await self.get_ue(imsi)
        if ue and ue.registration_status == 'attached':
            return True

        # Create waiter
        event = asyncio.Event()
        if imsi not in self._waiters:
            self._waiters[imsi] = []
        self._waiters[imsi].append(event)

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self._waiters[imsi].remove(event)
            if not self._waiters[imsi]:
                del self._waiters[imsi]

    async def detach_ue(self, imsi: str) -> bool:
        """Detach UE from network."""
        return await self._adapter.detach_ue(imsi)

    def get_cached_ues(self) -> List[UEInfo]:
        """Get cached UE list without fetching."""
        return list(self._ue_cache.values())
```

### 5. SMS Manager

SMS injection and monitoring.

```python
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SMSMessage:
    """SMS message information."""
    message_id: str
    direction: str  # mt or mo
    imsi: str
    pdu: bytes
    timestamp: datetime
    status: str  # pending, delivered, failed

class SMSManager:
    """Manages SMS injection and monitoring."""

    def __init__(self, adapter: SimulatorInterface,
                 event_emitter: Optional['EventEmitter'] = None):
        self._adapter = adapter
        self._event_emitter = event_emitter
        self._message_history: List[SMSMessage] = []
        self._message_id = 0

        # Subscribe to SMS events
        self._adapter.subscribe_events(self._handle_event)

    def _handle_event(self, event: dict) -> None:
        """Handle SMS-related events."""
        event_type = event.get('event')

        if event_type == 'sms_delivered':
            message_id = event.get('message_id')
            for msg in self._message_history:
                if msg.message_id == message_id:
                    msg.status = 'delivered'
                    break

            if self._event_emitter:
                self._event_emitter.emit('sms_delivered', {
                    'message_id': message_id,
                    'imsi': event.get('imsi')
                })

        elif event_type == 'sms_failed':
            message_id = event.get('message_id')
            for msg in self._message_history:
                if msg.message_id == message_id:
                    msg.status = 'failed'
                    break

            if self._event_emitter:
                self._event_emitter.emit('sms_failed', {
                    'message_id': message_id,
                    'cause': event.get('cause')
                })

        elif event_type == 'sms_received':
            # MO-SMS
            msg = SMSMessage(
                message_id=event.get('message_id', ''),
                direction='mo',
                imsi=event.get('imsi', ''),
                pdu=bytes.fromhex(event.get('pdu', '')),
                timestamp=datetime.utcnow(),
                status='received'
            )
            self._message_history.append(msg)

            if self._event_emitter:
                self._event_emitter.emit('sms_event', {
                    'direction': 'mo',
                    'imsi': event.get('imsi'),
                    'pdu': event.get('pdu')
                })

    async def send_mt_sms(self, imsi: str, pdu: bytes) -> str:
        """Send MT-SMS."""
        self._message_id += 1
        message_id = f"msg_{self._message_id}"

        # Record message
        msg = SMSMessage(
            message_id=message_id,
            direction='mt',
            imsi=imsi,
            pdu=pdu,
            timestamp=datetime.utcnow(),
            status='pending'
        )
        self._message_history.append(msg)

        # Send via adapter
        success = await self._adapter.send_sms(imsi, pdu)

        if not success:
            msg.status = 'failed'
            raise Exception("SMS send failed")

        if self._event_emitter:
            self._event_emitter.emit('sms_event', {
                'direction': 'mt',
                'imsi': imsi,
                'pdu': pdu.hex(),
                'message_id': message_id
            })

        return message_id

    async def send_sms_pp_trigger(self, imsi: str, tar: bytes,
                                  originating_address: str = None) -> str:
        """Send SMS-PP OTA trigger."""
        # Build SMS-PP PDU
        pdu = self._build_sms_pp_pdu(tar, originating_address)
        return await self.send_mt_sms(imsi, pdu)

    def _build_sms_pp_pdu(self, tar: bytes,
                         originating_address: str = None) -> bytes:
        """Build SMS-PP PDU for OTA trigger."""
        # Simplified SMS-PP PDU construction
        # In production, use proper PDU encoding
        pdu = bytearray()

        # SCA (Service Center Address) - empty
        pdu.append(0x00)

        # PDU Type: SMS-DELIVER
        pdu.append(0x04)

        # Originating Address
        if originating_address:
            oa_bytes = self._encode_address(originating_address)
            pdu.extend(oa_bytes)
        else:
            pdu.extend([0x00, 0x00])

        # Protocol Identifier - SIM Data Download
        pdu.append(0x7F)

        # Data Coding Scheme - 8-bit
        pdu.append(0xF6)

        # Timestamp (dummy)
        pdu.extend([0x00] * 7)

        # User Data Length
        ud = self._build_ota_command_packet(tar)
        pdu.append(len(ud))

        # User Data
        pdu.extend(ud)

        return bytes(pdu)

    def _encode_address(self, address: str) -> bytes:
        """Encode phone number for SMS PDU."""
        # Simplified address encoding
        digits = address.replace('+', '')
        length = len(digits)
        type_byte = 0x91 if address.startswith('+') else 0x81

        # BCD encode
        bcd = bytearray()
        for i in range(0, len(digits), 2):
            d1 = int(digits[i])
            d2 = int(digits[i+1]) if i+1 < len(digits) else 0x0F
            bcd.append((d2 << 4) | d1)

        return bytes([length, type_byte]) + bytes(bcd)

    def _build_ota_command_packet(self, tar: bytes) -> bytes:
        """Build OTA command packet."""
        # Command Packet Identifier
        cpi = 0x02

        # Command Header (simplified)
        header = bytearray()
        header.append(len(tar) + 5)  # CPL
        header.append(0x00)  # CHL
        header.append(0x00)  # SPI (first byte)
        header.append(0x00)  # SPI (second byte)
        header.append(0x00)  # KIc
        header.append(0x00)  # KID
        header.extend(tar)   # TAR

        return bytes([cpi]) + bytes(header)

    def get_message_history(self, limit: int = 100) -> List[SMSMessage]:
        """Get SMS message history."""
        return self._message_history[-limit:]

    def get_message(self, message_id: str) -> Optional[SMSMessage]:
        """Get specific message."""
        for msg in self._message_history:
            if msg.message_id == message_id:
                return msg
        return None
```

### 6. Event Manager

Event subscription and distribution.

```python
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class NetworkEvent:
    """Network event data."""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None

class EventManager:
    """Manages network events."""

    def __init__(self, adapter: SimulatorInterface,
                 event_emitter: Optional['EventEmitter'] = None):
        self._adapter = adapter
        self._event_emitter = event_emitter
        self._event_history: List[NetworkEvent] = []
        self._event_id = 0
        self._subscribers: Dict[str, List[Callable]] = {}
        self._monitoring = False

        # Subscribe to simulator events
        self._adapter.subscribe_events(self._handle_simulator_event)

    def _handle_simulator_event(self, event: dict) -> None:
        """Handle event from simulator."""
        self._event_id += 1

        network_event = NetworkEvent(
            event_id=f"evt_{self._event_id}",
            event_type=event.get('event', 'unknown'),
            timestamp=datetime.utcnow(),
            source='simulator',
            data=event
        )

        self._event_history.append(network_event)

        # Emit to external listeners
        if self._event_emitter:
            self._event_emitter.emit('network_event', {
                'event_id': network_event.event_id,
                'type': network_event.event_type,
                'timestamp': network_event.timestamp.isoformat(),
                'data': network_event.data
            })

        # Notify subscribers
        self._notify_subscribers(network_event)

    def _notify_subscribers(self, event: NetworkEvent) -> None:
        """Notify subscribers of event."""
        # Type-specific subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception:
                    pass

        # Wildcard subscribers
        if '*' in self._subscribers:
            for callback in self._subscribers['*']:
                try:
                    callback(event)
                except Exception:
                    pass

    def subscribe(self, event_type: str, callback: Callable[[NetworkEvent], None]) -> None:
        """Subscribe to event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable = None) -> None:
        """Unsubscribe from event type."""
        if event_type in self._subscribers:
            if callback:
                self._subscribers[event_type].remove(callback)
            else:
                del self._subscribers[event_type]

    async def start_monitoring(self) -> None:
        """Start event monitoring."""
        self._monitoring = True

    async def stop_monitoring(self) -> None:
        """Stop event monitoring."""
        self._monitoring = False

    def get_event_history(self,
                         event_type: str = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         limit: int = 100) -> List[NetworkEvent]:
        """Get filtered event history."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events[-limit:]

    def correlate_events(self, imsi: str,
                        time_window: float = 60.0) -> List[NetworkEvent]:
        """Get events correlated by IMSI within time window."""
        now = datetime.utcnow()
        correlated = []

        for event in self._event_history:
            # Check time window
            if (now - event.timestamp).total_seconds() > time_window:
                continue

            # Check IMSI in event data
            if event.data.get('imsi') == imsi:
                correlated.append(event)

        return correlated

    def export_events(self, format: str = 'json') -> str:
        """Export event history."""
        import json

        events = [
            {
                'event_id': e.event_id,
                'event_type': e.event_type,
                'timestamp': e.timestamp.isoformat(),
                'source': e.source,
                'data': e.data
            }
            for e in self._event_history
        ]

        if format == 'json':
            return json.dumps(events, indent=2)
        elif format == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['event_id', 'event_type', 'timestamp', 'source', 'data'])
            for e in events:
                writer.writerow([e['event_id'], e['event_type'], e['timestamp'],
                               e['source'], json.dumps(e['data'])])
            return output.getvalue()

        return ''
```

### 7. Scenario Runner

Test scenario orchestration.

```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import yaml

class StepStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    SKIPPED = 'skipped'

@dataclass
class ScenarioStep:
    """Scenario step definition."""
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    continue_on_failure: bool = False
    condition: Optional[str] = None

@dataclass
class StepResult:
    """Step execution result."""
    step_name: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None

@dataclass
class Scenario:
    """Test scenario definition."""
    name: str
    description: str
    steps: List[ScenarioStep]
    variables: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Scenario':
        """Load scenario from YAML."""
        data = yaml.safe_load(yaml_str)

        steps = [
            ScenarioStep(
                name=s.get('name', f'step_{i}'),
                action=s['action'],
                params=s.get('params', {}),
                timeout=s.get('timeout', 30.0),
                continue_on_failure=s.get('continue_on_failure', False),
                condition=s.get('condition')
            )
            for i, s in enumerate(data.get('steps', []))
        ]

        return cls(
            name=data.get('name', 'Unnamed'),
            description=data.get('description', ''),
            steps=steps,
            variables=data.get('variables', {})
        )


class ScenarioRunner:
    """Executes test scenarios."""

    def __init__(self,
                 simulator_manager: SimulatorManager,
                 device_controller=None,
                 server_controller=None,
                 event_emitter: Optional['EventEmitter'] = None):
        self._simulator = simulator_manager
        self._device = device_controller
        self._server = server_controller
        self._event_emitter = event_emitter
        self._running = False
        self._current_scenario: Optional[Scenario] = None
        self._results: List[StepResult] = []
        self._variables: Dict[str, Any] = {}

    async def run(self, scenario: Scenario) -> List[StepResult]:
        """Run scenario."""
        self._running = True
        self._current_scenario = scenario
        self._results = []
        self._variables = dict(scenario.variables)

        if self._event_emitter:
            self._event_emitter.emit('scenario_started', {
                'name': scenario.name,
                'step_count': len(scenario.steps)
            })

        for step in scenario.steps:
            if not self._running:
                break

            # Check condition
            if step.condition and not self._evaluate_condition(step.condition):
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    start_time=datetime.utcnow()
                )
                self._results.append(result)
                continue

            # Execute step
            result = await self._execute_step(step)
            self._results.append(result)

            if self._event_emitter:
                self._event_emitter.emit('scenario_step_completed', {
                    'step_name': step.name,
                    'status': result.status.value,
                    'duration_ms': result.duration_ms
                })

            # Check failure
            if result.status == StepStatus.FAILED and not step.continue_on_failure:
                break

        self._running = False

        if self._event_emitter:
            self._event_emitter.emit('scenario_completed', {
                'name': scenario.name,
                'results': [
                    {'step': r.step_name, 'status': r.status.value}
                    for r in self._results
                ]
            })

        return self._results

    async def _execute_step(self, step: ScenarioStep) -> StepResult:
        """Execute single step."""
        start_time = datetime.utcnow()

        result = StepResult(
            step_name=step.name,
            status=StepStatus.RUNNING,
            start_time=start_time
        )

        try:
            # Resolve parameters
            params = self._resolve_params(step.params)

            # Execute action
            output = await asyncio.wait_for(
                self._execute_action(step.action, params),
                timeout=step.timeout
            )

            result.status = StepStatus.PASSED
            result.output = output

            # Store output in variables
            if output and isinstance(output, dict):
                self._variables.update(output)

        except asyncio.TimeoutError:
            result.status = StepStatus.FAILED
            result.error = f"Timeout after {step.timeout}s"

        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)

        result.end_time = datetime.utcnow()
        result.duration_ms = (result.end_time - start_time).total_seconds() * 1000

        return result

    async def _execute_action(self, action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute action by name."""
        action_map = {
            # Simulator actions
            'simulator.start_cell': lambda p: self._simulator.cell.start(),
            'simulator.stop_cell': lambda p: self._simulator.cell.stop(),
            'simulator.wait_ue': lambda p: self._simulator.ue.wait_for_registration(
                p['imsi'], p.get('timeout', 60)
            ),
            'simulator.send_sms': lambda p: self._simulator.sms.send_mt_sms(
                p['imsi'], bytes.fromhex(p['pdu'])
            ),
            'simulator.trigger_event': lambda p: self._simulator._adapter.trigger_event(
                p['type'], p.get('params', {})
            ),

            # Wait actions
            'wait': lambda p: asyncio.sleep(p.get('seconds', 1)),

            # Variable actions
            'set_variable': lambda p: self._set_variable(p['name'], p['value']),
        }

        if action in action_map:
            return await action_map[action](params)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variable references in params."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                resolved[key] = self._variables.get(var_name, value)
            else:
                resolved[key] = value
        return resolved

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate condition expression."""
        # Simple variable existence check
        if condition.startswith('defined:'):
            var_name = condition[8:]
            return var_name in self._variables

        return True

    def _set_variable(self, name: str, value: Any) -> Dict[str, Any]:
        """Set variable."""
        self._variables[name] = value
        return {name: value}

    def stop(self) -> None:
        """Stop scenario execution."""
        self._running = False

    def get_results(self) -> List[StepResult]:
        """Get current results."""
        return self._results.copy()
```

## CLI Design

### Command Structure

```
cardlink-netsim
├── connect <url>           # Connect to simulator
│   ├── --type <type>      # Simulator type (amarisoft)
│   ├── --api-key <key>    # API key for auth
│   └── --tls              # Enable TLS
├── disconnect              # Disconnect from simulator
├── status                  # Show simulator status
│   └── --json             # JSON output
├── cell                    # Cell operations
│   ├── start              # Start cell
│   ├── stop               # Stop cell
│   └── status             # Cell status
├── ue                      # UE operations
│   ├── list               # List connected UEs
│   ├── get <imsi>         # Get UE details
│   ├── wait <imsi>        # Wait for registration
│   │   └── --timeout <s>  # Wait timeout
│   └── detach <imsi>      # Detach UE
├── sms                     # SMS operations
│   ├── send <imsi> <pdu>  # Send MT-SMS
│   └── trigger <imsi>     # Send OTA trigger
│       └── --tar <hex>    # TAR value
├── event                   # Event operations
│   ├── trigger <type>     # Trigger network event
│   ├── list               # List recent events
│   └── export <file>      # Export events
├── scenario                # Scenario operations
│   ├── run <file>         # Run scenario
│   ├── validate <file>    # Validate scenario
│   └── list               # List available scenarios
└── config                  # Configuration
    ├── show               # Show current config
    ├── load <file>        # Load config
    └── save <file>        # Save config
```

## Dependencies

### Required Packages

```
websockets>=11.0           # WebSocket client
pyyaml>=6.0                # YAML scenario files
```

### Optional Packages

```
aiohttp>=3.8.0             # Alternative HTTP client
```
