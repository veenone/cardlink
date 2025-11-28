"""Base model for GP OTA Tester database models.

This module provides the SQLAlchemy declarative base and common mixins
used by all database models.

Example:
    >>> from gp_ota_tester.database.models.base import Base, TimestampMixin
    >>> class MyModel(Base, TimestampMixin):
    ...     __tablename__ = 'my_table'
    ...     id = Column(Integer, primary_key=True)
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func


def generate_uuid() -> str:
    """Generate a new UUID string.

    Returns:
        UUID4 string (36 characters).
    """
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class.

    All database models should inherit from this class.
    Provides common functionality for all models.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Handle datetime serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary.

        Args:
            data: Dictionary with field values to update.
        """
        for key, value in data.items():
            if hasattr(self, key) and key in self.__table__.columns.keys():
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of model."""
        pk_columns = [c.name for c in self.__table__.primary_key.columns]
        pk_values = [getattr(self, name) for name in pk_columns]
        pk_str = ", ".join(f"{name}={value!r}" for name, value in zip(pk_columns, pk_values))
        return f"<{self.__class__.__name__}({pk_str})>"


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    Automatically sets created_at on insert and updated_at on update.

    Example:
        >>> class MyModel(Base, TimestampMixin):
        ...     __tablename__ = 'my_table'
        ...     id = Column(Integer, primary_key=True)
        >>> obj = MyModel()
        >>> # created_at and updated_at are set automatically
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when record was created."""
        return mapped_column(
            DateTime,
            default=func.now(),
            nullable=False,
            doc="Timestamp when record was created",
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when record was last updated."""
        return mapped_column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
            doc="Timestamp when record was last updated",
        )


class SoftDeleteMixin:
    """Mixin for soft delete functionality.

    Instead of permanently deleting records, marks them as deleted
    with a timestamp. Useful for audit trails and data recovery.

    Example:
        >>> class MyModel(Base, SoftDeleteMixin):
        ...     __tablename__ = 'my_table'
        ...     id = Column(Integer, primary_key=True)
        >>> obj = MyModel()
        >>> obj.soft_delete()  # Sets deleted_at timestamp
    """

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        """Timestamp when record was soft-deleted (None if active)."""
        return mapped_column(
            DateTime,
            nullable=True,
            default=None,
            doc="Timestamp when record was soft-deleted",
        )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
