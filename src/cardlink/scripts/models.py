"""Data models for configurable APDU scripts.

This module defines the core data structures for scripts and templates:
- APDUCommand: Single APDU command with optional name/description
- Script: Collection of APDUCommands with metadata
- ParameterDef: Parameter definition for templates
- Template: Script template with placeholder substitution

Example:
    >>> from cardlink.scripts.models import Script, APDUCommand
    >>> cmd = APDUCommand(hex="00A4040000", name="SELECT ISD")
    >>> script = Script(id="select-isd", name="Select ISD", commands=[cmd])
    >>> script.to_dict()
    {'id': 'select-isd', 'name': 'Select ISD', ...}
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ParameterType(Enum):
    """Supported parameter types for templates."""

    HEX = "hex"
    STRING = "string"


@dataclass
class APDUCommand:
    """Single APDU command with optional metadata.

    Attributes:
        hex: Raw APDU hex string (e.g., "00A4040000").
        name: Human-readable name for the command.
        description: Optional description of what the command does.
    """

    hex: str
    name: Optional[str] = None
    description: Optional[str] = None

    def to_bytes(self) -> bytes:
        """Convert hex string to bytes.

        Returns:
            APDU command as bytes.

        Raises:
            ValueError: If hex string is invalid.
        """
        return bytes.fromhex(self.hex)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/YAML.

        Returns:
            Dictionary representation of the command.
        """
        result = {"hex": self.hex}
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APDUCommand":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with 'hex' key and optional 'name', 'description'.

        Returns:
            APDUCommand instance.

        Raises:
            KeyError: If 'hex' key is missing.
            TypeError: If data is not a dict.
        """
        if isinstance(data, str):
            # Support shorthand: just hex string
            return cls(hex=data)
        return cls(
            hex=data["hex"],
            name=data.get("name"),
            description=data.get("description"),
        )


@dataclass
class Script:
    """Collection of APDU commands with metadata.

    Attributes:
        id: Unique identifier (kebab-case, e.g., "select-isd").
        name: Human-readable name.
        commands: List of APDU commands.
        description: Optional description.
        tags: List of tags for categorization.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    name: str
    commands: List[APDUCommand]
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Set timestamps if not provided."""
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/YAML.

        Returns:
            Dictionary representation of the script.
        """
        result = {
            "id": self.id,
            "name": self.name,
            "commands": [cmd.to_dict() for cmd in self.commands],
        }
        if self.description is not None:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        if self.created_at is not None:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at is not None:
            result["updated_at"] = self.updated_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Script":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with script data.

        Returns:
            Script instance.

        Raises:
            KeyError: If required keys are missing.
        """
        commands = [APDUCommand.from_dict(cmd) for cmd in data.get("commands", [])]

        created_at = None
        if "created_at" in data:
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if "updated_at" in data:
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            id=data["id"],
            name=data["name"],
            commands=commands,
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class ParameterDef:
    """Definition of a template parameter.

    Attributes:
        name: Parameter name (matches ${NAME} in commands).
        type: Parameter type (hex or string).
        description: Human-readable description.
        min_length: Minimum length for hex parameters (in bytes).
        max_length: Maximum length for hex parameters (in bytes).
        default: Default value if not provided.
        required: Whether the parameter is required.
    """

    name: str
    type: ParameterType = ParameterType.HEX
    description: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    default: Optional[str] = None
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/YAML.

        Returns:
            Dictionary representation of the parameter.
        """
        result = {
            "name": self.name,
            "type": self.type.value,
        }
        if self.description is not None:
            result["description"] = self.description
        if self.min_length is not None:
            result["min_length"] = self.min_length
        if self.max_length is not None:
            result["max_length"] = self.max_length
        if self.default is not None:
            result["default"] = self.default
        if not self.required:
            result["required"] = self.required
        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ParameterDef":
        """Deserialize from dictionary.

        Args:
            name: Parameter name.
            data: Dictionary with parameter definition.

        Returns:
            ParameterDef instance.
        """
        param_type = ParameterType(data.get("type", "hex"))
        return cls(
            name=name,
            type=param_type,
            description=data.get("description"),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            default=data.get("default"),
            required=data.get("required", True),
        )


@dataclass
class Template:
    """Script template with parameterized commands.

    Commands can contain ${PLACEHOLDER} patterns that are substituted
    with parameter values when rendered.

    Attributes:
        id: Unique identifier (kebab-case).
        name: Human-readable name.
        commands: List of APDU commands (may contain placeholders).
        parameters: Dictionary of parameter definitions.
        description: Optional description.
        tags: List of tags for categorization.
    """

    id: str
    name: str
    commands: List[APDUCommand]
    parameters: Dict[str, ParameterDef] = field(default_factory=dict)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/YAML.

        Returns:
            Dictionary representation of the template.
        """
        result = {
            "id": self.id,
            "name": self.name,
            "commands": [cmd.to_dict() for cmd in self.commands],
        }
        if self.parameters:
            result["parameters"] = {
                name: param.to_dict()
                for name, param in self.parameters.items()
            }
        if self.description is not None:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with template data.

        Returns:
            Template instance.
        """
        commands = [APDUCommand.from_dict(cmd) for cmd in data.get("commands", [])]

        parameters = {}
        for name, param_data in data.get("parameters", {}).items():
            parameters[name] = ParameterDef.from_dict(name, param_data)

        return cls(
            id=data["id"],
            name=data["name"],
            commands=commands,
            parameters=parameters,
            description=data.get("description"),
            tags=data.get("tags", []),
        )

    def get_placeholder_names(self) -> List[str]:
        """Extract all placeholder names from commands.

        Returns:
            List of unique placeholder names found in commands.
        """
        import re
        pattern = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}', re.IGNORECASE)
        placeholders = set()
        for cmd in self.commands:
            matches = pattern.findall(cmd.hex)
            placeholders.update(matches)
        return list(placeholders)


# Custom exceptions for the scripts module
class ScriptError(Exception):
    """Base exception for script-related errors."""
    pass


class ScriptNotFoundError(ScriptError):
    """Raised when a script is not found."""

    def __init__(self, script_id: str):
        self.script_id = script_id
        super().__init__(f"Script not found: {script_id}")


class TemplateNotFoundError(ScriptError):
    """Raised when a template is not found."""

    def __init__(self, template_id: str):
        self.template_id = template_id
        super().__init__(f"Template not found: {template_id}")


class ValidationError(ScriptError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message)


class RenderError(ScriptError):
    """Raised when template rendering fails."""
    pass
