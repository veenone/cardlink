"""Unit tests for PSK configuration module."""

import pytest
from unittest.mock import Mock, MagicMock

from cardlink.provisioner.psk_config import PSKConfig, EF_PSK_ID, EF_PSK_KEY
from cardlink.provisioner.models import PSKConfiguration, APDUResponse
from cardlink.provisioner.exceptions import SecurityError, ProfileError


class TestPSKConfig:
    """Test PSK configuration functionality."""

    @pytest.fixture
    def mock_apdu(self):
        """Create mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()
        apdu.send = Mock()
        return apdu

    @pytest.fixture
    def psk_config(self, mock_apdu):
        """Create PSK config instance."""
        return PSKConfig(mock_apdu)

    @pytest.fixture
    def psk_config_with_secure_channel(self, mock_apdu):
        """Create PSK config with secure channel."""
        secure_channel = Mock(return_value=b"\x90\x00")
        return PSKConfig(mock_apdu, secure_channel=secure_channel)

    def test_init(self, mock_apdu):
        """Test PSK config initialization."""
        config = PSKConfig(mock_apdu)
        assert config.apdu == mock_apdu
        assert config.secure_channel is None

    def test_init_with_secure_channel(self, mock_apdu):
        """Test initialization with secure channel."""
        secure_channel = Mock()
        config = PSKConfig(mock_apdu, secure_channel=secure_channel)
        assert config.apdu == mock_apdu
        assert config.secure_channel == secure_channel

    def test_configure_without_secure_channel_fails(self, psk_config):
        """Test that configuring PSK without secure channel fails."""
        psk = PSKConfiguration.generate("test_identity", 16)

        with pytest.raises(SecurityError) as exc_info:
            psk_config.configure(psk)

        assert "secure channel" in str(exc_info.value).lower()

    def test_configure_success(self, psk_config_with_secure_channel):
        """Test successful PSK configuration."""
        psk = PSKConfiguration.generate("test_identity", 16)

        # Mock successful responses
        psk_config_with_secure_channel.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        psk_config_with_secure_channel.configure(psk)

        # Verify select calls
        assert psk_config_with_secure_channel.apdu.select_by_path.call_count == 2
        psk_config_with_secure_channel.apdu.select_by_path.assert_any_call(EF_PSK_ID)
        psk_config_with_secure_channel.apdu.select_by_path.assert_any_call(EF_PSK_KEY)

        # Verify identity was written
        assert psk_config_with_secure_channel.apdu.send.called

        # Verify secure channel was used for key
        assert psk_config_with_secure_channel.secure_channel.called

    def test_write_psk_identity(self, psk_config_with_secure_channel):
        """Test writing PSK identity."""
        identity = "test_card_001"

        psk_config_with_secure_channel.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        psk_config_with_secure_channel._write_psk_identity(identity)

        # Verify file was selected
        psk_config_with_secure_channel.apdu.select_by_path.assert_called_with(
            EF_PSK_ID
        )

        # Verify identity was written
        call_args = psk_config_with_secure_channel.apdu.send.call_args
        command = call_args[0][0]
        assert command.data == identity.encode("ascii")

    def test_write_psk_identity_failure(self, psk_config_with_secure_channel):
        """Test write identity failure handling."""
        identity = "test_card_001"

        psk_config_with_secure_channel.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82  # File not found
        )

        with pytest.raises(ProfileError) as exc_info:
            psk_config_with_secure_channel._write_psk_identity(identity)

        assert "Failed to write PSK identity" in str(exc_info.value)

    def test_read_configuration(self, psk_config):
        """Test reading PSK configuration."""
        identity = "test_card_001"
        identity_data = identity.encode("ascii") + b"\x00" * 10  # Padded

        psk_config.apdu.send.return_value = APDUResponse(
            data=identity_data, sw1=0x90, sw2=0x00
        )

        result = psk_config.read_configuration()

        # Verify file was selected
        psk_config.apdu.select_by_path.assert_called_with(EF_PSK_ID)

        # Verify returned configuration
        assert result.identity == identity
        assert result.key == b""  # Key cannot be read back
        assert result.key_size == 0

    def test_read_configuration_failure(self, psk_config):
        """Test read configuration failure handling."""
        psk_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82  # File not found
        )

        with pytest.raises(ProfileError) as exc_info:
            psk_config.read_configuration()

        assert "Failed to read PSK" in str(exc_info.value)

    def test_verify_success(self, psk_config):
        """Test PSK verification success."""
        identity = "test_card_001"
        expected = PSKConfiguration(identity=identity, key=b"\x00" * 16, key_size=16)

        psk_config.apdu.send.return_value = APDUResponse(
            data=identity.encode("ascii"), sw1=0x90, sw2=0x00
        )

        assert psk_config.verify(expected) is True

    def test_verify_failure(self, psk_config):
        """Test PSK verification failure."""
        expected = PSKConfiguration(
            identity="test_card_001", key=b"\x00" * 16, key_size=16
        )

        psk_config.apdu.send.return_value = APDUResponse(
            data=b"different_identity", sw1=0x90, sw2=0x00
        )

        assert psk_config.verify(expected) is False


class TestPSKConfigIntegration:
    """Integration tests for PSK configuration."""

    @pytest.fixture
    def mock_apdu_full(self):
        """Create full mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()

        # Mock successful responses
        def send_side_effect(command):
            return APDUResponse(data=b"", sw1=0x90, sw2=0x00)

        apdu.send = Mock(side_effect=send_side_effect)
        return apdu

    def test_full_configuration_workflow(self, mock_apdu_full):
        """Test complete PSK configuration workflow."""
        # Create PSK configuration
        psk = PSKConfiguration.generate("test_card_001", 16)

        # Create config manager with secure channel
        secure_channel = Mock(return_value=b"\x90\x00")
        config = PSKConfig(mock_apdu_full, secure_channel=secure_channel)

        # Configure PSK
        config.configure(psk)

        # Verify operations
        assert mock_apdu_full.select_by_path.call_count == 2
        assert mock_apdu_full.send.called
        assert secure_channel.called

    def test_read_after_write(self):
        """Test reading PSK after writing."""
        identity = "test_card_001"
        psk = PSKConfiguration(identity=identity, key=b"\x00" * 16, key_size=16)

        # Create mock with side effects for different calls
        mock_apdu = Mock()
        mock_apdu.select_by_path = Mock()

        # First calls (for write) return success
        # Next calls (for read and verify) return the identity data
        mock_apdu.send = Mock(
            side_effect=[
                APDUResponse(data=b"", sw1=0x90, sw2=0x00),  # Write identity
                APDUResponse(
                    data=identity.encode("ascii"), sw1=0x90, sw2=0x00
                ),  # Read identity
                APDUResponse(
                    data=identity.encode("ascii"), sw1=0x90, sw2=0x00
                ),  # Verify (reads identity again)
            ]
        )

        secure_channel = Mock(return_value=b"\x90\x00")
        config = PSKConfig(mock_apdu, secure_channel=secure_channel)

        # Write PSK
        config.configure(psk)

        # Read PSK
        result = config.read_configuration()

        assert result.identity == identity
        assert config.verify(psk) is True
