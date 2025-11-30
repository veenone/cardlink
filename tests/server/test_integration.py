"""Integration tests for PSK-TLS Admin Server.

These tests verify end-to-end functionality of the server components
working together.

Note: These tests use mock TLS handlers to avoid actual network operations.
For full PSK-TLS testing with sslpsk3, see test_tls_integration.py.
"""

import socket
import threading
import time
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from cardlink.server import (
    AdminServer,
    APDUCommand,
    APDUResponse,
    CipherConfig,
    CloseReason,
    ErrorHandler,
    EventEmitter,
    FileKeyStore,
    GPCommandProcessor,
    HTTPHandler,
    HTTPRequest,
    HTTPResponse,
    HTTPStatus,
    MemoryKeyStore,
    MockEventEmitter,
    MockGPCommandProcessor,
    MockHTTPHandler,
    MockTLSHandler,
    ServerConfig,
    Session,
    SessionManager,
    SessionState,
    TLSSessionInfo,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def memory_key_store() -> MemoryKeyStore:
    """Create a memory key store with test keys."""
    key_store = MemoryKeyStore()
    key_store.add_key("test_card_001", bytes.fromhex("0102030405060708090A0B0C0D0E0F10"))
    key_store.add_key("test_card_002", bytes.fromhex("1112131415161718191A1B1C1D1E1F20"))
    return key_store


@pytest.fixture
def mock_event_emitter() -> MockEventEmitter:
    """Create a mock event emitter."""
    return MockEventEmitter()


@pytest.fixture
def session_manager(mock_event_emitter: MockEventEmitter) -> Generator[SessionManager, None, None]:
    """Create and start a session manager."""
    manager = SessionManager(
        event_emitter=mock_event_emitter,
        session_timeout=60.0,
        cleanup_interval=1.0,
    )
    manager.start()
    yield manager
    manager.stop()


@pytest.fixture
def error_handler(mock_event_emitter: MockEventEmitter) -> ErrorHandler:
    """Create an error handler."""
    return ErrorHandler(
        event_emitter=mock_event_emitter,
        mismatch_threshold=3,
        mismatch_window=60.0,
    )


@pytest.fixture
def command_processor(mock_event_emitter: MockEventEmitter) -> GPCommandProcessor:
    """Create a command processor."""
    return GPCommandProcessor(
        event_emitter=mock_event_emitter,
        register_default_handlers=True,
    )


@pytest.fixture
def http_handler(command_processor: GPCommandProcessor) -> HTTPHandler:
    """Create an HTTP handler."""
    return HTTPHandler(command_processor=command_processor)


# =============================================================================
# Session Tests (Tasks 238-242)
# =============================================================================


class TestSessionCreation:
    """Tests for session creation and lifecycle."""

    def test_session_creation_on_connection(
        self,
        session_manager: SessionManager,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test session creation when a connection is established."""
        # Create session
        session = session_manager.create_session(
            client_address="192.168.1.100:12345",
            metadata={"psk_identity": "test_card_001"},
        )

        # Verify session created
        assert session is not None
        assert session.session_id is not None
        assert session.state == SessionState.HANDSHAKING
        assert session.client_address == "192.168.1.100:12345"

        # Verify event emitted
        session_events = mock_event_emitter.get_events_by_type("session_started")
        assert len(session_events) == 1
        assert session_events[0].data["session_id"] == session.session_id

    def test_session_state_transitions(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test session state transitions during operation."""
        # Create session in HANDSHAKING state
        session = session_manager.create_session("192.168.1.100:12345")
        assert session.state == SessionState.HANDSHAKING

        # Transition to CONNECTED
        session_manager.set_session_state(
            session.session_id,
            SessionState.CONNECTED,
        )
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.state == SessionState.CONNECTED

        # Transition to ACTIVE
        session_manager.set_session_state(
            session.session_id,
            SessionState.ACTIVE,
        )
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.state == SessionState.ACTIVE

        # Transition to CLOSED
        session_manager.set_session_state(
            session.session_id,
            SessionState.CLOSED,
        )
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.state == SessionState.CLOSED

    def test_invalid_state_transition(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test that invalid state transitions are rejected."""
        from cardlink.server import InvalidStateTransition

        session = session_manager.create_session("192.168.1.100:12345")

        # Try invalid transition: HANDSHAKING -> ACTIVE (should fail)
        with pytest.raises(InvalidStateTransition):
            session_manager.set_session_state(
                session.session_id,
                SessionState.ACTIVE,
            )

    def test_session_timeout_expiration(
        self,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test session expiration after timeout."""
        # Create manager with very short timeout
        manager = SessionManager(
            event_emitter=mock_event_emitter,
            session_timeout=0.1,  # 100ms timeout
            cleanup_interval=0.05,  # 50ms cleanup
        )
        manager.start()

        try:
            # Create session
            session = manager.create_session("192.168.1.100:12345")
            session_id = session.session_id

            # Transition to CONNECTED (valid from HANDSHAKING)
            manager.set_session_state(session_id, SessionState.CONNECTED)

            # Wait for timeout
            time.sleep(0.3)

            # Session should be closed due to timeout
            updated_session = manager.get_session(session_id)
            assert updated_session.state == SessionState.CLOSED
            assert updated_session.close_reason == CloseReason.TIMEOUT

        finally:
            manager.stop()

    def test_concurrent_sessions(
        self,
        session_manager: SessionManager,
    ) -> None:
        """Test handling of concurrent sessions."""
        sessions = []

        # Create multiple sessions concurrently
        def create_session(index: int) -> None:
            session = session_manager.create_session(
                f"192.168.1.{index}:12345",
                metadata={"index": index},
            )
            sessions.append(session)

        threads = [
            threading.Thread(target=create_session, args=(i,))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all sessions created
        assert len(sessions) == 10
        assert len(set(s.session_id for s in sessions)) == 10  # All unique IDs

        # Verify all are active
        active_sessions = session_manager.get_active_sessions()
        assert len(active_sessions) == 10


# =============================================================================
# Error Handling Tests (Tasks 243-245)
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_psk_mismatch_detection(
        self,
        error_handler: ErrorHandler,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test PSK mismatch detection and event emission."""
        # Handle single mismatch
        alert = error_handler.handle_psk_mismatch(
            identity="unknown_card",
            client_address="192.168.1.100:12345",
        )

        # Verify TLS alert returned
        from cardlink.server import TLSAlert
        assert alert == TLSAlert.DECRYPT_ERROR

        # Verify event emitted
        mismatch_events = mock_event_emitter.get_events_by_type("psk_mismatch")
        assert len(mismatch_events) == 1
        assert mismatch_events[0].data["identity"] == "unknown_card"
        assert mismatch_events[0].data["repeated_attempts"] is False

    def test_psk_mismatch_alerting_multiple_attempts(
        self,
        error_handler: ErrorHandler,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test alerting when multiple PSK mismatches from same source."""
        # Generate multiple mismatches from same IP
        for i in range(3):
            error_handler.handle_psk_mismatch(
                identity=f"attempt_{i}",
                client_address="192.168.1.100:12345",
            )

        # Check that repeated_attempts flag is set on last attempt
        mismatch_events = mock_event_emitter.get_events_by_type("psk_mismatch")
        assert len(mismatch_events) == 3
        # Third attempt should trigger warning
        assert mismatch_events[2].data["repeated_attempts"] is True

    def test_connection_interruption_handling(
        self,
        session_manager: SessionManager,
        error_handler: ErrorHandler,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test connection interruption mid-session."""
        # Create and activate session
        session = session_manager.create_session("192.168.1.100:12345")
        session_manager.set_session_state(
            session.session_id,
            SessionState.CONNECTED,
        )
        session_manager.set_session_state(
            session.session_id,
            SessionState.ACTIVE,
        )

        # Simulate connection interruption
        error_handler.handle_connection_interrupted(
            session_id=session.session_id,
            last_command="00A4040007A0000000041010",
            error="Connection reset by peer",
        )

        # Verify event emitted
        interrupt_events = mock_event_emitter.get_events_by_type(
            "connection_interrupted"
        )
        assert len(interrupt_events) == 1
        assert interrupt_events[0].data["session_id"] == session.session_id

    def test_handshake_timeout_handling(
        self,
        error_handler: ErrorHandler,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test handshake timeout handling."""
        from cardlink.server import HandshakeProgress, HandshakeState

        # Create partial handshake state
        partial_state = HandshakeProgress(
            state=HandshakeState.CLIENT_HELLO_RECEIVED,
            client_address="192.168.1.100:12345",
            messages_received=["ClientHello"],
        )

        # Handle interrupted handshake
        error_handler.handle_handshake_interrupted(
            client_address="192.168.1.100:12345",
            partial_state=partial_state,
            reason="Handshake timeout",
        )

        # Error should be recorded
        error_count = error_handler.get_error_count("handshake_failed")
        assert error_count == 1

    def test_error_rate_threshold_alerting(
        self,
        mock_event_emitter: MockEventEmitter,
    ) -> None:
        """Test error rate threshold alerting."""
        # Create handler with low threshold
        handler = ErrorHandler(
            event_emitter=mock_event_emitter,
            error_rate_threshold=3,
            error_rate_window=60.0,
        )

        # Generate enough errors to exceed threshold
        for i in range(4):
            handler.handle_psk_mismatch(
                identity=f"card_{i}",
                client_address=f"192.168.1.{i}:12345",
            )

        # Verify high error rate event emitted
        high_rate_events = mock_event_emitter.get_events_by_type("high_error_rate")
        assert len(high_rate_events) >= 1


# =============================================================================
# Command Processing Tests (Tasks 246-250)
# =============================================================================


class TestCommandProcessing:
    """Tests for GP command processing."""

    def test_select_command_processing(
        self,
        command_processor: GPCommandProcessor,
    ) -> None:
        """Test SELECT command processing."""
        # Create SELECT APDU
        aid = bytes.fromhex("A000000151000000")
        apdu = APDUCommand(
            cla=0x00,
            ins=0xA4,  # SELECT
            p1=0x04,  # By DF name
            p2=0x00,
            lc=len(aid),
            data=aid,
            raw=bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid,
        )

        # Process command
        response = command_processor.process_command(apdu, None)

        # Verify success
        assert response.is_success
        assert response.sw1 == 0x90
        assert response.sw2 == 0x00
        # Should have FCI data
        assert len(response.data) > 0
        # FCI should start with tag 0x6F
        assert response.data[0] == 0x6F

    def test_install_command_processing(
        self,
        command_processor: GPCommandProcessor,
    ) -> None:
        """Test INSTALL command processing."""
        # Create INSTALL for LOAD APDU
        install_data = bytes.fromhex("0708A0000001510000000000")
        apdu = APDUCommand(
            cla=0x80,
            ins=0xE6,  # INSTALL
            p1=0x02,  # For LOAD
            p2=0x00,
            lc=len(install_data),
            data=install_data,
            raw=bytes([0x80, 0xE6, 0x02, 0x00, len(install_data)]) + install_data,
        )

        # Process command
        response = command_processor.process_command(apdu, None)

        # Verify success
        assert response.is_success

    def test_delete_command_processing(
        self,
        command_processor: GPCommandProcessor,
    ) -> None:
        """Test DELETE command processing."""
        # Create DELETE APDU with AID in TLV format
        aid = bytes.fromhex("A000000151000000")
        delete_data = bytes([0x4F, len(aid)]) + aid
        apdu = APDUCommand(
            cla=0x80,
            ins=0xE4,  # DELETE
            p1=0x00,
            p2=0x00,
            lc=len(delete_data),
            data=delete_data,
            raw=bytes([0x80, 0xE4, 0x00, 0x00, len(delete_data)]) + delete_data,
        )

        # Process command
        response = command_processor.process_command(apdu, None)

        # Verify success
        assert response.is_success

    def test_get_status_command_processing(
        self,
        command_processor: GPCommandProcessor,
    ) -> None:
        """Test GET STATUS command processing."""
        # Create GET STATUS APDU (ISD)
        search_criteria = bytes([0x4F, 0x00])  # All AIDs
        apdu = APDUCommand(
            cla=0x80,
            ins=0xF2,  # GET STATUS
            p1=0x80,  # ISD
            p2=0x00,
            lc=len(search_criteria),
            data=search_criteria,
            raw=bytes([0x80, 0xF2, 0x80, 0x00, len(search_criteria)]) + search_criteria,
        )

        # Process command
        response = command_processor.process_command(apdu, None)

        # Should return ISD status or 6A88 if not found
        assert response.sw1 in (0x90, 0x6A)

    def test_unknown_command_handling(
        self,
        command_processor: GPCommandProcessor,
    ) -> None:
        """Test handling of unknown INS codes."""
        # Create unknown command
        apdu = APDUCommand(
            cla=0x00,
            ins=0xFF,  # Unknown INS
            p1=0x00,
            p2=0x00,
            raw=bytes([0x00, 0xFF, 0x00, 0x00]),
        )

        # Process command
        response = command_processor.process_command(apdu, None)

        # Should return SW 6D00 (INS not supported)
        assert response.sw1 == 0x6D
        assert response.sw2 == 0x00

    def test_full_gp_admin_http_exchange(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test full GP Admin HTTP exchange."""
        # Build GP Admin HTTP request
        select_apdu = bytes.fromhex("00A40400 08 A000000151000000")

        # GP Admin format: 2-byte length + APDU
        body = bytes([0x00, len(select_apdu)]) + select_apdu

        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Host: localhost:8443\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: keep-alive\r\n"
            b"\r\n"
        ) + body

        # Parse request
        http_request = http_handler.parse_http_request(raw_request)
        assert http_request.method == "POST"

        # Parse admin request
        admin_request = http_handler.parse_admin_request(http_request)
        assert len(admin_request.apdus) == 1
        assert admin_request.is_keep_alive is True

        # Parse APDU
        apdu = http_handler.parse_apdu(admin_request.apdus[0])
        assert apdu.ins == 0xA4  # SELECT

        # Build response
        apdu_response = APDUResponse(
            data=bytes.fromhex("6F0C840BA000000151000000A50100"),
            sw1=0x90,
            sw2=0x00,
        )
        http_response = http_handler.build_admin_response([apdu_response])

        assert http_response.status_code == HTTPStatus.OK
        assert "Content-Type" in http_response.headers
        assert len(http_response.body) > 0


# =============================================================================
# Key Store Tests
# =============================================================================


class TestKeyStore:
    """Tests for key store functionality."""

    def test_memory_key_store(self) -> None:
        """Test in-memory key store."""
        store = MemoryKeyStore()

        # Add keys
        store.add_key("card_001", bytes.fromhex("01020304"))
        store.add_key("card_002", bytes.fromhex("05060708"))

        # Retrieve keys
        assert store.get_key("card_001") == bytes.fromhex("01020304")
        assert store.get_key("card_002") == bytes.fromhex("05060708")
        assert store.get_key("unknown") is None

        # Check identity existence
        assert store.identity_exists("card_001")
        assert not store.identity_exists("unknown")

    def test_memory_key_store_remove(self) -> None:
        """Test removing keys from memory store."""
        store = MemoryKeyStore()
        store.add_key("card_001", bytes.fromhex("01020304"))

        assert store.identity_exists("card_001")
        store.remove_key("card_001")
        assert not store.identity_exists("card_001")


# =============================================================================
# Event Emitter Tests
# =============================================================================


class TestEventEmitter:
    """Tests for event emitter functionality."""

    def test_event_subscription_and_emission(self) -> None:
        """Test event subscription and emission."""
        emitter = MockEventEmitter()
        received_events = []

        def handler(data):
            received_events.append(data)

        # Subscribe
        sub_id = emitter.subscribe("test_event", handler)
        assert sub_id is not None

        # Emit
        emitter.emit("test_event", {"key": "value"})

        # Verify received
        assert len(received_events) == 1
        assert received_events[0]["key"] == "value"

    def test_wildcard_subscription(self) -> None:
        """Test wildcard event subscription."""
        emitter = MockEventEmitter()
        received_events = []

        def handler(data):
            received_events.append(data)

        # Subscribe to all events
        emitter.subscribe("*", handler)

        # Emit different events
        emitter.emit("event_a", {"type": "a"})
        emitter.emit("event_b", {"type": "b"})

        # Should receive both
        assert len(received_events) == 2

    def test_unsubscribe(self) -> None:
        """Test event unsubscription."""
        emitter = MockEventEmitter()
        received_events = []

        def handler(data):
            received_events.append(data)

        sub_id = emitter.subscribe("test_event", handler)

        # Emit before unsubscribe
        emitter.emit("test_event", {"n": 1})
        assert len(received_events) == 1

        # Unsubscribe
        result = emitter.unsubscribe(sub_id)
        assert result is True

        # Emit after unsubscribe
        emitter.emit("test_event", {"n": 2})
        assert len(received_events) == 1  # Still 1, second not received


# =============================================================================
# HTTP Handler Tests
# =============================================================================


class TestHTTPHandler:
    """Tests for HTTP handler functionality."""

    def test_content_type_validation_valid(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test valid Content-Type header."""
        body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])
        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        admin_request = http_handler.parse_admin_request(http_request)

        assert admin_request is not None

    def test_content_type_validation_invalid(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test invalid Content-Type header."""
        from cardlink.server.http_handler import ContentTypeError

        body = b"test"
        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)

        with pytest.raises(ContentTypeError):
            http_handler.parse_admin_request(http_request)

    def test_apdu_extraction(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test APDU extraction from request body."""
        # Two APDUs in request
        apdu1 = bytes.fromhex("00A40400 08 A000000151000000")
        apdu2 = bytes.fromhex("80F28000 02 4F00")

        body = (
            bytes([0x00, len(apdu1)]) + apdu1 +
            bytes([0x00, len(apdu2)]) + apdu2
        )

        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        admin_request = http_handler.parse_admin_request(http_request)

        assert len(admin_request.apdus) == 2

    def test_response_building(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test HTTP response building."""
        responses = [
            APDUResponse(data=bytes.fromhex("6F08"), sw1=0x90, sw2=0x00),
            APDUResponse(sw1=0x69, sw2=0x85),
        ]

        http_response = http_handler.build_admin_response(responses)

        assert http_response.status_code == 200
        assert "Content-Type" in http_response.headers
        assert http_response.headers["Content-Type"].startswith(
            "application/vnd.globalplatform"
        )

    def test_keep_alive_handling(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test HTTP keep-alive handling."""
        body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])

        # With keep-alive
        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: keep-alive\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        admin_request = http_handler.parse_admin_request(http_request)
        assert admin_request.is_keep_alive is True

        # With close
        raw_request_close = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n"
        ) + body

        http_request_close = http_handler.parse_http_request(raw_request_close)
        admin_request_close = http_handler.parse_admin_request(http_request_close)
        assert admin_request_close.is_keep_alive is False


# =============================================================================
# GP Admin Header Tests (per GPC_SPE_011 Amendment B)
# =============================================================================


class TestGPAdminHeaders:
    """Tests for GP Admin protocol headers per GPC_SPE_011."""

    def test_response_includes_protocol_header(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test that responses include X-Admin-Protocol header."""
        responses = [APDUResponse(sw1=0x90, sw2=0x00)]
        http_response = http_handler.build_admin_response(responses)

        assert "X-Admin-Protocol" in http_response.headers
        assert http_response.headers["X-Admin-Protocol"] == "globalplatform-remote-admin/1.0"

    def test_response_includes_next_uri_header(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test that responses include X-Admin-Next-URI header when provided."""
        responses = [APDUResponse(sw1=0x90, sw2=0x00)]

        # With next_uri
        http_response = http_handler.build_admin_response(
            responses,
            next_uri="/admin/session/abc123"
        )
        assert "X-Admin-Next-URI" in http_response.headers
        assert http_response.headers["X-Admin-Next-URI"] == "/admin/session/abc123"

        # Without next_uri
        http_response_no_uri = http_handler.build_admin_response(responses)
        assert "X-Admin-Next-URI" not in http_response_no_uri.headers

    def test_response_includes_targeted_application_header(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test that responses include X-Admin-Targeted-Application header when provided."""
        responses = [APDUResponse(sw1=0x90, sw2=0x00)]

        # With targeted_application
        http_response = http_handler.build_admin_response(
            responses,
            targeted_application="A000000151000000"
        )
        assert "X-Admin-Targeted-Application" in http_response.headers
        assert http_response.headers["X-Admin-Targeted-Application"] == "A000000151000000"

        # Without targeted_application
        http_response_no_target = http_handler.build_admin_response(responses)
        assert "X-Admin-Targeted-Application" not in http_response_no_target.headers

    def test_session_complete_response(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test HTTP 204 No Content response for session completion."""
        http_response = http_handler.build_session_complete_response()

        assert http_response.status_code == 204
        assert http_response.body == b""
        assert "X-Admin-Protocol" in http_response.headers
        assert http_response.headers["X-Admin-Protocol"] == "globalplatform-remote-admin/1.0"
        assert http_response.headers["Connection"] == "close"

    def test_parse_gp_admin_headers_from_request(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test parsing GP Admin headers from client request."""
        body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])

        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Host: localhost:8443\r\n"
            b"X-Admin-Protocol: globalplatform-remote-admin/1.0\r\n"
            b"X-Admin-From: test_card_001\r\n"
            b"X-Admin-Script-Status: ok\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        admin_request = http_handler.parse_admin_request(http_request)

        assert admin_request.agent_id == "test_card_001"
        assert admin_request.protocol_version == "globalplatform-remote-admin/1.0"
        from cardlink.server.http_handler import ScriptStatus
        assert admin_request.script_status == ScriptStatus.OK
        assert admin_request.is_resume is False

    def test_parse_script_status_error_values(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test parsing different script status values."""
        from cardlink.server.http_handler import ScriptStatus

        test_cases = [
            ("ok", ScriptStatus.OK),
            ("unknown-application", ScriptStatus.UNKNOWN_APPLICATION),
            ("not-a-security-domain", ScriptStatus.NOT_A_SECURITY_DOMAIN),
            ("security-error", ScriptStatus.SECURITY_ERROR),
        ]

        for status_str, expected_status in test_cases:
            body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])
            raw_request = (
                b"POST /admin HTTP/1.1\r\n"
                b"Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0\r\n"
                b"X-Admin-Script-Status: " + status_str.encode() + b"\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"\r\n"
            ) + body

            http_request = http_handler.parse_http_request(raw_request)
            admin_request = http_handler.parse_admin_request(http_request)

            assert admin_request.script_status == expected_status, f"Failed for {status_str}"

    def test_parse_resume_header(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test parsing X-Admin-Resume header."""
        body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])

        # With resume=true
        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0\r\n"
            b"X-Admin-Resume: true\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        admin_request = http_handler.parse_admin_request(http_request)

        assert admin_request.is_resume is True

        # Without resume header
        raw_request_no_resume = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request_no_resume = http_handler.parse_http_request(raw_request_no_resume)
        admin_request_no_resume = http_handler.parse_admin_request(http_request_no_resume)

        assert admin_request_no_resume.is_resume is False

    def test_accepts_client_response_content_type(
        self,
        http_handler: HTTPHandler,
    ) -> None:
        """Test that server accepts R-APDU content type from client."""
        body = bytes([0x00, 0x04, 0x00, 0xA4, 0x04, 0x00])

        # Client sends R-APDU with response content type
        raw_request = (
            b"POST /admin HTTP/1.1\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        ) + body

        http_request = http_handler.parse_http_request(raw_request)
        # Should not raise ContentTypeError
        admin_request = http_handler.parse_admin_request(http_request)
        assert admin_request is not None
