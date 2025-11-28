"""Network Manager for Android device network configuration.

This module provides the NetworkManager class for controlling WiFi,
mobile data, and APN settings on Android devices.
"""

import logging
import re
from typing import Optional

from gp_ota_tester.phone.adb_client import ADBClient
from gp_ota_tester.phone.exceptions import NetworkConfigError
from gp_ota_tester.phone.models import APNConfig

logger = logging.getLogger(__name__)


class NetworkManager:
    """Manages network settings on Android devices.

    This class provides methods for:
    - WiFi enable/disable and connection
    - Mobile data enable/disable
    - APN configuration
    - Connectivity testing

    Note:
        Some operations may require root access or system app permissions.
        The availability of certain features depends on Android version
        and device manufacturer.

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.

    Example:
        ```python
        client = ADBClient()
        network = NetworkManager(client, "device123")

        # Control WiFi
        await network.enable_wifi()
        await network.connect_wifi("MyNetwork", "password123")

        # Control mobile data
        await network.enable_mobile_data()

        # Configure APN
        apn = APNConfig(name="Test", apn="test.apn")
        await network.set_apn(apn)

        # Test connectivity
        if await network.test_connectivity("https://example.com"):
            print("Connected!")
        ```
    """

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
    ):
        """Initialize network manager.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
        """
        self._client = adb_client
        self._serial = serial

    # =========================================================================
    # WiFi Control
    # =========================================================================

    async def enable_wifi(self) -> bool:
        """Enable WiFi on the device.

        Returns:
            True if WiFi was enabled successfully.
        """
        try:
            # Try svc command first (works on most Android versions)
            output = await self._client.shell(
                "svc wifi enable",
                self._serial,
                check_error=False,
            )

            # Check if enabled
            if await self.is_wifi_enabled():
                return True

            # Try cmd command for newer Android
            await self._client.shell(
                "cmd wifi set-wifi-enabled enabled",
                self._serial,
                check_error=False,
            )

            return await self.is_wifi_enabled()

        except Exception as e:
            logger.error(f"Failed to enable WiFi: {e}")
            return False

    async def disable_wifi(self) -> bool:
        """Disable WiFi on the device.

        Returns:
            True if WiFi was disabled successfully.
        """
        try:
            await self._client.shell(
                "svc wifi disable",
                self._serial,
                check_error=False,
            )

            if not await self.is_wifi_enabled():
                return True

            await self._client.shell(
                "cmd wifi set-wifi-enabled disabled",
                self._serial,
                check_error=False,
            )

            return not await self.is_wifi_enabled()

        except Exception as e:
            logger.error(f"Failed to disable WiFi: {e}")
            return False

    async def is_wifi_enabled(self) -> bool:
        """Check if WiFi is enabled.

        Returns:
            True if WiFi is enabled.
        """
        try:
            output = await self._client.shell(
                "dumpsys wifi | grep 'Wi-Fi is'",
                self._serial,
                check_error=False,
            )
            return "enabled" in output.lower()
        except Exception:
            return False

    async def is_wifi_connected(self) -> bool:
        """Check if WiFi is connected to a network.

        Returns:
            True if connected to WiFi.
        """
        try:
            output = await self._client.shell(
                "dumpsys wifi | grep 'mNetworkInfo'",
                self._serial,
                check_error=False,
            )
            return "CONNECTED" in output
        except Exception:
            return False

    async def get_wifi_ssid(self) -> str:
        """Get current WiFi SSID.

        Returns:
            Connected SSID or empty string.
        """
        try:
            output = await self._client.shell(
                "dumpsys wifi | grep 'mNetworkInfo'",
                self._serial,
                check_error=False,
            )
            match = re.search(r'extra: "([^"]+)"', output)
            if match:
                return match.group(1)
        except Exception:
            pass
        return ""

    async def connect_wifi(
        self,
        ssid: str,
        password: Optional[str] = None,
        security: str = "WPA",
    ) -> bool:
        """Connect to a WiFi network.

        Args:
            ssid: Network SSID.
            password: Network password (None for open networks).
            security: Security type (OPEN, WEP, WPA, WPA2).

        Returns:
            True if connection successful.

        Note:
            This method may not work on all devices without root
            or system app permissions.
        """
        try:
            # Try using cmd wifi on Android 10+
            if password:
                cmd = f'cmd wifi connect-network "{ssid}" {security.lower()} "{password}"'
            else:
                cmd = f'cmd wifi connect-network "{ssid}" open'

            output = await self._client.shell(cmd, self._serial, check_error=False)

            if "error" not in output.lower():
                # Wait for connection
                import asyncio

                for _ in range(10):
                    await asyncio.sleep(1)
                    if await self.is_wifi_connected():
                        current_ssid = await self.get_wifi_ssid()
                        if current_ssid == ssid:
                            return True

            # Try alternative method using wpa_supplicant
            # This requires root
            await self._connect_wifi_via_wpa(ssid, password, security)

            return await self.is_wifi_connected()

        except Exception as e:
            logger.error(f"Failed to connect to WiFi: {e}")
            return False

    async def _connect_wifi_via_wpa(
        self,
        ssid: str,
        password: Optional[str],
        security: str,
    ) -> None:
        """Connect via wpa_supplicant (requires root)."""
        try:
            if await self._client.is_root(self._serial):
                config = f'''
network={{
    ssid="{ssid}"
    key_mgmt={security.upper() if security != "OPEN" else "NONE"}
    {"psk=\"" + password + "\"" if password else ""}
}}
'''
                # Write to wpa_supplicant config
                await self._client.shell(
                    f'echo \'{config}\' >> /data/misc/wifi/wpa_supplicant.conf',
                    self._serial,
                    check_error=False,
                )
                # Reload wpa_supplicant
                await self._client.shell(
                    "wpa_cli reconfigure",
                    self._serial,
                    check_error=False,
                )
        except Exception:
            pass

    async def disconnect_wifi(self) -> bool:
        """Disconnect from current WiFi network.

        Returns:
            True if disconnected.
        """
        try:
            await self._client.shell(
                "cmd wifi forget-network all",
                self._serial,
                check_error=False,
            )
            return not await self.is_wifi_connected()
        except Exception:
            return False

    async def scan_wifi(self) -> list:
        """Scan for available WiFi networks.

        Returns:
            List of detected SSIDs.
        """
        try:
            output = await self._client.shell(
                "cmd wifi list-scan-results",
                self._serial,
                check_error=False,
            )

            ssids = []
            for line in output.split("\n"):
                parts = line.split()
                if len(parts) >= 5:
                    ssid = parts[4] if len(parts) > 4 else ""
                    if ssid and ssid not in ssids:
                        ssids.append(ssid)
            return ssids
        except Exception:
            return []

    # =========================================================================
    # Mobile Data Control
    # =========================================================================

    async def enable_mobile_data(self) -> bool:
        """Enable mobile data.

        Returns:
            True if mobile data was enabled.
        """
        try:
            await self._client.shell(
                "svc data enable",
                self._serial,
                check_error=False,
            )
            return await self.is_mobile_data_enabled()
        except Exception as e:
            logger.error(f"Failed to enable mobile data: {e}")
            return False

    async def disable_mobile_data(self) -> bool:
        """Disable mobile data.

        Returns:
            True if mobile data was disabled.
        """
        try:
            await self._client.shell(
                "svc data disable",
                self._serial,
                check_error=False,
            )
            return not await self.is_mobile_data_enabled()
        except Exception as e:
            logger.error(f"Failed to disable mobile data: {e}")
            return False

    async def is_mobile_data_enabled(self) -> bool:
        """Check if mobile data is enabled.

        Returns:
            True if mobile data is enabled.
        """
        try:
            output = await self._client.shell(
                "settings get global mobile_data",
                self._serial,
                check_error=False,
            )
            return output.strip() == "1"
        except Exception:
            return False

    async def is_mobile_data_connected(self) -> bool:
        """Check if mobile data is connected.

        Returns:
            True if connected via mobile data.
        """
        try:
            output = await self._client.shell(
                "dumpsys telephony.registry | grep mDataConnectionState",
                self._serial,
                check_error=False,
            )
            return "=2" in output  # 2 = DATA_CONNECTED
        except Exception:
            return False

    # =========================================================================
    # APN Configuration
    # =========================================================================

    async def set_apn(self, config: APNConfig) -> bool:
        """Configure APN settings.

        Args:
            config: APN configuration.

        Returns:
            True if APN was configured successfully.

        Note:
            APN configuration may be restricted by carrier settings.
        """
        try:
            # Build content values
            values = [
                f'--bind name:s:"{config.name}"',
                f'--bind apn:s:"{config.apn}"',
                f'--bind type:s:"{config.type}"',
                f'--bind protocol:s:"{config.protocol}"',
                f'--bind roaming_protocol:s:"{config.roaming_protocol}"',
            ]

            if config.mcc:
                values.append(f'--bind mcc:s:"{config.mcc}"')
            if config.mnc:
                values.append(f'--bind mnc:s:"{config.mnc}"')
            if config.user:
                values.append(f'--bind user:s:"{config.user}"')
            if config.password:
                values.append(f'--bind password:s:"{config.password}"')
            if config.auth_type:
                values.append(f'--bind authtype:i:{config.auth_type}')
            if config.proxy:
                values.append(f'--bind proxy:s:"{config.proxy}"')
            if config.port:
                values.append(f'--bind port:s:"{config.port}"')

            # Insert APN
            cmd = f"content insert --uri content://telephony/carriers {' '.join(values)}"
            output = await self._client.shell(cmd, self._serial, check_error=False)

            if "Row:" in output:
                # Get the inserted APN ID
                match = re.search(r"Row:\s*(\d+)", output)
                if match:
                    apn_id = match.group(1)
                    # Set as preferred APN
                    await self._client.shell(
                        f"content insert --uri content://telephony/carriers/preferapn --bind apn_id:i:{apn_id}",
                        self._serial,
                        check_error=False,
                    )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to set APN: {e}")
            raise NetworkConfigError(str(e), "set_apn")

    async def get_current_apn(self) -> Optional[APNConfig]:
        """Get current APN configuration.

        Returns:
            APNConfig or None if not available.
        """
        try:
            output = await self._client.shell(
                "content query --uri content://telephony/carriers/preferapn",
                self._serial,
                check_error=False,
            )

            if not output or "No result" in output:
                return None

            # Parse output
            config = APNConfig(name="", apn="")

            name_match = re.search(r"name=([^,]+)", output)
            if name_match:
                config.name = name_match.group(1)

            apn_match = re.search(r"apn=([^,]+)", output)
            if apn_match:
                config.apn = apn_match.group(1)

            type_match = re.search(r"type=([^,]+)", output)
            if type_match:
                config.type = type_match.group(1)

            user_match = re.search(r"user=([^,]+)", output)
            if user_match:
                config.user = user_match.group(1)

            return config

        except Exception as e:
            logger.error(f"Failed to get APN: {e}")
            return None

    async def list_apns(self) -> list:
        """List all configured APNs.

        Returns:
            List of APN names.
        """
        try:
            output = await self._client.shell(
                "content query --uri content://telephony/carriers --projection name,apn",
                self._serial,
                check_error=False,
            )

            apns = []
            for line in output.split("\n"):
                name_match = re.search(r"name=([^,]+)", line)
                if name_match:
                    apns.append(name_match.group(1))
            return apns

        except Exception:
            return []

    async def delete_apn(self, name: str) -> bool:
        """Delete an APN by name.

        Args:
            name: APN name to delete.

        Returns:
            True if deleted.
        """
        try:
            output = await self._client.shell(
                f'content delete --uri content://telephony/carriers --where "name=\'{name}\'"',
                self._serial,
                check_error=False,
            )
            return "deleted" in output.lower()
        except Exception:
            return False

    # =========================================================================
    # Connectivity Testing
    # =========================================================================

    async def test_connectivity(
        self,
        url: str = "https://www.google.com",
        timeout: int = 10,
    ) -> bool:
        """Test network connectivity by fetching a URL.

        Args:
            url: URL to fetch.
            timeout: Request timeout in seconds.

        Returns:
            True if URL was reachable.
        """
        try:
            # Try curl first
            output, exit_code = await self._client.shell_with_exit_code(
                f'curl -s -o /dev/null -w "%{{http_code}}" --connect-timeout {timeout} "{url}"',
                self._serial,
                timeout=timeout + 5,
            )

            if exit_code == 0 and output.strip().startswith(("2", "3")):
                return True

            # Try wget as fallback
            output, exit_code = await self._client.shell_with_exit_code(
                f'wget -q -O /dev/null --timeout={timeout} "{url}"',
                self._serial,
                timeout=timeout + 5,
            )

            return exit_code == 0

        except Exception as e:
            logger.debug(f"Connectivity test failed: {e}")
            return False

    async def ping(
        self,
        host: str,
        count: int = 3,
        timeout: int = 5,
    ) -> Optional[float]:
        """Ping a host.

        Args:
            host: Host to ping.
            count: Number of ping packets.
            timeout: Ping timeout.

        Returns:
            Average latency in ms, or None if ping failed.
        """
        try:
            output = await self._client.shell(
                f"ping -c {count} -W {timeout} {host}",
                self._serial,
                timeout=timeout * count + 5,
                check_error=False,
            )

            # Parse average latency
            match = re.search(r"avg[^=]*=\s*[\d.]+/([\d.]+)", output)
            if match:
                return float(match.group(1))

            # Try alternative format
            match = re.search(r"time[=<]([\d.]+)\s*ms", output)
            if match:
                return float(match.group(1))

        except Exception as e:
            logger.debug(f"Ping failed: {e}")

        return None

    async def get_ip_address(self) -> Optional[str]:
        """Get device's current IP address.

        Returns:
            IP address string or None.
        """
        # Try WiFi interface first
        try:
            output = await self._client.shell(
                "ip addr show wlan0 | grep 'inet '",
                self._serial,
                check_error=False,
            )
            match = re.search(r"inet ([\d.]+)", output)
            if match:
                return match.group(1)
        except Exception:
            pass

        # Try mobile data interface
        try:
            for iface in ["rmnet_data0", "rmnet0", "ccmni0"]:
                output = await self._client.shell(
                    f"ip addr show {iface} | grep 'inet '",
                    self._serial,
                    check_error=False,
                )
                match = re.search(r"inet ([\d.]+)", output)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None

    # =========================================================================
    # Airplane Mode
    # =========================================================================

    async def enable_airplane_mode(self) -> bool:
        """Enable airplane mode.

        Returns:
            True if airplane mode was enabled.
        """
        try:
            await self._client.shell(
                "settings put global airplane_mode_on 1",
                self._serial,
                check_error=False,
            )
            await self._client.shell(
                'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true',
                self._serial,
                check_error=False,
            )
            return await self.is_airplane_mode_enabled()
        except Exception:
            return False

    async def disable_airplane_mode(self) -> bool:
        """Disable airplane mode.

        Returns:
            True if airplane mode was disabled.
        """
        try:
            await self._client.shell(
                "settings put global airplane_mode_on 0",
                self._serial,
                check_error=False,
            )
            await self._client.shell(
                'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false',
                self._serial,
                check_error=False,
            )
            return not await self.is_airplane_mode_enabled()
        except Exception:
            return False

    async def is_airplane_mode_enabled(self) -> bool:
        """Check if airplane mode is enabled.

        Returns:
            True if airplane mode is on.
        """
        try:
            output = await self._client.shell(
                "settings get global airplane_mode_on",
                self._serial,
                check_error=False,
            )
            return output.strip() == "1"
        except Exception:
            return False
