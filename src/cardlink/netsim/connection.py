"""Connection layer for network simulator integration.

This module provides connection classes for communicating with network simulators
over WebSocket and TCP protocols, with support for automatic reconnection.

Classes:
    BaseConnection: Abstract base class defining connection interface
    WSConnection: WebSocket connection implementation
    TCPConnection: TCP connection with newline-delimited JSON
    ReconnectManager: Automatic reconnection with exponential backoff
"""

import abc
import asyncio
import json
import logging
import ssl
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional
from urllib.parse import urlparse

from cardlink.netsim.constants import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_MAX_MESSAGE_SIZE,
    DEFAULT_MAX_RECONNECT_DELAY,
    DEFAULT_PONG_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_RECONNECT_MULTIPLIER,
)
from cardlink.netsim.exceptions import (
    CircuitBreakerOpenError,
    ConfigurationError,
    ConnectionError,
    PermanentConnectionError,
    RetryableError,
    TimeoutError,
    TransientConnectionError,
)
from cardlink.netsim.types import TLSConfig

log = logging.getLogger(__name__)

# Type alias for message callbacks
MessageCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class BaseConnection(abc.ABC):
    """Abstract base class for all connection types.

    This class defines the interface that all connection implementations must
    follow, ensuring consistent connection handling across different protocols
    (WebSocket, TCP, etc.).

    Subclasses must implement all abstract methods to provide protocol-specific
    connection functionality.

    Attributes:
        url: The connection URL.
        tls_config: TLS/SSL configuration for secure connections.

    Example:
        >>> class MyConnection(BaseConnection):
        ...     async def connect(self):
        ...         # Implementation
        ...         pass
    """

    def __init__(self, url: str, tls_config: Optional[TLSConfig] = None) -> None:
        """Initialize the connection.

        Args:
            url: Connection URL (ws://, wss://, tcp://, tcps://).
            tls_config: Optional TLS configuration for secure connections.
        """
        self.url = url
        self.tls_config = tls_config or TLSConfig()
        self._callbacks: list[MessageCallback] = []

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish connection to the server.

        This method should:
        1. Parse the URL and extract host/port
        2. Create appropriate SSL context if using secure protocol
        3. Establish the connection
        4. Start any background tasks (receive loop, keepalive, etc.)
        5. Set connection state to connected

        Raises:
            ConnectionError: If connection cannot be established.
            ConfigurationError: If URL or configuration is invalid.
            TimeoutError: If connection times out.
        """
        pass

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Close the connection gracefully.

        This method should:
        1. Stop all background tasks
        2. Close the underlying socket/connection
        3. Clean up any resources
        4. Set connection state to disconnected

        This method should be safe to call multiple times (idempotent).
        It should not raise exceptions even if the connection is already closed.
        """
        pass

    @abc.abstractmethod
    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to the server.

        Args:
            message: The message to send (will be JSON-serialized).

        Raises:
            ConnectionError: If not connected or send fails.
        """
        pass

    @abc.abstractmethod
    async def receive(self) -> dict[str, Any]:
        """Receive a single message from the server.

        This method blocks until a message is received.

        Returns:
            The received message (JSON-deserialized).

        Raises:
            ConnectionError: If not connected or receive fails.
            TimeoutError: If receive times out.
        """
        pass

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for incoming messages.

        The callback will be invoked asynchronously for each message received.
        Multiple callbacks can be registered.

        Args:
            callback: Async function to call with each received message.
                     Signature: async def callback(message: dict) -> None
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: MessageCallback) -> None:
        """Remove a previously registered callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _invoke_callbacks(self, message: dict[str, Any]) -> None:
        """Invoke all registered callbacks with a message.

        Args:
            message: The message to pass to callbacks.
        """
        for callback in self._callbacks:
            try:
                await callback(message)
            except Exception as e:
                log.error(f"Error in message callback: {e}")

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is currently established.

        Returns:
            True if connected, False otherwise.
        """
        pass

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context from TLS configuration.

        Returns:
            Configured SSLContext or None if TLS is disabled.

        Raises:
            ConfigurationError: If SSL configuration is invalid.
        """
        if not self.tls_config.enabled:
            return None

        try:
            context = ssl.create_default_context()

            if not self.tls_config.verify_cert:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            else:
                context.verify_mode = ssl.CERT_REQUIRED

            if self.tls_config.ca_cert:
                context.load_verify_locations(self.tls_config.ca_cert)

            if self.tls_config.client_cert and self.tls_config.client_key:
                context.load_cert_chain(
                    self.tls_config.client_cert,
                    self.tls_config.client_key,
                )

            return context

        except ssl.SSLError as e:
            raise ConfigurationError(
                f"Invalid SSL configuration: {e}",
                config_key="tls_config",
            )
        except FileNotFoundError as e:
            raise ConfigurationError(
                f"Certificate file not found: {e}",
                config_key="tls_config",
            )


class WSConnection(BaseConnection):
    """WebSocket connection implementation.

    Provides full-featured WebSocket client supporting:
    - Secure connections (wss://)
    - Automatic keepalive with ping/pong
    - JSON message serialization
    - Asynchronous message callbacks
    - Connection state tracking

    Attributes:
        ping_interval: Interval between ping frames (seconds).
        pong_timeout: Timeout waiting for pong response (seconds).
        max_message_size: Maximum message size in bytes.

    Example:
        >>> conn = WSConnection("wss://callbox.local:9001")
        >>> conn.on_message(handle_message)
        >>> await conn.connect()
        >>> await conn.send({"method": "status"})
        >>> await conn.disconnect()
    """

    def __init__(
        self,
        url: str,
        tls_config: Optional[TLSConfig] = None,
        ping_interval: float = DEFAULT_KEEPALIVE_INTERVAL,
        pong_timeout: float = DEFAULT_PONG_TIMEOUT,
        max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """Initialize WebSocket connection.

        Args:
            url: WebSocket URL (ws:// or wss://).
            tls_config: TLS configuration for secure connections.
            ping_interval: Interval between ping frames (seconds).
            pong_timeout: Timeout waiting for pong response (seconds).
            max_message_size: Maximum message size in bytes.
            connect_timeout: Connection timeout in seconds.
        """
        super().__init__(url, tls_config)
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.max_message_size = max_message_size
        self.connect_timeout = connect_timeout

        self._websocket: Optional[Any] = None  # websockets.WebSocketClientProtocol
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection.

        Raises:
            ConnectionError: If connection fails.
            ConfigurationError: If URL is invalid.
            TimeoutError: If connection times out.
        """
        try:
            import websockets
            from websockets.exceptions import WebSocketException
        except ImportError:
            raise ConfigurationError(
                "websockets library is required for WebSocket connections. "
                "Install with: pip install websockets",
                config_key="url",
            )

        # Validate URL scheme
        parsed = urlparse(self.url)
        if parsed.scheme not in ("ws", "wss"):
            raise ConfigurationError(
                f"Invalid WebSocket URL scheme: {parsed.scheme}. "
                "Use ws:// or wss://",
                config_key="url",
                config_value=self.url,
            )

        # Create SSL context for secure connections
        ssl_context = None
        if parsed.scheme == "wss":
            ssl_context = self._create_ssl_context()

        try:
            log.info(f"Connecting to WebSocket: {self.url}")

            self._websocket = await asyncio.wait_for(
                websockets.connect(
                    self.url,
                    ssl=ssl_context,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.pong_timeout,
                    max_size=self.max_message_size,
                    close_timeout=10,
                ),
                timeout=self.connect_timeout,
            )

            self._connected = True

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            log.info(f"WebSocket connected to {self.url}")

        except asyncio.TimeoutError:
            raise TimeoutError(
                "WebSocket connection timed out",
                operation="connect",
                timeout=self.connect_timeout,
                details={"url": self.url},
            )
        except WebSocketException as e:
            raise ConnectionError(
                f"WebSocket connection failed: {e}",
                url=self.url,
                cause=str(e),
            )
        except OSError as e:
            raise ConnectionError(
                f"Network error during WebSocket connection: {e}",
                url=self.url,
                cause=str(e),
            )

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        self._connected = False

        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Close WebSocket
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                log.debug(f"Error closing WebSocket: {e}")
            self._websocket = None

        log.info("WebSocket disconnected")

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON message over WebSocket.

        Args:
            message: Message to send.

        Raises:
            ConnectionError: If not connected or send fails.
        """
        if not self._connected or not self._websocket:
            raise ConnectionError(
                "Cannot send: not connected",
                details={"state": "disconnected"},
            )

        try:
            json_data = json.dumps(message)
            await self._websocket.send(json_data)
            log.debug(f"Sent: {json_data[:200]}...")
        except Exception as e:
            self._connected = False
            raise ConnectionError(
                f"Send failed: {e}",
                url=self.url,
                cause=str(e),
            )

    async def receive(self) -> dict[str, Any]:
        """Receive a single message from WebSocket.

        Returns:
            Parsed JSON message.

        Raises:
            ConnectionError: If not connected or receive fails.
        """
        if not self._connected or not self._websocket:
            raise ConnectionError(
                "Cannot receive: not connected",
                details={"state": "disconnected"},
            )

        try:
            data = await self._websocket.recv()
            message = json.loads(data)
            log.debug(f"Received: {str(data)[:200]}...")
            return message
        except json.JSONDecodeError as e:
            raise ConnectionError(
                f"Invalid JSON received: {e}",
                details={"raw_data": str(data)[:100]},
            )
        except Exception as e:
            self._connected = False
            raise ConnectionError(
                f"Receive failed: {e}",
                url=self.url,
                cause=str(e),
            )

    async def _receive_loop(self) -> None:
        """Background task to receive and dispatch messages."""
        try:
            import websockets
            from websockets.exceptions import ConnectionClosed
        except ImportError:
            return

        while self._connected and self._websocket:
            try:
                data = await self._websocket.recv()
                message = json.loads(data)
                log.debug(f"Received (loop): {str(data)[:200]}...")

                # Invoke callbacks
                await self._invoke_callbacks(message)

            except ConnectionClosed as e:
                log.warning(f"WebSocket connection closed: {e}")
                self._connected = False
                break
            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON in receive loop: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in receive loop: {e}")
                self._connected = False
                break

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self._websocket is not None


class TCPConnection(BaseConnection):
    """TCP connection with newline-delimited JSON protocol.

    Provides TCP connection supporting:
    - Secure connections (tcps://)
    - Newline-delimited JSON messages
    - Asynchronous message callbacks
    - Connection state tracking

    Protocol:
        Messages are sent as JSON objects terminated by newline (\\n).
        Each line is a complete JSON document.

    Example:
        >>> conn = TCPConnection("tcp://callbox.local:9001")
        >>> conn.on_message(handle_message)
        >>> await conn.connect()
        >>> await conn.send({"method": "status"})
        >>> await conn.disconnect()
    """

    def __init__(
        self,
        url: str,
        tls_config: Optional[TLSConfig] = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        """Initialize TCP connection.

        Args:
            url: TCP URL (tcp:// or tcps://).
            tls_config: TLS configuration for secure connections.
            connect_timeout: Connection timeout in seconds.
            read_timeout: Read timeout in seconds.
        """
        super().__init__(url, tls_config)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False

    def _parse_url(self) -> tuple[str, int, bool]:
        """Parse TCP URL to extract host, port, and TLS flag.

        Returns:
            Tuple of (host, port, use_tls).

        Raises:
            ConfigurationError: If URL is invalid.
        """
        parsed = urlparse(self.url)

        if parsed.scheme not in ("tcp", "tcps"):
            raise ConfigurationError(
                f"Invalid TCP URL scheme: {parsed.scheme}. "
                "Use tcp:// or tcps://",
                config_key="url",
                config_value=self.url,
            )

        if not parsed.hostname:
            raise ConfigurationError(
                "TCP URL must include hostname",
                config_key="url",
                config_value=self.url,
            )

        host = parsed.hostname
        port = parsed.port or (9001 if parsed.scheme == "tcps" else 9000)
        use_tls = parsed.scheme == "tcps"

        return host, port, use_tls

    async def connect(self) -> None:
        """Establish TCP connection.

        Raises:
            ConnectionError: If connection fails.
            ConfigurationError: If URL is invalid.
            TimeoutError: If connection times out.
        """
        host, port, use_tls = self._parse_url()

        # Create SSL context for secure connections
        ssl_context = None
        if use_tls:
            ssl_context = self._create_ssl_context()

        try:
            log.info(f"Connecting to TCP: {host}:{port} (TLS: {use_tls})")

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ssl_context),
                timeout=self.connect_timeout,
            )

            self._connected = True

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            log.info(f"TCP connected to {host}:{port}")

        except asyncio.TimeoutError:
            raise TimeoutError(
                "TCP connection timed out",
                operation="connect",
                timeout=self.connect_timeout,
                details={"host": host, "port": port},
            )
        except ssl.SSLError as e:
            raise ConnectionError(
                f"TLS handshake failed: {e}",
                url=self.url,
                cause=str(e),
            )
        except OSError as e:
            raise ConnectionError(
                f"TCP connection failed: {e}",
                url=self.url,
                cause=str(e),
            )

    async def disconnect(self) -> None:
        """Close TCP connection gracefully."""
        self._connected = False

        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Close writer (which also closes the socket)
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                log.debug(f"Error closing TCP connection: {e}")
            self._writer = None

        self._reader = None

        log.info("TCP disconnected")

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON message over TCP with newline delimiter.

        Args:
            message: Message to send.

        Raises:
            ConnectionError: If not connected or send fails.
        """
        if not self._connected or not self._writer:
            raise ConnectionError(
                "Cannot send: not connected",
                details={"state": "disconnected"},
            )

        try:
            json_data = json.dumps(message) + "\n"
            self._writer.write(json_data.encode("utf-8"))
            await self._writer.drain()
            log.debug(f"Sent: {json_data[:200]}...")
        except Exception as e:
            self._connected = False
            raise ConnectionError(
                f"Send failed: {e}",
                url=self.url,
                cause=str(e),
            )

    async def receive(self) -> dict[str, Any]:
        """Receive a single newline-delimited JSON message.

        Returns:
            Parsed JSON message.

        Raises:
            ConnectionError: If not connected or receive fails.
            TimeoutError: If read times out.
        """
        if not self._connected or not self._reader:
            raise ConnectionError(
                "Cannot receive: not connected",
                details={"state": "disconnected"},
            )

        try:
            line = await asyncio.wait_for(
                self._reader.readline(),
                timeout=self.read_timeout,
            )

            if not line:
                self._connected = False
                raise ConnectionError(
                    "Connection closed by remote host",
                    url=self.url,
                )

            data = line.decode("utf-8").strip()
            message = json.loads(data)
            log.debug(f"Received: {data[:200]}...")
            return message

        except asyncio.TimeoutError:
            raise TimeoutError(
                "Read operation timed out",
                operation="receive",
                timeout=self.read_timeout,
            )
        except json.JSONDecodeError as e:
            raise ConnectionError(
                f"Invalid JSON received: {e}",
                details={"raw_data": data[:100] if data else "empty"},
            )
        except Exception as e:
            self._connected = False
            raise ConnectionError(
                f"Receive failed: {e}",
                url=self.url,
                cause=str(e),
            )

    async def _receive_loop(self) -> None:
        """Background task to receive and dispatch messages."""
        while self._connected and self._reader:
            try:
                line = await self._reader.readline()

                if not line:
                    log.warning("TCP connection closed by remote host")
                    self._connected = False
                    break

                data = line.decode("utf-8").strip()
                if not data:
                    continue

                message = json.loads(data)
                log.debug(f"Received (loop): {data[:200]}...")

                # Invoke callbacks
                await self._invoke_callbacks(message)

            except json.JSONDecodeError as e:
                log.error(f"Invalid JSON in receive loop: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in TCP receive loop: {e}")
                self._connected = False
                break

    @property
    def is_connected(self) -> bool:
        """Check if TCP connection is established."""
        return self._connected and self._writer is not None


@dataclass
class ReconnectState:
    """State tracking for reconnection attempts."""

    attempt_count: int = 0
    last_attempt: Optional[datetime] = None
    is_reconnecting: bool = False
    current_delay: float = DEFAULT_RECONNECT_DELAY


class ReconnectManager:
    """Automatic reconnection manager with exponential backoff.

    Provides intelligent reconnection logic that:
    - Uses exponential backoff to avoid overwhelming servers
    - Respects maximum delay and attempt limits
    - Emits events for monitoring reconnection status
    - Handles concurrent reconnection attempts safely

    Attributes:
        initial_delay: Initial delay between reconnection attempts (seconds).
        max_delay: Maximum delay between attempts (seconds).
        multiplier: Backoff multiplier for exponential increase.
        max_attempts: Maximum reconnection attempts (0 = unlimited).

    Example:
        >>> manager = ReconnectManager()
        >>> manager.on_reconnect_start(handle_start)
        >>> manager.on_reconnect_success(handle_success)
        >>> await manager.reconnect(connection)
    """

    def __init__(
        self,
        initial_delay: float = DEFAULT_RECONNECT_DELAY,
        max_delay: float = DEFAULT_MAX_RECONNECT_DELAY,
        multiplier: float = DEFAULT_RECONNECT_MULTIPLIER,
        max_attempts: int = 0,
    ) -> None:
        """Initialize reconnection manager.

        Args:
            initial_delay: Initial delay between attempts (seconds).
            max_delay: Maximum delay (seconds).
            multiplier: Exponential backoff multiplier.
            max_attempts: Maximum attempts (0 = unlimited).
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_attempts = max_attempts

        self._state = ReconnectState(current_delay=initial_delay)
        self._lock = asyncio.Lock()

        # Event callbacks
        self._on_start: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._on_success: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._on_failure: list[Callable[[Exception], Coroutine[Any, Any, None]]] = []
        self._on_attempt: list[
            Callable[[int, float], Coroutine[Any, Any, None]]
        ] = []

    def on_reconnect_start(
        self, callback: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for reconnection start.

        Args:
            callback: Async function called when reconnection starts.
        """
        self._on_start.append(callback)

    def on_reconnect_success(
        self, callback: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for successful reconnection.

        Args:
            callback: Async function called on successful reconnection.
        """
        self._on_success.append(callback)

    def on_reconnect_failure(
        self, callback: Callable[[Exception], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for final reconnection failure.

        Args:
            callback: Async function called when all attempts exhausted.
        """
        self._on_failure.append(callback)

    def on_reconnect_attempt(
        self, callback: Callable[[int, float], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for each reconnection attempt.

        Args:
            callback: Async function called on each attempt with
                     (attempt_number, delay_seconds).
        """
        self._on_attempt.append(callback)

    async def reconnect(self, connection: BaseConnection) -> bool:
        """Attempt to reconnect with exponential backoff.

        This method will retry connection attempts until successful,
        max_attempts is reached, or the operation is cancelled.

        Args:
            connection: The connection to reconnect.

        Returns:
            True if reconnection successful, False if max attempts reached.

        Raises:
            asyncio.CancelledError: If reconnection is cancelled.
        """
        async with self._lock:
            if self._state.is_reconnecting:
                log.debug("Reconnection already in progress")
                return False

            self._state.is_reconnecting = True

        try:
            # Emit start event
            await self._emit_start()

            while True:
                self._state.attempt_count += 1
                self._state.last_attempt = datetime.utcnow()

                # Check max attempts
                if self.max_attempts > 0 and self._state.attempt_count > self.max_attempts:
                    log.warning(
                        f"Max reconnection attempts ({self.max_attempts}) reached"
                    )
                    await self._emit_failure(
                        ConnectionError(
                            f"Max reconnection attempts ({self.max_attempts}) reached"
                        )
                    )
                    return False

                # Emit attempt event
                await self._emit_attempt(
                    self._state.attempt_count, self._state.current_delay
                )

                log.info(
                    f"Reconnection attempt {self._state.attempt_count} "
                    f"(delay: {self._state.current_delay:.1f}s)"
                )

                # Wait before attempting
                await asyncio.sleep(self._state.current_delay)

                try:
                    await connection.connect()

                    # Success!
                    log.info(
                        f"Reconnected after {self._state.attempt_count} attempts"
                    )
                    self.reset()
                    await self._emit_success()
                    return True

                except Exception as e:
                    log.warning(f"Reconnection attempt failed: {e}")

                    # Calculate next delay with exponential backoff
                    self._state.current_delay = min(
                        self._state.current_delay * self.multiplier,
                        self.max_delay,
                    )

        finally:
            self._state.is_reconnecting = False

    def reset(self) -> None:
        """Reset reconnection state.

        Call this after a successful manual connection to reset
        the backoff delay and attempt counter.
        """
        self._state.attempt_count = 0
        self._state.current_delay = self.initial_delay
        self._state.last_attempt = None
        log.debug("Reconnection state reset")

    @property
    def is_reconnecting(self) -> bool:
        """Check if reconnection is currently in progress."""
        return self._state.is_reconnecting

    @property
    def attempt_count(self) -> int:
        """Get current attempt count."""
        return self._state.attempt_count

    async def _emit_start(self) -> None:
        """Emit reconnection start events."""
        for callback in self._on_start:
            try:
                await callback()
            except Exception as e:
                log.error(f"Error in reconnect start callback: {e}")

    async def _emit_success(self) -> None:
        """Emit reconnection success events."""
        for callback in self._on_success:
            try:
                await callback()
            except Exception as e:
                log.error(f"Error in reconnect success callback: {e}")

    async def _emit_failure(self, error: Exception) -> None:
        """Emit reconnection failure events."""
        for callback in self._on_failure:
            try:
                await callback(error)
            except Exception as e:
                log.error(f"Error in reconnect failure callback: {e}")

    async def _emit_attempt(self, attempt: int, delay: float) -> None:
        """Emit reconnection attempt events."""
        for callback in self._on_attempt:
            try:
                await callback(attempt, delay)
            except Exception as e:
                log.error(f"Error in reconnect attempt callback: {e}")


def create_connection(
    url: str,
    tls_config: Optional[TLSConfig] = None,
    **kwargs: Any,
) -> BaseConnection:
    """Factory function to create appropriate connection based on URL scheme.

    Args:
        url: Connection URL (ws://, wss://, tcp://, tcps://).
        tls_config: Optional TLS configuration.
        **kwargs: Additional arguments passed to connection constructor.

    Returns:
        Appropriate connection instance (WSConnection or TCPConnection).

    Raises:
        ConfigurationError: If URL scheme is not supported.

    Example:
        >>> conn = create_connection("wss://callbox.local:9001")
        >>> await conn.connect()
    """
    parsed = urlparse(url)

    if parsed.scheme in ("ws", "wss"):
        return WSConnection(url, tls_config, **kwargs)
    elif parsed.scheme in ("tcp", "tcps"):
        return TCPConnection(url, tls_config, **kwargs)
    else:
        raise ConfigurationError(
            f"Unsupported URL scheme: {parsed.scheme}. "
            "Supported schemes: ws, wss, tcp, tcps",
            config_key="url",
            config_value=url,
        )


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================


class CircuitBreakerState:
    """State enumeration for circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        success_threshold: Successes needed to close from half-open.
        timeout: Seconds before transitioning from open to half-open.
        excluded_exceptions: Exception types that don't count as failures.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    excluded_exceptions: tuple = ()


class CircuitBreaker:
    """Circuit breaker for connection resilience.

    Implements the circuit breaker pattern to prevent cascading failures
    when a service is experiencing issues. After a threshold of failures,
    the circuit "opens" and fails fast without attempting operations.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Failing fast, requests immediately rejected
        - HALF_OPEN: Testing if service recovered, limited requests

    Attributes:
        config: Circuit breaker configuration.
        state: Current circuit state.

    Example:
        >>> breaker = CircuitBreaker()
        >>> async with breaker.protect():
        ...     await some_operation()
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration.
        """
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

        # Callbacks
        self._on_state_change: list[Callable[[str, str], Coroutine[Any, Any, None]]] = []

    @property
    def state(self) -> str:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitBreakerState.OPEN

    def on_state_change(
        self, callback: Callable[[str, str], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for state changes.

        Args:
            callback: Async function called with (old_state, new_state).
        """
        self._on_state_change.append(callback)

    async def _change_state(self, new_state: str) -> None:
        """Change circuit state and emit event.

        Args:
            new_state: The new state to transition to.
        """
        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state

        log.info(f"Circuit breaker state change: {old_state} -> {new_state}")

        for callback in self._on_state_change:
            try:
                await callback(old_state, new_state)
            except Exception as e:
                log.error(f"Error in circuit breaker callback: {e}")

    async def _check_timeout(self) -> None:
        """Check if timeout has elapsed and transition to half-open."""
        if self._state != CircuitBreakerState.OPEN:
            return

        if self._last_failure_time is None:
            return

        import time
        elapsed = time.time() - self._last_failure_time

        if elapsed >= self.config.timeout:
            await self._change_state(CircuitBreakerState.HALF_OPEN)
            self._success_count = 0

    async def record_success(self) -> None:
        """Record a successful operation.

        In HALF_OPEN state, accumulates successes toward closing.
        In CLOSED state, resets failure count.
        """
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._change_state(CircuitBreakerState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self, exception: Optional[Exception] = None) -> None:
        """Record a failed operation.

        Args:
            exception: The exception that caused the failure.
        """
        # Check if exception should be excluded
        if exception and isinstance(exception, self.config.excluded_exceptions):
            log.debug(f"Exception excluded from circuit breaker: {type(exception)}")
            return

        async with self._lock:
            import time
            self._last_failure_time = time.time()
            self._failure_count += 1

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open immediately opens
                await self._change_state(CircuitBreakerState.OPEN)
            elif self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._change_state(CircuitBreakerState.OPEN)

    async def can_execute(self) -> bool:
        """Check if an operation can be executed.

        Returns:
            True if operation is allowed, False if circuit is open.
        """
        async with self._lock:
            await self._check_timeout()

            if self._state == CircuitBreakerState.OPEN:
                return False

            return True

    async def execute(
        self,
        operation: Callable[[], Coroutine[Any, Any, Any]],
    ) -> Any:
        """Execute an operation with circuit breaker protection.

        Args:
            operation: Async function to execute.

        Returns:
            Result of the operation.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
            Exception: Any exception from the operation.
        """
        if not await self.can_execute():
            import time
            open_until = None
            if self._last_failure_time:
                open_until = self._last_failure_time + self.config.timeout

            raise CircuitBreakerOpenError(
                "Circuit breaker open - too many failures",
                open_until=open_until,
                failure_count=self._failure_count,
            )

        try:
            result = await operation()
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to closed state.

        Use after manual intervention or known recovery.
        """
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        log.info("Circuit breaker reset to CLOSED")


# =============================================================================
# Retry Utilities
# =============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including initial).
        initial_delay: Initial delay between retries (seconds).
        max_delay: Maximum delay between retries (seconds).
        multiplier: Delay multiplier for exponential backoff.
        retryable_exceptions: Exception types to retry on.
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    retryable_exceptions: tuple = (RetryableError, TimeoutError)


async def retry_operation(
    operation: Callable[[], Coroutine[Any, Any, Any]],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], Coroutine[Any, Any, None]]] = None,
) -> Any:
    """Execute an operation with automatic retries.

    Uses exponential backoff between attempts. Only retries on
    exceptions matching retryable_exceptions.

    Args:
        operation: Async function to execute.
        config: Retry configuration.
        on_retry: Optional callback called before each retry with
                 (attempt_number, exception, delay).

    Returns:
        Result of the operation.

    Raises:
        Exception: The last exception if all retries fail.

    Example:
        >>> result = await retry_operation(
        ...     lambda: connection.connect(),
        ...     RetryConfig(max_attempts=3),
        ... )
    """
    config = config or RetryConfig()
    delay = config.initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await operation()
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt == config.max_attempts:
                log.warning(
                    f"Operation failed after {attempt} attempts: {e}"
                )
                raise

            log.info(
                f"Retry attempt {attempt}/{config.max_attempts} "
                f"after {delay:.1f}s (error: {e})"
            )

            if on_retry:
                try:
                    await on_retry(attempt, e, delay)
                except Exception as callback_error:
                    log.error(f"Error in retry callback: {callback_error}")

            await asyncio.sleep(delay)
            delay = min(delay * config.multiplier, config.max_delay)

        except Exception as e:
            # Non-retryable exception
            log.debug(f"Non-retryable exception: {type(e).__name__}: {e}")
            raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly")


def classify_connection_error(
    error: Exception, url: str = ""
) -> ConnectionError:
    """Classify a connection error as transient or permanent.

    Analyzes the error type and message to determine if the error
    is likely to succeed on retry (transient) or not (permanent).

    Args:
        error: The original exception.
        url: The URL that was being connected to.

    Returns:
        TransientConnectionError or PermanentConnectionError.

    Example:
        >>> try:
        ...     await connect()
        ... except Exception as e:
        ...     classified = classify_connection_error(e, url)
        ...     if isinstance(classified, TransientConnectionError):
        ...         # Safe to retry
        ...         pass
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Permanent errors - don't retry
    permanent_patterns = [
        "certificate",
        "ssl",
        "tls",
        "authentication",
        "permission denied",
        "access denied",
        "invalid url",
        "invalid host",
        "name or service not known",
        "getaddrinfo failed",
        "no such host",
    ]

    for pattern in permanent_patterns:
        if pattern in error_str:
            return PermanentConnectionError(
                f"Permanent connection error: {error}",
                url=url,
                cause=error_type,
            )

    # Transient errors - safe to retry
    transient_patterns = [
        "connection refused",
        "connection reset",
        "connection aborted",
        "broken pipe",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "try again",
        "network unreachable",
        "no route to host",
    ]

    for pattern in transient_patterns:
        if pattern in error_str:
            return TransientConnectionError(
                f"Transient connection error: {error}",
                url=url,
                cause=error_type,
            )

    # Default to transient for unknown errors (optimistic)
    return TransientConnectionError(
        f"Connection error (assuming transient): {error}",
        url=url,
        cause=error_type,
    )
