"""Settings repository for GP OTA Tester.

This module provides the repository for application settings
CRUD operations.

Example:
    >>> from gp_ota_tester.database.repositories import SettingRepository
    >>> with UnitOfWork(manager) as uow:
    ...     port = uow.settings.get_value("server.port", default=8443)
    ...     uow.settings.set_value("server.port", 9443)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from gp_ota_tester.database.models import Setting
from gp_ota_tester.database.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    """Repository for settings operations.

    Provides CRUD operations and settings-specific methods.

    Example:
        >>> repo = SettingRepository(session)
        >>> value = repo.get_value("server.port", default=8443)
        >>> repo.set_value("server.port", 9443)
    """

    def __init__(self, session: Session) -> None:
        """Initialize settings repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, Setting)

    def get_value(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get setting value by key.

        Args:
            key: Setting key.
            default: Default value if not found.

        Returns:
            Setting value or default.
        """
        setting = self.get(key)
        if setting is None:
            return default
        return setting.value

    def set_value(
        self,
        key: str,
        value: Any,
        category: str = "general",
        description: Optional[str] = None,
    ) -> Setting:
        """Set a setting value.

        Creates the setting if it doesn't exist, updates if it does.

        Args:
            key: Setting key.
            value: Setting value.
            category: Setting category.
            description: Setting description.

        Returns:
            Created or updated setting.
        """
        setting = self.get(key)
        if setting is None:
            setting = Setting(
                key=key,
                value=value,
                category=category,
                description=description,
            )
            return self.create(setting)
        else:
            setting.value = value
            if description:
                setting.description = description
            if category:
                setting.category = category
            return self.update(setting)

    def delete_key(self, key: str) -> bool:
        """Delete a setting by key.

        Args:
            key: Setting key.

        Returns:
            True if deleted, False if not found.
        """
        return self.delete_by_id(key)

    def find_by_category(self, category: str) -> List[Setting]:
        """Find all settings in a category.

        Args:
            category: Category name.

        Returns:
            List of settings in the category.
        """
        stmt = (
            select(Setting)
            .where(Setting.category == category)
            .order_by(Setting.key)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_categories(self) -> List[str]:
        """Get all distinct categories.

        Returns:
            List of category names.
        """
        stmt = select(Setting.category).distinct().order_by(Setting.category)
        result = self._session.execute(stmt)
        return [row[0] for row in result.all()]

    def get_all_as_dict(self) -> Dict[str, Any]:
        """Get all settings as a dictionary.

        Returns:
            Dictionary mapping keys to values.
        """
        settings = self.get_all()
        return {s.key: s.value for s in settings}

    def get_category_as_dict(self, category: str) -> Dict[str, Any]:
        """Get all settings in a category as a dictionary.

        Args:
            category: Category name.

        Returns:
            Dictionary mapping keys to values.
        """
        settings = self.find_by_category(category)
        return {s.key: s.value for s in settings}

    def set_many(self, settings: Dict[str, Any], category: str = "general") -> int:
        """Set multiple settings at once.

        Args:
            settings: Dictionary of key-value pairs.
            category: Category for new settings.

        Returns:
            Number of settings updated/created.
        """
        count = 0
        for key, value in settings.items():
            self.set_value(key, value, category=category)
            count += 1
        return count

    def search(self, query: str) -> List[Setting]:
        """Search settings by key or description.

        Args:
            query: Search string.

        Returns:
            List of matching settings.
        """
        pattern = f"%{query}%"
        stmt = select(Setting).where(
            Setting.key.ilike(pattern) | Setting.description.ilike(pattern)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # Typed Getters
    # =========================================================================

    def get_string(self, key: str, default: str = "") -> str:
        """Get setting as string.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            String value.
        """
        setting = self.get(key)
        if setting is None:
            return default
        return setting.as_string(default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get setting as integer.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            Integer value.
        """
        setting = self.get(key)
        if setting is None:
            return default
        return setting.as_int(default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get setting as float.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            Float value.
        """
        setting = self.get(key)
        if setting is None:
            return default
        return setting.as_float(default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get setting as boolean.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            Boolean value.
        """
        setting = self.get(key)
        if setting is None:
            return default
        return setting.as_bool(default)

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get setting as list.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            List value.
        """
        setting = self.get(key)
        if setting is None:
            return default if default is not None else []
        return setting.as_list(default)

    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """Get setting as dictionary.

        Args:
            key: Setting key.
            default: Default value.

        Returns:
            Dict value.
        """
        setting = self.get(key)
        if setting is None:
            return default if default is not None else {}
        return setting.as_dict(default)
