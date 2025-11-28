"""Modem Manager for Modem Controller.

This module manages modem discovery, connection monitoring,
and modem lifecycle management.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from gp_ota_tester.modem.at_interface import ATInterface
from gp_ota_tester.modem.exceptions import ModemNotFoundError, SerialPortError
from gp_ota_tester.modem.models import (
    ModemProfile,
    ModemVendor,
    PortInfo,
    QUECTEL_USB_IDS,
)
from gp_ota_tester.modem.serial_client import SerialClient

logger = logging.getLogger(__name__)

# Default polling interval for modem monitoring
DEFAULT_POLL_INTERVAL = 5.0

# Identification timeout
IDENTIFY_TIMEOUT = 3.0


class ModemManager:
    """Manages modem discovery and connection state.

    Provides automatic modem detection, identification, and
    connection monitoring with event callbacks.

    Example:
        >>> manager = ModemManager()
        >>>
        >>> # One-time scan
        >>> modems = await manager.scan_modems()
        >>> for modem in modems:
        ...     print(f"{modem.port}: {modem.manufacturer} {modem.model}")
        >>>
        >>> # Background monitoring
        >>> manager.on_modem_connected(lambda info: print(f"Connected: {info.port}"))
        >>> await manager.start_monitoring()
    """

    def __init__(self, poll_interval: float = DEFAULT_POLL_INTERVAL):
        """Initialize modem manager.

        Args:
            poll_interval: Interval between modem scans in seconds.
        """
        self.poll_interval = poll_interval

        # Connected modems registry: port -> ModemInfo
        self._modems: Dict[str, ModemInfo] = {}

        # Known ports from last scan
        self._known_ports: Set[str] = set()

        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Event callbacks
        self._on_connected_callbacks: List[Callable] = []
        self._on_disconnected_callbacks: List[Callable] = []

    @property
    def modems(self) -> Dict[str, "ModemInfo"]:
        """Get dictionary of connected modems."""
        return self._modems.copy()

    @property
    def connected_ports(self) -> List[str]:
        """Get list of connected modem ports."""
        return list(self._modems.keys())

    def is_modem_connected(self, port: str) -> bool:
        """Check if specific modem is connected.

        Args:
            port: Serial port path.

        Returns:
            True if modem is connected on port.
        """
        return port in self._modems

    async def scan_modems(self) -> List["ModemInfo"]:
        """Perform one-time modem scan.

        Scans all serial ports for connected modems and identifies them.

        Returns:
            List of ModemInfo for detected modems.
        """
        logger.debug("Scanning for modems...")

        # Get list of modem-like ports
        modem_ports = SerialClient.list_modem_ports()

        # Also get all ports in case USB IDs aren't recognized
        all_ports = SerialClient.list_ports()

        # Combine, preferring modem_ports but including others
        ports_to_check = {p.port: p for p in modem_ports}
        for port in all_ports:
            if port.port not in ports_to_check:
                # Check if it looks like an AT port
                desc = port.description.lower()
                if any(x in desc for x in ["at", "modem", "gsm", "lte", "usb serial"]):
                    ports_to_check[port.port] = port

        detected = []
        for port_path, port_info in ports_to_check.items():
            info = await self._identify_modem(port_path, port_info)
            if info:
                detected.append(info)
                self._modems[port_path] = info

        logger.info("Found %d modem(s)", len(detected))
        return detected

    async def _identify_modem(
        self,
        port: str,
        port_info: Optional[PortInfo] = None,
    ) -> Optional["ModemInfo"]:
        """Identify modem on serial port.

        Args:
            port: Serial port path.
            port_info: Optional port information.

        Returns:
            ModemInfo if modem identified, None otherwise.
        """
        serial = SerialClient(port, timeout=IDENTIFY_TIMEOUT)

        try:
            await serial.open()

            # Create temporary AT interface
            at = ATInterface(serial)

            # Clear any pending data
            await serial.clear_buffers()

            # Try AT command first
            try:
                response = await at.send_command("AT", timeout=1.0, check_error=False)
                if not response.success:
                    return None
            except Exception:
                return None

            # Get identification info
            profile = await self._get_modem_profile(at)

            # Create ModemInfo
            info = ModemInfo(
                port=port,
                port_info=port_info or PortInfo(port=port),
                profile=profile,
            )

            logger.debug("Identified modem on %s: %s %s", port, profile.manufacturer, profile.model)
            return info

        except SerialPortError as e:
            logger.debug("Cannot access port %s: %s", port, e)
            return None
        except Exception as e:
            logger.debug("Error identifying modem on %s: %s", port, e)
            return None
        finally:
            await serial.close()

    async def _get_modem_profile(self, at: ATInterface) -> ModemProfile:
        """Get basic modem profile via AT commands.

        Args:
            at: AT interface.

        Returns:
            ModemProfile with basic info.
        """
        profile = ModemProfile()

        # Get manufacturer (AT+CGMI)
        try:
            response = await at.send_command("AT+CGMI", timeout=2.0, check_error=False)
            if response.success and response.data:
                profile.manufacturer = response.data[0].strip()
        except Exception:
            pass

        # Get model (AT+CGMM)
        try:
            response = await at.send_command("AT+CGMM", timeout=2.0, check_error=False)
            if response.success and response.data:
                profile.model = response.data[0].strip()
        except Exception:
            pass

        # Get firmware (AT+CGMR)
        try:
            response = await at.send_command("AT+CGMR", timeout=2.0, check_error=False)
            if response.success and response.data:
                profile.firmware_version = response.data[0].strip()
        except Exception:
            pass

        # Get IMEI (AT+CGSN)
        try:
            response = await at.send_command("AT+CGSN", timeout=2.0, check_error=False)
            if response.success and response.data:
                profile.imei = response.data[0].strip()
        except Exception:
            pass

        # Determine vendor
        profile.vendor = self._detect_vendor(profile)

        return profile

    def _detect_vendor(self, profile: ModemProfile) -> ModemVendor:
        """Detect vendor from profile information."""
        manufacturer = profile.manufacturer.lower()

        if "quectel" in manufacturer:
            return ModemVendor.QUECTEL
        elif "sierra" in manufacturer:
            return ModemVendor.SIERRA
        elif "simcom" in manufacturer:
            return ModemVendor.SIMCOM
        elif "telit" in manufacturer:
            return ModemVendor.TELIT
        elif "u-blox" in manufacturer or "ublox" in manufacturer:
            return ModemVendor.UBLOX
        elif "huawei" in manufacturer:
            return ModemVendor.HUAWEI
        elif "zte" in manufacturer:
            return ModemVendor.ZTE

        return ModemVendor.UNKNOWN

    # =========================================================================
    # Background Monitoring
    # =========================================================================

    async def start_monitoring(self) -> None:
        """Start background modem monitoring.

        Periodically scans for modem changes and emits events.
        """
        if self._monitoring:
            return

        self._monitoring = True

        # Initial scan
        await self.scan_modems()
        self._known_ports = set(self._modems.keys())

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started modem monitoring (interval=%ds)", self.poll_interval)

    async def stop_monitoring(self) -> None:
        """Stop background modem monitoring."""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Stopped modem monitoring")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                await asyncio.sleep(self.poll_interval)

                if not self._monitoring:
                    break

                # Check for changes
                await self._check_modem_changes()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in modem monitor: %s", e)

    async def _check_modem_changes(self) -> None:
        """Check for modem connection/disconnection changes."""
        # Get current modem ports
        modem_ports = SerialClient.list_modem_ports()
        current_ports = {p.port for p in modem_ports}

        # Detect new connections
        new_ports = current_ports - self._known_ports
        for port in new_ports:
            port_info = next((p for p in modem_ports if p.port == port), None)
            info = await self._identify_modem(port, port_info)
            if info:
                self._modems[port] = info
                await self._emit_connected(info)

        # Detect disconnections
        removed_ports = self._known_ports - current_ports
        for port in removed_ports:
            if port in self._modems:
                info = self._modems.pop(port)
                await self._emit_disconnected(info)

        self._known_ports = current_ports

    async def _emit_connected(self, info: "ModemInfo") -> None:
        """Emit modem connected event."""
        logger.info("Modem connected: %s (%s %s)", info.port, info.profile.manufacturer, info.profile.model)

        for callback in self._on_connected_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(info)
                else:
                    callback(info)
            except Exception as e:
                logger.error("Error in connected callback: %s", e)

    async def _emit_disconnected(self, info: "ModemInfo") -> None:
        """Emit modem disconnected event."""
        logger.info("Modem disconnected: %s", info.port)

        for callback in self._on_disconnected_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(info)
                else:
                    callback(info)
            except Exception as e:
                logger.error("Error in disconnected callback: %s", e)

    # =========================================================================
    # Event Registration
    # =========================================================================

    def on_modem_connected(self, callback: Callable[["ModemInfo"], Any]) -> None:
        """Register callback for modem connection events.

        Args:
            callback: Function to call when modem connects.
        """
        self._on_connected_callbacks.append(callback)

    def on_modem_disconnected(self, callback: Callable[["ModemInfo"], Any]) -> None:
        """Register callback for modem disconnection events.

        Args:
            callback: Function to call when modem disconnects.
        """
        self._on_disconnected_callbacks.append(callback)

    # =========================================================================
    # Modem Access
    # =========================================================================

    def get_modem(self, port: str) -> "ModemInfo":
        """Get modem info by port.

        Args:
            port: Serial port path.

        Returns:
            ModemInfo for the port.

        Raises:
            ModemNotFoundError: If modem not found on port.
        """
        if port not in self._modems:
            raise ModemNotFoundError(port)
        return self._modems[port]

    def get_first_modem(self) -> Optional["ModemInfo"]:
        """Get first available modem.

        Returns:
            ModemInfo for first modem, None if none connected.
        """
        if self._modems:
            return next(iter(self._modems.values()))
        return None


class ModemInfo:
    """Information about a connected modem.

    Contains port information and basic modem profile.
    """

    def __init__(
        self,
        port: str,
        port_info: PortInfo,
        profile: ModemProfile,
    ):
        """Initialize modem info.

        Args:
            port: Serial port path.
            port_info: Port information.
            profile: Modem profile.
        """
        self.port = port
        self.port_info = port_info
        self.profile = profile

    @property
    def manufacturer(self) -> str:
        """Get manufacturer name."""
        return self.profile.manufacturer

    @property
    def model(self) -> str:
        """Get model name."""
        return self.profile.model

    @property
    def vendor(self) -> ModemVendor:
        """Get vendor enum."""
        return self.profile.vendor

    @property
    def imei(self) -> str:
        """Get IMEI."""
        return self.profile.imei

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "port": self.port,
            "manufacturer": self.profile.manufacturer,
            "model": self.profile.model,
            "firmware": self.profile.firmware_version,
            "imei": self.profile.imei,
            "vendor": self.profile.vendor.value,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"ModemInfo(port={self.port!r}, manufacturer={self.manufacturer!r}, model={self.model!r})"
