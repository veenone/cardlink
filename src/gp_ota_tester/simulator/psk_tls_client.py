"""PSK-TLS client for connecting to admin server.

This module provides a TLS-PSK client that establishes secure connections
to the PSK-TLS Admin Server for GP Amendment B communication.
"""

import asyncio
import logging
import socket
import ssl
import time
from typing import Optional, Tuple

from .models import TLSConnectionInfo

logger = logging.getLogger(__name__)


class PSKTLSClientError(Exception):
    """Base exception for PSK-TLS client errors."""

    pass


class ConnectionError(PSKTLSClientError):
    """Connection establishment failed."""

    pass


class HandshakeError(PSKTLSClientError):
    """TLS handshake failed."""

    pass


class TimeoutError(PSKTLSClientError):
    """Operation timed out."""

    pass


class PSKTLSClient:
    """TLS-PSK client for connecting to admin server.

    Establishes PSK-TLS connections to the admin server and provides
    async send/receive operations over the encrypted channel.

    Attributes:
        host: Server hostname or IP address.
        port: Server port number.
        psk_identity: PSK identity for authentication.
        psk_key: PSK key bytes.
        timeout: Connection and read timeout in seconds.

    Example:
        >>> client = PSKTLSClient(
        ...     host="127.0.0.1",
        ...     port=8443,
        ...     psk_identity="test_card",
        ...     psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10")
        ... )
        >>> await client.connect()
        >>> await client.send(b"data")
        >>> response = await client.receive()
        >>> await client.close()
    """

    # Supported PSK cipher suites
    PSK_CIPHERS = [
        "TLS_PSK_WITH_AES_128_CBC_SHA256",
        "TLS_PSK_WITH_AES_256_CBC_SHA384",
        "TLS_PSK_WITH_AES_128_CBC_SHA",
        "TLS_PSK_WITH_AES_256_CBC_SHA",
    ]

    def __init__(
        self,
        host: str,
        port: int,
        psk_identity: str,
        psk_key: bytes,
        timeout: float = 30.0,
    ):
        """Initialize TLS client with connection parameters.

        Args:
            host: Server hostname or IP address.
            port: Server port number.
            psk_identity: PSK identity for authentication.
            psk_key: PSK key bytes (16 or 32 bytes).
            timeout: Connection and read timeout in seconds.
        """
        self.host = host
        self.port = port
        self.psk_identity = psk_identity
        self.psk_key = psk_key
        self.timeout = timeout

        self._socket: Optional[socket.socket] = None
        self._ssl_socket: Optional[ssl.SSLSocket] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._connection_info: Optional[TLSConnectionInfo] = None

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected and self._writer is not None

    @property
    def connection_info(self) -> Optional[TLSConnectionInfo]:
        """Get connection information."""
        return self._connection_info

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for PSK-TLS client mode.

        Returns:
            Configured SSL context.

        Raises:
            ImportError: If sslpsk3 is not available.
        """
        try:
            import sslpsk3
        except ImportError as e:
            raise ImportError(
                "sslpsk3 library is required for PSK-TLS support. "
                "Install with: pip install sslpsk3"
            ) from e

        # Create context for TLS client
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Set cipher suites
        try:
            context.set_ciphers(":".join(self.PSK_CIPHERS))
        except ssl.SSLError:
            # Fallback to PSK cipher filter
            context.set_ciphers("PSK")

        return context

    def _psk_callback(
        self, ssl_socket: ssl.SSLSocket, hint: Optional[str]
    ) -> Tuple[str, bytes]:
        """PSK callback to provide identity and key.

        Args:
            ssl_socket: The SSL socket.
            hint: Server-provided PSK identity hint (may be None).

        Returns:
            Tuple of (psk_identity, psk_key).
        """
        logger.debug(f"PSK callback called, hint: {hint}")
        return self.psk_identity, self.psk_key

    async def connect(self) -> TLSConnectionInfo:
        """Establish PSK-TLS connection to server.

        Returns:
            TLSConnectionInfo with connection details.

        Raises:
            ConnectionError: If connection cannot be established.
            HandshakeError: If TLS handshake fails.
            TimeoutError: If connection times out.
        """
        if self._connected:
            raise ConnectionError("Already connected")

        start_time = time.monotonic()
        logger.info(f"Connecting to {self.host}:{self.port}...")

        try:
            import sslpsk3
        except ImportError as e:
            raise ImportError(
                "sslpsk3 library is required for PSK-TLS support. "
                "Install with: pip install sslpsk3"
            ) from e

        try:
            # Create TCP socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)

            # Connect to server
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self._socket.connect, (self.host, self.port)
                    ),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Connection timeout after {self.timeout}s")
            except socket.error as e:
                raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

            # Wrap socket with PSK-TLS
            try:
                self._ssl_socket = sslpsk3.wrap_socket(
                    self._socket,
                    psk=lambda hint: (self.psk_identity, self.psk_key),
                    server_side=False,
                    ssl_version=ssl.PROTOCOL_TLSv1_2,
                    ciphers=":".join(self.PSK_CIPHERS),
                )
            except ssl.SSLError as e:
                error_msg = str(e)
                if "unknown_psk_identity" in error_msg.lower():
                    raise HandshakeError(f"Unknown PSK identity: {self.psk_identity}")
                elif "handshake failure" in error_msg.lower():
                    raise HandshakeError(f"TLS handshake failed: {e}")
                else:
                    raise HandshakeError(f"SSL error: {e}")
            except Exception as e:
                raise HandshakeError(f"Failed to wrap socket with PSK-TLS: {e}")

            # Set non-blocking for asyncio
            self._ssl_socket.setblocking(False)

            # Create asyncio streams
            loop = asyncio.get_event_loop()
            self._reader, self._writer = await asyncio.open_connection(
                sock=self._ssl_socket
            )

            # Calculate handshake duration
            handshake_duration_ms = (time.monotonic() - start_time) * 1000

            # Get connection info
            cipher_suite = self._ssl_socket.cipher()
            self._connection_info = TLSConnectionInfo(
                cipher_suite=cipher_suite[0] if cipher_suite else "unknown",
                psk_identity=self.psk_identity,
                protocol_version=self._ssl_socket.version() or "TLSv1.2",
                handshake_duration_ms=handshake_duration_ms,
                server_address=f"{self.host}:{self.port}",
            )

            self._connected = True
            logger.info(
                f"Connected to {self.host}:{self.port} "
                f"(cipher: {self._connection_info.cipher_suite}, "
                f"handshake: {handshake_duration_ms:.1f}ms)"
            )

            return self._connection_info

        except (ConnectionError, HandshakeError, TimeoutError):
            await self._cleanup()
            raise
        except Exception as e:
            await self._cleanup()
            raise ConnectionError(f"Unexpected connection error: {e}") from e

    async def send(self, data: bytes) -> None:
        """Send data over TLS connection.

        Args:
            data: Data bytes to send.

        Raises:
            ConnectionError: If not connected or send fails.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        try:
            self._writer.write(data)
            await self._writer.drain()
            logger.debug(f"Sent {len(data)} bytes")
        except Exception as e:
            raise ConnectionError(f"Failed to send data: {e}") from e

    async def receive(self, max_bytes: int = 4096) -> bytes:
        """Receive data from TLS connection.

        Args:
            max_bytes: Maximum bytes to read.

        Returns:
            Received data bytes.

        Raises:
            ConnectionError: If not connected or receive fails.
            TimeoutError: If read times out.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        try:
            data = await asyncio.wait_for(
                self._reader.read(max_bytes),
                timeout=self.timeout,
            )
            logger.debug(f"Received {len(data)} bytes")
            return data
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except Exception as e:
            raise ConnectionError(f"Failed to receive data: {e}") from e

    async def receive_until(self, delimiter: bytes) -> bytes:
        """Receive data until delimiter is found.

        Args:
            delimiter: Bytes to search for in stream.

        Returns:
            Received data including delimiter.

        Raises:
            ConnectionError: If not connected or receive fails.
            TimeoutError: If read times out.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        try:
            data = await asyncio.wait_for(
                self._reader.readuntil(delimiter),
                timeout=self.timeout,
            )
            logger.debug(f"Received {len(data)} bytes (until delimiter)")
            return data
        except asyncio.IncompleteReadError as e:
            return e.partial
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except Exception as e:
            raise ConnectionError(f"Failed to receive data: {e}") from e

    async def receive_exactly(self, num_bytes: int) -> bytes:
        """Receive exactly the specified number of bytes.

        Args:
            num_bytes: Exact number of bytes to read.

        Returns:
            Received data bytes.

        Raises:
            ConnectionError: If not connected or receive fails.
            TimeoutError: If read times out.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(num_bytes),
                timeout=self.timeout,
            )
            logger.debug(f"Received exactly {len(data)} bytes")
            return data
        except asyncio.IncompleteReadError as e:
            raise ConnectionError(f"Connection closed, received only {len(e.partial)} bytes")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except Exception as e:
            raise ConnectionError(f"Failed to receive data: {e}") from e

    async def close(self) -> None:
        """Close TLS connection gracefully."""
        logger.info("Closing TLS connection...")
        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up connection resources."""
        self._connected = False

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

        if self._ssl_socket:
            try:
                self._ssl_socket.close()
            except Exception:
                pass
            self._ssl_socket = None

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        logger.debug("Connection cleaned up")

    async def __aenter__(self) -> "PSKTLSClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
