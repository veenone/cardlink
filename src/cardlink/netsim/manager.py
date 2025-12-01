"""Main SimulatorManager for network simulator integration.

This module provides the primary entry point for all network simulator
operations, coordinating connections, adapters, and sub-managers.

Classes:
    SimulatorManager: Main manager coordinating all simulator operations
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional
from urllib.parse import urlparse

from cardlink.netsim.adapters import AmarisoftAdapter, GenericAdapter
from cardlink.netsim.connection import (
    BaseConnection,
    ReconnectManager,
    WSConnection,
    TCPConnection,
    create_connection,
)
from cardlink.netsim.constants import (
    EVENT_SIMULATOR_CONNECTED,
    EVENT_SIMULATOR_DISCONNECTED,
    EVENT_SIMULATOR_ERROR,
    EVENT_SIMULATOR_RECONNECTING,
)
from cardlink.netsim.exceptions import (
    ConfigurationError,
    ConnectionError,
    NotConnectedError,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.managers import (
    CellManager,
    SessionManager,
    SMSManager,
    UEManager,
)
from cardlink.netsim.types import (
    CellInfo,
    SimulatorConfig,
    SimulatorStatus,
    SimulatorType,
)

log = logging.getLogger(__name__)

# Type for event listeners
EventListener = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventEmitter:
    """Simple async event emitter for simulator events."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventListener]] = {}

    def on(self, event: str, callback: EventListener) -> None:
        """Register a callback for an event.

        Args:
            event: Event name.
            callback: Async callback function.
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def off(self, event: str, callback: EventListener) -> None:
        """Remove a callback for an event.

        Args:
            event: Event name.
            callback: Callback to remove.
        """
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    async def emit(self, event: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit an event to all listeners.

        Args:
            event: Event name.
            data: Event data.
        """
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    await callback(event, data or {})
                except Exception as e:
                    log.error(f"Error in event listener for '{event}': {e}")


class SimulatorManager:
    """Main manager for network simulator operations.

    This class provides a unified entry point for all network simulator
    functionality, coordinating connections, adapters, and sub-managers.

    Features:
        - Automatic connection and reconnection handling
        - Protocol detection (WebSocket/TCP)
        - Adapter selection based on simulator type
        - Status aggregation from sub-managers
        - Event emission for monitoring

    Attributes:
        config: The simulator configuration.
        events: Event emitter for simulator events.

    Example:
        >>> config = SimulatorConfig(
        ...     url="wss://callbox.local:9001",
        ...     simulator_type=SimulatorType.AMARISOFT,
        ...     api_key="secret"
        ... )
        >>> manager = SimulatorManager(config)
        >>> await manager.connect()
        >>> status = await manager.get_status()
        >>> print(f"Connected UEs: {status.ue_count}")
        >>> await manager.disconnect()
    """

    def __init__(
        self,
        config: SimulatorConfig,
        event_emitter: Optional[EventEmitter] = None,
    ) -> None:
        """Initialize SimulatorManager.

        Args:
            config: Simulator configuration.
            event_emitter: Optional event emitter (creates one if not provided).
        """
        self._config = config
        self._events = event_emitter or EventEmitter()

        # Connection components
        self._connection: Optional[BaseConnection] = None
        self._reconnect_manager: Optional[ReconnectManager] = None
        self._adapter: Optional[SimulatorInterface] = None

        # Sub-managers (initialized on connect)
        self._ue_manager: Optional[UEManager] = None
        self._session_manager: Optional[SessionManager] = None
        self._sms_manager: Optional[SMSManager] = None
        self._cell_manager: Optional[CellManager] = None

        # State
        self._connected = False

    @property
    def config(self) -> SimulatorConfig:
        """Get the simulator configuration."""
        return self._config

    @property
    def events(self) -> EventEmitter:
        """Get the event emitter."""
        return self._events

    @property
    def is_connected(self) -> bool:
        """Check if connected to simulator."""
        return self._connected and self._connection is not None and self._connection.is_connected

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        """Connect to the network simulator.

        This method:
        1. Validates configuration
        2. Creates appropriate connection (WebSocket/TCP)
        3. Sets up reconnection manager if auto_reconnect is enabled
        4. Creates appropriate adapter (Amarisoft/Generic)
        5. Authenticates if API key provided
        6. Initializes sub-managers
        7. Emits 'simulator_connected' event

        Raises:
            ConnectionError: If connection fails.
            ConfigurationError: If configuration is invalid.
            AuthenticationError: If authentication fails.
        """
        # Validate config
        self._config.validate()

        log.info(f"Connecting to {self._config.url}")

        try:
            # Create connection based on protocol
            self._connection = create_connection(
                self._config.url,
                self._config.tls_config,
                connect_timeout=self._config.connect_timeout,
            )

            # Setup reconnection if enabled
            if self._config.auto_reconnect:
                self._reconnect_manager = ReconnectManager(
                    initial_delay=self._config.reconnect_delay,
                    max_attempts=self._config.max_reconnect_attempts,
                )
                self._reconnect_manager.on_reconnect_start(self._on_reconnect_start)
                self._reconnect_manager.on_reconnect_success(self._on_reconnect_success)
                self._reconnect_manager.on_reconnect_failure(self._on_reconnect_failure)

            # Connect
            await self._connection.connect()

            # Create adapter based on simulator type
            self._adapter = self._create_adapter()

            # Authenticate if API key provided
            if self._config.api_key:
                await self._adapter.authenticate(self._config.api_key)

            # Initialize sub-managers
            await self._init_managers()

            self._connected = True

            # Emit connected event
            await self._events.emit(EVENT_SIMULATOR_CONNECTED, {
                "url": self._config.url,
                "simulator_type": self._config.simulator_type.value,
            })

            log.info(f"Connected to {self._config.simulator_type.value} simulator")

        except Exception as e:
            # Clean up on failure
            await self._cleanup()
            raise

    async def disconnect(self) -> None:
        """Disconnect from the network simulator.

        This method gracefully shuts down:
        1. Sub-managers
        2. Adapter
        3. Connection
        4. Reconnection manager

        Emits 'simulator_disconnected' event.

        This method is safe to call multiple times.
        """
        log.info("Disconnecting from simulator")

        self._connected = False

        # Cleanup
        await self._cleanup()

        # Emit disconnected event
        await self._events.emit(EVENT_SIMULATOR_DISCONNECTED, {})

        log.info("Disconnected from simulator")

    async def _cleanup(self) -> None:
        """Clean up all resources."""
        # Clear sub-managers
        self._ue_manager = None
        self._session_manager = None
        self._sms_manager = None
        self._cell_manager = None

        # Clear adapter
        if self._adapter and hasattr(self._adapter, 'cancel_pending_requests'):
            self._adapter.cancel_pending_requests()
        if self._adapter and hasattr(self._adapter, 'clear_auth_state'):
            self._adapter.clear_auth_state()
        self._adapter = None

        # Disconnect connection
        if self._connection:
            try:
                await self._connection.disconnect()
            except Exception as e:
                log.debug(f"Error during connection disconnect: {e}")
            self._connection = None

    def _create_adapter(self) -> SimulatorInterface:
        """Create appropriate adapter based on simulator type.

        Returns:
            Configured adapter instance.
        """
        if self._config.simulator_type == SimulatorType.AMARISOFT:
            return AmarisoftAdapter(self._connection)
        else:
            return GenericAdapter(self._connection)

    async def _init_managers(self) -> None:
        """Initialize sub-managers."""
        self._ue_manager = UEManager(self._adapter, self._events)
        self._session_manager = SessionManager(self._adapter, self._events)
        self._sms_manager = SMSManager(self._adapter, self._events)
        self._cell_manager = CellManager(self._adapter, self._events)

    # =========================================================================
    # Reconnection Callbacks
    # =========================================================================

    async def _on_reconnect_start(self) -> None:
        """Handle reconnection start."""
        await self._events.emit(EVENT_SIMULATOR_RECONNECTING, {})

    async def _on_reconnect_success(self) -> None:
        """Handle successful reconnection."""
        # Re-authenticate if needed
        if self._adapter and self._config.api_key:
            try:
                await self._adapter.authenticate(self._config.api_key)
            except Exception as e:
                log.error(f"Re-authentication failed: {e}")

        await self._events.emit(EVENT_SIMULATOR_CONNECTED, {
            "url": self._config.url,
            "reconnected": True,
        })

    async def _on_reconnect_failure(self, error: Exception) -> None:
        """Handle reconnection failure."""
        await self._events.emit(EVENT_SIMULATOR_ERROR, {
            "error": str(error),
            "type": "reconnection_failed",
        })

    # =========================================================================
    # Status and Information
    # =========================================================================

    async def get_status(self) -> SimulatorStatus:
        """Get aggregated simulator status.

        Queries status from adapter and sub-managers, combining them
        into a single status object.

        Returns:
            SimulatorStatus with current state information.

        Raises:
            NotConnectedError: If not connected to simulator.
        """
        if not self.is_connected or not self._adapter:
            raise NotConnectedError()

        try:
            # Query status in parallel where possible
            cell_info: Optional[CellInfo] = None
            ue_count = 0
            session_count = 0
            error: Optional[str] = None

            try:
                # Get cell status
                cell_info = await self._adapter.get_cell_status()
            except Exception as e:
                log.warning(f"Failed to get cell status: {e}")
                error = str(e)

            try:
                # Get UE count
                ues = await self._adapter.list_ues()
                ue_count = len(ues)
            except Exception as e:
                log.warning(f"Failed to list UEs: {e}")

            try:
                # Get session count
                sessions = await self._adapter.list_sessions()
                session_count = len(sessions)
            except Exception as e:
                log.warning(f"Failed to list sessions: {e}")

            return SimulatorStatus(
                connected=self.is_connected,
                authenticated=self._adapter.is_authenticated if self._adapter else False,
                cell=cell_info,
                ue_count=ue_count,
                session_count=session_count,
                error=error,
            )

        except Exception as e:
            return SimulatorStatus(
                connected=False,
                authenticated=False,
                error=str(e),
            )

    # =========================================================================
    # Sub-Manager Access
    # =========================================================================

    @property
    def ue(self) -> UEManager:
        """Access UE manager.

        Returns:
            UEManager for UE operations.

        Raises:
            NotConnectedError: If not connected.
        """
        if not self.is_connected or self._ue_manager is None:
            raise NotConnectedError("Not connected - call connect() first")
        return self._ue_manager

    @property
    def sessions(self) -> SessionManager:
        """Access session manager.

        Returns:
            SessionManager for session operations.

        Raises:
            NotConnectedError: If not connected.
        """
        if not self.is_connected or self._session_manager is None:
            raise NotConnectedError("Not connected - call connect() first")
        return self._session_manager

    @property
    def sms(self) -> SMSManager:
        """Access SMS manager.

        Returns:
            SMSManager for SMS operations.

        Raises:
            NotConnectedError: If not connected.
        """
        if not self.is_connected or self._sms_manager is None:
            raise NotConnectedError("Not connected - call connect() first")
        return self._sms_manager

    @property
    def cell(self) -> CellManager:
        """Access cell manager.

        Returns:
            CellManager for cell operations.

        Raises:
            NotConnectedError: If not connected.
        """
        if not self.is_connected or self._cell_manager is None:
            raise NotConnectedError("Not connected - call connect() first")
        return self._cell_manager

    @property
    def adapter(self) -> SimulatorInterface:
        """Access the underlying adapter directly.

        Returns:
            The simulator adapter.

        Raises:
            NotConnectedError: If not connected.
        """
        if not self.is_connected or self._adapter is None:
            raise NotConnectedError("Not connected - call connect() first")
        return self._adapter

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    async def __aenter__(self) -> "SimulatorManager":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
