"""Setting model for GP OTA Tester.

This module defines the Setting model for storing server
configuration as key-value pairs.

Example:
    >>> from gp_ota_tester.database.models import Setting
    >>> setting = Setting(
    ...     key="server.port",
    ...     value=8443,
    ...     category="server",
    ...     description="Server listening port",
    ... )
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import Index, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from gp_ota_tester.database.models.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """Server configuration setting model.

    Stores configuration as key-value pairs with optional
    categorization and descriptions.

    Attributes:
        key: Setting key (primary key).
        value: Setting value (JSON for any type).
        description: Human-readable description.
        category: Setting category for grouping.

    Example:
        >>> setting = Setting(key="server.port", value=8443)
        >>> setting.value
        8443
    """

    __tablename__ = "settings"

    # Primary key
    key: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        doc="Setting key (e.g., 'server.port')",
    )

    # Value (JSON for flexibility)
    value: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
        doc="Setting value (any JSON-serializable type)",
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        doc="Human-readable description",
    )

    # Category for grouping
    category: Mapped[str] = mapped_column(
        String(64),
        default="general",
        nullable=False,
        doc="Setting category for grouping",
    )

    # Table configuration
    __table_args__ = (Index("idx_setting_category", "category"),)

    @property
    def is_boolean(self) -> bool:
        """Check if value is boolean."""
        return isinstance(self.value, bool)

    @property
    def is_string(self) -> bool:
        """Check if value is string."""
        return isinstance(self.value, str)

    @property
    def is_number(self) -> bool:
        """Check if value is a number."""
        return isinstance(self.value, (int, float)) and not isinstance(self.value, bool)

    @property
    def is_list(self) -> bool:
        """Check if value is a list."""
        return isinstance(self.value, list)

    @property
    def is_dict(self) -> bool:
        """Check if value is a dictionary."""
        return isinstance(self.value, dict)

    def as_bool(self, default: bool = False) -> bool:
        """Get value as boolean.

        Args:
            default: Default value if conversion fails.

        Returns:
            Boolean value.
        """
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "on")
        if isinstance(self.value, (int, float)):
            return bool(self.value)
        return default

    def as_int(self, default: int = 0) -> int:
        """Get value as integer.

        Args:
            default: Default value if conversion fails.

        Returns:
            Integer value.
        """
        try:
            return int(self.value)
        except (TypeError, ValueError):
            return default

    def as_float(self, default: float = 0.0) -> float:
        """Get value as float.

        Args:
            default: Default value if conversion fails.

        Returns:
            Float value.
        """
        try:
            return float(self.value)
        except (TypeError, ValueError):
            return default

    def as_string(self, default: str = "") -> str:
        """Get value as string.

        Args:
            default: Default value if None.

        Returns:
            String value.
        """
        if self.value is None:
            return default
        return str(self.value)

    def as_list(self, default: Optional[List] = None) -> List:
        """Get value as list.

        Args:
            default: Default value if not a list.

        Returns:
            List value.
        """
        if isinstance(self.value, list):
            return self.value
        return default if default is not None else []

    def as_dict(self, default: Optional[Dict] = None) -> Dict:
        """Get value as dictionary.

        Args:
            default: Default value if not a dict.

        Returns:
            Dict value.
        """
        if isinstance(self.value, dict):
            return self.value
        return default if default is not None else {}

    @classmethod
    def create(
        cls,
        key: str,
        value: Any,
        category: str = "general",
        description: Optional[str] = None,
    ) -> "Setting":
        """Create a new setting.

        Args:
            key: Setting key.
            value: Setting value.
            category: Setting category.
            description: Setting description.

        Returns:
            New Setting instance.
        """
        return cls(
            key=key,
            value=value,
            category=category,
            description=description,
        )


# Common setting keys
class SettingKeys:
    """Common setting key constants."""

    # Server settings
    SERVER_HOST = "server.host"
    SERVER_PORT = "server.port"
    SERVER_SESSION_TIMEOUT = "server.session_timeout"
    SERVER_MAX_CONNECTIONS = "server.max_connections"

    # TLS settings
    TLS_CIPHER_SUITES = "tls.cipher_suites"
    TLS_ALLOW_LEGACY = "tls.allow_legacy"
    TLS_ALLOW_NULL = "tls.allow_null"

    # Logging settings
    LOG_LEVEL = "logging.level"
    LOG_FILE = "logging.file"
    LOG_MAX_SIZE = "logging.max_size"
    LOG_BACKUP_COUNT = "logging.backup_count"

    # Database settings
    DB_POOL_SIZE = "database.pool_size"
    DB_POOL_TIMEOUT = "database.pool_timeout"
    DB_ECHO = "database.echo"

    # Test settings
    TEST_TIMEOUT = "test.timeout"
    TEST_RETRIES = "test.retries"
