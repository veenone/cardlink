"""Error Handler for PSK-TLS Admin Server.

This module provides centralized error handling, including PSK mismatch tracking,
connection interruption handling, and error rate monitoring.

Example:
    >>> from gp_ota_tester.server.error_handler import ErrorHandler
    >>> handler = ErrorHandler(event_emitter)
    >>> handler.handle_psk_mismatch("card_001", "192.168.1.1:12345")
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import DefaultDict, Dict, List, Optional

from gp_ota_tester.server.event_emitter import (
    EVENT_CONNECTION_INTERRUPTED,
    EVENT_HIGH_ERROR_RATE,
    EVENT_PSK_MISMATCH,
    EventEmitter,
)
from gp_ota_tester.server.models import HandshakeProgress, TLSAlert

logger = logging.getLogger(__name__)


@dataclass
class MismatchRecord:
    """Record of a PSK mismatch attempt."""

    identity: str
    client_address: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ErrorRateWindow:
    """Sliding window for error rate tracking."""

    window_seconds: float
    threshold: int
    timestamps: List[datetime] = field(default_factory=list)

    def record_error(self) -> None:
        """Record an error occurrence."""
        self.timestamps.append(datetime.utcnow())
        self._cleanup_old()

    def get_count(self) -> int:
        """Get error count in current window."""
        self._cleanup_old()
        return len(self.timestamps)

    def is_threshold_exceeded(self) -> bool:
        """Check if error rate threshold is exceeded."""
        return self.get_count() >= self.threshold

    def _cleanup_old(self) -> None:
        """Remove timestamps outside the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        self.timestamps = [t for t in self.timestamps if t > cutoff]


class MismatchTracker:
    """Tracks PSK mismatches per client IP for detecting attacks.

    Monitors PSK mismatch attempts and warns when multiple mismatches
    occur from the same source within a time window.

    Attributes:
        window_seconds: Time window for tracking mismatches.
        threshold: Number of mismatches to trigger warning.
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        threshold: int = 3,
    ) -> None:
        """Initialize MismatchTracker.

        Args:
            window_seconds: Time window for tracking.
            threshold: Mismatch count to trigger warning.
        """
        self._window_seconds = window_seconds
        self._threshold = threshold
        self._records: DefaultDict[str, List[MismatchRecord]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_mismatch(
        self,
        identity: str,
        client_address: str,
    ) -> bool:
        """Record a PSK mismatch and check for warning threshold.

        Args:
            identity: PSK identity that was attempted.
            client_address: Client IP address.

        Returns:
            True if warning threshold exceeded, False otherwise.
        """
        # Extract IP from address (remove port if present)
        client_ip = client_address.split(":")[0]

        record = MismatchRecord(
            identity=identity,
            client_address=client_address,
        )

        with self._lock:
            self._records[client_ip].append(record)
            self._cleanup_old(client_ip)

            count = len(self._records[client_ip])
            return count >= self._threshold

    def get_mismatch_count(self, client_ip: str) -> int:
        """Get mismatch count for a client IP.

        Args:
            client_ip: Client IP address.

        Returns:
            Number of mismatches in current window.
        """
        with self._lock:
            self._cleanup_old(client_ip)
            return len(self._records.get(client_ip, []))

    def _cleanup_old(self, client_ip: str) -> None:
        """Remove old records outside the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self._window_seconds)
        if client_ip in self._records:
            self._records[client_ip] = [
                r for r in self._records[client_ip]
                if r.timestamp > cutoff
            ]

    def clear(self) -> None:
        """Clear all tracked mismatches."""
        with self._lock:
            self._records.clear()


class ErrorHandler:
    """Centralized error handling for the PSK-TLS Admin Server.

    Handles various error conditions including:
    - PSK authentication mismatches
    - Connection interruptions
    - Handshake failures
    - Error rate monitoring

    Attributes:
        mismatch_window: Time window for PSK mismatch tracking.
        mismatch_threshold: Mismatch count to trigger warning.
        error_rate_window: Time window for error rate calculation.
        error_rate_threshold: Error count to trigger high rate alert.

    Example:
        >>> emitter = EventEmitter()
        >>> handler = ErrorHandler(emitter)
        >>>
        >>> # Handle PSK mismatch
        >>> alert = handler.handle_psk_mismatch("card_001", "192.168.1.1:12345")
        >>>
        >>> # Handle connection interruption
        >>> handler.handle_connection_interrupted(
        ...     session_id="abc123",
        ...     last_command="00A4040007A0000000041010",
        ... )
    """

    def __init__(
        self,
        event_emitter: Optional[EventEmitter] = None,
        mismatch_window: float = 60.0,
        mismatch_threshold: int = 3,
        error_rate_window: float = 300.0,
        error_rate_threshold: int = 10,
    ) -> None:
        """Initialize Error Handler.

        Args:
            event_emitter: Event emitter for error events.
            mismatch_window: Time window for mismatch tracking (seconds).
            mismatch_threshold: Mismatches to trigger warning.
            error_rate_window: Time window for error rate (seconds).
            error_rate_threshold: Errors to trigger high rate alert.
        """
        self._event_emitter = event_emitter
        self._mismatch_tracker = MismatchTracker(
            window_seconds=mismatch_window,
            threshold=mismatch_threshold,
        )

        # Error rate tracking by error type
        self._error_rates: Dict[str, ErrorRateWindow] = {
            "psk_mismatch": ErrorRateWindow(error_rate_window, error_rate_threshold),
            "connection_interrupted": ErrorRateWindow(error_rate_window, error_rate_threshold),
            "handshake_failed": ErrorRateWindow(error_rate_window, error_rate_threshold),
        }
        self._error_rates_lock = threading.Lock()

    def handle_psk_mismatch(
        self,
        identity: str,
        client_address: str,
    ) -> TLSAlert:
        """Handle PSK authentication mismatch.

        Logs the mismatch (without logging the key!), tracks for repeated
        attempts, and emits an event.

        Args:
            identity: PSK identity that was attempted.
            client_address: Client IP:port string.

        Returns:
            TLS Alert code to send to client (DECRYPT_ERROR).
        """
        # Log the mismatch - NEVER log the key!
        logger.warning(
            "PSK mismatch: identity='%s', client=%s",
            identity,
            client_address,
        )

        # Track mismatch
        threshold_exceeded = self._mismatch_tracker.record_mismatch(
            identity, client_address
        )

        # Check for repeated attempts (possible attack)
        if threshold_exceeded:
            client_ip = client_address.split(":")[0]
            count = self._mismatch_tracker.get_mismatch_count(client_ip)
            logger.warning(
                "╔════════════════════════════════════════════════════════════╗"
            )
            logger.warning(
                "║  MULTIPLE PSK MISMATCHES FROM SAME SOURCE                  ║"
            )
            logger.warning(
                "║  Client: %s", client_ip.ljust(49) + " ║"
            )
            logger.warning(
                "║  Count: %d in last 60 seconds", count
            )
            logger.warning(
                "║  Possible brute-force attempt or misconfiguration          ║"
            )
            logger.warning(
                "╚════════════════════════════════════════════════════════════╝"
            )

        # Record error for rate tracking
        self._record_error("psk_mismatch")

        # Emit event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_PSK_MISMATCH,
                {
                    "identity": identity,
                    "client_address": client_address,
                    "repeated_attempts": threshold_exceeded,
                },
            )

        # Check error rate
        self._check_error_rate("psk_mismatch")

        # Return TLS Alert 51 (decrypt_error) per SCP81/TLS spec
        return TLSAlert.DECRYPT_ERROR

    def handle_connection_interrupted(
        self,
        session_id: str,
        last_command: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Handle unexpected connection interruption.

        Args:
            session_id: Session that was interrupted.
            last_command: Last APDU command (if any).
            error: Error message/description.
        """
        logger.warning(
            "Connection interrupted: session=%s, last_command=%s, error=%s",
            session_id,
            last_command[:16] + "..." if last_command and len(last_command) > 16 else last_command,
            error,
        )

        # Record error
        self._record_error("connection_interrupted")

        # Emit event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_CONNECTION_INTERRUPTED,
                {
                    "session_id": session_id,
                    "last_command": last_command,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        # Check error rate
        self._check_error_rate("connection_interrupted")

    def handle_handshake_interrupted(
        self,
        client_address: str,
        partial_state: Optional[HandshakeProgress] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Handle TLS handshake interruption.

        Args:
            client_address: Client IP:port string.
            partial_state: Handshake progress at time of interruption.
            reason: Reason for interruption.
        """
        state_info = ""
        if partial_state:
            state_info = f", state={partial_state.state.value}, messages={partial_state.messages_received}"

        logger.warning(
            "Handshake interrupted: client=%s%s, reason=%s",
            client_address,
            state_info,
            reason,
        )

        # Check if this looks like a network issue
        if partial_state and len(partial_state.messages_received) <= 1:
            logger.info(
                "Handshake interrupted after only ClientHello - "
                "potential network issue or client abort for %s",
                client_address,
            )

        # Record error
        self._record_error("handshake_failed")

        # Check error rate
        self._check_error_rate("handshake_failed")

    def _record_error(self, error_type: str) -> None:
        """Record an error for rate tracking.

        Args:
            error_type: Type of error.
        """
        with self._error_rates_lock:
            if error_type in self._error_rates:
                self._error_rates[error_type].record_error()

    def _check_error_rate(self, error_type: str) -> bool:
        """Check if error rate threshold is exceeded and emit alert.

        Args:
            error_type: Type of error to check.

        Returns:
            True if threshold exceeded, False otherwise.
        """
        with self._error_rates_lock:
            if error_type not in self._error_rates:
                return False

            window = self._error_rates[error_type]
            if window.is_threshold_exceeded():
                count = window.get_count()

                logger.error(
                    "High error rate detected: type=%s, count=%d, window=%ds, threshold=%d",
                    error_type,
                    count,
                    window.window_seconds,
                    window.threshold,
                )

                # Emit high error rate event
                if self._event_emitter:
                    self._event_emitter.emit(
                        EVENT_HIGH_ERROR_RATE,
                        {
                            "error_type": error_type,
                            "count": count,
                            "window_seconds": window.window_seconds,
                            "threshold": window.threshold,
                            "rate_per_minute": count / (window.window_seconds / 60),
                        },
                    )

                return True

        return False

    def get_error_count(self, error_type: str) -> int:
        """Get current error count for a type.

        Args:
            error_type: Type of error.

        Returns:
            Error count in current window.
        """
        with self._error_rates_lock:
            if error_type in self._error_rates:
                return self._error_rates[error_type].get_count()
        return 0

    def get_error_stats(self) -> Dict[str, Dict]:
        """Get error statistics for all tracked types.

        Returns:
            Dictionary of error type to stats.
        """
        with self._error_rates_lock:
            return {
                error_type: {
                    "count": window.get_count(),
                    "threshold": window.threshold,
                    "window_seconds": window.window_seconds,
                    "threshold_exceeded": window.is_threshold_exceeded(),
                }
                for error_type, window in self._error_rates.items()
            }

    def clear_tracking(self) -> None:
        """Clear all error tracking data."""
        self._mismatch_tracker.clear()
        with self._error_rates_lock:
            for window in self._error_rates.values():
                window.timestamps.clear()
        logger.debug("Error tracking data cleared")
