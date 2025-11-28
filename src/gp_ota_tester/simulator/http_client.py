"""HTTP Admin protocol client.

This module implements the GP Amendment B HTTP Admin protocol for
communication with the PSK-TLS Admin Server.
"""

import logging
import re
from typing import Dict, Optional, Tuple

from .psk_tls_client import PSKTLSClient

logger = logging.getLogger(__name__)


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

    Attributes:
        CONTENT_TYPE_REQUEST: Content-Type for R-APDU requests.
        CONTENT_TYPE_RESPONSE: Content-Type for C-APDU responses.

    Example:
        >>> client = HTTPAdminClient(tls_client)
        >>> c_apdu = await client.initial_request()
        >>> while c_apdu:
        ...     r_apdu = process_apdu(c_apdu)
        ...     c_apdu = await client.send_response(r_apdu)
    """

    # GP Admin Content-Types
    CONTENT_TYPE_REQUEST = "application/vnd.globalplatform.card-content-mgt-response;version=1.0"
    CONTENT_TYPE_RESPONSE = "application/vnd.globalplatform.card-content-mgt;version=1.0"

    # HTTP line ending
    CRLF = b"\r\n"

    def __init__(self, tls_client: PSKTLSClient, admin_path: str = "/admin"):
        """Initialize with TLS client.

        Args:
            tls_client: Connected PSKTLSClient for transport.
            admin_path: URL path for admin endpoint.
        """
        if tls_client is None:
            raise ValueError("tls_client cannot be None")

        self.tls_client = tls_client
        self.admin_path = admin_path
        self._request_count = 0

    def build_request(self, body: bytes = b"") -> bytes:
        """Build HTTP POST request with GP Admin headers.

        Args:
            body: Request body (R-APDU bytes or empty for initial request).

        Returns:
            Complete HTTP request bytes.

        Example:
            >>> request = client.build_request(bytes.fromhex("9000"))
        """
        host = f"{self.tls_client.host}:{self.tls_client.port}"

        headers = [
            f"POST {self.admin_path} HTTP/1.1",
            f"Host: {host}",
            f"Content-Type: {self.CONTENT_TYPE_REQUEST}",
            f"Accept: {self.CONTENT_TYPE_RESPONSE}",
            f"Content-Length: {len(body)}",
            "Connection: keep-alive",
        ]

        # Build request
        request = self.CRLF.join(h.encode("ascii") for h in headers)
        request += self.CRLF + self.CRLF + body

        return request

    def parse_response(self, response: bytes) -> Tuple[int, Dict[str, str], bytes]:
        """Parse HTTP response into status, headers, body.

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

        # Handle chunked transfer encoding
        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = self._decode_chunked(body)

        return status_code, headers, body

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
            return body
        elif status_code == 204:
            # Session complete immediately (unusual but valid)
            return b""
        else:
            raise HTTPStatusError(status_code, "Server error", body)

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

        # Build and send POST with R-APDU
        request = self.build_request(r_apdu)
        await self.tls_client.send(request)
        self._request_count += 1

        # Receive and parse response
        response = await self._receive_response()
        status_code, headers, body = self.parse_response(response)

        logger.debug(f"Response: HTTP {status_code}, body={len(body)} bytes")

        # Check status
        if status_code == 200:
            if body:
                logger.debug(f"Received C-APDU: {body.hex().upper()}")
            return body
        elif status_code == 204:
            logger.info("Session complete (204 No Content)")
            return None
        elif status_code >= 400 and status_code < 500:
            raise HTTPStatusError(status_code, "Client error", body)
        elif status_code >= 500:
            raise HTTPStatusError(status_code, "Server error", body)
        else:
            raise HTTPStatusError(status_code, f"Unexpected status", body)

    @property
    def request_count(self) -> int:
        """Get number of requests sent."""
        return self._request_count
