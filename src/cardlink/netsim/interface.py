"""Abstract simulator interface for network simulator integration.

This module defines the abstract interface that all simulator adapters must
implement, providing a vendor-agnostic API for network simulator operations.

Classes:
    SimulatorInterface: Abstract base class for simulator adapters
"""

import abc
from typing import Any, Callable, Coroutine, Optional

from cardlink.netsim.types import (
    CellInfo,
    DataSession,
    NetworkEvent,
    SMSMessage,
    UEInfo,
)

# Type alias for event callbacks
EventCallback = Callable[[NetworkEvent], Coroutine[Any, Any, None]]


class SimulatorInterface(abc.ABC):
    """Abstract interface for network simulator operations.

    This class defines the contract that all simulator adapters must implement,
    enabling support for multiple simulator vendors (Amarisoft, srsRAN, etc.)
    through a unified API.

    All methods are asynchronous to support non-blocking network operations.

    Subclasses must implement all abstract methods with vendor-specific
    communication logic.

    Example:
        >>> class MySimulatorAdapter(SimulatorInterface):
        ...     async def authenticate(self, api_key: str) -> bool:
        ...         # Vendor-specific authentication
        ...         pass
    """

    # =========================================================================
    # Authentication
    # =========================================================================

    @abc.abstractmethod
    async def authenticate(self, api_key: str) -> bool:
        """Authenticate with the simulator using an API key.

        This method should establish authentication with the simulator and
        store any necessary session tokens or state.

        Args:
            api_key: The API key for authentication.

        Returns:
            True if authentication was successful, False otherwise.

        Raises:
            AuthenticationError: If authentication fails with an error.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # Cell Operations
    # =========================================================================

    @abc.abstractmethod
    async def get_cell_status(self) -> CellInfo:
        """Get the current status of the simulated cell (eNB/gNB).

        Returns information about the cell including its operational status,
        radio parameters, and connected UE count.

        Returns:
            CellInfo object with current cell status and parameters.

        Raises:
            CommandError: If the status query fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def start_cell(self) -> bool:
        """Start the simulated cell (eNB/gNB).

        Activates the cell so that UEs can attach. This may take several
        seconds to complete as the cell initializes.

        Returns:
            True if the cell was started successfully.

        Raises:
            CommandError: If the start operation fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def stop_cell(self) -> bool:
        """Stop the simulated cell (eNB/gNB).

        Deactivates the cell, causing all connected UEs to detach.
        This may take several seconds to complete.

        Returns:
            True if the cell was stopped successfully.

        Raises:
            CommandError: If the stop operation fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def configure_cell(self, params: dict[str, Any]) -> bool:
        """Configure cell parameters.

        Updates cell configuration such as PLMN, frequency, bandwidth,
        and transmit power. The cell may need to be restarted for some
        changes to take effect.

        Args:
            params: Dictionary of configuration parameters to set.
                   Valid keys depend on the simulator vendor.
                   Common keys include:
                   - plmn: PLMN identity (MCC-MNC)
                   - frequency: Operating frequency (MHz)
                   - bandwidth: Channel bandwidth (MHz)
                   - tx_power: Transmit power (dBm)

        Returns:
            True if configuration was applied successfully.

        Raises:
            CommandError: If configuration fails.
            ConfigurationError: If parameters are invalid.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # UE Operations
    # =========================================================================

    @abc.abstractmethod
    async def list_ues(self) -> list[UEInfo]:
        """List all UEs currently connected to the simulator.

        Returns information about all UEs that are attached or
        in the process of attaching to the network.

        Returns:
            List of UEInfo objects for all connected UEs.

        Raises:
            CommandError: If the query fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get detailed information about a specific UE.

        Args:
            imsi: The IMSI of the UE to query.

        Returns:
            UEInfo object if found, None if UE is not connected.

        Raises:
            CommandError: If the query fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def detach_ue(self, imsi: str) -> bool:
        """Force detach a UE from the network.

        Sends a detach request to the specified UE, causing it to
        disconnect from the network.

        Args:
            imsi: The IMSI of the UE to detach.

        Returns:
            True if detach was successful.

        Raises:
            CommandError: If detach fails.
            ResourceNotFoundError: If UE is not found.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # Session Operations
    # =========================================================================

    @abc.abstractmethod
    async def list_sessions(self) -> list[DataSession]:
        """List all active data sessions (PDN/PDU contexts).

        Returns information about all active data sessions including
        IP addresses, APNs, and QoS parameters.

        Returns:
            List of DataSession objects for all active sessions.

        Raises:
            CommandError: If the query fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def release_session(self, session_id: str) -> bool:
        """Release (terminate) a specific data session.

        Forcefully terminates the specified PDN/PDU context.

        Args:
            session_id: The unique identifier of the session to release.

        Returns:
            True if session was released successfully.

        Raises:
            CommandError: If release fails.
            ResourceNotFoundError: If session is not found.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # SMS Operations
    # =========================================================================

    @abc.abstractmethod
    async def send_sms(self, imsi: str, pdu: bytes) -> SMSMessage:
        """Send an MT-SMS to a specific UE.

        Injects a Mobile Terminated SMS message to be delivered to the
        specified UE. The PDU should be properly formatted according to
        3GPP specifications.

        Args:
            imsi: The IMSI of the target UE.
            pdu: The raw SMS PDU bytes.

        Returns:
            SMSMessage object with message ID and initial status.

        Raises:
            CommandError: If SMS send fails.
            ResourceNotFoundError: If target UE is not found.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # Event Operations
    # =========================================================================

    @abc.abstractmethod
    async def trigger_event(
        self, event_type: str, params: Optional[dict[str, Any]] = None
    ) -> bool:
        """Trigger a network event in the simulator.

        Causes the simulator to generate a specific network event such as
        a handover, tracking area update, or service request.

        Args:
            event_type: The type of event to trigger. Valid types depend
                       on the simulator vendor but common types include:
                       - "handover": Trigger handover to another cell
                       - "tau": Trigger Tracking Area Update
                       - "service_request": Trigger Service Request
                       - "rlf": Trigger Radio Link Failure
            params: Optional parameters for the event. Content depends on
                   event_type.

        Returns:
            True if event was triggered successfully.

        Raises:
            CommandError: If event triggering fails.
            ConfigurationError: If event_type or params are invalid.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # Configuration Operations
    # =========================================================================

    @abc.abstractmethod
    async def get_config(self) -> dict[str, Any]:
        """Get the current simulator configuration.

        Returns the complete configuration of the simulator including
        cell parameters, network settings, and operational state.

        Returns:
            Dictionary containing all configuration values.

        Raises:
            CommandError: If config query fails.
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def set_config(self, config: dict[str, Any]) -> bool:
        """Update simulator configuration.

        Sets one or more configuration values. The simulator may need
        to be restarted for some changes to take effect.

        Args:
            config: Dictionary of configuration key-value pairs to set.

        Returns:
            True if configuration was applied successfully.

        Raises:
            CommandError: If config update fails.
            ConfigurationError: If configuration values are invalid.
            ConnectionError: If not connected to the simulator.
        """
        pass

    # =========================================================================
    # Event Subscription
    # =========================================================================

    @abc.abstractmethod
    async def subscribe_events(self, callback: EventCallback) -> None:
        """Subscribe to network events from the simulator.

        Registers a callback function that will be invoked asynchronously
        whenever the simulator reports a network event (UE attach/detach,
        session activation, SMS delivery, etc.).

        Multiple callbacks can be registered by calling this method
        multiple times.

        Args:
            callback: Async function to call with each event.
                     Signature: async def callback(event: NetworkEvent) -> None

        Raises:
            ConnectionError: If not connected to the simulator.
        """
        pass

    @abc.abstractmethod
    async def unsubscribe_events(self, callback: EventCallback) -> None:
        """Unsubscribe from network events.

        Removes a previously registered event callback.

        Args:
            callback: The callback to remove.
        """
        pass

    # =========================================================================
    # Connection State
    # =========================================================================

    @property
    @abc.abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with the simulator.

        Returns:
            True if authenticated, False otherwise.
        """
        pass
