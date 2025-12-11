"""Script model for GP OTA Tester.

This module defines the Script model for storing APDU scripts
in the database with full metadata and command details.

Example:
    >>> from cardlink.database.models import Script
    >>> script = Script(
    ...     id="select-isd",
    ...     name="Select ISD",
    ...     commands=[{"hex": "00A4040000", "name": "SELECT"}],
    ... )
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from cardlink.database.models.base import Base, TimestampMixin


class Script(Base, TimestampMixin):
    """APDU Script model for database storage.

    Stores APDU scripts with their commands, metadata, and categorization.
    Commands are stored as JSON to preserve the full structure.

    Attributes:
        id: Unique identifier (kebab-case, e.g., "select-isd").
        name: Human-readable name.
        description: Optional description of what the script does.
        commands: JSON array of APDU command objects.
        tags: JSON array of tags for categorization.

    Example:
        >>> script = Script(
        ...     id="select-isd",
        ...     name="Select ISD",
        ...     commands=[{"hex": "00A4040000"}],
        ...     tags=["gp", "security-domain"],
        ... )
    """

    __tablename__ = "scripts"

    # Primary key - script identifier
    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        doc="Unique script identifier (kebab-case)",
    )

    # Script metadata
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        doc="Human-readable script name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Script description",
    )

    # Commands stored as JSON array
    # Structure: [{"hex": "...", "name": "...", "description": "..."}, ...]
    commands: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="APDU commands as JSON array",
    )

    # Tags for categorization (JSON array)
    tags: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Tags for categorization",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_script_name", "name"),
        Index("idx_script_created", "created_at"),
        Index("idx_script_updated", "updated_at"),
    )

    def to_script_model(self) -> "cardlink.scripts.models.Script":
        """Convert to scripts.models.Script dataclass.

        Returns:
            Script dataclass instance.
        """
        from cardlink.scripts.models import APDUCommand, Script as ScriptModel

        commands = [APDUCommand.from_dict(cmd) for cmd in self.commands]
        return ScriptModel(
            id=self.id,
            name=self.name,
            commands=commands,
            description=self.description,
            tags=self.tags or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_script_model(cls, script: "cardlink.scripts.models.Script") -> "Script":
        """Create from scripts.models.Script dataclass.

        Args:
            script: Script dataclass instance.

        Returns:
            Database Script model instance.
        """
        return cls(
            id=script.id,
            name=script.name,
            description=script.description,
            commands=[cmd.to_dict() for cmd in script.commands],
            tags=script.tags or [],
            created_at=script.created_at or datetime.utcnow(),
            updated_at=script.updated_at or datetime.utcnow(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation including timestamps.
        """
        result = super().to_dict()
        return result
