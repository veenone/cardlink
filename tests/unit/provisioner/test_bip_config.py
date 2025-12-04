"""Unit tests for BIP configuration module."""

import pytest
from unittest.mock import Mock

from cardlink.provisioner.bip_config import BIPConfig, EF_BIP_CONFIG
from cardlink.provisioner.models import BIPConfiguration, BearerType, APDUResponse
from cardlink.provisioner.exceptions import ProfileError


class TestBIPConfiguration:
    """Test BIP configuration model."""

    def test_create_bip_configuration(self):
        """Test creating BIP configuration."""
        config = BIPConfiguration(
            bearer_type=BearerType.GPRS,
            apn="internet.example.com",
            buffer_size=1400,
            timeout=30,
        )

        assert config.bearer_type == BearerType.GPRS
        assert config.apn == "internet.example.com"
        assert config.buffer_size == 1400
        assert config.timeout == 30

    def test_default_values(self):
        """Test default BIP configuration values."""
        config = BIPConfiguration()

        assert config.bearer_type == BearerType.DEFAULT
        assert config.apn == ""
        assert config.buffer_size == 1400
        assert config.timeout == 30
        assert config.user_login is None
        assert config.user_password is None

    def test_buffer_size_validation(self):
        """Test buffer size validation."""
        with pytest.raises(ValueError) as exc_info:
            BIPConfiguration(buffer_size=0)

        assert "Buffer size must be between 1 and 65535" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            BIPConfiguration(buffer_size=70000)

        assert "Buffer size must be between 1 and 65535" in str(exc_info.value)

    def test_timeout_validation(self):
        """Test timeout validation."""
        with pytest.raises(ValueError) as exc_info:
            BIPConfiguration(timeout=0)

        assert "Timeout must be at least 1 second" in str(exc_info.value)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = BIPConfiguration(
            bearer_type=BearerType.GPRS,
            apn="internet.example.com",
            user_login="user1",
            user_password="secret",
        )
        result = config.to_dict()

        assert result["bearer_type"] == "GPRS"
        assert result["apn"] == "internet.example.com"
        assert result["user_login"] == "user1"
        assert result["user_password"] == "***"  # Password masked

    def test_encode_apn(self):
        """Test APN DNS label encoding."""
        # Simple APN
        result = BIPConfiguration._encode_apn("internet")
        assert result == b"\x08internet"

        # Multi-label APN
        result = BIPConfiguration._encode_apn("internet.example.com")
        expected = b"\x08internet\x07example\x03com"
        assert result == expected

        # Empty APN
        result = BIPConfiguration._encode_apn("")
        assert result == b""

    def test_encode_apn_invalid(self):
        """Test APN encoding with invalid input."""
        # Label too long
        with pytest.raises(ValueError) as exc_info:
            BIPConfiguration._encode_apn("a" * 64 + ".example.com")

        assert "Invalid APN label" in str(exc_info.value)

    def test_decode_apn(self):
        """Test APN DNS label decoding."""
        # Simple APN
        data = b"\x08internet"
        result = BIPConfiguration._decode_apn(data)
        assert result == "internet"

        # Multi-label APN
        data = b"\x08internet\x07example\x03com"
        result = BIPConfiguration._decode_apn(data)
        assert result == "internet.example.com"

        # Empty APN
        result = BIPConfiguration._decode_apn(b"")
        assert result == ""

        # APN with null terminator
        data = b"\x08internet\x00"
        result = BIPConfiguration._decode_apn(data)
        assert result == "internet"

    def test_to_tlv(self):
        """Test BIP configuration TLV encoding."""
        config = BIPConfiguration(
            bearer_type=BearerType.GPRS, apn="internet", buffer_size=1400, timeout=30
        )

        tlv_data = config.to_tlv()

        # Should contain multiple TLV structures
        assert len(tlv_data) > 0
        # Bearer type tag (0x80)
        assert b"\x80" in tlv_data
        # APN tag (0x81)
        assert b"\x81" in tlv_data
        # Buffer size tag (0x82)
        assert b"\x82" in tlv_data

    def test_to_tlv_with_credentials(self):
        """Test TLV encoding with user credentials."""
        config = BIPConfiguration(
            bearer_type=BearerType.GPRS,
            apn="internet",
            user_login="user1",
            user_password="secret",
        )

        tlv_data = config.to_tlv()

        # Should contain credential tags
        assert b"\x84" in tlv_data  # User login tag
        assert b"\x85" in tlv_data  # User password tag


class TestBIPConfig:
    """Test BIP config functionality."""

    @pytest.fixture
    def mock_apdu(self):
        """Create mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()
        apdu.send = Mock()
        return apdu

    @pytest.fixture
    def bip_config(self, mock_apdu):
        """Create BIP config instance."""
        return BIPConfig(mock_apdu)

    def test_init(self, mock_apdu):
        """Test BIP config initialization."""
        config = BIPConfig(mock_apdu)
        assert config.apdu == mock_apdu

    def test_configure(self, bip_config):
        """Test configuring BIP."""
        bip_conf = BIPConfiguration(
            bearer_type=BearerType.GPRS, apn="internet.example.com"
        )

        bip_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x90, sw2=0x00
        )

        bip_config.configure(bip_conf)

        # Verify file was selected
        bip_config.apdu.select_by_path.assert_called_with(EF_BIP_CONFIG)

        # Verify data was written
        assert bip_config.apdu.send.called
        call_args = bip_config.apdu.send.call_args
        command = call_args[0][0]
        assert len(command.data) > 0  # TLV encoded data

    def test_configure_failure(self, bip_config):
        """Test BIP configuration failure."""
        bip_conf = BIPConfiguration(bearer_type=BearerType.GPRS, apn="internet")

        bip_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82  # File not found
        )

        with pytest.raises(ProfileError) as exc_info:
            bip_config.configure(bip_conf)

        assert "Failed to configure BIP" in str(exc_info.value)

    def test_read_empty_configuration(self, bip_config):
        """Test reading empty BIP configuration."""
        bip_config.apdu.send.return_value = APDUResponse(
            data=b"\x00" * 10, sw1=0x90, sw2=0x00  # Zeroed data
        )

        result = bip_config.read_configuration()

        # Should return default configuration
        assert result.bearer_type == BearerType.DEFAULT
        assert result.apn == ""

    def test_read_configuration_failure(self, bip_config):
        """Test read configuration failure."""
        bip_config.apdu.send.return_value = APDUResponse(
            data=b"", sw1=0x6A, sw2=0x82
        )

        with pytest.raises(ProfileError) as exc_info:
            bip_config.read_configuration()

        assert "Failed to read BIP configuration" in str(exc_info.value)

    def test_check_terminal_support(self, bip_config):
        """Test checking terminal BIP support."""
        # Currently returns True as placeholder
        result = bip_config.check_terminal_support()

        assert result is True  # Placeholder implementation


class TestBIPConfigIntegration:
    """Integration tests for BIP configuration."""

    @pytest.fixture
    def mock_apdu_full(self):
        """Create full mock APDU interface."""
        apdu = Mock()
        apdu.select_by_path = Mock()
        apdu.send = Mock(return_value=APDUResponse(data=b"", sw1=0x90, sw2=0x00))
        return apdu

    def test_full_bip_workflow(self, mock_apdu_full):
        """Test complete BIP configuration workflow."""
        config = BIPConfig(mock_apdu_full)

        # Create BIP configuration
        bip_conf = BIPConfiguration(
            bearer_type=BearerType.GPRS,
            apn="internet.example.com",
            buffer_size=1400,
            timeout=30,
        )

        # Configure BIP
        config.configure(bip_conf)

        # Verify operations
        assert mock_apdu_full.select_by_path.called
        assert mock_apdu_full.send.called

    def test_configure_with_credentials(self, mock_apdu_full):
        """Test BIP configuration with user credentials."""
        config = BIPConfig(mock_apdu_full)

        # Create BIP configuration with credentials
        bip_conf = BIPConfiguration(
            bearer_type=BearerType.GPRS,
            apn="internet.example.com",
            user_login="user1",
            user_password="secret",
        )

        # Configure BIP
        config.configure(bip_conf)

        # Verify configuration was written
        call_args = mock_apdu_full.send.call_args
        command = call_args[0][0]

        # Verify TLV data contains credentials
        assert b"user1" in command.data
        assert b"secret" in command.data

    def test_different_bearer_types(self, mock_apdu_full):
        """Test configuring different bearer types."""
        config = BIPConfig(mock_apdu_full)

        bearer_types = [
            BearerType.GPRS,
            BearerType.UTRAN,
            BearerType.EUTRAN,
            BearerType.WIFI,
        ]

        for bearer in bearer_types:
            bip_conf = BIPConfiguration(
                bearer_type=bearer, apn=f"{bearer.name.lower()}.apn"
            )

            config.configure(bip_conf)

            # Verify each was configured
            assert mock_apdu_full.send.called
