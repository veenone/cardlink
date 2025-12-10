"""Script Manager service for APDU script storage and retrieval.

This module provides in-memory management of scripts and templates with
CRUD operations and persistence to YAML files.

Example:
    >>> from cardlink.scripts.manager import ScriptManager
    >>> manager = ScriptManager()
    >>> manager.load_from_directory("scripts/")
    >>> script = manager.get_script("select-isd")
    >>> print(script.name)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cardlink.scripts.loader import load_directory, load_file, save_file
from cardlink.scripts.models import (
    APDUCommand,
    Script,
    ScriptNotFoundError,
    Template,
    TemplateNotFoundError,
    ValidationError,
)
from cardlink.scripts.renderer import render_template, render_to_script
from cardlink.scripts.validator import validate_script, validate_template

logger = logging.getLogger(__name__)


class ScriptManager:
    """Manages in-memory storage of scripts and templates.

    Provides CRUD operations and persistence to YAML files.

    Attributes:
        scripts: Dictionary mapping script ID to Script object.
        templates: Dictionary mapping template ID to Template object.
    """

    def __init__(self):
        """Initialize empty script manager."""
        self._scripts: Dict[str, Script] = {}
        self._templates: Dict[str, Template] = {}
        self._scripts_dir: Optional[Path] = None

    @property
    def scripts(self) -> Dict[str, Script]:
        """Get all scripts as a dictionary."""
        return dict(self._scripts)

    @property
    def templates(self) -> Dict[str, Template]:
        """Get all templates as a dictionary."""
        return dict(self._templates)

    # =========================================================================
    # Loading
    # =========================================================================

    def load_from_file(
        self,
        file_path: str,
        validate: bool = True,
        skip_invalid: bool = True
    ) -> Tuple[int, int]:
        """Load scripts and templates from a YAML file.

        Args:
            file_path: Path to YAML file.
            validate: If True, validate items before adding.
            skip_invalid: If True, skip invalid items instead of raising.

        Returns:
            Tuple of (scripts_loaded, templates_loaded) counts.
        """
        scripts, templates = load_file(file_path, validate, skip_invalid)

        scripts_added = 0
        templates_added = 0

        for script in scripts:
            if script.id not in self._scripts:
                self._scripts[script.id] = script
                scripts_added += 1
            else:
                logger.warning(f"Duplicate script ID '{script.id}', skipping")

        for template in templates:
            if template.id not in self._templates:
                self._templates[template.id] = template
                templates_added += 1
            else:
                logger.warning(f"Duplicate template ID '{template.id}', skipping")

        logger.info(
            f"Loaded {scripts_added} scripts and {templates_added} templates "
            f"from {file_path}"
        )
        return scripts_added, templates_added

    def load_from_directory(
        self,
        directory_path: str,
        recursive: bool = False,
        validate: bool = True,
        skip_invalid: bool = True
    ) -> Tuple[int, int]:
        """Load scripts and templates from all YAML files in a directory.

        Args:
            directory_path: Path to directory containing YAML files.
            recursive: If True, search subdirectories.
            validate: If True, validate items before adding.
            skip_invalid: If True, skip invalid items.

        Returns:
            Tuple of (scripts_loaded, templates_loaded) counts.
        """
        self._scripts_dir = Path(directory_path)

        scripts, templates = load_directory(
            directory_path, recursive, validate, skip_invalid
        )

        scripts_added = 0
        templates_added = 0

        for script in scripts:
            if script.id not in self._scripts:
                self._scripts[script.id] = script
                scripts_added += 1
            else:
                logger.warning(f"Duplicate script ID '{script.id}', skipping")

        for template in templates:
            if template.id not in self._templates:
                self._templates[template.id] = template
                templates_added += 1
            else:
                logger.warning(f"Duplicate template ID '{template.id}', skipping")

        logger.info(
            f"Loaded {scripts_added} scripts and {templates_added} templates "
            f"from directory {directory_path}"
        )
        return scripts_added, templates_added

    # =========================================================================
    # Script CRUD Operations
    # =========================================================================

    def get_script(self, script_id: str) -> Script:
        """Get a script by ID.

        Args:
            script_id: The script identifier.

        Returns:
            The Script object.

        Raises:
            ScriptNotFoundError: If script does not exist.
        """
        if script_id not in self._scripts:
            raise ScriptNotFoundError(f"Script '{script_id}' not found")
        return self._scripts[script_id]

    def list_scripts(
        self,
        tag: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Script]:
        """List all scripts, optionally filtered.

        Args:
            tag: Filter by tag (case-insensitive).
            search: Search in name and description (case-insensitive).

        Returns:
            List of matching Script objects.
        """
        result = list(self._scripts.values())

        if tag:
            tag_lower = tag.lower()
            result = [
                s for s in result
                if any(t.lower() == tag_lower for t in s.tags)
            ]

        if search:
            search_lower = search.lower()
            result = [
                s for s in result
                if search_lower in s.name.lower()
                or (s.description and search_lower in s.description.lower())
            ]

        return result

    def create_script(
        self,
        script_id: str,
        name: str,
        commands: List[APDUCommand],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True
    ) -> Script:
        """Create a new script.

        Args:
            script_id: Unique identifier for the script.
            name: Human-readable name.
            commands: List of APDU commands.
            description: Optional description.
            tags: Optional list of tags.
            validate_flag: If True, validate before creating.

        Returns:
            The created Script object.

        Raises:
            ValidationError: If validation fails.
            ValueError: If script ID already exists.
        """
        if script_id in self._scripts:
            raise ValueError(f"Script '{script_id}' already exists")

        now = datetime.now()
        script = Script(
            id=script_id,
            name=name,
            commands=commands,
            description=description,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )

        if validate_flag:
            valid, errors = validate_script(script)
            if not valid:
                raise ValidationError(f"Script validation failed: {'; '.join(errors)}")

        self._scripts[script_id] = script
        logger.info(f"Created script '{script_id}'")
        return script

    def update_script(
        self,
        script_id: str,
        name: Optional[str] = None,
        commands: Optional[List[APDUCommand]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True
    ) -> Script:
        """Update an existing script.

        Args:
            script_id: ID of script to update.
            name: New name (if provided).
            commands: New commands (if provided).
            description: New description (if provided).
            tags: New tags (if provided).
            validate_flag: If True, validate after updating.

        Returns:
            The updated Script object.

        Raises:
            ScriptNotFoundError: If script does not exist.
            ValidationError: If validation fails.
        """
        if script_id not in self._scripts:
            raise ScriptNotFoundError(f"Script '{script_id}' not found")

        existing = self._scripts[script_id]

        updated = Script(
            id=script_id,
            name=name if name is not None else existing.name,
            commands=commands if commands is not None else existing.commands,
            description=description if description is not None else existing.description,
            tags=tags if tags is not None else existing.tags,
            created_at=existing.created_at,
            updated_at=datetime.now()
        )

        if validate_flag:
            valid, errors = validate_script(updated)
            if not valid:
                raise ValidationError(f"Script validation failed: {'; '.join(errors)}")

        self._scripts[script_id] = updated
        logger.info(f"Updated script '{script_id}'")
        return updated

    def delete_script(self, script_id: str) -> bool:
        """Delete a script.

        Args:
            script_id: ID of script to delete.

        Returns:
            True if deleted.

        Raises:
            ScriptNotFoundError: If script does not exist.
        """
        if script_id not in self._scripts:
            raise ScriptNotFoundError(f"Script '{script_id}' not found")

        del self._scripts[script_id]
        logger.info(f"Deleted script '{script_id}'")
        return True

    def script_exists(self, script_id: str) -> bool:
        """Check if a script exists.

        Args:
            script_id: The script identifier.

        Returns:
            True if script exists.
        """
        return script_id in self._scripts

    # =========================================================================
    # Template CRUD Operations
    # =========================================================================

    def get_template(self, template_id: str) -> Template:
        """Get a template by ID.

        Args:
            template_id: The template identifier.

        Returns:
            The Template object.

        Raises:
            TemplateNotFoundError: If template does not exist.
        """
        if template_id not in self._templates:
            raise TemplateNotFoundError(f"Template '{template_id}' not found")
        return self._templates[template_id]

    def list_templates(
        self,
        tag: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Template]:
        """List all templates, optionally filtered.

        Args:
            tag: Filter by tag (case-insensitive).
            search: Search in name and description (case-insensitive).

        Returns:
            List of matching Template objects.
        """
        result = list(self._templates.values())

        if tag:
            tag_lower = tag.lower()
            result = [
                t for t in result
                if any(tg.lower() == tag_lower for tg in t.tags)
            ]

        if search:
            search_lower = search.lower()
            result = [
                t for t in result
                if search_lower in t.name.lower()
                or (t.description and search_lower in t.description.lower())
            ]

        return result

    def create_template(
        self,
        template_id: str,
        name: str,
        commands: List[APDUCommand],
        parameters: Dict,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True
    ) -> Template:
        """Create a new template.

        Args:
            template_id: Unique identifier for the template.
            name: Human-readable name.
            commands: List of APDU commands with placeholders.
            parameters: Dictionary of parameter definitions.
            description: Optional description.
            tags: Optional list of tags.
            validate_flag: If True, validate before creating.

        Returns:
            The created Template object.

        Raises:
            ValidationError: If validation fails.
            ValueError: If template ID already exists.
        """
        if template_id in self._templates:
            raise ValueError(f"Template '{template_id}' already exists")

        template = Template(
            id=template_id,
            name=name,
            commands=commands,
            parameters=parameters,
            description=description,
            tags=tags or []
        )

        if validate_flag:
            valid, errors = validate_template(template)
            if not valid:
                raise ValidationError(
                    f"Template validation failed: {'; '.join(errors)}"
                )

        self._templates[template_id] = template
        logger.info(f"Created template '{template_id}'")
        return template

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        commands: Optional[List[APDUCommand]] = None,
        parameters: Optional[Dict] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True
    ) -> Template:
        """Update an existing template.

        Args:
            template_id: ID of template to update.
            name: New name (if provided).
            commands: New commands (if provided).
            parameters: New parameters (if provided).
            description: New description (if provided).
            tags: New tags (if provided).
            validate_flag: If True, validate after updating.

        Returns:
            The updated Template object.

        Raises:
            TemplateNotFoundError: If template does not exist.
            ValidationError: If validation fails.
        """
        if template_id not in self._templates:
            raise TemplateNotFoundError(f"Template '{template_id}' not found")

        existing = self._templates[template_id]

        updated = Template(
            id=template_id,
            name=name if name is not None else existing.name,
            commands=commands if commands is not None else existing.commands,
            parameters=parameters if parameters is not None else existing.parameters,
            description=description if description is not None else existing.description,
            tags=tags if tags is not None else existing.tags
        )

        if validate_flag:
            valid, errors = validate_template(updated)
            if not valid:
                raise ValidationError(
                    f"Template validation failed: {'; '.join(errors)}"
                )

        self._templates[template_id] = updated
        logger.info(f"Updated template '{template_id}'")
        return updated

    def delete_template(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: ID of template to delete.

        Returns:
            True if deleted.

        Raises:
            TemplateNotFoundError: If template does not exist.
        """
        if template_id not in self._templates:
            raise TemplateNotFoundError(f"Template '{template_id}' not found")

        del self._templates[template_id]
        logger.info(f"Deleted template '{template_id}'")
        return True

    def template_exists(self, template_id: str) -> bool:
        """Check if a template exists.

        Args:
            template_id: The template identifier.

        Returns:
            True if template exists.
        """
        return template_id in self._templates

    # =========================================================================
    # Template Rendering
    # =========================================================================

    def render_template(
        self,
        template_id: str,
        params: Dict[str, str]
    ) -> List[APDUCommand]:
        """Render a template with parameter values.

        Args:
            template_id: ID of template to render.
            params: Dictionary of parameter name -> value.

        Returns:
            List of rendered APDUCommand objects.

        Raises:
            TemplateNotFoundError: If template does not exist.
            RenderError: If rendering fails.
        """
        template = self.get_template(template_id)
        return render_template(template, params)

    def render_template_to_script(
        self,
        template_id: str,
        params: Dict[str, str],
        script_id: Optional[str] = None,
        script_name: Optional[str] = None,
        save: bool = False
    ) -> Script:
        """Render a template to a new Script object.

        Args:
            template_id: ID of template to render.
            params: Dictionary of parameter name -> value.
            script_id: Optional ID for the new script.
            script_name: Optional name for the new script.
            save: If True, save the script to the manager.

        Returns:
            The rendered Script object.

        Raises:
            TemplateNotFoundError: If template does not exist.
            RenderError: If rendering fails.
        """
        template = self.get_template(template_id)
        script = render_to_script(template, params, script_id, script_name)

        if save:
            # Avoid duplicate ID
            if script.id in self._scripts:
                # Generate unique ID
                base_id = script.id
                counter = 1
                while f"{base_id}-{counter}" in self._scripts:
                    counter += 1
                script = Script(
                    id=f"{base_id}-{counter}",
                    name=script.name,
                    commands=script.commands,
                    description=script.description,
                    tags=script.tags,
                    created_at=script.created_at,
                    updated_at=script.updated_at
                )

            self._scripts[script.id] = script
            logger.info(f"Saved rendered script '{script.id}'")

        return script

    # =========================================================================
    # Persistence
    # =========================================================================

    def save_to_file(self, file_path: str) -> None:
        """Save all scripts and templates to a YAML file.

        Args:
            file_path: Path to output YAML file.
        """
        scripts = list(self._scripts.values())
        templates = list(self._templates.values())
        save_file(file_path, scripts, templates)
        logger.info(
            f"Saved {len(scripts)} scripts and {len(templates)} templates "
            f"to {file_path}"
        )

    def save_scripts_to_file(self, file_path: str) -> None:
        """Save only scripts to a YAML file.

        Args:
            file_path: Path to output YAML file.
        """
        scripts = list(self._scripts.values())
        save_file(file_path, scripts, [])
        logger.info(f"Saved {len(scripts)} scripts to {file_path}")

    def save_templates_to_file(self, file_path: str) -> None:
        """Save only templates to a YAML file.

        Args:
            file_path: Path to output YAML file.
        """
        templates = list(self._templates.values())
        save_file(file_path, [], templates)
        logger.info(f"Saved {len(templates)} templates to {file_path}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clear(self) -> None:
        """Clear all scripts and templates."""
        self._scripts.clear()
        self._templates.clear()
        logger.info("Cleared all scripts and templates")

    def get_stats(self) -> Dict:
        """Get statistics about stored scripts and templates.

        Returns:
            Dictionary with counts and metadata.
        """
        all_tags = set()
        for script in self._scripts.values():
            all_tags.update(script.tags)
        for template in self._templates.values():
            all_tags.update(template.tags)

        return {
            'script_count': len(self._scripts),
            'template_count': len(self._templates),
            'total_commands': sum(
                len(s.commands) for s in self._scripts.values()
            ),
            'tags': sorted(all_tags),
            'scripts_dir': str(self._scripts_dir) if self._scripts_dir else None
        }

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across scripts and templates.

        Returns:
            Sorted list of unique tags.
        """
        tags = set()
        for script in self._scripts.values():
            tags.update(script.tags)
        for template in self._templates.values():
            tags.update(template.tags)
        return sorted(tags)
