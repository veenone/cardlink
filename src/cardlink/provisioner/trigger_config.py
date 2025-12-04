"""Trigger configuration for OTA provisioning.

This module handles storage and retrieval of OTA (Over-The-Air) trigger
configuration on UICC cards for remote profile provisioning.
"""

import logging
from typing import Optional

from cardlink.provisioner.apdu_interface import APDUInterface
from cardlink.provisioner.exceptions import ProfileError
from cardlink.provisioner.models import (
    APDUCommand,
    INS,
    PollTriggerConfig,
    SMSTriggerConfig,
    TriggerConfiguration,
    TriggerType,
)
from cardlink.provisioner.tlv_parser import TLVParser

logger = logging.getLogger(__name__)


# Elementary File ID for trigger configuration storage
EF_TRIGGER_CONFIG = "2F53"  # File for trigger configuration (example location)

# TLV tags for trigger data
TAG_SMS_TRIGGER = 0x90
TAG_POLL_TRIGGER = 0x91
TAG_TAR = 0x01
TAG_ORIGINATING_ADDRESS = 0x02
TAG_KIC = 0x03
TAG_KID = 0x04
TAG_COUNTER = 0x05
TAG_POLL_INTERVAL = 0x06
TAG_POLL_ENABLED = 0x07


class TriggerConfig:
    """Trigger configuration manager for UICC cards.

    Handles storing and retrieving OTA trigger configuration on UICC cards
    for remote profile provisioning.

    Supported Triggers:
        - SMS-PP: SMS Push Protocol trigger with security parameters
        - Polling: Periodic polling trigger with configurable interval

    Storage Format:
        Triggers are stored in nested TLV format:
        - SMS Trigger (Tag 0x90):
            - TAR (Tag 0x01): 3 bytes
            - Originating Address (Tag 0x02): variable length
            - KIc (Tag 0x03): 1 byte
            - KId (Tag 0x04): 1 byte
            - Counter (Tag 0x05): 5 bytes
        - Poll Trigger (Tag 0x91):
            - Interval (Tag 0x06): 4 bytes (seconds)
            - Enabled (Tag 0x07): 1 byte (0x00/0x01)

    Example:
        >>> from cardlink.provisioner import PCSCClient, APDUInterface
        >>> from cardlink.provisioner.trigger_config import TriggerConfig
        >>> from cardlink.provisioner.models import SMSTriggerConfig
        >>>
        >>> # Connect to card
        >>> client = PCSCClient()
        >>> client.connect(client.list_readers()[0])
        >>> apdu = APDUInterface(client.transmit)
        >>>
        >>> # Create SMS trigger configuration
        >>> sms_trigger = SMSTriggerConfig(
        ...     tar=bytes.fromhex("000001"),
        ...     originating_address="+1234567890",
        ...     kic=bytes.fromhex("01"),
        ...     kid=bytes.fromhex("01"),
        ... )
        >>>
        >>> # Configure on card
        >>> trigger_config = TriggerConfig(apdu)
        >>> trigger_config.configure_sms_trigger(sms_trigger)
        >>>
        >>> # Read current configuration
        >>> current = trigger_config.read_configuration()
        >>> if current.sms_trigger:
        ...     print(f"SMS TAR: {current.sms_trigger.tar.hex()}")
    """

    def __init__(self, apdu_interface: APDUInterface):
        """Initialize trigger configuration manager.

        Args:
            apdu_interface: APDU interface for card communication.
        """
        self.apdu = apdu_interface

    def configure_sms_trigger(self, config: SMSTriggerConfig) -> None:
        """Configure SMS-PP trigger on the card.

        Args:
            config: SMS trigger configuration to store.

        Raises:
            ProfileError: If configuration fails.

        Example:
            >>> sms_config = SMSTriggerConfig(
            ...     tar=bytes.fromhex("000001"),
            ...     originating_address="+1234567890"
            ... )
            >>> trigger_config.configure_sms_trigger(sms_config)
        """
        logger.info(f"Configuring SMS trigger with TAR: {config.tar.hex()}")

        try:
            # Build nested TLV for SMS trigger
            sms_tlv = b""
            sms_tlv += TLVParser.build(TAG_TAR, config.tar)
            if config.originating_address:
                addr_bytes = config.originating_address.encode("ascii")
                sms_tlv += TLVParser.build(TAG_ORIGINATING_ADDRESS, addr_bytes)
            sms_tlv += TLVParser.build(TAG_KIC, config.kic)
            sms_tlv += TLVParser.build(TAG_KID, config.kid)
            sms_tlv += TLVParser.build(TAG_COUNTER, config.counter)

            # Wrap in SMS trigger tag
            trigger_tlv = TLVParser.build(TAG_SMS_TRIGGER, sms_tlv)

            # Write to card
            self._write_trigger_data(trigger_tlv)

            logger.info("SMS trigger configuration completed")

        except Exception as e:
            logger.error(f"Failed to configure SMS trigger: {e}")
            raise ProfileError(f"Failed to configure SMS trigger: {e}") from e

    def configure_poll_trigger(self, config: PollTriggerConfig) -> None:
        """Configure polling trigger on the card.

        Args:
            config: Poll trigger configuration to store.

        Raises:
            ProfileError: If configuration fails.

        Example:
            >>> poll_config = PollTriggerConfig(interval=3600, enabled=True)
            >>> trigger_config.configure_poll_trigger(poll_config)
        """
        logger.info(f"Configuring poll trigger: interval={config.interval}s, enabled={config.enabled}")

        try:
            # Build nested TLV for poll trigger
            poll_tlv = b""
            interval_bytes = config.interval.to_bytes(4, byteorder="big")
            poll_tlv += TLVParser.build(TAG_POLL_INTERVAL, interval_bytes)
            enabled_byte = bytes([0x01 if config.enabled else 0x00])
            poll_tlv += TLVParser.build(TAG_POLL_ENABLED, enabled_byte)

            # Wrap in poll trigger tag
            trigger_tlv = TLVParser.build(TAG_POLL_TRIGGER, poll_tlv)

            # Write to card
            self._write_trigger_data(trigger_tlv)

            logger.info("Poll trigger configuration completed")

        except Exception as e:
            logger.error(f"Failed to configure poll trigger: {e}")
            raise ProfileError(f"Failed to configure poll trigger: {e}") from e

    def read_configuration(self) -> TriggerConfiguration:
        """Read current trigger configuration from card.

        Returns:
            Current trigger configuration.

        Raises:
            ProfileError: If read fails or data is invalid.

        Example:
            >>> config = trigger_config.read_configuration()
            >>> if config.sms_trigger:
            ...     print(f"SMS TAR: {config.sms_trigger.tar.hex()}")
            >>> if config.poll_trigger:
            ...     print(f"Poll interval: {config.poll_trigger.interval}s")
        """
        try:
            # Select and read trigger configuration file
            self.apdu.select_by_path(EF_TRIGGER_CONFIG)

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
                    f"Failed to read trigger configuration: {response.status_message}"
                )

            # Parse TLV data
            config = self._parse_trigger_config(response.data)

            logger.debug("Read trigger configuration successfully")
            return config

        except Exception as e:
            logger.error(f"Failed to read trigger configuration: {e}")
            raise ProfileError(f"Failed to read trigger configuration: {e}") from e

    def disable_trigger(self, trigger_type: TriggerType) -> None:
        """Disable a specific trigger type.

        Args:
            trigger_type: Type of trigger to disable.

        Raises:
            ProfileError: If disable operation fails.

        Example:
            >>> trigger_config.disable_trigger(TriggerType.SMS)
        """
        logger.info(f"Disabling {trigger_type.value} trigger")

        try:
            # Read current configuration
            current = self.read_configuration()

            # Clear the specified trigger
            if trigger_type == TriggerType.SMS:
                current.sms_trigger = None
            elif trigger_type == TriggerType.POLL:
                current.poll_trigger = None

            # Write back modified configuration
            # Implementation would write the updated config back
            # For now, this is a placeholder
            logger.warning("Trigger disable not fully implemented - file rewrite needed")

        except Exception as e:
            logger.error(f"Failed to disable trigger: {e}")
            raise ProfileError(f"Failed to disable trigger: {e}") from e

    def _write_trigger_data(self, trigger_tlv: bytes) -> None:
        """Write trigger TLV data to card.

        Args:
            trigger_tlv: TLV-encoded trigger data.

        Raises:
            ProfileError: If write fails.
        """
        try:
            # Select trigger configuration file
            self.apdu.select_by_path(EF_TRIGGER_CONFIG)

            # Update file with TLV data
            response = self.apdu.send(
                APDUCommand(
                    cla=0x00,
                    ins=INS.UPDATE_BINARY,
                    p1=0x00,
                    p2=0x00,
                    data=trigger_tlv,
                )
            )

            if not response.is_success:
                raise ProfileError(
                    f"Failed to write trigger data: {response.status_message}"
                )

        except Exception as e:
            logger.error(f"Failed to write trigger data: {e}")
            raise ProfileError(f"Failed to write trigger data: {e}") from e

    def _parse_trigger_config(self, data: bytes) -> TriggerConfiguration:
        """Parse trigger configuration from TLV data.

        Args:
            data: TLV-encoded trigger data.

        Returns:
            Parsed trigger configuration.

        Raises:
            ProfileError: If parsing fails.
        """
        if not data or data == b"\x00" * len(data):
            # Empty or zeroed data
            return TriggerConfiguration()

        try:
            tlv_list = TLVParser.parse(data)
            sms_trigger = None
            poll_trigger = None

            for tlv in tlv_list:
                if tlv.tag == TAG_SMS_TRIGGER:
                    # Parse SMS trigger
                    sms_tlv_list = TLVParser.parse(tlv.value)
                    sms_data = {}
                    for sms_tlv in sms_tlv_list:
                        if sms_tlv.tag == TAG_TAR:
                            sms_data["tar"] = sms_tlv.value
                        elif sms_tlv.tag == TAG_ORIGINATING_ADDRESS:
                            sms_data["originating_address"] = sms_tlv.value.decode(
                                "ascii"
                            ).rstrip("\x00")
                        elif sms_tlv.tag == TAG_KIC:
                            sms_data["kic"] = sms_tlv.value
                        elif sms_tlv.tag == TAG_KID:
                            sms_data["kid"] = sms_tlv.value
                        elif sms_tlv.tag == TAG_COUNTER:
                            sms_data["counter"] = sms_tlv.value

                    if "tar" in sms_data:
                        sms_trigger = SMSTriggerConfig(**sms_data)

                elif tlv.tag == TAG_POLL_TRIGGER:
                    # Parse poll trigger
                    poll_tlv_list = TLVParser.parse(tlv.value)
                    poll_data = {}
                    for poll_tlv in poll_tlv_list:
                        if poll_tlv.tag == TAG_POLL_INTERVAL:
                            poll_data["interval"] = int.from_bytes(
                                poll_tlv.value, byteorder="big"
                            )
                        elif poll_tlv.tag == TAG_POLL_ENABLED:
                            poll_data["enabled"] = poll_tlv.value[0] == 0x01

                    if "interval" in poll_data:
                        poll_trigger = PollTriggerConfig(**poll_data)

            return TriggerConfiguration(
                sms_trigger=sms_trigger, poll_trigger=poll_trigger
            )

        except Exception as e:
            logger.error(f"Failed to parse trigger configuration: {e}")
            raise ProfileError(f"Failed to parse trigger configuration: {e}") from e
