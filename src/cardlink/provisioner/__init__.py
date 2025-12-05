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
    from cardlink.provisioner import PCSCClient, APDUInterface

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

from cardlink.provisioner.exceptions import (
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
)

from cardlink.provisioner.models import (
    APDUCommand,
    APDULogEntry,
    APDUResponse,
    ApplicationInfo,
    BearerType,
    BIPConfiguration,
    CardInfo,
    CardProfile,
    CardType,
    Convention,
    ATRInfo,
    INS,
    LifeCycleState,
    PollTriggerConfig,
    Privilege,
    Protocol,
    ProvisionerEvent,
    PSKConfiguration,
    ReaderInfo,
    SCPKeys,
    SecurityDomainInfo,
    SMSTriggerConfig,
    TriggerConfiguration,
    TriggerType,
    URLConfiguration,
)

from cardlink.provisioner.tlv_parser import (
    TLV,
    TLVParser,
    Tags,
)

from cardlink.provisioner.atr_parser import (
    ATRParser,
    parse_atr,
)

from cardlink.provisioner.apdu_interface import (
    APDUInterface,
    SWDecoder,
    check_response,
)

from cardlink.provisioner.pcsc_client import (
    PCSCClient,
    list_readers,
    connect_card,
)

from cardlink.provisioner.secure_domain import (
    SecureDomainManager,
    ISD_AID,
)

from cardlink.provisioner.scp02 import SCP02
from cardlink.provisioner.scp03 import SCP03

from cardlink.provisioner.key_manager import KeyManager
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.url_config import URLConfig
from cardlink.provisioner.trigger_config import TriggerConfig
from cardlink.provisioner.bip_config import BIPConfig
from cardlink.provisioner.profile_manager import ProfileManager


__all__ = [
    # Exceptions
    "ProvisionerError",
    "ReaderNotFoundError",
    "CardNotFoundError",
    "NotConnectedError",
    "APDUError",
    "InvalidAPDUError",
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
    "TriggerType",
    "SMSTriggerConfig",
    "PollTriggerConfig",
    "TriggerConfiguration",
    "BearerType",
    "BIPConfiguration",
    "CardProfile",
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
    # Configuration
    "KeyManager",
    "PSKConfig",
    "URLConfig",
    "TriggerConfig",
    "BIPConfig",
    "ProfileManager",
]
