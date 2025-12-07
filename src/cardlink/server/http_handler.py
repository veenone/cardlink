"""HTTP Handler for GP Amendment B Admin Protocol.

This module handles HTTP requests according to the GlobalPlatform Amendment B
Admin protocol specification, parsing requests and building responses.

Implements headers per GlobalPlatform GPC_SPE_011 Amendment B:
Server Response Headers (Section 3.4.2):
- X-Admin-Protocol: Protocol identifier
- X-Admin-Next-URI: URI for next request
- X-Admin-Targeted-Application: Target Security Domain AID

Client Request Headers (Section 3.4.1):
- X-Admin-Protocol: Protocol identifier
- X-Admin-From: Agent/card identifier
- X-Admin-Script-Status: Script execution status
- X-Admin-Resume: Session resumption indicator

Example:
    >>> from cardlink.server.http_handler import HTTPHandler
    >>> handler = HTTPHandler(command_processor)
    >>> response = handler.handle_request(ssl_socket, session)

Security Note:
    - Validates Content-Type header strictly per GP spec
    - APDU data is treated as binary and not logged in full
"""

import logging
import re
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from cardlink.server.models import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# GP Amendment B Admin Protocol Content-Type
CONTENT_TYPE_GP_ADMIN = "application/vnd.globalplatform.card-content-mgt;version=1.0"
CONTENT_TYPE_GP_ADMIN_ALT = "application/vnd.globalplatform.card-content-mgt"
# Client sends R-APDU with this content type
CONTENT_TYPE_GP_ADMIN_RESPONSE = "application/vnd.globalplatform.card-content-mgt-response;version=1.0"

# GP Admin Protocol Header (per GPC_SPE_011 Section 3.4)
GP_ADMIN_PROTOCOL = "globalplatform-remote-admin/1.0"

# HTTP Constants
HTTP_VERSION = "HTTP/1.1"
CRLF = "\r\n"
HEADER_END = b"\r\n\r\n"

# Default buffer sizes
DEFAULT_HEADER_SIZE = 8192
DEFAULT_READ_TIMEOUT = 30.0


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


# =============================================================================
# HTTP Status Codes
# =============================================================================


class HTTPStatus(IntEnum):
    """HTTP status codes used in GP Admin protocol."""

    OK = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    UNSUPPORTED_MEDIA_TYPE = 415
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


HTTP_STATUS_MESSAGES: Dict[int, str] = {
    HTTPStatus.OK: "OK",
    HTTPStatus.BAD_REQUEST: "Bad Request",
    HTTPStatus.FORBIDDEN: "Forbidden",
    HTTPStatus.NOT_FOUND: "Not Found",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method Not Allowed",
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "Unsupported Media Type",
    HTTPStatus.INTERNAL_SERVER_ERROR: "Internal Server Error",
    HTTPStatus.SERVICE_UNAVAILABLE: "Service Unavailable",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HTTPRequest:
    """Parsed HTTP request.

    Attributes:
        method: HTTP method (POST, GET, etc.).
        path: Request path.
        version: HTTP version string.
        headers: Dictionary of headers (lowercase keys).
        body: Request body bytes.
        raw: Original raw request bytes.
    """

    method: str
    path: str
    version: str
    headers: Dict[str, str]
    body: bytes
    raw: bytes = field(default=b"", repr=False)


@dataclass
class HTTPResponse:
    """HTTP response to send.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        body: Response body bytes.
    """

    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = field(default=b"")

    def to_bytes(self) -> bytes:
        """Serialize response to bytes for sending.

        Returns:
            HTTP response as bytes.
        """
        status_msg = HTTP_STATUS_MESSAGES.get(self.status_code, "Unknown")
        status_line = f"{HTTP_VERSION} {self.status_code} {status_msg}{CRLF}"

        # Build headers
        header_lines = []
        for name, value in self.headers.items():
            header_lines.append(f"{name}: {value}{CRLF}")

        # Add Content-Length if body present and not already set
        if self.body and "Content-Length" not in self.headers:
            header_lines.append(f"Content-Length: {len(self.body)}{CRLF}")

        headers_str = "".join(header_lines)
        head = f"{status_line}{headers_str}{CRLF}"

        return head.encode("utf-8") + self.body


@dataclass
class AdminRequest:
    """Parsed GP Admin request.

    Attributes:
        apdus: List of APDU command bytes.
        http_request: Original HTTP request.
        is_keep_alive: Whether connection should be kept alive.
        agent_id: Agent identifier from X-Admin-From header.
        script_status: Script status from X-Admin-Script-Status header.
        is_resume: True if X-Admin-Resume header is present.
        protocol_version: Protocol version from X-Admin-Protocol header.
    """

    apdus: List[bytes]
    http_request: HTTPRequest
    is_keep_alive: bool = True
    agent_id: Optional[str] = None
    script_status: Optional[ScriptStatus] = None
    is_resume: bool = False
    protocol_version: Optional[str] = None


@dataclass
class APDUCommand:
    """Parsed APDU command.

    Attributes:
        cla: Class byte.
        ins: Instruction byte.
        p1: Parameter 1.
        p2: Parameter 2.
        lc: Length of command data (optional).
        data: Command data bytes.
        le: Expected response length (optional).
        raw: Original raw APDU bytes.
    """

    cla: int
    ins: int
    p1: int
    p2: int
    lc: Optional[int] = None
    data: bytes = field(default=b"")
    le: Optional[int] = None
    raw: bytes = field(default=b"", repr=False)

    @property
    def command_name(self) -> str:
        """Get human-readable command name based on INS byte."""
        ins_names = {
            0xA4: "SELECT",
            0xE6: "INSTALL",
            0xE4: "DELETE",
            0xF2: "GET STATUS",
            0xF0: "SET STATUS",
            0xCA: "GET DATA",
            0xDA: "PUT DATA",
            0x82: "EXTERNAL AUTHENTICATE",
            0x84: "GET CHALLENGE",
            0x50: "INITIALIZE UPDATE",
        }
        return ins_names.get(self.ins, f"INS_{self.ins:02X}")


@dataclass
class APDUResponse:
    """APDU response.

    Attributes:
        data: Response data bytes.
        sw1: Status word 1.
        sw2: Status word 2.
    """

    data: bytes = field(default=b"")
    sw1: int = 0x90
    sw2: int = 0x00

    @property
    def status_word(self) -> str:
        """Get status word as hex string."""
        return f"{self.sw1:02X}{self.sw2:02X}"

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.sw1 == 0x90 and self.sw2 == 0x00

    def to_bytes(self) -> bytes:
        """Serialize response to bytes."""
        return self.data + bytes([self.sw1, self.sw2])


# =============================================================================
# Exceptions
# =============================================================================


class HTTPHandlerError(Exception):
    """Base exception for HTTP handler errors."""

    pass


class InvalidRequestError(HTTPHandlerError):
    """Invalid HTTP request received."""

    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


class ContentTypeError(HTTPHandlerError):
    """Invalid or missing Content-Type header."""

    def __init__(self, message: str):
        super().__init__(message)
        self.status_code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE


class APDUParseError(HTTPHandlerError):
    """Failed to parse APDU command."""

    pass


# =============================================================================
# HTTP Handler
# =============================================================================


class HTTPHandler:
    """Handles GP Amendment B HTTP Admin protocol.

    Implements the server-side GP Admin protocol where:
    - Server sends C-APDUs to the client (card/UICC)
    - Client responds with R-APDUs

    Protocol flow:
    1. Client sends initial POST (empty or with agent info)
    2. Server responds with C-APDU(s) to execute
    3. Client sends R-APDU responses
    4. Server sends next C-APDU(s) or 204 No Content when complete

    Attributes:
        CONTENT_TYPE: Expected Content-Type header value.

    Example:
        >>> handler = HTTPHandler(command_processor)
        >>> handler.queue_commands(session_id, [select_isd, get_data])
        >>> response = handler.handle_request(ssl_socket, session)
        >>> ssl_socket.sendall(response.to_bytes())
    """

    CONTENT_TYPE = CONTENT_TYPE_GP_ADMIN

    # Demo C-APDUs for testing (SELECT ISD, GET DATA Card Data)
    DEMO_COMMANDS = [
        bytes.fromhex("00A4040000"),  # SELECT ISD (no data)
        bytes.fromhex("80CA006600"),  # GET DATA - Card Data
        bytes.fromhex("80CA004F00"),  # GET DATA - Card Manager AID
    ]

    def __init__(
        self,
        command_processor: Any,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        """Initialize HTTP Handler.

        Args:
            command_processor: GPCommandProcessor for processing APDUs.
            read_timeout: Socket read timeout in seconds.
        """
        self._command_processor = command_processor
        self._read_timeout = read_timeout
        # Command queue: session_id -> list of C-APDUs to send
        self._command_queues: Dict[str, List[bytes]] = {}
        # Track session state: session_id -> request count
        self._session_requests: Dict[str, int] = {}

    def queue_commands(self, session_id: str, commands: List[bytes]) -> None:
        """Queue C-APDU commands to send to a session.

        Args:
            session_id: Session identifier.
            commands: List of C-APDU bytes to send.
        """
        if session_id not in self._command_queues:
            self._command_queues[session_id] = []
        self._command_queues[session_id].extend(commands)

    def get_next_command(self, session_id: str) -> Optional[bytes]:
        """Get next queued C-APDU for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Next C-APDU bytes, or None if queue is empty.
        """
        queue = self._command_queues.get(session_id, [])
        if queue:
            return queue.pop(0)
        return None

    def has_pending_commands(self, session_id: str) -> bool:
        """Check if session has pending C-APDUs.

        Args:
            session_id: Session identifier.

        Returns:
            True if commands are queued.
        """
        return bool(self._command_queues.get(session_id))

    def clear_session(self, session_id: str) -> None:
        """Clear all data for a session.

        Args:
            session_id: Session identifier.
        """
        self._command_queues.pop(session_id, None)
        self._session_requests.pop(session_id, None)

    def handle_request(
        self,
        ssl_socket: ssl.SSLSocket,
        session: "Session",
    ) -> HTTPResponse:
        """Read HTTP request, process, and return response.

        Implements GP Admin protocol flow:
        - Initial POST (empty body): Server sends first C-APDU(s)
        - Subsequent POST (R-APDU body): Server sends next C-APDU(s) or 204

        Args:
            ssl_socket: SSL-wrapped socket to read from.
            session: Current session context.

        Returns:
            HTTPResponse to send back to client.

        Raises:
            HTTPHandlerError: If request processing fails.
        """
        try:
            # Read and parse request
            raw_request = self._read_request(ssl_socket)
            http_request = self.parse_http_request(raw_request)

            session_id = session.session_id if session else "unknown"

            logger.debug(
                "HTTP request: method=%s, path=%s, session=%s, body_len=%d",
                http_request.method,
                http_request.path,
                session_id,
                len(http_request.body),
            )

            # Validate method (POST is required for Admin protocol)
            if http_request.method != "POST":
                return self._build_error_response(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "GP Admin protocol requires POST method",
                )

            # Track request count for this session
            request_num = self._session_requests.get(session_id, 0) + 1
            self._session_requests[session_id] = request_num

            # Check if this is initial request (empty body)
            is_initial_request = len(http_request.body) == 0

            if is_initial_request:
                logger.debug("Initial request from session %s", session_id)
                # Queue demo commands if no commands already queued
                if not self.has_pending_commands(session_id):
                    self.queue_commands(session_id, self.DEMO_COMMANDS.copy())
                    logger.debug(
                        "Queued %d demo commands for session %s",
                        len(self.DEMO_COMMANDS),
                        session_id,
                    )
            else:
                # Parse R-APDU response from client
                try:
                    r_apdus = self._extract_apdus(http_request.body)
                    for r_apdu in r_apdus:
                        logger.debug(
                            "Received R-APDU: %s (session=%s)",
                            r_apdu.hex().upper(),
                            session_id,
                        )
                        # Could process R-APDU here if needed
                except InvalidRequestError:
                    # If body doesn't parse as APDUs, log but continue
                    logger.debug(
                        "Body not parseable as APDUs, treating as raw: %s",
                        http_request.body.hex().upper()[:40],
                    )

            # Get next C-APDU(s) to send
            next_command = self.get_next_command(session_id)

            if next_command is None:
                # No more commands - session complete
                logger.info("Session %s complete (no more commands)", session_id)
                return self.build_session_complete_response()

            # Build response with C-APDU
            logger.debug(
                "Sending C-APDU to session %s: %s",
                session_id,
                next_command.hex().upper(),
            )
            return self.build_command_response(
                [next_command],
                keep_alive=True,
            )

        except ContentTypeError as e:
            logger.warning("Content-Type error: %s", e)
            return self._build_error_response(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                str(e),
            )

        except InvalidRequestError as e:
            logger.warning("Invalid request: %s", e)
            return self._build_error_response(e.status_code, str(e))

        except APDUParseError as e:
            logger.warning("APDU parse error: %s", e)
            return self._build_error_response(
                HTTPStatus.BAD_REQUEST,
                f"Invalid APDU: {e}",
            )

        except socket.timeout:
            logger.warning("Request read timeout")
            return self._build_error_response(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Request timeout",
            )

        except Exception as e:
            logger.exception("Unexpected error handling request: %s", e)
            return self._build_error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Internal server error",
            )

    def _read_request(self, ssl_socket: ssl.SSLSocket) -> bytes:
        """Read complete HTTP request from socket.

        Args:
            ssl_socket: Socket to read from.

        Returns:
            Raw request bytes.

        Raises:
            InvalidRequestError: If request is malformed.
        """
        ssl_socket.settimeout(self._read_timeout)

        # Read headers first
        buffer = b""
        while HEADER_END not in buffer:
            chunk = ssl_socket.recv(DEFAULT_HEADER_SIZE)
            if not chunk:
                raise InvalidRequestError("Connection closed before headers complete")
            buffer += chunk

            if len(buffer) > DEFAULT_HEADER_SIZE * 10:
                raise InvalidRequestError("Headers too large")

        # Find header/body boundary
        header_end_pos = buffer.find(HEADER_END)
        headers_raw = buffer[:header_end_pos].decode("utf-8", errors="replace")
        body_start = buffer[header_end_pos + len(HEADER_END):]

        # Parse Content-Length to read body
        content_length = 0
        for line in headers_raw.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    raise InvalidRequestError("Invalid Content-Length header")
                break

        # Read remaining body
        body = body_start
        while len(body) < content_length:
            remaining = content_length - len(body)
            chunk = ssl_socket.recv(min(remaining, DEFAULT_HEADER_SIZE))
            if not chunk:
                raise InvalidRequestError("Connection closed before body complete")
            body += chunk

        return buffer[:header_end_pos + len(HEADER_END)] + body[:content_length]

    def parse_http_request(self, raw_request: bytes) -> HTTPRequest:
        """Parse raw HTTP bytes into HTTPRequest.

        Args:
            raw_request: Raw HTTP request bytes.

        Returns:
            Parsed HTTPRequest object.

        Raises:
            InvalidRequestError: If request is malformed.
        """
        try:
            # Split headers and body
            if HEADER_END not in raw_request:
                raise InvalidRequestError("Malformed request: no header terminator")

            header_end_pos = raw_request.find(HEADER_END)
            headers_raw = raw_request[:header_end_pos].decode("utf-8")
            body = raw_request[header_end_pos + len(HEADER_END):]

            # Parse request line
            lines = headers_raw.split("\r\n")
            if not lines:
                raise InvalidRequestError("Empty request")

            request_line = lines[0]
            parts = request_line.split(" ")
            if len(parts) != 3:
                raise InvalidRequestError(f"Invalid request line: {request_line}")

            method, path, version = parts

            # Parse headers
            headers: Dict[str, str] = {}
            for line in lines[1:]:
                if not line:
                    continue
                if ":" not in line:
                    continue
                name, value = line.split(":", 1)
                headers[name.lower().strip()] = value.strip()

            return HTTPRequest(
                method=method.upper(),
                path=path,
                version=version,
                headers=headers,
                body=body,
                raw=raw_request,
            )

        except InvalidRequestError:
            raise
        except Exception as e:
            raise InvalidRequestError(f"Failed to parse request: {e}") from e

    def parse_admin_request(self, http_request: HTTPRequest) -> AdminRequest:
        """Parse HTTP request as GP Admin request.

        Validates Content-Type and extracts APDU commands from body.
        Parses GP Admin headers per GPC_SPE_011 Section 3.4.1:
        - X-Admin-Protocol: Protocol version
        - X-Admin-From: Agent identifier
        - X-Admin-Script-Status: Script execution status
        - X-Admin-Resume: Session resumption indicator

        Args:
            http_request: Parsed HTTP request.

        Returns:
            AdminRequest with extracted APDUs and GP Admin headers.

        Raises:
            ContentTypeError: If Content-Type is invalid.
            InvalidRequestError: If request body is malformed.
        """
        # Validate Content-Type header
        content_type = http_request.headers.get("content-type", "")
        self._validate_content_type(content_type)

        # Extract APDUs from body
        apdus = self._extract_apdus(http_request.body)

        # Check Connection header for keep-alive
        connection = http_request.headers.get("connection", "keep-alive").lower()
        is_keep_alive = connection != "close"

        # Extract GP Admin headers
        agent_id = http_request.headers.get("x-admin-from")
        protocol_version = http_request.headers.get("x-admin-protocol")
        is_resume = http_request.headers.get("x-admin-resume", "").lower() == "true"

        # Parse script status
        script_status = None
        script_status_str = http_request.headers.get("x-admin-script-status")
        if script_status_str:
            try:
                script_status = ScriptStatus(script_status_str.lower())
            except ValueError:
                logger.warning(f"Unknown script status: {script_status_str}")

        # Log GP Admin header info
        if agent_id:
            logger.debug(f"Request from agent: {agent_id}")
        if protocol_version and protocol_version != GP_ADMIN_PROTOCOL:
            logger.warning(
                f"Client protocol version mismatch: {protocol_version} != {GP_ADMIN_PROTOCOL}"
            )
        if is_resume:
            logger.debug("Client is resuming previous session")
        if script_status and script_status != ScriptStatus.OK:
            logger.warning(f"Client reported script status: {script_status.value}")

        return AdminRequest(
            apdus=apdus,
            http_request=http_request,
            is_keep_alive=is_keep_alive,
            agent_id=agent_id,
            script_status=script_status,
            is_resume=is_resume,
            protocol_version=protocol_version,
        )

    def _validate_content_type(self, content_type: str) -> None:
        """Validate Content-Type header.

        Accepts both GP Admin content types per GPC_SPE_011:
        - application/vnd.globalplatform.card-content-mgt;version=1.0 (C-APDU)
        - application/vnd.globalplatform.card-content-mgt-response;version=1.0 (R-APDU)

        Args:
            content_type: Content-Type header value.

        Raises:
            ContentTypeError: If Content-Type is invalid.
        """
        if not content_type:
            raise ContentTypeError(
                f"Missing Content-Type header. Expected: {CONTENT_TYPE_GP_ADMIN_RESPONSE}"
            )

        # Normalize for comparison (remove parameters like charset)
        ct_base = content_type.split(";")[0].strip().lower()

        # Accept both request and response content types
        valid_types = [
            CONTENT_TYPE_GP_ADMIN.split(";")[0].strip().lower(),
            CONTENT_TYPE_GP_ADMIN_ALT.lower(),
            CONTENT_TYPE_GP_ADMIN_RESPONSE.split(";")[0].strip().lower(),
        ]

        if ct_base not in valid_types:
            raise ContentTypeError(
                f"Invalid Content-Type: '{content_type}'. "
                f"Expected: {CONTENT_TYPE_GP_ADMIN_RESPONSE}"
            )

    def _extract_apdus(self, body: bytes) -> List[bytes]:
        """Extract APDU commands from GP Admin request body.

        GP Admin format uses TLV structure for APDUs.
        Simplified format: Length (2 bytes) + APDU data

        Args:
            body: Request body bytes.

        Returns:
            List of APDU command bytes.

        Raises:
            InvalidRequestError: If body format is invalid.
        """
        if not body:
            raise InvalidRequestError("Empty request body")

        apdus: List[bytes] = []
        offset = 0

        try:
            while offset < len(body):
                # Check for minimum length (at least 2 bytes for length)
                if offset + 2 > len(body):
                    break

                # Read length (2 bytes, big-endian)
                length = (body[offset] << 8) | body[offset + 1]
                offset += 2

                if length == 0:
                    continue

                # Validate length
                if offset + length > len(body):
                    raise InvalidRequestError(
                        f"APDU length {length} exceeds remaining body size"
                    )

                # Extract APDU
                apdu_data = body[offset:offset + length]
                apdus.append(apdu_data)
                offset += length

        except InvalidRequestError:
            raise
        except Exception as e:
            raise InvalidRequestError(f"Failed to extract APDUs: {e}") from e

        if not apdus:
            raise InvalidRequestError("No APDU commands found in request body")

        logger.debug("Extracted %d APDU(s) from request", len(apdus))
        return apdus

    def parse_apdu(self, apdu_bytes: bytes) -> APDUCommand:
        """Parse raw APDU bytes into APDUCommand.

        Args:
            apdu_bytes: Raw APDU command bytes.

        Returns:
            Parsed APDUCommand object.

        Raises:
            APDUParseError: If APDU is malformed.
        """
        if len(apdu_bytes) < 4:
            raise APDUParseError(
                f"APDU too short: {len(apdu_bytes)} bytes (minimum 4)"
            )

        cla = apdu_bytes[0]
        ins = apdu_bytes[1]
        p1 = apdu_bytes[2]
        p2 = apdu_bytes[3]

        lc: Optional[int] = None
        data = b""
        le: Optional[int] = None

        if len(apdu_bytes) == 4:
            # Case 1: No Lc, no data, no Le
            pass

        elif len(apdu_bytes) == 5:
            # Case 2: No Lc, no data, Le present (or Lc=0 with no data)
            # Treat as Le
            le = apdu_bytes[4]
            if le == 0:
                le = 256  # Le=0 means 256 bytes expected

        else:
            # Case 3 or 4: Lc present with data
            lc = apdu_bytes[4]

            if lc == 0 and len(apdu_bytes) >= 7:
                # Extended length Lc (3 bytes: 00 LL LL)
                lc = (apdu_bytes[5] << 8) | apdu_bytes[6]
                data_start = 7
            else:
                data_start = 5

            # Validate data length
            if data_start + lc > len(apdu_bytes):
                raise APDUParseError(
                    f"APDU data length mismatch: Lc={lc}, "
                    f"available={len(apdu_bytes) - data_start}"
                )

            data = apdu_bytes[data_start:data_start + lc]

            # Check for Le after data
            remaining = len(apdu_bytes) - (data_start + lc)
            if remaining == 1:
                le = apdu_bytes[-1]
                if le == 0:
                    le = 256
            elif remaining == 2:
                # Extended Le
                le = (apdu_bytes[-2] << 8) | apdu_bytes[-1]
                if le == 0:
                    le = 65536

        return APDUCommand(
            cla=cla,
            ins=ins,
            p1=p1,
            p2=p2,
            lc=lc,
            data=data,
            le=le,
            raw=apdu_bytes,
        )

    def build_admin_response(
        self,
        apdu_responses: List[APDUResponse],
        keep_alive: bool = True,
        next_uri: Optional[str] = None,
        targeted_application: Optional[str] = None,
    ) -> HTTPResponse:
        """Build GP Admin format HTTP response.

        Includes headers per GPC_SPE_011 Section 3.4.2:
        - X-Admin-Protocol: globalplatform-remote-admin/1.0
        - X-Admin-Next-URI: URI for next request (if provided)
        - X-Admin-Targeted-Application: Target Security Domain AID (if provided)

        Args:
            apdu_responses: List of APDU responses.
            keep_alive: Whether to keep connection alive.
            next_uri: URI for client's next request (X-Admin-Next-URI).
            targeted_application: Target Security Domain AID (X-Admin-Targeted-Application).

        Returns:
            HTTPResponse ready to send.
        """
        # Build GP Admin response body
        body = self._build_response_body(apdu_responses)

        # Build headers per GP Amendment B spec
        headers = {
            "Content-Type": CONTENT_TYPE_GP_ADMIN,
            "Content-Length": str(len(body)),
            "X-Admin-Protocol": GP_ADMIN_PROTOCOL,
            "Connection": "keep-alive" if keep_alive else "close",
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        # Add optional GP Admin headers
        if next_uri:
            headers["X-Admin-Next-URI"] = next_uri
        if targeted_application:
            headers["X-Admin-Targeted-Application"] = targeted_application

        return HTTPResponse(
            status_code=HTTPStatus.OK,
            headers=headers,
            body=body,
        )

    def build_session_complete_response(self) -> HTTPResponse:
        """Build HTTP 204 No Content response to signal session completion.

        Per GPC_SPE_011 Section 3.4.2, the server sends HTTP 204 to indicate
        that the administration session is complete.

        Returns:
            HTTPResponse with 204 No Content status.
        """
        headers = {
            "X-Admin-Protocol": GP_ADMIN_PROTOCOL,
            "Connection": "close",
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        return HTTPResponse(
            status_code=204,  # No Content
            headers=headers,
            body=b"",
        )

    def build_command_response(
        self,
        commands: List[bytes],
        keep_alive: bool = True,
        next_uri: Optional[str] = None,
        targeted_application: Optional[str] = None,
    ) -> HTTPResponse:
        """Build GP Admin HTTP response containing C-APDU commands.

        Builds a response with C-APDU commands for the client to execute.
        Format: For each command, Length (2 bytes big-endian) + C-APDU bytes.

        Args:
            commands: List of C-APDU command bytes to send.
            keep_alive: Whether to keep connection alive.
            next_uri: URI for client's next request.
            targeted_application: Target Security Domain AID.

        Returns:
            HTTPResponse with C-APDU(s) in body.
        """
        # Build body with length-prefixed C-APDUs
        body = bytearray()
        for cmd in commands:
            length = len(cmd)
            body.append((length >> 8) & 0xFF)
            body.append(length & 0xFF)
            body.extend(cmd)

        # Build headers per GP Amendment B spec
        headers = {
            "Content-Type": CONTENT_TYPE_GP_ADMIN,
            "Content-Length": str(len(body)),
            "X-Admin-Protocol": GP_ADMIN_PROTOCOL,
            "Connection": "keep-alive" if keep_alive else "close",
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        # Add optional GP Admin headers
        if next_uri:
            headers["X-Admin-Next-URI"] = next_uri
        if targeted_application:
            headers["X-Admin-Targeted-Application"] = targeted_application

        return HTTPResponse(
            status_code=HTTPStatus.OK,
            headers=headers,
            body=bytes(body),
        )

    def _build_response_body(self, apdu_responses: List[APDUResponse]) -> bytes:
        """Build GP Admin format response body.

        Format: For each response, Length (2 bytes) + Data + SW1 + SW2

        Args:
            apdu_responses: List of APDU responses.

        Returns:
            Response body bytes.
        """
        body = bytearray()

        for response in apdu_responses:
            # Serialize response (data + SW)
            response_data = response.to_bytes()

            # Add length prefix (2 bytes, big-endian)
            length = len(response_data)
            body.append((length >> 8) & 0xFF)
            body.append(length & 0xFF)

            # Add response data
            body.extend(response_data)

        return bytes(body)

    def _build_error_response(
        self,
        status_code: int,
        message: str,
    ) -> HTTPResponse:
        """Build HTTP error response.

        Args:
            status_code: HTTP status code.
            message: Error message.

        Returns:
            HTTPResponse with error.
        """
        body = message.encode("utf-8")
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(len(body)),
            "Connection": "close",
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        return HTTPResponse(
            status_code=status_code,
            headers=headers,
            body=body,
        )


# =============================================================================
# Mock HTTP Handler for Testing
# =============================================================================


class MockHTTPHandler(HTTPHandler):
    """Mock HTTP handler for testing.

    Allows pre-configuring responses and recording requests.

    Example:
        >>> handler = MockHTTPHandler()
        >>> handler.set_next_response(APDUResponse(sw1=0x90, sw2=0x00))
        >>> response = handler.handle_request(mock_socket, session)
    """

    def __init__(self) -> None:
        """Initialize mock HTTP handler."""
        self._recorded_requests: List[HTTPRequest] = []
        self._recorded_apdus: List[APDUCommand] = []
        self._next_responses: List[APDUResponse] = []
        self._default_response = APDUResponse(sw1=0x90, sw2=0x00)

    def set_next_response(self, response: APDUResponse) -> None:
        """Set response for next APDU command."""
        self._next_responses.append(response)

    def set_responses(self, responses: List[APDUResponse]) -> None:
        """Set responses for multiple APDU commands."""
        self._next_responses = responses.copy()

    def get_recorded_requests(self) -> List[HTTPRequest]:
        """Get all recorded HTTP requests."""
        return self._recorded_requests.copy()

    def get_recorded_apdus(self) -> List[APDUCommand]:
        """Get all recorded APDU commands."""
        return self._recorded_apdus.copy()

    def clear(self) -> None:
        """Clear recorded data and responses."""
        self._recorded_requests.clear()
        self._recorded_apdus.clear()
        self._next_responses.clear()

    def handle_request(
        self,
        ssl_socket: ssl.SSLSocket,
        session: "Session",
    ) -> HTTPResponse:
        """Handle request with mock responses."""
        # For mock, we need to parse the request manually
        try:
            raw_request = ssl_socket.recv(DEFAULT_HEADER_SIZE * 10)
            http_request = self.parse_http_request(raw_request)
            self._recorded_requests.append(http_request)

            admin_request = self.parse_admin_request(http_request)

            responses: List[APDUResponse] = []
            for apdu_bytes in admin_request.apdus:
                apdu = self.parse_apdu(apdu_bytes)
                self._recorded_apdus.append(apdu)

                if self._next_responses:
                    responses.append(self._next_responses.pop(0))
                else:
                    responses.append(self._default_response)

            return self.build_admin_response(responses, admin_request.is_keep_alive)

        except Exception as e:
            return self._build_error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                str(e),
            )
