"""Mobile Simulator package for GP OTA Tester.

This package provides a mobile phone/UICC simulator for testing
PSK-TLS Admin Server functionality without physical hardware.

Main Classes:
    MobileSimulator: Main simulator class that orchestrates connections.
    SimulatorConfig: Configuration for simulator behavior.
    VirtualUICC: Virtual UICC card implementation.

Example:
    >>> from cardlink.simulator import MobileSimulator, SimulatorConfig
    >>>
    >>> config = SimulatorConfig(
    ...     server_host="127.0.0.1",
    ...     server_port=8443,
    ...     psk_identity="test_card",
    ...     psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10")
    ... )
    >>>
    >>> simulator = MobileSimulator(config)
    >>> result = await simulator.run_complete_session()
    >>> print(f"Success: {result.success}, APDUs: {result.apdu_count}")
"""

from .behavior import BehaviorController
from .client import MobileSimulator, SimulatorError
from .config import BehaviorConfig, SimulatorConfig, UICCProfile
from .http_client import HTTPAdminClient, HTTPAdminError, HTTPStatusError
from .models import (
    APDUExchange,
    BehaviorMode,
    ConnectionMode,
    ConnectionState,
    SessionResult,
    SimulatorStats,
    TLSConnectionInfo,
    VirtualApplet,
)
from .psk_tls_client import (
    ConnectionError,
    HandshakeError,
    PSKTLSClient,
    PSKTLSClientError,
    TimeoutError,
)
from .virtual_uicc import ParsedAPDU, VirtualUICC

__all__ = [
    # Main classes
    "MobileSimulator",
    "SimulatorConfig",
    "VirtualUICC",
    # Configuration
    "BehaviorConfig",
    "UICCProfile",
    # Components
    "PSKTLSClient",
    "HTTPAdminClient",
    "BehaviorController",
    # Models
    "ConnectionState",
    "BehaviorMode",
    "ConnectionMode",
    "TLSConnectionInfo",
    "APDUExchange",
    "SessionResult",
    "SimulatorStats",
    "VirtualApplet",
    "ParsedAPDU",
    # Exceptions
    "SimulatorError",
    "PSKTLSClientError",
    "ConnectionError",
    "HandshakeError",
    "TimeoutError",
    "HTTPAdminError",
    "HTTPStatusError",
]
