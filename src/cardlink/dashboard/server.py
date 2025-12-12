"""Dashboard Server for GP OTA Tester.

This module provides a web server for the dashboard frontend with:
- Static file serving
- REST API endpoints
- WebSocket support for real-time updates
- Network simulator integration

Example:
    >>> from cardlink.dashboard import DashboardServer
    >>>
    >>> server = DashboardServer(host="127.0.0.1", port=8080)
    >>> await server.start()
"""

import asyncio
import json
import logging
import mimetypes
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Import protocol layer for APDU parsing and analysis
try:
    from cardlink.protocol import (
        # Remote APDU parsing
        CompactRemoteAPDU,
        ExpandedRemoteAPDU,
        RemoteAPDUFormat,
        APDUCase,
        # Scripting templates
        CommandScriptingTemplate,
        ResponseScriptingTemplate,
        ScriptingTag,
        ScriptChaining,
        # HTTP constants
        CONTENT_TYPE_COMMAND,
        CONTENT_TYPE_RESPONSE,
        GP_CONTENT_TYPE_COMMAND,
        GP_CONTENT_TYPE_RESPONSE,
        ScriptStatus,
        encode_aid_for_header,
        decode_aid_from_header,
        # RAM commands
        RAMCommand,
        InstallType,
        KeyType,
        # GP SCP81
        PSKKeyType,
        PSKCipherSuite,
        CIPHER_SUITE_IDS,
        TriggerTag,
        get_supported_cipher_suites,
    )
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False

# Import network simulator components (optional)
try:
    from cardlink.netsim import (
        SimulatorManager,
        SimulatorConfig,
        SimulatorType,
        SimulatorStatus,
        TLSConfig,
        UEInfo,
        DataSession,
        CellInfo,
        NetworkEvent,
        NotConnectedError,
    )
    NETSIM_AVAILABLE = True
except ImportError:
    NETSIM_AVAILABLE = False
    SimulatorManager = None
    SimulatorConfig = None
    SimulatorType = None
    SimulatorStatus = None
    TLSConfig = None
    NotConnectedError = Exception

# Import AdminServer components (optional - for embedded mode)
try:
    from cardlink.server import AdminServer
    from cardlink.server.models import SessionState
    ADMIN_SERVER_AVAILABLE = True
except ImportError:
    ADMIN_SERVER_AVAILABLE = False
    AdminServer = None
    SessionState = None

# Import Scripts API (optional - for script management)
try:
    from cardlink.dashboard.scripts_api import ScriptsAPI
    SCRIPTS_API_AVAILABLE = True
except ImportError:
    SCRIPTS_API_AVAILABLE = False
    ScriptsAPI = None

logger = logging.getLogger(__name__)

# Get the static files directory
STATIC_DIR = Path(__file__).parent / "static"


@dataclass
class DashboardConfig:
    """Dashboard server configuration."""

    host: str = "127.0.0.1"
    port: int = 8080
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    static_dir: Path = STATIC_DIR
    debug: bool = False
    session_timeout_seconds: float = 0.0  # 0 = disabled, auto-close sessions after timeout
    scripts_dir: Optional[Path] = None  # Directory to load APDU scripts from


@dataclass
class Session:
    """Test session with protocol details."""

    id: str
    name: str
    status: str = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    apdu_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    psk_identity: Optional[str] = None
    client_ip: Optional[str] = None
    # Card identifiers per GP Amendment B / ETSI TS 102.226
    # Extracted from X-Admin-From header URI formats
    iccid: Optional[str] = None   # //se/iccid/<ICCID> - Card identification
    eid: Optional[str] = None     # //se/eid/<EID> - eSIM identification
    imei: Optional[str] = None    # //terminal/imei/<IMEI> - Device identification
    seid: Optional[str] = None    # //se/seid/<SEID> - SE identification
    # Protocol details (GP SCP81 / ETSI TS 102.226)
    cipher_suite: Optional[str] = None
    tls_version: Optional[str] = None
    handshake_duration_ms: Optional[float] = None
    protocol_mode: str = "gp"  # "gp" for GlobalPlatform, "etsi" for ETSI
    # Protocol statistics
    ram_command_count: int = 0
    rfm_command_count: int = 0
    script_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Include psk_identity and client_ip in metadata for frontend
        metadata = dict(self.metadata)
        if self.psk_identity:
            metadata["psk_identity"] = self.psk_identity
        if self.client_ip:
            metadata["client_ip"] = self.client_ip

        # Get identifiers from explicit fields or metadata
        iccid = self.iccid or self.metadata.get("iccid")
        eid = self.eid or self.metadata.get("eid")
        imei = self.imei or self.metadata.get("imei")
        seid = self.seid or self.metadata.get("seid")

        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "apduCount": self.apdu_count,
            "metadata": metadata,
            "pskIdentity": self.psk_identity,
            "clientIp": self.client_ip,
            # Card identifiers (per GP Amendment B / ETSI TS 102.226)
            "iccid": iccid,
            "eid": eid,
            "imei": imei,
            "seid": seid,
            # Protocol details
            "cipherSuite": self.cipher_suite,
            "tlsVersion": self.tls_version,
            "handshakeDurationMs": self.handshake_duration_ms,
            "protocolMode": self.protocol_mode,
            # Protocol statistics
            "ramCommandCount": self.ram_command_count,
            "rfmCommandCount": self.rfm_command_count,
            "scriptCount": self.script_count,
        }


@dataclass
class APDUEntry:
    """APDU log entry with protocol analysis."""

    id: str
    session_id: str
    timestamp: datetime
    direction: str  # 'command' or 'response'
    data: str
    sw: Optional[str] = None
    response_data: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Protocol analysis fields
    ins: Optional[int] = None
    ins_name: Optional[str] = None
    apdu_type: Optional[str] = None  # 'ram', 'rfm', 'standard', 'unknown'
    remote_apdu_format: Optional[str] = None  # 'compact', 'expanded', None
    script_chaining: Optional[str] = None  # 'first', 'subsequent', 'last', 'only'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "timestamp": int(self.timestamp.timestamp() * 1000),
            "direction": self.direction,
            "data": self.data,
            "sw": self.sw,
            "responseData": self.response_data,
            "metadata": self.metadata,
            # Protocol analysis
            "ins": self.ins,
            "insName": self.ins_name,
            "apduType": self.apdu_type,
            "remoteApduFormat": self.remote_apdu_format,
            "scriptChaining": self.script_chaining,
        }


# APDU parsing helper functions
def _parse_apdu_info(apdu_hex: str, direction: str) -> Dict[str, Any]:
    """Parse APDU and extract protocol information.

    Args:
        apdu_hex: APDU data as hex string.
        direction: 'command' or 'response'.

    Returns:
        Dictionary with parsed info: ins, ins_name, apdu_type.
    """
    result = {
        "ins": None,
        "ins_name": None,
        "apdu_type": None,
        "remote_apdu_format": None,
    }

    if direction != "command" or len(apdu_hex) < 8:
        return result

    try:
        apdu_bytes = bytes.fromhex(apdu_hex)
        if len(apdu_bytes) < 4:
            return result

        ins = apdu_bytes[1]
        result["ins"] = ins

        # INS name mapping
        ins_names = {
            0xA4: "SELECT",
            0xB0: "READ BINARY",
            0xB2: "READ RECORD",
            0xC0: "GET RESPONSE",
            0xCA: "GET DATA",
            0xD6: "UPDATE BINARY",
            0xDC: "UPDATE RECORD",
            0xE2: "STORE DATA",
            0xE4: "DELETE",
            0xE6: "INSTALL",
            0xE8: "LOAD",
            0xF2: "GET STATUS",
            0xF0: "SET STATUS",
            0x50: "INITIALIZE UPDATE",
            0x82: "EXTERNAL AUTHENTICATE",
            0x84: "GET CHALLENGE",
            0xD8: "PUT KEY",
        }
        result["ins_name"] = ins_names.get(ins, f"INS_{ins:02X}")

        # Determine APDU type (RAM, RFM, standard)
        ram_commands = {0xE4, 0xE6, 0xE8, 0xF2, 0xF0, 0xD8, 0xE2}
        if ins in ram_commands:
            result["apdu_type"] = "ram"
        elif ins in {0xA4, 0xB0, 0xB2, 0xC0, 0xCA, 0xD6, 0xDC}:
            result["apdu_type"] = "standard"
        else:
            result["apdu_type"] = "unknown"

    except (ValueError, IndexError):
        pass

    return result


class DashboardState:
    """In-memory state storage for dashboard."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.apdus: Dict[str, List[APDUEntry]] = {}  # session_id -> apdus
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        name: str,
        psk_identity: Optional[str] = None,
        client_ip: Optional[str] = None,
        iccid: Optional[str] = None,
        eid: Optional[str] = None,
        imei: Optional[str] = None,
        seid: Optional[str] = None,
        cipher_suite: Optional[str] = None,
        tls_version: Optional[str] = None,
        handshake_duration_ms: Optional[float] = None,
        protocol_mode: str = "gp",
        **metadata,
    ) -> Session:
        """Create a new session with protocol details.

        Args:
            name: Session display name.
            psk_identity: PSK identity for the connection.
            client_ip: Client IP address.
            iccid: ICCID from X-Admin-From: //se/iccid/<ICCID>
            eid: EID from X-Admin-From: //se/eid/<EID>
            imei: IMEI from X-Admin-From: //terminal/imei/<IMEI>
            seid: SEID from X-Admin-From: //se/seid/<SEID>
            cipher_suite: TLS cipher suite (e.g., 'PSK-AES128-CBC-SHA256').
            tls_version: TLS version (e.g., 'TLSv1.2').
            handshake_duration_ms: TLS handshake duration in milliseconds.
            protocol_mode: Protocol mode ('gp' or 'etsi').
            **metadata: Additional metadata.

        Returns:
            Created session.
        """
        async with self._lock:
            # Use psk_identity as name if name is generic
            display_name = name
            if psk_identity and (not name or name.startswith("Session ")):
                display_name = psk_identity

            # Extract identifiers from metadata if not passed directly
            if not iccid:
                iccid = metadata.pop("iccid", None)
            if not eid:
                eid = metadata.pop("eid", None)
            if not imei:
                imei = metadata.pop("imei", None)
            if not seid:
                seid = metadata.pop("seid", None)

            session = Session(
                id=str(uuid.uuid4()),
                name=display_name,
                psk_identity=psk_identity,
                client_ip=client_ip,
                iccid=iccid,
                eid=eid,
                imei=imei,
                seid=seid,
                cipher_suite=cipher_suite,
                tls_version=tls_version,
                handshake_duration_ms=handshake_duration_ms,
                protocol_mode=protocol_mode,
                metadata=metadata,
            )
            self.sessions[session.id] = session
            self.apdus[session.id] = []
            return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    async def get_session_by_psk_identity(self, psk_identity: str) -> Optional[Session]:
        """Get a session by PSK identity.

        This is used to map APDU events (which use PSK identity as session_id)
        to dashboard sessions (which use a random UUID as session ID).
        """
        for session in self.sessions.values():
            if session.psk_identity == psk_identity:
                return session
        return None

    async def get_sessions(self) -> List[Session]:
        """Get all sessions."""
        return list(self.sessions.values())

    async def update_session(self, session_id: str, **updates) -> Optional[Session]:
        """Update a session."""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)

            session.updated_at = datetime.now()
            return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.apdus.pop(session_id, None)
                return True
            return False

    async def add_apdu(
        self,
        session_id: str,
        direction: str,
        data: str,
        sw: Optional[str] = None,
        response_data: Optional[str] = None,
        **metadata,
    ) -> Optional[APDUEntry]:
        """Add an APDU entry with protocol analysis."""
        async with self._lock:
            if session_id not in self.sessions:
                return None

            # Parse APDU for protocol information
            apdu_info = _parse_apdu_info(data, direction)

            entry = APDUEntry(
                id=str(uuid.uuid4()),
                session_id=session_id,
                timestamp=datetime.now(),
                direction=direction,
                data=data,
                sw=sw,
                response_data=response_data,
                metadata=metadata,
                # Protocol analysis fields
                ins=apdu_info.get("ins"),
                ins_name=apdu_info.get("ins_name"),
                apdu_type=apdu_info.get("apdu_type"),
                remote_apdu_format=apdu_info.get("remote_apdu_format"),
            )

            if session_id not in self.apdus:
                self.apdus[session_id] = []

            self.apdus[session_id].append(entry)

            # Update session counters
            session = self.sessions[session_id]
            session.apdu_count = len(self.apdus[session_id])
            session.updated_at = datetime.now()

            # Update protocol-specific counters
            if apdu_info.get("apdu_type") == "ram":
                session.ram_command_count += 1
            elif apdu_info.get("apdu_type") == "rfm":
                session.rfm_command_count += 1

            return entry

    async def get_apdus(self, session_id: str) -> List[APDUEntry]:
        """Get APDUs for a session."""
        return self.apdus.get(session_id, [])

    async def clear_apdus(self, session_id: str) -> bool:
        """Clear APDUs for a session."""
        async with self._lock:
            if session_id in self.apdus:
                self.apdus[session_id] = []
                self.sessions[session_id].apdu_count = 0
                return True
            return False


class WebSocketClient:
    """WebSocket client connection."""

    def __init__(self, writer: asyncio.StreamWriter):
        self.writer = writer
        self.id = str(uuid.uuid4())
        self.subscriptions: Set[str] = set()

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message to the client."""
        try:
            data = json.dumps(message).encode()
            # Simple WebSocket frame (text frame)
            if len(data) <= 125:
                frame = bytes([0x81, len(data)]) + data
            elif len(data) <= 65535:
                frame = bytes([0x81, 126]) + len(data).to_bytes(2, "big") + data
            else:
                frame = bytes([0x81, 127]) + len(data).to_bytes(8, "big") + data

            self.writer.write(frame)
            await self.writer.drain()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Connection was closed by client - this is expected behavior
            logger.debug("Connection closed for client %s: %s", self.id, e)
        except Exception as e:
            logger.debug("Failed to send to client %s: %s", self.id, e)


class DashboardServer:
    """Dashboard HTTP/WebSocket server.

    Example:
        >>> server = DashboardServer()
        >>> await server.start()
    """

    def __init__(self, config: Optional[DashboardConfig] = None):
        """Initialize dashboard server.

        Args:
            config: Server configuration.
        """
        self.config = config or DashboardConfig()
        self.state = DashboardState()
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Dict[str, WebSocketClient] = {}
        self._apdu_callbacks: List[Callable] = []

        # Network simulator integration
        self._simulator: Optional[SimulatorManager] = None
        self._simulator_events: List[Dict[str, Any]] = []
        self._max_events = 1000  # Max events to keep in memory

        # TLS PSK Admin Server integration
        self._admin_server: Optional[Any] = None  # AdminServer instance
        self._admin_server_event_handler = None

        # Event loop reference for cross-thread event handling
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Session timeout task
        self._session_timeout_task: Optional[asyncio.Task] = None

        # Scripts API integration
        self._scripts_api: Optional[Any] = None
        if SCRIPTS_API_AVAILABLE:
            try:
                self._scripts_api = ScriptsAPI(scripts_dir=self.config.scripts_dir)
                logger.info("Scripts API initialized")
            except Exception as e:
                logger.warning("Failed to initialize Scripts API: %s", e)

    def _setup_scripts_execute_callback(self) -> None:
        """Set up the script execution callback.

        This method configures the Scripts API to execute commands via the
        AdminServer's HTTP handler. It handles the case where the handler
        may not exist yet at setup time.
        """
        if not self._scripts_api:
            return

        admin_server = self._admin_server

        def execute_commands(session_id: str, commands: list) -> None:
            """Queue commands to AdminServer for execution.

            Args:
                session_id: Target session ID (PSK identity).
                commands: List of APDU command bytes to execute.
            """
            if not admin_server:
                logger.error("No AdminServer connected - cannot execute commands")
                raise RuntimeError("AdminServer not connected")

            # Check for handler at execution time
            handler = getattr(admin_server, '_handler', None)
            if handler:
                handler.queue_commands(session_id, commands)
                logger.debug("Queued %d commands for session %s via Scripts API",
                            len(commands), session_id)
            else:
                logger.error("AdminServer handler not available for command execution")
                raise RuntimeError("AdminServer handler not ready")

        self._scripts_api.set_execute_callback(execute_commands)
        logger.info("Scripts API execute callback connected to AdminServer")

    def set_admin_server(self, admin_server: Any) -> None:
        """Set the AdminServer instance for dashboard integration.

        When set, the dashboard will display real-time session and APDU
        data from the PSK-TLS server. Event subscriptions will be set up
        when start() is called (after the event loop is ready).

        Args:
            admin_server: AdminServer instance to connect to.
        """
        if not ADMIN_SERVER_AVAILABLE:
            logger.warning("AdminServer module not available")
            return

        self._admin_server = admin_server
        logger.info("Dashboard connected to AdminServer (events will be subscribed on start)")

        # Wire up the Scripts API execute callback to AdminServer's queue_commands
        # Note: The callback checks for handler at execution time, not setup time
        self._setup_scripts_execute_callback()

    def _subscribe_to_admin_events(self) -> None:
        """Subscribe to AdminServer events. Called from start() after loop is ready."""
        if not self._admin_server:
            return

        if not hasattr(self._admin_server, '_event_emitter') or not self._admin_server._event_emitter:
            logger.warning("AdminServer has no event emitter")
            return

        emitter = self._admin_server._event_emitter

        def on_handshake_completed(event):
            # Use thread-safe scheduling since this may be called from AdminServer thread
            if self._loop and self._loop.is_running():
                logger.info("Scheduling handshake_completed event for dashboard: %s", event.get('psk_identity', 'unknown'))
                asyncio.run_coroutine_threadsafe(
                    self._handle_server_session_created(event),
                    self._loop
                )
            else:
                logger.warning("Dashboard event loop not available for session event (loop=%s, running=%s)",
                              self._loop is not None, self._loop.is_running() if self._loop else False)

        def on_apdu_received(event):
            # Use thread-safe scheduling since this may be called from AdminServer thread
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._handle_server_apdu_received(event),
                    self._loop
                )
            else:
                logger.debug("Dashboard event loop not available for APDU received event")

        def on_apdu_sent(event):
            # Use thread-safe scheduling since this may be called from AdminServer thread
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._handle_server_apdu_sent(event),
                    self._loop
                )
            else:
                logger.debug("Dashboard event loop not available for APDU sent event")

        def on_session_updated(event):
            # Use thread-safe scheduling since this may be called from AdminServer thread
            if self._loop and self._loop.is_running():
                logger.debug("Scheduling session_updated event for dashboard: %s", event.get('psk_identity', 'unknown'))
                asyncio.run_coroutine_threadsafe(
                    self._handle_server_session_updated(event),
                    self._loop
                )
            else:
                logger.debug("Dashboard event loop not available for session_updated event")

        # Subscribe to correct server event names
        emitter.subscribe('handshake_completed', on_handshake_completed)
        emitter.subscribe('apdu_received', on_apdu_received)
        emitter.subscribe('apdu_sent', on_apdu_sent)
        emitter.subscribe('session_updated', on_session_updated)
        self._admin_server_event_handler = (on_handshake_completed, on_apdu_received, on_apdu_sent, on_session_updated)
        logger.info("Subscribed to AdminServer events: handshake_completed, apdu_received, apdu_sent, session_updated")

    @property
    def admin_server(self) -> Optional[Any]:
        """Get connected AdminServer instance."""
        return self._admin_server

    @property
    def is_server_connected(self) -> bool:
        """Check if AdminServer is connected and running."""
        if not self._admin_server:
            return False
        return getattr(self._admin_server, 'is_running', False)

    async def _handle_server_session_created(self, event: Dict[str, Any]) -> None:
        """Handle handshake_completed event from AdminServer.

        Event format from AdminServer:
        {
            'client_address': '127.0.0.1:12345',
            'psk_identity': 'test_card',
            'cipher_suite': 'PSK-AES128-CBC-SHA256',
            'protocol_version': 'TLSv1.2',
            'handshake_duration_ms': 5.2,
        }

        In persistent mode, the simulator reconnects multiple times. We check
        for existing sessions by PSK identity to avoid creating duplicates.
        """
        try:
            psk_identity = event.get('psk_identity', '')
            client_address = event.get('client_address', '')
            cipher_suite = event.get('cipher_suite', '')
            tls_version = event.get('protocol_version', '')
            handshake_duration_ms = event.get('handshake_duration_ms')

            # Check if session already exists for this PSK identity (persistent mode)
            existing_session = await self.state.get_session_by_psk_identity(psk_identity)
            if existing_session:
                # Update existing session instead of creating duplicate
                await self.state.update_session(
                    existing_session.id,
                    status="active",
                    client_ip=client_address.split(':')[0] if ':' in client_address else client_address,
                    cipher_suite=cipher_suite,
                    tls_version=tls_version,
                    handshake_duration_ms=handshake_duration_ms,
                )
                logger.info(
                    "Dashboard session reconnected: %s (PSK: %s, cipher: %s)",
                    existing_session.id, psk_identity, cipher_suite
                )

                # Notify WebSocket clients of reconnection
                await self._broadcast('session_updated', {
                    'session': existing_session.to_dict(),
                    'reconnected': True,
                })
                return

            # Create new dashboard session with protocol details
            session = await self.state.create_session(
                name=psk_identity or f"Session {client_address}",
                psk_identity=psk_identity,
                client_ip=client_address.split(':')[0] if ':' in client_address else client_address,
                cipher_suite=cipher_suite,
                tls_version=tls_version,
                handshake_duration_ms=handshake_duration_ms,
            )

            logger.info("Dashboard session created: %s (PSK: %s)", session.id, psk_identity)

            # Notify WebSocket clients
            await self._broadcast('session_created', {
                'session': session.to_dict(),
            })
        except Exception as e:
            logger.error("Error handling session created event: %s", e)

    async def _handle_server_apdu_received(self, event: Dict[str, Any]) -> None:
        """Handle apdu_received event from AdminServer (R-APDU from card)."""
        try:
            # Get PSK identity from the event (added by HTTPHandler)
            psk_identity = event.get('psk_identity', '')
            apdu = event.get('apdu', b'')
            apdu_hex = apdu.hex().upper() if isinstance(apdu, bytes) else str(apdu).upper()

            # Look up the dashboard session by PSK identity
            session = await self.state.get_session_by_psk_identity(psk_identity)
            if not session:
                logger.warning("No session found for PSK identity: %s", psk_identity)
                return

            # Parse R-APDU: response data + SW (last 2 bytes / 4 hex chars)
            sw = ''
            response_data = ''
            if len(apdu_hex) >= 4:
                sw = apdu_hex[-4:]
                response_data = apdu_hex[:-4] if len(apdu_hex) > 4 else ''

            # Store APDU for later retrieval (use actual session ID)
            await self.state.add_apdu(
                session_id=session.id,
                direction='response',
                data=apdu_hex,
                sw=sw,
                response_data=response_data,
            )

            # Extract HTTP info from event if available
            http_info = event.get('http')

            # Notify WebSocket clients
            apdu_data = {
                'id': str(uuid.uuid4()),
                'direction': 'response',
                'sessionId': session.id,
                'data': apdu_hex,
                'sw': sw,
                'responseData': response_data,
                'timestamp': int(datetime.now().timestamp() * 1000),
            }
            if http_info:
                apdu_data['http'] = http_info

            await self._broadcast('apdu', apdu_data)
        except Exception as e:
            logger.error("Error handling APDU received event: %s", e)

    async def _handle_server_apdu_sent(self, event: Dict[str, Any]) -> None:
        """Handle apdu_sent event from AdminServer (C-APDU to card)."""
        try:
            # Get PSK identity from the event (added by HTTPHandler)
            psk_identity = event.get('psk_identity', '')
            apdu = event.get('apdu', b'')
            apdu_hex = apdu.hex().upper() if isinstance(apdu, bytes) else str(apdu).upper()

            # Look up the dashboard session by PSK identity
            session = await self.state.get_session_by_psk_identity(psk_identity)
            if not session:
                logger.warning("No session found for PSK identity: %s", psk_identity)
                return

            # Store APDU for later retrieval (use actual session ID)
            await self.state.add_apdu(
                session_id=session.id,
                direction='command',
                data=apdu_hex,
            )

            # Extract HTTP info from event if available
            http_info = event.get('http')

            # Notify WebSocket clients
            apdu_data = {
                'id': str(uuid.uuid4()),
                'direction': 'command',
                'sessionId': session.id,
                'data': apdu_hex,
                'timestamp': int(datetime.now().timestamp() * 1000),
            }
            if http_info:
                apdu_data['http'] = http_info

            await self._broadcast('apdu', apdu_data)
        except Exception as e:
            logger.error("Error handling APDU sent event: %s", e)

    async def _handle_server_session_updated(self, event: Dict[str, Any]) -> None:
        """Handle session_updated event from AdminServer.

        Event format from AdminServer (when X-Admin-From header is parsed):
        {
            'session_id': 'session-uuid',
            'psk_identity': 'test_card',
            'agent_id': '//se/iccid/8933102300001234567F',
            'iccid': '8933102300001234567F',
            'eid': '89049032123456789012345678901234',
            'imei': '353456789012345',
            'seid': None,
        }

        This event is emitted when the HTTP handler parses identifiers from
        the X-Admin-From header, which happens after the TLS handshake.
        """
        try:
            psk_identity = event.get('psk_identity', '')

            # Look up the dashboard session by PSK identity
            session = await self.state.get_session_by_psk_identity(psk_identity)
            if not session:
                logger.warning("No session found for PSK identity: %s", psk_identity)
                return

            # Extract identifiers from event
            iccid = event.get('iccid')
            eid = event.get('eid')
            imei = event.get('imei')
            seid = event.get('seid')

            # Update session with identifiers
            updates = {}
            if iccid:
                updates['iccid'] = iccid
            if eid:
                updates['eid'] = eid
            if imei:
                updates['imei'] = imei
            if seid:
                updates['seid'] = seid

            if updates:
                await self.state.update_session(session.id, **updates)
                logger.info(
                    "Updated session %s with identifiers: iccid=%s, eid=%s, imei=%s, seid=%s",
                    session.id, iccid, eid, imei, seid
                )

                # Notify WebSocket clients of session update
                updated_session = await self.state.get_session(session.id)
                if updated_session:
                    await self._broadcast('session_updated', {
                        'session': updated_session.to_dict(),
                    })

        except Exception as e:
            logger.error("Error handling session_updated event: %s", e)

    async def start(self) -> None:
        """Start the server."""
        # Store event loop reference for cross-thread event handling
        self._loop = asyncio.get_event_loop()

        # Subscribe to AdminServer events now that the loop is ready
        self._subscribe_to_admin_events()

        # Start session timeout checker if enabled
        if self.config.session_timeout_seconds > 0:
            self._session_timeout_task = asyncio.create_task(
                self._run_session_timeout_checker()
            )
            logger.info(
                "Session timeout enabled: %.0f seconds",
                self.config.session_timeout_seconds
            )

        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self.config.host,
                self.config.port,
            )
        except OSError as e:
            if e.errno == 10013:  # Windows: Access forbidden
                raise OSError(
                    f"Cannot bind to {self.config.host}:{self.config.port}. "
                    f"Port may be blocked by Windows or already in use. "
                    f"Try a different port: --port 8081 or --port 8082"
                ) from e
            elif e.errno == 98:  # Linux: Address already in use
                raise OSError(
                    f"Port {self.config.port} is already in use. "
                    f"Try a different port: --port 8081"
                ) from e
            raise

        addr = self._server.sockets[0].getsockname()
        logger.info("Dashboard server started at http://%s:%s", addr[0], addr[1])

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the server."""
        # Cancel session timeout task
        if self._session_timeout_task:
            self._session_timeout_task.cancel()
            try:
                await self._session_timeout_task
            except asyncio.CancelledError:
                pass
            self._session_timeout_task = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Dashboard server stopped")

    async def _run_session_timeout_checker(self) -> None:
        """Background task to check and close timed-out sessions.

        Runs periodically to check all sessions and close those that
        haven't had activity within the configured timeout period.
        """
        timeout = self.config.session_timeout_seconds
        # Check every 10% of the timeout, but at least every 5 seconds
        check_interval = max(5.0, timeout * 0.1)

        logger.debug(
            "Session timeout checker started (timeout=%.0fs, interval=%.0fs)",
            timeout, check_interval
        )

        try:
            while True:
                await asyncio.sleep(check_interval)

                now = datetime.now()
                sessions_to_close = []

                # Find sessions that have timed out
                for session_id, session in list(self.state.sessions.items()):
                    elapsed = (now - session.updated_at).total_seconds()
                    if elapsed > timeout:
                        sessions_to_close.append((session_id, session, elapsed))

                # Close timed-out sessions
                for session_id, session, elapsed in sessions_to_close:
                    logger.info(
                        "Closing session %s (PSK: %s) due to timeout (%.0fs idle)",
                        session_id, session.psk_identity or "unknown", elapsed
                    )

                    # Delete session from state
                    await self.state.delete_session(session_id)

                    # Notify WebSocket clients
                    await self._broadcast('session.deleted', {
                        'id': session_id,
                        'reason': 'timeout',
                    })

        except asyncio.CancelledError:
            logger.debug("Session timeout checker stopped")
            raise

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming connection."""
        try:
            # Read request line
            request_line = await reader.readline()
            if not request_line:
                return

            request_line = request_line.decode().strip()
            parts = request_line.split()
            if len(parts) < 2:
                return

            method = parts[0]
            path = parts[1]

            # Read headers
            headers = {}
            while True:
                line = await reader.readline()
                if line == b"\r\n" or not line:
                    break
                line = line.decode().strip()
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key.lower()] = value

            # Check for WebSocket upgrade
            if headers.get("upgrade", "").lower() == "websocket":
                await self._handle_websocket(reader, writer, headers)
                return

            # Read body if present
            body = None
            content_length = int(headers.get("content-length", 0))
            if content_length > 0:
                body = await reader.read(content_length)
                body = body.decode()

            # Route request
            await self._route_request(method, path, headers, body, writer)

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Connection was closed by client - this is expected behavior
            logger.debug("Client connection closed: %s", e)
        except Exception as e:
            logger.error("Connection error: %s", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                # Ignore errors when closing already-closed connection
                pass

    async def _route_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[str],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Route HTTP request."""
        # Remove query string
        if "?" in path:
            path = path.split("?")[0]

        # API routes
        if path.startswith("/api/"):
            await self._handle_api(method, path, headers, body, writer)
            return

        # Static files
        await self._serve_static(path, writer)

    async def _handle_api(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[str],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle API requests."""
        try:
            # Parse body
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        response = None
        status = 200

        # Sessions
        if path == "/api/sessions":
            if method == "GET":
                sessions = await self.state.get_sessions()
                response = [s.to_dict() for s in sessions]
            elif method == "POST":
                # Extract psk_identity and client_ip from request
                psk_identity = data.get("pskIdentity") or data.get("psk_identity")
                client_ip = data.get("clientIp") or data.get("client_ip")
                metadata = data.get("metadata", {})

                # Also check metadata for these fields
                if not psk_identity:
                    psk_identity = metadata.get("psk_identity") or metadata.get("pskIdentity")
                if not client_ip:
                    client_ip = metadata.get("client_ip") or metadata.get("clientIp")

                session = await self.state.create_session(
                    name=data.get("name", f"Session {datetime.now().strftime('%H:%M:%S')}"),
                    psk_identity=psk_identity,
                    client_ip=client_ip,
                    **metadata,
                )
                response = session.to_dict()
                await self._broadcast("session.created", response)
                status = 201

        elif path.startswith("/api/sessions/") and "/apdus" not in path:
            session_id = path.split("/")[-1]

            if method == "GET":
                session = await self.state.get_session(session_id)
                if session:
                    response = session.to_dict()
                else:
                    status = 404
                    response = {"error": "Session not found"}

            elif method == "PATCH":
                session = await self.state.update_session(session_id, **data)
                if session:
                    response = session.to_dict()
                    await self._broadcast("session.updated", response)
                else:
                    status = 404
                    response = {"error": "Session not found"}

            elif method == "DELETE":
                if await self.state.delete_session(session_id):
                    response = {"success": True}
                    await self._broadcast("session.deleted", {"id": session_id})
                else:
                    status = 404
                    response = {"error": "Session not found"}

        # APDUs
        elif "/apdus" in path:
            parts = path.split("/")
            session_idx = parts.index("sessions") + 1
            session_id = parts[session_idx] if session_idx < len(parts) else None

            if method == "GET" and session_id:
                apdus = await self.state.get_apdus(session_id)
                response = [a.to_dict() for a in apdus]

            elif method == "POST" and session_id:
                apdu_hex = data.get("data", "")
                is_manual = data.get("manual", False)  # Flag for manually sent APDUs
                payload_format = data.get("payloadFormat", "auto")  # Payload format per ETSI TS 102.226

                # Queue the command for execution via AdminServer if connected
                if self._admin_server and apdu_hex:
                    handler = getattr(self._admin_server, '_handler', None)
                    if handler:
                        try:
                            # Convert hex string to bytes and queue
                            apdu_bytes = bytes.fromhex(apdu_hex.replace(" ", ""))
                            # Store manual flag in session for tracking
                            if is_manual:
                                if not hasattr(handler, '_manual_apdus'):
                                    handler._manual_apdus = {}
                                if session_id not in handler._manual_apdus:
                                    handler._manual_apdus[session_id] = set()
                                handler._manual_apdus[session_id].add(apdu_hex.upper().replace(" ", ""))
                            handler.queue_commands(session_id, [apdu_bytes])
                            logger.debug("Queued %sAPDU command for session %s: %s (format: %s)",
                                        "manual " if is_manual else "", session_id, apdu_hex, payload_format)
                            response = {"queued": True, "apdu": apdu_hex, "manual": is_manual, "payloadFormat": payload_format}
                            status = 202  # Accepted
                        except ValueError as e:
                            status = 400
                            response = {"error": f"Invalid APDU hex: {e}"}
                    else:
                        # AdminServer handler not ready - just log for now
                        apdu = await self.state.add_apdu(
                            session_id=session_id,
                            direction=data.get("direction", "command"),
                            data=apdu_hex,
                            sw=data.get("sw"),
                            response_data=data.get("responseData"),
                            manual=is_manual,
                            payload_format=payload_format,
                        )
                        if apdu:
                            response = apdu.to_dict()
                            await self._broadcast("apdu", response)
                            status = 201
                        else:
                            status = 404
                            response = {"error": "Session not found"}
                else:
                    # No AdminServer - just log the APDU
                    apdu = await self.state.add_apdu(
                        session_id=session_id,
                        direction=data.get("direction", "command"),
                        data=apdu_hex,
                        sw=data.get("sw"),
                        response_data=data.get("responseData"),
                        manual=is_manual,
                        payload_format=payload_format,
                    )
                    if apdu:
                        response = apdu.to_dict()
                        await self._broadcast("apdu", response)
                        status = 201
                    else:
                        status = 404
                        response = {"error": "Session not found"}

            elif method == "DELETE" and session_id:
                if await self.state.clear_apdus(session_id):
                    response = {"success": True}
                else:
                    status = 404
                    response = {"error": "Session not found"}

        # Status
        elif path == "/api/status":
            response = {
                "status": "running",
                "sessions": len(self.state.sessions),
                "clients": len(self._clients),
                "simulator_available": NETSIM_AVAILABLE,
                "simulator_connected": self._simulator is not None and self._simulator.is_connected,
                "server_available": ADMIN_SERVER_AVAILABLE,
                "server_connected": self.is_server_connected,
                "protocol_available": PROTOCOL_AVAILABLE,
                "scripts_available": SCRIPTS_API_AVAILABLE and self._scripts_api is not None,
            }

        # =====================================================================
        # APDU Scripts and Templates API
        # =====================================================================

        elif path.startswith("/api/scripts") or path.startswith("/api/templates"):
            if self._scripts_api is None:
                status = 503
                response = {"error": "Scripts API not available"}
            else:
                # Parse query params from URL (if any)
                query_params = {}
                response, status = self._scripts_api.handle_request(
                    method, path, query_params, body
                )

        # =====================================================================
        # Protocol Information API (GP SCP81 / ETSI TS 102.226)
        # =====================================================================

        elif path == "/api/protocol/info":
            if method == "GET":
                response = await self._get_protocol_info()

        elif path == "/api/protocol/ciphers":
            if method == "GET":
                response = await self._get_supported_ciphers()

        elif path == "/api/protocol/stats":
            if method == "GET":
                response = await self._get_protocol_stats()

        # =====================================================================
        # GP SCP81 Configuration API
        # =====================================================================

        elif path == "/api/scp81/config":
            if method == "GET":
                response = await self._get_scp81_config()
            elif method == "PUT":
                response = await self._update_scp81_config(body)

        elif path == "/api/scp81/keys":
            if method == "GET":
                response = await self._get_scp81_keys()
            elif method == "POST":
                response = await self._add_scp81_key(body)

        elif path.startswith("/api/scp81/keys/"):
            key_id = path.split("/")[-1]
            if method == "DELETE":
                response = await self._delete_scp81_key(key_id)

        elif path == "/api/scp81/trigger":
            if method == "GET":
                response = await self._get_trigger_params()
            elif method == "PUT":
                response = await self._update_trigger_params(body)

        # =====================================================================
        # Network Simulator API
        # =====================================================================

        elif path == "/api/simulator/status":
            if method == "GET":
                response = await self._get_simulator_status()

        elif path == "/api/simulator/connect":
            if method == "POST":
                response, status = await self._connect_simulator(data)

        elif path == "/api/simulator/disconnect":
            if method == "POST":
                response, status = await self._disconnect_simulator()

        elif path == "/api/simulator/ues":
            if method == "GET":
                response, status = await self._get_simulator_ues()

        elif path == "/api/simulator/sessions":
            if method == "GET":
                response, status = await self._get_simulator_sessions()

        elif path == "/api/simulator/events":
            if method == "GET":
                response = self._simulator_events[-100:]  # Last 100 events

        elif path == "/api/simulator/cell/start":
            if method == "POST":
                response, status = await self._start_simulator_cell(data)

        elif path == "/api/simulator/cell/stop":
            if method == "POST":
                response, status = await self._stop_simulator_cell()

        elif path == "/api/simulator/sms/send":
            if method == "POST":
                response, status = await self._send_simulator_sms(data)

        # =====================================================================
        # TLS PSK Server API
        # =====================================================================

        elif path == "/api/server/status":
            if method == "GET":
                response = await self._get_server_status()

        elif path == "/api/server/sessions":
            if method == "GET":
                response, status = await self._get_server_sessions()

        elif path == "/api/server/config":
            if method == "GET":
                response = await self._get_server_config()

        else:
            status = 404
            response = {"error": "Not found"}

        # Send response
        await self._send_json_response(writer, response, status)

    # Explicit MIME type mapping for ES modules and common web files
    MIME_TYPES = {
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".htm": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
    }

    async def _serve_static(
        self, path: str, writer: asyncio.StreamWriter
    ) -> None:
        """Serve static files."""
        # Default to index.html
        if path == "/" or path == "":
            path = "/index.html"

        # Security: prevent directory traversal
        file_path = self.config.static_dir / path.lstrip("/")
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.config.static_dir.resolve())):
                await self._send_error(writer, 403, "Forbidden")
                return
        except Exception:
            await self._send_error(writer, 400, "Bad request")
            return

        if not file_path.exists() or not file_path.is_file():
            await self._send_error(writer, 404, "Not found")
            return

        # Determine content type - use explicit mapping first for ES module compatibility
        suffix = file_path.suffix.lower()
        content_type = self.MIME_TYPES.get(suffix)
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        # Read and send file
        content = file_path.read_bytes()

        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + content

        writer.write(response)
        await writer.drain()

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        data: Any,
        status: int = 200,
    ) -> None:
        """Send JSON response."""
        body = json.dumps(data).encode()
        status_text = {200: "OK", 201: "Created", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}

        response = (
            f"HTTP/1.1 {status} {status_text.get(status, 'Unknown')}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + body

        writer.write(response)
        await writer.drain()

    async def _send_error(
        self, writer: asyncio.StreamWriter, status: int, message: str
    ) -> None:
        """Send error response."""
        await self._send_json_response(writer, {"error": message}, status)

    async def _handle_websocket(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        headers: Dict[str, str],
    ) -> None:
        """Handle WebSocket connection."""
        import base64
        import hashlib

        # Compute accept key
        key = headers.get("sec-websocket-key", "")
        accept = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
            ).digest()
        ).decode()

        # Send handshake response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        try:
            writer.write(response.encode())
            await writer.drain()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            logger.debug("WebSocket handshake failed - client disconnected: %s", e)
            return

        # Create client
        client = WebSocketClient(writer)
        self._clients[client.id] = client
        logger.info("WebSocket client connected: %s", client.id)

        try:
            while True:
                # Read frame header
                header = await reader.read(2)
                if len(header) < 2:
                    break

                fin = (header[0] >> 7) & 1
                opcode = header[0] & 0x0F
                masked = (header[1] >> 7) & 1
                payload_len = header[1] & 0x7F

                # Handle close frame
                if opcode == 0x8:
                    break

                # Read extended payload length
                if payload_len == 126:
                    ext_len = await reader.read(2)
                    payload_len = int.from_bytes(ext_len, "big")
                elif payload_len == 127:
                    ext_len = await reader.read(8)
                    payload_len = int.from_bytes(ext_len, "big")

                # Read mask key
                mask_key = await reader.read(4) if masked else None

                # Read payload
                payload = await reader.read(payload_len)

                # Unmask if needed
                if masked and mask_key:
                    payload = bytes(
                        payload[i] ^ mask_key[i % 4] for i in range(len(payload))
                    )

                # Handle text frame
                if opcode == 0x1:
                    try:
                        message = json.loads(payload.decode())
                        await self._handle_ws_message(client, message)
                    except json.JSONDecodeError:
                        pass

                # Handle ping
                elif opcode == 0x9:
                    # Send pong
                    try:
                        pong = bytes([0x8A, len(payload)]) + payload
                        writer.write(pong)
                        await writer.drain()
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                        # Client disconnected
                        break

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Connection was closed by client - this is expected behavior
            logger.debug("WebSocket client disconnected: %s", e)
        except Exception as e:
            logger.debug("WebSocket error: %s", e)
        finally:
            self._clients.pop(client.id, None)
            logger.info("WebSocket client disconnected: %s", client.id)

    async def _handle_ws_message(
        self, client: WebSocketClient, message: Dict[str, Any]
    ) -> None:
        """Handle incoming WebSocket message."""
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == "subscribe":
            # Subscribe to events
            client.subscriptions.add(payload.get("channel", "*"))

        elif msg_type == "unsubscribe":
            # Unsubscribe from events
            client.subscriptions.discard(payload.get("channel", "*"))

        elif msg_type == "ping":
            await client.send({"type": "pong", "payload": {}})

    async def _broadcast(self, event_type: str, data: Any) -> None:
        """Broadcast message to all connected clients."""
        message = {"type": event_type, "payload": data}

        for client in list(self._clients.values()):
            try:
                await client.send(message)
            except Exception:
                pass

    # =========================================================================
    # Public API for external integration
    # =========================================================================

    async def emit_apdu(
        self,
        session_id: str,
        direction: str,
        data: str,
        sw: Optional[str] = None,
        response_data: Optional[str] = None,
    ) -> Optional[APDUEntry]:
        """Emit an APDU event to all clients.

        This is the main entry point for integrating the dashboard
        with the APDU capture system.

        Args:
            session_id: Session ID.
            direction: 'command' or 'response'.
            data: APDU data (hex string).
            sw: Status word for responses.
            response_data: Response data for responses.

        Returns:
            Created APDU entry or None if session not found.
        """
        apdu = await self.state.add_apdu(
            session_id=session_id,
            direction=direction,
            data=data,
            sw=sw,
            response_data=response_data,
        )

        if apdu:
            await self._broadcast("apdu", apdu.to_dict())

        return apdu

    def on_apdu(self, callback: Callable) -> None:
        """Register callback for APDU events.

        Args:
            callback: Function to call when APDU is received.
        """
        self._apdu_callbacks.append(callback)

    # =========================================================================
    # Protocol Information API (GP SCP81 / ETSI TS 102.226)
    # =========================================================================

    async def _get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol layer information."""
        if not PROTOCOL_AVAILABLE:
            return {
                "available": False,
                "error": "Protocol module not installed",
            }

        return {
            "available": True,
            "standards": [
                {
                    "name": "GlobalPlatform RAM over HTTP",
                    "version": "1.1.2",
                    "spec": "Amendment B",
                    "features": ["SCP81 (PSK-TLS)", "RAM commands", "HTTP Admin protocol"],
                },
                {
                    "name": "ETSI TS 102.226",
                    "version": "latest",
                    "features": ["Remote APDU", "Command Scripting", "Response Scripting"],
                },
            ],
            "supportedCommands": {
                "ram": [
                    {"ins": "0xE4", "name": "DELETE"},
                    {"ins": "0xE6", "name": "INSTALL"},
                    {"ins": "0xE8", "name": "LOAD"},
                    {"ins": "0xD8", "name": "PUT KEY"},
                    {"ins": "0xE2", "name": "STORE DATA"},
                    {"ins": "0xF2", "name": "GET STATUS"},
                    {"ins": "0xF0", "name": "SET STATUS"},
                ],
                "standard": [
                    {"ins": "0xA4", "name": "SELECT"},
                    {"ins": "0xB0", "name": "READ BINARY"},
                    {"ins": "0xB2", "name": "READ RECORD"},
                    {"ins": "0xC0", "name": "GET RESPONSE"},
                    {"ins": "0xCA", "name": "GET DATA"},
                ],
            },
        }

    async def _get_supported_ciphers(self) -> Dict[str, Any]:
        """Get supported PSK-TLS cipher suites."""
        if not PROTOCOL_AVAILABLE:
            return {
                "available": False,
                "ciphers": [],
            }

        # Get cipher suites from the protocol layer
        try:
            cipher_suites = get_supported_cipher_suites()
            ciphers = [
                {
                    "id": f"0x{CIPHER_SUITE_IDS.get(cs.name, 0):04X}",
                    "name": cs.name,
                    "keyType": cs.name.split('-')[0],  # PSK, RSA-PSK, etc.
                }
                for cs in cipher_suites
            ]
        except Exception:
            ciphers = [
                {"id": "0x008C", "name": "PSK-AES128-CBC-SHA", "keyType": "PSK"},
                {"id": "0x008D", "name": "PSK-AES256-CBC-SHA", "keyType": "PSK"},
                {"id": "0x00AE", "name": "PSK-AES128-CBC-SHA256", "keyType": "PSK"},
                {"id": "0x00AF", "name": "PSK-AES256-CBC-SHA384", "keyType": "PSK"},
            ]

        return {
            "available": True,
            "ciphers": ciphers,
            "keyTypes": [
                {"type": "PSK", "description": "Pre-Shared Key (SCP81)"},
                {"type": "RSA-PSK", "description": "RSA + PSK hybrid"},
            ],
        }

    async def _get_protocol_stats(self) -> Dict[str, Any]:
        """Get protocol statistics from sessions."""
        sessions = await self.state.get_sessions()

        # Aggregate statistics
        total_ram = sum(s.ram_command_count for s in sessions)
        total_rfm = sum(s.rfm_command_count for s in sessions)
        total_scripts = sum(s.script_count for s in sessions)
        total_apdus = sum(s.apdu_count for s in sessions)

        # Cipher suite distribution
        cipher_counts: Dict[str, int] = {}
        for s in sessions:
            if s.cipher_suite:
                cipher_counts[s.cipher_suite] = cipher_counts.get(s.cipher_suite, 0) + 1

        # TLS version distribution
        tls_counts: Dict[str, int] = {}
        for s in sessions:
            if s.tls_version:
                tls_counts[s.tls_version] = tls_counts.get(s.tls_version, 0) + 1

        return {
            "sessionCount": len(sessions),
            "totalApdus": total_apdus,
            "ramCommands": total_ram,
            "rfmCommands": total_rfm,
            "scriptCount": total_scripts,
            "cipherDistribution": cipher_counts,
            "tlsVersionDistribution": tls_counts,
        }

    # =========================================================================
    # GP SCP81 Configuration API Implementation
    # =========================================================================

    async def _get_scp81_config(self) -> Dict[str, Any]:
        """Get current SCP81 configuration."""
        # Get default cipher suites from protocol layer
        default_ciphers = []
        if PROTOCOL_AVAILABLE:
            # Get all PSK cipher suites from the enum
            default_ciphers = [cs.name for cs in PSKCipherSuite]

        # If no admin server connected, return protocol defaults
        if not self._admin_server:
            return {
                "available": True,
                "connected": False,
                "protocol": "SCP81",
                "protocolVersion": "1.1.2",
                "tlsVersion": "TLSv1.2",
                "supportedCiphers": default_ciphers,
                "enabledCiphers": default_ciphers[:4] if default_ciphers else [],
                "nullCiphersEnabled": False,
                "sessionTimeout": 300,
                "handshakeTimeout": 30,
                "message": "Showing protocol defaults (server not connected)",
            }

        try:
            config = getattr(self._admin_server, 'config', None)
            if not config:
                return {
                    "available": True,
                    "connected": True,
                    "protocol": "SCP81",
                    "protocolVersion": "1.1.2",
                    "tlsVersion": "TLSv1.2",
                    "supportedCiphers": default_ciphers,
                    "enabledCiphers": default_ciphers[:4] if default_ciphers else [],
                    "nullCiphersEnabled": False,
                    "sessionTimeout": 300,
                    "handshakeTimeout": 30,
                }

            return {
                "available": True,
                "connected": True,
                "protocol": "SCP81",
                "protocolVersion": "1.1.2",
                "tlsVersion": getattr(config, 'tls_version', 'TLSv1.2'),
                "supportedCiphers": default_ciphers,
                "enabledCiphers": getattr(config, 'cipher_suites', default_ciphers),
                "nullCiphersEnabled": getattr(config, 'enable_null_ciphers', False),
                "sessionTimeout": getattr(config, 'session_timeout', 300),
                "handshakeTimeout": getattr(config, 'handshake_timeout', 30),
            }
        except Exception as e:
            logger.error("Failed to get SCP81 config: %s", e)
            return {"available": False, "error": str(e)}

    async def _update_scp81_config(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update SCP81 configuration."""
        if not self._admin_server:
            return {"error": "Server not connected"}, 503

        try:
            config = getattr(self._admin_server, 'config', None)
            if not config:
                return {"error": "Server config not available"}, 500

            # Update allowed fields
            if 'sessionTimeout' in body:
                config.session_timeout = int(body['sessionTimeout'])
            if 'handshakeTimeout' in body:
                config.handshake_timeout = int(body['handshakeTimeout'])
            if 'enabledCiphers' in body:
                config.cipher_suites = body['enabledCiphers']

            logger.info("SCP81 config updated: %s", body)
            return {"success": True, "message": "Configuration updated"}
        except Exception as e:
            logger.error("Failed to update SCP81 config: %s", e)
            return {"error": str(e)}, 500

    async def _get_scp81_keys(self) -> Dict[str, Any]:
        """Get configured PSK keys."""
        # Initialize local key storage if needed
        if not hasattr(self, '_local_scp81_keys'):
            self._local_scp81_keys = {}

        # If no admin server, return local keys
        if not self._admin_server:
            keys = list(self._local_scp81_keys.values())
            return {
                "keys": keys,
                "count": len(keys),
                "connected": False,
                "message": "Using local key storage (server not connected)",
            }

        try:
            key_manager = getattr(self._admin_server, '_key_manager', None)
            if not key_manager:
                return {
                    "keys": list(self._local_scp81_keys.values()),
                    "count": len(self._local_scp81_keys),
                    "connected": True,
                    "message": "Key manager not available, showing local keys",
                }

            keys = []
            all_keys = getattr(key_manager, 'get_all_keys', lambda: [])()
            for key in all_keys:
                keys.append({
                    "identity": key.identity if hasattr(key, 'identity') else str(key),
                    "keyId": getattr(key, 'key_id', 0),
                    "keyVersion": getattr(key, 'key_version', 1),
                    "algorithm": getattr(key, 'algorithm', 'AES-128'),
                    "active": getattr(key, 'active', True),
                })

            return {"keys": keys, "count": len(keys), "connected": True}
        except Exception as e:
            logger.error("Failed to get SCP81 keys: %s", e)
            return {"keys": [], "error": str(e)}

    async def _add_scp81_key(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new PSK key."""
        # Initialize local key storage if needed
        if not hasattr(self, '_local_scp81_keys'):
            self._local_scp81_keys = {}

        identity = body.get('identity')
        key_hex = body.get('keyHex') or body.get('key')
        key_id = body.get('keyId', f"key_{len(self._local_scp81_keys) + 1}")
        key_version = body.get('keyVersion', 1)
        cipher_suites = body.get('cipherSuites', [])

        if not identity or not key_hex:
            return {"error": "identity and keyHex are required"}, 400

        try:
            # Validate key format
            key_bytes = bytes.fromhex(key_hex)
            if len(key_bytes) not in (16, 24, 32):
                return {"error": "Key must be 16, 24, or 32 bytes (128/192/256-bit)"}, 400

            # Compute KCV
            kcv = key_bytes[:3].hex().upper()

            key_entry = {
                "keyId": key_id,
                "identity": identity,
                "keyVersion": key_version,
                "algorithm": f"AES-{len(key_bytes) * 8}",
                "cipherSuites": cipher_suites,
                "kcv": kcv,
                "active": True,
            }

            # If admin server is connected, try to add to server
            if self._admin_server:
                key_manager = getattr(self._admin_server, '_key_manager', None)
                if key_manager:
                    try:
                        add_fn = getattr(key_manager, 'add_key', None)
                        if add_fn:
                            add_fn(identity, key_bytes, key_id=key_id, key_version=key_version)
                            logger.info("Added PSK key to server: identity=%s, keyId=%s", identity, key_id)
                    except Exception as e:
                        logger.warning("Failed to add key to server: %s", e)

            # Always store locally as well
            self._local_scp81_keys[key_id] = key_entry
            logger.info("Added PSK key locally: identity=%s, keyId=%s", identity, key_id)

            return {"success": True, "key": key_entry}
        except ValueError as e:
            return {"error": f"Invalid key format: {e}"}, 400
        except Exception as e:
            logger.error("Failed to add SCP81 key: %s", e)
            return {"error": str(e)}, 500

    async def _delete_scp81_key(self, key_id: str) -> Dict[str, Any]:
        """Delete a PSK key."""
        # Initialize local key storage if needed
        if not hasattr(self, '_local_scp81_keys'):
            self._local_scp81_keys = {}

        deleted_from_server = False
        deleted_from_local = False

        # Try to delete from server if connected
        if self._admin_server:
            try:
                key_manager = getattr(self._admin_server, '_key_manager', None)
                if key_manager:
                    remove_fn = getattr(key_manager, 'remove_key', None)
                    if remove_fn:
                        remove_fn(key_id)
                        deleted_from_server = True
                        logger.info("Deleted PSK key from server: %s", key_id)
            except KeyError:
                pass  # Key not on server
            except Exception as e:
                logger.warning("Failed to delete key from server: %s", e)

        # Also delete from local storage
        if key_id in self._local_scp81_keys:
            del self._local_scp81_keys[key_id]
            deleted_from_local = True
            logger.info("Deleted PSK key locally: %s", key_id)

        if deleted_from_server or deleted_from_local:
            return {"success": True, "keyId": key_id}
        else:
            return {"error": f"Key not found: {key_id}"}, 404

    async def _get_trigger_params(self) -> Dict[str, Any]:
        """Get session trigger parameters."""
        if not PROTOCOL_AVAILABLE:
            return {
                "available": False,
                "message": "Protocol module not available",
            }

        try:
            # Return supported trigger parameter tags
            return {
                "available": True,
                "supportedTags": {
                    "adminUrl": "5F50",
                    "cipherSuite": "81",
                    "pskIdentity": "84",
                    "retryPolicy": "85",
                    "triggerTime": "86",
                },
                "retryPolicies": [
                    {"id": 0, "name": "No retry"},
                    {"id": 1, "name": "Retry once"},
                    {"id": 2, "name": "Retry until success"},
                    {"id": 3, "name": "Retry with backoff"},
                ],
            }
        except Exception as e:
            logger.error("Failed to get trigger params: %s", e)
            return {"available": False, "error": str(e)}

    async def _update_trigger_params(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update trigger parameters for next session."""
        if not PROTOCOL_AVAILABLE:
            return {"error": "Protocol module not available"}, 503

        try:
            # Store trigger params for next session
            trigger_config = {
                "adminUrl": body.get('adminUrl'),
                "cipherSuite": body.get('cipherSuite'),
                "pskIdentity": body.get('pskIdentity'),
                "retryPolicy": body.get('retryPolicy', 0),
            }

            # Store in state for next session
            self.state._trigger_params = trigger_config
            logger.info("Trigger params updated: %s", trigger_config)
            return {"success": True, "params": trigger_config}
        except Exception as e:
            logger.error("Failed to update trigger params: %s", e)
            return {"error": str(e)}, 500

    # =========================================================================
    # TLS PSK Server API Implementation
    # =========================================================================

    async def _get_server_status(self) -> Dict[str, Any]:
        """Get TLS PSK Admin Server status."""
        if not ADMIN_SERVER_AVAILABLE:
            return {
                "available": False,
                "connected": False,
                "running": False,
                "error": "AdminServer module not installed",
            }

        if self._admin_server is None:
            return {
                "available": True,
                "connected": False,
                "running": False,
                "message": "Dashboard not connected to server. Start with: gp-server start --dashboard",
            }

        try:
            is_running = getattr(self._admin_server, 'is_running', False)
            config = getattr(self._admin_server, 'config', None)

            # Get session counts from session manager
            session_manager = getattr(self._admin_server, '_session_manager', None)
            active_sessions = 0
            total_sessions = 0
            if session_manager:
                active_sessions = session_manager.get_active_session_count()
                total_sessions = session_manager.get_session_count()

            return {
                "available": True,
                "connected": True,
                "running": is_running,
                "host": config.host if config else None,
                "port": config.port if config else None,
                "activeSessions": active_sessions,
                "totalSessions": total_sessions,
            }
        except Exception as e:
            logger.error("Failed to get server status: %s", e)
            return {
                "available": True,
                "connected": True,
                "running": False,
                "error": str(e),
            }

    async def _get_server_sessions(self) -> tuple:
        """Get sessions from TLS PSK Admin Server."""
        if not self._admin_server:
            return {"error": "Server not connected"}, 503

        try:
            session_manager = getattr(self._admin_server, '_session_manager', None)
            if not session_manager:
                return {"error": "Session manager not available"}, 500

            sessions = session_manager.get_all_sessions()
            result = []
            for session in sessions:
                result.append({
                    "id": session.session_id,
                    "state": session.state.name if hasattr(session.state, 'name') else str(session.state),
                    "pskIdentity": session.psk_identity,
                    "clientAddress": list(session.client_address) if session.client_address else None,
                    "createdAt": session.created_at.isoformat() if session.created_at else None,
                    "lastActivity": session.last_activity.isoformat() if session.last_activity else None,
                    "exchangeCount": len(session.apdu_exchanges) if hasattr(session, 'apdu_exchanges') else 0,
                    "tlsInfo": {
                        "cipher": session.tls_info.cipher_suite if session.tls_info else None,
                        "version": session.tls_info.protocol_version if session.tls_info else None,
                    } if session.tls_info else None,
                })

            return result, 200
        except Exception as e:
            logger.error("Failed to get server sessions: %s", e)
            return {"error": str(e)}, 500

    async def _get_server_config(self) -> Dict[str, Any]:
        """Get TLS PSK Admin Server configuration."""
        if not self._admin_server:
            return {
                "connected": False,
                "error": "Server not connected",
            }

        try:
            config = getattr(self._admin_server, 'config', None)
            if not config:
                return {"error": "Config not available"}

            cipher_config = getattr(config, 'cipher_config', None)

            return {
                "connected": True,
                "host": config.host,
                "port": config.port,
                "maxConnections": config.max_connections,
                "sessionTimeout": config.session_timeout,
                "handshakeTimeout": config.handshake_timeout,
                "cipherConfig": {
                    "enableLegacy": cipher_config.enable_legacy if cipher_config else False,
                    "enableNullCiphers": cipher_config.enable_null_ciphers if cipher_config else False,
                    "enabledCiphers": cipher_config.get_enabled_ciphers() if cipher_config else [],
                } if cipher_config else None,
            }
        except Exception as e:
            logger.error("Failed to get server config: %s", e)
            return {"error": str(e)}

    # =========================================================================
    # Network Simulator API Implementation
    # =========================================================================

    async def _get_simulator_status(self) -> Dict[str, Any]:
        """Get network simulator status."""
        if not NETSIM_AVAILABLE:
            return {
                "available": False,
                "connected": False,
                "error": "Network simulator module not installed",
            }

        if self._simulator is None or not self._simulator.is_connected:
            return {
                "available": True,
                "connected": False,
                "ue_count": 0,
                "session_count": 0,
            }

        try:
            status = await self._simulator.get_status()
            return {
                "available": True,
                "connected": status.connected,
                "authenticated": status.authenticated,
                "ue_count": status.ue_count,
                "session_count": status.session_count,
                "cell": status.cell.to_dict() if status.cell else None,
                "error": status.error,
            }
        except Exception as e:
            logger.error("Failed to get simulator status: %s", e)
            return {
                "available": True,
                "connected": False,
                "error": str(e),
            }

    async def _connect_simulator(
        self, data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """Connect to network simulator."""
        if not NETSIM_AVAILABLE:
            return {"error": "Network simulator module not installed"}, 400

        if self._simulator is not None and self._simulator.is_connected:
            return {"error": "Already connected to simulator"}, 400

        # Get connection parameters
        url = data.get("url")
        if not url:
            return {"error": "URL is required"}, 400

        simulator_type_str = data.get("simulator_type", "amarisoft")
        api_key = data.get("api_key")

        # Parse simulator type
        try:
            simulator_type = SimulatorType(simulator_type_str.lower())
        except ValueError:
            return {"error": f"Unknown simulator type: {simulator_type_str}"}, 400

        # Build TLS config if provided
        tls_config = None
        if data.get("tls"):
            tls_data = data["tls"]
            tls_config = TLSConfig(
                verify_ssl=tls_data.get("verify_ssl", True),
                ca_cert=tls_data.get("ca_cert"),
                client_cert=tls_data.get("client_cert"),
                client_key=tls_data.get("client_key"),
            )

        # Build config
        config = SimulatorConfig(
            url=url,
            simulator_type=simulator_type,
            api_key=api_key,
            tls_config=tls_config,
            auto_reconnect=data.get("auto_reconnect", True),
            connect_timeout=data.get("connect_timeout", 30.0),
        )

        try:
            # Create manager and connect
            self._simulator = SimulatorManager(config)

            # Register event handlers for broadcasting
            self._simulator.events.on("simulator_connected", self._on_simulator_event)
            self._simulator.events.on("simulator_disconnected", self._on_simulator_event)
            self._simulator.events.on("simulator_error", self._on_simulator_event)
            self._simulator.events.on("ue_registered", self._on_simulator_event)
            self._simulator.events.on("ue_deregistered", self._on_simulator_event)
            self._simulator.events.on("session_created", self._on_simulator_event)
            self._simulator.events.on("session_released", self._on_simulator_event)
            self._simulator.events.on("sms_sent", self._on_simulator_event)
            self._simulator.events.on("sms_received", self._on_simulator_event)
            self._simulator.events.on("cell_started", self._on_simulator_event)
            self._simulator.events.on("cell_stopped", self._on_simulator_event)

            await self._simulator.connect()

            # Broadcast connection event
            await self._broadcast("simulator.connected", {
                "url": url,
                "simulator_type": simulator_type.value,
            })

            return {
                "success": True,
                "url": url,
                "simulator_type": simulator_type.value,
            }, 200

        except Exception as e:
            logger.error("Failed to connect to simulator: %s", e)
            self._simulator = None
            return {"error": str(e)}, 500

    async def _disconnect_simulator(self) -> tuple[Dict[str, Any], int]:
        """Disconnect from network simulator."""
        if self._simulator is None:
            return {"error": "Not connected to simulator"}, 400

        try:
            await self._simulator.disconnect()
            self._simulator = None

            # Broadcast disconnection event
            await self._broadcast("simulator.disconnected", {})

            return {"success": True}, 200

        except Exception as e:
            logger.error("Failed to disconnect from simulator: %s", e)
            return {"error": str(e)}, 500

    async def _get_simulator_ues(self) -> tuple[Any, int]:
        """Get list of UEs from simulator."""
        if self._simulator is None or not self._simulator.is_connected:
            return {"error": "Not connected to simulator"}, 400

        try:
            ues = await self._simulator.ue.list_ues()
            return [ue.to_dict() for ue in ues], 200
        except NotConnectedError:
            return {"error": "Not connected to simulator"}, 400
        except Exception as e:
            logger.error("Failed to get UEs: %s", e)
            return {"error": str(e)}, 500

    async def _get_simulator_sessions(self) -> tuple[Any, int]:
        """Get list of data sessions from simulator."""
        if self._simulator is None or not self._simulator.is_connected:
            return {"error": "Not connected to simulator"}, 400

        try:
            sessions = await self._simulator.sessions.list_sessions()
            return [s.to_dict() for s in sessions], 200
        except NotConnectedError:
            return {"error": "Not connected to simulator"}, 400
        except Exception as e:
            logger.error("Failed to get sessions: %s", e)
            return {"error": str(e)}, 500

    async def _start_simulator_cell(
        self, data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """Start the simulated cell."""
        if self._simulator is None or not self._simulator.is_connected:
            return {"error": "Not connected to simulator"}, 400

        try:
            timeout = data.get("timeout", 60.0)
            success = await self._simulator.cell.start(timeout=timeout)

            if success:
                await self._broadcast("simulator.cell_started", {})
                return {"success": True}, 200
            else:
                return {"error": "Cell start timed out"}, 500

        except NotConnectedError:
            return {"error": "Not connected to simulator"}, 400
        except Exception as e:
            logger.error("Failed to start cell: %s", e)
            return {"error": str(e)}, 500

    async def _stop_simulator_cell(self) -> tuple[Dict[str, Any], int]:
        """Stop the simulated cell."""
        if self._simulator is None or not self._simulator.is_connected:
            return {"error": "Not connected to simulator"}, 400

        try:
            success = await self._simulator.cell.stop()

            if success:
                await self._broadcast("simulator.cell_stopped", {})
                return {"success": True}, 200
            else:
                return {"error": "Cell stop timed out"}, 500

        except NotConnectedError:
            return {"error": "Not connected to simulator"}, 400
        except Exception as e:
            logger.error("Failed to stop cell: %s", e)
            return {"error": str(e)}, 500

    async def _send_simulator_sms(
        self, data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], int]:
        """Send SMS via simulator."""
        if self._simulator is None or not self._simulator.is_connected:
            return {"error": "Not connected to simulator"}, 400

        imsi = data.get("imsi")
        if not imsi:
            return {"error": "IMSI is required"}, 400

        pdu = data.get("pdu")
        text = data.get("text")

        if not pdu and not text:
            return {"error": "Either pdu or text is required"}, 400

        try:
            # Convert hex PDU to bytes if provided
            pdu_bytes = bytes.fromhex(pdu) if pdu else None

            message_id = await self._simulator.sms.send_mt_sms(
                imsi=imsi,
                pdu=pdu_bytes,
                text=text,
            )

            await self._broadcast("simulator.sms_sent", {
                "imsi": imsi,
                "message_id": message_id,
            })

            return {"success": True, "message_id": message_id}, 200

        except NotConnectedError:
            return {"error": "Not connected to simulator"}, 400
        except Exception as e:
            logger.error("Failed to send SMS: %s", e)
            return {"error": str(e)}, 500

    async def _on_simulator_event(
        self, event_name: str, data: Dict[str, Any]
    ) -> None:
        """Handle simulator events and broadcast to clients."""
        # Store event
        event_entry = {
            "type": event_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        self._simulator_events.append(event_entry)

        # Trim events if needed
        if len(self._simulator_events) > self._max_events:
            self._simulator_events = self._simulator_events[-self._max_events:]

        # Broadcast to WebSocket clients
        await self._broadcast(f"simulator.{event_name}", data)


async def start_dashboard(
    host: str = "127.0.0.1",
    port: int = 8080,
) -> DashboardServer:
    """Start the dashboard server.

    Args:
        host: Host to bind to.
        port: Port to bind to.

    Returns:
        DashboardServer instance.

    Example:
        >>> server = await start_dashboard(port=8080)
    """
    config = DashboardConfig(host=host, port=port)
    server = DashboardServer(config)

    # Start in background
    asyncio.create_task(server.start())

    return server
