"""Mock Amarisoft Simulator for testing.

This module provides a mock WebSocket server that simulates
the Amarisoft Remote API for testing purposes.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class MockUE:
    """Mock UE state."""

    imsi: str
    status: str = "registered"
    cell_id: int = 1
    ip_address: str = "10.0.0.100"
    imei: Optional[str] = None


@dataclass
class MockSession:
    """Mock data session."""

    session_id: str
    imsi: str
    apn: str = "internet"
    ip_address: str = "10.0.0.100"
    qci: int = 9


@dataclass
class MockCell:
    """Mock cell state."""

    cell_id: int = 1
    status: str = "active"
    plmn: str = "001-01"
    frequency: int = 1950
    bandwidth: int = 20
    tx_power: int = 23


class MockAmarisoftServer:
    """Mock Amarisoft WebSocket server for testing.

    Simulates the JSON-RPC 2.0 API of Amarisoft Remote API.

    Example:
        >>> server = MockAmarisoftServer()
        >>> await server.start("localhost", 9001)
        >>> # Run tests...
        >>> await server.stop()
    """

    def __init__(self) -> None:
        """Initialize mock server."""
        self._server: Optional[Any] = None
        self._clients: list[Any] = []

        # Mock state
        self._ues: dict[str, MockUE] = {}
        self._sessions: dict[str, MockSession] = {}
        self._cell = MockCell()
        self._authenticated = False
        self._api_key: Optional[str] = None

        # Event handlers
        self._event_callbacks: list[Callable] = []

        # Configuration
        self._config: dict[str, Any] = {
            "cell": {
                "plmn": "001-01",
                "frequency": 1950,
                "bandwidth": 20,
                "tx_power": 23,
            },
            "network": {
                "apn": "internet",
            },
        }

    async def start(self, host: str = "localhost", port: int = 9001) -> None:
        """Start the mock server.

        Args:
            host: Host to bind to.
            port: Port to listen on.
        """
        try:
            import websockets
        except ImportError:
            raise RuntimeError("websockets package required for mock server")

        self._server = await websockets.serve(
            self._handle_client,
            host,
            port,
        )
        log.info(f"Mock Amarisoft server started on ws://{host}:{port}")

    async def stop(self) -> None:
        """Stop the mock server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            log.info("Mock Amarisoft server stopped")

    async def _handle_client(self, websocket: Any, path: str) -> None:
        """Handle WebSocket client connection.

        Args:
            websocket: WebSocket connection.
            path: Request path.
        """
        self._clients.append(websocket)
        log.debug(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                response = await self._process_message(message)
                if response:
                    await websocket.send(json.dumps(response))
        except Exception as e:
            log.error(f"Client error: {e}")
        finally:
            self._clients.remove(websocket)
            log.debug("Client disconnected")

    async def _process_message(self, message: str) -> Optional[dict[str, Any]]:
        """Process incoming JSON-RPC message.

        Args:
            message: Raw JSON message.

        Returns:
            Response dictionary or None.
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return self._error_response(None, -32700, "Parse error")

        # Validate JSON-RPC 2.0 format
        if data.get("jsonrpc") != "2.0":
            return self._error_response(
                data.get("id"), -32600, "Invalid Request"
            )

        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        log.debug(f"Request: {method} {params}")

        # Route to handler
        handler = self._get_handler(method)
        if not handler:
            return self._error_response(request_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(params)
            return self._success_response(request_id, result)
        except Exception as e:
            return self._error_response(request_id, -32000, str(e))

    def _get_handler(self, method: str) -> Optional[Callable]:
        """Get handler for JSON-RPC method.

        Args:
            method: Method name.

        Returns:
            Handler function or None.
        """
        handlers = {
            "authenticate": self._handle_authenticate,
            "ue.list": self._handle_ue_list,
            "ue.get": self._handle_ue_get,
            "ue.detach": self._handle_ue_detach,
            "session.list": self._handle_session_list,
            "session.get": self._handle_session_get,
            "session.release": self._handle_session_release,
            "sms.send": self._handle_sms_send,
            "enb.get_status": self._handle_cell_status,
            "enb.start": self._handle_cell_start,
            "enb.stop": self._handle_cell_stop,
            "enb.configure": self._handle_cell_configure,
            "config.get": self._handle_config_get,
            "config.set": self._handle_config_set,
            "event.subscribe": self._handle_event_subscribe,
            "trigger": self._handle_trigger,
        }
        return handlers.get(method)

    def _success_response(self, request_id: Any, result: Any) -> dict[str, Any]:
        """Create success response.

        Args:
            request_id: Request ID.
            result: Result data.

        Returns:
            JSON-RPC response.
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
    ) -> dict[str, Any]:
        """Create error response.

        Args:
            request_id: Request ID.
            code: Error code.
            message: Error message.

        Returns:
            JSON-RPC error response.
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    # =========================================================================
    # Method Handlers
    # =========================================================================

    async def _handle_authenticate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle authenticate method."""
        api_key = params.get("api_key")
        if self._api_key and api_key != self._api_key:
            raise Exception("Invalid API key")

        self._authenticated = True
        return {"authenticated": True, "user": "test_user"}

    async def _handle_ue_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle ue.list method."""
        return [
            {
                "imsi": ue.imsi,
                "status": ue.status,
                "cell_id": ue.cell_id,
                "ip_address": ue.ip_address,
                "imei": ue.imei,
            }
            for ue in self._ues.values()
        ]

    async def _handle_ue_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ue.get method."""
        imsi = params.get("imsi")
        if imsi not in self._ues:
            raise Exception(f"UE not found: {imsi}")

        ue = self._ues[imsi]
        return {
            "imsi": ue.imsi,
            "status": ue.status,
            "cell_id": ue.cell_id,
            "ip_address": ue.ip_address,
            "imei": ue.imei,
        }

    async def _handle_ue_detach(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ue.detach method."""
        imsi = params.get("imsi")
        if imsi in self._ues:
            del self._ues[imsi]
        return {"success": True, "imsi": imsi}

    async def _handle_session_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle session.list method."""
        imsi = params.get("imsi")
        sessions = self._sessions.values()
        if imsi:
            sessions = [s for s in sessions if s.imsi == imsi]

        return [
            {
                "session_id": s.session_id,
                "imsi": s.imsi,
                "apn": s.apn,
                "ip_address": s.ip_address,
                "qci": s.qci,
            }
            for s in sessions
        ]

    async def _handle_session_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle session.get method."""
        session_id = params.get("session_id")
        if session_id not in self._sessions:
            raise Exception(f"Session not found: {session_id}")

        s = self._sessions[session_id]
        return {
            "session_id": s.session_id,
            "imsi": s.imsi,
            "apn": s.apn,
            "ip_address": s.ip_address,
            "qci": s.qci,
        }

    async def _handle_session_release(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle session.release method."""
        session_id = params.get("session_id")
        if session_id in self._sessions:
            del self._sessions[session_id]
        return {"success": True, "session_id": session_id}

    async def _handle_sms_send(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle sms.send method."""
        imsi = params.get("imsi")
        pdu = params.get("pdu")

        if not imsi or not pdu:
            raise Exception("Missing imsi or pdu")

        message_id = f"sms_{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "message_id": message_id,
            "imsi": imsi,
        }

    async def _handle_cell_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle enb.get_status method."""
        return {
            "cell_id": self._cell.cell_id,
            "status": self._cell.status,
            "plmn": self._cell.plmn,
            "frequency": self._cell.frequency,
            "bandwidth": self._cell.bandwidth,
            "tx_power": self._cell.tx_power,
        }

    async def _handle_cell_start(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle enb.start method."""
        self._cell.status = "active"
        return {"success": True, "status": "active"}

    async def _handle_cell_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle enb.stop method."""
        self._cell.status = "inactive"
        return {"success": True, "status": "inactive"}

    async def _handle_cell_configure(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle enb.configure method."""
        if "plmn" in params:
            self._cell.plmn = params["plmn"]
        if "frequency" in params:
            self._cell.frequency = params["frequency"]
        if "bandwidth" in params:
            self._cell.bandwidth = params["bandwidth"]
        if "tx_power" in params:
            self._cell.tx_power = params["tx_power"]

        return {"success": True}

    async def _handle_config_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle config.get method."""
        return self._config

    async def _handle_config_set(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle config.set method."""
        for key, value in params.items():
            if key in self._config:
                if isinstance(self._config[key], dict) and isinstance(value, dict):
                    self._config[key].update(value)
                else:
                    self._config[key] = value
        return {"success": True}

    async def _handle_event_subscribe(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle event.subscribe method."""
        return {"success": True, "subscribed": True}

    async def _handle_trigger(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle trigger method."""
        event_type = params.get("event_type")
        return {"success": True, "event_type": event_type}

    # =========================================================================
    # Test Helpers
    # =========================================================================

    def add_ue(
        self,
        imsi: str,
        status: str = "registered",
        cell_id: int = 1,
        ip_address: str = "10.0.0.100",
    ) -> MockUE:
        """Add a mock UE.

        Args:
            imsi: IMSI of the UE.
            status: UE status.
            cell_id: Cell ID.
            ip_address: IP address.

        Returns:
            The created MockUE.
        """
        ue = MockUE(
            imsi=imsi,
            status=status,
            cell_id=cell_id,
            ip_address=ip_address,
        )
        self._ues[imsi] = ue
        return ue

    def add_session(
        self,
        imsi: str,
        apn: str = "internet",
        ip_address: str = "10.0.0.100",
    ) -> MockSession:
        """Add a mock session.

        Args:
            imsi: IMSI of the UE.
            apn: Access Point Name.
            ip_address: IP address.

        Returns:
            The created MockSession.
        """
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        session = MockSession(
            session_id=session_id,
            imsi=imsi,
            apn=apn,
            ip_address=ip_address,
        )
        self._sessions[session_id] = session
        return session

    def set_api_key(self, api_key: str) -> None:
        """Set required API key.

        Args:
            api_key: API key to require.
        """
        self._api_key = api_key

    def clear_state(self) -> None:
        """Clear all mock state."""
        self._ues.clear()
        self._sessions.clear()
        self._authenticated = False
        self._cell = MockCell()

    async def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event to all connected clients.

        Args:
            event_type: Event type.
            data: Event data.
        """
        event = {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        for client in self._clients:
            try:
                await client.send(json.dumps(event))
            except Exception as e:
                log.error(f"Failed to emit event: {e}")


# Convenience fixture for pytest
async def create_mock_server(
    host: str = "localhost",
    port: int = 9001,
) -> MockAmarisoftServer:
    """Create and start a mock server.

    Args:
        host: Host to bind to.
        port: Port to listen on.

    Returns:
        Running MockAmarisoftServer instance.
    """
    server = MockAmarisoftServer()
    await server.start(host, port)
    return server
