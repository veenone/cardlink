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
from typing import Any, Callable, Dict, List, Optional, Set

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


@dataclass
class Session:
    """Test session."""

    id: str
    name: str
    status: str = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    apdu_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    psk_identity: Optional[str] = None
    client_ip: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Include psk_identity and client_ip in metadata for frontend
        metadata = dict(self.metadata)
        if self.psk_identity:
            metadata["psk_identity"] = self.psk_identity
        if self.client_ip:
            metadata["client_ip"] = self.client_ip

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
        }


@dataclass
class APDUEntry:
    """APDU log entry."""

    id: str
    session_id: str
    timestamp: datetime
    direction: str  # 'command' or 'response'
    data: str
    sw: Optional[str] = None
    response_data: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

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
        }


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
        **metadata,
    ) -> Session:
        """Create a new session.

        Args:
            name: Session display name.
            psk_identity: PSK identity (typically ICCID) for the connection.
            client_ip: Client IP address.
            **metadata: Additional metadata.

        Returns:
            Created session.
        """
        async with self._lock:
            # Use psk_identity as name if name is generic
            display_name = name
            if psk_identity and (not name or name.startswith("Session ")):
                display_name = psk_identity

            session = Session(
                id=str(uuid.uuid4()),
                name=display_name,
                psk_identity=psk_identity,
                client_ip=client_ip,
                metadata=metadata,
            )
            self.sessions[session.id] = session
            self.apdus[session.id] = []
            return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

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
        """Add an APDU entry."""
        async with self._lock:
            if session_id not in self.sessions:
                return None

            entry = APDUEntry(
                id=str(uuid.uuid4()),
                session_id=session_id,
                timestamp=datetime.now(),
                direction=direction,
                data=data,
                sw=sw,
                response_data=response_data,
                metadata=metadata,
            )

            if session_id not in self.apdus:
                self.apdus[session_id] = []

            self.apdus[session_id].append(entry)
            self.sessions[session_id].apdu_count = len(self.apdus[session_id])
            self.sessions[session_id].updated_at = datetime.now()

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

    async def start(self) -> None:
        """Start the server."""
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
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Dashboard server stopped")

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

        except Exception as e:
            logger.error("Connection error: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()

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
                apdu = await self.state.add_apdu(
                    session_id=session_id,
                    direction=data.get("direction", "command"),
                    data=data.get("data", ""),
                    sw=data.get("sw"),
                    response_data=data.get("responseData"),
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
            }

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

        else:
            status = 404
            response = {"error": "Not found"}

        # Send response
        await self._send_json_response(writer, response, status)

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

        # Determine content type
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
        writer.write(response.encode())
        await writer.drain()

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
                    pong = bytes([0x8A, len(payload)]) + payload
                    writer.write(pong)
                    await writer.drain()

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
