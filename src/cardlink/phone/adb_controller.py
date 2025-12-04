"""ADB-based Android device control.

This module provides an interface to control Android devices via the
Android Debug Bridge (ADB) command-line tool.
"""

import logging
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Information about an Android device.

    Attributes:
        serial: Device serial number.
        model: Device model name.
        android_version: Android OS version (e.g., "13").
        sdk_version: Android SDK version number.
        manufacturer: Device manufacturer name.
    """

    serial: str
    model: str
    android_version: str
    sdk_version: int
    manufacturer: str


class ADBController:
    """Control Android device via ADB.

    This class provides methods to interact with Android devices using the
    ADB (Android Debug Bridge) command-line tool. It requires ADB to be
    installed and accessible in the system PATH.

    Example:
        >>> # List connected devices
        >>> devices = ADBController.list_devices()
        >>> print(f"Found {len(devices)} device(s)")
        >>>
        >>> # Connect to first device
        >>> adb = ADBController(devices[0] if devices else None)
        >>> info = adb.get_device_info()
        >>> print(f"Device: {info.model} running Android {info.android_version}")
        >>>
        >>> # Execute shell command
        >>> result = adb.shell('getprop ro.build.version.sdk')
        >>> print(f"SDK version: {result}")
    """

    def __init__(self, serial: Optional[str] = None):
        """Initialize ADB controller.

        Args:
            serial: Device serial number to target. If None, will use the
                   only connected device (fails if multiple devices).

        Raises:
            RuntimeError: If ADB is not installed or not found in PATH.
        """
        self.serial = serial
        self._verify_adb()

    def _verify_adb(self) -> None:
        """Verify ADB is available.

        Raises:
            RuntimeError: If ADB is not installed or not accessible.
        """
        try:
            result = subprocess.run(
                ["adb", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("ADB not found")
            logger.debug(f"ADB version: {result.stdout.strip().split()[4]}")
        except FileNotFoundError:
            raise RuntimeError(
                "ADB not installed. Please install Android SDK Platform Tools."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ADB command timed out")

    def _adb(self, *args: str, timeout: int = 30) -> str:
        """Execute ADB command.

        Args:
            *args: ADB command arguments.
            timeout: Command timeout in seconds.

        Returns:
            Command stdout output.

        Raises:
            RuntimeError: If command fails or times out.
        """
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)

        logger.debug(f"ADB: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode != 0:
                raise RuntimeError(f"ADB error: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ADB command timed out after {timeout}s")

    def shell(self, command: str, timeout: int = 30) -> str:
        """Execute shell command on device.

        Args:
            command: Shell command to execute.
            timeout: Command timeout in seconds.

        Returns:
            Command output.

        Example:
            >>> adb = ADBController()
            >>> output = adb.shell('getprop ro.build.version.release')
            >>> print(f"Android version: {output}")
        """
        return self._adb("shell", command, timeout=timeout)

    @classmethod
    def list_devices(cls) -> List[str]:
        """List connected devices.

        Returns:
            List of device serial numbers.

        Example:
            >>> devices = ADBController.list_devices()
            >>> for device in devices:
            ...     print(f"Device: {device}")
        """
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            devices = [
                line.split("\t")[0] for line in lines if "\tdevice" in line
            ]
            logger.debug(f"Found {len(devices)} device(s)")
            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def get_device_info(self) -> DeviceInfo:
        """Get device information.

        Returns:
            DeviceInfo object with device details.

        Raises:
            RuntimeError: If unable to retrieve device information.

        Example:
            >>> adb = ADBController()
            >>> info = adb.get_device_info()
            >>> print(f"{info.manufacturer} {info.model}")
        """
        try:
            return DeviceInfo(
                serial=self.serial or self._adb("get-serialno"),
                model=self.shell("getprop ro.product.model"),
                android_version=self.shell("getprop ro.build.version.release"),
                sdk_version=int(self.shell("getprop ro.build.version.sdk")),
                manufacturer=self.shell("getprop ro.product.manufacturer"),
            )
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(f"Failed to get device info: {e}") from e

    def is_screen_on(self) -> bool:
        """Check if screen is on.

        Returns:
            True if screen is on, False otherwise.

        Example:
            >>> adb = ADBController()
            >>> if not adb.is_screen_on():
            ...     adb.wake_screen()
        """
        try:
            # Try modern method first (Android 7+)
            result = self.shell("dumpsys display | grep 'mScreenState'")
            return "ON" in result
        except RuntimeError:
            # Fallback for older Android versions
            try:
                result = self.shell("dumpsys power | grep 'Display Power'")
                return "state=ON" in result or "state=2" in result
            except RuntimeError:
                logger.warning("Could not determine screen state")
                return False

    def wake_screen(self) -> None:
        """Wake up screen if it's off.

        Example:
            >>> adb = ADBController()
            >>> adb.wake_screen()
        """
        if not self.is_screen_on():
            try:
                self.shell("input keyevent KEYCODE_WAKEUP")
                logger.debug("Screen woken up")
            except RuntimeError as e:
                logger.warning(f"Failed to wake screen: {e}")

    def push_file(self, local: str, remote: str) -> None:
        """Push file to device.

        Args:
            local: Local file path.
            remote: Remote (device) file path.

        Raises:
            RuntimeError: If push fails.

        Example:
            >>> adb = ADBController()
            >>> adb.push_file('config.json', '/sdcard/config.json')
        """
        self._adb("push", local, remote)
        logger.debug(f"Pushed {local} -> {remote}")

    def pull_file(self, remote: str, local: str) -> None:
        """Pull file from device.

        Args:
            remote: Remote (device) file path.
            local: Local file path.

        Raises:
            RuntimeError: If pull fails.

        Example:
            >>> adb = ADBController()
            >>> adb.pull_file('/sdcard/log.txt', 'device_log.txt')
        """
        self._adb("pull", remote, local)
        logger.debug(f"Pulled {remote} -> {local}")

    def get_property(self, prop: str) -> str:
        """Get system property value.

        Args:
            prop: Property name (e.g., 'ro.build.version.sdk').

        Returns:
            Property value.

        Example:
            >>> adb = ADBController()
            >>> sdk = adb.get_property('ro.build.version.sdk')
        """
        return self.shell(f"getprop {prop}")

    def reboot(self, mode: Optional[str] = None) -> None:
        """Reboot device.

        Args:
            mode: Reboot mode ('bootloader', 'recovery', or None for normal).

        Example:
            >>> adb = ADBController()
            >>> adb.reboot()  # Normal reboot
            >>> adb.reboot('recovery')  # Reboot to recovery
        """
        if mode:
            self._adb("reboot", mode)
        else:
            self._adb("reboot")
        logger.info(f"Device rebooting{' to ' + mode if mode else ''}")
