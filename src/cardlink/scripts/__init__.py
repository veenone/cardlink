"""Configurable APDU scripts module.

This module provides configurable APDU script management for the GP-OTA
test platform, allowing users to define, load, and execute APDU command
scripts from YAML configuration files.

Main Components:
    - APDUCommand: Single APDU command with metadata
    - Script: Collection of APDU commands
    - Template: Parameterized script with placeholder substitution
    - ScriptManager: Central service for script management

Example:
    >>> from cardlink.scripts import ScriptManager, Script, APDUCommand
    >>> manager = ScriptManager()
    >>> manager.load_directory("scripts/")
    >>> script = manager.get_script("select-isd")
    >>> commands = [cmd.to_bytes() for cmd in script.commands]
"""

from cardlink.scripts.models import (
    APDUCommand,
    ParameterDef,
    ParameterType,
    RenderError,
    Script,
    ScriptError,
    ScriptNotFoundError,
    Template,
    TemplateNotFoundError,
    ValidationError,
)
from cardlink.scripts.validator import (
    sanitize_script_id,
    validate_apdu_command,
    validate_hex,
    validate_parameter_def,
    validate_parameter_value,
    validate_script,
    validate_script_id,
    validate_template,
)
from cardlink.scripts.loader import (
    load_file,
    load_directory,
    load_scripts_from_data,
    save_file,
    LoadError,
)
from cardlink.scripts.renderer import (
    render_template,
    render_to_script,
    render_command,
    preview_render,
    extract_placeholders,
    extract_all_placeholders,
    get_missing_params,
    validate_params,
)
from cardlink.scripts.manager import ScriptManager

__all__ = [
    # Models
    "APDUCommand",
    "Script",
    "Template",
    "ParameterDef",
    "ParameterType",
    # Manager
    "ScriptManager",
    # Exceptions
    "ScriptError",
    "ScriptNotFoundError",
    "TemplateNotFoundError",
    "ValidationError",
    "RenderError",
    "LoadError",
    # Validators
    "validate_script_id",
    "validate_hex",
    "validate_apdu_command",
    "validate_script",
    "validate_template",
    "validate_parameter_def",
    "validate_parameter_value",
    "sanitize_script_id",
    # Loader
    "load_file",
    "load_directory",
    "load_scripts_from_data",
    "save_file",
    # Renderer
    "render_template",
    "render_to_script",
    "render_command",
    "preview_render",
    "extract_placeholders",
    "extract_all_placeholders",
    "get_missing_params",
    "validate_params",
]
