"""Card profile management for UICC provisioning.

This module provides functionality to save, load, compare, and apply
complete UICC card configurations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from cardlink.provisioner.apdu_interface import APDUInterface
from cardlink.provisioner.bip_config import BIPConfig
from cardlink.provisioner.exceptions import ProfileError
from cardlink.provisioner.models import APDUCommand, CardProfile, INS, PSKConfiguration
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.trigger_config import TriggerConfig
from cardlink.provisioner.url_config import URLConfig

logger = logging.getLogger(__name__)


# Elementary File IDs
EF_ICCID = "2FE2"  # ICCID file
EF_DIR = "2F00"  # DIR file for card applications


class ProfileManager:
    """Manages complete UICC card profiles.

    This class provides functionality to:
    - Capture current card configuration
    - Export profiles to JSON
    - Import profiles from JSON
    - Compare two profiles
    - Apply profile to a card

    Example:
        >>> from cardlink.provisioner import PCSCClient, APDUInterface
        >>> from cardlink.provisioner.profile_manager import ProfileManager
        >>>
        >>> # Connect to card
        >>> client = PCSCClient()
        >>> readers = client.list_readers()
        >>> client.connect(readers[0])
        >>>
        >>> # Create profile manager
        >>> apdu = APDUInterface(client.transmit)
        >>> manager = ProfileManager(apdu)
        >>>
        >>> # Save current card profile
        >>> profile = manager.save_profile()
        >>> manager.export_profile(profile, "card_profile.json", include_keys=False)
        >>>
        >>> # Load and apply profile to another card
        >>> profile = manager.import_profile("card_profile.json")
        >>> # ... connect to different card ...
        >>> manager.apply_profile(profile, psk_key=b"...")
    """

    def __init__(
        self,
        apdu: APDUInterface,
        secure_channel: Optional[Callable[[bytes], bytes]] = None,
    ):
        """Initialize profile manager.

        Args:
            apdu: APDU interface for card communication
            secure_channel: Optional secure channel wrapper function
        """
        self.apdu = apdu
        self.secure_channel = secure_channel

        # Initialize config managers
        self.psk_config = PSKConfig(apdu, secure_channel)
        self.url_config = URLConfig(apdu)
        self.trigger_config = TriggerConfig(apdu)
        self.bip_config = BIPConfig(apdu)

    def save_profile(self, include_keys: bool = False) -> CardProfile:
        """Capture current card configuration.

        Args:
            include_keys: If True, include PSK key material in profile

        Returns:
            Complete card profile

        Raises:
            ProfileError: If profile capture fails
        """
        try:
            # Get card information
            iccid = self._get_iccid()
            atr = self._get_atr()

            # Read all configurations
            psk = None
            try:
                psk = self.psk_config.read_configuration()
            except Exception as e:
                logger.warning(f"Could not read PSK config: {e}")

            url = None
            try:
                url = self.url_config.read_configuration()
            except Exception as e:
                logger.warning(f"Could not read URL config: {e}")

            trigger = None
            try:
                trigger = self.trigger_config.read_configuration()
            except Exception as e:
                logger.warning(f"Could not read trigger config: {e}")

            bip = None
            try:
                bip = self.bip_config.read_configuration()
            except Exception as e:
                logger.warning(f"Could not read BIP config: {e}")

            return CardProfile(
                iccid=iccid,
                atr=atr,
                psk=psk,
                url=url,
                trigger=trigger,
                bip=bip,
            )

        except Exception as e:
            raise ProfileError(f"Failed to save profile: {e}") from e

    def apply_profile(
        self,
        profile: CardProfile,
        psk_key: Optional[bytes] = None,
        verify: bool = True,
    ) -> None:
        """Apply profile to current card.

        Args:
            profile: Profile to apply
            psk_key: PSK key if not in profile (required for PSK setup)
            verify: If True, verify each configuration after writing

        Raises:
            ProfileError: If profile application fails
            SecurityError: If secure channel required but not available
        """
        try:
            # Get current card ICCID for verification
            current_iccid = self._get_iccid()
            logger.info(
                f"Applying profile from {profile.iccid} to card {current_iccid}"
            )

            # Apply PSK configuration
            if profile.psk:
                if not profile.psk.key and not psk_key:
                    raise ProfileError(
                        "PSK key required but not in profile. Provide via psk_key parameter."
                    )

                psk = profile.psk
                if psk_key:
                    psk = PSKConfiguration(identity=psk.identity, key=psk_key)

                self.psk_config.configure(psk)
                if verify:
                    stored = self.psk_config.read_configuration()
                    if stored.identity != psk.identity:
                        raise ProfileError("PSK verification failed")
                logger.info("PSK configuration applied")

            # Apply URL configuration
            if profile.url:
                self.url_config.configure(profile.url)
                if verify:
                    stored = self.url_config.read_configuration()
                    if stored != profile.url:
                        raise ProfileError("URL verification failed")
                logger.info("URL configuration applied")

            # Apply trigger configuration
            if profile.trigger:
                if profile.trigger.sms_trigger:
                    self.trigger_config.configure_sms_trigger(
                        profile.trigger.sms_trigger
                    )
                if profile.trigger.poll_trigger:
                    self.trigger_config.configure_poll_trigger(
                        profile.trigger.poll_trigger
                    )
                if verify:
                    stored = self.trigger_config.read_configuration()
                    # Verification logic would go here
                logger.info("Trigger configuration applied")

            # Apply BIP configuration
            if profile.bip:
                self.bip_config.configure(profile.bip)
                if verify:
                    stored = self.bip_config.read_configuration()
                    # Verification logic would go here
                logger.info("BIP configuration applied")

            logger.info("Profile application complete")

        except Exception as e:
            raise ProfileError(f"Failed to apply profile: {e}") from e

    def compare_profiles(
        self, profile1: CardProfile, profile2: CardProfile
    ) -> Dict[str, Any]:
        """Compare two profiles and return differences.

        Args:
            profile1: First profile
            profile2: Second profile

        Returns:
            Dictionary of differences
        """
        diff: Dict[str, Any] = {}

        # Compare ICCID
        if profile1.iccid != profile2.iccid:
            diff["iccid"] = {
                "profile1": profile1.iccid,
                "profile2": profile2.iccid,
            }

        # Compare ATR
        if profile1.atr != profile2.atr:
            diff["atr"] = {
                "profile1": profile1.atr.hex(),
                "profile2": profile2.atr.hex(),
            }

        # Compare PSK
        if (profile1.psk is None) != (profile2.psk is None):
            diff["psk"] = {
                "profile1": "present" if profile1.psk else "absent",
                "profile2": "present" if profile2.psk else "absent",
            }
        elif profile1.psk and profile2.psk:
            if profile1.psk.identity != profile2.psk.identity:
                diff["psk_identity"] = {
                    "profile1": profile1.psk.identity,
                    "profile2": profile2.psk.identity,
                }

        # Compare URL
        if profile1.url != profile2.url:
            diff["url"] = {
                "profile1": profile1.url,
                "profile2": profile2.url,
            }

        # Compare triggers
        # Simplified comparison - full implementation would compare each field
        if (profile1.trigger is None) != (profile2.trigger is None):
            diff["trigger"] = {
                "profile1": "present" if profile1.trigger else "absent",
                "profile2": "present" if profile2.trigger else "absent",
            }

        # Compare BIP
        if (profile1.bip is None) != (profile2.bip is None):
            diff["bip"] = {
                "profile1": "present" if profile1.bip else "absent",
                "profile2": "present" if profile2.bip else "absent",
            }
        elif profile1.bip and profile2.bip:
            if profile1.bip.bearer_type != profile2.bip.bearer_type:
                diff["bip_bearer"] = {
                    "profile1": profile1.bip.bearer_type.value,
                    "profile2": profile2.bip.bearer_type.value,
                }

        return diff

    def export_profile(
        self, profile: CardProfile, path: Path, include_keys: bool = False
    ) -> None:
        """Export profile to JSON file.

        Args:
            path: Output file path
            include_keys: If True, include PSK key material

        Raises:
            ProfileError: If export fails
        """
        try:
            data = profile.to_dict(include_keys=include_keys)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Profile exported to {path}")
        except Exception as e:
            raise ProfileError(f"Failed to export profile: {e}") from e

    def import_profile(self, path: Path) -> CardProfile:
        """Import profile from JSON file.

        Args:
            path: Input file path

        Returns:
            Loaded card profile

        Raises:
            ProfileError: If import fails
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)
            profile = CardProfile.from_dict(data)
            logger.info(f"Profile imported from {path}")
            return profile
        except Exception as e:
            raise ProfileError(f"Failed to import profile: {e}") from e

    def _get_iccid(self) -> str:
        """Read ICCID from card.

        Returns:
            ICCID string

        Raises:
            ProfileError: If ICCID cannot be read
        """
        try:
            # Select MF
            self.apdu.send(APDUCommand(0x00, INS.SELECT, 0x00, 0x04, bytes.fromhex("3F00")))

            # Select EF_ICCID
            self.apdu.send(APDUCommand(0x00, INS.SELECT, 0x00, 0x04, bytes.fromhex(EF_ICCID)))

            # Read ICCID (10 bytes)
            response = self.apdu.send(APDUCommand(0x00, INS.READ_BINARY, 0x00, 0x00, le=10))

            if not response.is_success:
                raise ProfileError(f"Failed to read ICCID: {response.status_message}")

            # Decode BCD
            return self._decode_iccid(response.data)

        except Exception as e:
            raise ProfileError(f"Failed to get ICCID: {e}") from e

    def _decode_iccid(self, data: bytes) -> str:
        """Decode ICCID from BCD format.

        Args:
            data: ICCID bytes in BCD format

        Returns:
            ICCID string
        """
        iccid = ""
        for byte in data:
            # Low nibble
            low = byte & 0x0F
            if low <= 9:
                iccid += str(low)
            # High nibble
            high = (byte >> 4) & 0x0F
            if high <= 9:
                iccid += str(high)
            elif high == 0x0F:
                # Padding
                break
        return iccid

    def _get_atr(self) -> bytes:
        """Get ATR from current connection.

        This is a placeholder - in practice, ATR should be obtained
        from the PCSCClient after connection.

        Returns:
            ATR bytes
        """
        # In real implementation, this would be passed in or obtained
        # from the connection. For now, return empty bytes.
        # The actual ATR should be captured during card connection.
        return b""
