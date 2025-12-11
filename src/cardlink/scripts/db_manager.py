"""Database-backed Script Manager for APDU scripts.

This module provides database-backed storage for scripts and templates,
extending the base ScriptManager with persistent SQLite/PostgreSQL/MySQL storage.

Example:
    >>> from cardlink.scripts.db_manager import DatabaseScriptManager
    >>> from cardlink.database import DatabaseManager
    >>>
    >>> db_manager = DatabaseManager("sqlite:///scripts.db")
    >>> script_manager = DatabaseScriptManager(db_manager)
    >>> script_manager.sync_from_database()  # Load from DB
    >>>
    >>> # Or with auto-sync mode
    >>> script_manager = DatabaseScriptManager(db_manager, auto_sync=True)
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from cardlink.scripts.manager import ScriptManager
from cardlink.scripts.models import (
    APDUCommand,
    Script,
    ScriptNotFoundError,
    Template,
    TemplateNotFoundError,
    ValidationError,
)
from cardlink.scripts.validator import validate_script, validate_template

if TYPE_CHECKING:
    from cardlink.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseScriptManager(ScriptManager):
    """Script manager with database persistence.

    Extends ScriptManager to provide optional database backing for
    scripts and templates. Supports SQLite, PostgreSQL, and MySQL
    through the DatabaseManager.

    The manager can operate in two modes:
    1. **Manual sync**: Call sync_to_database() and sync_from_database()
       explicitly to persist/load data.
    2. **Auto-sync**: Automatically persist changes on each CRUD operation.

    Attributes:
        db_manager: DatabaseManager instance for database operations.
        auto_sync: If True, automatically persist changes to database.

    Example:
        >>> db_manager = DatabaseManager("sqlite:///scripts.db")
        >>> manager = DatabaseScriptManager(db_manager, auto_sync=True)
        >>> manager.create_script("test", "Test", [cmd])  # Auto-saved to DB
    """

    def __init__(
        self,
        db_manager: "DatabaseManager",
        auto_sync: bool = False,
    ) -> None:
        """Initialize database-backed script manager.

        Args:
            db_manager: Database manager for persistence.
            auto_sync: If True, auto-persist changes to database.
        """
        super().__init__()
        self._db_manager = db_manager
        self._auto_sync = auto_sync
        logger.info(
            f"Initialized DatabaseScriptManager (auto_sync={auto_sync})"
        )

    @property
    def db_manager(self) -> "DatabaseManager":
        """Get the database manager."""
        return self._db_manager

    @property
    def auto_sync(self) -> bool:
        """Check if auto-sync is enabled."""
        return self._auto_sync

    @auto_sync.setter
    def auto_sync(self, value: bool) -> None:
        """Set auto-sync mode."""
        self._auto_sync = value
        logger.info(f"Auto-sync set to {value}")

    # =========================================================================
    # Database Sync Operations
    # =========================================================================

    def sync_from_database(self) -> Tuple[int, int]:
        """Load all scripts and templates from database.

        Replaces in-memory data with database contents.

        Returns:
            Tuple of (scripts_loaded, templates_loaded) counts.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        scripts_loaded = 0
        templates_loaded = 0

        with UnitOfWork(self._db_manager) as uow:
            # Load scripts
            db_scripts = uow.scripts.get_all()
            self._scripts.clear()
            for db_script in db_scripts:
                script = db_script.to_script_model()
                self._scripts[script.id] = script
                scripts_loaded += 1

            # Load templates
            db_templates = uow.templates.get_all()
            self._templates.clear()
            for db_template in db_templates:
                template = db_template.to_template_model()
                self._templates[template.id] = template
                templates_loaded += 1

        logger.info(
            f"Synced from database: {scripts_loaded} scripts, "
            f"{templates_loaded} templates"
        )
        return scripts_loaded, templates_loaded

    def sync_to_database(self) -> Tuple[int, int]:
        """Save all in-memory scripts and templates to database.

        Updates existing records and creates new ones.

        Returns:
            Tuple of (scripts_saved, templates_saved) counts.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        scripts_saved = 0
        templates_saved = 0

        with UnitOfWork(self._db_manager) as uow:
            # Save scripts
            for script in self._scripts.values():
                uow.scripts.save_script_model(script)
                scripts_saved += 1

            # Save templates
            for template in self._templates.values():
                uow.templates.save_template_model(template)
                templates_saved += 1

            uow.commit()

        logger.info(
            f"Synced to database: {scripts_saved} scripts, "
            f"{templates_saved} templates"
        )
        return scripts_saved, templates_saved

    def _save_script_to_db(self, script: Script) -> None:
        """Save a single script to database (internal helper).

        Args:
            script: Script to save.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            uow.scripts.save_script_model(script)
            uow.commit()

    def _delete_script_from_db(self, script_id: str) -> None:
        """Delete a script from database (internal helper).

        Args:
            script_id: Script ID to delete.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            uow.scripts.delete_script(script_id)
            uow.commit()

    def _save_template_to_db(self, template: Template) -> None:
        """Save a single template to database (internal helper).

        Args:
            template: Template to save.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            uow.templates.save_template_model(template)
            uow.commit()

    def _delete_template_from_db(self, template_id: str) -> None:
        """Delete a template from database (internal helper).

        Args:
            template_id: Template ID to delete.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            uow.templates.delete_template(template_id)
            uow.commit()

    # =========================================================================
    # Script CRUD Operations (Override with DB sync)
    # =========================================================================

    def create_script(
        self,
        script_id: str,
        name: str,
        commands: List[APDUCommand],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True,
    ) -> Script:
        """Create a new script with optional database persistence.

        Args:
            script_id: Unique identifier for the script.
            name: Human-readable name.
            commands: List of APDU commands.
            description: Optional description.
            tags: Optional list of tags.
            validate_flag: If True, validate before creating.

        Returns:
            The created Script object.
        """
        script = super().create_script(
            script_id, name, commands, description, tags, validate_flag
        )

        if self._auto_sync:
            self._save_script_to_db(script)
            logger.debug(f"Auto-synced script '{script_id}' to database")

        return script

    def update_script(
        self,
        script_id: str,
        name: Optional[str] = None,
        commands: Optional[List[APDUCommand]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True,
    ) -> Script:
        """Update an existing script with optional database persistence.

        Args:
            script_id: ID of script to update.
            name: New name (if provided).
            commands: New commands (if provided).
            description: New description (if provided).
            tags: New tags (if provided).
            validate_flag: If True, validate after updating.

        Returns:
            The updated Script object.
        """
        script = super().update_script(
            script_id, name, commands, description, tags, validate_flag
        )

        if self._auto_sync:
            self._save_script_to_db(script)
            logger.debug(f"Auto-synced script '{script_id}' to database")

        return script

    def delete_script(self, script_id: str) -> bool:
        """Delete a script with optional database persistence.

        Args:
            script_id: ID of script to delete.

        Returns:
            True if deleted.
        """
        result = super().delete_script(script_id)

        if self._auto_sync and result:
            self._delete_script_from_db(script_id)
            logger.debug(f"Auto-deleted script '{script_id}' from database")

        return result

    # =========================================================================
    # Template CRUD Operations (Override with DB sync)
    # =========================================================================

    def create_template(
        self,
        template_id: str,
        name: str,
        commands: List[APDUCommand],
        parameters: Dict,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True,
    ) -> Template:
        """Create a new template with optional database persistence.

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
        """
        template = super().create_template(
            template_id, name, commands, parameters, description, tags, validate_flag
        )

        if self._auto_sync:
            self._save_template_to_db(template)
            logger.debug(f"Auto-synced template '{template_id}' to database")

        return template

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        commands: Optional[List[APDUCommand]] = None,
        parameters: Optional[Dict] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        validate_flag: bool = True,
    ) -> Template:
        """Update an existing template with optional database persistence.

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
        """
        template = super().update_template(
            template_id, name, commands, parameters, description, tags, validate_flag
        )

        if self._auto_sync:
            self._save_template_to_db(template)
            logger.debug(f"Auto-synced template '{template_id}' to database")

        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template with optional database persistence.

        Args:
            template_id: ID of template to delete.

        Returns:
            True if deleted.
        """
        result = super().delete_template(template_id)

        if self._auto_sync and result:
            self._delete_template_from_db(template_id)
            logger.debug(f"Auto-deleted template '{template_id}' from database")

        return result

    # =========================================================================
    # Database-Specific Operations
    # =========================================================================

    def get_script_from_db(self, script_id: str) -> Optional[Script]:
        """Get a script directly from database (bypasses cache).

        Args:
            script_id: Script ID to retrieve.

        Returns:
            Script object or None if not found.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            return uow.scripts.get_script_model(script_id)

    def get_template_from_db(self, template_id: str) -> Optional[Template]:
        """Get a template directly from database (bypasses cache).

        Args:
            template_id: Template ID to retrieve.

        Returns:
            Template object or None if not found.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            return uow.templates.get_template_model(template_id)

    def search_scripts_in_db(self, query: str) -> List[Script]:
        """Search scripts in database by name or description.

        Args:
            query: Search string.

        Returns:
            List of matching Script objects.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            db_scripts = uow.scripts.search(query)
            return [s.to_script_model() for s in db_scripts]

    def search_templates_in_db(self, query: str) -> List[Template]:
        """Search templates in database by name or description.

        Args:
            query: Search string.

        Returns:
            List of matching Template objects.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            db_templates = uow.templates.search(query)
            return [t.to_template_model() for t in db_templates]

    def get_db_stats(self) -> Dict:
        """Get database statistics.

        Returns:
            Dictionary with database statistics.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        with UnitOfWork(self._db_manager) as uow:
            script_count = uow.scripts.count()
            template_count = uow.templates.count()
            script_tags = uow.scripts.get_all_tags()
            template_tags = uow.templates.get_all_tags()

        all_tags = sorted(set(script_tags) | set(template_tags))

        return {
            "script_count": script_count,
            "template_count": template_count,
            "tags": all_tags,
            "database_url": str(self._db_manager.database_url),
        }

    def clear_database(self) -> Tuple[int, int]:
        """Delete all scripts and templates from database.

        WARNING: This is destructive and cannot be undone!

        Returns:
            Tuple of (scripts_deleted, templates_deleted) counts.
        """
        from cardlink.database.unit_of_work import UnitOfWork

        scripts_deleted = 0
        templates_deleted = 0

        with UnitOfWork(self._db_manager) as uow:
            scripts_deleted = uow.scripts.delete_all()
            templates_deleted = uow.templates.delete_all()
            uow.commit()

        logger.warning(
            f"Cleared database: {scripts_deleted} scripts, "
            f"{templates_deleted} templates deleted"
        )
        return scripts_deleted, templates_deleted

    def import_from_yaml_to_db(
        self,
        file_path: str,
        validate: bool = True,
        skip_invalid: bool = True,
    ) -> Tuple[int, int]:
        """Import scripts and templates from YAML directly to database.

        Combines load_from_file and sync_to_database in one operation.

        Args:
            file_path: Path to YAML file.
            validate: If True, validate items before importing.
            skip_invalid: If True, skip invalid items.

        Returns:
            Tuple of (scripts_imported, templates_imported) counts.
        """
        # Load into memory
        scripts_loaded, templates_loaded = self.load_from_file(
            file_path, validate, skip_invalid
        )

        # Sync to database
        if scripts_loaded > 0 or templates_loaded > 0:
            self.sync_to_database()

        return scripts_loaded, templates_loaded

    def export_from_db_to_yaml(self, file_path: str) -> Tuple[int, int]:
        """Export all scripts and templates from database to YAML.

        Combines sync_from_database and save_to_file in one operation.

        Args:
            file_path: Path to output YAML file.

        Returns:
            Tuple of (scripts_exported, templates_exported) counts.
        """
        # Sync from database
        scripts_loaded, templates_loaded = self.sync_from_database()

        # Save to file
        if scripts_loaded > 0 or templates_loaded > 0:
            self.save_to_file(file_path)

        return scripts_loaded, templates_loaded
