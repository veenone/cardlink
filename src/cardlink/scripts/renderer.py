"""Template renderer for parameterized APDU scripts.

This module renders templates by substituting ${PLACEHOLDER} patterns
with provided parameter values, producing concrete APDU commands.

Example:
    >>> from cardlink.scripts.renderer import render_template
    >>> from cardlink.scripts.models import Template, APDUCommand, ParameterDef
    >>> template = Template(
    ...     id="select-aid",
    ...     name="Select AID",
    ...     commands=[APDUCommand(hex="00A40400${AID}00")],
    ...     parameters={"AID": ParameterDef(name="AID")}
    ... )
    >>> commands = render_template(template, {"AID": "A0000000030000"})
    >>> print(commands[0].hex)  # "00A40400A000000003000000"
"""

import re
from typing import Dict, List, Set, Tuple

from cardlink.scripts.models import (
    APDUCommand,
    ParameterDef,
    ParameterType,
    RenderError,
    Script,
    Template,
)
from cardlink.scripts.validator import validate_hex, validate_parameter_value

# Pattern to match ${PLACEHOLDER} syntax
PLACEHOLDER_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')


def extract_placeholders(hex_string: str) -> List[str]:
    """Extract all placeholder names from a hex string.

    Args:
        hex_string: String that may contain ${PLACEHOLDER} patterns.

    Returns:
        List of unique placeholder names found (in order of first appearance).
    """
    seen: Set[str] = set()
    result: List[str] = []

    for match in PLACEHOLDER_PATTERN.finditer(hex_string):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            result.append(name)

    return result


def extract_all_placeholders(template: Template) -> List[str]:
    """Extract all placeholder names from a template's commands.

    Args:
        template: Template to extract placeholders from.

    Returns:
        List of unique placeholder names across all commands.
    """
    seen: Set[str] = set()
    result: List[str] = []

    for cmd in template.commands:
        for name in extract_placeholders(cmd.hex):
            if name not in seen:
                seen.add(name)
                result.append(name)

    return result


def validate_params(
    template: Template,
    params: Dict[str, str]
) -> Tuple[bool, List[str]]:
    """Validate parameter values against template definitions.

    Args:
        template: Template with parameter definitions.
        params: Dictionary of parameter name -> value.

    Returns:
        Tuple of (is_valid, list_of_errors). Empty list if valid.
    """
    errors: List[str] = []

    # Get all placeholders used in template
    placeholders = extract_all_placeholders(template)

    # Check each placeholder has a value or default
    for name in placeholders:
        param_def = template.parameters.get(name)

        if param_def is None:
            # No parameter definition - this is a template validation issue
            errors.append(f"No parameter definition for '{name}'")
            continue

        value = params.get(name, "")

        # Use default if value not provided
        if not value and param_def.default is not None:
            continue  # Will use default

        # Validate the value
        valid, error = validate_parameter_value(value, param_def)
        if not valid:
            errors.append(f"Parameter '{name}': {error}")

    # Check for extra parameters (warning, not error)
    defined_names = set(template.parameters.keys())
    provided_names = set(params.keys())
    extra = provided_names - defined_names
    # Note: We don't add this to errors since extra params are just ignored

    return len(errors) == 0, errors


def render_command(
    command: APDUCommand,
    params: Dict[str, str],
    param_defs: Dict[str, ParameterDef]
) -> APDUCommand:
    """Render a single command by substituting placeholders.

    Args:
        command: Command with ${PLACEHOLDER} patterns.
        params: Dictionary of parameter name -> value.
        param_defs: Parameter definitions for type conversion.

    Returns:
        New APDUCommand with substituted hex string.

    Raises:
        RenderError: If a required placeholder has no value.
    """
    hex_string = command.hex

    def replace_placeholder(match: re.Match) -> str:
        name = match.group(1)
        value = params.get(name, "")

        # Try to get default if no value provided
        if not value:
            param_def = param_defs.get(name)
            if param_def and param_def.default is not None:
                value = param_def.default

        if not value:
            raise RenderError(f"No value for required parameter '{name}'")

        # Convert string type to hex if needed
        param_def = param_defs.get(name)
        if param_def and param_def.type == ParameterType.STRING:
            value = value.encode('utf-8').hex().upper()
        else:
            # Normalize hex to uppercase
            value = value.upper()

        return value

    rendered_hex = PLACEHOLDER_PATTERN.sub(replace_placeholder, hex_string)

    return APDUCommand(
        hex=rendered_hex,
        name=command.name,
        description=command.description
    )


def render_template(
    template: Template,
    params: Dict[str, str]
) -> List[APDUCommand]:
    """Render a template with parameter values.

    Args:
        template: Template to render.
        params: Dictionary of parameter name -> value.

    Returns:
        List of APDUCommand with all placeholders substituted.

    Raises:
        RenderError: If validation fails or required params missing.
    """
    # Validate parameters
    valid, errors = validate_params(template, params)
    if not valid:
        raise RenderError(f"Parameter validation failed: {'; '.join(errors)}")

    # Render each command
    rendered_commands: List[APDUCommand] = []

    for cmd in template.commands:
        try:
            rendered_cmd = render_command(cmd, params, template.parameters)
            rendered_commands.append(rendered_cmd)
        except RenderError:
            raise
        except Exception as e:
            raise RenderError(f"Failed to render command: {e}")

    # Validate final hex strings
    for i, cmd in enumerate(rendered_commands):
        valid, error = validate_hex(cmd.hex)
        if not valid:
            raise RenderError(f"Rendered command {i + 1} has invalid hex: {error}")

    return rendered_commands


def render_to_script(
    template: Template,
    params: Dict[str, str],
    script_id: str = None,
    script_name: str = None
) -> Script:
    """Render a template to a Script object.

    This is useful for creating a concrete Script from a Template.

    Args:
        template: Template to render.
        params: Dictionary of parameter name -> value.
        script_id: Optional ID for the resulting script.
                   Defaults to template.id + "-rendered".
        script_name: Optional name for the resulting script.
                     Defaults to template.name + " (Rendered)".

    Returns:
        Script with rendered commands.

    Raises:
        RenderError: If rendering fails.
    """
    rendered_commands = render_template(template, params)

    return Script(
        id=script_id or f"{template.id}-rendered",
        name=script_name or f"{template.name} (Rendered)",
        commands=rendered_commands,
        description=template.description,
        tags=template.tags + ["rendered"]
    )


def preview_render(
    template: Template,
    params: Dict[str, str]
) -> List[Dict[str, str]]:
    """Preview template rendering without full validation.

    This is useful for showing a preview in the UI as the user
    types parameter values.

    Args:
        template: Template to preview.
        params: Dictionary of parameter name -> value (may be incomplete).

    Returns:
        List of dicts with 'hex', 'name', 'valid' keys for each command.
    """
    results: List[Dict[str, str]] = []

    for cmd in template.commands:
        hex_string = cmd.hex

        # Substitute available values
        def replace_if_available(match: re.Match) -> str:
            name = match.group(1)
            value = params.get(name, "")

            if not value:
                param_def = template.parameters.get(name)
                if param_def and param_def.default is not None:
                    value = param_def.default

            if not value:
                return match.group(0)  # Keep placeholder

            # Convert string type to hex if needed
            param_def = template.parameters.get(name)
            if param_def and param_def.type == ParameterType.STRING:
                value = value.encode('utf-8').hex().upper()
            else:
                value = value.upper()

            return value

        preview_hex = PLACEHOLDER_PATTERN.sub(replace_if_available, hex_string)

        # Check if any placeholders remain
        has_placeholders = bool(PLACEHOLDER_PATTERN.search(preview_hex))

        # Validate rendered hex (if no placeholders)
        is_valid = not has_placeholders
        if is_valid:
            valid, _ = validate_hex(preview_hex)
            is_valid = valid

        results.append({
            'hex': preview_hex,
            'name': cmd.name or '',
            'valid': is_valid,
            'complete': not has_placeholders
        })

    return results


def get_missing_params(
    template: Template,
    params: Dict[str, str]
) -> List[str]:
    """Get list of required parameters that are missing values.

    Args:
        template: Template to check.
        params: Dictionary of provided parameter values.

    Returns:
        List of parameter names that are required but not provided.
    """
    missing: List[str] = []

    for name in extract_all_placeholders(template):
        param_def = template.parameters.get(name)
        if param_def is None:
            continue

        value = params.get(name, "")
        if not value and param_def.default is None and param_def.required:
            missing.append(name)

    return missing
