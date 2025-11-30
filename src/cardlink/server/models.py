"""Server models and data structures.

This module defines dataclasses and enums for the PSK-TLS Admin Server,
including session state management, TLS session info, and APDU exchange tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums (Tasks 5-8)
# =============================================================================


class SessionState(Enum):
    """Session lifecycle states.

    States:
        HANDSHAKING: TLS handshake in progress.
        CONNECTED: TLS connection established, awaiting first request.
        ACTIVE: Session is actively processing requests.
        CLOSED: Session has been terminated.
    """

    HANDSHAKING = "handshaking"
    CONNECTED = "connected"
    ACTIVE = "active"
    CLOSED = "closed"


class CloseReason(Enum):
    """Reason for session closure.

    Reasons:
        NORMAL: Clean shutdown initiated by client or server.
        TIMEOUT: Session timed out due to inactivity.
        ERROR: Session closed due to an error.
        CLIENT_DISCONNECT: Client disconnected unexpectedly.
        SERVER_SHUTDOWN: Server is shutting down.
        HANDSHAKE_FAILED: TLS handshake failed.
    """

    NORMAL = "normal"
    TIMEOUT = "timeout"
    ERROR = "error"
    CLIENT_DISCONNECT = "client_disconnect"
    SERVER_SHUTDOWN = "server_shutdown"
    HANDSHAKE_FAILED = "handshake_failed"


class HandshakeState(Enum):
    """TLS handshake progress states.

    Used to track partial handshake state for debugging connection issues.

    States:
        INITIAL: No handshake messages received.
        CLIENT_HELLO_RECEIVED: ClientHello message received.
        SERVER_HELLO_SENT: ServerHello message sent.
        KEY_EXCHANGE: Key exchange in progress.
        FINISHED: Handshake completed successfully.
        FAILED: Handshake failed.
    """

    INITIAL = "initial"
    CLIENT_HELLO_RECEIVED = "client_hello_received"
    SERVER_HELLO_SENT = "server_hello_sent"
    KEY_EXCHANGE = "key_exchange"
    FINISHED = "finished"
    FAILED = "failed"


class TLSAlert(IntEnum):
    """TLS Alert codes (RFC 5246).

    Common TLS alert codes used for error reporting.
    """

    CLOSE_NOTIFY = 0
    UNEXPECTED_MESSAGE = 10
    BAD_RECORD_MAC = 20
    DECRYPTION_FAILED = 21
    RECORD_OVERFLOW = 22
    DECOMPRESSION_FAILURE = 30
    HANDSHAKE_FAILURE = 40
    NO_CERTIFICATE = 41
    BAD_CERTIFICATE = 42
    UNSUPPORTED_CERTIFICATE = 43
    CERTIFICATE_REVOKED = 44
    CERTIFICATE_EXPIRED = 45
    CERTIFICATE_UNKNOWN = 46
    ILLEGAL_PARAMETER = 47
    UNKNOWN_CA = 48
    ACCESS_DENIED = 49
    DECODE_ERROR = 50
    DECRYPT_ERROR = 51
    EXPORT_RESTRICTION = 60
    PROTOCOL_VERSION = 70
    INSUFFICIENT_SECURITY = 71
    INTERNAL_ERROR = 80
    USER_CANCELED = 90
    NO_RENEGOTIATION = 100
    UNSUPPORTED_EXTENSION = 110
    UNKNOWN_PSK_IDENTITY = 115

    @classmethod
    def get_description(cls, alert: "TLSAlert") -> str:
        """Get human-readable description for an alert code.

        Args:
            alert: The TLS alert code.

        Returns:
            Human-readable description of the alert.
        """
        descriptions = {
            cls.CLOSE_NOTIFY: "Connection closed normally",
            cls.UNEXPECTED_MESSAGE: "Unexpected message received",
            cls.BAD_RECORD_MAC: "Bad record MAC",
            cls.DECRYPTION_FAILED: "Decryption failed",
            cls.RECORD_OVERFLOW: "Record overflow",
            cls.DECOMPRESSION_FAILURE: "Decompression failure",
            cls.HANDSHAKE_FAILURE: "Handshake failure",
            cls.BAD_CERTIFICATE: "Bad certificate",
            cls.ILLEGAL_PARAMETER: "Illegal parameter",
            cls.DECODE_ERROR: "Decode error",
            cls.DECRYPT_ERROR: "Decrypt error (PSK mismatch)",
            cls.PROTOCOL_VERSION: "Protocol version not supported",
            cls.INSUFFICIENT_SECURITY: "Insufficient security",
            cls.INTERNAL_ERROR: "Internal error",
            cls.UNKNOWN_PSK_IDENTITY: "Unknown PSK identity",
        }
        return descriptions.get(alert, f"Unknown alert ({alert})")


# =============================================================================
# Dataclasses (Task 4)
# =============================================================================


@dataclass
class TLSSessionInfo:
    """Information about an established TLS session.

    Attributes:
        cipher_suite: Negotiated cipher suite name.
        psk_identity: PSK identity used for authentication.
        protocol_version: TLS protocol version.
        handshake_duration_ms: Time taken for handshake in milliseconds.
        client_address: Client IP address and port.

    Example:
        >>> info = TLSSessionInfo(
        ...     cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
        ...     psk_identity="card_001",
        ...     handshake_duration_ms=45.2
        ... )
    """

    cipher_suite: str
    psk_identity: str
    protocol_version: str = "TLSv1.2"
    handshake_duration_ms: float = 0.0
    client_address: Optional[str] = None


@dataclass
class APDUExchange:
    """Record of a single APDU command/response exchange.

    Attributes:
        command: APDU command bytes (hex string).
        response: APDU response bytes (hex string).
        status_word: Response status word (e.g., "9000").
        timestamp: Time of the exchange.
        duration_ms: Time taken for the exchange in milliseconds.
        command_name: Human-readable command name (e.g., "SELECT").

    Example:
        >>> exchange = APDUExchange(
        ...     command="00A4040007A0000000041010",
        ...     response="9000",
        ...     status_word="9000",
        ...     duration_ms=12.5
        ... )
    """

    command: str
    response: str
    status_word: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    command_name: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Check if the exchange was successful (SW 9000 or 61xx/62xx/63xx)."""
        if not self.status_word:
            return False
        sw = self.status_word.upper()
        return sw == "9000" or sw.startswith(("61", "62", "63"))


@dataclass
class Session:
    """Active server session.

    Represents a client session from connection to close, tracking
    all APDU exchanges and session metadata.

    Attributes:
        session_id: Unique session identifier (UUID).
        state: Current session state.
        tls_info: TLS session information.
        created_at: Session creation timestamp.
        last_activity: Last activity timestamp.
        apdu_exchanges: List of APDU exchanges in this session.
        command_count: Total number of commands processed.
        client_address: Client IP address and port.
        close_reason: Reason for session closure (if closed).
        metadata: Additional session metadata.

    Example:
        >>> session = Session(session_id="550e8400-e29b-41d4-a716-446655440000")
        >>> session.state = SessionState.ACTIVE
        >>> session.record_exchange(exchange)
    """

    session_id: str
    state: SessionState = SessionState.HANDSHAKING
    tls_info: Optional[TLSSessionInfo] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    apdu_exchanges: List[APDUExchange] = field(default_factory=list)
    command_count: int = 0
    client_address: Optional[str] = None
    close_reason: Optional[CloseReason] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_exchange(self, exchange: APDUExchange) -> None:
        """Record an APDU exchange in this session.

        Args:
            exchange: The APDU exchange to record.
        """
        self.apdu_exchanges.append(exchange)
        self.command_count += 1
        self.last_activity = datetime.utcnow()

    def get_duration_seconds(self) -> float:
        """Get session duration in seconds.

        Returns:
            Duration from creation to now (or close time) in seconds.
        """
        end_time = self.last_activity if self.state == SessionState.CLOSED else datetime.utcnow()
        return (end_time - self.created_at).total_seconds()

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary for logging/reporting.

        Returns:
            Dictionary containing session summary information.
        """
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "client_address": self.client_address,
            "duration_seconds": self.get_duration_seconds(),
            "command_count": self.command_count,
            "cipher_suite": self.tls_info.cipher_suite if self.tls_info else None,
            "psk_identity": self.tls_info.psk_identity if self.tls_info else None,
            "close_reason": self.close_reason.value if self.close_reason else None,
        }


@dataclass
class HandshakeProgress:
    """Track TLS handshake progress for debugging.

    Attributes:
        state: Current handshake state.
        client_address: Client IP address.
        started_at: Handshake start time.
        messages_received: List of received message types.
        error: Error message if handshake failed.
    """

    state: HandshakeState = HandshakeState.INITIAL
    client_address: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    messages_received: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def get_duration_ms(self) -> float:
        """Get handshake duration in milliseconds."""
        return (datetime.utcnow() - self.started_at).total_seconds() * 1000
