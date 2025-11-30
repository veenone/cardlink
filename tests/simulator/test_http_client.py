"""Tests for HTTP Admin protocol client headers.

Tests for GP Admin protocol headers per GPC_SPE_011 Amendment B.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from cardlink.simulator.http_client import (
    HTTPAdminClient,
    ScriptStatus,
    GP_ADMIN_PROTOCOL,
)


class MockTLSClient:
    """Mock TLS client for testing."""

    def __init__(self, host: str = "localhost", port: int = 8443):
        self.host = host
        self.port = port
        self.psk_identity = "test_card_001"


class TestHTTPAdminClientHeaders:
    """Tests for HTTP Admin client GP Admin headers."""

    def test_build_request_includes_protocol_header(self):
        """Test that requests include X-Admin-Protocol header."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert f"X-Admin-Protocol: {GP_ADMIN_PROTOCOL}" in request_str

    def test_build_request_includes_agent_id_header(self):
        """Test that requests include X-Admin-From header."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client, agent_id="my_card_123")

        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "X-Admin-From: my_card_123" in request_str

    def test_build_request_uses_psk_identity_as_default_agent_id(self):
        """Test that X-Admin-From defaults to PSK identity."""
        tls_client = MockTLSClient()
        tls_client.psk_identity = "card_from_psk"
        client = HTTPAdminClient(tls_client)

        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "X-Admin-From: card_from_psk" in request_str

    def test_build_request_includes_script_status_with_body(self):
        """Test that requests include X-Admin-Script-Status when body is present."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        # With body (R-APDU response)
        request = client.build_request(b"\x90\x00", script_status=ScriptStatus.OK)
        # Split headers from body to decode only the header part
        header_end = request.find(b"\r\n\r\n")
        headers_str = request[:header_end].decode("ascii")

        assert "X-Admin-Script-Status: ok" in headers_str

    def test_build_request_excludes_script_status_without_body(self):
        """Test that requests exclude X-Admin-Script-Status for initial request."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        # Empty body (initial request)
        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "X-Admin-Script-Status" not in request_str

    def test_build_request_all_script_status_values(self):
        """Test all script status values are correctly formatted."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        test_cases = [
            (ScriptStatus.OK, "ok"),
            (ScriptStatus.UNKNOWN_APPLICATION, "unknown-application"),
            (ScriptStatus.NOT_A_SECURITY_DOMAIN, "not-a-security-domain"),
            (ScriptStatus.SECURITY_ERROR, "security-error"),
        ]

        for status, expected_str in test_cases:
            request = client.build_request(b"\x90\x00", script_status=status)
            # Split headers from body to decode only the header part
            header_end = request.find(b"\r\n\r\n")
            headers_str = request[:header_end].decode("ascii")

            assert f"X-Admin-Script-Status: {expected_str}" in headers_str, \
                f"Failed for {status}"

    def test_build_request_includes_resume_header(self):
        """Test that requests include X-Admin-Resume when resuming."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        # With resume flag
        request = client.build_request(b"", is_resume=True)
        request_str = request.decode("ascii")

        assert "X-Admin-Resume: true" in request_str

    def test_build_request_excludes_resume_header_by_default(self):
        """Test that requests exclude X-Admin-Resume by default."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "X-Admin-Resume" not in request_str

    def test_set_resume_mode_affects_requests(self):
        """Test that set_resume_mode affects subsequent requests."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        client.set_resume_mode(True)
        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "X-Admin-Resume: true" in request_str

    def test_build_request_content_type(self):
        """Test correct Content-Type for client requests."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        request = client.build_request(b"")
        request_str = request.decode("ascii")

        assert "Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0" in request_str

    def test_build_request_uses_next_uri_from_server(self):
        """Test that client uses X-Admin-Next-URI from server response."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        # Simulate server providing next URI
        client._next_uri = "/admin/session/abc123"

        request = client.build_request(b"\x90\x00")
        # Split headers from body to decode only the header part
        header_end = request.find(b"\r\n\r\n")
        headers_str = request[:header_end].decode("ascii")

        assert "POST /admin/session/abc123 HTTP/1.1" in headers_str


class TestHTTPAdminClientResponseParsing:
    """Tests for parsing GP Admin headers from server responses."""

    def test_parse_response_extracts_next_uri(self):
        """Test extraction of X-Admin-Next-URI from response."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"X-Admin-Protocol: globalplatform-remote-admin/1.0\r\n"
            b"X-Admin-Next-URI: /admin/session/xyz789\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: 4\r\n"
            b"\r\n"
            b"\x00\x02\x90\x00"
        )

        status_code, headers, body = client.parse_response(response)

        assert status_code == 200
        assert client.next_uri == "/admin/session/xyz789"

    def test_parse_response_extracts_targeted_application(self):
        """Test extraction of X-Admin-Targeted-Application from response."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"X-Admin-Protocol: globalplatform-remote-admin/1.0\r\n"
            b"X-Admin-Targeted-Application: A000000151000000\r\n"
            b"Content-Type: application/vnd.globalplatform.card-content-mgt;version=1.0\r\n"
            b"Content-Length: 4\r\n"
            b"\r\n"
            b"\x00\x02\x90\x00"
        )

        status_code, headers, body = client.parse_response(response)

        assert status_code == 200
        assert headers.get("x-admin-targeted-application") == "A000000151000000"

    def test_agent_id_property(self):
        """Test agent_id property returns correct value."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client, agent_id="custom_agent")

        assert client.agent_id == "custom_agent"

    def test_set_script_status(self):
        """Test set_script_status method."""
        tls_client = MockTLSClient()
        client = HTTPAdminClient(tls_client)

        client.set_script_status(ScriptStatus.SECURITY_ERROR)

        # Build request to verify status is used
        request = client.build_request(b"\x90\x00")
        # Split headers from body to decode only the header part
        header_end = request.find(b"\r\n\r\n")
        headers_str = request[:header_end].decode("ascii")

        assert "X-Admin-Script-Status: security-error" in headers_str
