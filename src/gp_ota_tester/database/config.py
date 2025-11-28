"""Database configuration for GP OTA Tester.

This module provides database configuration management with support
for environment variables and multiple database backends.

Environment Variables:
    DATABASE_URL: Database connection URL (overrides all other settings)
    CARDLINK_DB_HOST: Database host
    CARDLINK_DB_PORT: Database port
    CARDLINK_DB_NAME: Database name
    CARDLINK_DB_USER: Database username
    CARDLINK_DB_PASSWORD: Database password

Example:
    >>> from gp_ota_tester.database.config import DatabaseConfig
    >>> config = DatabaseConfig()
    >>> print(config.url)
    'sqlite:///data/cardlink.db'

    >>> config = DatabaseConfig(url="mysql://user:pass@localhost/dbname")
    >>> print(config.is_mysql)
    True
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from gp_ota_tester.database.exceptions import ConfigurationError


# Default database file path relative to project root
DEFAULT_SQLITE_PATH = "data/cardlink.db"


@dataclass
class DatabaseConfig:
    """Database configuration settings.

    Supports SQLite (default), MySQL, and PostgreSQL backends.
    Configuration can be provided directly or via environment variables.

    Attributes:
        url: Full database connection URL.
        pool_size: Connection pool size (for pooled backends).
        max_overflow: Maximum overflow connections.
        pool_timeout: Connection pool timeout in seconds.
        echo: Whether to log SQL statements.

    Example:
        >>> # Default SQLite
        >>> config = DatabaseConfig()
        >>>
        >>> # Custom SQLite path
        >>> config = DatabaseConfig(url="sqlite:///custom/path.db")
        >>>
        >>> # MySQL
        >>> config = DatabaseConfig(url="mysql://user:pass@localhost/db")
        >>>
        >>> # PostgreSQL
        >>> config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
    """

    url: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False

    def __post_init__(self) -> None:
        """Initialize configuration, applying environment overrides."""
        if self.url is None:
            self.url = self._resolve_url()

    def _resolve_url(self) -> str:
        """Resolve database URL from environment or defaults.

        Returns:
            Database connection URL.
        """
        # Check for explicit DATABASE_URL
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url

        # Check for component-based configuration
        host = os.environ.get("CARDLINK_DB_HOST")
        if host:
            return self._build_url_from_components()

        # Default to SQLite
        return f"sqlite:///{DEFAULT_SQLITE_PATH}"

    def _build_url_from_components(self) -> str:
        """Build URL from environment variable components.

        Returns:
            Database connection URL.

        Raises:
            ConfigurationError: If required components are missing.
        """
        host = os.environ.get("CARDLINK_DB_HOST", "localhost")
        port = os.environ.get("CARDLINK_DB_PORT")
        name = os.environ.get("CARDLINK_DB_NAME", "cardlink")
        user = os.environ.get("CARDLINK_DB_USER")
        password = os.environ.get("CARDLINK_DB_PASSWORD")
        driver = os.environ.get("CARDLINK_DB_DRIVER", "mysql")

        if driver not in ("mysql", "postgresql", "sqlite"):
            raise ConfigurationError(
                f"Unsupported database driver: {driver}. "
                "Use 'mysql', 'postgresql', or 'sqlite'."
            )

        if driver == "sqlite":
            return f"sqlite:///{name}"

        if not user:
            raise ConfigurationError(
                "CARDLINK_DB_USER required for MySQL/PostgreSQL"
            )

        # Build URL
        auth = user
        if password:
            auth = f"{user}:{password}"

        host_part = host
        if port:
            host_part = f"{host}:{port}"

        return f"{driver}://{auth}@{host_part}/{name}"

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite backend."""
        return self.url.startswith("sqlite")

    @property
    def is_mysql(self) -> bool:
        """Check if using MySQL backend."""
        return self.url.startswith("mysql")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL backend."""
        return self.url.startswith("postgresql") or self.url.startswith("postgres")

    @property
    def backend_name(self) -> str:
        """Get human-readable backend name."""
        if self.is_sqlite:
            return "SQLite"
        elif self.is_mysql:
            return "MySQL"
        elif self.is_postgresql:
            return "PostgreSQL"
        return "Unknown"

    @property
    def database_name(self) -> str:
        """Get database name from URL."""
        if self.is_sqlite:
            # Extract file path
            path = self.url.replace("sqlite:///", "")
            return Path(path).name if path != ":memory:" else ":memory:"

        # Parse URL for other backends
        parsed = urlparse(self.url)
        return parsed.path.lstrip("/") if parsed.path else "unknown"

    @property
    def safe_url(self) -> str:
        """Get URL with password redacted for logging.

        Returns:
            URL string with password replaced by asterisks.
        """
        if "@" not in self.url:
            return self.url

        # Parse and redact
        parsed = urlparse(self.url)
        if parsed.password:
            # Reconstruct with redacted password
            auth = parsed.username or ""
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            path = parsed.path or ""
            return f"{parsed.scheme}://{auth}:***@{host}{port}{path}"

        return self.url

    def validate(self) -> None:
        """Validate configuration settings.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        if not self.url:
            raise ConfigurationError("Database URL is required")

        if self.pool_size < 1:
            raise ConfigurationError("pool_size must be at least 1")

        if self.max_overflow < 0:
            raise ConfigurationError("max_overflow cannot be negative")

        if self.pool_timeout < 1:
            raise ConfigurationError("pool_timeout must be at least 1 second")

        # Validate URL format
        if not any([
            self.url.startswith("sqlite"),
            self.url.startswith("mysql"),
            self.url.startswith("postgresql"),
            self.url.startswith("postgres"),
        ]):
            raise ConfigurationError(
                f"Unsupported database URL scheme: {self.url.split(':')[0]}"
            )

    def get_sqlite_path(self) -> Optional[Path]:
        """Get SQLite database file path.

        Returns:
            Path to SQLite file, or None if not using SQLite.
        """
        if not self.is_sqlite:
            return None

        path_str = self.url.replace("sqlite:///", "")
        if path_str == ":memory:":
            return None

        return Path(path_str)

    def copy(self, **kwargs) -> "DatabaseConfig":
        """Create a copy with optional overrides.

        Args:
            **kwargs: Fields to override.

        Returns:
            New DatabaseConfig instance.
        """
        return DatabaseConfig(
            url=kwargs.get("url", self.url),
            pool_size=kwargs.get("pool_size", self.pool_size),
            max_overflow=kwargs.get("max_overflow", self.max_overflow),
            pool_timeout=kwargs.get("pool_timeout", self.pool_timeout),
            echo=kwargs.get("echo", self.echo),
        )

    @classmethod
    def for_testing(cls) -> "DatabaseConfig":
        """Create configuration for testing with in-memory SQLite.

        Returns:
            DatabaseConfig configured for testing.
        """
        return cls(
            url="sqlite:///:memory:",
            echo=False,
        )

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "DatabaseConfig":
        """Create configuration from URL.

        Args:
            url: Database connection URL.
            **kwargs: Additional configuration options.

        Returns:
            DatabaseConfig instance.
        """
        return cls(url=url, **kwargs)
