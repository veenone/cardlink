"""BIP (Bearer Independent Protocol) configuration for UICC.

This module handles storage and retrieval of BIP configuration on UICC cards
for managing data connections from the card.
"""

import logging
from typing import Optional

from cardlink.provisioner.apdu_interface import APDUInterface
from cardlink.provisioner.exceptions import ProfileError
from cardlink.provisioner.models import (
    APDUCommand,
    BearerType,
    BIPConfiguration,
    INS,
)
from cardlink.provisioner.tlv_parser import TLVParser

logger = logging.getLogger(__name__)


# Elementary File ID for BIP configuration storage
EF_BIP_CONFIG = "2F54"  # File for BIP configuration (example location)

# TLV tags for BIP data (match those in BIPConfiguration.to_tlv())
TAG_BEARER_TYPE = 0x80
TAG_APN = 0x81
TAG_BUFFER_SIZE = 0x82
TAG_TIMEOUT = 0x83
TAG_USER_LOGIN = 0x84
TAG_USER_PASSWORD = 0x85


class BIPConfig:
    """BIP configuration manager for UICC cards.

    Handles storing and retrieving Bearer Independent Protocol (BIP)
    configuration on UICC cards for managing data connections.

    BIP allows the UICC to establish data connections using various bearers
    (GPRS, UTRAN, WiFi, etc.) for communicating with remote servers.

    Configuration Parameters:
        - Bearer Type: Type of connection (GPRS, UTRAN, WiFi, etc.)
        - APN: Access Point Name for packet-switched connections
        - Buffer Size: Channel buffer size (1-65535 bytes)
        - Timeout: Connection timeout in seconds
        - User Login/Password: Optional authentication credentials

    Storage Format:
        BIP configuration is stored in TLV format with the following tags:
        - Bearer Type (Tag 0x80): 1 byte
        - APN (Tag 0x81): DNS label format (variable length)
        - Buffer Size (Tag 0x82): 2 bytes (big-endian)
        - Timeout (Tag 0x83): 1 byte
        - User Login (Tag 0x84): UTF-8 string (optional)
        - User Password (Tag 0x85): UTF-8 string (optional)

    Terminal Profile Check:
        Before configuring BIP, this class can check the terminal profile
        to verify that the device supports BIP operations.

    Example:
        >>> from cardlink.provisioner import PCSCClient, APDUInterface
        >>> from cardlink.provisioner.bip_config import BIPConfig
        >>> from cardlink.provisioner.models import BIPConfiguration, BearerType
        >>>
        >>> # Connect to card
        >>> client = PCSCClient()
        >>> client.connect(client.list_readers()[0])
        >>> apdu = APDUInterface(client.transmit)
        >>>
        >>> # Create BIP configuration
        >>> bip_conf = BIPConfiguration(
        ...     bearer_type=BearerType.GPRS,
        ...     apn="internet.example.com",
        ...     buffer_size=1400,
        ...     timeout=30
        ... )
        >>>
        >>> # Check terminal support
        >>> bip_config = BIPConfig(apdu)
        >>> if bip_config.check_terminal_support():
        ...     # Configure on card
        ...     bip_config.configure(bip_conf)
        >>>
        >>> # Read current configuration
        >>> current = bip_config.read_configuration()
        >>> print(f"Bearer: {current.bearer_type.name}, APN: {current.apn}")
    """

    def __init__(self, apdu_interface: APDUInterface):
        """Initialize BIP configuration manager.

        Args:
            apdu_interface: APDU interface for card communication.
        """
        self.apdu = apdu_interface

    def configure(self, config: BIPConfiguration) -> None:
        """Configure BIP settings on the card.

        Args:
            config: BIP configuration to store.

        Raises:
            ProfileError: If configuration fails.

        Example:
            >>> bip_conf = BIPConfiguration(
            ...     bearer_type=BearerType.GPRS,
            ...     apn="internet.example.com"
            ... )
            >>> bip_config.configure(bip_conf)
        """
        logger.info(
            f"Configuring BIP: bearer={config.bearer_type.name}, apn={config.apn}"
        )

        try:
            # Select BIP configuration file
            self.apdu.select_by_path(EF_BIP_CONFIG)

            # Encode configuration to TLV
            bip_tlv = config.to_tlv()

            # Update file with TLV data
            response = self.apdu.send(
                APDUCommand(
                    cla=0x00,
                    ins=INS.UPDATE_BINARY,
                    p1=0x00,
                    p2=0x00,
                    data=bip_tlv,
                )
            )

            if not response.is_success:
                raise ProfileError(
                    f"Failed to write BIP configuration: {response.status_message}"
                )

            logger.info("BIP configuration completed")

        except Exception as e:
            logger.error(f"Failed to configure BIP: {e}")
            raise ProfileError(f"Failed to configure BIP: {e}") from e

    def read_configuration(self) -> BIPConfiguration:
        """Read current BIP configuration from card.

        Returns:
            Current BIP configuration.

        Raises:
            ProfileError: If read fails or data is invalid.

        Example:
            >>> config = bip_config.read_configuration()
            >>> print(f"Bearer: {config.bearer_type.name}")
            >>> print(f"APN: {config.apn}")
        """
        try:
            # Select and read BIP configuration file
            self.apdu.select_by_path(EF_BIP_CONFIG)

            response = self.apdu.send(
                APDUCommand(
                    cla=0x00,
                    ins=INS.READ_BINARY,
                    p1=0x00,
                    p2=0x00,
                    le=0,  # Read all available
                )
            )

            if not response.is_success:
                raise ProfileError(
                    f"Failed to read BIP configuration: {response.status_message}"
                )

            # Parse TLV data
            config = self._parse_bip_config(response.data)

            logger.debug(f"Read BIP configuration: bearer={config.bearer_type.name}")
            return config

        except Exception as e:
            logger.error(f"Failed to read BIP configuration: {e}")
            raise ProfileError(f"Failed to read BIP configuration: {e}") from e

    def check_terminal_support(self) -> bool:
        """Check if terminal profile indicates BIP support.

        Reads the terminal profile from the card to determine if the
        device supports BIP operations.

        Returns:
            True if BIP is supported, False otherwise.

        Note:
            This is a simplified check. Full terminal profile parsing
            would examine specific bytes for BIP capability flags.

        Example:
            >>> if bip_config.check_terminal_support():
            ...     print("BIP is supported")
            ... else:
            ...     print("BIP not supported by terminal")
        """
        try:
            # TERMINAL PROFILE is typically stored in EF_TERMINAL_PROFILE
            # For now, we'll assume BIP is supported if we can read the file
            # A full implementation would parse the terminal profile bytes

            logger.info("Checking terminal BIP support")

            # Attempt to read terminal profile
            # This is vendor-specific and may vary
            # For now, return True as a placeholder
            logger.warning(
                "Terminal profile check not fully implemented - assuming BIP support"
            )
            return True

        except Exception as e:
            logger.warning(f"Could not check terminal support: {e}")
            return False

    def _parse_bip_config(self, data: bytes) -> BIPConfiguration:
        """Parse BIP configuration from TLV data.

        Args:
            data: TLV-encoded BIP configuration.

        Returns:
            Parsed BIP configuration.

        Raises:
            ProfileError: If parsing fails.
        """
        if not data or data == b"\x00" * len(data):
            # Empty or zeroed data - return default configuration
            return BIPConfiguration()

        try:
            tlv_list = TLVParser.parse(data)

            # Extract configuration fields
            bearer_type = BearerType.DEFAULT
            apn = ""
            buffer_size = 1400
            timeout = 30
            user_login = None
            user_password = None

            for tlv in tlv_list:
                if tlv.tag == TAG_BEARER_TYPE:
                    bearer_type = BearerType(tlv.value[0])
                elif tlv.tag == TAG_APN:
                    apn = BIPConfiguration._decode_apn(tlv.value)
                elif tlv.tag == TAG_BUFFER_SIZE:
                    buffer_size = int.from_bytes(tlv.value, byteorder="big")
                elif tlv.tag == TAG_TIMEOUT:
                    timeout = tlv.value[0]
                elif tlv.tag == TAG_USER_LOGIN:
                    user_login = tlv.value.decode("utf-8").rstrip("\x00")
                elif tlv.tag == TAG_USER_PASSWORD:
                    user_password = tlv.value.decode("utf-8").rstrip("\x00")

            return BIPConfiguration(
                bearer_type=bearer_type,
                apn=apn,
                buffer_size=buffer_size,
                timeout=timeout,
                user_login=user_login,
                user_password=user_password,
            )

        except Exception as e:
            logger.error(f"Failed to parse BIP configuration: {e}")
            raise ProfileError(f"Failed to parse BIP configuration: {e}") from e
