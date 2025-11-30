"""Database exceptions for GP OTA Tester.

This module defines custom exceptions for database operations,
providing clear error handling throughout the database layer.

Example:
    >>> from cardlink.database.exceptions import NotFoundError
    >>> raise NotFoundError("Device", "device_123")
"""

from typing import Any, Optional


class DatabaseError(Exception):
    """Base exception for all database errors.

    All database-related exceptions inherit from this class,
    allowing for broad exception handling.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """Initialize database error.

        Args:
            message: Error description.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.cause = cause


class ConnectionError(DatabaseError):
    """Failed to connect to the database.

    Raised when database connection cannot be established
    or when the connection is lost unexpectedly.

    Example:
        >>> raise ConnectionError("Failed to connect to MySQL at localhost:3306")
    """

    pass


class MigrationError(DatabaseError):
    """Database migration failed.

    Raised when Alembic migrations encounter errors
    during upgrade or downgrade operations.

    Example:
        >>> raise MigrationError("Migration abc123 failed: column already exists")
    """

    pass


class IntegrityError(DatabaseError):
    """Data integrity constraint violation.

    Raised when an operation violates database constraints
    such as unique, foreign key, or check constraints.

    Example:
        >>> raise IntegrityError("Duplicate ICCID: 89012345678901234567")
    """

    def __init__(
        self,
        message: str,
        constraint: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize integrity error.

        Args:
            message: Error description.
            constraint: Name of the violated constraint.
            cause: Original exception.
        """
        super().__init__(message, cause)
        self.constraint = constraint


class NotFoundError(DatabaseError):
    """Entity not found in database.

    Raised when attempting to retrieve, update, or delete
    an entity that does not exist.

    Example:
        >>> raise NotFoundError("Device", "device_123")
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        message: Optional[str] = None,
    ):
        """Initialize not found error.

        Args:
            entity_type: Type of entity (e.g., "Device", "CardProfile").
            entity_id: ID of the missing entity.
            message: Optional custom message.
        """
        if message is None:
            message = f"{entity_type} not found: {entity_id}"
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id


class ValidationError(DatabaseError):
    """Data validation failed.

    Raised when data fails validation before
    being inserted or updated in the database.

    Example:
        >>> raise ValidationError("psk_key", "Key must be at least 16 bytes")
    """

    def __init__(
        self,
        field: str,
        message: str,
        value: Optional[Any] = None,
    ):
        """Initialize validation error.

        Args:
            field: Name of the invalid field.
            message: Validation error message.
            value: The invalid value (optional, may contain sensitive data).
        """
        super().__init__(f"Validation error for '{field}': {message}")
        self.field = field
        self.validation_message = message
        self.value = value


class EncryptionError(DatabaseError):
    """Encryption or decryption failed.

    Raised when PSK key encryption or decryption fails,
    typically due to missing or invalid encryption key.

    Example:
        >>> raise EncryptionError("Decryption failed: invalid key")
    """

    pass


class ConfigurationError(DatabaseError):
    """Invalid database configuration.

    Raised when database configuration is invalid
    or missing required settings.

    Example:
        >>> raise ConfigurationError("DATABASE_URL not set")
    """

    pass
