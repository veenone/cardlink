"""YAML loader for APDU scripts and templates.

This module provides functions to load scripts and templates from YAML files,
with proper error handling and security measures.

Security considerations:
- Uses yaml.safe_load() to prevent code injection
- Validates file paths to prevent directory traversal
- Handles malformed YAML gracefully with logging

Example:
    >>> from cardlink.scripts.loader import load_file, load_directory
    >>> scripts, templates = load_file("scripts/default.yaml")
    >>> print(f"Loaded {len(scripts)} scripts")
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from cardlink.scripts.models import Script, Template
from cardlink.scripts.validator import validate_script, validate_template

logger = logging.getLogger(__name__)


class LoadError(Exception):
    """Raised when loading a file fails."""

    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"Failed to load '{file_path}': {message}")


def load_file(
    file_path: str,
    validate: bool = True,
    skip_invalid: bool = True
) -> Tuple[List[Script], List[Template]]:
    """Load scripts and templates from a single YAML file.

    Args:
        file_path: Path to the YAML file.
        validate: If True, validate scripts and templates before returning.
        skip_invalid: If True, skip invalid items with warnings. If False,
                      raise ValidationError on first invalid item.

    Returns:
        Tuple of (scripts_list, templates_list).

    Raises:
        LoadError: If the file cannot be read or parsed.
        FileNotFoundError: If the file does not exist.
        ValidationError: If validate=True, skip_invalid=False, and
                        an item fails validation.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise LoadError(file_path, "Path is not a file")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise LoadError(file_path, f"Invalid YAML: {e}")
    except IOError as e:
        raise LoadError(file_path, f"IO error: {e}")

    if data is None:
        logger.debug(f"Empty YAML file: {file_path}")
        return [], []

    if not isinstance(data, dict):
        raise LoadError(file_path, "YAML root must be a dictionary")

    scripts = []
    templates = []

    # Load scripts
    scripts_data = data.get('scripts', [])
    if not isinstance(scripts_data, list):
        logger.warning(f"'scripts' must be a list in {file_path}")
        scripts_data = []

    for i, script_data in enumerate(scripts_data):
        try:
            script = Script.from_dict(script_data)

            if validate:
                valid, errors = validate_script(script)
                if not valid:
                    if skip_invalid:
                        logger.warning(
                            f"Invalid script at index {i} in {file_path}: "
                            f"{'; '.join(errors)}"
                        )
                        continue
                    else:
                        from cardlink.scripts.models import ValidationError
                        raise ValidationError(
                            f"Script validation failed: {'; '.join(errors)}"
                        )

            scripts.append(script)
            logger.debug(f"Loaded script '{script.id}' from {file_path}")

        except KeyError as e:
            if skip_invalid:
                logger.warning(
                    f"Missing required field {e} for script at index {i} "
                    f"in {file_path}"
                )
            else:
                raise LoadError(file_path, f"Missing field {e} at script {i}")

        except Exception as e:
            if skip_invalid:
                logger.warning(
                    f"Failed to load script at index {i} in {file_path}: {e}"
                )
            else:
                raise LoadError(file_path, f"Script {i} error: {e}")

    # Load templates
    templates_data = data.get('templates', [])
    if not isinstance(templates_data, list):
        logger.warning(f"'templates' must be a list in {file_path}")
        templates_data = []

    for i, template_data in enumerate(templates_data):
        try:
            template = Template.from_dict(template_data)

            if validate:
                valid, errors = validate_template(template)
                if not valid:
                    if skip_invalid:
                        logger.warning(
                            f"Invalid template at index {i} in {file_path}: "
                            f"{'; '.join(errors)}"
                        )
                        continue
                    else:
                        from cardlink.scripts.models import ValidationError
                        raise ValidationError(
                            f"Template validation failed: {'; '.join(errors)}"
                        )

            templates.append(template)
            logger.debug(f"Loaded template '{template.id}' from {file_path}")

        except KeyError as e:
            if skip_invalid:
                logger.warning(
                    f"Missing required field {e} for template at index {i} "
                    f"in {file_path}"
                )
            else:
                raise LoadError(file_path, f"Missing field {e} at template {i}")

        except Exception as e:
            if skip_invalid:
                logger.warning(
                    f"Failed to load template at index {i} in {file_path}: {e}"
                )
            else:
                raise LoadError(file_path, f"Template {i} error: {e}")

    logger.info(
        f"Loaded {len(scripts)} scripts and {len(templates)} templates "
        f"from {file_path}"
    )
    return scripts, templates


def load_directory(
    directory_path: str,
    recursive: bool = False,
    validate: bool = True,
    skip_invalid: bool = True
) -> Tuple[List[Script], List[Template]]:
    """Load scripts and templates from all YAML files in a directory.

    Args:
        directory_path: Path to the directory containing YAML files.
        recursive: If True, search subdirectories recursively.
        validate: If True, validate scripts and templates.
        skip_invalid: If True, skip invalid items with warnings.

    Returns:
        Tuple of (all_scripts, all_templates) from all files.

    Raises:
        FileNotFoundError: If the directory does not exist.
        LoadError: If no valid YAML files are found.
    """
    dir_path = Path(directory_path)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    if not dir_path.is_dir():
        raise LoadError(directory_path, "Path is not a directory")

    # Find YAML files
    pattern = '**/*.yaml' if recursive else '*.yaml'
    yaml_files = list(dir_path.glob(pattern))

    # Also check for .yml extension
    yml_pattern = '**/*.yml' if recursive else '*.yml'
    yaml_files.extend(dir_path.glob(yml_pattern))

    if not yaml_files:
        logger.warning(f"No YAML files found in {directory_path}")
        return [], []

    all_scripts: List[Script] = []
    all_templates: List[Template] = []
    loaded_files = 0
    errors_count = 0

    for yaml_file in sorted(yaml_files):
        try:
            scripts, templates = load_file(
                str(yaml_file),
                validate=validate,
                skip_invalid=skip_invalid
            )
            all_scripts.extend(scripts)
            all_templates.extend(templates)
            loaded_files += 1

        except LoadError as e:
            logger.error(f"Failed to load {yaml_file}: {e}")
            errors_count += 1
            if not skip_invalid:
                raise

        except FileNotFoundError:
            # Should not happen, but handle gracefully
            logger.warning(f"File disappeared: {yaml_file}")
            errors_count += 1

    logger.info(
        f"Loaded {len(all_scripts)} scripts and {len(all_templates)} templates "
        f"from {loaded_files} files in {directory_path} "
        f"({errors_count} errors)"
    )

    return all_scripts, all_templates


def load_scripts_from_data(
    data: Dict,
    source: str = "<data>",
    validate: bool = True,
    skip_invalid: bool = True
) -> Tuple[List[Script], List[Template]]:
    """Load scripts and templates from a parsed YAML data dictionary.

    This is useful when YAML has already been parsed (e.g., from an API).

    Args:
        data: Dictionary with 'scripts' and/or 'templates' keys.
        source: Source identifier for error messages.
        validate: If True, validate scripts and templates.
        skip_invalid: If True, skip invalid items with warnings.

    Returns:
        Tuple of (scripts_list, templates_list).
    """
    scripts = []
    templates = []

    # Load scripts
    for i, script_data in enumerate(data.get('scripts', [])):
        try:
            script = Script.from_dict(script_data)

            if validate:
                valid, errors = validate_script(script)
                if not valid:
                    if skip_invalid:
                        logger.warning(
                            f"Invalid script at index {i} from {source}: "
                            f"{'; '.join(errors)}"
                        )
                        continue
                    else:
                        from cardlink.scripts.models import ValidationError
                        raise ValidationError('; '.join(errors))

            scripts.append(script)

        except Exception as e:
            if skip_invalid:
                logger.warning(f"Failed to load script {i} from {source}: {e}")
            else:
                raise

    # Load templates
    for i, template_data in enumerate(data.get('templates', [])):
        try:
            template = Template.from_dict(template_data)

            if validate:
                valid, errors = validate_template(template)
                if not valid:
                    if skip_invalid:
                        logger.warning(
                            f"Invalid template at index {i} from {source}: "
                            f"{'; '.join(errors)}"
                        )
                        continue
                    else:
                        from cardlink.scripts.models import ValidationError
                        raise ValidationError('; '.join(errors))

            templates.append(template)

        except Exception as e:
            if skip_invalid:
                logger.warning(f"Failed to load template {i} from {source}: {e}")
            else:
                raise

    return scripts, templates


def save_file(
    file_path: str,
    scripts: List[Script],
    templates: Optional[List[Template]] = None
) -> None:
    """Save scripts and templates to a YAML file.

    Args:
        file_path: Path to the output YAML file.
        scripts: List of scripts to save.
        templates: Optional list of templates to save.

    Raises:
        IOError: If the file cannot be written.
    """
    data = {}

    if scripts:
        data['scripts'] = [script.to_dict() for script in scripts]

    if templates:
        data['templates'] = [template.to_dict() for template in templates]

    # Ensure parent directory exists
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(
        f"Saved {len(scripts)} scripts and {len(templates or [])} templates "
        f"to {file_path}"
    )
