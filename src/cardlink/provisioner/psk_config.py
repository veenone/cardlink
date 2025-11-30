"""PSK (Pre-Shared Key) configuration for UICC provisioning.

This module handles storage and retrieval of TLS-PSK credentials
on UICC cards for secure server connections.
"""

import logging
from typing import Callable, Optional

from cardlink.provisioner.apdu_interface import APDUInterface
from cardlink.provisioner.exceptions import ProfileError, SecurityError
from cardlink.provisioner.key_manager import KeyManager
from cardlink.provisioner.models import APDUCommand, INS, PSKConfiguration

logger = logging.getLogger(__name__)


# Elementary File IDs for PSK storage
# These are vendor-specific and may need customization
EF_PSK_ID = "2F50"  # File for PSK identity (example location)
EF_PSK_KEY = "2F51"  # File for PSK key (example location)


class PSKConfig:
    """PSK configuration manager for UICC cards.

    Handles storing and retrieving Pre-Shared Key configuration
    on UICC cards for TLS-PSK authentication.

    The PSK configuration consists of:
    - Identity: A string identifier (stored in EF_PSK_ID)
    - Key: Binary key material (stored in EF_PSK_KEY)

    File Locations:
        The elementary files (EF) for storing PSK data are vendor-specific.
        Default locations:
        - EF_PSK_ID (2F50): PSK identity string
        - EF_PSK_KEY (2F51): PSK key bytes

    Security Note:
        PSK key storage should only be performed through a secure
        channel (SCP02/SCP03) to prevent key exposure.

    Example:
        >>> from cardlink.provisioner import PCSCClient, APDUInterface
        >>> from cardlink.provisioner.psk_config import PSKConfig
        >>> from cardlink.provisioner.models import PSKConfiguration
        >>>
        >>> # Connect to card
        >>> client = PCSCClient()
        >>> client.connect(client.list_readers()[0])
        >>> apdu = APDUInterface(client.transmit)
        >>>
        >>> # Create PSK configuration
        >>> psk = PSKConfiguration.generate("my_card_001", key_size=16)
        >>>
        >>> # Configure on card (requires secure channel)
        >>> psk_config = PSKConfig(apdu)
        >>> psk_config.configure(psk)
        >>>
        >>> # Read current configuration
        >>> current_psk = psk_config.read_configuration()
        >>> print(f"PSK Identity: {current_psk.identity}")
    """

    def __init__(
        self,
        apdu_interface: APDUInterface,
        secure_channel: Optional[Callable[[APDUCommand], bytes]] = None,
    ):
        """Initialize PSK configuration manager.

        Args:
            apdu_interface: APDU interface for card communication.
            secure_channel: Optional secure channel wrapper for
                           protected commands. If provided, all
                           PSK key write operations will use this.
        """
        self.apdu = apdu_interface
        self.secure_channel = secure_channel

    def configure(self, psk: PSKConfiguration) -> None:
        """Configure PSK on the card.

        Writes both PSK identity and key to the card.

        Args:
            psk: PSK configuration to store.

        Raises:
            SecurityError: If writing key without secure channel.
            ProfileError: If configuration fails.

        Example:
            >>> psk = PSKConfiguration.generate("card001", 16)
            >>> psk_config.configure(psk)
        """
        logger.info(f"Configuring PSK with identity: {psk.identity}")

        # Write PSK identity
        self._write_psk_identity(psk.identity)

        # Write PSK key (must use secure channel)
        self._write_psk_key(psk.key)

        logger.info("PSK configuration completed")

    def _write_psk_identity(self, identity: str) -> None:
        """Write PSK identity to card.

        Args:
            identity: PSK identity string.

        Raises:
            ProfileError: If write fails.
        """
        try:
            # Select PSK identity file
            self.apdu.select_by_path(EF_PSK_ID)

            # Convert identity to bytes (ASCII encoding)
            identity_bytes = identity.encode("ascii")

            # Update file with identity
            response = self.apdu.send(
                APDUCommand(
                    cla=0x00,
                    ins=INS.UPDATE_BINARY,
                    p1=0x00,
                    p2=0x00,
                    data=identity_bytes,
                )
            )

            if not response.is_success:
                raise ProfileError(
                    f"Failed to write PSK identity: {response.status_message}"
                )

            logger.debug(f"PSK identity written: {identity}")

        except Exception as e:
            logger.error(f"Failed to write PSK identity: {e}")
            raise ProfileError(f"Failed to write PSK identity: {e}") from e

    def _write_psk_key(self, key: bytes) -> None:
        """Write PSK key to card.

        This operation should only be performed through a secure
        channel to protect the key material.

        Args:
            key: PSK key bytes.

        Raises:
            SecurityError: If no secure channel is established.
            ProfileError: If write fails.
        """
        if self.secure_channel is None:
            raise SecurityError(
                "PSK key must be written through secure channel. "
                "Establish SCP02/SCP03 before writing keys."
            )

        try:
            # Select PSK key file
            self.apdu.select_by_path(EF_PSK_KEY)

            # Create update command
            command = APDUCommand(
                cla=0x84,  # Secure messaging CLA
                ins=INS.UPDATE_BINARY,
                p1=0x00,
                p2=0x00,
                data=key,
            )

            # Send through secure channel
            response_data = self.secure_channel(command)

            logger.debug(f"PSK key written ({len(key)} bytes)")
            logger.info("PSK key configured (not logging key material for security)")

        except Exception as e:
            logger.error(f"Failed to write PSK key: {e}")
            raise ProfileError(f"Failed to write PSK key: {e}") from e

    def read_configuration(self) -> PSKConfiguration:
        """Read current PSK configuration from card.

        Note:
            For security reasons, the PSK key cannot be read back
            from the card. This method only retrieves the identity.
            The returned PSKConfiguration will have an empty key.

        Returns:
            PSK configuration with identity (key will be empty).

        Raises:
            ProfileError: If read fails.

        Example:
            >>> psk = psk_config.read_configuration()
            >>> print(f"Current PSK Identity: {psk.identity}")
        """
        try:
            # Select and read PSK identity file
            self.apdu.select_by_path(EF_PSK_ID)

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
                    f"Failed to read PSK identity: {response.status_message}"
                )

            # Decode identity
            identity = response.data.decode("ascii").rstrip("\x00")

            logger.debug(f"Read PSK identity: {identity}")

            # Return configuration with empty key (cannot read key back)
            return PSKConfiguration(
                identity=identity,
                key=b"",  # Key cannot be read back for security
                key_size=0,
            )

        except Exception as e:
            logger.error(f"Failed to read PSK configuration: {e}")
            raise ProfileError(f"Failed to read PSK configuration: {e}") from e

    def verify(self, expected: PSKConfiguration) -> bool:
        """Verify PSK identity matches expected value.

        Note:
            Only the identity can be verified. The key cannot be
            read back from the card for security reasons.

        Args:
            expected: Expected PSK configuration.

        Returns:
            True if identity matches, False otherwise.

        Example:
            >>> psk = PSKConfiguration.generate("card001", 16)
            >>> psk_config.configure(psk)
            >>> assert psk_config.verify(psk)
        """
        current = self.read_configuration()
        return current.identity == expected.identity

    def _create_psk_file(self, file_id: str, size: int) -> None:
        """Create PSK elementary file if it doesn't exist.

        This is a vendor-specific operation and may need customization.

        Args:
            file_id: File identifier (e.g., "2F50").
            size: File size in bytes.

        Raises:
            ProfileError: If file creation fails.
        """
        try:
            # CREATE FILE command (vendor-specific)
            # This is a placeholder - actual implementation depends on card vendor
            logger.warning(
                f"CREATE FILE for {file_id} not implemented. "
                "File must exist on card or be created using vendor tools."
            )

        except Exception as e:
            logger.error(f"Failed to create PSK file {file_id}: {e}")
            raise ProfileError(f"Failed to create PSK file: {e}") from e
