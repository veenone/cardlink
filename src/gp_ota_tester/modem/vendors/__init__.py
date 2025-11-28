"""Vendor-specific modem implementations.

This package contains modem implementations for specific vendors:
- Quectel (EG25-G, EC25, RG500Q, etc.)
- Sierra Wireless (future)
- SIMCom (future)
"""

from typing import Dict, Type

from gp_ota_tester.modem.vendors.base import Modem, SignalInfo
from gp_ota_tester.modem.vendors.quectel import QuectelModem, QuectelSignalInfo, ServingCellInfo

# Vendor modem registry
VENDOR_MODEMS: Dict[str, Type[Modem]] = {
    "quectel": QuectelModem,
}

__all__ = [
    "Modem",
    "SignalInfo",
    "QuectelModem",
    "QuectelSignalInfo",
    "ServingCellInfo",
    "VENDOR_MODEMS",
]
