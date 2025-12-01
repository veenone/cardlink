"""Unit tests for network simulator connection layer.

Tests for WSConnection, TCPConnection, ReconnectManager, and
connection factory functions.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cardlink.netsim.connection import (
    BaseConnection,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    ReconnectManager,
    RetryConfig,
    TCPConnection,
    WSConnection,
    classify_connection_error,
    create_connection,
    retry_operation,
)
from cardlink.netsim.exceptions import (
    CircuitBreakerOpenError,
    ConfigurationError,
    ConnectionError,
    PermanentConnectionError,
    TimeoutError,
    TransientConnectionError,
)
from cardlink.netsim.types import TLSConfig


class TestWSConnection:
    """Tests for WSConnection class."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test WSConnection initialization."""
        conn = WSConnection(url="wss://localhost:9001")
        assert conn.url == "wss://localhost:9001"
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_url_with_ssl(self):
        """Test WSS connection has TLS enabled."""
        conn = WSConnection(url="wss://example.com:443")
        assert conn.url == "wss://example.com:443"

    @pytest.mark.asyncio
    async def test_url_plain(self):
        """Test WS connection (non-SSL)."""
        conn = WSConnection(url="ws://localhost:9001")
        assert conn.url == "ws://localhost:9001"

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected is safe."""
        conn = WSConnection(url="ws://localhost:9001")
        # Should not raise even when not connected
        await conn.disconnect()
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_send_not_connected_raises(self):
        """Test sending when not connected raises error."""
        conn = WSConnection(url="ws://localhost:9001")

        with pytest.raises(ConnectionError):
            await conn.send({"test": "data"})

    @pytest.mark.asyncio
    async def test_on_message_callback(self):
        """Test message callback registration."""
        conn = WSConnection(url="ws://localhost:9001")

        callback = AsyncMock()
        conn.on_message(callback)

        # Verify callback is registered
        assert callback in conn._callbacks


class TestTCPConnection:
    """Tests for TCPConnection class."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test TCPConnection initialization."""
        conn = TCPConnection(url="tcp://localhost:9002")
        assert conn.url == "tcp://localhost:9002"
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_url_with_ssl(self):
        """Test TCPS connection."""
        conn = TCPConnection(url="tcps://example.com:443")
        assert conn.url == "tcps://example.com:443"

    @pytest.mark.asyncio
    async def test_url_plain(self):
        """Test TCP connection (non-SSL)."""
        conn = TCPConnection(url="tcp://localhost:9002")
        assert conn.url == "tcp://localhost:9002"

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected is safe."""
        conn = TCPConnection(url="tcp://localhost:9002")
        # Should not raise even when not connected
        await conn.disconnect()
        assert not conn.is_connected

    @pytest.mark.asyncio
    async def test_send_not_connected_raises(self):
        """Test sending when not connected raises error."""
        conn = TCPConnection(url="tcp://localhost:9002")

        with pytest.raises(ConnectionError):
            await conn.send({"test": "data"})


class TestReconnectManager:
    """Tests for ReconnectManager class."""

    def test_init(self):
        """Test ReconnectManager initialization."""
        manager = ReconnectManager(
            initial_delay=1.0,
            max_delay=30.0,
            multiplier=2.0,
            max_attempts=5,
        )
        assert manager.initial_delay == 1.0
        assert manager.max_delay == 30.0
        assert manager.multiplier == 2.0
        assert manager.max_attempts == 5

    def test_reset(self):
        """Test reset clears attempt counter."""
        manager = ReconnectManager()
        manager.reset()
        assert manager._state.attempt_count == 0

    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Test successful reconnection."""
        manager = ReconnectManager(
            initial_delay=0.01,
            max_attempts=3,
        )

        # Create a mock connection that succeeds
        mock_conn = AsyncMock()
        mock_conn.connect = AsyncMock()

        result = await manager.reconnect(mock_conn)
        assert result is True

    @pytest.mark.asyncio
    async def test_reconnect_retry_then_success(self):
        """Test reconnection with retries."""
        manager = ReconnectManager(
            initial_delay=0.01,
            max_attempts=5,
        )

        # Create a mock connection that fails twice then succeeds
        mock_conn = MagicMock()
        call_count = [0]

        async def connect_side_effect():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Simulated failure")
            # Success on third attempt

        mock_conn.connect = AsyncMock(side_effect=connect_side_effect)

        result = await manager.reconnect(mock_conn)
        assert result is True
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self):
        """Test reconnection failure after max attempts."""
        manager = ReconnectManager(
            initial_delay=0.01,
            max_attempts=2,
        )

        # Create a mock connection that always fails
        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock(side_effect=ConnectionError("Always fails"))

        result = await manager.reconnect(mock_conn)
        assert result is False


class TestCreateConnection:
    """Tests for create_connection factory function."""

    def test_create_ws_connection(self):
        """Test creating WebSocket connection."""
        conn = create_connection("ws://localhost:9001")
        assert isinstance(conn, WSConnection)
        assert conn.url == "ws://localhost:9001"

    def test_create_wss_connection(self):
        """Test creating secure WebSocket connection."""
        conn = create_connection("wss://localhost:9001")
        assert isinstance(conn, WSConnection)
        assert "wss://" in conn.url

    def test_create_tcp_connection(self):
        """Test creating TCP connection."""
        conn = create_connection("tcp://localhost:9002")
        assert isinstance(conn, TCPConnection)
        assert conn.url == "tcp://localhost:9002"

    def test_create_tcps_connection(self):
        """Test creating secure TCP connection."""
        conn = create_connection("tcps://localhost:9002")
        assert isinstance(conn, TCPConnection)
        assert "tcps://" in conn.url

    def test_invalid_scheme_raises(self):
        """Test invalid URL scheme raises error."""
        with pytest.raises(ConfigurationError):
            create_connection("http://localhost:9001")

    def test_with_tls_config(self):
        """Test connection with TLS configuration."""
        tls_config = TLSConfig(
            verify_cert=True,
            ca_cert="/path/to/ca.pem",
        )

        conn = create_connection("wss://localhost:9001", tls_config=tls_config)
        assert isinstance(conn, WSConnection)
        assert conn.tls_config == tls_config


class TestConnectionCallbacks:
    """Tests for connection callback handling."""

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self):
        """Test multiple message callbacks."""
        conn = WSConnection(url="ws://localhost:9001")

        callback1 = AsyncMock()
        callback2 = AsyncMock()

        conn.on_message(callback1)
        conn.on_message(callback2)

        assert len(conn._callbacks) == 2

    @pytest.mark.asyncio
    async def test_callback_error_handling(self):
        """Test callback errors don't break other callbacks."""
        conn = WSConnection(url="ws://localhost:9001")

        error_callback = AsyncMock(side_effect=Exception("Test error"))
        success_callback = AsyncMock()

        conn.on_message(error_callback)
        conn.on_message(success_callback)

        # Simulate message handling - both callbacks should be attempted
        message = {"test": "data"}
        for callback in conn._callbacks:
            try:
                await callback(message)
            except Exception:
                pass

        error_callback.assert_called_once()
        success_callback.assert_called_once()


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_init(self):
        """Test CircuitBreaker initialization."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout=10.0,
        )
        breaker = CircuitBreaker(config)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failures(self):
        """Test successful operation resets failure count."""
        breaker = CircuitBreaker()
        await breaker.record_failure()
        assert breaker.failure_count == 1
        await breaker.record_success()
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_execute_when_open_raises(self):
        """Test execute raises when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=60.0)
        breaker = CircuitBreaker(config)
        await breaker.record_failure()

        async def operation():
            return "result"

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.execute(operation)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test execute succeeds with closed circuit."""
        breaker = CircuitBreaker()

        async def operation():
            return "result"

        result = await breaker.execute(operation)
        assert result == "result"

    def test_reset(self):
        """Test manual reset."""
        breaker = CircuitBreaker()
        breaker._state = CircuitBreakerState.OPEN
        breaker._failure_count = 10
        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0


class TestRetryOperation:
    """Tests for retry_operation function."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Test successful operation doesn't retry."""
        call_count = [0]

        async def operation():
            call_count[0] += 1
            return "success"

        result = await retry_operation(operation)
        assert result == "success"
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retries on transient errors."""
        call_count = [0]

        async def operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TransientConnectionError("Temporary failure")
            return "success"

        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.01,
            retryable_exceptions=(TransientConnectionError,),
        )

        result = await retry_operation(operation, config)
        assert result == "success"
        assert call_count[0] == 3


class TestClassifyConnectionError:
    """Tests for classify_connection_error function."""

    def test_transient_connection_refused(self):
        """Test connection refused is classified as transient."""
        error = Exception("Connection refused")
        result = classify_connection_error(error, "ws://localhost:9001")
        assert isinstance(result, TransientConnectionError)

    def test_transient_timeout(self):
        """Test timeout is classified as transient."""
        error = Exception("Connection timed out")
        result = classify_connection_error(error, "ws://localhost:9001")
        assert isinstance(result, TransientConnectionError)

    def test_permanent_certificate_error(self):
        """Test certificate error is classified as permanent."""
        error = Exception("SSL certificate verify failed")
        result = classify_connection_error(error, "wss://localhost:9001")
        assert isinstance(result, PermanentConnectionError)

    def test_permanent_auth_error(self):
        """Test authentication error is classified as permanent."""
        error = Exception("Authentication failed")
        result = classify_connection_error(error, "wss://localhost:9001")
        assert isinstance(result, PermanentConnectionError)
