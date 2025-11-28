"""Server configuration dataclasses.

This module defines configuration dataclasses for the PSK-TLS Admin Server,
including server settings and cipher suite configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CipherConfig:
    """TLS cipher suite configuration.

    Attributes:
        production_ciphers: List of production-grade cipher suites (AES-CBC-SHA256/384).
        legacy_ciphers: List of legacy cipher suites (AES-CBC-SHA).
        null_ciphers: List of NULL cipher suites for testing only.
        enable_legacy: Whether to enable legacy cipher suites.
        enable_null_ciphers: Whether to enable NULL ciphers (DANGEROUS - testing only).

    Example:
        >>> config = CipherConfig(enable_legacy=True)
        >>> config.get_enabled_ciphers()
        ['TLS_PSK_WITH_AES_128_CBC_SHA256', ...]
    """

    production_ciphers: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_AES_128_CBC_SHA256",
        "TLS_PSK_WITH_AES_256_CBC_SHA384",
    ])
    legacy_ciphers: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_AES_128_CBC_SHA",
        "TLS_PSK_WITH_AES_256_CBC_SHA",
    ])
    null_ciphers: List[str] = field(default_factory=lambda: [
        "TLS_PSK_WITH_NULL_SHA",
        "TLS_PSK_WITH_NULL_SHA256",
    ])
    enable_legacy: bool = False
    enable_null_ciphers: bool = False

    def get_enabled_ciphers(self) -> List[str]:
        """Get list of enabled cipher suites.

        Returns:
            List of cipher suite names that are currently enabled.
        """
        ciphers = list(self.production_ciphers)

        if self.enable_legacy:
            ciphers.extend(self.legacy_ciphers)

        if self.enable_null_ciphers:
            ciphers.extend(self.null_ciphers)

        return ciphers

    def get_openssl_cipher_string(self) -> str:
        """Get OpenSSL cipher string for enabled ciphers.

        Returns:
            Colon-separated cipher string for OpenSSL.
        """
        return ":".join(self.get_enabled_ciphers())


@dataclass
class ServerConfig:
    """PSK-TLS Admin Server configuration.

    Attributes:
        host: Server bind address.
        port: Server listen port.
        max_connections: Maximum concurrent connections.
        session_timeout: Session timeout in seconds.
        handshake_timeout: TLS handshake timeout in seconds.
        read_timeout: HTTP read timeout in seconds.
        backlog: Socket listen backlog.
        thread_pool_size: Number of worker threads for connection handling.
        cipher_config: Cipher suite configuration.
        enable_dashboard: Whether to enable web dashboard.
        dashboard_port: Web dashboard port (if enabled).
        key_store_path: Path to YAML key store file (optional).
        log_level: Logging level.

    Example:
        >>> config = ServerConfig(port=8443, session_timeout=600)
        >>> config.cipher_config.enable_legacy = True
    """

    host: str = "0.0.0.0"
    port: int = 8443
    max_connections: int = 100
    session_timeout: float = 300.0  # 5 minutes
    handshake_timeout: float = 30.0
    read_timeout: float = 30.0
    backlog: int = 5
    thread_pool_size: int = 10
    cipher_config: CipherConfig = field(default_factory=CipherConfig)
    enable_dashboard: bool = False
    dashboard_port: int = 8080
    key_store_path: Optional[str] = None
    log_level: str = "INFO"

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid.
        """
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")

        if self.max_connections < 1:
            raise ValueError(f"Invalid max_connections: {self.max_connections}")

        if self.session_timeout <= 0:
            raise ValueError(f"Invalid session_timeout: {self.session_timeout}")

        if self.handshake_timeout <= 0:
            raise ValueError(f"Invalid handshake_timeout: {self.handshake_timeout}")

        if self.read_timeout <= 0:
            raise ValueError(f"Invalid read_timeout: {self.read_timeout}")

        if self.thread_pool_size < 1:
            raise ValueError(f"Invalid thread_pool_size: {self.thread_pool_size}")

        if self.enable_dashboard and (self.dashboard_port < 1 or self.dashboard_port > 65535):
            raise ValueError(f"Invalid dashboard_port: {self.dashboard_port}")
