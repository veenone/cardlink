"""
Unit tests for APDU Interface.

Tests the APDUInterface class with mocked transmit functions to verify
APDU command construction, response handling, and helper methods.
"""

import pytest
from unittest.mock import Mock, patch

from cardlink.provisioner.apdu_interface import (
    APDUInterface,
    SWDecoder,
    check_response,
)
from cardlink.provisioner.models import APDUCommand, APDUResponse, INS
from cardlink.provisioner.exceptions import APDUError, InvalidAPDUError


class TestSWDecoder:
    """Test status word decoder."""

    def test_decode_success(self):
        """Test decoding success status."""
        message = SWDecoder.decode(0x90, 0x00)
        assert message == "Success"

    def test_decode_warning(self):
        """Test decoding warning status."""
        message = SWDecoder.decode(0x62, 0x81)
        assert "Warning" in message
        assert "corrupted" in message

    def test_decode_security_error(self):
        """Test decoding security error."""
        message = SWDecoder.decode(0x69, 0x82)
        assert "Security status not satisfied" in message

    def test_decode_file_not_found(self):
        """Test decoding file not found error."""
        message = SWDecoder.decode(0x6A, 0x82)
        assert "File or application not found" in message

    def test_decode_more_data_available(self):
        """Test decoding 61xx (more data available)."""
        message = SWDecoder.decode(0x61, 0x10)
        assert "More data available" in message
        assert "16 bytes" in message

    def test_decode_wrong_le(self):
        """Test decoding 6Cxx (wrong Le)."""
        message = SWDecoder.decode(0x6C, 0x20)
        assert "Wrong Le" in message
        assert "32 bytes available" in message

    def test_decode_verification_failed(self):
        """Test decoding verification failed with retries."""
        message = SWDecoder.decode(0x63, 0xC3)
        assert "Verification failed" in message
        assert "3 retries" in message

    def test_decode_sim_toolkit_success(self):
        """Test decoding SIM toolkit success (9Fxx)."""
        message = SWDecoder.decode(0x9F, 0x08)
        assert "Success with 8 bytes available" in message

    def test_decode_unknown_status(self):
        """Test decoding unknown status word."""
        message = SWDecoder.decode(0xAB, 0xCD)
        assert "Unknown status" in message
        assert "ABCD" in message

    def test_decode_base_status_with_info(self):
        """Test decoding status with base pattern."""
        message = SWDecoder.decode(0x6A, 0x99)
        assert "Error" in message
        assert "SW2=99" in message


class TestAPDUInterfaceInit:
    """Test APDUInterface initialization."""

    def test_init_with_transmit_func(self):
        """Test initialization with transmit function."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        assert interface is not None
        assert interface._transmit == transmit_func
        assert interface._auto_get_response is True

    def test_init_disable_auto_get_response(self):
        """Test initialization with auto GET RESPONSE disabled."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func, auto_get_response=False)

        assert interface._auto_get_response is False


class TestAPDUInterfaceSend:
    """Test basic APDU sending."""

    def test_send_success(self):
        """Test sending APDU with success response."""
        transmit_func = Mock(return_value=APDUResponse(b"\x90\x00", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        command = APDUCommand(0x00, 0xA4, 0x04, 0x00, bytes.fromhex("A0000000031010"))
        response = interface.send(command)

        assert response.is_success
        assert transmit_func.called

    def test_send_with_get_response(self):
        """Test automatic GET RESPONSE handling."""
        # First call returns 61xx, second returns actual data
        transmit_func = Mock(side_effect=[
            APDUResponse(b"", 0x61, 0x10),  # More data available
            APDUResponse(b"\xAA\xBB\xCC", 0x90, 0x00)  # GET RESPONSE result
        ])
        interface = APDUInterface(transmit_func)

        command = APDUCommand(0x00, 0xA4, 0x04, 0x00, bytes.fromhex("A000000003"))
        response = interface.send(command)

        assert transmit_func.call_count == 2
        assert response.is_success
        assert response.data == b"\xAA\xBB\xCC"

    def test_send_without_auto_get_response(self):
        """Test sending without automatic GET RESPONSE."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x61, 0x10))
        interface = APDUInterface(transmit_func, auto_get_response=False)

        command = APDUCommand(0x00, 0xA4, 0x04, 0x00, bytes.fromhex("A000000003"))
        response = interface.send(command)

        assert transmit_func.call_count == 1
        assert response.needs_get_response

    def test_send_with_wrong_le_retry(self):
        """Test automatic retry with correct Le on 6Cxx."""
        # First call returns 6C20 (wrong Le), second succeeds with correct Le
        transmit_func = Mock(side_effect=[
            APDUResponse(b"", 0x6C, 0x20),  # Wrong Le, 32 bytes available
            APDUResponse(b"\xAA" * 32, 0x90, 0x00)  # Retry with Le=32
        ])
        interface = APDUInterface(transmit_func)

        command = APDUCommand(0x00, 0xB0, 0x00, 0x00, le=10)
        response = interface.send(command)

        assert transmit_func.call_count == 2
        assert response.is_success
        assert len(response.data) == 32


class TestAPDUInterfaceSendRaw:
    """Test sending raw APDU."""

    def test_send_raw_bytes(self):
        """Test sending raw APDU as bytes."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.send_raw(bytes.fromhex("00A4040007A0000000041010"))

        assert response.is_success
        assert transmit_func.called

    def test_send_raw_hex_string(self):
        """Test sending raw APDU as hex string."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.send_raw("00 A4 04 00 07 A0 00 00 00 04 10 10")

        assert response.is_success

    def test_send_raw_invalid_hex(self):
        """Test sending raw APDU with invalid hex string."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        with pytest.raises(InvalidAPDUError, match="Invalid hex string"):
            interface.send_raw("not a hex string")

    def test_send_raw_too_short(self):
        """Test sending APDU that's too short."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        with pytest.raises(InvalidAPDUError, match="too short"):
            interface.send_raw(bytes([0x00, 0xA4]))


class TestAPDUInterfaceSelectCommands:
    """Test SELECT command helpers."""

    def test_select_by_aid_bytes(self):
        """Test SELECT by AID with bytes."""
        transmit_func = Mock(return_value=APDUResponse(b"\x6F\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        aid = bytes.fromhex("A0000000031010")
        response = interface.select_by_aid(aid)

        assert response.is_success
        # Verify command structure
        call_args = transmit_func.call_args[0][0]
        assert call_args[0:4] == bytes([0x00, INS.SELECT, 0x04, 0x00])

    def test_select_by_aid_hex_string(self):
        """Test SELECT by AID with hex string."""
        transmit_func = Mock(return_value=APDUResponse(b"\x6F\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_by_aid("A0 00 00 00 03 10 10")

        assert response.is_success

    def test_select_by_aid_next_occurrence(self):
        """Test SELECT by AID with next occurrence."""
        transmit_func = Mock(return_value=APDUResponse(b"\x6F\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_by_aid("A0000000031010", next_occurrence=True)

        # Verify P2 = 0x02 for next occurrence
        call_args = transmit_func.call_args[0][0]
        assert call_args[3] == 0x02

    def test_select_by_path_from_mf(self):
        """Test SELECT by path from MF."""
        transmit_func = Mock(return_value=APDUResponse(b"\x62\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_by_path("7F106F07", from_mf=True)

        assert response.is_success
        # Verify P1 = 0x08 (from MF)
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x08

    def test_select_by_path_from_current(self):
        """Test SELECT by path from current DF."""
        transmit_func = Mock(return_value=APDUResponse(b"\x62\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_by_path("6F07", from_mf=False)

        # Verify P1 = 0x09 (from current DF)
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x09

    def test_select_by_file_id(self):
        """Test SELECT by file identifier."""
        transmit_func = Mock(return_value=APDUResponse(b"\x62\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_by_file_id(0x6F07)

        assert response.is_success
        # Verify P1 = 0x00, data contains file ID
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x00
        assert call_args[5:7] == bytes([0x6F, 0x07])

    def test_select_mf(self):
        """Test SELECT Master File."""
        transmit_func = Mock(return_value=APDUResponse(b"\x62\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.select_mf()

        assert response.is_success
        # Verify MF file ID (3F00)
        call_args = transmit_func.call_args[0][0]
        assert call_args[5:7] == bytes([0x3F, 0x00])


class TestAPDUInterfaceReadCommands:
    """Test READ command helpers."""

    def test_read_binary_default(self):
        """Test READ BINARY with default parameters."""
        transmit_func = Mock(return_value=APDUResponse(b"\xAA" * 256, 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.read_binary()

        assert response.is_success
        assert len(response.data) == 256

    def test_read_binary_with_offset(self):
        """Test READ BINARY with offset."""
        transmit_func = Mock(return_value=APDUResponse(b"\xBB" * 100, 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.read_binary(offset=100, length=100)

        assert response.is_success
        # Verify offset encoding in P1/P2
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x00  # P1 (high byte of offset)
        assert call_args[3] == 0x64  # P2 (low byte of offset = 100)

    def test_read_binary_large_offset(self):
        """Test READ BINARY with large offset."""
        transmit_func = Mock(return_value=APDUResponse(b"\xCC" * 100, 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.read_binary(offset=0x1234, length=100)

        # Verify offset encoding
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x12  # P1
        assert call_args[3] == 0x34  # P2

    def test_read_binary_offset_too_large(self):
        """Test READ BINARY with offset exceeding limit."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        with pytest.raises(InvalidAPDUError, match="Offset too large"):
            interface.read_binary(offset=0x8000)

    def test_read_record(self):
        """Test READ RECORD."""
        transmit_func = Mock(return_value=APDUResponse(b"\xDD" * 50, 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.read_record(record_number=5)

        assert response.is_success
        # Verify P1 = record number
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 5

    def test_read_record_with_mode(self):
        """Test READ RECORD with specific mode."""
        transmit_func = Mock(return_value=APDUResponse(b"\xEE" * 50, 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.read_record(record_number=3, mode=0x02)

        # Verify P2 = mode
        call_args = transmit_func.call_args[0][0]
        assert call_args[3] == 0x02


class TestAPDUInterfaceUpdateCommands:
    """Test UPDATE command helpers."""

    def test_update_binary_bytes(self):
        """Test UPDATE BINARY with bytes data."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        data = bytes([0xFF] * 10)
        response = interface.update_binary(data, offset=0)

        assert response.is_success
        # Verify command structure
        call_args = transmit_func.call_args[0][0]
        assert call_args[1] == INS.UPDATE_BINARY

    def test_update_binary_hex_string(self):
        """Test UPDATE BINARY with hex string data."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.update_binary("AABBCCDD", offset=0)

        assert response.is_success

    def test_update_binary_with_offset(self):
        """Test UPDATE BINARY with offset."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.update_binary(bytes([0xFF] * 10), offset=0x100)

        # Verify offset encoding
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x01  # P1
        assert call_args[3] == 0x00  # P2

    def test_update_binary_offset_too_large(self):
        """Test UPDATE BINARY with offset exceeding limit."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        with pytest.raises(InvalidAPDUError, match="Offset too large"):
            interface.update_binary(bytes([0xFF]), offset=0x8000)


class TestAPDUInterfaceVerifyPIN:
    """Test PIN verification helpers."""

    def test_verify_pin_success(self):
        """Test successful PIN verification."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.verify_pin("1234")

        assert response.is_success
        # Verify PIN is padded to 8 bytes
        call_args = transmit_func.call_args[0][0]
        assert len(call_args) == 13  # CLA INS P1 P2 Lc + 8 bytes data

    def test_verify_pin_bytes(self):
        """Test PIN verification with bytes."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.verify_pin(b"1234")

        assert response.is_success

    def test_verify_pin_with_reference(self):
        """Test PIN verification with specific reference."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.verify_pin("1234", pin_ref=0x02)

        # Verify P2 = pin_ref
        call_args = transmit_func.call_args[0][0]
        assert call_args[3] == 0x02

    def test_verify_pin_padding(self):
        """Test PIN is properly padded."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        interface.verify_pin("12")

        # Verify padding with 0xFF
        call_args = transmit_func.call_args[0][0]
        data = call_args[5:]  # Skip header
        assert len(data) == 8
        assert data[0:2] == b"12"
        assert data[2:] == b"\xFF" * 6

    def test_get_remaining_pin_retries(self):
        """Test getting remaining PIN retries."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x63, 0xC3))
        interface = APDUInterface(transmit_func)

        retries = interface.get_remaining_pin_retries()

        assert retries == 3

    def test_get_remaining_pin_retries_verified(self):
        """Test getting retries when PIN already verified."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        retries = interface.get_remaining_pin_retries()

        assert retries == -1

    def test_get_remaining_pin_retries_blocked(self):
        """Test getting retries when PIN is blocked."""
        transmit_func = Mock(return_value=APDUResponse(b"", 0x69, 0x83))
        interface = APDUInterface(transmit_func)

        retries = interface.get_remaining_pin_retries()

        assert retries == 0


class TestAPDUInterfaceGetData:
    """Test GET DATA command."""

    def test_get_data_single_byte_tag(self):
        """Test GET DATA with single-byte tag."""
        transmit_func = Mock(return_value=APDUResponse(b"\xAA\xBB", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.get_data(0x42)

        assert response.is_success
        # Verify P1=0x00, P2=tag
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x00
        assert call_args[3] == 0x42

    def test_get_data_two_byte_tag(self):
        """Test GET DATA with two-byte tag."""
        transmit_func = Mock(return_value=APDUResponse(b"\xCC\xDD", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.get_data(0x5F50)

        # Verify P1=0x5F, P2=0x50
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x5F
        assert call_args[3] == 0x50


class TestAPDUInterfaceGetStatus:
    """Test GlobalPlatform GET STATUS command."""

    def test_get_status_isd(self):
        """Test GET STATUS for ISD."""
        transmit_func = Mock(return_value=APDUResponse(b"\xE3\x10", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.get_status(p1=0x80)

        assert response.is_success
        # Verify CLA=0x80 (GlobalPlatform)
        call_args = transmit_func.call_args[0][0]
        assert call_args[0] == 0x80

    def test_get_status_applications(self):
        """Test GET STATUS for applications."""
        transmit_func = Mock(return_value=APDUResponse(b"\xE3\x20", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        response = interface.get_status(p1=0x40)

        # Verify P1=0x40 (applications)
        call_args = transmit_func.call_args[0][0]
        assert call_args[2] == 0x40

    def test_get_status_with_aid_filter(self):
        """Test GET STATUS with AID filter."""
        transmit_func = Mock(return_value=APDUResponse(b"\xE3\x30", 0x90, 0x00))
        interface = APDUInterface(transmit_func)

        aid = bytes.fromhex("A0000000031010")
        response = interface.get_status(p1=0x40, aid_filter=aid)

        # Verify AID filter is included in command data
        call_args = transmit_func.call_args[0][0]
        assert aid in call_args


class TestAPDUInterfaceStatusDecoder:
    """Test status word decoder integration."""

    def test_get_response_sw_success(self):
        """Test getting status description for success."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        response = APDUResponse(b"", 0x90, 0x00)
        message = interface.get_response_sw(response)

        assert message == "Success"

    def test_get_response_sw_error(self):
        """Test getting status description for error."""
        transmit_func = Mock()
        interface = APDUInterface(transmit_func)

        response = APDUResponse(b"", 0x6A, 0x82)
        message = interface.get_response_sw(response)

        assert "File or application not found" in message


class TestCheckResponse:
    """Test check_response helper function."""

    def test_check_response_success(self):
        """Test check_response with successful response."""
        response = APDUResponse(b"", 0x90, 0x00)

        # Should not raise
        check_response(response)

    def test_check_response_failure(self):
        """Test check_response with failure response."""
        response = APDUResponse(b"", 0x6A, 0x82)

        with pytest.raises(APDUError):
            check_response(response)

    def test_check_response_custom_expected_sw(self):
        """Test check_response with custom expected SW."""
        response = APDUResponse(b"", 0x61, 0x10)

        # Should not raise when expecting 6110
        check_response(response, expected_sw=0x6110)

    def test_check_response_with_operation_name(self):
        """Test check_response includes operation name in error."""
        response = APDUResponse(b"", 0x6A, 0x82)

        with pytest.raises(APDUError):
            check_response(response, operation="SELECT")
