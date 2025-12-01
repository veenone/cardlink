"""Generic simulator adapter for network simulator integration.

This module provides a generic adapter implementation that can serve as a
base for integrating non-Amarisoft simulators (e.g., srsRAN, OpenAirInterface).

Classes:
    GenericAdapter: Generic REST-like adapter with stub implementations
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from cardlink.netsim.connection import BaseConnection
from cardlink.netsim.exceptions import CommandError
from cardlink.netsim.interface import EventCallback, SimulatorInterface
from cardlink.netsim.types import (
    CellInfo,
    CellStatus,
    DataSession,
    NetworkEvent,
    NetworkEventType,
    SMSDirection,
    SMSMessage,
    SMSStatus,
    UEInfo,
)

log = logging.getLogger(__name__)


class GenericAdapter(SimulatorInterface):
    """Generic simulator adapter with REST-like API.

    This adapter provides a foundation for integrating non-Amarisoft
    simulators. It implements the full SimulatorInterface with stub
    implementations that can be extended for specific vendors.

    Extension Points:
        - Override _send_request() for vendor-specific protocol
        - Override parsing methods (_parse_*) for vendor response formats
        - Add vendor-specific methods as needed

    Note:
        This is a placeholder implementation. Actual functionality
        requires vendor-specific implementation.

    Example:
        >>> class SrsRANAdapter(GenericAdapter):
        ...     async def _send_request(self, method, params):
        ...         # srsRAN-specific implementation
        ...         pass
    """

    def __init__(self, connection: BaseConnection) -> None:
        """Initialize generic adapter.

        Args:
            connection: The connection to use for communication.
        """
        self._connection = connection
        self._authenticated = False
        self._event_callbacks: list[EventCallback] = []

    @property
    def connection(self) -> BaseConnection:
        """Get the underlying connection."""
        return self._connection

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with simulator."""
        return self._authenticated

    # =========================================================================
    # Protocol Abstraction - Override in subclasses
    # =========================================================================

    async def _send_request(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Any:
        """Send a request to the simulator.

        Override this method in subclasses to implement vendor-specific
        request/response protocol.

        Args:
            method: The method/endpoint name.
            params: Optional parameters.
            timeout: Response timeout.

        Returns:
            Response data.

        Raises:
            CommandError: If request fails.
            NotImplementedError: In base implementation.
        """
        # TODO: Implement vendor-specific request handling
        # This is a stub that should be overridden
        raise NotImplementedError(
            f"GenericAdapter._send_request not implemented. "
            f"Override in subclass for vendor-specific protocol."
        )

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, api_key: str) -> bool:
        """Authenticate with the simulator.

        Override for vendor-specific authentication.

        Args:
            api_key: API key or credentials.

        Returns:
            True if authentication successful.
        """
        # TODO: Implement vendor-specific authentication
        log.warning("GenericAdapter.authenticate: Using stub implementation")
        self._authenticated = True
        return True

    # =========================================================================
    # Cell Operations
    # =========================================================================

    async def get_cell_status(self) -> CellInfo:
        """Get cell status.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific cell status query
        log.warning("GenericAdapter.get_cell_status: Using stub implementation")
        return CellInfo(
            cell_id=1,
            status=CellStatus.INACTIVE,
            rat_type="LTE",
        )

    async def start_cell(self) -> bool:
        """Start the cell.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific cell start
        log.warning("GenericAdapter.start_cell: Using stub implementation")
        return False

    async def stop_cell(self) -> bool:
        """Stop the cell.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific cell stop
        log.warning("GenericAdapter.stop_cell: Using stub implementation")
        return False

    async def configure_cell(self, params: dict[str, Any]) -> bool:
        """Configure cell parameters.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific cell configuration
        log.warning("GenericAdapter.configure_cell: Using stub implementation")
        return False

    # =========================================================================
    # UE Operations
    # =========================================================================

    async def list_ues(self) -> list[UEInfo]:
        """List connected UEs.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific UE listing
        log.warning("GenericAdapter.list_ues: Using stub implementation")
        return []

    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get specific UE information.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific UE query
        log.warning("GenericAdapter.get_ue: Using stub implementation")
        return None

    async def detach_ue(self, imsi: str) -> bool:
        """Force detach a UE.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific UE detach
        log.warning("GenericAdapter.detach_ue: Using stub implementation")
        return False

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def list_sessions(self) -> list[DataSession]:
        """List active data sessions.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific session listing
        log.warning("GenericAdapter.list_sessions: Using stub implementation")
        return []

    async def release_session(self, session_id: str) -> bool:
        """Release a data session.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific session release
        log.warning("GenericAdapter.release_session: Using stub implementation")
        return False

    # =========================================================================
    # SMS Operations
    # =========================================================================

    async def send_sms(self, imsi: str, pdu: bytes) -> SMSMessage:
        """Send MT-SMS to a UE.

        Override for vendor-specific implementation.

        Args:
            imsi: Target UE IMSI.
            pdu: Raw SMS PDU bytes.

        Returns:
            SMSMessage with message ID and status.
        """
        # TODO: Implement vendor-specific SMS sending
        log.warning("GenericAdapter.send_sms: Using stub implementation")

        return SMSMessage(
            message_id=str(uuid.uuid4()),
            imsi=imsi,
            direction=SMSDirection.MT,
            pdu=pdu,
            status=SMSStatus.FAILED,
            timestamp=datetime.utcnow(),
            error_cause="Not implemented",
        )

    # =========================================================================
    # Event Operations
    # =========================================================================

    async def trigger_event(
        self, event_type: str, params: Optional[dict[str, Any]] = None
    ) -> bool:
        """Trigger a network event.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific event triggering
        log.warning("GenericAdapter.trigger_event: Using stub implementation")
        return False

    async def get_config(self) -> dict[str, Any]:
        """Get simulator configuration.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific config query
        log.warning("GenericAdapter.get_config: Using stub implementation")
        return {}

    async def set_config(self, config: dict[str, Any]) -> bool:
        """Set simulator configuration.

        Override for vendor-specific implementation.
        """
        # TODO: Implement vendor-specific config update
        log.warning("GenericAdapter.set_config: Using stub implementation")
        return False

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
    # Helper Methods for Subclasses
    # =========================================================================

    async def _emit_event(self, event: NetworkEvent) -> None:
        """Emit an event to all registered callbacks.

        Helper method for subclasses to emit events.

        Args:
            event: The event to emit.
        """
        for callback in self._event_callbacks:
            try:
                await callback(event)
            except Exception as e:
                log.error(f"Error in event callback: {e}")

    def _create_event(
        self,
        event_type: NetworkEventType,
        data: Optional[dict[str, Any]] = None,
        imsi: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> NetworkEvent:
        """Create a NetworkEvent instance.

        Helper method for subclasses to create events.

        Args:
            event_type: Type of event.
            data: Event data.
            imsi: Associated IMSI.
            session_id: Associated session ID.

        Returns:
            New NetworkEvent instance.
        """
        return NetworkEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source="generic",
            data=data or {},
            imsi=imsi,
            session_id=session_id,
        )
