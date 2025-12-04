"""WiFi and network management via ADB.

This module provides WiFi and network configuration capabilities for
Android devices via ADB.
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import List, Optional

from cardlink.phone.adb_controller import ADBController

logger = logging.getLogger(__name__)


@dataclass
class WiFiNetwork:
    """WiFi network information.

    Attributes:
        ssid: Network SSID (name).
        bssid: Network BSSID (MAC address).
        signal: Signal strength (RSSI in dBm).
        security: Security type (e.g., "WPA2", "WPA3", "Open").
    """

    ssid: str
    bssid: str
    signal: int
    security: str


@dataclass
class NetworkStatus:
    """Current network status.

    Attributes:
        wifi_enabled: Whether WiFi is enabled.
        connected: Whether connected to a network.
        ssid: Connected network SSID (None if not connected).
        ip_address: Device IP address (None if not connected).
        gateway: Gateway IP address (None if not connected).
    """

    wifi_enabled: bool
    connected: bool
    ssid: Optional[str]
    ip_address: Optional[str]
    gateway: Optional[str]


class NetworkManager:
    """Manage device network settings."""

    def __init__(self, adb: ADBController):
        """Initialize network manager."""
        self.adb = adb

    def get_status(self) -> NetworkStatus:
        """Get current network status."""
        try:
            wifi_info = self.adb.shell("dumpsys wifi | grep 'mWifiInfo'")
            wifi_state = self.adb.shell("dumpsys wifi | grep 'Wi-Fi is'")
            wifi_enabled = "enabled" in wifi_state

            ssid_match = re.search(r'SSID: "?([^",]+)"?,', wifi_info)
            ssid = ssid_match.group(1) if ssid_match else None

            ip_address = None
            gateway = None
            if ssid and ssid != "<unknown ssid>":
                try:
                    ip_info = self.adb.shell("ip addr show wlan0")
                    ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_info)
                    if ip_match:
                        ip_address = ip_match.group(1)
                        gateway = self._get_gateway()
                except RuntimeError:
                    pass

            return NetworkStatus(
                wifi_enabled=wifi_enabled,
                connected=ssid is not None and ssid != "<unknown ssid>",
                ssid=ssid if ssid and ssid != "<unknown ssid>" else None,
                ip_address=ip_address,
                gateway=gateway,
            )
        except RuntimeError as e:
            logger.warning(f"Failed to get network status: {e}")
            return NetworkStatus(False, False, None, None, None)

    def enable_wifi(self) -> None:
        """Enable WiFi."""
        self.adb.shell("svc wifi enable")
        time.sleep(2)
        logger.info("WiFi enabled")

    def disable_wifi(self) -> None:
        """Disable WiFi."""
        self.adb.shell("svc wifi disable")
        logger.info("WiFi disabled")

    def disable_mobile_data(self) -> None:
        """Disable mobile data."""
        try:
            self.adb.shell("svc data disable")
            logger.info("Mobile data disabled")
        except RuntimeError as e:
            logger.warning(f"Failed to disable mobile data: {e}")

    def connect_wifi(self, ssid: str, password: str, security: str = "WPA") -> bool:
        """Connect to WiFi network."""
        try:
            logger.info(f"Connecting to {ssid}...")
            self.adb.shell(
                f'cmd wifi connect-network "{ssid}" {security.lower()} "{password}"',
                timeout=15,
            )
            for _ in range(30):
                status = self.get_status()
                if status.connected and status.ssid == ssid:
                    logger.info(f"Connected to {ssid}")
                    return True
                time.sleep(1)
            return False
        except RuntimeError as e:
            logger.error(f"WiFi connection error: {e}")
            return False

    def ping(self, host: str, count: int = 3) -> bool:
        """Ping a host."""
        try:
            result = self.adb.shell(f"ping -c {count} -W 2 {host}", timeout=15)
            return f"{count} packets transmitted" in result
        except RuntimeError:
            return False

    def _get_gateway(self) -> Optional[str]:
        """Get default gateway."""
        try:
            result = self.adb.shell("ip route | grep default")
            match = re.search(r"via (\d+\.\d+\.\d+\.\d+)", result)
            return match.group(1) if match else None
        except RuntimeError:
            return None
