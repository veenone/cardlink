"""Script repository for GP OTA Tester.

This module provides the repository for APDU script CRUD operations.

Example:
    >>> from cardlink.database.repositories import ScriptRepository
    >>> with UnitOfWork(manager) as uow:
    ...     script = uow.scripts.get("select-isd")
    ...     all_scripts = uow.scripts.get_all()
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cardlink.database.models import Script
from cardlink.database.repositories.base import BaseRepository
from cardlink.scripts.models import Script as ScriptModel


class ScriptRepository(BaseRepository[Script]):
    """Repository for APDU script operations.

    Provides CRUD operations and script-specific methods for
    database-backed script storage.

    Example:
        >>> repo = ScriptRepository(session)
        >>> script = repo.get("select-isd")
        >>> scripts = repo.find_by_tag("gp")
    """

    def __init__(self, session: Session) -> None:
        """Initialize script repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, Script)

    def get_script_model(self, script_id: str) -> Optional[ScriptModel]:
        """Get script as dataclass model.

        Args:
            script_id: Script identifier.

        Returns:
            Script dataclass or None if not found.
        """
        db_script = self.get(script_id)
        if db_script is None:
            return None
        return db_script.to_script_model()

    def get_all_script_models(self) -> List[ScriptModel]:
        """Get all scripts as dataclass models.

        Returns:
            List of Script dataclass instances.
        """
        db_scripts = self.get_all()
        return [s.to_script_model() for s in db_scripts]

    def save_script_model(self, script: ScriptModel) -> Script:
        """Save or update a script from dataclass model.

        Creates if doesn't exist, updates if it does.

        Args:
            script: Script dataclass instance.

        Returns:
            Database Script model.
        """
        existing = self.get(script.id)
        if existing is None:
            # Create new
            db_script = Script.from_script_model(script)
            return self.create(db_script)
        else:
            # Update existing
            existing.name = script.name
            existing.description = script.description
            existing.commands = [cmd.to_dict() for cmd in script.commands]
            existing.tags = script.tags or []
            existing.updated_at = datetime.utcnow()
            return self.update(existing)

    def delete_script(self, script_id: str) -> bool:
        """Delete a script by ID.

        Args:
            script_id: Script identifier.

        Returns:
            True if deleted, False if not found.
        """
        return self.delete_by_id(script_id)

    def find_by_tag(self, tag: str) -> List[Script]:
        """Find scripts containing a specific tag.

        Note: JSON array containment query varies by database.
        This implementation uses SQLite JSON functions.

        Args:
            tag: Tag to search for.

        Returns:
            List of scripts with the tag.
        """
        # For SQLite, we use json_each to search JSON arrays
        # This is a simplified approach that works across databases
        all_scripts = self.get_all()
        return [s for s in all_scripts if tag in (s.tags or [])]

    def find_by_name(self, name: str, partial: bool = True) -> List[Script]:
        """Find scripts by name.

        Args:
            name: Name to search for.
            partial: If True, performs partial match.

        Returns:
            List of matching scripts.
        """
        if partial:
            pattern = f"%{name}%"
            stmt = select(Script).where(Script.name.ilike(pattern))
        else:
            stmt = select(Script).where(Script.name == name)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def search(self, query: str) -> List[Script]:
        """Search scripts by name or description.

        Args:
            query: Search string.

        Returns:
            List of matching scripts.
        """
        pattern = f"%{query}%"
        stmt = select(Script).where(
            or_(
                Script.name.ilike(pattern),
                Script.description.ilike(pattern),
                Script.id.ilike(pattern),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all scripts.

        Returns:
            List of unique tag names.
        """
        all_scripts = self.get_all()
        tags = set()
        for script in all_scripts:
            if script.tags:
                tags.update(script.tags)
        return sorted(list(tags))

    def get_recent(self, limit: int = 10) -> List[Script]:
        """Get recently updated scripts.

        Args:
            limit: Maximum number to return.

        Returns:
            List of scripts ordered by updated_at descending.
        """
        stmt = (
            select(Script)
            .order_by(Script.updated_at.desc())
            .limit(limit)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def bulk_save(self, scripts: List[ScriptModel]) -> int:
        """Bulk save multiple scripts.

        Args:
            scripts: List of Script dataclass instances.

        Returns:
            Number of scripts saved.
        """
        count = 0
        for script in scripts:
            self.save_script_model(script)
            count += 1
        return count
