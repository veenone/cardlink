"""URL configuration for remote profile server access.

This module handles storage and retrieval of remote server URLs
on UICC cards for OTA profile provisioning.
"""

import logging
from urllib.parse import urlparse

from cardlink.provisioner.apdu_interface import APDUInterface
from cardlink.provisioner.exceptions import ProfileError
from cardlink.provisioner.models import APDUCommand, INS, URLConfiguration
from cardlink.provisioner.tlv_parser import TLVParser

logger = logging.getLogger(__name__)


# Elementary File ID for URL storage
EF_ADMIN_URL = "2F52"  # File for admin server URL (example location)

# TLV tag for URL data
TAG_URL = 0x80


class URLConfig:
    """URL configuration manager for UICC cards.

    Handles storing and retrieving remote server URLs on UICC cards
    for OTA profile provisioning and management.

    URL Format:
        URLs must be valid HTTP or HTTPS URLs with the following constraints:
        - Scheme: http or https
        - Maximum length: 255 bytes
        - Must include host
        - Port is optional (defaults: 80 for HTTP, 443 for HTTPS)

    Storage Format:
        URLs are stored in TLV format:
        - Tag: 0x80 (URL)
        - Length: URL byte length
        - Value: URL string (ASCII/UTF-8)

    Example:
        >>> from cardlink.provisioner import PCSCClient, APDUInterface
        >>> from cardlink.provisioner.url_config import URLConfig
        >>> from cardlink.provisioner.models import URLConfiguration
        >>>
        >>> # Connect to card
        >>> client = PCSCClient()
        >>> client.connect(client.list_readers()[0])
        >>> apdu = APDUInterface(client.transmit)
        >>>
        >>> # Create URL configuration
        >>> url_conf = URLConfiguration.from_url("https://server.example.com:8443/admin")
        >>>
        >>> # Configure on card
        >>> url_config = URLConfig(apdu)
        >>> url_config.configure(url_conf)
        >>>
        >>> # Read current configuration
        >>> current = url_config.read_configuration()
        >>> print(f"Admin URL: {current.url}")
    """

    # Maximum URL length (card storage constraint)
    MAX_URL_LENGTH = 255

    def __init__(self, apdu_interface: APDUInterface):
        """Initialize URL configuration manager.

        Args:
            apdu_interface: APDU interface for card communication.
        """
        self.apdu = apdu_interface

    def configure(self, config: URLConfiguration) -> None:
        """Configure admin server URL on the card.

        Args:
            config: URL configuration to store.

        Raises:
            ProfileError: If configuration fails or URL is invalid.

        Example:
            >>> url_conf = URLConfiguration.from_url("https://admin.example.com/api")
            >>> url_config.configure(url_conf)
        """
        # Validate URL
        if not self.validate(config.url):
            raise ProfileError(f"Invalid URL: {config.url}")

        logger.info(f"Configuring admin URL: {config.url}")

        try:
            # Select URL file
            self.apdu.select_by_path(EF_ADMIN_URL)

            # Encode URL to TLV
            url_tlv = config.to_tlv()

            # Update file with TLV data
            response = self.apdu.send(
                APDUCommand(
                    cla=0x00,
                    ins=INS.UPDATE_BINARY,
                    p1=0x00,
                    p2=0x00,
                    data=url_tlv,
                )
            )

            if not response.is_success:
                raise ProfileError(
                    f"Failed to write URL configuration: {response.status_message}"
                )

            logger.info("URL configuration completed")

        except Exception as e:
            logger.error(f"Failed to configure URL: {e}")
            raise ProfileError(f"Failed to configure URL: {e}") from e

    def read_configuration(self) -> URLConfiguration:
        """Read current URL configuration from card.

        Returns:
            Current URL configuration.

        Raises:
            ProfileError: If read fails or data is invalid.

        Example:
            >>> config = url_config.read_configuration()
            >>> print(f"Admin URL: {config.url}")
        """
        try:
            # Select and read URL file
            self.apdu.select_by_path(EF_ADMIN_URL)

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
                    f"Failed to read URL configuration: {response.status_message}"
                )

            # Parse TLV data
            tlv_list = TLVParser.parse(response.data)
            if not tlv_list:
                raise ProfileError("No URL data found")

            # Find URL tag
            url_tlv = next((t for t in tlv_list if t.tag == TAG_URL), None)
            if not url_tlv:
                raise ProfileError(f"URL tag {TAG_URL:02X} not found")

            # Decode URL
            url = url_tlv.value.decode("utf-8").rstrip("\x00")

            logger.debug(f"Read URL configuration: {url}")

            return URLConfiguration.from_url(url)

        except Exception as e:
            logger.error(f"Failed to read URL configuration: {e}")
            raise ProfileError(f"Failed to read URL configuration: {e}") from e

    @classmethod
    def validate(cls, url: str) -> bool:
        """Validate URL format and constraints.

        Args:
            url: URL string to validate.

        Returns:
            True if URL is valid, False otherwise.

        Validation Rules:
            - Must be parseable as URL
            - Scheme must be http or https
            - Must have hostname
            - Length must be <= MAX_URL_LENGTH

        Example:
            >>> URLConfig.validate("https://server.example.com:8443/admin")
            True
            >>> URLConfig.validate("ftp://invalid.com")
            False
            >>> URLConfig.validate("not_a_url")
            False
        """
        try:
            # Check length
            if len(url) > cls.MAX_URL_LENGTH:
                logger.warning(f"URL too long: {len(url)} > {cls.MAX_URL_LENGTH}")
                return False

            # Parse URL
            parsed = urlparse(url)

            # Validate scheme
            if parsed.scheme not in ("http", "https"):
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Validate hostname
            if not parsed.netloc:
                logger.warning("URL missing hostname")
                return False

            return True

        except Exception as e:
            logger.warning(f"URL validation failed: {e}")
            return False
