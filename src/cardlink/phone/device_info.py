"""Device Information retrieval and profiling.

This module provides the DeviceInfo class for querying comprehensive
device, SIM, and network information from Android devices.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from cardlink.phone.adb_client import ADBClient
from cardlink.phone.models import (
    DataConnectionState,
    DeviceProfile,
    FullProfile,
    NetworkProfile,
    NetworkType,
    SIMProfile,
    SIMStatus,
)

logger = logging.getLogger(__name__)


class DeviceInfo:
    """Retrieves and caches device information.

    This class provides methods for querying:
    - Device hardware/software info
    - SIM/UICC information
    - Network status and configuration
    - Complete device profiles

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.
        cache_ttl: Cache time-to-live in seconds (default 30).

    Example:
        ```python
        client = ADBClient()
        info = DeviceInfo(client, "device123")

        # Get device info
        device = await info.get_device_info()
        print(f"Model: {device.model}")

        # Get SIM info
        sims = await info.get_sim_info()
        for sim in sims:
            print(f"ICCID: {sim.iccid}")

        # Get full profile
        profile = await info.get_full_profile()
        print(profile.to_json())
        ```
    """

    # Property mappings for device info
    DEVICE_PROPS = {
        "model": "ro.product.model",
        "manufacturer": "ro.product.manufacturer",
        "brand": "ro.product.brand",
        "device": "ro.product.device",
        "product": "ro.product.name",
        "android_version": "ro.build.version.release",
        "api_level": "ro.build.version.sdk",
        "build_number": "ro.build.display.id",
        "build_fingerprint": "ro.build.fingerprint",
        "security_patch": "ro.build.version.security_patch",
        "hardware": "ro.hardware",
        "board": "ro.product.board",
    }

    # Network type mapping from Android constants
    NETWORK_TYPE_MAP = {
        "GPRS": NetworkType.GPRS,
        "EDGE": NetworkType.EDGE,
        "UMTS": NetworkType.UMTS,
        "CDMA": NetworkType.CDMA,
        "EVDO_0": NetworkType.EVDO_0,
        "EVDO_A": NetworkType.EVDO_A,
        "1xRTT": NetworkType.RTT,
        "HSDPA": NetworkType.HSDPA,
        "HSUPA": NetworkType.HSUPA,
        "HSPA": NetworkType.HSPA,
        "IDEN": NetworkType.IDEN,
        "EVDO_B": NetworkType.EVDO_B,
        "LTE": NetworkType.LTE,
        "EHRPD": NetworkType.EHRPD,
        "HSPAP": NetworkType.HSPAP,
        "GSM": NetworkType.GSM,
        "TD_SCDMA": NetworkType.TD_SCDMA,
        "IWLAN": NetworkType.IWLAN,
        "LTE_CA": NetworkType.LTE_CA,
        "NR": NetworkType.NR,
    }

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
        cache_ttl: float = 30.0,
    ):
        """Initialize device info retriever.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
            cache_ttl: Cache TTL in seconds.
        """
        self._client = adb_client
        self._serial = serial
        self._cache_ttl = cache_ttl

        # Caches
        self._device_cache: Optional[DeviceProfile] = None
        self._device_cache_time: float = 0
        self._sim_cache: Optional[List[SIMProfile]] = None
        self._sim_cache_time: float = 0
        self._network_cache: Optional[NetworkProfile] = None
        self._network_cache_time: float = 0

    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if cache is still valid."""
        import time

        return (time.time() - cache_time) < self._cache_ttl

    def invalidate_cache(self) -> None:
        """Invalidate all caches."""
        self._device_cache = None
        self._device_cache_time = 0
        self._sim_cache = None
        self._sim_cache_time = 0
        self._network_cache = None
        self._network_cache_time = 0

    async def get_device_info(self, refresh: bool = False) -> DeviceProfile:
        """Get device hardware and software information.

        Args:
            refresh: Force refresh, ignoring cache.

        Returns:
            DeviceProfile with device information.
        """
        import time

        if not refresh and self._device_cache and self._is_cache_valid(self._device_cache_time):
            return self._device_cache

        profile = DeviceProfile(serial=self._serial)

        # Get basic properties
        for attr, prop in self.DEVICE_PROPS.items():
            value = await self._client.get_property(self._serial, prop)
            if attr == "api_level":
                try:
                    setattr(profile, attr, int(value))
                except ValueError:
                    setattr(profile, attr, 0)
            else:
                setattr(profile, attr, value)

        # Get kernel version
        try:
            kernel = await self._client.shell("uname -r", self._serial, check_error=False)
            profile.kernel_version = kernel.strip()
        except Exception:
            pass

        # Get baseband version
        baseband = await self._client.get_property(self._serial, "gsm.version.baseband")
        profile.baseband_version = baseband

        # Get IMEI (requires TelephonyManager access)
        profile.imei, profile.imei2 = await self._get_imei()

        # Get ABI
        abi = await self._client.get_property(self._serial, "ro.product.cpu.abi")
        profile.abi = abi

        profile.timestamp = datetime.now()

        self._device_cache = profile
        self._device_cache_time = time.time()

        return profile

    async def _get_imei(self) -> Tuple[str, str]:
        """Get IMEI numbers (may require permissions).

        Returns:
            Tuple of (imei1, imei2).
        """
        imei1 = ""
        imei2 = ""

        # Try service call method
        try:
            # service call iphonesubinfo 1 (IMEI for slot 0)
            output = await self._client.shell(
                "service call iphonesubinfo 1",
                self._serial,
                check_error=False,
            )
            imei1 = self._parse_service_call_string(output)
        except Exception as e:
            logger.debug(f"Could not get IMEI via service call: {e}")

        # Try slot 2 for dual-SIM
        try:
            output = await self._client.shell(
                "service call iphonesubinfo 3",
                self._serial,
                check_error=False,
            )
            imei2 = self._parse_service_call_string(output)
        except Exception:
            pass

        # Try dumpsys as fallback
        if not imei1:
            try:
                output = await self._client.shell(
                    "dumpsys iphonesubinfo",
                    self._serial,
                    check_error=False,
                )
                match = re.search(r"Device ID = (\d+)", output)
                if match:
                    imei1 = match.group(1)
            except Exception:
                pass

        return imei1, imei2

    def _parse_service_call_string(self, output: str) -> str:
        """Parse string from service call result format.

        Android service call returns hex-encoded UTF-16 strings.
        """
        result = ""
        # Extract hex values from format like "Result: Parcel(00000000 00000010 '...')"
        hex_pattern = re.compile(r"'([^']+)'")
        matches = hex_pattern.findall(output)
        if matches:
            for match in matches:
                # Convert UTF-16 hex to string
                chars = match.replace(".", "").replace(" ", "")
                result += chars
        return result.strip()

    async def get_sim_info(self, refresh: bool = False) -> List[SIMProfile]:
        """Get SIM/UICC information for all slots.

        Args:
            refresh: Force refresh, ignoring cache.

        Returns:
            List of SIMProfile for each SIM slot.
        """
        import time

        if not refresh and self._sim_cache and self._is_cache_valid(self._sim_cache_time):
            return self._sim_cache

        profiles: List[SIMProfile] = []

        # Get number of SIM slots
        num_slots = await self._get_sim_slot_count()

        for slot in range(num_slots):
            profile = await self._get_slot_sim_info(slot)
            profiles.append(profile)

        self._sim_cache = profiles
        self._sim_cache_time = time.time()

        return profiles

    async def _get_sim_slot_count(self) -> int:
        """Get number of SIM slots on device."""
        # Try TelephonyManager slot count
        try:
            output = await self._client.shell(
                "dumpsys telephony.registry | grep 'mPhoneId'",
                self._serial,
                check_error=False,
            )
            # Count unique phone IDs
            ids = set(re.findall(r"mPhoneId=(\d+)", output))
            if ids:
                return max(int(i) for i in ids) + 1
        except Exception:
            pass

        # Check for dual SIM properties
        dual_sim = await self._client.get_property(
            self._serial,
            "persist.radio.multisim.config",
        )
        if "dsds" in dual_sim.lower() or "dsda" in dual_sim.lower():
            return 2

        return 1  # Default single SIM

    async def _get_slot_sim_info(self, slot: int) -> SIMProfile:
        """Get SIM info for a specific slot."""
        profile = SIMProfile(slot=slot)

        # Get SIM state
        state_prop = f"gsm.sim.state" if slot == 0 else f"gsm.sim.state.{slot}"
        state_str = await self._client.get_property(self._serial, state_prop)

        # Map state string to enum
        state_map = {
            "ABSENT": SIMStatus.ABSENT,
            "PIN_REQUIRED": SIMStatus.PIN_REQUIRED,
            "PUK_REQUIRED": SIMStatus.PUK_REQUIRED,
            "NETWORK_LOCKED": SIMStatus.NETWORK_LOCKED,
            "READY": SIMStatus.READY,
            "NOT_READY": SIMStatus.NOT_READY,
            "PERM_DISABLED": SIMStatus.PERM_DISABLED,
            "CARD_IO_ERROR": SIMStatus.CARD_IO_ERROR,
            "CARD_RESTRICTED": SIMStatus.CARD_RESTRICTED,
            "LOADED": SIMStatus.LOADED,
        }
        profile.status = state_map.get(state_str.upper(), SIMStatus.UNKNOWN)

        if profile.status in (SIMStatus.ABSENT, SIMStatus.UNKNOWN):
            return profile

        # Get operator info
        operator_prop = f"gsm.sim.operator.alpha" if slot == 0 else f"gsm.sim.operator.alpha.{slot}"
        profile.operator_name = await self._client.get_property(self._serial, operator_prop)

        # Get SPN
        spn_prop = f"gsm.sim.spn" if slot == 0 else f"gsm.sim.spn.{slot}"
        profile.spn = await self._client.get_property(self._serial, spn_prop)

        # Get MCC/MNC
        numeric_prop = f"gsm.sim.operator.numeric" if slot == 0 else f"gsm.sim.operator.numeric.{slot}"
        numeric = await self._client.get_property(self._serial, numeric_prop)
        if len(numeric) >= 5:
            profile.mcc = numeric[:3]
            profile.mnc = numeric[3:]

        # Try to get ICCID, IMSI via dumpsys
        await self._get_sim_identifiers(profile, slot)

        profile.is_active = slot == 0  # Assume slot 0 is active by default
        profile.timestamp = datetime.now()

        return profile

    async def _get_sim_identifiers(self, profile: SIMProfile, slot: int) -> None:
        """Get ICCID and IMSI for a SIM slot."""
        # Try dumpsys
        try:
            output = await self._client.shell(
                "dumpsys telephony.registry",
                self._serial,
                check_error=False,
            )

            # Parse ICCID
            iccid_pattern = rf"mSubscriptionId=\d+.*?iccId=([0-9A-Fa-f]+)"
            matches = re.findall(iccid_pattern, output, re.DOTALL)
            if len(matches) > slot:
                profile.iccid = matches[slot]

        except Exception as e:
            logger.debug(f"Could not get SIM identifiers via dumpsys: {e}")

        # Try service call for IMSI
        try:
            # Different method for different slots
            method = 7 if slot == 0 else 8
            output = await self._client.shell(
                f"service call iphonesubinfo {method}",
                self._serial,
                check_error=False,
            )
            imsi = self._parse_service_call_string(output)
            if imsi and imsi.isdigit():
                profile.imsi = imsi
        except Exception:
            pass

    async def get_network_info(self, refresh: bool = False) -> NetworkProfile:
        """Get current network status and configuration.

        Args:
            refresh: Force refresh, ignoring cache.

        Returns:
            NetworkProfile with network information.
        """
        import time

        if not refresh and self._network_cache and self._is_cache_valid(self._network_cache_time):
            return self._network_cache

        profile = NetworkProfile()

        # Get operator name
        profile.operator_name = await self._client.get_property(
            self._serial,
            "gsm.operator.alpha",
        )

        # Get network type
        network_type_str = await self._client.get_property(
            self._serial,
            "gsm.network.type",
        )
        profile.network_type = self.NETWORK_TYPE_MAP.get(
            network_type_str.upper(),
            NetworkType.UNKNOWN,
        )

        # Get MCC/MNC
        numeric = await self._client.get_property(self._serial, "gsm.operator.numeric")
        if len(numeric) >= 5:
            profile.mcc = numeric[:3]
            profile.mnc = numeric[3:]

        # Get data state
        await self._get_data_connection_info(profile)

        # Get WiFi info
        await self._get_wifi_info(profile)

        # Get APN info
        await self._get_apn_info(profile)

        # Get signal strength
        await self._get_signal_info(profile)

        profile.timestamp = datetime.now()

        self._network_cache = profile
        self._network_cache_time = time.time()

        return profile

    async def _get_data_connection_info(self, profile: NetworkProfile) -> None:
        """Get mobile data connection info."""
        try:
            output = await self._client.shell(
                "dumpsys telephony.registry | grep -E 'mDataConnectionState|mDataActivity'",
                self._serial,
                check_error=False,
            )

            # Parse data state
            state_match = re.search(r"mDataConnectionState=(\d+)", output)
            if state_match:
                state_code = int(state_match.group(1))
                state_map = {
                    0: DataConnectionState.DISCONNECTED,
                    1: DataConnectionState.CONNECTING,
                    2: DataConnectionState.CONNECTED,
                    3: DataConnectionState.SUSPENDED,
                }
                profile.data_state = state_map.get(state_code, DataConnectionState.UNKNOWN)

            # Get mobile IP
            ip_output = await self._client.shell(
                "ip addr show rmnet_data0 2>/dev/null | grep 'inet '",
                self._serial,
                check_error=False,
            )
            ip_match = re.search(r"inet ([\d.]+)", ip_output)
            if ip_match:
                profile.mobile_ip = ip_match.group(1)

        except Exception as e:
            logger.debug(f"Could not get data connection info: {e}")

    async def _get_wifi_info(self, profile: NetworkProfile) -> None:
        """Get WiFi connection info."""
        try:
            output = await self._client.shell(
                "dumpsys wifi | grep -E 'mNetworkInfo|Wi-Fi is'",
                self._serial,
                check_error=False,
            )

            # Check if WiFi is connected
            profile.is_wifi_connected = "CONNECTED" in output

            if profile.is_wifi_connected:
                # Get SSID
                ssid_match = re.search(r'extra: "([^"]+)"', output)
                if ssid_match:
                    profile.wifi_ssid = ssid_match.group(1)

                # Get WiFi IP
                ip_output = await self._client.shell(
                    "ip addr show wlan0 | grep 'inet '",
                    self._serial,
                    check_error=False,
                )
                ip_match = re.search(r"inet ([\d.]+)", ip_output)
                if ip_match:
                    profile.wifi_ip = ip_match.group(1)

        except Exception as e:
            logger.debug(f"Could not get WiFi info: {e}")

    async def _get_apn_info(self, profile: NetworkProfile) -> None:
        """Get APN configuration info."""
        try:
            # Query content provider for current APN
            output = await self._client.shell(
                "content query --uri content://telephony/carriers/preferapn",
                self._serial,
                check_error=False,
            )

            # Parse APN name
            name_match = re.search(r"name=([^,]+)", output)
            if name_match:
                profile.apn_name = name_match.group(1)

            type_match = re.search(r"type=([^,]+)", output)
            if type_match:
                profile.apn_type = type_match.group(1)

        except Exception as e:
            logger.debug(f"Could not get APN info: {e}")

    async def _get_signal_info(self, profile: NetworkProfile) -> None:
        """Get signal strength information."""
        try:
            output = await self._client.shell(
                "dumpsys telephony.registry | grep -E 'mSignalStrength'",
                self._serial,
                check_error=False,
            )

            # Parse signal level (0-4)
            level_match = re.search(r"level=(\d+)", output)
            if level_match:
                profile.signal_level = int(level_match.group(1))

            # Parse dBm
            dbm_match = re.search(r"rsrp=(-?\d+)", output)  # LTE RSRP
            if dbm_match:
                profile.signal_strength_dbm = int(dbm_match.group(1))
            else:
                dbm_match = re.search(r"signalStrength=(\d+)", output)  # GSM
                if dbm_match:
                    # Convert ASU to dBm
                    asu = int(dbm_match.group(1))
                    profile.signal_strength_dbm = 2 * asu - 113 if asu < 99 else -999

        except Exception as e:
            logger.debug(f"Could not get signal info: {e}")

    async def get_full_profile(self, refresh: bool = False) -> FullProfile:
        """Get complete device profile with all information.

        Args:
            refresh: Force refresh all data.

        Returns:
            FullProfile containing device, SIM, and network info.
        """
        device = await self.get_device_info(refresh)
        sims = await self.get_sim_info(refresh)
        network = await self.get_network_info(refresh)

        return FullProfile(
            device=device,
            sim_profiles=sims,
            network=network,
            timestamp=datetime.now(),
        )

    def export_json(self, profile: FullProfile) -> str:
        """Export profile to JSON string.

        Args:
            profile: Profile to export.

        Returns:
            JSON string representation.
        """
        return profile.to_json()

    @staticmethod
    def compare(profile1: FullProfile, profile2: FullProfile) -> Dict[str, Any]:
        """Compare two profiles and return differences.

        Args:
            profile1: First profile.
            profile2: Second profile.

        Returns:
            Dictionary of differences by category.
        """
        differences: Dict[str, Any] = {
            "device": {},
            "sim": [],
            "network": {},
        }

        # Compare device info
        d1, d2 = profile1.device.to_dict(), profile2.device.to_dict()
        for key in d1:
            if key != "timestamp" and d1.get(key) != d2.get(key):
                differences["device"][key] = {
                    "old": d1.get(key),
                    "new": d2.get(key),
                }

        # Compare SIM info
        for i, (s1, s2) in enumerate(
            zip(profile1.sim_profiles, profile2.sim_profiles)
        ):
            s1_dict, s2_dict = s1.to_dict(), s2.to_dict()
            slot_diff = {}
            for key in s1_dict:
                if key != "timestamp" and s1_dict.get(key) != s2_dict.get(key):
                    slot_diff[key] = {
                        "old": s1_dict.get(key),
                        "new": s2_dict.get(key),
                    }
            if slot_diff:
                differences["sim"].append({"slot": i, "changes": slot_diff})

        # Compare network info
        if profile1.network and profile2.network:
            n1, n2 = profile1.network.to_dict(), profile2.network.to_dict()
            for key in n1:
                if key != "timestamp" and n1.get(key) != n2.get(key):
                    differences["network"][key] = {
                        "old": n1.get(key),
                        "new": n2.get(key),
                    }

        return differences
