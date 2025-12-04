"""
Unit tests for PC/SC Client.

Tests the PCSCClient class with mocked smartcard library to verify
reader enumeration, card connection, APDU transmission, and monitoring
without requiring physical hardware.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time

from cardlink.provisioner.pcsc_client import PCSCClient, list_readers, connect_card
from cardlink.provisioner.models import ReaderInfo, CardInfo, Protocol
from cardlink.provisioner.exceptions import (
    ReaderNotFoundError,
    CardNotFoundError,
    NotConnectedError,
    APDUError,
)


class TestPCSCClientInit:
    """Test PCSCClient initialization."""

    def test_init_creates_instance(self):
        """Test that PCSCClient can be instantiated."""
        client = PCSCClient()
        assert client is not None
        assert not client.is_connected
        assert client.card_info is None
        assert client.reader_info is None

    def test_init_creates_lock(self):
        """Test that threading lock is created."""
        client = PCSCClient()
        assert hasattr(client, '_lock')
        assert isinstance(client._lock, type(threading.Lock()))


class TestPCSCClientListReaders:
    """Test reader enumeration."""

    @patch('smartcard.System.readers')
    def test_list_readers_success(self, mock_readers):
        """Test successful reader enumeration."""
        # Create mock readers
        mock_reader1 = Mock()
        mock_reader1.name = "Mock Reader 1"
        mock_reader1.__str__ = Mock(return_value="Mock Reader 1")

        mock_reader2 = Mock()
        mock_reader2.name = "Mock Reader 2"
        mock_reader2.__str__ = Mock(return_value="Mock Reader 2")

        mock_readers.return_value = [mock_reader1, mock_reader2]

        # Test
        client = PCSCClient()
        readers = client.list_readers()

        # Verify
        assert len(readers) == 2
        assert all(isinstance(r, ReaderInfo) for r in readers)
        assert readers[0].name == "Mock Reader 1"
        assert readers[0].index == 0
        assert readers[1].name == "Mock Reader 2"
        assert readers[1].index == 1

    @patch('smartcard.System.readers')
    def test_list_readers_empty(self, mock_readers):
        """Test reader enumeration when no readers available."""
        mock_readers.return_value = []

        client = PCSCClient()
        readers = client.list_readers()

        assert readers == []

    @patch('smartcard.System.readers')
    def test_list_readers_with_card_detection(self, mock_readers):
        """Test reader enumeration with card presence detection."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        # Mock createConnection to simulate card present
        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.disconnect = Mock()
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        readers = client.list_readers()

        assert len(readers) == 1
        # Card presence is detected during createConnection attempt


class TestPCSCClientConnect:
    """Test card connection."""

    @patch('smartcard.System.readers')
    def test_connect_by_name_success(self, mock_readers, sample_atr):
        """Test successful connection to card by reader name."""
        # Setup mock reader and connection
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        # Test
        client = PCSCClient()
        client.connect("Mock Reader")

        # Verify
        assert client.is_connected
        assert client.card_info is not None
        assert client.card_info.atr == sample_atr
        assert client.reader_info is not None
        assert client.reader_info.name == "Mock Reader"
        mock_connection.connect.assert_called_once()

    @patch('smartcard.System.readers')
    def test_connect_by_index_success(self, mock_readers, sample_atr):
        """Test successful connection to card by reader index."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        client.connect(0)

        assert client.is_connected
        assert client.reader_info.index == 0

    @patch('smartcard.System.readers')
    def test_connect_reader_not_found(self, mock_readers):
        """Test connection fails when reader not found."""
        mock_readers.return_value = []

        client = PCSCClient()

        with pytest.raises(ReaderNotFoundError, match="No readers found"):
            client.connect(0)

    @patch('smartcard.System.readers')
    def test_connect_invalid_reader_name(self, mock_readers):
        """Test connection fails with invalid reader name."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")
        mock_readers.return_value = [mock_reader]

        client = PCSCClient()

        with pytest.raises(ReaderNotFoundError, match="Reader 'Invalid' not found"):
            client.connect("Invalid")

    @patch('smartcard.System.readers')
    def test_connect_no_card(self, mock_readers):
        """Test connection fails when no card in reader."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock(side_effect=Exception("No card"))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()

        with pytest.raises(CardNotFoundError):
            client.connect(0)


class TestPCSCClientDisconnect:
    """Test card disconnection."""

    @patch('smartcard.System.readers')
    def test_disconnect_success(self, mock_readers, sample_atr):
        """Test successful disconnection from card."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.disconnect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        client.connect(0)
        assert client.is_connected

        client.disconnect()

        assert not client.is_connected
        assert client.card_info is None
        mock_connection.disconnect.assert_called_once()

    def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected doesn't raise error."""
        client = PCSCClient()
        client.disconnect()  # Should not raise

        assert not client.is_connected


class TestPCSCClientTransmit:
    """Test APDU transmission."""

    @patch('smartcard.System.readers')
    def test_transmit_success(self, mock_readers, sample_atr):
        """Test successful APDU transmission."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        # Mock successful SELECT response
        mock_connection.transmit = Mock(return_value=([0x61, 0x10], 0x90, 0x00))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        client.connect(0)

        # Test
        apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x00])
        response = client.transmit(apdu)

        # Verify
        assert response.sw == 0x9000
        assert response.is_success
        mock_connection.transmit.assert_called()

    @patch('smartcard.System.readers')
    def test_transmit_get_response_handling(self, mock_readers, sample_atr):
        """Test automatic GET RESPONSE handling for 61xx status."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))

        # First response: 61 10 (more data available)
        # Second response: actual data with 90 00
        mock_connection.transmit = Mock(side_effect=[
            ([], 0x61, 0x10),  # Indicates 16 bytes available
            ([0xAA, 0xBB, 0xCC], 0x90, 0x00)  # GET RESPONSE result
        ])
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        client.connect(0)

        apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x00])
        response = client.transmit(apdu)

        # Should have called transmit twice (original + GET RESPONSE)
        assert mock_connection.transmit.call_count == 2
        assert response.sw == 0x9000
        assert len(response.data) == 3

    def test_transmit_not_connected(self):
        """Test transmission fails when not connected."""
        client = PCSCClient()

        with pytest.raises(NotConnectedError, match="Not connected"):
            client.transmit(bytes([0x00, 0xA4, 0x04, 0x00]))

    @patch('smartcard.System.readers')
    def test_transmit_thread_safety(self, mock_readers, sample_atr):
        """Test that transmit operations are thread-safe."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))

        # Add small delay to simulate real transmission
        def mock_transmit(apdu):
            time.sleep(0.01)
            return ([], 0x90, 0x00)

        mock_connection.transmit = Mock(side_effect=mock_transmit)
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = PCSCClient()
        client.connect(0)

        # Run multiple transmissions in parallel
        results = []

        def transmit_thread():
            try:
                response = client.transmit(bytes([0x00, 0xA4, 0x04, 0x00]))
                results.append(response.sw == 0x9000)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=transmit_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All transmissions should succeed
        assert all(results)
        assert len(results) == 5


class TestPCSCClientContextManager:
    """Test context manager protocol."""

    @patch('smartcard.System.readers')
    def test_context_manager(self, mock_readers, sample_atr):
        """Test using PCSCClient as context manager."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.disconnect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        # Test
        with PCSCClient() as client:
            client.connect(0)
            assert client.is_connected

        # After context, should be disconnected
        mock_connection.disconnect.assert_called()


class TestPCSCClientHelperFunctions:
    """Test module-level helper functions."""

    @patch('smartcard.System.readers')
    def test_list_readers_function(self, mock_readers):
        """Test list_readers() helper function."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")
        mock_readers.return_value = [mock_reader]

        readers = list_readers()

        assert len(readers) == 1
        assert readers[0].name == "Mock Reader"

    @patch('smartcard.System.readers')
    def test_connect_card_function(self, mock_readers, sample_atr):
        """Test connect_card() helper function."""
        mock_reader = Mock()
        mock_reader.name = "Mock Reader"
        mock_reader.__str__ = Mock(return_value="Mock Reader")

        mock_connection = Mock()
        mock_connection.connect = Mock()
        mock_connection.getATR = Mock(return_value=list(sample_atr))
        mock_reader.createConnection = Mock(return_value=mock_connection)

        mock_readers.return_value = [mock_reader]

        client = connect_card(0)

        assert client.is_connected
        assert isinstance(client, PCSCClient)


class TestPCSCClientCardMonitoring:
    """Test card monitoring functionality."""

    @patch('smartcard.CardMonitor')
    def test_start_monitoring(self, mock_monitor_class):
        """Test starting card monitoring."""
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor

        client = PCSCClient()
        client.start_monitoring()

        # Should create monitor and observer
        assert client._monitor is not None
        assert client._observer is not None
        mock_monitor_class.assert_called_once()

    def test_stop_monitoring(self):
        """Test stopping card monitoring."""
        client = PCSCClient()

        # Start monitoring first
        with patch('smartcard.CardMonitor'):
            client.start_monitoring()
            assert client._monitor is not None

            # Stop monitoring
            client.stop_monitoring()

            assert client._monitor is None
            assert client._observer is None

    def test_on_card_event_callback(self):
        """Test registering card event callbacks."""
        client = PCSCClient()
        callback_called = []

        def callback(card_info, is_insertion):
            callback_called.append((card_info, is_insertion))

        client.on_card_event(callback)

        assert callback in client._card_callbacks

        # Test callback removal
        client.remove_card_callback(callback)
        assert callback not in client._card_callbacks
