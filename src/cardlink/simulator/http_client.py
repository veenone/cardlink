"""HTTP Admin protocol client.

This module implements the GP Amendment B HTTP Admin protocol for
communication with the PSK-TLS Admin Server.

Implements headers per GlobalPlatform GPC_SPE_011 Amendment B:
- X-Admin-Protocol: Protocol identifier
- X-Admin-From: Agent/card identifier
- X-Admin-Script-Status: Script execution status
- X-Admin-Resume: Session resumption indicator
"""

import logging
import re
from enum import Enum
from typing import Dict, Optional, Tuple

from .psk_tls_client import PSKTLSClient

logger = logging.getLogger(__name__)


# =============================================================================
# GP Admin Protocol Constants (per GPC_SPE_011)
# =============================================================================

# Protocol version header value
GP_ADMIN_PROTOCOL = "globalplatform-remote-admin/1.0"


class ScriptStatus(Enum):
    """Script execution status per GP Amendment B Section 3.4.1.

    Values:
        OK: Script executed successfully.
        UNKNOWN_APPLICATION: Target application not found.
        NOT_A_SECURITY_DOMAIN: Target is not a Security Domain.
        SECURITY_ERROR: Security check failed during script execution.
    """
    OK = "ok"
    UNKNOWN_APPLICATION = "unknown-application"
    NOT_A_SECURITY_DOMAIN = "not-a-security-domain"
    SECURITY_ERROR = "security-error"


class HTTPAdminError(Exception):
    """Base exception for HTTP Admin client errors."""

    pass


class HTTPProtocolError(HTTPAdminError):
    """HTTP protocol error."""

    pass


class HTTPStatusError(HTTPAdminError):
    """HTTP status code indicates an error."""

    def __init__(self, status_code: int, reason: str, body: bytes = b""):
        self.status_code = status_code
        self.reason = reason
        self.body = body
        super().__init__(f"HTTP {status_code} {reason}")


class HTTPAdminClient:
    """HTTP Admin protocol client.

    Implements the GlobalPlatform Amendment B HTTP Admin protocol
    for APDU exchange over TLS-PSK connections.

    Headers implemented per GPC_SPE_011 Section 3.4.1:
    - X-Admin-Protocol: globalplatform-remote-admin/1.0
    - X-Admin-From: Agent/card identifier
    - X-Admin-Script-Status: Script execution status
    - X-Admin-Resume: Session resumption indicator

    Attributes:
        CONTENT_TYPE_REQUEST: Content-Type for R-APDU requests.
        CONTENT_TYPE_RESPONSE: Content-Type for C-APDU responses.

    Example:
        >>> client = HTTPAdminClient(tls_client, agent_id="card_001")
        >>> c_apdu = await client.initial_request()
        >>> while c_apdu:
        ...     r_apdu = process_apdu(c_apdu)
        ...     c_apdu = await client.send_response(r_apdu)
    """

    # GP Admin Content-Types per Section 3.4.1
    CONTENT_TYPE_REQUEST = "application/vnd.globalplatform.card-content-mgt-response;version=1.0"
    CONTENT_TYPE_RESPONSE = "application/vnd.globalplatform.card-content-mgt;version=1.0"

    # HTTP line ending
    CRLF = b"\r\n"

    def __init__(
        self,
        tls_client: PSKTLSClient,
        admin_path: str = "/admin",
        agent_id: Optional[str] = None,
    ):
        """Initialize with TLS client.

        Args:
            tls_client: Connected PSKTLSClient for transport.
            admin_path: URL path for admin endpoint.
            agent_id: Agent identifier for X-Admin-From header.
                     If None, uses PSK identity from tls_client.
        """
        if tls_client is None:
            raise ValueError("tls_client cannot be None")

        self.tls_client = tls_client
        self.admin_path = admin_path
        self._agent_id = agent_id or getattr(tls_client, 'psk_identity', 'unknown')
        self._request_count = 0
        self._script_status: ScriptStatus = ScriptStatus.OK
        self._is_resuming: bool = False
        self._next_uri: Optional[str] = None  # From server X-Admin-Next-URI

    def build_request(
        self,
        body: bytes = b"",
        script_status: Optional[ScriptStatus] = None,
        is_resume: bool = False,
    ) -> bytes:
        """Build HTTP POST request with GP Admin headers.

        Implements headers per GPC_SPE_011 Section 3.4.1:
        - Host: Administration Host
        - X-Admin-Protocol: globalplatform-remote-admin/1.0
        - X-Admin-From: Agent identifier
        - Content-Type: application/vnd.globalplatform.card-content-mgt-response;version=1.0
        - Content-Length: body length
        - X-Admin-Script-Status: ok|unknown-application|not-a-security-domain|security-error
        - X-Admin-Resume: true (when resuming)

        Args:
            body: Request body (R-APDU bytes or empty for initial request).
            script_status: Script execution status for X-Admin-Script-Status header.
                          Uses last set status if None.
            is_resume: If True, adds X-Admin-Resume: true header.

        Returns:
            Complete HTTP request bytes.

        Example:
            >>> request = client.build_request(bytes.fromhex("9000"))
        """
        # Use next_uri if server provided one, otherwise use default admin_path
        path = self._next_uri or self.admin_path
        host = f"{self.tls_client.host}:{self.tls_client.port}"

        # Update status if provided
        if script_status is not None:
            self._script_status = script_status

        # Build headers per GP Amendment B spec
        headers = [
            f"POST {path} HTTP/1.1",
            f"Host: {host}",
            f"X-Admin-Protocol: {GP_ADMIN_PROTOCOL}",
            f"X-Admin-From: {self._agent_id}",
            f"Content-Type: {self.CONTENT_TYPE_REQUEST}",
            f"Accept: {self.CONTENT_TYPE_RESPONSE}",
            f"Content-Length: {len(body)}",
            "Connection: keep-alive",
        ]

        # Add script status when sending R-APDU (not on initial request)
        if body:
            headers.append(f"X-Admin-Script-Status: {self._script_status.value}")

        # Add resume header when resuming a session
        if is_resume or self._is_resuming:
            headers.append("X-Admin-Resume: true")

        # Build request
        request = self.CRLF.join(h.encode("ascii") for h in headers)
        request += self.CRLF + self.CRLF + body

        return request

    def set_script_status(self, status: ScriptStatus) -> None:
        """Set script execution status for subsequent requests.

        Args:
            status: Script execution status.
        """
        self._script_status = status

    def set_resume_mode(self, resuming: bool) -> None:
        """Set resume mode for subsequent requests.

        Args:
            resuming: True if resuming a previous session.
        """
        self._is_resuming = resuming

    @property
    def agent_id(self) -> str:
        """Get agent identifier."""
        return self._agent_id

    @property
    def next_uri(self) -> Optional[str]:
        """Get next URI from server (X-Admin-Next-URI)."""
        return self._next_uri

    def parse_response(self, response: bytes) -> Tuple[int, Dict[str, str], bytes]:
        """Parse HTTP response into status, headers, body.

        Extracts GP Admin headers per GPC_SPE_011 Section 3.4.2:
        - X-Admin-Protocol: Protocol version
        - X-Admin-Next-URI: URI for next request
        - X-Admin-Targeted-Application: Target Security Domain AID

        Args:
            response: Raw HTTP response bytes.

        Returns:
            Tuple of (status_code, headers_dict, body_bytes).

        Raises:
            HTTPProtocolError: If response format is invalid.
        """
        # Find header/body separator
        separator_idx = response.find(b"\r\n\r\n")
        if separator_idx == -1:
            raise HTTPProtocolError("Invalid HTTP response: no header/body separator")

        header_part = response[:separator_idx].decode("ascii", errors="replace")
        body = response[separator_idx + 4:]

        # Parse status line
        lines = header_part.split("\r\n")
        if not lines:
            raise HTTPProtocolError("Invalid HTTP response: empty headers")

        status_match = re.match(r"HTTP/\d\.\d\s+(\d+)\s+(.*)", lines[0])
        if not status_match:
            raise HTTPProtocolError(f"Invalid HTTP status line: {lines[0]}")

        status_code = int(status_match.group(1))
        reason = status_match.group(2)

        # Parse headers
        headers = {}
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key.lower()] = value

        # Extract GP Admin headers
        self._extract_gp_headers(headers)

        # Handle chunked transfer encoding
        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = self._decode_chunked(body)

        return status_code, headers, body

    def _extract_gp_headers(self, headers: Dict[str, str]) -> None:
        """Extract and store GP Admin protocol headers from response.

        Args:
            headers: Parsed response headers (lowercase keys).
        """
        # Extract X-Admin-Next-URI for next request
        next_uri = headers.get("x-admin-next-uri")
        if next_uri:
            self._next_uri = next_uri
            logger.debug(f"Server provided next URI: {next_uri}")

        # Log X-Admin-Targeted-Application if present
        targeted_app = headers.get("x-admin-targeted-application")
        if targeted_app:
            logger.debug(f"Targeted application: {targeted_app}")

        # Verify protocol version
        protocol = headers.get("x-admin-protocol")
        if protocol and protocol != GP_ADMIN_PROTOCOL:
            logger.warning(
                f"Server protocol version mismatch: {protocol} != {GP_ADMIN_PROTOCOL}"
            )

    def _decode_chunked(self, data: bytes) -> bytes:
        """Decode chunked transfer encoding.

        Args:
            data: Chunked encoded data.

        Returns:
            Decoded body bytes.
        """
        result = b""
        remaining = data

        while remaining:
            # Find chunk size line
            line_end = remaining.find(b"\r\n")
            if line_end == -1:
                break

            # Parse chunk size (hex)
            try:
                chunk_size = int(remaining[:line_end].decode("ascii").split(";")[0], 16)
            except ValueError:
                break

            if chunk_size == 0:
                break

            # Extract chunk data
            chunk_start = line_end + 2
            chunk_end = chunk_start + chunk_size
            result += remaining[chunk_start:chunk_end]

            # Move past chunk and CRLF
            remaining = remaining[chunk_end + 2:]

        return result

    async def _receive_response(self) -> bytes:
        """Receive complete HTTP response.

        Returns:
            Complete HTTP response bytes.

        Raises:
            HTTPProtocolError: If response is invalid.
        """
        # Read headers first
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = await self.tls_client.receive(4096)
            if not chunk:
                raise HTTPProtocolError("Connection closed while reading headers")
            response += chunk

        # Parse headers to get content length
        separator_idx = response.find(b"\r\n\r\n")
        header_part = response[:separator_idx].decode("ascii", errors="replace")
        body_start = response[separator_idx + 4:]

        # Find content-length or transfer-encoding
        content_length = None
        chunked = False
        for line in header_part.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
            elif line.lower().startswith("transfer-encoding:"):
                chunked = "chunked" in line.lower()

        # Read remaining body if needed
        if content_length is not None:
            bytes_needed = content_length - len(body_start)
            while bytes_needed > 0:
                chunk = await self.tls_client.receive(min(bytes_needed, 4096))
                if not chunk:
                    break
                response += chunk
                bytes_needed -= len(chunk)
        elif chunked:
            # Read until final chunk (0\r\n\r\n)
            while not response.endswith(b"0\r\n\r\n") and not response.endswith(b"\r\n0\r\n\r\n"):
                chunk = await self.tls_client.receive(4096)
                if not chunk:
                    break
                response += chunk

        return response

    def _extract_first_apdu(self, body: bytes) -> bytes:
        """Extract first C-APDU from length-prefixed body.

        GP Admin format uses length-prefixed APDUs:
        [length (2 bytes big-endian)] [APDU bytes] ...

        Args:
            body: Response body with length-prefixed APDUs.

        Returns:
            First C-APDU bytes, or empty bytes if body is empty.
        """
        if len(body) < 2:
            # Body too short for length prefix, return as-is
            return body

        # Read length prefix (2 bytes, big-endian)
        length = (body[0] << 8) | body[1]

        if length == 0:
            return b""

        if len(body) < 2 + length:
            # Not enough data, return what we have after prefix
            logger.warning(
                f"Body length mismatch: expected {length}, got {len(body) - 2}"
            )
            return body[2:]

        # Extract APDU
        return body[2:2 + length]

    async def initial_request(self) -> bytes:
        """Send initial empty request, receive first C-APDU.

        Returns:
            First C-APDU bytes from server.

        Raises:
            HTTPStatusError: If server returns error status.
            HTTPProtocolError: If protocol error occurs.
        """
        logger.debug("Sending initial request to /admin")

        # Build and send empty POST
        request = self.build_request(b"")
        await self.tls_client.send(request)
        self._request_count += 1

        # Receive and parse response
        response = await self._receive_response()
        status_code, headers, body = self.parse_response(response)

        logger.debug(f"Initial response: HTTP {status_code}, body={len(body)} bytes")

        # Check status
        if status_code == 200:
            # Parse length-prefixed C-APDU
            c_apdu = self._extract_first_apdu(body)
            if c_apdu:
                logger.debug(f"Received C-APDU: {c_apdu.hex().upper()}")
            return c_apdu
        elif status_code == 204:
            # Session complete immediately (unusual but valid)
            return b""
        else:
            raise HTTPStatusError(status_code, "Server error", body)

    def _build_length_prefixed_apdu(self, r_apdu: bytes) -> bytes:
        """Build length-prefixed R-APDU for sending.

        Args:
            r_apdu: Raw R-APDU bytes.

        Returns:
            Length-prefixed R-APDU.
        """
        length = len(r_apdu)
        return bytes([(length >> 8) & 0xFF, length & 0xFF]) + r_apdu

    async def send_response(self, r_apdu: bytes) -> Optional[bytes]:
        """Send R-APDU and receive next C-APDU.

        Args:
            r_apdu: R-APDU bytes to send to server.

        Returns:
            Next C-APDU bytes, or None if session is complete (204 No Content).

        Raises:
            HTTPStatusError: If server returns error status.
            HTTPProtocolError: If protocol error occurs.

        Example:
            >>> c_apdu = await client.send_response(bytes.fromhex("9000"))
            >>> if c_apdu is None:
            ...     print("Session complete")
        """
        logger.debug(f"Sending R-APDU: {r_apdu.hex().upper()}")

        # Build length-prefixed R-APDU body
        body = self._build_length_prefixed_apdu(r_apdu)

        # Build and send POST with R-APDU
        request = self.build_request(body)
        await self.tls_client.send(request)
        self._request_count += 1

        # Receive and parse response
        response = await self._receive_response()
        status_code, headers, body = self.parse_response(response)

        logger.debug(f"Response: HTTP {status_code}, body={len(body)} bytes")

        # Check status
        if status_code == 200:
            # Parse length-prefixed C-APDU
            c_apdu = self._extract_first_apdu(body)
            if c_apdu:
                logger.debug(f"Received C-APDU: {c_apdu.hex().upper()}")
            return c_apdu
        elif status_code == 204:
            logger.info("Session complete (204 No Content)")
            return None
        elif status_code >= 400 and status_code < 500:
            raise HTTPStatusError(status_code, "Client error", body)
        elif status_code >= 500:
            raise HTTPStatusError(status_code, "Server error", body)
        else:
            raise HTTPStatusError(status_code, f"Unexpected status", body)

    async def poll_request(self) -> bytes:
        """Poll for new commands (used in persistent mode).

        Similar to initial_request but with X-Admin-Resume header
        to maintain session context.

        Returns:
            Next C-APDU bytes, or empty bytes if no commands available.

        Raises:
            HTTPStatusError: If server returns error status.
            HTTPProtocolError: If protocol error occurs.
        """
        logger.debug("Polling for new commands")

        # Build and send empty POST with resume header
        request = self.build_request(b"", is_resume=True)
        await self.tls_client.send(request)
        self._request_count += 1

        # Receive and parse response
        response = await self._receive_response()
        status_code, headers, body = self.parse_response(response)

        logger.debug(f"Poll response: HTTP {status_code}, body={len(body)} bytes")

        # Check status
        if status_code == 200:
            # Parse length-prefixed C-APDU
            c_apdu = self._extract_first_apdu(body)
            if c_apdu:
                logger.debug(f"Received C-APDU: {c_apdu.hex().upper()}")
            return c_apdu
        elif status_code == 204:
            # No commands available yet
            return b""
        else:
            raise HTTPStatusError(status_code, "Server error", body)

    @property
    def request_count(self) -> int:
        """Get number of requests sent."""
        return self._request_count
