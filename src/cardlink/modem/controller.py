"""Modem Controller Main Class.

This module provides the main ModemController class that orchestrates
all modem control operations.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from cardlink.modem.exceptions import ModemNotFoundError
from cardlink.modem.models import BIPEvent, FullModemProfile, ModemVendor
from cardlink.modem.modem_manager import ModemInfo, ModemManager
from cardlink.modem.vendors import VENDOR_MODEMS, Modem, QuectelModem

logger = logging.getLogger(__name__)


class ModemController:
    """Main modem controller for IoT cellular modem management.

    Coordinates modem discovery, access, and event handling.

    Example:
        >>> controller = ModemController()
        >>>
        >>> # Discover modems
        >>> modems = await controller.discover_modems()
        >>> for modem_info in modems:
        ...     print(f"{modem_info.port}: {modem_info.manufacturer}")
        >>>
        >>> # Get modem instance
        >>> modem = await controller.get_modem("/dev/ttyUSB2")
        >>>
        >>> # Use modem
        >>> profile = await modem.get_profile()
        >>> print(f"IMEI: {profile.modem.imei}")
        >>>
        >>> # Register for events
        >>> controller.on_modem_connected(lambda info: print(f"Connected: {info.port}"))
        >>> await controller.start_monitoring()
    """

    def __init__(self, poll_interval: float = 5.0):
        """Initialize modem controller.

        Args:
            poll_interval: Interval for modem monitoring in seconds.
        """
        self._manager = ModemManager(poll_interval=poll_interval)
        self._modems: Dict[str, Modem] = {}
        self._bip_callbacks: List[Callable[[BIPEvent], Any]] = []

    @property
    def connected_modems(self) -> List[ModemInfo]:
        """Get list of connected modem info."""
        return list(self._manager.modems.values())

    @property
    def connected_ports(self) -> List[str]:
        """Get list of connected modem ports."""
        return self._manager.connected_ports

    # =========================================================================
    # Discovery
    # =========================================================================

    async def discover_modems(self) -> List[ModemInfo]:
        """Scan for connected modems.

        Returns:
            List of ModemInfo for detected modems.
        """
        return await self._manager.scan_modems()

    async def refresh_modems(self) -> None:
        """Refresh modem list."""
        await self._manager.scan_modems()

    def is_modem_connected(self, port: str) -> bool:
        """Check if modem is connected on port.

        Args:
            port: Serial port path.

        Returns:
            True if modem detected on port.
        """
        return self._manager.is_modem_connected(port)

    # =========================================================================
    # Modem Access
    # =========================================================================

    async def get_modem(self, port: str) -> Modem:
        """Get modem instance by port.

        Creates and connects to modem if not already connected.

        Args:
            port: Serial port path.

        Returns:
            Connected Modem instance.

        Raises:
            ModemNotFoundError: If modem not found on port.
        """
        # Return cached modem if already connected
        if port in self._modems and self._modems[port].is_connected:
            return self._modems[port]

        # Check if modem is detected
        if not self._manager.is_modem_connected(port):
            # Try to scan first
            await self._manager.scan_modems()
            if not self._manager.is_modem_connected(port):
                raise ModemNotFoundError(port)

        # Get modem info
        modem_info = self._manager.get_modem(port)

        # Create appropriate modem instance based on vendor
        modem = self._create_modem_instance(port, modem_info.profile.vendor)

        # Connect
        await modem.connect()

        # Cache
        self._modems[port] = modem

        return modem

    def _create_modem_instance(self, port: str, vendor: ModemVendor) -> Modem:
        """Create modem instance based on vendor.

        Args:
            port: Serial port path.
            vendor: Modem vendor.

        Returns:
            Modem instance (not connected).
        """
        vendor_key = vendor.value.lower().replace(" ", "_")

        if vendor_key in VENDOR_MODEMS:
            modem_class = VENDOR_MODEMS[vendor_key]
            return modem_class(port=port)

        # Default to Quectel for unknown vendors (most common)
        logger.warning("Unknown vendor %s, using QuectelModem", vendor.value)
        return QuectelModem(port=port)

    async def get_first_modem(self) -> Optional[Modem]:
        """Get first available modem.

        Returns:
            Connected Modem instance, or None if none available.
        """
        if not self._manager.modems:
            await self.discover_modems()

        first_info = self._manager.get_first_modem()
        if first_info:
            return await self.get_modem(first_info.port)

        return None

    async def close_modem(self, port: str) -> None:
        """Close modem connection.

        Args:
            port: Serial port path.
        """
        if port in self._modems:
            modem = self._modems.pop(port)
            await modem.disconnect()
            logger.info("Closed modem on %s", port)

    async def close_all_modems(self) -> None:
        """Close all modem connections."""
        for port in list(self._modems.keys()):
            await self.close_modem(port)

    # =========================================================================
    # Monitoring
    # =========================================================================

    async def start_monitoring(self) -> None:
        """Start background modem monitoring.

        Detects modem connections and disconnections.
        """
        await self._manager.start_monitoring()

    async def stop_monitoring(self) -> None:
        """Stop background modem monitoring."""
        await self._manager.stop_monitoring()

    def on_modem_connected(self, callback: Callable[[ModemInfo], Any]) -> None:
        """Register callback for modem connection events.

        Args:
            callback: Function to call when modem connects.
        """
        self._manager.on_modem_connected(callback)

    def on_modem_disconnected(self, callback: Callable[[ModemInfo], Any]) -> None:
        """Register callback for modem disconnection events.

        Args:
            callback: Function to call when modem disconnects.
        """
        self._manager.on_modem_disconnected(callback)

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def get_modem_profile(self, port: str) -> FullModemProfile:
        """Get full modem profile.

        Args:
            port: Serial port path.

        Returns:
            FullModemProfile with modem, SIM, and network info.
        """
        modem = await self.get_modem(port)
        return await modem.get_profile()

    async def send_at_command(self, port: str, command: str) -> str:
        """Send AT command to modem.

        Args:
            port: Serial port path.
            command: AT command to send.

        Returns:
            Command response.
        """
        modem = await self.get_modem(port)
        return await modem.send_command(command)

    async def start_bip_monitoring(self, port: str) -> None:
        """Start BIP event monitoring on modem.

        Args:
            port: Serial port path.
        """
        modem = await self.get_modem(port)

        # Register callbacks
        for callback in self._bip_callbacks:
            modem.on_bip_event(callback)

        await modem.start_bip_monitoring()
        logger.info("Started BIP monitoring on %s", port)

    async def stop_bip_monitoring(self, port: str) -> None:
        """Stop BIP event monitoring on modem.

        Args:
            port: Serial port path.
        """
        if port in self._modems:
            await self._modems[port].stop_bip_monitoring()
            logger.info("Stopped BIP monitoring on %s", port)

    def on_bip_event(self, callback: Callable[[BIPEvent], Any]) -> None:
        """Register global BIP event callback.

        Callback will be registered on all modems when BIP monitoring starts.

        Args:
            callback: Function to call for BIP events.
        """
        self._bip_callbacks.append(callback)

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self) -> "ModemController":
        """Async context manager entry."""
        await self.discover_modems()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_monitoring()
        await self.close_all_modems()

    def __repr__(self) -> str:
        """String representation."""
        return f"ModemController(modems={len(self._manager.modems)})"


# =============================================================================
# Module-level Convenience Functions
# =============================================================================

_default_controller: Optional[ModemController] = None


async def get_controller() -> ModemController:
    """Get or create default modem controller.

    Returns:
        ModemController instance.
    """
    global _default_controller
    if _default_controller is None:
        _default_controller = ModemController()
    return _default_controller


async def discover_modems() -> List[ModemInfo]:
    """Discover connected modems using default controller.

    Returns:
        List of ModemInfo for detected modems.
    """
    controller = await get_controller()
    return await controller.discover_modems()


async def get_modem(port: str) -> Modem:
    """Get modem instance using default controller.

    Args:
        port: Serial port path.

    Returns:
        Connected Modem instance.
    """
    controller = await get_controller()
    return await controller.get_modem(port)
