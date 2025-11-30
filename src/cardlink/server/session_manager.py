"""Session Manager for PSK-TLS Admin Server.

This module manages client sessions, tracking state transitions, APDU exchanges,
and session timeouts.

Example:
    >>> from cardlink.server.session_manager import SessionManager
    >>> manager = SessionManager(event_emitter, session_timeout=300)
    >>> session = manager.create_session("192.168.1.1:12345")
    >>> manager.set_session_state(session.session_id, SessionState.ACTIVE)
"""

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from cardlink.server.event_emitter import (
    EVENT_SESSION_ENDED,
    EVENT_SESSION_STARTED,
    EventEmitter,
)
from cardlink.server.models import (
    APDUExchange,
    CloseReason,
    Session,
    SessionState,
    TLSSessionInfo,
)

logger = logging.getLogger(__name__)


# Valid state transitions
VALID_TRANSITIONS: Dict[SessionState, List[SessionState]] = {
    SessionState.HANDSHAKING: [SessionState.CONNECTED, SessionState.CLOSED],
    SessionState.CONNECTED: [SessionState.ACTIVE, SessionState.CLOSED],
    SessionState.ACTIVE: [SessionState.CLOSED],
    SessionState.CLOSED: [],  # Terminal state
}


class SessionManagerError(Exception):
    """Base exception for session manager errors."""

    pass


class InvalidStateTransition(SessionManagerError):
    """Invalid session state transition attempted."""

    pass


class SessionNotFound(SessionManagerError):
    """Session not found."""

    pass


class SessionManager:
    """Manages client sessions for the PSK-TLS Admin Server.

    Handles session lifecycle including creation, state transitions,
    APDU tracking, and timeout expiration.

    Thread Safety:
        All methods are thread-safe and can be called from any thread.

    Attributes:
        session_timeout: Session timeout in seconds.
        cleanup_interval: Interval for expired session cleanup in seconds.

    Example:
        >>> emitter = EventEmitter()
        >>> manager = SessionManager(emitter, session_timeout=300)
        >>> manager.start()
        >>>
        >>> # Create session
        >>> session = manager.create_session("192.168.1.1:12345")
        >>>
        >>> # Update state
        >>> manager.set_session_state(session.session_id, SessionState.CONNECTED)
        >>> manager.set_tls_info(session.session_id, tls_info)
        >>>
        >>> # Record APDU exchange
        >>> manager.record_exchange(session.session_id, apdu_exchange)
        >>>
        >>> # Close session
        >>> manager.close_session(session.session_id, CloseReason.NORMAL)
        >>>
        >>> manager.stop()
    """

    def __init__(
        self,
        event_emitter: Optional[EventEmitter] = None,
        session_timeout: float = 300.0,
        cleanup_interval: float = 30.0,
    ) -> None:
        """Initialize Session Manager.

        Args:
            event_emitter: Event emitter for session events.
            session_timeout: Session timeout in seconds (default 5 minutes).
            cleanup_interval: Interval for cleanup thread in seconds.
        """
        self._event_emitter = event_emitter
        self._session_timeout = session_timeout
        self._cleanup_interval = cleanup_interval

        self._sessions: Dict[str, Session] = {}
        self._sessions_lock = threading.RLock()

        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        self._state_change_callbacks: List[Callable[[Session, SessionState, SessionState], None]] = []

    def start(self) -> None:
        """Start the session manager and cleanup thread."""
        if self._running:
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="SessionManager-Cleanup",
            daemon=True,
        )
        self._cleanup_thread.start()
        logger.info(
            "Session manager started (timeout=%ss, cleanup_interval=%ss)",
            self._session_timeout,
            self._cleanup_interval,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the session manager and cleanup thread.

        Args:
            timeout: Maximum time to wait for cleanup thread.
        """
        if not self._running:
            return

        self._running = False

        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=timeout)
            self._cleanup_thread = None

        # Close all remaining sessions
        with self._sessions_lock:
            for session_id in list(self._sessions.keys()):
                self._close_session_internal(session_id, CloseReason.SERVER_SHUTDOWN)

        logger.info("Session manager stopped")

    def create_session(
        self,
        client_address: str,
        metadata: Optional[Dict] = None,
    ) -> Session:
        """Create a new session.

        Args:
            client_address: Client IP:port string.
            metadata: Optional metadata to attach to session.

        Returns:
            New Session object in HANDSHAKING state.
        """
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            state=SessionState.HANDSHAKING,
            client_address=client_address,
            metadata=metadata or {},
        )

        with self._sessions_lock:
            self._sessions[session_id] = session

        logger.info(
            "Session created: id=%s, client=%s",
            session_id,
            client_address,
        )

        # Emit event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_SESSION_STARTED,
                {
                    "session_id": session_id,
                    "client_address": client_address,
                    "state": session.state.value,
                },
            )

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session object or None if not found.
        """
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def get_all_sessions(self) -> List[Session]:
        """Get all active sessions.

        Returns:
            List of all sessions (including closed ones still in memory).
        """
        with self._sessions_lock:
            return list(self._sessions.values())

    def get_active_sessions(self) -> List[Session]:
        """Get all non-closed sessions.

        Returns:
            List of sessions that are not in CLOSED state.
        """
        with self._sessions_lock:
            return [
                s for s in self._sessions.values()
                if s.state != SessionState.CLOSED
            ]

    def set_session_state(
        self,
        session_id: str,
        new_state: SessionState,
    ) -> None:
        """Set session state with transition validation.

        Args:
            session_id: Session identifier.
            new_state: New state to transition to.

        Raises:
            SessionNotFound: If session does not exist.
            InvalidStateTransition: If transition is not allowed.
        """
        with self._sessions_lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionNotFound(f"Session not found: {session_id}")

            old_state = session.state

            # Validate transition
            if new_state not in VALID_TRANSITIONS.get(old_state, []):
                raise InvalidStateTransition(
                    f"Invalid state transition: {old_state.value} -> {new_state.value}"
                )

            session.state = new_state
            session.last_activity = datetime.utcnow()

            logger.debug(
                "Session state changed: id=%s, %s -> %s",
                session_id,
                old_state.value,
                new_state.value,
            )

        # Notify callbacks (outside lock)
        for callback in self._state_change_callbacks:
            try:
                callback(session, old_state, new_state)
            except Exception as e:
                logger.exception("Error in state change callback: %s", e)

    def set_tls_info(self, session_id: str, tls_info: TLSSessionInfo) -> None:
        """Set TLS session information.

        Args:
            session_id: Session identifier.
            tls_info: TLS session information.

        Raises:
            SessionNotFound: If session does not exist.
        """
        with self._sessions_lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionNotFound(f"Session not found: {session_id}")

            session.tls_info = tls_info
            session.last_activity = datetime.utcnow()

    def record_exchange(self, session_id: str, exchange: APDUExchange) -> None:
        """Record an APDU exchange in a session.

        Args:
            session_id: Session identifier.
            exchange: APDU exchange to record.

        Raises:
            SessionNotFound: If session does not exist.
        """
        with self._sessions_lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionNotFound(f"Session not found: {session_id}")

            session.record_exchange(exchange)

            logger.debug(
                "APDU exchange recorded: session=%s, cmd=%s, sw=%s, count=%d",
                session_id,
                exchange.command_name or exchange.command[:8] + "...",
                exchange.status_word,
                session.command_count,
            )

    def close_session(
        self,
        session_id: str,
        reason: CloseReason = CloseReason.NORMAL,
    ) -> Optional[Session]:
        """Close a session.

        Args:
            session_id: Session identifier.
            reason: Reason for closing the session.

        Returns:
            Closed session or None if not found.
        """
        with self._sessions_lock:
            return self._close_session_internal(session_id, reason)

    def _close_session_internal(
        self,
        session_id: str,
        reason: CloseReason,
    ) -> Optional[Session]:
        """Internal method to close a session (must hold lock).

        Args:
            session_id: Session identifier.
            reason: Reason for closing.

        Returns:
            Closed session or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.state == SessionState.CLOSED:
            return session

        old_state = session.state
        session.state = SessionState.CLOSED
        session.close_reason = reason
        session.last_activity = datetime.utcnow()

        logger.info(
            "Session closed: id=%s, reason=%s, duration=%.1fs, commands=%d",
            session_id,
            reason.value,
            session.get_duration_seconds(),
            session.command_count,
        )

        # Emit event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_SESSION_ENDED,
                {
                    "session_id": session_id,
                    "reason": reason.value,
                    "previous_state": old_state.value,
                    "duration_seconds": session.get_duration_seconds(),
                    "command_count": session.command_count,
                    **session.get_summary(),
                },
            )

        return session

    def cleanup_expired(self) -> int:
        """Clean up expired sessions.

        Sessions are expired if they have been inactive longer than
        the session timeout.

        Returns:
            Number of sessions closed due to timeout.
        """
        now = datetime.utcnow()
        expired_count = 0

        with self._sessions_lock:
            for session_id, session in list(self._sessions.items()):
                if session.state == SessionState.CLOSED:
                    continue

                inactive_seconds = (now - session.last_activity).total_seconds()
                if inactive_seconds > self._session_timeout:
                    self._close_session_internal(session_id, CloseReason.TIMEOUT)
                    expired_count += 1
                    logger.warning(
                        "Session expired: id=%s, inactive=%.1fs",
                        session_id,
                        inactive_seconds,
                    )

        if expired_count > 0:
            logger.info("Cleaned up %d expired sessions", expired_count)

        return expired_count

    def purge_closed_sessions(self, max_age_seconds: float = 3600.0) -> int:
        """Remove closed sessions from memory.

        Args:
            max_age_seconds: Maximum age of closed sessions to keep.

        Returns:
            Number of sessions purged.
        """
        now = datetime.utcnow()
        purged_count = 0

        with self._sessions_lock:
            for session_id, session in list(self._sessions.items()):
                if session.state != SessionState.CLOSED:
                    continue

                age_seconds = (now - session.last_activity).total_seconds()
                if age_seconds > max_age_seconds:
                    del self._sessions[session_id]
                    purged_count += 1

        if purged_count > 0:
            logger.debug("Purged %d closed sessions from memory", purged_count)

        return purged_count

    def _cleanup_loop(self) -> None:
        """Background thread for session cleanup."""
        while self._running:
            try:
                self.cleanup_expired()
                self.purge_closed_sessions()
            except Exception as e:
                logger.exception("Error in cleanup loop: %s", e)

            # Sleep in small intervals to allow quick shutdown
            for _ in range(int(self._cleanup_interval * 10)):
                if not self._running:
                    break
                time.sleep(0.1)

    def on_state_change(
        self,
        callback: Callable[[Session, SessionState, SessionState], None],
    ) -> None:
        """Register a callback for state changes.

        Args:
            callback: Function called with (session, old_state, new_state).
        """
        self._state_change_callbacks.append(callback)

    def get_session_count(self) -> int:
        """Get total number of sessions (including closed)."""
        with self._sessions_lock:
            return len(self._sessions)

    def get_active_session_count(self) -> int:
        """Get number of non-closed sessions."""
        with self._sessions_lock:
            return sum(
                1 for s in self._sessions.values()
                if s.state != SessionState.CLOSED
            )

    @property
    def session_timeout(self) -> float:
        """Get session timeout in seconds."""
        return self._session_timeout

    @session_timeout.setter
    def session_timeout(self, value: float) -> None:
        """Set session timeout in seconds."""
        if value <= 0:
            raise ValueError("Session timeout must be positive")
        self._session_timeout = value
