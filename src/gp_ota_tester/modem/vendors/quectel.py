"""Quectel modem implementation.

This module provides Quectel-specific modem functionality
for models like EG25-G, EC25, RG500Q, etc.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from gp_ota_tester.modem.exceptions import ATCommandError
from gp_ota_tester.modem.models import ModemVendor, NetworkType
from gp_ota_tester.modem.vendors.base import Modem, SignalInfo

logger = logging.getLogger(__name__)


# Quectel-specific response patterns
QCSQ_PATTERN = re.compile(r'\+QCSQ:\s*"([^"]+)",(-?\d+)(?:,(-?\d+))?(?:,(-?\d+))?(?:,(-?\d+))?')
QENG_SERVING_PATTERN = re.compile(r'\+QENG:\s*"servingcell","([^"]+)"')
QCFG_BAND_PATTERN = re.compile(r'\+QCFG:\s*"band",([^,]+),([^,]+),([^,]+)')


@dataclass
class QuectelSignalInfo(SignalInfo):
    """Extended signal info for Quectel modems."""

    network_type: NetworkType = NetworkType.UNKNOWN


@dataclass
class ServingCellInfo:
    """Serving cell information from AT+QENG."""

    state: str = ""  # SEARCH, LIMSRV, NOCONN, CONNECT
    is_tdd: bool = False
    mcc: str = ""
    mnc: str = ""
    cell_id: str = ""
    pcid: int = 0  # Physical Cell ID
    earfcn: int = 0  # E-UTRA Absolute Radio Frequency Channel Number
    freq_band: int = 0
    ul_bandwidth: int = 0
    dl_bandwidth: int = 0
    tac: str = ""
    rsrp: Optional[int] = None
    rsrq: Optional[int] = None
    rssi: Optional[int] = None
    sinr: Optional[int] = None


class QuectelModem(Modem):
    """Quectel-specific modem implementation.

    Supports EG25-G, EC25, EG12, BG96, RG500Q, RG520N, and similar models.

    Example:
        >>> modem = QuectelModem("/dev/ttyUSB2")
        >>> await modem.connect()
        >>>
        >>> # Get detailed signal
        >>> signal = await modem.get_signal_info()
        >>> print(f"RSRP: {signal.rsrp} dBm, SINR: {signal.sinr} dB")
        >>>
        >>> # Configure bands
        >>> await modem.configure_bands(["B1", "B3", "B7", "B20"])
        >>>
        >>> # Get engineering mode info
        >>> cell_info = await modem.get_serving_cell_info()
    """

    VENDOR = ModemVendor.QUECTEL

    async def _initialize(self) -> None:
        """Quectel-specific initialization."""
        # Enable verbose error messages
        await self.at.set_verbose_errors(True)

        # Disable echo for cleaner parsing
        await self.at.disable_echo()

    async def get_signal_info(self) -> QuectelSignalInfo:
        """Get detailed signal information via AT+QCSQ.

        Returns:
            QuectelSignalInfo with network-specific signal data.
        """
        info = QuectelSignalInfo()

        try:
            response = await self.at.send_command("AT+QCSQ", check_error=False)
            if response.success:
                match = QCSQ_PATTERN.search(response.raw_response)
                if match:
                    net_type = match.group(1)
                    param1 = int(match.group(2)) if match.group(2) else None
                    param2 = int(match.group(3)) if match.group(3) else None
                    param3 = int(match.group(4)) if match.group(4) else None
                    param4 = int(match.group(5)) if match.group(5) else None

                    # Map network type
                    type_map = {
                        "GSM": NetworkType.GSM,
                        "WCDMA": NetworkType.UMTS,
                        "LTE": NetworkType.LTE,
                        "CAT-M1": NetworkType.LTE,
                        "CAT-NB1": NetworkType.LTE,
                        "TDSCDMA": NetworkType.UMTS,
                        "NR5G-NSA": NetworkType.NR5G_NSA,
                        "NR5G-SA": NetworkType.NR5G_SA,
                    }
                    info.network_type = type_map.get(net_type, NetworkType.UNKNOWN)

                    # Parse parameters based on network type
                    if net_type == "GSM":
                        info.rssi = param1
                    elif net_type == "WCDMA":
                        info.rssi = param1
                        info.rsrp = param2
                        info.sinr = param3  # Actually ECNO for WCDMA
                    elif net_type in ("LTE", "CAT-M1", "CAT-NB1"):
                        info.rssi = param1
                        info.rsrp = param2
                        info.sinr = param3
                        info.rsrq = param4
                    elif net_type in ("NR5G-NSA", "NR5G-SA"):
                        info.rsrp = param1
                        info.sinr = param2
                        info.rsrq = param3

                    logger.debug(
                        "Signal info: type=%s, RSRP=%s, SINR=%s, RSRQ=%s",
                        net_type, info.rsrp, info.sinr, info.rsrq
                    )

        except ATCommandError as e:
            logger.warning("Failed to get QCSQ: %s", e)

        return info

    async def enable_stk(self) -> bool:
        """Enable STK notifications via AT+QSTK=1.

        Returns:
            True if successful.
        """
        try:
            response = await self.at.send_command("AT+QSTK=1", check_error=False)
            if response.success:
                logger.info("STK notifications enabled")
                return True
        except ATCommandError:
            pass
        return False

    async def disable_stk(self) -> bool:
        """Disable STK notifications via AT+QSTK=0.

        Returns:
            True if successful.
        """
        try:
            response = await self.at.send_command("AT+QSTK=0", check_error=False)
            return response.success
        except ATCommandError:
            return False

    async def get_serving_cell_info(self) -> Optional[ServingCellInfo]:
        """Get serving cell information via AT+QENG.

        Returns:
            ServingCellInfo if available, None otherwise.
        """
        try:
            response = await self.at.send_command('AT+QENG="servingcell"', check_error=False)
            if response.success:
                return self._parse_qeng_response(response.raw_response)
        except ATCommandError:
            pass
        return None

    def _parse_qeng_response(self, response: str) -> Optional[ServingCellInfo]:
        """Parse AT+QENG response."""
        info = ServingCellInfo()

        # Check for state
        match = QENG_SERVING_PATTERN.search(response)
        if match:
            info.state = match.group(1)

        # Parse LTE format
        # +QENG: "servingcell","NOCONN","LTE","FDD",234,15,1234567,123,3350,7,3,3,4E7C,-92,-10,-64,11,0
        lte_pattern = re.compile(
            r'\+QENG:\s*"servingcell","([^"]+)","LTE","([^"]+)",(\d+),(\d+),([0-9A-Fa-f]+),(\d+),'
            r'(\d+),(\d+),(\d+),(\d+),([0-9A-Fa-f]+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)'
        )
        match = lte_pattern.search(response)
        if match:
            info.state = match.group(1)
            info.is_tdd = match.group(2) == "TDD"
            info.mcc = match.group(3)
            info.mnc = match.group(4)
            info.cell_id = match.group(5)
            info.pcid = int(match.group(6))
            info.earfcn = int(match.group(7))
            info.freq_band = int(match.group(8))
            info.ul_bandwidth = int(match.group(9))
            info.dl_bandwidth = int(match.group(10))
            info.tac = match.group(11)
            info.rsrp = int(match.group(12))
            info.rsrq = int(match.group(13))
            info.rssi = int(match.group(14))
            info.sinr = int(match.group(15))

            return info

        return None

    async def configure_bands(self, bands: List[str]) -> bool:
        """Configure LTE bands via AT+QCFG="band".

        Args:
            bands: List of band names (e.g., ["B1", "B3", "B7"]).

        Returns:
            True if successful.
        """
        # Convert band names to bitmask
        band_mask = self._bands_to_mask(bands)
        if band_mask is None:
            logger.warning("Invalid band configuration")
            return False

        try:
            # Format: AT+QCFG="band",<gsm_band>,<lte_band>,<nb_band>
            # We're only setting LTE bands here
            cmd = f'AT+QCFG="band",0,{band_mask:x},0'
            response = await self.at.send_command(cmd, check_error=False)
            return response.success
        except ATCommandError:
            return False

    def _bands_to_mask(self, bands: List[str]) -> Optional[int]:
        """Convert band names to bitmask."""
        # LTE band to bit position mapping
        band_bits = {
            "B1": 0, "B2": 1, "B3": 2, "B4": 3, "B5": 4,
            "B7": 6, "B8": 7, "B12": 11, "B13": 12,
            "B18": 17, "B19": 18, "B20": 19, "B25": 24,
            "B26": 25, "B28": 27, "B38": 37, "B39": 38,
            "B40": 39, "B41": 40, "B66": 65,
        }

        mask = 0
        for band in bands:
            band_upper = band.upper()
            if band_upper in band_bits:
                mask |= (1 << band_bits[band_upper])
            else:
                logger.warning("Unknown band: %s", band)

        return mask if mask > 0 else None

    async def get_configured_bands(self) -> Dict[str, int]:
        """Get currently configured bands.

        Returns:
            Dictionary with GSM, LTE, and NB-IoT band masks.
        """
        try:
            response = await self.at.send_command('AT+QCFG="band"', check_error=False)
            if response.success:
                match = QCFG_BAND_PATTERN.search(response.raw_response)
                if match:
                    return {
                        "gsm": int(match.group(1), 16),
                        "lte": int(match.group(2), 16),
                        "nb": int(match.group(3), 16),
                    }
        except ATCommandError:
            pass
        return {}

    async def send_ussd(self, code: str) -> Optional[str]:
        """Send USSD code via AT+CUSD.

        Args:
            code: USSD code (e.g., "*100#").

        Returns:
            USSD response if received, None otherwise.
        """
        try:
            # Enable USSD result presentation
            await self.at.send_command("AT+CUSD=1", check_error=False)

            # Send USSD code
            cmd = f'AT+CUSD=1,"{code}",15'
            response = await self.at.send_command(cmd, timeout=30.0, check_error=False)

            # Parse +CUSD response
            match = re.search(r'\+CUSD:\s*\d+,"([^"]*)"', response.raw_response)
            if match:
                return match.group(1)

        except ATCommandError:
            pass
        return None

    async def get_network_scan(self, timeout: float = 180.0) -> List[Dict[str, Any]]:
        """Perform network scan via AT+QSCAN.

        Args:
            timeout: Scan timeout (can take 2-3 minutes).

        Returns:
            List of network information dictionaries.
        """
        networks = []

        try:
            response = await self.at.send_command(
                "AT+QSCAN=3", timeout=timeout, check_error=False
            )
            if response.success:
                # Parse +QSCAN results
                # +QSCAN: "LTE",234,15,-85,-7,1839,7,1
                pattern = re.compile(
                    r'\+QSCAN:\s*"([^"]+)",(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+),(\d+)'
                )
                for match in pattern.finditer(response.raw_response):
                    networks.append({
                        "rat": match.group(1),
                        "mcc": match.group(2),
                        "mnc": match.group(3),
                        "rsrp": int(match.group(4)),
                        "rsrq": int(match.group(5)),
                        "earfcn": int(match.group(6)),
                        "band": int(match.group(7)),
                        "pci": int(match.group(8)),
                    })

        except ATCommandError:
            pass

        return networks

    async def enable_gps(self) -> bool:
        """Enable GPS via AT+QGPS=1.

        Returns:
            True if successful.
        """
        try:
            response = await self.at.send_command("AT+QGPS=1", check_error=False)
            return response.success
        except ATCommandError:
            return False

    async def disable_gps(self) -> bool:
        """Disable GPS via AT+QGPSEND.

        Returns:
            True if successful.
        """
        try:
            response = await self.at.send_command("AT+QGPSEND", check_error=False)
            return response.success
        except ATCommandError:
            return False

    async def get_gps_location(self) -> Optional[Dict[str, Any]]:
        """Get GPS location via AT+QGPSLOC.

        Returns:
            Location dictionary if available, None otherwise.
        """
        try:
            response = await self.at.send_command("AT+QGPSLOC=2", check_error=False)
            if response.success:
                # +QGPSLOC: <UTC>,<latitude>,<longitude>,<hdop>,<altitude>,<fix>,<cog>,<spkm>,<spkn>,<date>,<nsat>
                pattern = re.compile(
                    r'\+QGPSLOC:\s*([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),(\d+)'
                )
                match = pattern.search(response.raw_response)
                if match:
                    return {
                        "utc": match.group(1),
                        "latitude": float(match.group(2)),
                        "longitude": float(match.group(3)),
                        "hdop": float(match.group(4)),
                        "altitude": float(match.group(5)),
                        "fix": int(match.group(6)),
                    }
        except ATCommandError:
            pass
        return None
