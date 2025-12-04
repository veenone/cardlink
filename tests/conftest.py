"""
Pytest configuration and fixtures for cardlink tests.

This module provides shared fixtures for testing cardlink components,
including mocks for hardware dependencies like PC/SC readers and Android devices.
"""

import pytest
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch


# ============================================================================
# PC/SC Smart Card Reader Mocking
# ============================================================================

@pytest.fixture
def mock_smartcard_reader():
    """
    Mock smartcard.Reader object for testing without physical hardware.

    Returns:
        Mock: A configured mock reader with standard attributes
    """
    reader = Mock()
    reader.name = "Mock PC/SC Reader 00 00"
    reader.__str__ = Mock(return_value="Mock PC/SC Reader 00 00")
    return reader


@pytest.fixture
def mock_smartcard_connection():
    """
    Mock smartcard.CardConnection for APDU transmission testing.

    Returns:
        Mock: A configured mock connection with transmit capability
    """
    connection = Mock()

    # Default ATR for UICC card
    connection.getATR = Mock(return_value=[
        0x3B, 0x9F, 0x96, 0x80, 0x1F, 0xC7, 0x80, 0x31,
        0xA0, 0x73, 0xBE, 0x21, 0x13, 0x67, 0x43, 0x20,
        0x07, 0x18, 0x00, 0x00, 0x01, 0xA5
    ])

    # Default successful response (SW=9000)
    connection.transmit = Mock(return_value=([], 0x90, 0x00))

    connection.connect = Mock()
    connection.disconnect = Mock()

    return connection


@pytest.fixture
def mock_smartcard_system(mock_smartcard_reader):
    """
    Mock smartcard.System for reader enumeration testing.

    Args:
        mock_smartcard_reader: Injected mock reader fixture

    Returns:
        Mock: Configured system mock with readers() method
    """
    with patch('smartcard.System.readers') as mock_readers:
        mock_readers.return_value = [mock_smartcard_reader]
        yield mock_readers


@pytest.fixture
def mock_pcsc_client(mock_smartcard_reader, mock_smartcard_connection):
    """
    Mock PCSCClient for high-level provisioner testing.

    Args:
        mock_smartcard_reader: Injected mock reader
        mock_smartcard_connection: Injected mock connection

    Returns:
        Mock: Configured PCSCClient mock
    """
    with patch('cardlink.provisioner.pcsc_client.PCSCClient') as MockClient:
        client_instance = MockClient.return_value

        # Configure mock methods
        client_instance.list_readers = Mock(return_value=[
            Mock(name="Mock PC/SC Reader 00 00", index=0)
        ])
        client_instance.connect = Mock()
        client_instance.disconnect = Mock()
        client_instance.transmit = Mock(return_value=([],  0x90, 0x00))
        client_instance.is_connected = True

        # Mock card_info property
        card_info_mock = Mock()
        card_info_mock.atr = bytes([
            0x3B, 0x9F, 0x96, 0x80, 0x1F, 0xC7, 0x80, 0x31,
            0xA0, 0x73, 0xBE, 0x21, 0x13, 0x67, 0x43, 0x20,
            0x07, 0x18, 0x00, 0x00, 0x01, 0xA5
        ])
        card_info_mock.protocol = "T=1"
        type(client_instance).card_info = Mock(return_value=card_info_mock)

        yield client_instance


@pytest.fixture
def sample_atr():
    """
    Sample ATR (Answer To Reset) bytes for testing.

    Returns:
        bytes: A valid UICC card ATR
    """
    return bytes([
        0x3B,  # TS: Direct convention
        0x9F,  # T0: 15 historical bytes follow
        0x96, 0x80, 0x1F, 0xC7, 0x80, 0x31,  # Interface bytes
        0xA0, 0x73, 0xBE, 0x21, 0x13, 0x67,  # Historical bytes
        0x43, 0x20, 0x07, 0x18, 0x00, 0x00,
        0x01, 0xA5  # TCK: Checksum
    ])


@pytest.fixture
def sample_iccid():
    """
    Sample ICCID (Integrated Circuit Card Identifier) for testing.

    Returns:
        str: A valid 19-digit ICCID
    """
    return "8901234567890123456"


# ============================================================================
# APDU Testing Helpers
# ============================================================================

@pytest.fixture
def apdu_select_isd():
    """
    APDU command bytes for SELECT ISD (Issuer Security Domain).

    Returns:
        bytes: SELECT command for ISD AID A000000151000000
    """
    return bytes([
        0x00,  # CLA
        0xA4,  # INS: SELECT
        0x04,  # P1: Select by AID
        0x00,  # P2: First or only occurrence
        0x08,  # Lc: Length of AID
        0xA0, 0x00, 0x00, 0x01, 0x51, 0x00, 0x00, 0x00  # AID
    ])


@pytest.fixture
def apdu_response_success():
    """
    Successful APDU response (SW=9000).

    Returns:
        tuple: (data, sw1, sw2) where SW=9000
    """
    return ([], 0x90, 0x00)


@pytest.fixture
def apdu_response_error():
    """
    Error APDU response (SW=6A82 - File not found).

    Returns:
        tuple: (data, sw1, sw2) where SW=6A82
    """
    return ([], 0x6A, 0x82)


# ============================================================================
# Secure Channel Mocking
# ============================================================================

@pytest.fixture
def mock_scp02():
    """
    Mock SCP02 secure channel for testing without card authentication.

    Returns:
        Mock: Configured SCP02 mock with session keys
    """
    with patch('cardlink.provisioner.scp02.SCP02') as MockSCP02:
        scp_instance = MockSCP02.return_value

        scp_instance.initialize = Mock()
        scp_instance.send = Mock(return_value=([], 0x90, 0x00))
        scp_instance.is_authenticated = True

        # Mock session keys
        scp_instance.session_enc_key = bytes(16)
        scp_instance.session_mac_key = bytes(16)
        scp_instance.session_dek_key = bytes(16)

        yield scp_instance


@pytest.fixture
def mock_scp03():
    """
    Mock SCP03 secure channel for testing without card authentication.

    Returns:
        Mock: Configured SCP03 mock with session keys
    """
    with patch('cardlink.provisioner.scp03.SCP03') as MockSCP03:
        scp_instance = MockSCP03.return_value

        scp_instance.initialize = Mock()
        scp_instance.send = Mock(return_value=([], 0x90, 0x00))
        scp_instance.is_authenticated = True

        # Mock session keys
        scp_instance.session_enc_key = bytes(16)
        scp_instance.session_mac_key = bytes(16)
        scp_instance.session_rmac_key = bytes(16)

        yield scp_instance


# ============================================================================
# PSK Configuration Mocking
# ============================================================================

@pytest.fixture
def sample_psk_identity():
    """
    Sample PSK identity for testing.

    Returns:
        str: A sample device identity
    """
    return "device001"


@pytest.fixture
def sample_psk_key():
    """
    Sample PSK key for testing.

    Returns:
        bytes: A 32-byte PSK key
    """
    return bytes([0x00, 0x01, 0x02, 0x03] * 8)  # 32 bytes


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """
    Register custom pytest markers.
    """
    config.addinivalue_line(
        "markers", "pcsc: Tests requiring physical PC/SC smart card reader"
    )
    config.addinivalue_line(
        "markers", "phone: Tests requiring connected Android phone via ADB"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests requiring phone + UICC + server"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests that take more than 5 seconds"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip tests marked with hardware requirements unless explicitly enabled.

    This prevents tests from failing when hardware is not available during CI/CD.
    """
    skip_pcsc = pytest.mark.skip(reason="PC/SC reader not available (use --pcsc to run)")
    skip_phone = pytest.mark.skip(reason="Android phone not available (use --phone to run)")
    skip_e2e = pytest.mark.skip(reason="E2E setup not available (use --e2e to run)")

    run_pcsc = config.getoption("--pcsc", default=False)
    run_phone = config.getoption("--phone", default=False)
    run_e2e = config.getoption("--e2e", default=False)

    for item in items:
        if "pcsc" in item.keywords and not run_pcsc:
            item.add_marker(skip_pcsc)
        if "phone" in item.keywords and not run_phone:
            item.add_marker(skip_phone)
        if "e2e" in item.keywords and not run_e2e:
            item.add_marker(skip_e2e)


def pytest_addoption(parser):
    """
    Add custom command-line options for pytest.
    """
    parser.addoption(
        "--pcsc",
        action="store_true",
        default=False,
        help="Run tests that require PC/SC smart card reader"
    )
    parser.addoption(
        "--phone",
        action="store_true",
        default=False,
        help="Run tests that require Android phone via ADB"
    )
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests (requires phone + UICC + server)"
    )
