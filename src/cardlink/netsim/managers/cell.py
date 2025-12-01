"""Cell Manager for network simulator integration.

This module provides centralized cell (eNB/gNB) management with
status tracking, control operations, and configuration.

Classes:
    CellManager: Manager for cell control and monitoring
"""

import asyncio
import logging
from typing import Any, Optional

from cardlink.netsim.constants import (
    EVENT_CELL_STARTED,
    EVENT_CELL_STARTING,
    EVENT_CELL_STOPPED,
    EVENT_CELL_STOPPING,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.types import CellInfo, CellStatus

log = logging.getLogger(__name__)


class CellManager:
    """Manager for cell (eNB/gNB) control and monitoring.

    Provides centralized cell management with:
    - Cell start/stop with status polling
    - Status caching
    - Configuration management
    - Event emission

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> cell_manager = CellManager(adapter, event_emitter)
        >>> # Start the cell
        >>> await cell_manager.start()
        >>> # Check status
        >>> if cell_manager.is_active:
        ...     print("Cell is active")
    """

    # Default polling interval for status checks
    DEFAULT_POLL_INTERVAL = 1.0

    # Default timeout for start/stop operations
    DEFAULT_OPERATION_TIMEOUT = 60.0

    def __init__(self, adapter: SimulatorInterface, event_emitter: Any) -> None:
        """Initialize Cell Manager.

        Args:
            adapter: The simulator adapter for cell operations.
            event_emitter: Event emitter for broadcasting cell events.
        """
        self._adapter = adapter
        self._events = event_emitter

        # Cached cell status
        self._cell_status: Optional[CellInfo] = None

    # =========================================================================
    # Status Operations
    # =========================================================================

    async def get_status(self) -> CellInfo:
        """Get current cell status.

        Queries the adapter and updates the local cache.

        Returns:
            CellInfo with current cell status.
        """
        self._cell_status = await self._adapter.get_cell_status()
        return self._cell_status

    @property
    def cached_status(self) -> Optional[CellInfo]:
        """Get cached cell status without querying adapter.

        Returns:
            Cached CellInfo or None if not available.
        """
        return self._cell_status

    @property
    def is_active(self) -> bool:
        """Check if cell is active.

        Returns:
            True if cell status is ACTIVE.
        """
        if self._cell_status is None:
            return False
        return self._cell_status.status == CellStatus.ACTIVE

    # =========================================================================
    # Control Operations
    # =========================================================================

    async def start(
        self,
        timeout: float = DEFAULT_OPERATION_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> bool:
        """Start the simulated cell.

        Starts the cell and waits until it reaches ACTIVE status
        or timeout is reached.

        Args:
            timeout: Maximum time to wait for cell to become active.
            poll_interval: Interval between status checks.

        Returns:
            True if cell started successfully.
        """
        log.info("Starting cell...")

        # Emit starting event
        await self._events.emit(EVENT_CELL_STARTING, {})

        try:
            # Send start command
            result = await self._adapter.start_cell()
            if not result:
                log.error("Cell start command failed")
                return False

            # Poll for active status
            elapsed = 0.0
            while elapsed < timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await self.get_status()
                log.debug(f"Cell status: {status.status.value}")

                if status.status == CellStatus.ACTIVE:
                    log.info("Cell started successfully")
                    await self._events.emit(EVENT_CELL_STARTED, {
                        "cell": status.to_dict(),
                    })
                    return True

                if status.status == CellStatus.ERROR:
                    log.error("Cell entered error state")
                    return False

            log.warning(f"Cell start timed out after {timeout}s")
            return False

        except Exception as e:
            log.error(f"Error starting cell: {e}")
            return False

    async def stop(
        self,
        timeout: float = DEFAULT_OPERATION_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> bool:
        """Stop the simulated cell.

        Stops the cell and waits until it reaches INACTIVE status
        or timeout is reached.

        Args:
            timeout: Maximum time to wait for cell to become inactive.
            poll_interval: Interval between status checks.

        Returns:
            True if cell stopped successfully.
        """
        log.info("Stopping cell...")

        # Emit stopping event
        await self._events.emit(EVENT_CELL_STOPPING, {})

        try:
            # Send stop command
            result = await self._adapter.stop_cell()
            if not result:
                log.error("Cell stop command failed")
                return False

            # Poll for inactive status
            elapsed = 0.0
            while elapsed < timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await self.get_status()
                log.debug(f"Cell status: {status.status.value}")

                if status.status == CellStatus.INACTIVE:
                    log.info("Cell stopped successfully")
                    await self._events.emit(EVENT_CELL_STOPPED, {})
                    return True

            log.warning(f"Cell stop timed out after {timeout}s")
            return False

        except Exception as e:
            log.error(f"Error stopping cell: {e}")
            return False

    async def restart(
        self,
        timeout: float = DEFAULT_OPERATION_TIMEOUT * 2,
    ) -> bool:
        """Restart the cell.

        Stops the cell (if running) and starts it again.

        Args:
            timeout: Total timeout for restart operation.

        Returns:
            True if cell restarted successfully.
        """
        log.info("Restarting cell...")

        half_timeout = timeout / 2

        # Stop if active
        status = await self.get_status()
        if status.status != CellStatus.INACTIVE:
            if not await self.stop(timeout=half_timeout):
                return False

        # Start cell
        return await self.start(timeout=half_timeout)

    # =========================================================================
    # Configuration Operations
    # =========================================================================

    async def configure(self, params: dict[str, Any]) -> bool:
        """Configure cell parameters.

        Args:
            params: Configuration parameters to set.

        Returns:
            True if configuration was applied.
        """
        log.info(f"Configuring cell: {params}")
        return await self._adapter.configure_cell(params)

    async def set_plmn(self, mcc: str, mnc: str) -> bool:
        """Set cell PLMN identity.

        Args:
            mcc: Mobile Country Code (3 digits).
            mnc: Mobile Network Code (2-3 digits).

        Returns:
            True if PLMN was set.
        """
        plmn = f"{mcc}-{mnc}"
        return await self.configure({"plmn": plmn})

    async def set_frequency(self, frequency_mhz: float) -> bool:
        """Set cell operating frequency.

        Args:
            frequency_mhz: Frequency in MHz.

        Returns:
            True if frequency was set.
        """
        return await self.configure({"frequency": frequency_mhz})

    async def set_bandwidth(self, bandwidth_mhz: float) -> bool:
        """Set cell bandwidth.

        Args:
            bandwidth_mhz: Bandwidth in MHz.

        Returns:
            True if bandwidth was set.
        """
        return await self.configure({"bandwidth": bandwidth_mhz})

    async def set_power(self, tx_power_dbm: float) -> bool:
        """Set cell transmit power.

        Args:
            tx_power_dbm: Transmit power in dBm.

        Returns:
            True if power was set.
        """
        return await self.configure({"tx_power": tx_power_dbm})
