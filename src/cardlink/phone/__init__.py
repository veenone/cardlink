"""Phone controller package for Android device management via ADB.

This package provides tools for controlling Android devices via ADB for
OTA testing with real phones and UICC cards.

Core Components:
    - ADBController: Synchronous ADB command execution
    - NetworkManager: WiFi and network management
    - ATInterface: AT command interface for modem
    - BIPMonitor: BIP event monitoring via logcat
    - SMSTrigger: SMS-PP trigger sending
"""

# Synchronous interfaces (simpler, no async)
from cardlink.phone.adb_controller import ADBController, DeviceInfo
from cardlink.phone.network_manager import (
    NetworkManager,
    NetworkStatus,
    WiFiNetwork,
)

# Note: The following async-based modules are also available:
# - adb_client (async ADB operations)
# - at_interface (async AT commands)
# - bip_monitor (async BIP monitoring)
# - sms_trigger (async SMS sending)
# Import these directly if async operations are needed

__all__ = [
    # Sync interfaces
    "ADBController",
    "DeviceInfo",
    "NetworkManager",
    "NetworkStatus",
    "WiFiNetwork",
]
