"""Dashboard Server for GP OTA Tester.

This module provides a web server for the dashboard frontend with:
- Static file serving
- REST API endpoints
- WebSocket support for real-time updates

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "apduCount": self.apdu_count,
            "metadata": self.metadata,
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

    async def create_session(self, name: str, **metadata) -> Session:
        """Create a new session."""
        async with self._lock:
            session = Session(
                id=str(uuid.uuid4()),
                name=name,
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

    async def start(self) -> None:
        """Start the server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.config.host,
            self.config.port,
        )

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
                session = await self.state.create_session(
                    name=data.get("name", f"Session {datetime.now().strftime('%H:%M:%S')}"),
                    **data.get("metadata", {}),
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
            }

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
