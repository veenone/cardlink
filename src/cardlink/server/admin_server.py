"""PSK-TLS Admin Server for SCP81 OTA Testing.

This module provides the main AdminServer class that orchestrates all components
and manages the server lifecycle for GlobalPlatform SCP81 OTA administration.

Example:
    >>> from cardlink.server import AdminServer, ServerConfig, FileKeyStore
    >>> config = ServerConfig(port=8443)
    >>> key_store = FileKeyStore("keys.yaml")
    >>> server = AdminServer(config, key_store)
    >>> server.start()
    >>> # ... server runs ...
    >>> server.stop()

Security Note:
    - Server binds to configured interface only (default localhost)
    - PSK keys are never logged; only identities are logged
    - TLS 1.2 with PSK cipher suites required per SCP81 specification
"""

import logging
import socket
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from cardlink.server.config import CipherConfig, ServerConfig
from cardlink.server.error_handler import ErrorHandler
from cardlink.server.event_emitter import (
    EVENT_HANDSHAKE_COMPLETED,
    EVENT_HANDSHAKE_FAILED,
    EVENT_SERVER_STARTED,
    EVENT_SERVER_STOPPED,
    EventEmitter,
)
from cardlink.server.gp_command_processor import GPCommandProcessor
from cardlink.server.http_handler import HTTPHandler
from cardlink.server.key_store import KeyStore
from cardlink.server.models import CloseReason, Session, SessionState
from cardlink.server.session_manager import SessionManager
from cardlink.server.tls_handler import (
    HandshakeError,
    TLSHandler,
    HAS_PSK_SUPPORT,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class AdminServerError(Exception):
    """Base exception for admin server errors."""

    pass


class ServerStartError(AdminServerError):
    """Failed to start the server."""

    pass


class ServerNotRunningError(AdminServerError):
    """Operation requires server to be running."""

    pass


# =============================================================================
# Admin Server
# =============================================================================


class AdminServer:
    """PSK-TLS Admin Server for GP Amendment B RAM over HTTP.

    Orchestrates all server components: TLS handling, session management,
    HTTP parsing, and GP command processing.

    Thread Safety:
        The server is thread-safe. Connection handling is performed in a
        thread pool, and all shared state is protected by locks.

    Attributes:
        config: Server configuration.
        is_running: Whether the server is currently running.

    Example:
        >>> config = ServerConfig(host="0.0.0.0", port=8443)
        >>> key_store = FileKeyStore("keys.yaml")
        >>> emitter = EventEmitter()
        >>>
        >>> server = AdminServer(config, key_store, emitter)
        >>> server.start()
        >>>
        >>> # Server runs in background
        >>> sessions = server.get_active_sessions()
        >>> print(f"Active sessions: {len(sessions)}")
        >>>
        >>> server.stop()
    """

    def __init__(
        self,
        config: ServerConfig,
        key_store: KeyStore,
        event_emitter: Optional[EventEmitter] = None,
        metrics_collector: Optional[Any] = None,
    ) -> None:
        """Initialize Admin Server.

        Args:
            config: Server configuration.
            key_store: Key store for PSK lookup.
            event_emitter: Event emitter for server events.
            metrics_collector: Optional metrics collector for monitoring.

        Raises:
            RuntimeError: If PSK-TLS support is not available.
        """
        if not HAS_PSK_SUPPORT:
            raise RuntimeError(
                "PSK-TLS support requires sslpsk3. Install with: pip install sslpsk3"
            )

        self._config = config
        self._key_store = key_store
        self._event_emitter = event_emitter
        self._metrics_collector = metrics_collector

        # Create component instances
        self._tls_handler = TLSHandler(
            key_store=key_store,
            cipher_config=config.cipher_config,
            handshake_timeout=config.handshake_timeout,
        )
        self._session_manager = SessionManager(
            event_emitter=event_emitter,
            session_timeout=config.session_timeout,
        )
        self._error_handler = ErrorHandler(
            event_emitter=event_emitter,
        )
        self._command_processor = GPCommandProcessor(
            event_emitter=event_emitter,
        )
        self._http_handler = HTTPHandler(
            command_processor=self._command_processor,
            read_timeout=config.read_timeout,
        )

        # Server state
        self._server_socket: Optional[socket.socket] = None
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._running = False
        self._shutdown_event = threading.Event()
        self._accept_thread: Optional[threading.Thread] = None
        self._active_connections: Dict[str, Future] = {}
        self._connections_lock = threading.Lock()

        logger.debug(
            "AdminServer initialized: host=%s, port=%d, max_connections=%d",
            config.host,
            config.port,
            config.max_connections,
        )

    @property
    def config(self) -> ServerConfig:
        """Get server configuration."""
        return self._config

    @property
    def is_running(self) -> bool:
        """Check if server is currently running."""
        return self._running

    def start(self) -> None:
        """Start the server and begin accepting connections.

        Creates the server socket, binds to the configured address,
        and starts the accept loop in a separate thread.

        Raises:
            ServerStartError: If server fails to start.
            AdminServerError: If server is already running.
        """
        if self._running:
            raise AdminServerError("Server is already running")

        try:
            # Start event emitter if present
            if self._event_emitter:
                self._event_emitter.start()

            # Start session manager
            self._session_manager.start()

            # Create server socket
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to configured address
            bind_address = (self._config.host, self._config.port)
            self._server_socket.bind(bind_address)

            # Start listening
            self._server_socket.listen(self._config.backlog)

            # Set timeout for accept() to allow checking shutdown flag
            self._server_socket.settimeout(1.0)

            # Create thread pool for connection handling
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self._config.max_connections,
                thread_name_prefix="AdminServer-Worker",
            )

            # Mark server as running
            self._running = True
            self._shutdown_event.clear()

            # Start accept loop in separate thread
            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                name="AdminServer-Accept",
                daemon=True,
            )
            self._accept_thread.start()

            # Emit server started event
            if self._event_emitter:
                self._event_emitter.emit(
                    EVENT_SERVER_STARTED,
                    {
                        "host": self._config.host,
                        "port": self._config.port,
                        "max_connections": self._config.max_connections,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            logger.info(
                "╔════════════════════════════════════════════════════════════╗"
            )
            logger.info(
                "║  PSK-TLS Admin Server started                              ║"
            )
            logger.info(
                "║  Listening on: %s:%d",
                self._config.host.ljust(20),
                self._config.port,
            )
            logger.info(
                "║  Max connections: %d",
                self._config.max_connections,
            )
            logger.info(
                "╚════════════════════════════════════════════════════════════╝"
            )

        except OSError as e:
            self._cleanup()
            raise ServerStartError(f"Failed to bind to {bind_address}: {e}") from e

        except Exception as e:
            self._cleanup()
            raise ServerStartError(f"Failed to start server: {e}") from e

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop the server.

        Signals shutdown, closes all active sessions, and waits for
        cleanup to complete within the specified timeout.

        Args:
            timeout: Maximum time to wait for cleanup in seconds.
        """
        if not self._running:
            logger.warning("Server is not running")
            return

        logger.info("Stopping server...")
        self._running = False
        self._shutdown_event.set()

        # Wait for accept thread to finish
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)

        # Close all active sessions
        active_sessions = self._session_manager.get_active_sessions()
        for session in active_sessions:
            try:
                self._session_manager.close_session(
                    session.session_id,
                    CloseReason.SERVER_SHUTDOWN,
                )
            except Exception as e:
                logger.warning(
                    "Error closing session %s: %s",
                    session.session_id,
                    e,
                )

        # Shutdown thread pool
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True, cancel_futures=True)
            self._thread_pool = None

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.warning("Error closing server socket: %s", e)
            self._server_socket = None

        # Stop session manager
        self._session_manager.stop()

        # Stop event emitter
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_SERVER_STOPPED,
                {
                    "reason": "shutdown",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            self._event_emitter.stop()

        logger.info("Server stopped")

    def _cleanup(self) -> None:
        """Clean up resources on error."""
        self._running = False

        if self._thread_pool:
            try:
                self._thread_pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._thread_pool = None

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

    def _accept_loop(self) -> None:
        """Main loop for accepting incoming connections."""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Accept with timeout to check shutdown flag
                client_socket, client_address = self._server_socket.accept()

                logger.debug(
                    "Accepted connection from %s:%d",
                    client_address[0],
                    client_address[1],
                )

                # Check if we have capacity
                with self._connections_lock:
                    active_count = len(self._active_connections)
                    if active_count >= self._config.max_connections:
                        logger.warning(
                            "Max connections reached (%d), rejecting %s:%d",
                            self._config.max_connections,
                            client_address[0],
                            client_address[1],
                        )
                        client_socket.close()
                        continue

                # Submit connection handling to thread pool
                future = self._thread_pool.submit(
                    self._handle_connection,
                    client_socket,
                    client_address,
                )

                # Track connection
                connection_id = f"{client_address[0]}:{client_address[1]}"
                with self._connections_lock:
                    self._active_connections[connection_id] = future

                # Add callback to remove from tracking
                future.add_done_callback(
                    lambda f, cid=connection_id: self._connection_done(cid)
                )

            except socket.timeout:
                # Timeout is expected, allows checking shutdown flag
                continue

            except OSError as e:
                if self._running:
                    logger.error("Accept error: %s", e)
                break

            except Exception as e:
                if self._running:
                    logger.exception("Unexpected error in accept loop: %s", e)
                continue

        logger.debug("Accept loop exiting")

    def _connection_done(self, connection_id: str) -> None:
        """Callback when connection handling completes."""
        with self._connections_lock:
            self._active_connections.pop(connection_id, None)

    def _handle_connection(
        self,
        client_socket: socket.socket,
        client_address: Tuple[str, int],
    ) -> None:
        """Handle a single client connection.

        Performs TLS handshake, creates session, and processes
        HTTP requests until disconnect.

        Args:
            client_socket: Client socket.
            client_address: Client IP and port tuple.
        """
        client_addr_str = f"{client_address[0]}:{client_address[1]}"
        session: Optional[Session] = None
        ssl_socket: Optional[ssl.SSLSocket] = None

        try:
            # Perform TLS handshake
            ssl_socket, tls_info = self._tls_handler.wrap_socket(
                client_socket,
                client_address,
            )

            # Emit handshake completed event
            if self._event_emitter:
                self._event_emitter.emit(
                    EVENT_HANDSHAKE_COMPLETED,
                    {
                        "client_address": client_addr_str,
                        "psk_identity": tls_info.psk_identity,
                        "cipher_suite": tls_info.cipher_suite,
                        "protocol_version": tls_info.protocol_version,
                        "handshake_duration_ms": tls_info.handshake_duration_ms,
                    },
                )

            # Create session
            session = self._session_manager.create_session(
                client_address=client_addr_str,
                metadata={
                    "psk_identity": tls_info.psk_identity,
                    "cipher_suite": tls_info.cipher_suite,
                },
            )

            # Update session with TLS info and transition to CONNECTED
            self._session_manager.set_tls_info(session.session_id, tls_info)
            self._session_manager.set_session_state(
                session.session_id,
                SessionState.CONNECTED,
            )

            logger.info(
                "Session established: id=%s, client=%s, identity=%s",
                session.session_id,
                client_addr_str,
                tls_info.psk_identity,
            )

            # Process HTTP requests
            self._handle_session(ssl_socket, session)

        except HandshakeError as e:
            logger.warning(
                "TLS handshake failed for %s: %s",
                client_addr_str,
                e,
            )

            # Emit handshake failed event
            if self._event_emitter:
                self._event_emitter.emit(
                    EVENT_HANDSHAKE_FAILED,
                    {
                        "client_address": client_addr_str,
                        "error": str(e),
                        "alert": e.alert.value if e.alert else None,
                    },
                )

            # Handle via error handler
            self._error_handler.handle_handshake_interrupted(
                client_address=client_addr_str,
                partial_state=e.partial_state,
                reason=str(e),
            )

        except Exception as e:
            logger.exception(
                "Error handling connection from %s: %s",
                client_addr_str,
                e,
            )

            if session:
                self._error_handler.handle_connection_interrupted(
                    session_id=session.session_id,
                    error=str(e),
                )

        finally:
            # Close session if created
            if session and session.state != SessionState.CLOSED:
                self._session_manager.close_session(
                    session.session_id,
                    CloseReason.NORMAL,
                )

            # Close sockets
            if ssl_socket:
                try:
                    ssl_socket.close()
                except Exception:
                    pass

            if client_socket and client_socket != ssl_socket:
                try:
                    client_socket.close()
                except Exception:
                    pass

    def _handle_session(
        self,
        ssl_socket: ssl.SSLSocket,
        session: Session,
    ) -> None:
        """Handle HTTP requests for an established session.

        Args:
            ssl_socket: SSL-wrapped socket.
            session: Active session.
        """
        # Transition to ACTIVE state
        self._session_manager.set_session_state(
            session.session_id,
            SessionState.ACTIVE,
        )

        while self._running and not self._shutdown_event.is_set():
            try:
                # Handle HTTP request
                response = self._http_handler.handle_request(ssl_socket, session)

                # Send response
                ssl_socket.sendall(response.to_bytes())

                # Check for connection close
                if response.headers.get("Connection", "").lower() == "close":
                    logger.debug(
                        "Connection close requested, ending session %s",
                        session.session_id,
                    )
                    break

            except socket.timeout:
                # Check session timeout
                if self._session_manager.get_session(session.session_id) is None:
                    logger.debug(
                        "Session %s expired, closing connection",
                        session.session_id,
                    )
                    break
                continue

            except ssl.SSLError as e:
                if "SHUTDOWN" in str(e).upper():
                    logger.debug(
                        "TLS shutdown for session %s",
                        session.session_id,
                    )
                else:
                    logger.warning(
                        "SSL error in session %s: %s",
                        session.session_id,
                        e,
                    )
                break

            except ConnectionResetError:
                logger.debug(
                    "Connection reset for session %s",
                    session.session_id,
                )
                break

            except BrokenPipeError:
                logger.debug(
                    "Broken pipe for session %s",
                    session.session_id,
                )
                break

            except Exception as e:
                logger.exception(
                    "Error in session %s: %s",
                    session.session_id,
                    e,
                )
                self._error_handler.handle_connection_interrupted(
                    session_id=session.session_id,
                    error=str(e),
                )
                break

    def get_active_sessions(self) -> List[Session]:
        """Get list of currently active sessions.

        Returns:
            List of Session objects in non-CLOSED states.
        """
        return self._session_manager.get_active_sessions()

    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return self._session_manager.get_active_session_count()

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        with self._connections_lock:
            return len(self._active_connections)

    @property
    def tls_handler(self) -> TLSHandler:
        """Get TLS handler instance."""
        return self._tls_handler

    @property
    def session_manager(self) -> SessionManager:
        """Get session manager instance."""
        return self._session_manager

    @property
    def error_handler(self) -> ErrorHandler:
        """Get error handler instance."""
        return self._error_handler

    @property
    def command_processor(self) -> GPCommandProcessor:
        """Get command processor instance."""
        return self._command_processor

    @property
    def http_handler(self) -> HTTPHandler:
        """Get HTTP handler instance."""
        return self._http_handler


# =============================================================================
# Mock Admin Server for Testing
# =============================================================================


class MockAdminServer:
    """Mock admin server for testing without actual network operations.

    Simulates server behavior for unit testing.

    Example:
        >>> server = MockAdminServer()
        >>> server.start()
        >>> assert server.is_running
        >>> server.simulate_connection("192.168.1.1", "test_identity")
        >>> assert len(server.get_active_sessions()) == 1
    """

    def __init__(self) -> None:
        """Initialize mock server."""
        self._running = False
        self._sessions: List[Session] = []
        self._start_count = 0
        self._stop_count = 0

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def start(self) -> None:
        """Start mock server."""
        self._running = True
        self._start_count += 1

    def stop(self, timeout: float = 5.0) -> None:
        """Stop mock server."""
        self._running = False
        self._sessions.clear()
        self._stop_count += 1

    def simulate_connection(
        self,
        client_address: str,
        psk_identity: str,
    ) -> Session:
        """Simulate a new connection."""
        import uuid

        session = Session(
            session_id=str(uuid.uuid4()),
            state=SessionState.ACTIVE,
            client_address=client_address,
            metadata={"psk_identity": psk_identity},
        )
        self._sessions.append(session)
        return session

    def simulate_disconnect(self, session_id: str) -> None:
        """Simulate a disconnection."""
        self._sessions = [s for s in self._sessions if s.session_id != session_id]

    def get_active_sessions(self) -> List[Session]:
        """Get simulated active sessions."""
        return self._sessions.copy()

    def get_session_count(self) -> int:
        """Get number of simulated sessions."""
        return len(self._sessions)

    @property
    def start_count(self) -> int:
        """Get number of times start() was called."""
        return self._start_count

    @property
    def stop_count(self) -> int:
        """Get number of times stop() was called."""
        return self._stop_count
