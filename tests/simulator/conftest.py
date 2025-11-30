"""Pytest fixtures for simulator tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from cardlink.simulator import (
    SimulatorConfig,
    BehaviorConfig,
    UICCProfile,
    BehaviorMode,
    VirtualApplet,
)


@pytest.fixture
def default_config():
    """Default simulator configuration for testing."""
    return SimulatorConfig(
        server_host="127.0.0.1",
        server_port=8443,
        psk_identity="test_card",
        psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10"),
        connect_timeout=5.0,
        read_timeout=5.0,
        retry_count=2,
        retry_backoff=[0.1, 0.2],
    )


@pytest.fixture
def uicc_profile():
    """Default UICC profile for testing."""
    return UICCProfile(
        iccid="8901234567890123456",
        imsi="310150123456789",
        aid_isd="A000000151000000",
        applets=[
            VirtualApplet(
                aid="A0000001510001",
                name="TestApplet",
                state="SELECTABLE",
            )
        ],
    )


@pytest.fixture
def behavior_config_normal():
    """Normal behavior configuration."""
    return BehaviorConfig(mode=BehaviorMode.NORMAL)


@pytest.fixture
def behavior_config_error():
    """Error injection behavior configuration."""
    return BehaviorConfig(
        mode=BehaviorMode.ERROR,
        error_rate=0.5,
        error_codes=["6A82", "6985"],
    )


@pytest.fixture
def behavior_config_timeout():
    """Timeout simulation behavior configuration."""
    return BehaviorConfig(
        mode=BehaviorMode.TIMEOUT,
        timeout_probability=0.5,
        timeout_delay_min_ms=100,
        timeout_delay_max_ms=200,
    )


@pytest.fixture
def mock_ssl_socket():
    """Mock SSL socket for testing."""
    mock_socket = AsyncMock()
    mock_socket.getpeercert = Mock(return_value=None)
    mock_socket.version = Mock(return_value="TLSv1.2")
    mock_socket.cipher = Mock(return_value=("TLS_PSK_WITH_AES_128_CBC_SHA256", "TLSv1.2", 128))
    return mock_socket
