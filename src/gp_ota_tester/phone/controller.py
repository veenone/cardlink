"""Phone Controller - Main entry point for Android device management.

This module provides the PhoneController class that integrates all
phone controller components into a unified interface.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional

from gp_ota_tester.phone.adb_client import ADBClient
from gp_ota_tester.phone.at_interface import ATInterface
from gp_ota_tester.phone.bip_monitor import BIPMonitor
from gp_ota_tester.phone.device_info import DeviceInfo
from gp_ota_tester.phone.device_manager import DeviceManager
from gp_ota_tester.phone.exceptions import ADBNotFoundError, DeviceNotFoundError
from gp_ota_tester.phone.models import ADBDevice, BIPEvent, DeviceState
from gp_ota_tester.phone.network_manager import NetworkManager
from gp_ota_tester.phone.sms_trigger import SMSTrigger

logger = logging.getLogger(__name__)


# Callback types
DeviceCallback = Callable[[ADBDevice], None]
BIPCallback = Callable[[BIPEvent], None]
ErrorCallback = Callable[[str, Exception], None]


class Device:
    """Facade for accessing device functionality.

    This class provides a unified interface to all device capabilities:
    - info: Device information retrieval
    - at: AT command interface
    - network: Network configuration
    - sms: SMS trigger sending
    - bip: BIP event monitoring

    Args:
        serial: Device serial number.
        adb_client: ADBClient instance.

    Example:
        ```python
        device = Device("abc123", client)

        # Get device info
        profile = await device.info.get_full_profile()

        # Send AT command
        response = await device.at.send_command("AT+CPIN?")

        # Configure network
        await device.network.enable_wifi()
        ```
    """

    def __init__(self, serial: str, adb_client: ADBClient):
        """Initialize device facade.

        Args:
            serial: Device serial number.
            adb_client: ADBClient instance.
        """
        self._serial = serial
        self._client = adb_client

        # Lazy-initialized components
        self._info: Optional[DeviceInfo] = None
        self._at: Optional[ATInterface] = None
        self._network: Optional[NetworkManager] = None
        self._sms: Optional[SMSTrigger] = None
        self._bip: Optional[BIPMonitor] = None

    @property
    def serial(self) -> str:
        """Get device serial number."""
        return self._serial

    @property
    def info(self) -> DeviceInfo:
        """Get device information interface."""
        if self._info is None:
            self._info = DeviceInfo(self._client, self._serial)
        return self._info

    @property
    def at(self) -> ATInterface:
        """Get AT command interface."""
        if self._at is None:
            self._at = ATInterface(self._client, self._serial)
        return self._at

    @property
    def network(self) -> NetworkManager:
        """Get network manager."""
        if self._network is None:
            self._network = NetworkManager(self._client, self._serial)
        return self._network

    @property
    def sms(self) -> SMSTrigger:
        """Get SMS trigger interface."""
        if self._sms is None:
            self._sms = SMSTrigger(self._client, self._serial, self._at)
        return self._sms

    @property
    def bip(self) -> BIPMonitor:
        """Get BIP monitor."""
        if self._bip is None:
            self._bip = BIPMonitor(self._client, self._serial)
        return self._bip

    async def is_ready(self) -> bool:
        """Check if device is ready for use.

        Returns:
            True if device is connected and authorized.
        """
        try:
            devices = await self._client.get_devices()
            for d in devices:
                if d.serial == self._serial:
                    return d.state == DeviceState.DEVICE
            return False
        except Exception:
            return False


class PhoneController:
    """Main entry point for phone controller functionality.

    This class provides:
    - Device discovery and management
    - Device facades with full functionality
    - Event callbacks for device and BIP events
    - Global monitoring and coordination

    Args:
        adb_path: Optional custom path to ADB executable.
        poll_interval: Device polling interval in seconds.

    Example:
        ```python
        controller = PhoneController()

        # Check ADB availability
        if not controller.is_adb_available():
            print("ADB not found!")
            return

        # Discover devices
        devices = await controller.discover_devices()
        for device in devices:
            print(f"Found: {device.serial}")

        # Get device facade
        phone = await controller.get_device(devices[0].serial)

        # Use device functionality
        profile = await phone.info.get_full_profile()
        print(profile.to_json())

        # Register event callbacks
        controller.on_device_connected(lambda d: print(f"Connected: {d.serial}"))
        controller.on_bip_event(lambda e: print(f"BIP: {e.event_type}"))

        # Start monitoring
        await controller.start_monitoring()
        ```
    """

    def __init__(
        self,
        adb_path: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        """Initialize phone controller.

        Args:
            adb_path: Custom ADB path, or None for auto-detection.
            poll_interval: Device polling interval in seconds.
        """
        self._client = ADBClient(adb_path=adb_path)
        self._manager = DeviceManager(self._client, poll_interval)

        # Device cache
        self._devices: Dict[str, Device] = {}

        # Callbacks
        self._connected_callbacks: List[DeviceCallback] = []
        self._disconnected_callbacks: List[DeviceCallback] = []
        self._bip_callbacks: List[BIPCallback] = []
        self._error_callbacks: List[ErrorCallback] = []

        # BIP monitoring
        self._bip_monitors: Dict[str, BIPMonitor] = {}

        # Setup manager callbacks
        self._manager.on_device_connected(self._on_device_connected)
        self._manager.on_device_disconnected(self._on_device_disconnected)

    def is_adb_available(self) -> bool:
        """Check if ADB is available.

        Returns:
            True if ADB executable is found.
        """
        return self._client.is_available()

    async def get_adb_version(self) -> str:
        """Get ADB version string.

        Returns:
            ADB version string.

        Raises:
            ADBNotFoundError: If ADB is not available.
        """
        return await self._client.get_version()

    async def discover_devices(self) -> List[ADBDevice]:
        """Discover connected ADB devices.

        Returns:
            List of connected devices.
        """
        return await self._manager.scan_devices()

    @property
    def devices(self) -> List[ADBDevice]:
        """Get list of currently tracked devices."""
        return self._manager.devices

    def get_ready_devices(self) -> List[ADBDevice]:
        """Get list of devices in ready state.

        Returns:
            List of devices ready for use.
        """
        return self._manager.get_ready_devices()

    async def get_device(self, serial: str) -> Device:
        """Get device facade for a specific device.

        Args:
            serial: Device serial number.

        Returns:
            Device facade instance.

        Raises:
            DeviceNotFoundError: If device is not connected.
        """
        # Check if device exists
        device_info = self._manager.get_device(serial)
        if device_info is None:
            # Try to scan for it
            await self._manager.scan_devices()
            device_info = self._manager.get_device(serial)

        if device_info is None:
            raise DeviceNotFoundError(serial)

        if device_info.state == DeviceState.UNAUTHORIZED:
            from gp_ota_tester.phone.exceptions import DeviceUnauthorizedError

            raise DeviceUnauthorizedError(serial)

        # Return cached or create new
        if serial not in self._devices:
            self._devices[serial] = Device(serial, self._client)

        return self._devices[serial]

    async def start_monitoring(self) -> None:
        """Start background device monitoring.

        This starts monitoring for device connect/disconnect events.
        """
        await self._manager.start_monitoring()

    async def stop_monitoring(self) -> None:
        """Stop background device monitoring."""
        await self._manager.stop_monitoring()

        # Stop all BIP monitors
        for monitor in self._bip_monitors.values():
            await monitor.stop()
        self._bip_monitors.clear()

    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._manager.is_monitoring

    # =========================================================================
    # Event Callbacks
    # =========================================================================

    def on_device_connected(self, callback: DeviceCallback) -> None:
        """Register callback for device connection events.

        Args:
            callback: Function called when device connects.
        """
        self._connected_callbacks.append(callback)

    def on_device_disconnected(self, callback: DeviceCallback) -> None:
        """Register callback for device disconnection events.

        Args:
            callback: Function called when device disconnects.
        """
        self._disconnected_callbacks.append(callback)

    def on_bip_event(self, callback: BIPCallback) -> None:
        """Register callback for BIP events.

        Note: This requires starting BIP monitoring for each device.

        Args:
            callback: Function called when BIP event is detected.
        """
        self._bip_callbacks.append(callback)

    def on_error(self, callback: ErrorCallback) -> None:
        """Register callback for errors.

        Args:
            callback: Function called with (serial, exception) on error.
        """
        self._error_callbacks.append(callback)

    def _on_device_connected(self, device: ADBDevice) -> None:
        """Handle device connection event."""
        for callback in self._connected_callbacks:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Connected callback error: {e}")

    def _on_device_disconnected(self, device: ADBDevice) -> None:
        """Handle device disconnection event."""
        # Remove from cache
        if device.serial in self._devices:
            del self._devices[device.serial]

        # Stop BIP monitor if running
        if device.serial in self._bip_monitors:
            monitor = self._bip_monitors.pop(device.serial)
            asyncio.create_task(monitor.stop())

        for callback in self._disconnected_callbacks:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Disconnected callback error: {e}")

    def _on_bip_event(self, event: BIPEvent) -> None:
        """Handle BIP event from any device."""
        for callback in self._bip_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"BIP callback error: {e}")

    # =========================================================================
    # BIP Monitoring
    # =========================================================================

    async def start_bip_monitoring(self, serial: str) -> BIPMonitor:
        """Start BIP monitoring for a device.

        Args:
            serial: Device serial number.

        Returns:
            BIPMonitor instance.
        """
        if serial in self._bip_monitors:
            return self._bip_monitors[serial]

        device = await self.get_device(serial)
        monitor = device.bip

        # Register our callback
        monitor.on_bip_event(self._on_bip_event)

        await monitor.start()
        self._bip_monitors[serial] = monitor

        return monitor

    async def stop_bip_monitoring(self, serial: str) -> None:
        """Stop BIP monitoring for a device.

        Args:
            serial: Device serial number.
        """
        if serial in self._bip_monitors:
            monitor = self._bip_monitors.pop(serial)
            await monitor.stop()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def wait_for_device(
        self,
        serial: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Optional[ADBDevice]:
        """Wait for a device to become available.

        Args:
            serial: Specific device serial, or None for any device.
            timeout: Maximum wait time.

        Returns:
            ADBDevice if found, None if timeout.
        """
        return await self._manager.wait_for_device(serial, timeout)

    async def execute_on_all(
        self,
        func,
        *args,
        **kwargs,
    ) -> Dict[str, any]:
        """Execute a function on all connected devices.

        Args:
            func: Async function to execute, takes Device as first arg.
            *args: Additional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Dict mapping serial to result.
        """
        results = {}

        for device_info in self.get_ready_devices():
            try:
                device = await self.get_device(device_info.serial)
                result = await func(device, *args, **kwargs)
                results[device_info.serial] = result
            except Exception as e:
                results[device_info.serial] = e
                logger.error(f"Error on device {device_info.serial}: {e}")

        return results

    async def __aenter__(self) -> "PhoneController":
        """Async context manager entry - starts monitoring."""
        await self.start_monitoring()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - stops monitoring."""
        await self.stop_monitoring()


# ============================================================================
# Module-level convenience functions
# ============================================================================


_default_controller: Optional[PhoneController] = None


def get_controller(
    adb_path: Optional[str] = None,
) -> PhoneController:
    """Get the default phone controller instance.

    Creates a new instance if one doesn't exist.

    Args:
        adb_path: Optional custom ADB path.

    Returns:
        PhoneController instance.
    """
    global _default_controller
    if _default_controller is None:
        _default_controller = PhoneController(adb_path=adb_path)
    return _default_controller


async def discover_devices() -> List[ADBDevice]:
    """Discover connected devices using default controller.

    Returns:
        List of connected ADB devices.
    """
    return await get_controller().discover_devices()


async def get_device(serial: str) -> Device:
    """Get device facade using default controller.

    Args:
        serial: Device serial number.

    Returns:
        Device facade instance.
    """
    return await get_controller().get_device(serial)
