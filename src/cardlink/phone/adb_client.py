"""ADB Client for Android device communication.

This module provides the ADBClient class for executing ADB commands,
managing device connections, and streaming logcat output.
"""

import asyncio
import logging
import re
import shutil
from typing import AsyncIterator, List, Optional, Tuple

from cardlink.phone.exceptions import (
    ADBCommandError,
    ADBNotFoundError,
    ADBTimeoutError,
    DeviceNotFoundError,
    DeviceOfflineError,
    DeviceUnauthorizedError,
)
from cardlink.phone.models import ADBDevice, DeviceState

logger = logging.getLogger(__name__)


class ADBClient:
    """Client for executing ADB commands and managing Android devices.

    This class provides methods for:
    - Checking ADB availability
    - Executing ADB commands with timeout support
    - Running shell commands on devices
    - Listing connected devices
    - Streaming logcat output

    Args:
        adb_path: Path to ADB executable. If None, searches PATH.
        default_timeout: Default timeout for commands in seconds.

    Example:
        ```python
        client = ADBClient()
        if client.is_available():
            devices = await client.get_devices()
            for device in devices:
                result = await client.shell("getprop ro.product.model", device.serial)
                print(result)
        ```
    """

    # Regex patterns for parsing device list
    DEVICE_PATTERN = re.compile(
        r"^(?P<serial>[^\s]+)\s+"
        r"(?P<state>device|offline|unauthorized|recovery|sideload|bootloader|no permissions)"
        r"(?:\s+usb:(?P<usb>\S+))?"
        r"(?:\s+product:(?P<product>\S+))?"
        r"(?:\s+model:(?P<model>\S+))?"
        r"(?:\s+device:(?P<device>\S+))?"
        r"(?:\s+transport_id:(?P<transport_id>\d+))?"
    )

    def __init__(
        self,
        adb_path: Optional[str] = None,
        default_timeout: float = 30.0,
    ):
        """Initialize ADB client.

        Args:
            adb_path: Path to ADB executable. Auto-detected if None.
            default_timeout: Default command timeout in seconds.
        """
        self._adb_path = adb_path
        self._default_timeout = default_timeout
        self._resolved_path: Optional[str] = None

    @property
    def adb_path(self) -> str:
        """Get the resolved ADB executable path.

        Raises:
            ADBNotFoundError: If ADB is not found.
        """
        if self._resolved_path is None:
            self._resolved_path = self._find_adb()
        return self._resolved_path

    def _find_adb(self) -> str:
        """Find ADB executable path.

        Returns:
            Path to ADB executable.

        Raises:
            ADBNotFoundError: If ADB is not found.
        """
        if self._adb_path:
            # User specified path
            if shutil.which(self._adb_path):
                return self._adb_path
            raise ADBNotFoundError(f"ADB not found at specified path: {self._adb_path}")

        # Search in PATH
        adb = shutil.which("adb")
        if adb:
            return adb

        # Check common locations
        common_paths = [
            "/usr/bin/adb",
            "/usr/local/bin/adb",
            "~/Android/Sdk/platform-tools/adb",
            "~/Library/Android/sdk/platform-tools/adb",
            "C:\\Users\\%USERNAME%\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe",
        ]

        import os

        for path in common_paths:
            expanded = os.path.expanduser(os.path.expandvars(path))
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                return expanded

        raise ADBNotFoundError()

    def is_available(self) -> bool:
        """Check if ADB is available.

        Returns:
            True if ADB executable is found and executable.
        """
        try:
            _ = self.adb_path
            return True
        except ADBNotFoundError:
            return False

    async def get_version(self) -> str:
        """Get ADB version string.

        Returns:
            ADB version string (e.g., "1.0.41").

        Raises:
            ADBCommandError: If version check fails.
        """
        stdout, _ = await self.execute(["version"])
        # Parse "Android Debug Bridge version X.Y.Z"
        match = re.search(r"Android Debug Bridge version ([\d.]+)", stdout)
        if match:
            return match.group(1)
        return stdout.split("\n")[0]

    async def execute(
        self,
        args: List[str],
        serial: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[str, str]:
        """Execute an ADB command.

        Args:
            args: Command arguments (excluding 'adb').
            serial: Device serial number for device-specific commands.
            timeout: Command timeout in seconds. Uses default if None.

        Returns:
            Tuple of (stdout, stderr) as strings.

        Raises:
            ADBNotFoundError: If ADB is not found.
            ADBTimeoutError: If command times out.
            ADBCommandError: If command fails.
            DeviceNotFoundError: If specified device is not connected.
            DeviceUnauthorizedError: If device is unauthorized.
            DeviceOfflineError: If device is offline.
        """
        cmd = [self.adb_path]

        if serial:
            cmd.extend(["-s", serial])

        cmd.extend(args)

        timeout = timeout or self._default_timeout
        cmd_str = " ".join(cmd)

        logger.debug(f"Executing: {cmd_str}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Check for device errors
            combined = stdout + stderr
            if "device not found" in combined.lower():
                raise DeviceNotFoundError(serial)
            if "device unauthorized" in combined.lower():
                raise DeviceUnauthorizedError(serial or "unknown")
            if "device offline" in combined.lower():
                raise DeviceOfflineError(serial or "unknown")
            if "no devices/emulators found" in combined.lower():
                raise DeviceNotFoundError(serial)

            if process.returncode != 0:
                raise ADBCommandError(
                    command=cmd_str,
                    message=stderr.strip() or stdout.strip() or f"Exit code {process.returncode}",
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )

            logger.debug(f"Output: {stdout[:200]}...")
            return stdout, stderr

        except asyncio.TimeoutError:
            raise ADBTimeoutError(cmd_str, timeout)

    async def shell(
        self,
        command: str,
        serial: Optional[str] = None,
        timeout: Optional[float] = None,
        check_error: bool = True,
    ) -> str:
        """Execute a shell command on the device.

        Args:
            command: Shell command to execute.
            serial: Device serial number.
            timeout: Command timeout in seconds.
            check_error: Whether to check for shell command errors.

        Returns:
            Command output as string.

        Raises:
            ADBCommandError: If command fails and check_error is True.
        """
        stdout, stderr = await self.execute(
            ["shell", command],
            serial=serial,
            timeout=timeout,
        )

        # Shell commands return stdout even on error
        output = stdout.strip()

        if check_error:
            # Check for common error patterns
            if output.startswith("error:") or output.startswith("/system/bin/sh:"):
                raise ADBCommandError(
                    command=f"shell {command}",
                    message=output,
                    stdout=stdout,
                    stderr=stderr,
                )

        return output

    async def shell_with_exit_code(
        self,
        command: str,
        serial: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[str, int]:
        """Execute shell command and return output with exit code.

        Args:
            command: Shell command to execute.
            serial: Device serial number.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (output, exit_code).
        """
        # Run command and capture exit code
        full_command = f"{command}; echo $?"
        output = await self.shell(full_command, serial, timeout, check_error=False)

        # Parse exit code from last line
        lines = output.strip().split("\n")
        try:
            exit_code = int(lines[-1])
            output = "\n".join(lines[:-1])
        except (ValueError, IndexError):
            exit_code = 0

        return output, exit_code

    async def get_devices(self) -> List[ADBDevice]:
        """Get list of connected ADB devices.

        Returns:
            List of ADBDevice objects representing connected devices.
        """
        stdout, _ = await self.execute(["devices", "-l"])

        devices: List[ADBDevice] = []
        for line in stdout.strip().split("\n"):
            if not line or line.startswith("List of devices"):
                continue

            match = self.DEVICE_PATTERN.match(line)
            if match:
                groups = match.groupdict()

                # Map state string to enum
                state_str = groups.get("state", "")
                try:
                    state = DeviceState(state_str)
                except ValueError:
                    state = DeviceState.DISCONNECTED

                device = ADBDevice(
                    serial=groups.get("serial", ""),
                    state=state,
                    product=groups.get("product") or "",
                    model=groups.get("model") or "",
                    device=groups.get("device") or "",
                    transport_id=int(groups.get("transport_id") or 0),
                    usb=groups.get("usb") or "",
                )
                devices.append(device)

        return devices

    async def wait_for_device(
        self,
        serial: str,
        timeout: float = 30.0,
    ) -> bool:
        """Wait for a device to become available.

        Args:
            serial: Device serial number.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if device became available, False if timeout.
        """
        try:
            await self.execute(
                ["wait-for-device"],
                serial=serial,
                timeout=timeout,
            )
            return True
        except (ADBTimeoutError, DeviceNotFoundError):
            return False

    async def start_logcat(
        self,
        serial: str,
        filters: Optional[List[str]] = None,
        buffer: str = "main",
        clear: bool = False,
    ) -> AsyncIterator[str]:
        """Start streaming logcat output.

        Args:
            serial: Device serial number.
            filters: List of logcat filter specs (e.g., ["*:S", "CAT:V"]).
            buffer: Log buffer to read (main, system, radio, events, crash).
            clear: Whether to clear the buffer before starting.

        Yields:
            Log lines as strings.

        Example:
            ```python
            async for line in client.start_logcat("device123", ["Telephony:V"]):
                print(line)
            ```
        """
        if clear:
            await self.execute(["logcat", "-c", "-b", buffer], serial=serial)

        cmd = [self.adb_path, "-s", serial, "logcat", "-b", buffer, "-v", "threadtime"]

        if filters:
            cmd.extend(filters)

        logger.debug(f"Starting logcat: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                if process.stdout is None:
                    break

                line = await process.stdout.readline()
                if not line:
                    break

                yield line.decode("utf-8", errors="replace").rstrip()

        finally:
            # Cleanup
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    process.kill()

    async def root(self, serial: str) -> bool:
        """Restart ADB as root on the device.

        Args:
            serial: Device serial number.

        Returns:
            True if root access was granted.
        """
        try:
            stdout, _ = await self.execute(["root"], serial=serial)
            # "restarting adbd as root" or "adbd is already running as root"
            return "root" in stdout.lower()
        except ADBCommandError as e:
            logger.warning(f"Root failed: {e}")
            return False

    async def unroot(self, serial: str) -> bool:
        """Restart ADB as non-root on the device.

        Args:
            serial: Device serial number.

        Returns:
            True if successful.
        """
        try:
            await self.execute(["unroot"], serial=serial)
            return True
        except ADBCommandError:
            return False

    async def is_root(self, serial: str) -> bool:
        """Check if ADB is running as root.

        Args:
            serial: Device serial number.

        Returns:
            True if running as root.
        """
        output = await self.shell("id", serial=serial)
        return "uid=0(root)" in output

    async def push(
        self,
        serial: str,
        local: str,
        remote: str,
        timeout: Optional[float] = None,
    ) -> bool:
        """Push a file to the device.

        Args:
            serial: Device serial number.
            local: Local file path.
            remote: Remote destination path.
            timeout: Transfer timeout.

        Returns:
            True if successful.
        """
        try:
            await self.execute(["push", local, remote], serial=serial, timeout=timeout)
            return True
        except ADBCommandError:
            return False

    async def pull(
        self,
        serial: str,
        remote: str,
        local: str,
        timeout: Optional[float] = None,
    ) -> bool:
        """Pull a file from the device.

        Args:
            serial: Device serial number.
            remote: Remote file path.
            local: Local destination path.
            timeout: Transfer timeout.

        Returns:
            True if successful.
        """
        try:
            await self.execute(["pull", remote, local], serial=serial, timeout=timeout)
            return True
        except ADBCommandError:
            return False

    async def get_property(
        self,
        serial: str,
        prop: str,
    ) -> str:
        """Get a system property value.

        Args:
            serial: Device serial number.
            prop: Property name (e.g., "ro.product.model").

        Returns:
            Property value or empty string if not found.
        """
        output = await self.shell(f"getprop {prop}", serial=serial, check_error=False)
        return output.strip()

    async def set_property(
        self,
        serial: str,
        prop: str,
        value: str,
    ) -> bool:
        """Set a system property value.

        Args:
            serial: Device serial number.
            prop: Property name.
            value: Property value.

        Returns:
            True if successful.

        Note:
            Most system properties require root access to modify.
        """
        try:
            await self.shell(f"setprop {prop} '{value}'", serial=serial)
            return True
        except ADBCommandError:
            return False

    async def reboot(
        self,
        serial: str,
        mode: Optional[str] = None,
    ) -> None:
        """Reboot the device.

        Args:
            serial: Device serial number.
            mode: Reboot mode (None=normal, "bootloader", "recovery").
        """
        args = ["reboot"]
        if mode:
            args.append(mode)
        await self.execute(args, serial=serial)

    async def disconnect(self, serial: str) -> bool:
        """Disconnect from a device (for TCP/IP connections).

        Args:
            serial: Device serial/address to disconnect.

        Returns:
            True if disconnected.
        """
        try:
            await self.execute(["disconnect", serial])
            return True
        except ADBCommandError:
            return False

    async def connect(
        self,
        host: str,
        port: int = 5555,
        timeout: float = 10.0,
    ) -> bool:
        """Connect to a device over TCP/IP.

        Args:
            host: Device IP address.
            port: ADB port (default 5555).
            timeout: Connection timeout.

        Returns:
            True if connected.
        """
        try:
            stdout, _ = await self.execute(
                ["connect", f"{host}:{port}"],
                timeout=timeout,
            )
            return "connected" in stdout.lower()
        except ADBCommandError:
            return False
