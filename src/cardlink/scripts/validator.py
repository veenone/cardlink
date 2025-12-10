"""Validation utilities for APDU scripts.

This module provides validation functions for script IDs, hex strings,
scripts, and templates. All validators return tuple (is_valid, error_message).

Security considerations:
- Script IDs are validated to prevent path traversal
- Hex strings are strictly validated for APDU safety
- Length limits are enforced to prevent DoS

Example:
    >>> from cardlink.scripts.validator import validate_script_id, validate_hex
    >>> valid, error = validate_script_id("select-isd")
    >>> print(valid)  # True
    >>> valid, error = validate_script_id("../etc/passwd")
    >>> print(valid, error)  # False, "Invalid characters..."
"""

import re
from typing import List, Optional, Tuple

from cardlink.scripts.models import (
    APDUCommand,
    ParameterDef,
    ParameterType,
    Script,
    Template,
    ValidationError,
)

# Pattern for valid script/template IDs (kebab-case)
# Allows: lowercase letters, numbers, hyphens
# Must start with letter, no consecutive hyphens, no trailing hyphen
SCRIPT_ID_PATTERN = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')

# Maximum lengths
MAX_SCRIPT_ID_LENGTH = 64
MAX_SCRIPT_NAME_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMMANDS_PER_SCRIPT = 100
MAX_HEX_LENGTH = 520  # Max extended APDU: 5 + 3 + 255 + 2 = 265 bytes = 530 chars

# Pattern for valid hex string (even length, hex chars only)
HEX_PATTERN = re.compile(r'^[0-9A-Fa-f]*$')


def validate_script_id(script_id: str) -> Tuple[bool, Optional[str]]:
    """Validate a script/template ID.

    IDs must be kebab-case, start with a letter, and contain only
    lowercase letters, numbers, and hyphens.

    Args:
        script_id: The ID to validate.

    Returns:
        Tuple of (is_valid, error_message). Error is None if valid.
    """
    if not script_id:
        return False, "Script ID cannot be empty"

    if len(script_id) > MAX_SCRIPT_ID_LENGTH:
        return False, f"Script ID exceeds maximum length of {MAX_SCRIPT_ID_LENGTH}"

    # Security: Check for path traversal attempts
    if '..' in script_id or '/' in script_id or '\\' in script_id:
        return False, "Script ID contains invalid path characters"

    if not SCRIPT_ID_PATTERN.match(script_id):
        return False, (
            "Script ID must be kebab-case (lowercase letters, numbers, hyphens), "
            "start with a letter, and not end with a hyphen"
        )

    return True, None


def sanitize_script_id(name: str) -> str:
    """Convert a name to a valid script ID.

    Converts to lowercase, replaces spaces/underscores with hyphens,
    removes invalid characters, and ensures valid format.

    Args:
        name: The name to convert.

    Returns:
        A valid script ID derived from the name.
    """
    # Convert to lowercase
    result = name.lower().strip()

    # Replace spaces and underscores with hyphens
    result = re.sub(r'[\s_]+', '-', result)

    # Remove invalid characters
    result = re.sub(r'[^a-z0-9-]', '', result)

    # Collapse consecutive hyphens
    result = re.sub(r'-+', '-', result)

    # Remove leading/trailing hyphens
    result = result.strip('-')

    # Ensure starts with letter
    if result and not result[0].isalpha():
        result = 'script-' + result

    # Truncate if too long
    if len(result) > MAX_SCRIPT_ID_LENGTH:
        result = result[:MAX_SCRIPT_ID_LENGTH].rstrip('-')

    # Fallback for empty result
    if not result:
        result = 'script'

    return result


def validate_hex(hex_string: str, allow_placeholders: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate a hex string for APDU commands.

    Args:
        hex_string: The hex string to validate.
        allow_placeholders: If True, ${PLACEHOLDER} patterns are allowed.

    Returns:
        Tuple of (is_valid, error_message). Error is None if valid.
    """
    if not hex_string:
        return False, "Hex string cannot be empty"

    if len(hex_string) > MAX_HEX_LENGTH:
        return False, f"Hex string exceeds maximum length of {MAX_HEX_LENGTH}"

    # If placeholders allowed, remove them before validation
    check_string = hex_string
    if allow_placeholders:
        check_string = re.sub(r'\$\{[A-Za-z_][A-Za-z0-9_]*\}', '', hex_string)

    # Must be even length (each byte is 2 hex chars)
    if len(check_string) % 2 != 0:
        return False, "Hex string must have even length (2 characters per byte)"

    # Must contain only hex characters
    if not HEX_PATTERN.match(check_string):
        return False, "Hex string contains invalid characters (only 0-9, A-F allowed)"

    return True, None


def validate_apdu_command(command: APDUCommand, allow_placeholders: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate an APDU command.

    Args:
        command: The command to validate.
        allow_placeholders: If True, ${PLACEHOLDER} patterns are allowed in hex.

    Returns:
        Tuple of (is_valid, error_message). Error is None if valid.
    """
    # Validate hex
    valid, error = validate_hex(command.hex, allow_placeholders)
    if not valid:
        return False, f"Invalid hex: {error}"

    # Validate minimum APDU length (CLA, INS, P1, P2 = 4 bytes minimum)
    # Only check if no placeholders
    if not allow_placeholders:
        try:
            apdu_bytes = bytes.fromhex(command.hex)
            if len(apdu_bytes) < 4:
                return False, "APDU must be at least 4 bytes (CLA, INS, P1, P2)"
        except ValueError as e:
            return False, f"Invalid hex format: {e}"

    # Validate optional name length
    if command.name and len(command.name) > MAX_SCRIPT_NAME_LENGTH:
        return False, f"Command name exceeds maximum length of {MAX_SCRIPT_NAME_LENGTH}"

    # Validate optional description length
    if command.description and len(command.description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Command description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}"

    return True, None


def validate_script(script: Script) -> Tuple[bool, List[str]]:
    """Validate a complete script.

    Args:
        script: The script to validate.

    Returns:
        Tuple of (is_valid, list_of_errors). Empty list if valid.
    """
    errors = []

    # Validate ID
    valid, error = validate_script_id(script.id)
    if not valid:
        errors.append(f"ID: {error}")

    # Validate name
    if not script.name:
        errors.append("Name cannot be empty")
    elif len(script.name) > MAX_SCRIPT_NAME_LENGTH:
        errors.append(f"Name exceeds maximum length of {MAX_SCRIPT_NAME_LENGTH}")

    # Validate description
    if script.description and len(script.description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}")

    # Validate commands
    if not script.commands:
        errors.append("Script must have at least one command")
    elif len(script.commands) > MAX_COMMANDS_PER_SCRIPT:
        errors.append(f"Script exceeds maximum of {MAX_COMMANDS_PER_SCRIPT} commands")
    else:
        for i, cmd in enumerate(script.commands):
            valid, error = validate_apdu_command(cmd, allow_placeholders=False)
            if not valid:
                errors.append(f"Command {i + 1}: {error}")

    # Validate tags
    for tag in script.tags:
        if len(tag) > 32:
            errors.append(f"Tag '{tag[:20]}...' exceeds maximum length of 32")

    return len(errors) == 0, errors


def validate_template(template: Template) -> Tuple[bool, List[str]]:
    """Validate a complete template.

    Args:
        template: The template to validate.

    Returns:
        Tuple of (is_valid, list_of_errors). Empty list if valid.
    """
    errors = []

    # Validate ID
    valid, error = validate_script_id(template.id)
    if not valid:
        errors.append(f"ID: {error}")

    # Validate name
    if not template.name:
        errors.append("Name cannot be empty")
    elif len(template.name) > MAX_SCRIPT_NAME_LENGTH:
        errors.append(f"Name exceeds maximum length of {MAX_SCRIPT_NAME_LENGTH}")

    # Validate description
    if template.description and len(template.description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}")

    # Validate commands (allow placeholders in templates)
    if not template.commands:
        errors.append("Template must have at least one command")
    elif len(template.commands) > MAX_COMMANDS_PER_SCRIPT:
        errors.append(f"Template exceeds maximum of {MAX_COMMANDS_PER_SCRIPT} commands")
    else:
        for i, cmd in enumerate(template.commands):
            valid, error = validate_apdu_command(cmd, allow_placeholders=True)
            if not valid:
                errors.append(f"Command {i + 1}: {error}")

    # Validate parameters
    for name, param in template.parameters.items():
        valid, error = validate_parameter_def(param)
        if not valid:
            errors.append(f"Parameter '{name}': {error}")

    # Check that all placeholders have definitions
    placeholders = template.get_placeholder_names()
    for placeholder in placeholders:
        if placeholder not in template.parameters:
            errors.append(f"Placeholder ${{{placeholder}}} has no parameter definition")

    # Check for unused parameter definitions
    for name in template.parameters:
        if name not in placeholders:
            errors.append(f"Parameter '{name}' is defined but not used in commands")

    return len(errors) == 0, errors


def validate_parameter_def(param: ParameterDef) -> Tuple[bool, Optional[str]]:
    """Validate a parameter definition.

    Args:
        param: The parameter definition to validate.

    Returns:
        Tuple of (is_valid, error_message). Error is None if valid.
    """
    # Validate name format (uppercase with underscores)
    if not re.match(r'^[A-Z][A-Z0-9_]*$', param.name):
        return False, "Parameter name must be uppercase letters, numbers, underscores"

    # Validate length constraints
    if param.min_length is not None and param.min_length < 0:
        return False, "min_length cannot be negative"

    if param.max_length is not None and param.max_length < 0:
        return False, "max_length cannot be negative"

    if (param.min_length is not None and param.max_length is not None
            and param.min_length > param.max_length):
        return False, "min_length cannot be greater than max_length"

    # Validate default value if present
    if param.default is not None:
        if param.type == ParameterType.HEX:
            valid, error = validate_hex(param.default)
            if not valid:
                return False, f"Invalid default value: {error}"

            # Check length constraints on default
            default_len = len(param.default) // 2  # bytes
            if param.min_length is not None and default_len < param.min_length:
                return False, f"Default value is shorter than min_length ({param.min_length})"
            if param.max_length is not None and default_len > param.max_length:
                return False, f"Default value is longer than max_length ({param.max_length})"

    return True, None


def validate_parameter_value(
    value: str,
    param_def: ParameterDef
) -> Tuple[bool, Optional[str]]:
    """Validate a parameter value against its definition.

    Args:
        value: The value to validate.
        param_def: The parameter definition.

    Returns:
        Tuple of (is_valid, error_message). Error is None if valid.
    """
    if not value:
        if param_def.required and param_def.default is None:
            return False, "Parameter is required"
        return True, None  # Will use default

    if param_def.type == ParameterType.HEX:
        valid, error = validate_hex(value)
        if not valid:
            return False, error

        # Check length constraints
        value_len = len(value) // 2  # bytes
        if param_def.min_length is not None and value_len < param_def.min_length:
            return False, f"Value is shorter than minimum ({param_def.min_length} bytes)"
        if param_def.max_length is not None and value_len > param_def.max_length:
            return False, f"Value is longer than maximum ({param_def.max_length} bytes)"

    elif param_def.type == ParameterType.STRING:
        # Convert string to hex and validate
        try:
            hex_value = value.encode('utf-8').hex()
            value_len = len(hex_value) // 2
            if param_def.min_length is not None and value_len < param_def.min_length:
                return False, f"Value is shorter than minimum ({param_def.min_length} bytes)"
            if param_def.max_length is not None and value_len > param_def.max_length:
                return False, f"Value is longer than maximum ({param_def.max_length} bytes)"
        except UnicodeEncodeError:
            return False, "String contains invalid characters"

    return True, None


def raise_validation_errors(errors: List[str], entity: str = "Script"):
    """Raise ValidationError if there are errors.

    Args:
        errors: List of error messages.
        entity: Name of the entity being validated (for error message).

    Raises:
        ValidationError: If errors list is not empty.
    """
    if errors:
        raise ValidationError(f"{entity} validation failed: {'; '.join(errors)}")
