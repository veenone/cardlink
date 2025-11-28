"""TLS Handler for PSK-TLS connections.

This module provides TLS handling for PSK (Pre-Shared Key) authenticated
connections as required by GlobalPlatform SCP81.

Security Note:
    - NULL ciphers (TLS_PSK_WITH_NULL_*) are for testing only and provide NO encryption.
    - PSK keys are NEVER logged. Only PSK identities may be logged.
    - TLS 1.2 is required for PSK cipher suites per SCP81 specification.

Example:
    >>> from gp_ota_tester.server.tls_handler import TLSHandler
    >>> handler = TLSHandler(key_store, cipher_config)
    >>> ssl_socket, session_info = handler.wrap_socket(client_socket, client_addr)
"""

import logging
import socket
import ssl
import time
from typing import Optional, Tuple

from gp_ota_tester.server.config import CipherConfig
from gp_ota_tester.server.key_store import KeyStore
from gp_ota_tester.server.models import (
    HandshakeProgress,
    HandshakeState,
    TLSAlert,
    TLSSessionInfo,
)

logger = logging.getLogger(__name__)

# Try to import sslpsk3 for PSK support
try:
    import sslpsk3 as sslpsk

    HAS_PSK_SUPPORT = True
except ImportError:
    sslpsk = None  # type: ignore
    HAS_PSK_SUPPORT = False
    logger.warning(
        "sslpsk3 not available. PSK-TLS support disabled. "
        "Install with: pip install sslpsk3"
    )


class TLSHandlerError(Exception):
    """Base exception for TLS handler errors."""

    pass


class HandshakeError(TLSHandlerError):
    """TLS handshake failed."""

    def __init__(
        self,
        message: str,
        alert: Optional[TLSAlert] = None,
        partial_state: Optional[HandshakeProgress] = None,
    ):
        super().__init__(message)
        self.alert = alert
        self.partial_state = partial_state


class TLSHandler:
    """Handles TLS connections with PSK authentication.

    Provides PSK-TLS connection handling for SCP81 OTA sessions.
    Uses sslpsk3 library for PSK cipher suite support.

    Attributes:
        key_store: Key store for PSK lookup.
        cipher_config: Cipher suite configuration.

    Example:
        >>> key_store = FileKeyStore("keys.yaml")
        >>> cipher_config = CipherConfig(enable_legacy=True)
        >>> handler = TLSHandler(key_store, cipher_config)
        >>>
        >>> # Wrap a socket
        >>> ssl_sock, info = handler.wrap_socket(sock, ("192.168.1.1", 12345))
        >>> print(f"Connected with {info.cipher_suite}")
    """

    def __init__(
        self,
        key_store: KeyStore,
        cipher_config: Optional[CipherConfig] = None,
        handshake_timeout: float = 30.0,
    ) -> None:
        """Initialize TLS Handler.

        Args:
            key_store: Key store for PSK lookup.
            cipher_config: Cipher suite configuration. Uses defaults if None.
            handshake_timeout: Timeout for TLS handshake in seconds.

        Raises:
            RuntimeError: If sslpsk3 is not available.
        """
        if not HAS_PSK_SUPPORT:
            raise RuntimeError(
                "PSK-TLS support requires sslpsk3. Install with: pip install sslpsk3"
            )

        self._key_store = key_store
        self._cipher_config = cipher_config or CipherConfig()
        self._handshake_timeout = handshake_timeout

        # Warn about NULL ciphers
        if self._cipher_config.enable_null_ciphers:
            logger.warning(
                "╔════════════════════════════════════════════════════════════╗"
            )
            logger.warning(
                "║  WARNING: NULL CIPHERS ENABLED - NO ENCRYPTION!            ║"
            )
            logger.warning(
                "║  Traffic will be UNENCRYPTED. For testing only!            ║"
            )
            logger.warning(
                "╚════════════════════════════════════════════════════════════╝"
            )

        # Create SSL context
        self._ssl_context = self._create_ssl_context()

        logger.info(
            "TLS Handler initialized with ciphers: %s",
            self._cipher_config.get_enabled_ciphers(),
        )

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with PSK configuration.

        Returns:
            Configured SSL context.
        """
        # Create server-side SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Set minimum TLS version to 1.2 (required for SCP81)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2

        # Set cipher suites
        cipher_string = self._cipher_config.get_openssl_cipher_string()
        try:
            context.set_ciphers(cipher_string)
        except ssl.SSLError as e:
            logger.error("Failed to set cipher suites '%s': %s", cipher_string, e)
            raise TLSHandlerError(f"Invalid cipher configuration: {e}") from e

        # Disable certificate verification (using PSK instead)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        return context

    def _psk_callback(self, identity: Optional[bytes]) -> Optional[bytes]:
        """PSK callback function for sslpsk3.

        Called during TLS handshake to retrieve the PSK for an identity.

        Args:
            identity: PSK identity bytes from client.

        Returns:
            PSK key bytes, or None if identity not found (fails handshake).
        """
        if identity is None:
            logger.warning("PSK callback received None identity")
            return None

        try:
            identity_str = identity.decode("utf-8")
        except UnicodeDecodeError:
            identity_str = identity.hex()
            logger.warning("Non-UTF8 PSK identity received: %s", identity_str)

        # Log identity (NEVER log the key!)
        logger.debug("PSK identity requested: %s", identity_str)

        # Look up key in store
        key = self._key_store.get_key(identity_str)

        if key is None:
            logger.warning("Unknown PSK identity: %s", identity_str)
            return None

        # Return key (NEVER log this value!)
        return key

    def wrap_socket(
        self,
        sock: socket.socket,
        client_address: Tuple[str, int],
    ) -> Tuple[ssl.SSLSocket, TLSSessionInfo]:
        """Wrap a socket with TLS using PSK authentication.

        Performs TLS handshake with the client using PSK authentication.

        Args:
            sock: Plain socket to wrap.
            client_address: Client IP address and port tuple.

        Returns:
            Tuple of (wrapped SSL socket, TLS session info).

        Raises:
            HandshakeError: If TLS handshake fails.
        """
        client_addr_str = f"{client_address[0]}:{client_address[1]}"
        progress = HandshakeProgress(
            state=HandshakeState.INITIAL,
            client_address=client_addr_str,
        )

        # Track handshake timing
        start_time = time.monotonic()
        psk_identity: Optional[str] = None

        # Create callback that captures the identity
        def psk_callback_wrapper(identity: Optional[bytes]) -> Optional[bytes]:
            nonlocal psk_identity
            if identity:
                try:
                    psk_identity = identity.decode("utf-8")
                except UnicodeDecodeError:
                    psk_identity = identity.hex()
            return self._psk_callback(identity)

        try:
            # Set socket timeout for handshake
            sock.settimeout(self._handshake_timeout)

            # Wrap socket with PSK-TLS
            progress.state = HandshakeState.CLIENT_HELLO_RECEIVED
            progress.messages_received.append("ClientHello")

            ssl_sock = sslpsk.wrap_socket(
                sock,
                server_side=True,
                ssl_version=ssl.PROTOCOL_TLS_SERVER,
                ciphers=self._cipher_config.get_openssl_cipher_string(),
                psk=psk_callback_wrapper,
            )

            progress.state = HandshakeState.FINISHED
            progress.messages_received.append("Finished")

            # Calculate handshake duration
            handshake_duration = (time.monotonic() - start_time) * 1000

            # Get negotiated cipher
            cipher_info = ssl_sock.cipher()
            cipher_suite = cipher_info[0] if cipher_info else "UNKNOWN"

            # Check for NULL cipher warning
            if "NULL" in cipher_suite.upper():
                logger.warning(
                    "╔════════════════════════════════════════════════════════════╗"
                )
                logger.warning(
                    "║  UNENCRYPTED CONNECTION from %s", client_addr_str.ljust(20) + " ║"
                )
                logger.warning(
                    "║  Cipher: %s", cipher_suite.ljust(47) + " ║"
                )
                logger.warning(
                    "╚════════════════════════════════════════════════════════════╝"
                )

            # Create session info
            session_info = TLSSessionInfo(
                cipher_suite=cipher_suite,
                psk_identity=psk_identity or "unknown",
                protocol_version="TLSv1.2",
                handshake_duration_ms=handshake_duration,
                client_address=client_addr_str,
            )

            logger.info(
                "TLS handshake completed: client=%s, cipher=%s, identity=%s, duration=%.1fms",
                client_addr_str,
                cipher_suite,
                psk_identity,
                handshake_duration,
            )

            return ssl_sock, session_info

        except socket.timeout:
            progress.state = HandshakeState.FAILED
            progress.error = "Handshake timeout"
            self._handle_handshake_error(
                "Handshake timeout",
                progress,
                TLSAlert.HANDSHAKE_FAILURE,
            )
            raise HandshakeError(
                f"TLS handshake timeout after {self._handshake_timeout}s",
                alert=TLSAlert.HANDSHAKE_FAILURE,
                partial_state=progress,
            )

        except ssl.SSLError as e:
            progress.state = HandshakeState.FAILED
            progress.error = str(e)
            alert = self._map_ssl_error_to_alert(e)
            self._handle_handshake_error(str(e), progress, alert)
            raise HandshakeError(
                f"TLS handshake failed: {e}",
                alert=alert,
                partial_state=progress,
            ) from e

        except Exception as e:
            progress.state = HandshakeState.FAILED
            progress.error = str(e)
            self._handle_handshake_error(str(e), progress, TLSAlert.INTERNAL_ERROR)
            raise HandshakeError(
                f"TLS handshake error: {e}",
                alert=TLSAlert.INTERNAL_ERROR,
                partial_state=progress,
            ) from e

    def _handle_handshake_error(
        self,
        error_message: str,
        progress: HandshakeProgress,
        alert: TLSAlert,
    ) -> None:
        """Log and handle handshake errors.

        Args:
            error_message: Error description.
            progress: Handshake progress state.
            alert: TLS alert code.
        """
        logger.error(
            "TLS handshake failed: client=%s, state=%s, messages=%s, error=%s, alert=%s",
            progress.client_address,
            progress.state.value,
            progress.messages_received,
            error_message,
            TLSAlert.get_description(alert),
        )

        # Log additional context for debugging
        if progress.state == HandshakeState.CLIENT_HELLO_RECEIVED:
            logger.info(
                "Handshake failed after ClientHello - possible network issue or "
                "client abort for client %s",
                progress.client_address,
            )

    def _map_ssl_error_to_alert(self, error: ssl.SSLError) -> TLSAlert:
        """Map SSL error to TLS alert code.

        Args:
            error: SSL error from handshake.

        Returns:
            Appropriate TLS alert code.
        """
        error_str = str(error).lower()

        if "unknown psk identity" in error_str:
            return TLSAlert.UNKNOWN_PSK_IDENTITY
        elif "decrypt" in error_str or "mac" in error_str:
            return TLSAlert.DECRYPT_ERROR
        elif "handshake" in error_str:
            return TLSAlert.HANDSHAKE_FAILURE
        elif "protocol" in error_str or "version" in error_str:
            return TLSAlert.PROTOCOL_VERSION
        elif "certificate" in error_str:
            return TLSAlert.BAD_CERTIFICATE
        else:
            return TLSAlert.INTERNAL_ERROR

    @property
    def cipher_config(self) -> CipherConfig:
        """Get current cipher configuration."""
        return self._cipher_config

    @property
    def handshake_timeout(self) -> float:
        """Get handshake timeout in seconds."""
        return self._handshake_timeout


class MockTLSHandler:
    """Mock TLS handler for testing without actual TLS.

    Provides a testing interface that bypasses actual TLS handshake.
    Useful for unit testing server components.

    Example:
        >>> handler = MockTLSHandler()
        >>> handler.set_next_identity("test_card")
        >>> ssl_sock, info = handler.wrap_socket(sock, addr)
        >>> assert info.psk_identity == "test_card"
    """

    def __init__(self) -> None:
        """Initialize mock TLS handler."""
        self._next_identity = "mock_identity"
        self._next_cipher = "TLS_PSK_WITH_AES_128_CBC_SHA256"
        self._should_fail = False
        self._fail_reason: Optional[str] = None

    def set_next_identity(self, identity: str) -> None:
        """Set identity for next wrap_socket call."""
        self._next_identity = identity

    def set_next_cipher(self, cipher: str) -> None:
        """Set cipher suite for next wrap_socket call."""
        self._next_cipher = cipher

    def set_should_fail(self, should_fail: bool, reason: str = "Mock failure") -> None:
        """Configure whether next handshake should fail."""
        self._should_fail = should_fail
        self._fail_reason = reason

    def wrap_socket(
        self,
        sock: socket.socket,
        client_address: Tuple[str, int],
    ) -> Tuple[socket.socket, TLSSessionInfo]:
        """Mock wrap_socket that returns the original socket.

        Args:
            sock: Socket to "wrap".
            client_address: Client address.

        Returns:
            Tuple of (original socket, mock session info).

        Raises:
            HandshakeError: If configured to fail.
        """
        if self._should_fail:
            raise HandshakeError(
                self._fail_reason or "Mock handshake failure",
                alert=TLSAlert.HANDSHAKE_FAILURE,
            )

        session_info = TLSSessionInfo(
            cipher_suite=self._next_cipher,
            psk_identity=self._next_identity,
            protocol_version="TLSv1.2",
            handshake_duration_ms=1.0,
            client_address=f"{client_address[0]}:{client_address[1]}",
        )

        return sock, session_info
