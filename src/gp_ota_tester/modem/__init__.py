"""Modem Controller for GP OTA Tester.

This package provides modem management and control functionality for
IoT cellular modems (Quectel, Sierra Wireless, etc.) via serial/USB
communication.

Features:
- Modem discovery and identification
- AT command interface
- URC (Unsolicited Result Code) monitoring
- BIP (Bearer Independent Protocol) event detection via STK
- SMS-PP trigger message sending
- Network configuration and monitoring
- Optional QXDM diagnostic integration

Quick Start:
    >>> from gp_ota_tester.modem import ModemController
    >>>
    >>> # Create controller
    >>> controller = ModemController()
    >>>
    >>> # Discover modems
    >>> modems = await controller.discover_modems()
    >>>
    >>> # Get modem and send command
    >>> modem = await controller.get_modem("/dev/ttyUSB2")
    >>> response = await modem.send_command("ATI")

Example with BIP monitoring:
    >>> from gp_ota_tester.modem import ModemController
    >>>
    >>> controller = ModemController()
    >>> modem = await controller.get_modem("/dev/ttyUSB2")
    >>>
    >>> # Register BIP event callback
    >>> def on_bip_event(event):
    ...     print(f"BIP event: {event.command}")
    >>>
    >>> modem.on_bip_event(on_bip_event)
    >>> await modem.start_bip_monitoring()
"""

# Core Classes
from gp_ota_tester.modem.controller import ModemController
from gp_ota_tester.modem.serial_client import SerialClient
from gp_ota_tester.modem.at_interface import ATInterface
from gp_ota_tester.modem.urc_parser import URCParser, parse_urc, is_urc
from gp_ota_tester.modem.modem_manager import ModemManager, ModemInfo
from gp_ota_tester.modem.modem_info import ModemInfoRetriever
from gp_ota_tester.modem.bip_monitor import BIPMonitor
from gp_ota_tester.modem.sms_trigger import SMSTrigger
from gp_ota_tester.modem.network_manager import NetworkManager
from gp_ota_tester.modem.qxdm_interface import QXDMInterface

# Vendor Implementations
from gp_ota_tester.modem.vendors import (
    Modem,
    SignalInfo,
    QuectelModem,
    QuectelSignalInfo,
    ServingCellInfo,
    VENDOR_MODEMS,
)

# Models and Enums
from gp_ota_tester.modem.models import (
    ATResponse,
    ATResult,
    AuthType,
    BIPCommand,
    BIPEvent,
    FullModemProfile,
    ModemProfile,
    ModemVendor,
    NetworkProfile,
    NetworkType,
    PingResult,
    PortInfo,
    QUECTEL_PORT_FUNCTIONS,
    QUECTEL_USB_IDS,
    RegistrationStatus,
    SIMProfile,
    SIMStatus,
    TriggerResult,
    TriggerTemplate,
    URCEvent,
    URCType,
    USB_VENDOR_MAP,
)

# Exceptions
from gp_ota_tester.modem.exceptions import (
    ATCommandError,
    ATTimeoutError,
    BIPMonitorError,
    CMEError,
    CMSError,
    ModemControllerError,
    ModemNotFoundError,
    NetworkError,
    QXDMError,
    SerialPortError,
    SMSTriggerError,
    URCParseError,
)

__all__ = [
    # Core Classes
    "ModemController",
    "SerialClient",
    "ATInterface",
    "URCParser",
    "ModemManager",
    "ModemInfo",
    "ModemInfoRetriever",
    "BIPMonitor",
    "SMSTrigger",
    "NetworkManager",
    "QXDMInterface",
    # Vendor Classes
    "Modem",
    "SignalInfo",
    "QuectelModem",
    "QuectelSignalInfo",
    "ServingCellInfo",
    "VENDOR_MODEMS",
    # Utility Functions
    "parse_urc",
    "is_urc",
    # Enums
    "ATResult",
    "RegistrationStatus",
    "NetworkType",
    "SIMStatus",
    "AuthType",
    "URCType",
    "BIPCommand",
    "ModemVendor",
    # Data Models
    "PortInfo",
    "ATResponse",
    "URCEvent",
    "BIPEvent",
    "ModemProfile",
    "SIMProfile",
    "NetworkProfile",
    "FullModemProfile",
    "PingResult",
    "TriggerTemplate",
    "TriggerResult",
    # Constants
    "QUECTEL_USB_IDS",
    "USB_VENDOR_MAP",
    "QUECTEL_PORT_FUNCTIONS",
    # Exceptions
    "ModemControllerError",
    "ModemNotFoundError",
    "SerialPortError",
    "ATCommandError",
    "ATTimeoutError",
    "CMEError",
    "CMSError",
    "URCParseError",
    "BIPMonitorError",
    "SMSTriggerError",
    "NetworkError",
    "QXDMError",
]
