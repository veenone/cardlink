"""Base repository for GP OTA Tester.

This module provides the base repository class with common CRUD
operations that all entity repositories inherit from.

Example:
    >>> from gp_ota_tester.database.repositories.base import BaseRepository
    >>> class MyRepository(BaseRepository[MyModel]):
    ...     def __init__(self, session: Session):
    ...         super().__init__(session, MyModel)
"""

from dataclasses import dataclass
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from gp_ota_tester.database.exceptions import IntegrityError, NotFoundError

T = TypeVar("T")


@dataclass
class Page:
    """Pagination result container.

    Attributes:
        items: List of items for current page.
        total: Total number of items across all pages.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    @property
    def next_page(self) -> Optional[int]:
        """Get next page number or None."""
        return self.page + 1 if self.has_next else None

    @property
    def prev_page(self) -> Optional[int]:
        """Get previous page number or None."""
        return self.page - 1 if self.has_prev else None


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    Provides generic data access methods for any SQLAlchemy model.
    Subclasses should set the model class and add entity-specific methods.

    Type Parameters:
        T: The model type this repository manages.

    Attributes:
        _session: SQLAlchemy session for database operations.
        _model_class: The model class this repository manages.

    Example:
        >>> class DeviceRepository(BaseRepository[Device]):
        ...     def __init__(self, session: Session):
        ...         super().__init__(session, Device)
        ...
        ...     def find_active(self) -> List[Device]:
        ...         return self.find_by(is_active=True)
    """

    def __init__(self, session: Session, model_class: Type[T]) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy session.
            model_class: The model class to manage.
        """
        self._session = session
        self._model_class = model_class

    @property
    def session(self) -> Session:
        """Get the session."""
        return self._session

    @property
    def model_class(self) -> Type[T]:
        """Get the model class."""
        return self._model_class

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get(self, id: Any) -> Optional[T]:
        """Get entity by primary key.

        Args:
            id: Primary key value.

        Returns:
            Entity if found, None otherwise.
        """
        return self._session.get(self._model_class, id)

    def get_or_raise(self, id: Any) -> T:
        """Get entity by primary key or raise error.

        Args:
            id: Primary key value.

        Returns:
            Entity instance.

        Raises:
            NotFoundError: If entity not found.
        """
        entity = self.get(id)
        if entity is None:
            raise NotFoundError(self._model_class.__name__, id)
        return entity

    def get_all(self, limit: Optional[int] = None) -> List[T]:
        """Get all entities with optional limit.

        Args:
            limit: Maximum number of entities to return.

        Returns:
            List of entities.
        """
        stmt = select(self._model_class)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by(self, **kwargs: Any) -> List[T]:
        """Find entities by attribute values.

        Args:
            **kwargs: Attribute name-value pairs to filter by.

        Returns:
            List of matching entities.

        Example:
            >>> devices = repo.find_by(device_type=DeviceType.PHONE, is_active=True)
        """
        stmt = select(self._model_class)
        for key, value in kwargs.items():
            if hasattr(self._model_class, key):
                stmt = stmt.where(getattr(self._model_class, key) == value)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_one_by(self, **kwargs: Any) -> Optional[T]:
        """Find single entity by attribute values.

        Args:
            **kwargs: Attribute name-value pairs to filter by.

        Returns:
            First matching entity or None.
        """
        results = self.find_by(**kwargs)
        return results[0] if results else None

    def exists(self, id: Any) -> bool:
        """Check if entity exists by primary key.

        Args:
            id: Primary key value.

        Returns:
            True if entity exists.
        """
        return self.get(id) is not None

    def count(self) -> int:
        """Count all entities.

        Returns:
            Total number of entities.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self._model_class)
        result = self._session.execute(stmt)
        return result.scalar() or 0

    def count_by(self, **kwargs: Any) -> int:
        """Count entities matching criteria.

        Args:
            **kwargs: Attribute name-value pairs to filter by.

        Returns:
            Number of matching entities.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self._model_class)
        for key, value in kwargs.items():
            if hasattr(self._model_class, key):
                stmt = stmt.where(getattr(self._model_class, key) == value)
        result = self._session.execute(stmt)
        return result.scalar() or 0

    # =========================================================================
    # Write Operations
    # =========================================================================

    def add(self, entity: T) -> T:
        """Add a new entity to the session.

        The entity will be persisted when the session is committed.

        Args:
            entity: Entity to add.

        Returns:
            The added entity.
        """
        self._session.add(entity)
        return entity

    def add_all(self, entities: List[T]) -> List[T]:
        """Add multiple entities to the session.

        Args:
            entities: List of entities to add.

        Returns:
            List of added entities.
        """
        self._session.add_all(entities)
        return entities

    def create(self, entity: T) -> T:
        """Create a new entity (add and flush).

        Flushes immediately to get database-generated values.

        Args:
            entity: Entity to create.

        Returns:
            The created entity with generated values.

        Raises:
            IntegrityError: If database constraints are violated.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except Exception as e:
            if "UNIQUE constraint" in str(e) or "Duplicate" in str(e):
                raise IntegrityError(
                    f"Entity already exists: {entity}",
                    cause=e,
                ) from e
            raise

    def create_all(self, entities: List[T]) -> List[T]:
        """Create multiple entities.

        Args:
            entities: List of entities to create.

        Returns:
            List of created entities.
        """
        self._session.add_all(entities)
        self._session.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update an existing entity.

        The entity must already be in the session or be merged.

        Args:
            entity: Entity with updated values.

        Returns:
            The updated entity.
        """
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """Delete an entity.

        Args:
            entity: Entity to delete.
        """
        self._session.delete(entity)
        self._session.flush()

    def delete_by_id(self, id: Any) -> bool:
        """Delete entity by primary key.

        Args:
            id: Primary key value.

        Returns:
            True if entity was deleted, False if not found.
        """
        entity = self.get(id)
        if entity is not None:
            self.delete(entity)
            return True
        return False

    # =========================================================================
    # Pagination
    # =========================================================================

    def paginate(
        self,
        page: int = 1,
        per_page: int = 20,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Page:
        """Get paginated results.

        Args:
            page: Page number (1-based).
            per_page: Items per page.
            order_by: Column name to order by.
            descending: If True, order descending.

        Returns:
            Page object with items and pagination info.
        """
        # Build base query
        stmt = select(self._model_class)

        # Apply ordering
        if order_by and hasattr(self._model_class, order_by):
            column = getattr(self._model_class, order_by)
            if descending:
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column)

        # Get total count
        total = self.count()

        # Calculate pagination
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        offset = (page - 1) * per_page

        # Fetch items
        stmt = stmt.offset(offset).limit(per_page)
        result = self._session.execute(stmt)
        items = list(result.scalars().all())

        return Page(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def delete_all(self) -> int:
        """Delete all entities.

        WARNING: This deletes all records in the table!

        Returns:
            Number of deleted entities.
        """
        from sqlalchemy import delete

        stmt = delete(self._model_class)
        result = self._session.execute(stmt)
        return result.rowcount

    def delete_by(self, **kwargs: Any) -> int:
        """Delete entities matching criteria.

        Args:
            **kwargs: Attribute name-value pairs to filter by.

        Returns:
            Number of deleted entities.
        """
        from sqlalchemy import delete

        stmt = delete(self._model_class)
        for key, value in kwargs.items():
            if hasattr(self._model_class, key):
                stmt = stmt.where(getattr(self._model_class, key) == value)
        result = self._session.execute(stmt)
        return result.rowcount
