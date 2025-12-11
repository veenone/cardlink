"""Template model for GP OTA Tester.

This module defines the Template model for storing parameterized APDU
script templates in the database.

Example:
    >>> from cardlink.database.models import Template
    >>> template = Template(
    ...     id="install-applet",
    ...     name="Install Applet",
    ...     commands=[{"hex": "80E60200${AID_LENGTH}${AID}00"}],
    ...     parameters={"AID": {"type": "hex", "min_length": 5}},
    ... )
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from cardlink.database.models.base import Base, TimestampMixin


class Template(Base, TimestampMixin):
    """APDU Script Template model for database storage.

    Stores parameterized script templates with placeholder commands
    and parameter definitions. Commands can contain ${PLACEHOLDER}
    patterns that are substituted when rendered.

    Attributes:
        id: Unique identifier (kebab-case, e.g., "install-applet").
        name: Human-readable name.
        description: Optional description.
        commands: JSON array of APDU command objects (with placeholders).
        parameters: JSON object of parameter definitions.
        tags: JSON array of tags for categorization.

    Example:
        >>> template = Template(
        ...     id="install-applet",
        ...     name="Install Applet",
        ...     commands=[{"hex": "80E60200${LEN}${AID}00"}],
        ...     parameters={
        ...         "AID": {"type": "hex", "min_length": 5, "max_length": 16},
        ...         "LEN": {"type": "hex", "description": "AID length"},
        ...     },
        ... )
    """

    __tablename__ = "templates"

    # Primary key - template identifier
    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        doc="Unique template identifier (kebab-case)",
    )

    # Template metadata
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        doc="Human-readable template name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Template description",
    )

    # Commands stored as JSON array (may contain ${PLACEHOLDER} patterns)
    # Structure: [{"hex": "...", "name": "...", "description": "..."}, ...]
    commands: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="APDU commands as JSON array (with placeholders)",
    )

    # Parameter definitions stored as JSON object
    # Structure: {"PARAM_NAME": {"type": "hex", "min_length": 5, ...}, ...}
    parameters: Mapped[Dict[str, Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Parameter definitions as JSON object",
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
        Index("idx_template_name", "name"),
        Index("idx_template_created", "created_at"),
        Index("idx_template_updated", "updated_at"),
    )

    def to_template_model(self) -> "cardlink.scripts.models.Template":
        """Convert to scripts.models.Template dataclass.

        Returns:
            Template dataclass instance.
        """
        from cardlink.scripts.models import (
            APDUCommand,
            ParameterDef,
            Template as TemplateModel,
        )

        commands = [APDUCommand.from_dict(cmd) for cmd in self.commands]
        parameters = {}
        for name, param_data in (self.parameters or {}).items():
            parameters[name] = ParameterDef.from_dict(name, param_data)

        return TemplateModel(
            id=self.id,
            name=self.name,
            commands=commands,
            parameters=parameters,
            description=self.description,
            tags=self.tags or [],
        )

    @classmethod
    def from_template_model(
        cls, template: "cardlink.scripts.models.Template"
    ) -> "Template":
        """Create from scripts.models.Template dataclass.

        Args:
            template: Template dataclass instance.

        Returns:
            Database Template model instance.
        """
        # Convert parameters to dict format for JSON storage
        parameters = {}
        for name, param in template.parameters.items():
            param_dict = param.to_dict()
            # Remove name since it's the key
            param_dict.pop("name", None)
            parameters[name] = param_dict

        return cls(
            id=template.id,
            name=template.name,
            description=template.description,
            commands=[cmd.to_dict() for cmd in template.commands],
            parameters=parameters,
            tags=template.tags or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation including timestamps.
        """
        result = super().to_dict()
        return result
