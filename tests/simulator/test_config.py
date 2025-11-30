"""Tests for simulator configuration."""

import pytest
from cardlink.simulator import SimulatorConfig, BehaviorConfig, UICCProfile, BehaviorMode, ConnectionMode


class TestSimulatorConfig:
    """Test SimulatorConfig validation and loading."""

    def test_default_config(self):
        """Test default configuration."""
        config = SimulatorConfig()

        assert config.server_host == "127.0.0.1"
        assert config.server_port == 8443
        assert config.psk_identity == "test_card"
        assert len(config.psk_key) == 16

    def test_config_validation_success(self):
        """Test valid configuration passes validation."""
        config = SimulatorConfig(
            server_host="192.168.1.100",
            server_port=8443,
            psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10"),
        )
        config.validate()  # Should not raise

    def test_invalid_server_host(self):
        """Test empty server host fails validation."""
        config = SimulatorConfig(server_host="")

        with pytest.raises(ValueError, match="server_host cannot be empty"):
            config.validate()

    def test_invalid_server_port(self):
        """Test invalid server port fails validation."""
        config = SimulatorConfig(server_port=0)

        with pytest.raises(ValueError, match="Invalid server_port"):
            config.validate()

        config = SimulatorConfig(server_port=70000)

        with pytest.raises(ValueError, match="Invalid server_port"):
            config.validate()

    def test_invalid_timeout(self):
        """Test invalid timeout fails validation."""
        config = SimulatorConfig(connect_timeout=0)

        with pytest.raises(ValueError, match="Invalid connect_timeout"):
            config.validate()

        config = SimulatorConfig(read_timeout=-1)

        with pytest.raises(ValueError, match="Invalid read_timeout"):
            config.validate()

    def test_invalid_psk_identity(self):
        """Test empty PSK identity fails validation."""
        config = SimulatorConfig(psk_identity="")

        with pytest.raises(ValueError, match="psk_identity cannot be empty"):
            config.validate()

    def test_invalid_psk_key_length(self):
        """Test invalid PSK key length fails validation."""
        # 8 bytes (too short)
        config = SimulatorConfig(psk_key=b"\x00" * 8)

        with pytest.raises(ValueError, match="psk_key must be 16 or 32 bytes"):
            config.validate()

        # 24 bytes (invalid)
        config = SimulatorConfig(psk_key=b"\x00" * 24)

        with pytest.raises(ValueError, match="psk_key must be 16 or 32 bytes"):
            config.validate()

    def test_valid_psk_key_lengths(self):
        """Test valid PSK key lengths."""
        # 16 bytes
        config = SimulatorConfig(psk_key=b"\x00" * 16)
        config.validate()

        # 32 bytes
        config = SimulatorConfig(psk_key=b"\x00" * 32)
        config.validate()

    def test_server_address_property(self):
        """Test server_address property."""
        config = SimulatorConfig(server_host="192.168.1.100", server_port=8443)

        assert config.server_address == "192.168.1.100:8443"

    def test_psk_key_hex_property(self):
        """Test psk_key_hex property."""
        key = bytes.fromhex("0102030405060708090A0B0C0D0E0F10")
        config = SimulatorConfig(psk_key=key)

        assert config.psk_key_hex == "0102030405060708090A0B0C0D0E0F10"

    def test_from_dict_basic(self):
        """Test creating config from dictionary."""
        data = {
            "server": {
                "host": "192.168.1.100",
                "port": 9443,
            },
            "psk": {
                "identity": "card_001",
                "key": "0102030405060708090A0B0C0D0E0F10",
            },
        }

        config = SimulatorConfig.from_dict(data)

        assert config.server_host == "192.168.1.100"
        assert config.server_port == 9443
        assert config.psk_identity == "card_001"
        assert config.psk_key == bytes.fromhex("0102030405060708090A0B0C0D0E0F10")

    def test_from_dict_uicc_profile(self):
        """Test loading UICC profile from dictionary."""
        data = {
            "uicc": {
                "iccid": "8901234567890123456",
                "imsi": "310150123456789",
                "gp": {
                    "version": "2.2.1",
                    "scp_version": "03",
                    "isd_aid": "A000000151000000",
                },
                "applets": [
                    {
                        "aid": "A0000001510001",
                        "name": "TestApplet",
                        "state": "SELECTABLE",
                    }
                ],
            }
        }

        config = SimulatorConfig.from_dict(data)

        assert config.uicc_profile.iccid == "8901234567890123456"
        assert config.uicc_profile.imsi == "310150123456789"
        assert config.uicc_profile.gp_version == "2.2.1"
        assert len(config.uicc_profile.applets) == 1
        assert config.uicc_profile.applets[0].aid == "A0000001510001"

    def test_from_dict_behavior(self):
        """Test loading behavior config from dictionary."""
        data = {
            "behavior": {
                "mode": "error",
                "error": {
                    "rate": 0.1,
                    "codes": ["6A82", "6985"],
                },
                "timeout": {
                    "probability": 0.2,
                    "delay_range": {
                        "min": 1000,
                        "max": 5000,
                    },
                },
            }
        }

        config = SimulatorConfig.from_dict(data)

        assert config.behavior.mode == BehaviorMode.ERROR
        assert config.behavior.error_rate == 0.1
        assert config.behavior.error_codes == ["6A82", "6985"]
        assert config.behavior.timeout_probability == 0.2
        assert config.behavior.timeout_delay_min_ms == 1000
        assert config.behavior.timeout_delay_max_ms == 5000


class TestBehaviorConfig:
    """Test BehaviorConfig."""

    def test_default_config(self):
        """Test default behavior configuration."""
        config = BehaviorConfig()

        assert config.mode == BehaviorMode.NORMAL
        assert config.error_rate == 0.0
        assert config.timeout_probability == 0.0

    def test_error_mode_config(self):
        """Test error mode configuration."""
        config = BehaviorConfig(
            mode=BehaviorMode.ERROR,
            error_rate=0.5,
            error_codes=["6A82"],
        )

        assert config.mode == BehaviorMode.ERROR
        assert config.error_rate == 0.5
        assert config.error_codes == ["6A82"]


class TestUICCProfile:
    """Test UICCProfile."""

    def test_default_profile(self):
        """Test default UICC profile."""
        profile = UICCProfile()

        assert profile.iccid == "8901234567890123456"
        assert profile.aid_isd == "A000000151000000"
        assert profile.gp_version == "2.2.1"
        assert len(profile.applets) == 0

    def test_custom_profile(self):
        """Test custom UICC profile."""
        from cardlink.simulator import VirtualApplet

        profile = UICCProfile(
            iccid="8901111111111111111",
            imsi="310150987654321",
            applets=[
                VirtualApplet(aid="A0000001510001", name="TestApplet")
            ],
        )

        assert profile.iccid == "8901111111111111111"
        assert profile.imsi == "310150987654321"
        assert len(profile.applets) == 1
