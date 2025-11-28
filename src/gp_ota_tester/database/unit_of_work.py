"""Unit of Work pattern implementation for GP OTA Tester.

This module implements the Unit of Work pattern for managing
database transactions and repository access.

Example:
    >>> from gp_ota_tester.database import DatabaseManager, UnitOfWork
    >>> manager = DatabaseManager()
    >>> with UnitOfWork(manager) as uow:
    ...     device = uow.devices.get("RF8M33XXXXX")
    ...     device.name = "Updated Name"
    ...     uow.commit()
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from gp_ota_tester.database.exceptions import DatabaseError

if TYPE_CHECKING:
    from gp_ota_tester.database.manager import DatabaseManager
    from gp_ota_tester.database.repositories.base import BaseRepository
    from gp_ota_tester.database.repositories.card_repository import CardRepository
    from gp_ota_tester.database.repositories.device_repository import DeviceRepository
    from gp_ota_tester.database.repositories.log_repository import LogRepository
    from gp_ota_tester.database.repositories.session_repository import SessionRepository
    from gp_ota_tester.database.repositories.setting_repository import SettingRepository
    from gp_ota_tester.database.repositories.test_repository import TestRepository


logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseRepository")


class UnitOfWork:
    """Unit of Work pattern implementation.

    Manages database transactions and provides access to repositories.
    All changes made through repositories are tracked and can be
    committed or rolled back as a single transaction.

    The UnitOfWork ensures that:
    - All repositories share the same session
    - Changes are atomic (all or nothing)
    - Proper cleanup on exit

    Attributes:
        session: The SQLAlchemy session for this unit of work.

    Example:
        >>> with UnitOfWork(manager) as uow:
        ...     # All operations in same transaction
        ...     device = uow.devices.get("device_id")
        ...     device.name = "New Name"
        ...     uow.commit()

    Example with explicit rollback:
        >>> with UnitOfWork(manager) as uow:
        ...     try:
        ...         uow.devices.create(Device(...))
        ...         # Something fails
        ...         raise ValueError("oops")
        ...     except ValueError:
        ...         uow.rollback()
        ...         raise
    """

    def __init__(self, db_manager: "DatabaseManager") -> None:
        """Initialize Unit of Work.

        Args:
            db_manager: Database manager for session creation.
        """
        self._db_manager = db_manager
        self._session: Optional[Session] = None
        self._repositories: Dict[Type, Any] = {}
        self._committed = False

    def __enter__(self) -> "UnitOfWork":
        """Enter context manager, create session.

        Returns:
            This UnitOfWork instance.
        """
        self._session = self._db_manager.create_session()
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        """Exit context manager, cleanup session.

        If an exception occurred and no explicit commit was made,
        the transaction is rolled back.
        """
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
        elif not self._committed:
            # No exception, but not committed - also rollback
            # This ensures explicit commit is required
            self.rollback()

        self.close()

    @property
    def session(self) -> Session:
        """Get the current database session.

        Returns:
            SQLAlchemy session.

        Raises:
            RuntimeError: If UnitOfWork not entered as context manager.
        """
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork must be used as context manager: "
                "with UnitOfWork(manager) as uow: ..."
            )
        return self._session

    def commit(self) -> None:
        """Commit current transaction.

        All changes made through repositories are persisted to
        the database.

        Raises:
            DatabaseError: If commit fails.
        """
        try:
            self.session.commit()
            self._committed = True
            logger.debug("Transaction committed")
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to commit transaction: {e}", cause=e) from e

    def rollback(self) -> None:
        """Rollback current transaction.

        All changes made through repositories are discarded.
        """
        if self._session is not None:
            self._session.rollback()
            logger.debug("Transaction rolled back")

    def close(self) -> None:
        """Close session and cleanup repositories.

        Called automatically on context manager exit.
        """
        if self._session is not None:
            self._session.close()
            self._session = None
            self._repositories.clear()
            logger.debug("Session closed")

    def flush(self) -> None:
        """Flush pending changes to database without committing.

        Useful when you need database-generated IDs before commit.
        """
        self.session.flush()

    def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database.

        Args:
            instance: Model instance to refresh.
        """
        self.session.refresh(instance)

    def _get_repository(self, repo_class: Type[T]) -> T:
        """Get or create a repository instance.

        Repositories are cached per UnitOfWork instance to ensure
        they share the same session.

        Args:
            repo_class: Repository class to instantiate.

        Returns:
            Repository instance.
        """
        if repo_class not in self._repositories:
            self._repositories[repo_class] = repo_class(self.session)
        return self._repositories[repo_class]

    @property
    def devices(self) -> "DeviceRepository":
        """Get device repository.

        Returns:
            DeviceRepository instance.
        """
        from gp_ota_tester.database.repositories.device_repository import DeviceRepository

        return self._get_repository(DeviceRepository)

    @property
    def cards(self) -> "CardRepository":
        """Get card profile repository.

        Returns:
            CardRepository instance.
        """
        from gp_ota_tester.database.repositories.card_repository import CardRepository

        return self._get_repository(CardRepository)

    @property
    def sessions(self) -> "SessionRepository":
        """Get OTA session repository.

        Returns:
            SessionRepository instance.
        """
        from gp_ota_tester.database.repositories.session_repository import SessionRepository

        return self._get_repository(SessionRepository)

    @property
    def logs(self) -> "LogRepository":
        """Get communication log repository.

        Returns:
            LogRepository instance.
        """
        from gp_ota_tester.database.repositories.log_repository import LogRepository

        return self._get_repository(LogRepository)

    @property
    def tests(self) -> "TestRepository":
        """Get test result repository.

        Returns:
            TestRepository instance.
        """
        from gp_ota_tester.database.repositories.test_repository import TestRepository

        return self._get_repository(TestRepository)

    @property
    def settings(self) -> "SettingRepository":
        """Get settings repository.

        Returns:
            SettingRepository instance.
        """
        from gp_ota_tester.database.repositories.setting_repository import SettingRepository

        return self._get_repository(SettingRepository)
