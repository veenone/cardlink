"""Modem Information and Profiling for Modem Controller.

This module provides comprehensive modem, SIM, and network
information retrieval with caching support.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from gp_ota_tester.modem.at_interface import ATInterface
from gp_ota_tester.modem.exceptions import ATCommandError, ATTimeoutError
from gp_ota_tester.modem.models import (
    FullModemProfile,
    ModemProfile,
    ModemVendor,
    NetworkProfile,
    NetworkType,
    RegistrationStatus,
    SIMProfile,
    SIMStatus,
)

logger = logging.getLogger(__name__)

# Cache TTL
DEFAULT_CACHE_TTL = 60.0  # seconds

# AT Commands for information retrieval
MODEM_INFO_COMMANDS = {
    "manufacturer": "AT+CGMI",
    "model": "AT+CGMM",
    "firmware": "AT+CGMR",
    "imei": "AT+CGSN",
}

SIM_INFO_COMMANDS = {
    "status": "AT+CPIN?",
    "iccid": "AT+QCCID",  # Quectel specific
    "iccid_alt": "AT+CCID",  # Standard
    "imsi": "AT+CIMI",
    "msisdn": "AT+CNUM",
}

NETWORK_INFO_COMMANDS = {
    "registration": "AT+CREG?",
    "eps_registration": "AT+CEREG?",
    "operator": "AT+COPS?",
    "signal_csq": "AT+CSQ",
    "signal_qcsq": "AT+QCSQ",  # Quectel detailed
    "pdp_context": "AT+CGDCONT?",
    "ip_address": "AT+CGPADDR",
}

# Response parsing patterns
CREG_PATTERN = re.compile(r"\+CREG:\s*(\d+),(\d+)(?:,\"([0-9A-Fa-f]+)\",\"([0-9A-Fa-f]+)\")?")
CEREG_PATTERN = re.compile(r"\+CEREG:\s*(\d+),(\d+)(?:,\"([0-9A-Fa-f]+)\",\"([0-9A-Fa-f]+)\"(?:,(\d+))?)?")
COPS_PATTERN = re.compile(r'\+COPS:\s*(\d+)(?:,(\d+),"([^"]*)"(?:,(\d+))?)?')
CSQ_PATTERN = re.compile(r"\+CSQ:\s*(\d+),(\d+)")
QCSQ_PATTERN = re.compile(r'\+QCSQ:\s*"([^"]+)",(-?\d+)(?:,(-?\d+))?(?:,(-?\d+))?(?:,(-?\d+))?')
CPIN_PATTERN = re.compile(r"\+CPIN:\s*(.+)")
QCCID_PATTERN = re.compile(r"\+QCCID:\s*(\d+)")
CCID_PATTERN = re.compile(r"(\d{18,20})")  # ICCID is 18-20 digits
CNUM_PATTERN = re.compile(r'\+CNUM:\s*"[^"]*","(\+?\d+)"')
CGDCONT_PATTERN = re.compile(r'\+CGDCONT:\s*(\d+),"([^"]*)","([^"]*)"')
CGPADDR_PATTERN = re.compile(r"\+CGPADDR:\s*(\d+),\"?([^\"]+)\"?")


class ModemInfoRetriever:
    """Retrieves and caches modem, SIM, and network information.

    Provides methods to query comprehensive modem information
    via AT commands with caching support.

    Example:
        >>> info = ModemInfoRetriever(at_interface)
        >>>
        >>> # Get modem info
        >>> modem = await info.get_modem_info()
        >>> print(f"{modem.manufacturer} {modem.model}")
        >>>
        >>> # Get SIM info
        >>> sim = await info.get_sim_info()
        >>> print(f"ICCID: {sim.iccid}")
        >>>
        >>> # Get full profile
        >>> profile = await info.get_full_profile()
        >>> print(profile.to_json())
    """

    def __init__(
        self,
        at_interface: ATInterface,
        cache_ttl: float = DEFAULT_CACHE_TTL,
    ):
        """Initialize info retriever.

        Args:
            at_interface: AT interface for commands.
            cache_ttl: Cache time-to-live in seconds.
        """
        self.at = at_interface
        self.cache_ttl = cache_ttl

        # Cached profiles
        self._modem_profile: Optional[ModemProfile] = None
        self._modem_profile_time: Optional[datetime] = None

        self._sim_profile: Optional[SIMProfile] = None
        self._sim_profile_time: Optional[datetime] = None

        self._network_profile: Optional[NetworkProfile] = None
        self._network_profile_time: Optional[datetime] = None

    def _is_cache_valid(self, cache_time: Optional[datetime]) -> bool:
        """Check if cached value is still valid."""
        if cache_time is None:
            return False
        age = datetime.now() - cache_time
        return age.total_seconds() < self.cache_ttl

    async def get_modem_info(self, force_refresh: bool = False) -> ModemProfile:
        """Get modem hardware/firmware information.

        Args:
            force_refresh: Force refresh even if cached.

        Returns:
            ModemProfile with modem information.
        """
        if not force_refresh and self._is_cache_valid(self._modem_profile_time):
            return self._modem_profile

        profile = ModemProfile()

        # Manufacturer
        try:
            response = await self.at.send_command("AT+CGMI", check_error=False)
            if response.success and response.data:
                profile.manufacturer = self._clean_response(response.data[0])
        except (ATCommandError, ATTimeoutError):
            pass

        # Model
        try:
            response = await self.at.send_command("AT+CGMM", check_error=False)
            if response.success and response.data:
                profile.model = self._clean_response(response.data[0])
        except (ATCommandError, ATTimeoutError):
            pass

        # Firmware version
        try:
            response = await self.at.send_command("AT+CGMR", check_error=False)
            if response.success and response.data:
                profile.firmware_version = self._clean_response(response.data[0])
        except (ATCommandError, ATTimeoutError):
            pass

        # IMEI
        try:
            response = await self.at.send_command("AT+CGSN", check_error=False)
            if response.success and response.data:
                profile.imei = self._clean_response(response.data[0])
        except (ATCommandError, ATTimeoutError):
            pass

        # Detect vendor
        profile.vendor = self._detect_vendor(profile.manufacturer)

        # Cache
        self._modem_profile = profile
        self._modem_profile_time = datetime.now()

        return profile

    async def get_sim_info(self, force_refresh: bool = False) -> SIMProfile:
        """Get UICC/SIM card information.

        Args:
            force_refresh: Force refresh even if cached.

        Returns:
            SIMProfile with SIM information.
        """
        if not force_refresh and self._is_cache_valid(self._sim_profile_time):
            return self._sim_profile

        profile = SIMProfile()

        # SIM status
        try:
            response = await self.at.send_command("AT+CPIN?", check_error=False)
            if response.success:
                profile.status = self._parse_sim_status(response.raw_response)
        except (ATCommandError, ATTimeoutError):
            profile.status = SIMStatus.ERROR

        # Only continue if SIM is ready
        if profile.status != SIMStatus.READY:
            self._sim_profile = profile
            self._sim_profile_time = datetime.now()
            return profile

        # ICCID - try Quectel command first
        try:
            response = await self.at.send_command("AT+QCCID", check_error=False)
            if response.success:
                profile.iccid = self._parse_iccid(response.raw_response)
        except (ATCommandError, ATTimeoutError):
            pass

        # ICCID - try standard command if Quectel failed
        if not profile.iccid:
            try:
                response = await self.at.send_command("AT+CCID", check_error=False)
                if response.success and response.data:
                    profile.iccid = self._parse_iccid(response.raw_response)
            except (ATCommandError, ATTimeoutError):
                pass

        # IMSI
        try:
            response = await self.at.send_command("AT+CIMI", check_error=False)
            if response.success and response.data:
                imsi = self._clean_response(response.data[0])
                if imsi.isdigit():
                    profile.imsi = imsi
                    # Extract MCC/MNC from IMSI
                    if len(imsi) >= 5:
                        profile.mcc = imsi[:3]
                        profile.mnc = imsi[3:5]  # Could be 2 or 3 digits
        except (ATCommandError, ATTimeoutError):
            pass

        # MSISDN (phone number)
        try:
            response = await self.at.send_command("AT+CNUM", check_error=False)
            if response.success:
                profile.msisdn = self._parse_msisdn(response.raw_response)
        except (ATCommandError, ATTimeoutError):
            pass

        # Cache
        self._sim_profile = profile
        self._sim_profile_time = datetime.now()

        return profile

    async def get_network_info(self, force_refresh: bool = False) -> NetworkProfile:
        """Get network registration and signal information.

        Args:
            force_refresh: Force refresh even if cached.

        Returns:
            NetworkProfile with network information.
        """
        if not force_refresh and self._is_cache_valid(self._network_profile_time):
            return self._network_profile

        profile = NetworkProfile()

        # CS registration status
        try:
            response = await self.at.send_command("AT+CREG?", check_error=False)
            if response.success:
                self._parse_creg(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # EPS registration status
        try:
            response = await self.at.send_command("AT+CEREG?", check_error=False)
            if response.success:
                self._parse_cereg(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # Operator
        try:
            response = await self.at.send_command("AT+COPS?", check_error=False)
            if response.success:
                self._parse_cops(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # Signal strength - try detailed first
        signal_parsed = False
        try:
            response = await self.at.send_command("AT+QCSQ", check_error=False)
            if response.success:
                signal_parsed = self._parse_qcsq(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # Fallback to CSQ
        if not signal_parsed:
            try:
                response = await self.at.send_command("AT+CSQ", check_error=False)
                if response.success:
                    self._parse_csq(response.raw_response, profile)
            except (ATCommandError, ATTimeoutError):
                pass

        # APN from PDP context
        try:
            response = await self.at.send_command("AT+CGDCONT?", check_error=False)
            if response.success:
                self._parse_cgdcont(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # IP address
        try:
            response = await self.at.send_command("AT+CGPADDR", check_error=False)
            if response.success:
                self._parse_cgpaddr(response.raw_response, profile)
        except (ATCommandError, ATTimeoutError):
            pass

        # Cache
        self._network_profile = profile
        self._network_profile_time = datetime.now()

        return profile

    async def get_full_profile(self, force_refresh: bool = False) -> FullModemProfile:
        """Get complete modem profile.

        Args:
            force_refresh: Force refresh all data.

        Returns:
            FullModemProfile with all information.
        """
        # Gather all profiles concurrently
        modem, sim, network = await asyncio.gather(
            self.get_modem_info(force_refresh),
            self.get_sim_info(force_refresh),
            self.get_network_info(force_refresh),
        )

        return FullModemProfile(
            modem=modem,
            sim=sim,
            network=network,
            timestamp=datetime.now(),
        )

    async def refresh(self) -> None:
        """Force refresh all cached information."""
        await self.get_full_profile(force_refresh=True)

    def invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self._modem_profile = None
        self._modem_profile_time = None
        self._sim_profile = None
        self._sim_profile_time = None
        self._network_profile = None
        self._network_profile_time = None

    def export_json(self) -> str:
        """Export current cached profile as JSON.

        Returns:
            JSON string with profile data.
        """
        data = {
            "modem": self._modem_profile.to_dict() if self._modem_profile else {},
            "sim": self._sim_profile.to_dict() if self._sim_profile else {},
            "network": self._network_profile.to_dict() if self._network_profile else {},
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2)

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def _clean_response(self, value: str) -> str:
        """Clean response value."""
        return value.strip().strip('"')

    def _detect_vendor(self, manufacturer: str) -> ModemVendor:
        """Detect vendor from manufacturer string."""
        manufacturer = manufacturer.lower()

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

    def _parse_sim_status(self, response: str) -> SIMStatus:
        """Parse SIM status from +CPIN response."""
        match = CPIN_PATTERN.search(response)
        if not match:
            return SIMStatus.ERROR

        status_str = match.group(1).strip()
        status_map = {
            "READY": SIMStatus.READY,
            "SIM PIN": SIMStatus.SIM_PIN,
            "SIM PUK": SIMStatus.SIM_PUK,
            "SIM PIN2": SIMStatus.SIM_PIN2,
            "SIM PUK2": SIMStatus.SIM_PUK2,
            "PH-SIM PIN": SIMStatus.PH_SIM_PIN,
            "PH-NET PIN": SIMStatus.PH_NET_PIN,
            "PH-NET PUK": SIMStatus.PH_NET_PUK,
            "NOT INSERTED": SIMStatus.NOT_INSERTED,
            "NOT READY": SIMStatus.NOT_READY,
        }
        return status_map.get(status_str, SIMStatus.ERROR)

    def _parse_iccid(self, response: str) -> Optional[str]:
        """Parse ICCID from response."""
        # Try Quectel format first
        match = QCCID_PATTERN.search(response)
        if match:
            return match.group(1)

        # Try generic ICCID pattern
        match = CCID_PATTERN.search(response)
        if match:
            return match.group(1)

        return None

    def _parse_msisdn(self, response: str) -> Optional[str]:
        """Parse MSISDN from +CNUM response."""
        match = CNUM_PATTERN.search(response)
        if match:
            return match.group(1)
        return None

    def _parse_creg(self, response: str, profile: NetworkProfile) -> None:
        """Parse +CREG response into profile."""
        match = CREG_PATTERN.search(response)
        if not match:
            return

        mode = int(match.group(1))
        stat = int(match.group(2))
        lac = match.group(3)
        ci = match.group(4)

        try:
            profile.registration_status = RegistrationStatus(stat)
        except ValueError:
            profile.registration_status = RegistrationStatus.UNKNOWN

        if lac:
            profile.lac = lac
        if ci:
            profile.cell_id = ci

    def _parse_cereg(self, response: str, profile: NetworkProfile) -> None:
        """Parse +CEREG response into profile."""
        match = CEREG_PATTERN.search(response)
        if not match:
            return

        mode = int(match.group(1))
        stat = int(match.group(2))
        tac = match.group(3)
        ci = match.group(4)
        act = match.group(5)

        try:
            profile.eps_registration_status = RegistrationStatus(stat)
        except ValueError:
            profile.eps_registration_status = RegistrationStatus.UNKNOWN

        if tac:
            profile.tac = tac
        if ci:
            profile.cell_id = ci
        if act:
            profile.network_type = self._access_technology(int(act))

    def _parse_cops(self, response: str, profile: NetworkProfile) -> None:
        """Parse +COPS response into profile."""
        match = COPS_PATTERN.search(response)
        if not match:
            return

        mode = int(match.group(1))
        format_type = match.group(2)
        operator = match.group(3)
        act = match.group(4)

        if operator:
            # Check if numeric or alphanumeric
            if format_type == "2" and operator.isdigit():
                profile.operator_numeric = operator
            else:
                profile.operator_name = operator

        if act:
            profile.network_type = self._access_technology(int(act))

    def _parse_csq(self, response: str, profile: NetworkProfile) -> None:
        """Parse +CSQ response into profile."""
        match = CSQ_PATTERN.search(response)
        if not match:
            return

        rssi_raw = int(match.group(1))
        ber = int(match.group(2))

        # Convert to dBm
        if rssi_raw == 99:
            profile.rssi = None
        elif rssi_raw == 0:
            profile.rssi = -113
        elif rssi_raw == 31:
            profile.rssi = -51
        else:
            profile.rssi = -113 + (rssi_raw * 2)

    def _parse_qcsq(self, response: str, profile: NetworkProfile) -> bool:
        """Parse +QCSQ response into profile.

        Returns True if successfully parsed.
        """
        match = QCSQ_PATTERN.search(response)
        if not match:
            return False

        net_type = match.group(1)
        param1 = int(match.group(2)) if match.group(2) else None
        param2 = int(match.group(3)) if match.group(3) else None
        param3 = int(match.group(4)) if match.group(4) else None
        param4 = int(match.group(5)) if match.group(5) else None

        # Set network type
        net_type_map = {
            "GSM": NetworkType.GSM,
            "WCDMA": NetworkType.UMTS,
            "LTE": NetworkType.LTE,
            "CAT-M1": NetworkType.LTE,
            "CAT-NB1": NetworkType.LTE,
            "NR5G-NSA": NetworkType.NR5G_NSA,
            "NR5G-SA": NetworkType.NR5G_SA,
        }
        profile.network_type = net_type_map.get(net_type, NetworkType.UNKNOWN)

        # Parse parameters based on network type
        if net_type == "GSM":
            profile.rssi = param1
        elif net_type in ("WCDMA", "LTE", "CAT-M1", "CAT-NB1"):
            profile.rssi = param1
            profile.rsrp = param2
            profile.sinr = param3
            profile.rsrq = param4
        elif net_type in ("NR5G-NSA", "NR5G-SA"):
            profile.rsrp = param1
            profile.sinr = param2
            profile.rsrq = param3

        return True

    def _parse_cgdcont(self, response: str, profile: NetworkProfile) -> None:
        """Parse +CGDCONT response into profile."""
        # Find first active PDP context (usually cid=1)
        for match in CGDCONT_PATTERN.finditer(response):
            cid = int(match.group(1))
            pdp_type = match.group(2)
            apn = match.group(3)

            if cid == 1 and apn:
                profile.apn = apn
                break

    def _parse_cgpaddr(self, response: str, profile: NetworkProfile) -> None:
        """Parse +CGPADDR response into profile."""
        match = CGPADDR_PATTERN.search(response)
        if match:
            ip = match.group(2).strip()
            if ip and ip != "0.0.0.0":
                profile.ip_address = ip

    def _access_technology(self, act: int) -> NetworkType:
        """Convert access technology code to NetworkType."""
        act_map = {
            0: NetworkType.GSM,
            1: NetworkType.GSM,  # GSM Compact
            2: NetworkType.UMTS,
            3: NetworkType.EDGE,
            4: NetworkType.HSDPA,
            5: NetworkType.HSUPA,
            6: NetworkType.HSPA,
            7: NetworkType.LTE,
            8: NetworkType.LTE_CA,
            9: NetworkType.LTE,
            10: NetworkType.NR5G_NSA,
            11: NetworkType.NR5G_SA,
            12: NetworkType.NR5G_NSA,
            13: NetworkType.NR5G_SA,
        }
        return act_map.get(act, NetworkType.UNKNOWN)
