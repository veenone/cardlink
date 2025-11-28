"""Device Manager for tracking connected Android devices.

This module provides the DeviceManager class for discovering devices,
monitoring connection changes, and emitting device events.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional, Set

from gp_ota_tester.phone.adb_client import ADBClient
from gp_ota_tester.phone.models import ADBDevice, DeviceState

logger = logging.getLogger(__name__)


# Event callback types
DeviceCallback = Callable[[ADBDevice], None]
StateChangeCallback = Callable[[ADBDevice, DeviceState, DeviceState], None]


class DeviceManager:
    """Manages device discovery and monitors connection changes.

    This class provides:
    - Device discovery via ADB
    - Background monitoring for connection/disconnection
    - Device state tracking
    - Event callbacks for device events

    Args:
        adb_client: ADBClient instance for device communication.
        poll_interval: Seconds between device scans (default 2.0).

    Example:
        ```python
        client = ADBClient()
        manager = DeviceManager(client)

        # Register callbacks
        manager.on_device_connected(lambda d: print(f"Connected: {d.serial}"))
        manager.on_device_disconnected(lambda d: print(f"Disconnected: {d.serial}"))

        # Start monitoring
        await manager.start_monitoring()

        # Get current devices
        devices = manager.devices
        ```
    """

    def __init__(
        self,
        adb_client: ADBClient,
        poll_interval: float = 2.0,
    ):
        """Initialize device manager.

        Args:
            adb_client: ADBClient instance.
            poll_interval: Seconds between device scans.
        """
        self._client = adb_client
        self._poll_interval = poll_interval

        # Device tracking
        self._devices: Dict[str, ADBDevice] = {}
        self._device_states: Dict[str, DeviceState] = {}

        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Event callbacks
        self._connected_callbacks: List[DeviceCallback] = []
        self._disconnected_callbacks: List[DeviceCallback] = []
        self._state_change_callbacks: List[StateChangeCallback] = []

    @property
    def devices(self) -> List[ADBDevice]:
        """Get list of currently tracked devices."""
        return list(self._devices.values())

    @property
    def device_serials(self) -> Set[str]:
        """Get set of tracked device serial numbers."""
        return set(self._devices.keys())

    @property
    def is_monitoring(self) -> bool:
        """Check if background monitoring is active."""
        return self._monitoring

    def get_device(self, serial: str) -> Optional[ADBDevice]:
        """Get device by serial number.

        Args:
            serial: Device serial number.

        Returns:
            ADBDevice if found, None otherwise.
        """
        return self._devices.get(serial)

    def get_device_state(self, serial: str) -> DeviceState:
        """Get current state of a device.

        Args:
            serial: Device serial number.

        Returns:
            DeviceState, or DISCONNECTED if not found.
        """
        return self._device_states.get(serial, DeviceState.DISCONNECTED)

    async def scan_devices(self) -> List[ADBDevice]:
        """Scan for connected devices and update tracking.

        Returns:
            List of discovered devices.
        """
        try:
            discovered = await self._client.get_devices()
        except Exception as e:
            logger.error(f"Failed to scan devices: {e}")
            return []

        discovered_serials = {d.serial for d in discovered}
        current_serials = set(self._devices.keys())

        # Detect new devices
        new_serials = discovered_serials - current_serials
        for serial in new_serials:
            device = next(d for d in discovered if d.serial == serial)
            self._devices[serial] = device
            self._device_states[serial] = device.state
            logger.info(f"Device connected: {serial} ({device.state.value})")
            self._emit_connected(device)

        # Detect disconnected devices
        disconnected_serials = current_serials - discovered_serials
        for serial in disconnected_serials:
            device = self._devices.pop(serial)
            old_state = self._device_states.pop(serial, DeviceState.DEVICE)
            logger.info(f"Device disconnected: {serial}")
            self._emit_disconnected(device)

        # Detect state changes for existing devices
        for device in discovered:
            if device.serial in current_serials:
                old_state = self._device_states.get(device.serial)
                new_state = device.state

                if old_state != new_state:
                    logger.info(
                        f"Device state changed: {device.serial} "
                        f"{old_state.value if old_state else 'unknown'} -> {new_state.value}"
                    )
                    self._device_states[device.serial] = new_state
                    self._devices[device.serial] = device
                    if old_state:
                        self._emit_state_change(device, old_state, new_state)

        return discovered

    async def start_monitoring(self) -> None:
        """Start background device monitoring.

        Scans for devices periodically and emits events on changes.
        """
        if self._monitoring:
            logger.warning("Monitoring already started")
            return

        self._monitoring = True

        # Initial scan
        await self.scan_devices()

        # Start background task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Device monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background device monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Device monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                await asyncio.sleep(self._poll_interval)
                await self.scan_devices()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    def on_device_connected(self, callback: DeviceCallback) -> None:
        """Register callback for device connection events.

        Args:
            callback: Function called with ADBDevice when connected.
        """
        self._connected_callbacks.append(callback)

    def on_device_disconnected(self, callback: DeviceCallback) -> None:
        """Register callback for device disconnection events.

        Args:
            callback: Function called with ADBDevice when disconnected.
        """
        self._disconnected_callbacks.append(callback)

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """Register callback for device state change events.

        Args:
            callback: Function called with (device, old_state, new_state).
        """
        self._state_change_callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> bool:
        """Remove a registered callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed.
        """
        removed = False
        if callback in self._connected_callbacks:
            self._connected_callbacks.remove(callback)
            removed = True
        if callback in self._disconnected_callbacks:
            self._disconnected_callbacks.remove(callback)
            removed = True
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
            removed = True
        return removed

    def clear_callbacks(self) -> None:
        """Remove all registered callbacks."""
        self._connected_callbacks.clear()
        self._disconnected_callbacks.clear()
        self._state_change_callbacks.clear()

    def _emit_connected(self, device: ADBDevice) -> None:
        """Emit device connected event."""
        for callback in self._connected_callbacks:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Connected callback error: {e}")

    def _emit_disconnected(self, device: ADBDevice) -> None:
        """Emit device disconnected event."""
        for callback in self._disconnected_callbacks:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Disconnected callback error: {e}")

    def _emit_state_change(
        self,
        device: ADBDevice,
        old_state: DeviceState,
        new_state: DeviceState,
    ) -> None:
        """Emit device state change event."""
        for callback in self._state_change_callbacks:
            try:
                callback(device, old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    async def wait_for_device(
        self,
        serial: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Optional[ADBDevice]:
        """Wait for a device to become available.

        Args:
            serial: Specific device serial, or None for any device.
            timeout: Maximum time to wait.

        Returns:
            ADBDevice if found, None if timeout.
        """
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            await self.scan_devices()

            if serial:
                device = self._devices.get(serial)
                if device and device.state == DeviceState.DEVICE:
                    return device
            else:
                # Return any ready device
                for device in self._devices.values():
                    if device.state == DeviceState.DEVICE:
                        return device

            await asyncio.sleep(0.5)

        return None

    async def wait_for_state(
        self,
        serial: str,
        state: DeviceState,
        timeout: float = 30.0,
    ) -> bool:
        """Wait for a device to reach a specific state.

        Args:
            serial: Device serial number.
            state: Target device state.
            timeout: Maximum time to wait.

        Returns:
            True if device reached state, False if timeout.
        """
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            await self.scan_devices()

            current_state = self._device_states.get(serial)
            if current_state == state:
                return True

            await asyncio.sleep(0.5)

        return False

    def get_ready_devices(self) -> List[ADBDevice]:
        """Get list of devices in 'device' (ready) state.

        Returns:
            List of ready devices.
        """
        return [
            d for d in self._devices.values()
            if d.state == DeviceState.DEVICE
        ]

    def get_unauthorized_devices(self) -> List[ADBDevice]:
        """Get list of unauthorized devices.

        Returns:
            List of unauthorized devices.
        """
        return [
            d for d in self._devices.values()
            if d.state == DeviceState.UNAUTHORIZED
        ]

    async def __aenter__(self) -> "DeviceManager":
        """Async context manager entry - starts monitoring."""
        await self.start_monitoring()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - stops monitoring."""
        await self.stop_monitoring()
