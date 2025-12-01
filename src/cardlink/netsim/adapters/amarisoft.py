"""Amarisoft Callbox adapter for network simulator integration.

This module provides the adapter implementation for communicating with
Amarisoft Callbox simulators using their Remote API (JSON-RPC 2.0).

Classes:
    AmarisoftAdapter: Full adapter implementation for Amarisoft simulators
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

from cardlink.netsim.connection import BaseConnection
from cardlink.netsim.constants import (
    DEFAULT_COMMAND_TIMEOUT,
    ERROR_NOT_AUTHENTICATED,
    ERROR_RATE_LIMITED,
    ERROR_RESOURCE_NOT_FOUND,
    JSONRPC_VERSION,
    METHOD_AUTHENTICATE,
    METHOD_CONFIG_GET,
    METHOD_CONFIG_SET,
    METHOD_ENB_CONFIGURE,
    METHOD_ENB_GET_STATUS,
    METHOD_ENB_START,
    METHOD_ENB_STOP,
    METHOD_SESSION_LIST,
    METHOD_SESSION_RELEASE,
    METHOD_SMS_SEND,
    METHOD_UE_DETACH,
    METHOD_UE_GET,
    METHOD_UE_LIST,
)
from cardlink.netsim.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    NotConnectedError,
    RateLimitError,
    ResourceNotFoundError,
    TimeoutError,
)
from cardlink.netsim.interface import EventCallback, SimulatorInterface
from cardlink.netsim.types import (
    CellInfo,
    CellStatus,
    DataSession,
    NetworkEvent,
    NetworkEventType,
    QoSParameters,
    SMSDirection,
    SMSMessage,
    SMSStatus,
    UEInfo,
    UEStatus,
)

log = logging.getLogger(__name__)


class AmarisoftAdapter(SimulatorInterface):
    """Amarisoft Callbox adapter implementing JSON-RPC 2.0 protocol.

    This adapter provides full integration with Amarisoft Callbox simulators
    (LTE eNodeB and 5G gNodeB) through their Remote API.

    Features:
        - JSON-RPC 2.0 request/response handling
        - Request ID tracking with Future-based response matching
        - Event notification routing
        - Cell (eNB/gNB) control
        - UE monitoring and control
        - Data session management
        - SMS injection

    Attributes:
        connection: The underlying connection (WebSocket or TCP).

    Example:
        >>> adapter = AmarisoftAdapter(connection)
        >>> await adapter.authenticate("my-api-key")
        >>> status = await adapter.get_cell_status()
        >>> print(f"Cell status: {status.status}")
    """

    def __init__(self, connection: BaseConnection) -> None:
        """Initialize Amarisoft adapter.

        Args:
            connection: The connection to use for communication.
        """
        self._connection = connection
        self._authenticated = False
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._event_callbacks: list[EventCallback] = []

        # Register message handler
        self._connection.on_message(self._handle_message)

    @property
    def connection(self) -> BaseConnection:
        """Get the underlying connection."""
        return self._connection

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with simulator."""
        return self._authenticated

    # =========================================================================
    # JSON-RPC 2.0 Protocol
    # =========================================================================

    async def _send_request(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        timeout: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> Any:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: The RPC method name.
            params: Optional method parameters.
            timeout: Response timeout in seconds.

        Returns:
            The result from the JSON-RPC response.

        Raises:
            CommandError: If the request fails or returns an error.
            TimeoutError: If no response within timeout.
            NotConnectedError: If not connected to simulator.
        """
        if not self._connection.is_connected:
            raise NotConnectedError("Not connected to simulator")

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Build JSON-RPC request
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "method": method,
            "id": request_id,
        }
        if params:
            request["params"] = params

        # Create Future for response
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            await self._connection.send(request)
            log.debug(f"Sent request: {method} (id={request_id[:8]}...)")

            # Wait for response
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Request timed out: {method}",
                    operation=method,
                    timeout=timeout,
                )

        finally:
            # Clean up pending request
            self._pending_requests.pop(request_id, None)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle incoming JSON-RPC message.

        Routes responses to pending request Futures and events to callbacks.

        Args:
            message: The received JSON-RPC message.
        """
        # Check if this is a response (has id) or notification (no id)
        message_id = message.get("id")

        if message_id is not None:
            # This is a response to a request
            await self._handle_response(message)
        else:
            # This is a notification/event
            await self._handle_event(message)

    async def _handle_response(self, message: dict[str, Any]) -> None:
        """Handle JSON-RPC response message.

        Args:
            message: The response message.
        """
        message_id = message.get("id")

        if message_id not in self._pending_requests:
            log.warning(f"Received response for unknown request: {message_id}")
            return

        future = self._pending_requests[message_id]

        if "error" in message:
            # Error response
            error = message["error"]
            error_code = error.get("code", -1)
            error_message = error.get("message", "Unknown error")
            error_data = error.get("data", {})

            log.debug(f"Request error: {error_message} (code={error_code})")

            if not future.done():
                # Map error code to specific exception type
                exception = self._create_exception(
                    error_code, error_message, error_data
                )
                future.set_exception(exception)
        else:
            # Success response
            result = message.get("result")
            log.debug(f"Request success (id={str(message_id)[:8]}...)")

            if not future.done():
                future.set_result(result)

    def _create_exception(
        self,
        error_code: int,
        error_message: str,
        error_data: Optional[dict[str, Any]] = None,
    ) -> Exception:
        """Create appropriate exception based on error code.

        Args:
            error_code: JSON-RPC error code.
            error_message: Error message.
            error_data: Additional error data.

        Returns:
            Appropriate exception instance.
        """
        error_data = error_data or {}

        # Rate limit error
        if error_code == ERROR_RATE_LIMITED or error_code == -32429:
            retry_after = error_data.get("retry_after")
            return RateLimitError(
                error_message,
                retry_after=retry_after,
                method=error_data.get("method"),
            )

        # Authentication error
        if error_code == ERROR_NOT_AUTHENTICATED:
            return AuthenticationError(
                error_message,
                details=error_data,
            )

        # Resource not found
        if error_code == ERROR_RESOURCE_NOT_FOUND:
            return ResourceNotFoundError(
                error_message,
                resource_type=error_data.get("resource_type"),
                resource_id=error_data.get("resource_id"),
                method=error_data.get("method"),
            )

        # Generic command error
        return CommandError(
            error_message,
            error_code=error_code,
            details=error_data,
        )

    async def _handle_event(self, message: dict[str, Any]) -> None:
        """Handle JSON-RPC notification (event).

        Args:
            message: The notification message.
        """
        method = message.get("method", "")
        params = message.get("params", {})

        log.debug(f"Received event: {method}")

        # Convert to NetworkEvent
        event = self._parse_event(method, params)
        if event:
            # Invoke all callbacks
            for callback in self._event_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    log.error(f"Error in event callback: {e}")

    def _parse_event(
        self, method: str, params: dict[str, Any]
    ) -> Optional[NetworkEvent]:
        """Parse Amarisoft event into NetworkEvent.

        Args:
            method: The event method name.
            params: The event parameters.

        Returns:
            NetworkEvent or None if event type is unknown.
        """
        event_mapping = {
            "ue_attached": NetworkEventType.UE_ATTACH,
            "ue_detached": NetworkEventType.UE_DETACH,
            "pdn_connected": NetworkEventType.PDN_CONNECT,
            "pdn_disconnected": NetworkEventType.PDN_DISCONNECT,
            "sms_received": NetworkEventType.SMS_RECEIVED,
            "sms_sent": NetworkEventType.SMS_SENT,
            "handover": NetworkEventType.HANDOVER,
            "paging": NetworkEventType.PAGING,
        }

        event_type = event_mapping.get(method)
        if not event_type:
            # Custom/unknown event
            event_type = NetworkEventType.CUSTOM

        return NetworkEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source="amarisoft",
            data=params,
            imsi=params.get("imsi"),
            session_id=params.get("session_id"),
        )

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, api_key: str) -> bool:
        """Authenticate with Amarisoft Remote API.

        Args:
            api_key: The API key for authentication.

        Returns:
            True if authentication was successful.

        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            result = await self._send_request(
                METHOD_AUTHENTICATE,
                {"api_key": api_key},
            )

            # Check result
            if result is True or (isinstance(result, dict) and result.get("success")):
                self._authenticated = True
                log.info("Authentication successful")
                return True
            else:
                raise AuthenticationError(
                    "Authentication failed: invalid credentials",
                    identity=api_key[:8] + "..." if api_key else None,
                )

        except CommandError as e:
            if e.error_code == ERROR_NOT_AUTHENTICATED:
                raise AuthenticationError(
                    "Authentication failed: invalid API key",
                    identity=api_key[:8] + "..." if api_key else None,
                )
            raise

    # =========================================================================
    # Cell Operations
    # =========================================================================

    async def get_cell_status(self) -> CellInfo:
        """Get current cell status."""
        result = await self._send_request(METHOD_ENB_GET_STATUS)
        return self._parse_cell_info(result)

    async def start_cell(self) -> bool:
        """Start the simulated cell."""
        result = await self._send_request(METHOD_ENB_START)
        return result is True or (isinstance(result, dict) and result.get("success"))

    async def stop_cell(self) -> bool:
        """Stop the simulated cell."""
        result = await self._send_request(METHOD_ENB_STOP)
        return result is True or (isinstance(result, dict) and result.get("success"))

    async def configure_cell(self, params: dict[str, Any]) -> bool:
        """Configure cell parameters."""
        result = await self._send_request(METHOD_ENB_CONFIGURE, params)
        return result is True or (isinstance(result, dict) and result.get("success"))

    def _parse_cell_info(self, data: dict[str, Any]) -> CellInfo:
        """Parse Amarisoft response into CellInfo.

        Args:
            data: Raw response data.

        Returns:
            Parsed CellInfo object.
        """
        # Map status string to enum
        status_mapping = {
            "inactive": CellStatus.INACTIVE,
            "starting": CellStatus.STARTING,
            "active": CellStatus.ACTIVE,
            "stopping": CellStatus.STOPPING,
            "error": CellStatus.ERROR,
        }

        status_str = data.get("status", "inactive").lower()
        status = status_mapping.get(status_str, CellStatus.INACTIVE)

        return CellInfo(
            cell_id=data.get("cell_id", 1),
            status=status,
            rat_type=data.get("rat_type", "LTE"),
            plmn=data.get("plmn"),
            frequency=data.get("frequency"),
            bandwidth=data.get("bandwidth"),
            tx_power=data.get("tx_power"),
            connected_ues=data.get("ue_count", 0),
            metadata=data.get("metadata", {}),
        )

    # =========================================================================
    # UE Operations
    # =========================================================================

    async def list_ues(self) -> list[UEInfo]:
        """List all connected UEs."""
        result = await self._send_request(METHOD_UE_LIST)

        ues = []
        ue_list = result if isinstance(result, list) else result.get("ues", [])

        for ue_data in ue_list:
            ues.append(self._parse_ue_info(ue_data))

        return ues

    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get specific UE information."""
        try:
            result = await self._send_request(METHOD_UE_GET, {"imsi": imsi})
            return self._parse_ue_info(result)
        except CommandError as e:
            if e.error_code == ERROR_RESOURCE_NOT_FOUND:
                return None
            raise

    async def detach_ue(self, imsi: str) -> bool:
        """Force detach a UE."""
        try:
            result = await self._send_request(METHOD_UE_DETACH, {"imsi": imsi})
            return result is True or (isinstance(result, dict) and result.get("success"))
        except CommandError as e:
            if e.error_code == ERROR_RESOURCE_NOT_FOUND:
                raise ResourceNotFoundError(
                    f"UE not found: {imsi}",
                    resource_type="UE",
                    resource_id=imsi,
                    method=METHOD_UE_DETACH,
                )
            raise

    def _parse_ue_info(self, data: dict[str, Any]) -> UEInfo:
        """Parse Amarisoft response into UEInfo.

        Args:
            data: Raw UE data.

        Returns:
            Parsed UEInfo object.
        """
        # Map status string to enum
        status_mapping = {
            "detached": UEStatus.DETACHED,
            "attaching": UEStatus.ATTACHING,
            "attached": UEStatus.ATTACHED,
            "registered": UEStatus.REGISTERED,
            "connected": UEStatus.CONNECTED,
            "idle": UEStatus.IDLE,
        }

        status_str = data.get("status", "detached").lower()
        status = status_mapping.get(status_str, UEStatus.DETACHED)

        # Parse attached_at timestamp if present
        attached_at = None
        if "attached_at" in data:
            try:
                attached_at = datetime.fromisoformat(data["attached_at"])
            except (ValueError, TypeError):
                pass

        return UEInfo(
            imsi=data.get("imsi", ""),
            imei=data.get("imei"),
            status=status,
            cell_id=data.get("cell_id"),
            ip_address=data.get("ip_address"),
            apn=data.get("apn"),
            rat_type=data.get("rat_type"),
            signal_strength=data.get("rsrp"),
            attached_at=attached_at,
            metadata=data.get("metadata", {}),
        )

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def list_sessions(self) -> list[DataSession]:
        """List all active data sessions."""
        result = await self._send_request(METHOD_SESSION_LIST)

        sessions = []
        session_list = result if isinstance(result, list) else result.get("sessions", [])

        for session_data in session_list:
            sessions.append(self._parse_session(session_data))

        return sessions

    async def release_session(self, session_id: str) -> bool:
        """Release a data session."""
        try:
            result = await self._send_request(
                METHOD_SESSION_RELEASE, {"session_id": session_id}
            )
            return result is True or (isinstance(result, dict) and result.get("success"))
        except CommandError as e:
            if e.error_code == ERROR_RESOURCE_NOT_FOUND:
                raise ResourceNotFoundError(
                    f"Session not found: {session_id}",
                    resource_type="Session",
                    resource_id=session_id,
                    method=METHOD_SESSION_RELEASE,
                )
            raise

    def _parse_session(self, data: dict[str, Any]) -> DataSession:
        """Parse Amarisoft response into DataSession.

        Args:
            data: Raw session data.

        Returns:
            Parsed DataSession object.
        """
        # Parse QoS parameters
        qos_data = data.get("qos", {})
        qos = QoSParameters(
            qci=qos_data.get("qci"),
            arp=qos_data.get("arp"),
            mbr_ul=qos_data.get("mbr_ul"),
            mbr_dl=qos_data.get("mbr_dl"),
            gbr_ul=qos_data.get("gbr_ul"),
            gbr_dl=qos_data.get("gbr_dl"),
        )

        # Parse created_at timestamp if present
        created_at = None
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass

        return DataSession(
            session_id=data.get("session_id", ""),
            imsi=data.get("imsi", ""),
            apn=data.get("apn", ""),
            ip_address=data.get("ip_address"),
            ipv6_address=data.get("ipv6_address"),
            qos=qos,
            pdn_type=data.get("pdn_type", "IPv4"),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )

    # =========================================================================
    # SMS Operations
    # =========================================================================

    async def send_sms(self, imsi: str, pdu: bytes) -> SMSMessage:
        """Send MT-SMS to a UE.

        Args:
            imsi: Target UE IMSI.
            pdu: Raw SMS PDU bytes.

        Returns:
            SMSMessage with message ID and status.
        """
        # Convert PDU to hex string
        pdu_hex = pdu.hex().upper()

        try:
            result = await self._send_request(
                METHOD_SMS_SEND,
                {"imsi": imsi, "pdu": pdu_hex},
            )

            # Parse response
            message_id = result.get("message_id", str(uuid.uuid4()))
            status_str = result.get("status", "pending").lower()

            status_mapping = {
                "pending": SMSStatus.PENDING,
                "sent": SMSStatus.SENT,
                "delivered": SMSStatus.DELIVERED,
                "failed": SMSStatus.FAILED,
            }
            status = status_mapping.get(status_str, SMSStatus.PENDING)

            return SMSMessage(
                message_id=message_id,
                imsi=imsi,
                direction=SMSDirection.MT,
                pdu=pdu,
                status=status,
                timestamp=datetime.utcnow(),
                error_cause=result.get("error_cause"),
            )

        except CommandError as e:
            if e.error_code == ERROR_RESOURCE_NOT_FOUND:
                raise ResourceNotFoundError(
                    f"Target UE not found: {imsi}",
                    resource_type="UE",
                    resource_id=imsi,
                    method=METHOD_SMS_SEND,
                )
            raise

    # =========================================================================
    # Event Operations
    # =========================================================================

    async def trigger_event(
        self, event_type: str, params: Optional[dict[str, Any]] = None
    ) -> bool:
        """Trigger a network event.

        Args:
            event_type: Event type to trigger.
            params: Event parameters.

        Returns:
            True if event was triggered.
        """
        # Map event types to Amarisoft methods
        event_methods = {
            "handover": "ue.handover",
            "tau": "ue.tau",
            "service_request": "ue.service_request",
            "rlf": "ue.rlf",
            "paging": "ue.paging",
        }

        method = event_methods.get(event_type.lower())
        if not method:
            # Try using event_type as method name directly
            method = event_type

        result = await self._send_request(method, params)
        return result is True or (isinstance(result, dict) and result.get("success"))

    async def get_config(self) -> dict[str, Any]:
        """Get simulator configuration."""
        result = await self._send_request(METHOD_CONFIG_GET)
        return result if isinstance(result, dict) else {}

    async def set_config(self, config: dict[str, Any]) -> bool:
        """Set simulator configuration."""
        result = await self._send_request(METHOD_CONFIG_SET, config)
        return result is True or (isinstance(result, dict) and result.get("success"))

    async def subscribe_events(self, callback: EventCallback) -> None:
        """Subscribe to network events.

        Args:
            callback: Async callback function for events.
        """
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
            log.debug("Added event callback")

    async def unsubscribe_events(self, callback: EventCallback) -> None:
        """Unsubscribe from network events.

        Args:
            callback: Callback to remove.
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            log.debug("Removed event callback")

    # =========================================================================
    # Cleanup
    # =========================================================================

    def clear_auth_state(self) -> None:
        """Clear authentication state.

        Should be called when connection is lost.
        """
        self._authenticated = False

    def cancel_pending_requests(self) -> None:
        """Cancel all pending requests.

        Should be called when connection is lost.
        """
        for request_id, future in list(self._pending_requests.items()):
            if not future.done():
                future.set_exception(
                    ConnectionError("Connection lost while waiting for response")
                )
        self._pending_requests.clear()
