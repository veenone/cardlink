"""Unit tests for trigger configuration module."""

import pytest
from unittest.mock import Mock

from cardlink.provisioner.trigger_config import TriggerConfig, EF_TRIGGER_CONFIG
from cardlink.provisioner.models import (
    SMSTriggerConfig,
    PollTriggerConfig,
    TriggerConfiguration,
    TriggerType,
    APDUResponse,
)
from cardlink.provisioner.exceptions import ProfileError


class TestSMSTriggerConfig:
    """Test SMS trigger configuration model."""

    def test_create_sms_trigger(self):
        """Test creating SMS trigger configuration."""
        tar = bytes.fromhex("000001")
        config = SMSTriggerConfig(
            tar=tar,
            originating_address="+1234567890",
            kic=bytes.fromhex("01"),
            kid=bytes.fromhex("01"),
        )

        assert config.tar == tar
        assert config.originating_address == "+1234567890"
        assert config.kic == bytes.fromhex("01")
        assert config.kid == bytes.fromhex("01")
        assert len(config.counter) == 5

    def test_tar_validation(self):
        """Test TAR length validation."""
        with pytest.raises(ValueError) as exc_info:
            SMSTriggerConfig(tar=bytes.fromhex("0001"))  # Only 2 bytes

        assert "TAR must be 3 bytes" in str(exc_info.value)

    def test_counter_validation(self):
        """Test counter length validation."""
        with pytest.raises(ValueError) as exc_info:
            SMSTriggerConfig(
                tar=bytes.fromhex("000001"), counter=bytes.fromhex("00000000")  # 4 bytes
            )

        assert "Counter must be 5 bytes" in str(exc_info.value)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = SMSTriggerConfig(tar=bytes.fromhex("000001"))
        result = config.to_dict()

        assert result["tar"] == "000001"
        assert "kic" in result
        assert "kid" in result


class TestPollTriggerConfig:
    """Test polling trigger configuration model."""

    def test_create_poll_trigger(self):
        """Test creating poll trigger configuration."""
        config = PollTriggerConfig(interval=3600, enabled=True)

        assert config.interval == 3600
        assert config.enabled is True

    def test_default_values(self):
        """Test default poll trigger values."""
        config = PollTriggerConfig()

        assert config.interval == 3600  # Default 1 hour
        assert config.enabled is False

    def test_interval_validation(self):
        """Test polling interval validation."""
        with pytest.raises(ValueError) as exc_info:
            PollTriggerConfig(interval=30)  # Too short

        assert "at least 60 seconds" in str(exc_info.value)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = PollTriggerConfig(interval=7200, enabled=True)
        result = config.to_dict()

        assert result["interval"] == 7200
        assert result["enabled"] is True


class TestTriggerConfig:
    """Test trigger configuration functionality."""

    @pytest.fixture
    def mock_apdu(self):
        """Create mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()
        apdu.send = Mock()
        return apdu

    @pytest.fixture
    def trigger_config(self, mock_apdu):
        """Create trigger config instance."""
        return TriggerConfig(mock_apdu)

    def test_init(self, mock_apdu):
        """Test trigger config initialization."""
        config = TriggerConfig(mock_apdu)
        assert config.apdu == mock_apdu

    def test_configure_sms_trigger(self, trigger_config):
        """Test configuring SMS trigger."""
        sms_trigger = SMSTriggerConfig(
            tar=bytes.fromhex("000001"), originating_address="+1234567890"
        )

        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        trigger_config.configure_sms_trigger(sms_trigger)

        # Verify file was selected
        trigger_config.apdu.select_by_path.assert_called_with(EF_TRIGGER_CONFIG)

        # Verify data was written
        assert trigger_config.apdu.send.called
        call_args = trigger_config.apdu.send.call_args
        command = call_args[0][0]
        assert len(command.data) > 0  # TLV encoded data

    def test_configure_sms_trigger_failure(self, trigger_config):
        """Test SMS trigger configuration failure."""
        sms_trigger = SMSTriggerConfig(tar=bytes.fromhex("000001"))

        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82  # File not found
        )

        with pytest.raises(ProfileError) as exc_info:
            trigger_config.configure_sms_trigger(sms_trigger)

        assert "Failed to configure SMS trigger" in str(exc_info.value)

    def test_configure_poll_trigger(self, trigger_config):
        """Test configuring poll trigger."""
        poll_trigger = PollTriggerConfig(interval=3600, enabled=True)

        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        trigger_config.configure_poll_trigger(poll_trigger)

        # Verify file was selected
        trigger_config.apdu.select_by_path.assert_called_with(EF_TRIGGER_CONFIG)

        # Verify data was written
        assert trigger_config.apdu.send.called

    def test_configure_poll_trigger_failure(self, trigger_config):
        """Test poll trigger configuration failure."""
        poll_trigger = PollTriggerConfig(interval=3600, enabled=True)

        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82
        )

        with pytest.raises(ProfileError) as exc_info:
            trigger_config.configure_poll_trigger(poll_trigger)

        assert "Failed to configure poll trigger" in str(exc_info.value)

    def test_read_empty_configuration(self, trigger_config):
        """Test reading empty trigger configuration."""
        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"\x00" * 10, sw1=0x90, sw2=0x00  # Zeroed data
        )

        result = trigger_config.read_configuration()

        assert result.sms_trigger is None
        assert result.poll_trigger is None

    def test_read_configuration_failure(self, trigger_config):
        """Test read configuration failure."""
        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82
        )

        with pytest.raises(ProfileError) as exc_info:
            trigger_config.read_configuration()

        assert "Failed to read trigger configuration" in str(exc_info.value)

    def test_disable_trigger(self, trigger_config):
        """Test disabling trigger."""
        # Mock current configuration with SMS trigger
        sms_trigger = SMSTriggerConfig(tar=bytes.fromhex("000001"))
        current_config = TriggerConfiguration(sms_trigger=sms_trigger)

        # Mock read to return current config
        # This is a placeholder - full implementation would need TLV encoding
        trigger_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        # Disable SMS trigger
        trigger_config.disable_trigger(TriggerType.SMS)

        # Verify operation was attempted
        assert trigger_config.apdu.select_by_path.called


class TestTriggerConfigIntegration:
    """Integration tests for trigger configuration."""

    @pytest.fixture
    def mock_apdu_full(self):
        """Create full mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()
        apdu.send = Mock(return_value=APDUResponse(data=b"", sw1=0x90, sw2=0x00))
        return apdu

    def test_sms_trigger_workflow(self, mock_apdu_full):
        """Test complete SMS trigger workflow."""
        config = TriggerConfig(mock_apdu_full)

        # Create and configure SMS trigger
        sms_trigger = SMSTriggerConfig(
            tar=bytes.fromhex("000001"),
            originating_address="+1234567890",
            kic=bytes.fromhex("01"),
            kid=bytes.fromhex("01"),
        )

        config.configure_sms_trigger(sms_trigger)

        # Verify operations
        assert mock_apdu_full.select_by_path.called
        assert mock_apdu_full.send.called

    def test_poll_trigger_workflow(self, mock_apdu_full):
        """Test complete poll trigger workflow."""
        config = TriggerConfig(mock_apdu_full)

        # Create and configure poll trigger
        poll_trigger = PollTriggerConfig(interval=7200, enabled=True)

        config.configure_poll_trigger(poll_trigger)

        # Verify operations
        assert mock_apdu_full.select_by_path.called
        assert mock_apdu_full.send.called
