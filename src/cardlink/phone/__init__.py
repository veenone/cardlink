"""Phone Controller - Android device management via ADB for SCP81 OTA testing.

This module provides the phone controller implementation for managing Android
smartphones as test harnesses for GlobalPlatform SCP81 OTA testing.

Features:
- ADB device discovery and connection management
- Device, SIM, and network information retrieval
- AT command interface for modem access
- BIP (Bearer Independent Protocol) event monitoring
- SMS-PP trigger simulation for OTA sessions
- Logcat monitoring and parsing
- Network configuration (WiFi, mobile data, APN)
- Device profile management

Example usage:
    ```python
    from cardlink.phone import PhoneController

    async def main():
        controller = PhoneController()

        # Discover connected devices
        devices = await controller.discover_devices()
        for device in devices:
            print(f"Found: {device.serial} - {device.model}")

        # Get device facade
        phone = await controller.get_device(devices[0].serial)

        # Get device info
        profile = await phone.info.get_full_profile()
        print(profile.to_json())

        # Send AT command
        response = await phone.at.send_command("AT+CPIN?")
        print(response.data)

        # Monitor BIP events
        async with phone.bip.start_monitoring() as events:
            async for event in events:
                print(f"BIP: {event.event_type}")
    ```
"""

from cardlink.phone.models import (
    # Enums
    ATMethod,
    ATResult,
    BIPEventType,
    DataConnectionState,
    DeviceState,
    NetworkType,
    SIMStatus,
    # Device models
    ADBDevice,
    DeviceProfile,
    FullProfile,
    NetworkProfile,
    SIMProfile,
    # AT models
    ATResponse,
    # BIP models
    BIPEvent,
    LogcatEntry,
    # SMS models
    TriggerResult,
    TriggerTemplate,
    # Network models
    APNConfig,
)
from cardlink.phone.exceptions import (
    ADBCommandError,
    ADBNotFoundError,
    ADBTimeoutError,
    ATCommandError,
    ATTimeoutError,
    ATUnavailableError,
    BIPMonitorError,
    DeviceNotFoundError,
    DeviceOfflineError,
    DeviceUnauthorizedError,
    LogcatError,
    NetworkConfigError,
    PhoneControllerError,
    ProfileError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileSaveError,
    RootRequiredError,
    SMSTriggerError,
    TimeoutError,
)
from cardlink.phone.adb_client import ADBClient
from cardlink.phone.device_manager import DeviceManager
from cardlink.phone.device_info import DeviceInfo
from cardlink.phone.at_interface import ATInterface
from cardlink.phone.logcat_parser import LogcatParser
from cardlink.phone.bip_monitor import BIPMonitor, LogcatMonitor
from cardlink.phone.sms_trigger import SMSTrigger
from cardlink.phone.network_manager import NetworkManager
from cardlink.phone.profile_manager import ProfileManager
from cardlink.phone.controller import (
    Device,
    PhoneController,
    get_controller,
    discover_devices,
    get_device,
)

__all__ = [
    # Main classes
    "PhoneController",
    "Device",
    "ADBClient",
    "DeviceManager",
    "DeviceInfo",
    "ATInterface",
    "BIPMonitor",
    "LogcatMonitor",
    "LogcatParser",
    "SMSTrigger",
    "NetworkManager",
    "ProfileManager",
    # Convenience functions
    "get_controller",
    "discover_devices",
    "get_device",
    # Enums
    "ATMethod",
    "ATResult",
    "BIPEventType",
    "DataConnectionState",
    "DeviceState",
    "NetworkType",
    "SIMStatus",
    # Device models
    "ADBDevice",
    "DeviceProfile",
    "FullProfile",
    "NetworkProfile",
    "SIMProfile",
    # AT models
    "ATResponse",
    # BIP models
    "BIPEvent",
    "LogcatEntry",
    # SMS models
    "TriggerResult",
    "TriggerTemplate",
    # Network models
    "APNConfig",
    # Exceptions
    "ADBCommandError",
    "ADBNotFoundError",
    "ADBTimeoutError",
    "ATCommandError",
    "ATTimeoutError",
    "ATUnavailableError",
    "BIPMonitorError",
    "DeviceNotFoundError",
    "DeviceOfflineError",
    "DeviceUnauthorizedError",
    "LogcatError",
    "NetworkConfigError",
    "PhoneControllerError",
    "ProfileError",
    "ProfileLoadError",
    "ProfileNotFoundError",
    "ProfileSaveError",
    "RootRequiredError",
    "SMSTriggerError",
    "TimeoutError",
]
