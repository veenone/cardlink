"""Base Modem class for vendor implementations.

This module defines the abstract base class for vendor-specific
modem implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from cardlink.modem.at_interface import ATInterface
from cardlink.modem.bip_monitor import BIPMonitor
from cardlink.modem.models import (
    BIPEvent,
    FullModemProfile,
    ModemProfile,
    ModemVendor,
    NetworkProfile,
    SIMProfile,
)
from cardlink.modem.modem_info import ModemInfoRetriever
from cardlink.modem.network_manager import NetworkManager
from cardlink.modem.serial_client import SerialClient
from cardlink.modem.sms_trigger import SMSTrigger

logger = logging.getLogger(__name__)


@dataclass
class SignalInfo:
    """Signal quality information."""

    rssi: Optional[int] = None  # dBm
    rsrp: Optional[int] = None  # dBm (LTE)
    rsrq: Optional[int] = None  # dB (LTE)
    sinr: Optional[int] = None  # dB (LTE)
    ber: Optional[int] = None  # Bit error rate


class Modem(ABC):
    """Abstract base class for modem implementations.

    Provides common functionality and defines interface for
    vendor-specific implementations.

    Example:
        >>> modem = QuectelModem(port="/dev/ttyUSB2")
        >>> await modem.connect()
        >>>
        >>> # Get info
        >>> profile = await modem.get_profile()
        >>> print(f"{profile.modem.manufacturer} {profile.modem.model}")
        >>>
        >>> # Start BIP monitoring
        >>> modem.on_bip_event(lambda e: print(f"BIP: {e.command}"))
        >>> await modem.start_bip_monitoring()
        >>>
        >>> await modem.disconnect()
    """

    # Vendor identifier (override in subclass)
    VENDOR: ModemVendor = ModemVendor.UNKNOWN

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ):
        """Initialize modem.

        Args:
            port: Serial port path.
            baudrate: Baud rate.
            timeout: Default timeout.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # Core components
        self._serial: Optional[SerialClient] = None
        self._at: Optional[ATInterface] = None

        # Feature modules
        self._info: Optional[ModemInfoRetriever] = None
        self._network: Optional[NetworkManager] = None
        self._sms: Optional[SMSTrigger] = None
        self._bip_monitor: Optional[BIPMonitor] = None

        # State
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if modem is connected."""
        return self._connected and self._serial is not None and self._serial.is_open

    @property
    def at(self) -> ATInterface:
        """Get AT interface."""
        if self._at is None:
            raise RuntimeError("Modem not connected")
        return self._at

    @property
    def info(self) -> ModemInfoRetriever:
        """Get info retriever."""
        if self._info is None:
            raise RuntimeError("Modem not connected")
        return self._info

    @property
    def network(self) -> NetworkManager:
        """Get network manager."""
        if self._network is None:
            raise RuntimeError("Modem not connected")
        return self._network

    @property
    def sms(self) -> SMSTrigger:
        """Get SMS trigger."""
        if self._sms is None:
            raise RuntimeError("Modem not connected")
        return self._sms

    async def connect(self) -> None:
        """Connect to modem and initialize components.

        Raises:
            Exception: If connection fails.
        """
        if self._connected:
            return

        # Create serial client
        self._serial = SerialClient(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

        # Open connection
        await self._serial.open()

        # Create AT interface
        self._at = ATInterface(self._serial)

        # Verify modem responds
        if not await self._at.check_alive():
            await self._serial.close()
            raise RuntimeError(f"Modem not responding on {self.port}")

        # Initialize components
        self._info = ModemInfoRetriever(self._at)
        self._network = NetworkManager(self._at)
        self._sms = SMSTrigger(self._at)
        self._bip_monitor = BIPMonitor(self._at)

        # Vendor-specific initialization
        await self._initialize()

        self._connected = True
        logger.info("Connected to modem on %s", self.port)

    async def disconnect(self) -> None:
        """Disconnect from modem."""
        if not self._connected:
            return

        # Stop BIP monitoring
        if self._bip_monitor and self._bip_monitor.is_running:
            await self._bip_monitor.stop()

        # Stop URC monitoring
        if self._at:
            await self._at.stop_urc_monitoring()

        # Close serial
        if self._serial:
            await self._serial.close()

        self._connected = False
        self._serial = None
        self._at = None
        self._info = None
        self._network = None
        self._sms = None
        self._bip_monitor = None

        logger.info("Disconnected from modem on %s", self.port)

    async def _initialize(self) -> None:
        """Vendor-specific initialization.

        Override in subclass for vendor-specific setup.
        """
        pass

    # =========================================================================
    # AT Commands
    # =========================================================================

    async def send_command(
        self,
        command: str,
        timeout: Optional[float] = None,
        check_error: bool = True,
    ) -> str:
        """Send AT command and return response.

        Args:
            command: AT command to send.
            timeout: Command timeout.
            check_error: Whether to raise on error.

        Returns:
            Response data as string.
        """
        response = await self.at.send_command(command, timeout, check_error=check_error)
        return "\n".join(response.data) if response.data else ""

    # =========================================================================
    # Information
    # =========================================================================

    async def get_profile(self, force_refresh: bool = False) -> FullModemProfile:
        """Get full modem profile.

        Args:
            force_refresh: Force refresh cached data.

        Returns:
            FullModemProfile with all information.
        """
        profile = await self.info.get_full_profile(force_refresh)
        profile.port = self.port
        return profile

    async def get_modem_info(self) -> ModemProfile:
        """Get modem hardware/firmware info."""
        return await self.info.get_modem_info()

    async def get_sim_info(self) -> SIMProfile:
        """Get SIM card info."""
        return await self.info.get_sim_info()

    async def get_network_info(self) -> NetworkProfile:
        """Get network info."""
        return await self.info.get_network_info()

    @abstractmethod
    async def get_signal_info(self) -> SignalInfo:
        """Get detailed signal information.

        Vendor-specific implementation.

        Returns:
            SignalInfo with signal quality data.
        """
        pass

    # =========================================================================
    # Network
    # =========================================================================

    async def configure_apn(
        self,
        apn: str,
        username: str = "",
        password: str = "",
    ) -> bool:
        """Configure APN settings."""
        return await self.network.configure_apn(apn, username=username, password=password)

    async def is_registered(self) -> bool:
        """Check if registered to network."""
        info = await self.network.check_registration()
        return info.is_registered

    async def wait_for_registration(self, timeout: float = 60.0) -> bool:
        """Wait for network registration."""
        return await self.network.wait_for_registration(timeout)

    async def ping(self, host: str, count: int = 4) -> bool:
        """Ping host.

        Returns:
            True if at least one ping succeeds.
        """
        result = await self.network.ping(host, count)
        return result.success

    # =========================================================================
    # BIP Monitoring
    # =========================================================================

    async def start_bip_monitoring(self) -> None:
        """Start BIP event monitoring."""
        if self._bip_monitor:
            await self._bip_monitor.start()

    async def stop_bip_monitoring(self) -> None:
        """Stop BIP event monitoring."""
        if self._bip_monitor:
            await self._bip_monitor.stop()

    def on_bip_event(self, callback: Callable[[BIPEvent], Any]) -> None:
        """Register BIP event callback."""
        if self._bip_monitor:
            self._bip_monitor.on_bip_event(callback)

    # =========================================================================
    # SMS Trigger
    # =========================================================================

    async def send_sms_pdu(self, pdu_hex: str) -> bool:
        """Send SMS in PDU mode.

        Args:
            pdu_hex: Hex-encoded PDU.

        Returns:
            True if send successful.
        """
        result = await self.sms.send_raw_pdu(pdu_hex)
        return result.success

    # =========================================================================
    # Vendor-Specific (override in subclass)
    # =========================================================================

    @abstractmethod
    async def enable_stk(self) -> bool:
        """Enable STK notifications.

        Vendor-specific implementation.

        Returns:
            True if successful.
        """
        pass

    async def __aenter__(self) -> "Modem":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected else "disconnected"
        return f"{self.__class__.__name__}(port={self.port!r}, {status})"
