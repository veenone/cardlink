"""Simulator models and data structures.

This module defines dataclasses and enums for the Mobile Simulator,
including connection state management, session results, and APDU exchange tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class ConnectionState(Enum):
    """Simulator connection states.

    States:
        IDLE: Not connected, ready to connect.
        CONNECTING: TLS handshake in progress.
        CONNECTED: TLS connection established, ready for HTTP.
        EXCHANGING: APDU exchange in progress.
        CLOSING: Graceful disconnect in progress.
        ERROR: Connection failed with error.
        TIMEOUT: Connection or operation timed out.
    """

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    EXCHANGING = "exchanging"
    CLOSING = "closing"
    ERROR = "error"
    TIMEOUT = "timeout"


class BehaviorMode(Enum):
    """Simulation behavior modes.

    Modes:
        NORMAL: Process all commands correctly.
        ERROR: Inject errors at configured rate.
        TIMEOUT: Simulate slow responses or timeouts.
    """

    NORMAL = "normal"
    ERROR = "error"
    TIMEOUT = "timeout"


class ConnectionMode(Enum):
    """Connection behavior patterns.

    Modes:
        SINGLE: Single connection for entire session.
        PER_COMMAND: New connection per command.
        BATCH: Multiple commands per connection.
        RECONNECT: Disconnect and reconnect mid-session.
        PERSISTENT: Keep connection open and poll for new commands.
    """

    SINGLE = "single"
    PER_COMMAND = "per_command"
    BATCH = "batch"
    RECONNECT = "reconnect"
    PERSISTENT = "persistent"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class TLSConnectionInfo:
    """Information about an established TLS connection.

    Attributes:
        cipher_suite: Negotiated cipher suite name.
        psk_identity: PSK identity used for authentication.
        protocol_version: TLS protocol version.
        handshake_duration_ms: Time taken for handshake in milliseconds.
        server_address: Server IP address and port.
        iccid: ICCID of the virtual UICC (if available).
        imsi: IMSI of the virtual UICC (if available).

    Example:
        >>> info = TLSConnectionInfo(
        ...     cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
        ...     psk_identity="test_card_001",
        ...     iccid="8901234567890123456",
        ...     handshake_duration_ms=45.2
        ... )
    """

    cipher_suite: str
    psk_identity: str
    protocol_version: str = "TLSv1.2"
    handshake_duration_ms: float = 0.0
    server_address: Optional[str] = None
    iccid: Optional[str] = None
    imsi: Optional[str] = None

    @property
    def display_identity(self) -> str:
        """Get display identity (ICCID preferred, then psk_identity)."""
        return self.iccid or self.psk_identity


@dataclass
class APDUExchange:
    """Record of a single APDU command/response exchange.

    Attributes:
        command: C-APDU command bytes (hex string).
        response: R-APDU response bytes (hex string).
        sw: Response status word (e.g., "9000").
        timestamp: Time of the exchange.
        duration_ms: Time taken for the exchange in milliseconds.
        ins: INS byte value for the command.
        description: Human-readable command description.

    Example:
        >>> exchange = APDUExchange(
        ...     command="00A4040007A0000000041010",
        ...     response="6F10840EA0000000041010A5029F6501FF",
        ...     sw="9000",
        ...     ins=0xA4,
        ...     description="SELECT ISD-R"
        ... )
    """

    command: str
    response: str
    sw: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    ins: int = 0
    description: str = ""

    @property
    def is_success(self) -> bool:
        """Check if the exchange was successful (SW 9000 or 61xx/62xx/63xx)."""
        if not self.sw:
            return False
        sw = self.sw.upper()
        return sw == "9000" or sw.startswith(("61", "62", "63"))


@dataclass
class SessionResult:
    """Result of a completed simulation session.

    Attributes:
        success: Whether the session completed successfully.
        session_id: Unique session identifier.
        duration_seconds: Total session duration in seconds.
        apdu_count: Number of APDU exchanges.
        final_sw: Final status word from last exchange.
        exchanges: List of all APDU exchanges.
        error: Error message if session failed.
        tls_info: TLS connection information.

    Example:
        >>> result = SessionResult(
        ...     success=True,
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     duration_seconds=1.5,
        ...     apdu_count=5,
        ...     final_sw="9000"
        ... )
    """

    success: bool
    session_id: str
    duration_seconds: float = 0.0
    apdu_count: int = 0
    final_sw: str = ""
    exchanges: List[APDUExchange] = field(default_factory=list)
    error: Optional[str] = None
    tls_info: Optional[TLSConnectionInfo] = None

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary for logging/reporting.

        Returns:
            Dictionary containing session summary information.
        """
        return {
            "success": self.success,
            "session_id": self.session_id,
            "duration_seconds": self.duration_seconds,
            "apdu_count": self.apdu_count,
            "final_sw": self.final_sw,
            "error": self.error,
            "cipher_suite": self.tls_info.cipher_suite if self.tls_info else None,
            "psk_identity": self.tls_info.psk_identity if self.tls_info else None,
            "iccid": self.tls_info.iccid if self.tls_info else None,
            "imsi": self.tls_info.imsi if self.tls_info else None,
        }


@dataclass
class SimulatorStats:
    """Simulator session statistics.

    Attributes:
        connections_attempted: Total connection attempts.
        connections_succeeded: Successful connections.
        connections_failed: Failed connections.
        connection_errors: Error counts by type.
        sessions_completed: Successfully completed sessions.
        sessions_failed: Failed sessions.
        total_apdus_sent: Total R-APDUs sent.
        total_apdus_received: Total C-APDUs received.
        avg_connection_time_ms: Average connection time.
        avg_session_duration_ms: Average session duration.
        avg_apdu_response_time_ms: Average APDU response time.
        error_responses: Error SW counts by code.
        timeout_count: Number of timeouts.

    Example:
        >>> stats = SimulatorStats()
        >>> stats.connections_attempted = 10
        >>> stats.connections_succeeded = 9
    """

    # Connection stats
    connections_attempted: int = 0
    connections_succeeded: int = 0
    connections_failed: int = 0
    connection_errors: Dict[str, int] = field(default_factory=dict)

    # Session stats
    sessions_completed: int = 0
    sessions_failed: int = 0
    total_apdus_sent: int = 0
    total_apdus_received: int = 0

    # Timing stats
    avg_connection_time_ms: float = 0.0
    avg_session_duration_ms: float = 0.0
    avg_apdu_response_time_ms: float = 0.0

    # Error stats
    error_responses: Dict[str, int] = field(default_factory=dict)
    timeout_count: int = 0

    # Internal tracking for averages
    _connection_times: List[float] = field(default_factory=list, repr=False)
    _session_durations: List[float] = field(default_factory=list, repr=False)
    _apdu_times: List[float] = field(default_factory=list, repr=False)

    def record_connection_time(self, time_ms: float) -> None:
        """Record a connection time for averaging.

        Args:
            time_ms: Connection time in milliseconds.
        """
        self._connection_times.append(time_ms)
        self.avg_connection_time_ms = sum(self._connection_times) / len(self._connection_times)

    def record_session_duration(self, duration_ms: float) -> None:
        """Record a session duration for averaging.

        Args:
            duration_ms: Session duration in milliseconds.
        """
        self._session_durations.append(duration_ms)
        self.avg_session_duration_ms = sum(self._session_durations) / len(self._session_durations)

    def record_apdu_time(self, time_ms: float) -> None:
        """Record an APDU response time for averaging.

        Args:
            time_ms: APDU response time in milliseconds.
        """
        self._apdu_times.append(time_ms)
        self.avg_apdu_response_time_ms = sum(self._apdu_times) / len(self._apdu_times)

    def record_error(self, error_type: str) -> None:
        """Record a connection error.

        Args:
            error_type: Type of error that occurred.
        """
        self.connection_errors[error_type] = self.connection_errors.get(error_type, 0) + 1

    def record_error_sw(self, sw: str) -> None:
        """Record an error status word.

        Args:
            sw: Status word that indicates an error.
        """
        self.error_responses[sw] = self.error_responses.get(sw, 0) + 1


@dataclass
class VirtualApplet:
    """Virtual applet configuration.

    Attributes:
        aid: Application Identifier (hex string).
        name: Human-readable applet name.
        state: Applet lifecycle state.
        privileges: Applet privileges (hex string).

    Example:
        >>> applet = VirtualApplet(
        ...     aid="A0000001510001",
        ...     name="TestApplet",
        ...     state="SELECTABLE"
        ... )
    """

    aid: str
    name: str = ""
    state: str = "SELECTABLE"
    privileges: str = "00"
