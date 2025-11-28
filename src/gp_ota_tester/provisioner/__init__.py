"""UICC Provisioner - Smart card provisioning via PC/SC.

This package provides tools for provisioning UICC/SIM cards using the
GlobalPlatform specification over PC/SC interface.

Core Components:
    - PCSCClient: PC/SC reader and card communication
    - ATRParser: Answer-To-Reset parsing and card type detection
    - TLVParser: BER-TLV parsing and construction
    - APDUInterface: High-level APDU command helpers

Example:
    ```python
    from gp_ota_tester.provisioner import PCSCClient, APDUInterface

    # Connect to card
    client = PCSCClient()
    readers = client.list_readers()
    client.connect(readers[0])

    # Create APDU interface
    apdu = APDUInterface(client.transmit)

    # Select ISD
    response = apdu.select_by_aid("A0000000151000")
    print(f"ISD selected, SW={response.sw:04X}")

    client.disconnect()
    ```
"""

from gp_ota_tester.provisioner.exceptions import (
    APDUError,
    ATRError,
    AuthenticationError,
    CardNotFoundError,
    InvalidAPDUError,
    NotConnectedError,
    ProfileError,
    ProvisionerError,
    ReaderNotFoundError,
    SecurityError,
    TLVError,
    TransmitError,
)

from gp_ota_tester.provisioner.models import (
    APDUCommand,
    APDULogEntry,
    APDUResponse,
    ApplicationInfo,
    CardInfo,
    CardType,
    Convention,
    ATRInfo,
    INS,
    LifeCycleState,
    Privilege,
    Protocol,
    ProvisionerEvent,
    PSKConfiguration,
    ReaderInfo,
    SCPKeys,
    SecurityDomainInfo,
    URLConfiguration,
)

from gp_ota_tester.provisioner.tlv_parser import (
    TLV,
    TLVParser,
    Tags,
)

from gp_ota_tester.provisioner.atr_parser import (
    ATRParser,
    parse_atr,
)

from gp_ota_tester.provisioner.apdu_interface import (
    APDUInterface,
    SWDecoder,
    check_response,
)

from gp_ota_tester.provisioner.pcsc_client import (
    PCSCClient,
    list_readers,
    connect_card,
)

from gp_ota_tester.provisioner.secure_domain import (
    SecureDomainManager,
    ISD_AID,
)

from gp_ota_tester.provisioner.scp02 import SCP02
from gp_ota_tester.provisioner.scp03 import SCP03


__all__ = [
    # Exceptions
    "ProvisionerError",
    "ReaderNotFoundError",
    "CardNotFoundError",
    "NotConnectedError",
    "APDUError",
    "InvalidAPDUError",
    "TransmitError",
    "AuthenticationError",
    "SecurityError",
    "ProfileError",
    "TLVError",
    "ATRError",
    # Models
    "Protocol",
    "Convention",
    "CardType",
    "LifeCycleState",
    "Privilege",
    "INS",
    "ReaderInfo",
    "CardInfo",
    "ATRInfo",
    "APDUCommand",
    "APDUResponse",
    "APDULogEntry",
    "SecurityDomainInfo",
    "ApplicationInfo",
    "SCPKeys",
    "PSKConfiguration",
    "URLConfiguration",
    "ProvisionerEvent",
    # TLV
    "TLV",
    "TLVParser",
    "Tags",
    # ATR
    "ATRParser",
    "parse_atr",
    # APDU
    "APDUInterface",
    "SWDecoder",
    "check_response",
    # PC/SC
    "PCSCClient",
    "list_readers",
    "connect_card",
    # Security Domain
    "SecureDomainManager",
    "ISD_AID",
    # Secure Channels
    "SCP02",
    "SCP03",
]
