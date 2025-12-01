"""UE Manager for network simulator integration.

This module provides centralized UE (User Equipment) management with
registration tracking, caching, and wait-for-registration capability.

Classes:
    UEManager: Manager for UE registration and monitoring
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from cardlink.netsim.constants import (
    EVENT_UE_ATTACHED,
    EVENT_UE_DETACHED,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.types import NetworkEvent, NetworkEventType, UEInfo

log = logging.getLogger(__name__)


class UEManager:
    """Manager for UE registration tracking and control.

    Provides centralized UE management with:
    - UE cache for efficient queries
    - Wait-for-registration with timeout
    - Event handling for attach/detach
    - Automatic cache synchronization

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> ue_manager = UEManager(adapter, event_emitter)
        >>> # Wait for specific UE to register
        >>> registered = await ue_manager.wait_for_registration(
        ...     "001010123456789", timeout=30
        ... )
        >>> if registered:
        ...     ue = await ue_manager.get_ue("001010123456789")
        ...     print(f"UE connected with IP: {ue.ip_address}")
    """

    def __init__(self, adapter: SimulatorInterface, event_emitter: Any) -> None:
        """Initialize UE Manager.

        Args:
            adapter: The simulator adapter for UE operations.
            event_emitter: Event emitter for broadcasting UE events.
        """
        self._adapter = adapter
        self._events = event_emitter

        # UE cache: IMSI -> UEInfo
        self._ue_cache: dict[str, UEInfo] = {}

        # Waiters: IMSI -> list of asyncio.Event
        self._waiters: dict[str, list[asyncio.Event]] = {}

        # Subscribe to adapter events
        asyncio.create_task(self._subscribe_events())

    async def _subscribe_events(self) -> None:
        """Subscribe to UE events from adapter."""
        try:
            await self._adapter.subscribe_events(self._handle_event)
        except Exception as e:
            log.error(f"Failed to subscribe to UE events: {e}")

    async def _handle_event(self, event: NetworkEvent) -> None:
        """Handle incoming UE events.

        Args:
            event: The network event.
        """
        if event.event_type == NetworkEventType.UE_ATTACH:
            await self._handle_attach(event)
        elif event.event_type == NetworkEventType.UE_DETACH:
            await self._handle_detach(event)

    async def _handle_attach(self, event: NetworkEvent) -> None:
        """Handle UE attach event.

        Args:
            event: The attach event.
        """
        imsi = event.imsi or event.data.get("imsi")
        if not imsi:
            log.warning("Received attach event without IMSI")
            return

        log.info(f"UE attached: {imsi}")

        # Create UEInfo from event data
        ue_info = UEInfo(
            imsi=imsi,
            imei=event.data.get("imei"),
            status=event.data.get("status", "attached"),
            cell_id=event.data.get("cell_id"),
            ip_address=event.data.get("ip_address"),
            apn=event.data.get("apn"),
            rat_type=event.data.get("rat_type"),
            attached_at=datetime.utcnow(),
            metadata=event.data,
        )

        # Update cache
        self._ue_cache[imsi] = ue_info

        # Notify waiters
        if imsi in self._waiters:
            for waiter in self._waiters[imsi]:
                waiter.set()
            # Clear waiters after notification
            self._waiters[imsi] = []

        # Emit event
        await self._events.emit(EVENT_UE_ATTACHED, {
            "imsi": imsi,
            "ue": ue_info.to_dict(),
        })

    async def _handle_detach(self, event: NetworkEvent) -> None:
        """Handle UE detach event.

        Args:
            event: The detach event.
        """
        imsi = event.imsi or event.data.get("imsi")
        if not imsi:
            log.warning("Received detach event without IMSI")
            return

        log.info(f"UE detached: {imsi}")

        # Remove from cache
        ue_info = self._ue_cache.pop(imsi, None)

        # Emit event
        await self._events.emit(EVENT_UE_DETACHED, {
            "imsi": imsi,
            "ue": ue_info.to_dict() if ue_info else None,
        })

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def list_ues(self) -> list[UEInfo]:
        """List all connected UEs.

        Queries the adapter and updates the local cache.

        Returns:
            List of UEInfo for all connected UEs.
        """
        ues = await self._adapter.list_ues()

        # Update cache
        self._ue_cache.clear()
        for ue in ues:
            self._ue_cache[ue.imsi] = ue

        return ues

    async def get_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get information about a specific UE.

        Checks cache first, then queries adapter if not found.

        Args:
            imsi: The IMSI of the UE.

        Returns:
            UEInfo if found, None otherwise.
        """
        # Check cache first
        if imsi in self._ue_cache:
            return self._ue_cache[imsi]

        # Query adapter
        ue = await self._adapter.get_ue(imsi)
        if ue:
            self._ue_cache[imsi] = ue
        return ue

    def get_cached_ues(self) -> list[UEInfo]:
        """Get all cached UE information.

        Returns cached UEs without querying the adapter.

        Returns:
            List of cached UEInfo objects.
        """
        return list(self._ue_cache.values())

    def get_cached_ue(self, imsi: str) -> Optional[UEInfo]:
        """Get cached UE information.

        Args:
            imsi: The IMSI of the UE.

        Returns:
            Cached UEInfo if available, None otherwise.
        """
        return self._ue_cache.get(imsi)

    # =========================================================================
    # Wait Operations
    # =========================================================================

    async def wait_for_registration(
        self, imsi: str, timeout: float = 30.0
    ) -> bool:
        """Wait for a specific UE to register.

        Blocks until the specified UE attaches to the network or
        timeout is reached.

        Args:
            imsi: The IMSI of the UE to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if UE registered within timeout, False otherwise.
        """
        # Check if already registered
        if imsi in self._ue_cache:
            log.debug(f"UE {imsi} already registered")
            return True

        # Also check via adapter
        try:
            ue = await self._adapter.get_ue(imsi)
            if ue:
                self._ue_cache[imsi] = ue
                return True
        except Exception:
            pass

        # Create waiter event
        event = asyncio.Event()

        # Add to waiters list
        if imsi not in self._waiters:
            self._waiters[imsi] = []
        self._waiters[imsi].append(event)

        try:
            log.debug(f"Waiting for UE {imsi} registration (timeout={timeout}s)")
            await asyncio.wait_for(event.wait(), timeout=timeout)
            log.info(f"UE {imsi} registered")
            return True
        except asyncio.TimeoutError:
            log.warning(f"Timeout waiting for UE {imsi} registration")
            return False
        finally:
            # Clean up waiter
            if imsi in self._waiters and event in self._waiters[imsi]:
                self._waiters[imsi].remove(event)
                if not self._waiters[imsi]:
                    del self._waiters[imsi]

    # =========================================================================
    # Control Operations
    # =========================================================================

    async def detach_ue(self, imsi: str) -> bool:
        """Force detach a UE from the network.

        Args:
            imsi: The IMSI of the UE to detach.

        Returns:
            True if detach was successful.
        """
        result = await self._adapter.detach_ue(imsi)

        if result:
            # Remove from cache
            self._ue_cache.pop(imsi, None)

            # Emit event
            await self._events.emit(EVENT_UE_DETACHED, {
                "imsi": imsi,
                "forced": True,
            })

        return result

    # =========================================================================
    # Cache Management
    # =========================================================================

    def clear_cache(self) -> None:
        """Clear the UE cache."""
        self._ue_cache.clear()
        log.debug("UE cache cleared")

    @property
    def cached_count(self) -> int:
        """Get number of cached UEs."""
        return len(self._ue_cache)
