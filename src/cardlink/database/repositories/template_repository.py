"""Template repository for GP OTA Tester.

This module provides the repository for APDU template CRUD operations.

Example:
    >>> from cardlink.database.repositories import TemplateRepository
    >>> with UnitOfWork(manager) as uow:
    ...     template = uow.templates.get("install-applet")
    ...     all_templates = uow.templates.get_all()
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cardlink.database.models import Template
from cardlink.database.repositories.base import BaseRepository
from cardlink.scripts.models import Template as TemplateModel


class TemplateRepository(BaseRepository[Template]):
    """Repository for APDU template operations.

    Provides CRUD operations and template-specific methods for
    database-backed template storage.

    Example:
        >>> repo = TemplateRepository(session)
        >>> template = repo.get("install-applet")
        >>> templates = repo.find_by_tag("gp")
    """

    def __init__(self, session: Session) -> None:
        """Initialize template repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, Template)

    def get_template_model(self, template_id: str) -> Optional[TemplateModel]:
        """Get template as dataclass model.

        Args:
            template_id: Template identifier.

        Returns:
            Template dataclass or None if not found.
        """
        db_template = self.get(template_id)
        if db_template is None:
            return None
        return db_template.to_template_model()

    def get_all_template_models(self) -> List[TemplateModel]:
        """Get all templates as dataclass models.

        Returns:
            List of Template dataclass instances.
        """
        db_templates = self.get_all()
        return [t.to_template_model() for t in db_templates]

    def save_template_model(self, template: TemplateModel) -> Template:
        """Save or update a template from dataclass model.

        Creates if doesn't exist, updates if it does.

        Args:
            template: Template dataclass instance.

        Returns:
            Database Template model.
        """
        existing = self.get(template.id)
        if existing is None:
            # Create new
            db_template = Template.from_template_model(template)
            return self.create(db_template)
        else:
            # Update existing
            existing.name = template.name
            existing.description = template.description
            existing.commands = [cmd.to_dict() for cmd in template.commands]
            # Convert parameters to dict format
            parameters = {}
            for name, param in template.parameters.items():
                param_dict = param.to_dict()
                param_dict.pop("name", None)
                parameters[name] = param_dict
            existing.parameters = parameters
            existing.tags = template.tags or []
            existing.updated_at = datetime.utcnow()
            return self.update(existing)

    def delete_template(self, template_id: str) -> bool:
        """Delete a template by ID.

        Args:
            template_id: Template identifier.

        Returns:
            True if deleted, False if not found.
        """
        return self.delete_by_id(template_id)

    def find_by_tag(self, tag: str) -> List[Template]:
        """Find templates containing a specific tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of templates with the tag.
        """
        all_templates = self.get_all()
        return [t for t in all_templates if tag in (t.tags or [])]

    def find_by_name(self, name: str, partial: bool = True) -> List[Template]:
        """Find templates by name.

        Args:
            name: Name to search for.
            partial: If True, performs partial match.

        Returns:
            List of matching templates.
        """
        if partial:
            pattern = f"%{name}%"
            stmt = select(Template).where(Template.name.ilike(pattern))
        else:
            stmt = select(Template).where(Template.name == name)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def search(self, query: str) -> List[Template]:
        """Search templates by name or description.

        Args:
            query: Search string.

        Returns:
            List of matching templates.
        """
        pattern = f"%{query}%"
        stmt = select(Template).where(
            or_(
                Template.name.ilike(pattern),
                Template.description.ilike(pattern),
                Template.id.ilike(pattern),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all templates.

        Returns:
            List of unique tag names.
        """
        all_templates = self.get_all()
        tags = set()
        for template in all_templates:
            if template.tags:
                tags.update(template.tags)
        return sorted(list(tags))

    def find_by_parameter(self, param_name: str) -> List[Template]:
        """Find templates that have a specific parameter.

        Args:
            param_name: Parameter name to search for.

        Returns:
            List of templates with the parameter.
        """
        all_templates = self.get_all()
        return [t for t in all_templates if param_name in (t.parameters or {})]

    def get_recent(self, limit: int = 10) -> List[Template]:
        """Get recently updated templates.

        Args:
            limit: Maximum number to return.

        Returns:
            List of templates ordered by updated_at descending.
        """
        stmt = (
            select(Template)
            .order_by(Template.updated_at.desc())
            .limit(limit)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def bulk_save(self, templates: List[TemplateModel]) -> int:
        """Bulk save multiple templates.

        Args:
            templates: List of Template dataclass instances.

        Returns:
            Number of templates saved.
        """
        count = 0
        for template in templates:
            self.save_template_model(template)
            count += 1
        return count
