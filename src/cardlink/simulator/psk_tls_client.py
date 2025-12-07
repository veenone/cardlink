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

    # Supported PSK cipher suites per GlobalPlatform GPC_SPE_011 Table 3-2
    # Using OpenSSL cipher names (not IANA names)
    # Production ciphers (TLS 1.2 mandatory)
    PSK_CIPHERS = [
        "PSK-AES128-CBC-SHA256",  # Mandatory per GP spec
        "PSK-AES256-CBC-SHA384",  # Recommended
        "PSK-AES128-CBC-SHA",     # Legacy support
        "PSK-AES256-CBC-SHA",     # Legacy support
    ]

    # NULL ciphers for testing only (NO ENCRYPTION)
    PSK_NULL_CIPHERS = [
        "PSK-NULL-SHA256",
        "PSK-NULL-SHA",
    ]

    def __init__(
        self,
        host: str,
        port: int,
        psk_identity: str,
        psk_key: bytes,
        timeout: float = 30.0,
        enable_null_ciphers: bool = False,
    ):
        """Initialize TLS client with connection parameters.

        Args:
            host: Server hostname or IP address.
            port: Server port number.
            psk_identity: PSK identity for authentication.
            psk_key: PSK key bytes (16 or 32 bytes).
            timeout: Connection and read timeout in seconds.
            enable_null_ciphers: Enable NULL ciphers for testing (DANGEROUS - no encryption).

        Note:
            Per GlobalPlatform GPC_SPE_011 Table 3-2, the following cipher suites are supported:
            - TLS_PSK_WITH_AES_128_CBC_SHA256 (mandatory)
            - TLS_PSK_WITH_AES_256_CBC_SHA384 (recommended)
            - TLS_PSK_WITH_NULL_SHA256 (testing only)
        """
        self.host = host
        self.port = port
        self.psk_identity = psk_identity
        self.psk_key = psk_key
        self.timeout = timeout
        self._enable_null_ciphers = enable_null_ciphers

        # Store identity as bytes for sslpsk3 callback
        self._psk_identity_bytes = psk_identity.encode('utf-8') if isinstance(psk_identity, str) else psk_identity

        self._socket: Optional[socket.socket] = None
        self._ssl_socket: Optional[ssl.SSLSocket] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._connection_info: Optional[TLSConnectionInfo] = None

        # Warn about NULL ciphers
        if enable_null_ciphers:
            logger.warning(
                "NULL ciphers enabled - traffic will be UNENCRYPTED. For testing only!"
            )

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected and self._ssl_socket is not None

    @property
    def connection_info(self) -> Optional[TLSConnectionInfo]:
        """Get connection information."""
        return self._connection_info

    def _get_cipher_string(self) -> str:
        """Get OpenSSL cipher string for enabled ciphers.

        Returns:
            Colon-separated cipher string for OpenSSL.
        """
        ciphers = list(self.PSK_CIPHERS)
        if self._enable_null_ciphers:
            ciphers.extend(self.PSK_NULL_CIPHERS)
        return ":".join(ciphers)

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
            # Uses cipher suites per GlobalPlatform GPC_SPE_011 Table 3-2
            try:
                cipher_string = self._get_cipher_string()
                logger.debug(f"Using cipher suites: {cipher_string}")

                # sslpsk3 client callback returns (psk, identity) - PSK first, then identity
                self._ssl_socket = sslpsk3.wrap_socket(
                    self._socket,
                    psk=lambda hint: (self.psk_key, self._psk_identity_bytes),
                    server_side=False,
                    ssl_version=ssl.PROTOCOL_TLSv1_2,
                    ciphers=cipher_string,
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

            # Keep socket blocking for synchronous I/O
            # We'll use sync read/write wrapped in run_in_executor for async
            self._ssl_socket.setblocking(True)
            self._ssl_socket.settimeout(self.timeout)

            # Store the socket directly - we'll use sync I/O
            self._connected = True
            self._reader = None  # Not using asyncio streams
            self._writer = None  # Not using asyncio streams

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
            # Use synchronous send wrapped in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._ssl_socket.sendall, data)
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
            # Use synchronous recv wrapped in executor
            loop = asyncio.get_event_loop()
            data = await asyncio.wait_for(
                loop.run_in_executor(None, self._ssl_socket.recv, max_bytes),
                timeout=self.timeout,
            )
            logger.debug(f"Received {len(data)} bytes")
            return data
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except socket.timeout:
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
            loop = asyncio.get_event_loop()
            buffer = b""
            start_time = time.monotonic()

            while True:
                # Check timeout
                elapsed = time.monotonic() - start_time
                if elapsed >= self.timeout:
                    raise TimeoutError(f"Read timeout after {self.timeout}s")

                # Read one byte at a time to find delimiter
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, self._ssl_socket.recv, 1),
                    timeout=self.timeout - elapsed,
                )

                if not chunk:
                    # Connection closed
                    logger.debug(f"Received {len(buffer)} bytes (connection closed)")
                    return buffer

                buffer += chunk
                if buffer.endswith(delimiter):
                    logger.debug(f"Received {len(buffer)} bytes (until delimiter)")
                    return buffer

        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except socket.timeout:
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
            loop = asyncio.get_event_loop()
            buffer = b""
            start_time = time.monotonic()

            while len(buffer) < num_bytes:
                # Check timeout
                elapsed = time.monotonic() - start_time
                if elapsed >= self.timeout:
                    raise TimeoutError(f"Read timeout after {self.timeout}s")

                remaining = num_bytes - len(buffer)
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, self._ssl_socket.recv, remaining),
                    timeout=self.timeout - elapsed,
                )

                if not chunk:
                    raise ConnectionError(f"Connection closed, received only {len(buffer)} bytes")

                buffer += chunk

            logger.debug(f"Received exactly {len(buffer)} bytes")
            return buffer
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except socket.timeout:
            raise TimeoutError(f"Read timeout after {self.timeout}s")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"Failed to receive data: {e}") from e

    async def close(self) -> None:
        """Close TLS connection gracefully."""
        logger.info("Closing TLS connection...")
        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up connection resources."""
        self._connected = False

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

        self._reader = None
        self._writer = None

        logger.debug("Connection cleaned up")

    async def __aenter__(self) -> "PSKTLSClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
