"""Database manager for GP OTA Tester.

This module provides the DatabaseManager class for managing database
connections, sessions, and lifecycle operations.

Example:
    >>> from cardlink.database import DatabaseManager, DatabaseConfig
    >>> config = DatabaseConfig(url="sqlite:///data/test.db")
    >>> manager = DatabaseManager(config)
    >>> manager.initialize()
    >>> with manager.session_scope() as session:
    ...     # perform database operations
    ...     pass
    >>> manager.close()
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from cardlink.database.config import DatabaseConfig
from cardlink.database.exceptions import ConnectionError, DatabaseError

if TYPE_CHECKING:
    from sqlalchemy import Engine


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and session lifecycle.

    The DatabaseManager is responsible for:
    - Creating and configuring the SQLAlchemy engine
    - Managing connection pooling per backend type
    - Providing session factory and context manager
    - Database health checks and lifecycle management

    Attributes:
        config: Database configuration settings.

    Example:
        >>> manager = DatabaseManager()
        >>> manager.initialize()
        >>> session = manager.create_session()
        >>> # ... use session ...
        >>> session.close()
        >>> manager.close()

    Example with context manager:
        >>> with manager.session_scope() as session:
        ...     # All operations in transaction
        ...     result = session.execute(text("SELECT 1"))
    """

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database manager.

        Args:
            config: Database configuration. If None, uses defaults.
        """
        self.config = config or DatabaseConfig()
        self._engine: Optional["Engine"] = None
        self._session_factory: Optional[sessionmaker] = None
        self._initialized = False

    @property
    def engine(self) -> "Engine":
        """Get database engine, initializing if needed.

        Returns:
            SQLAlchemy engine instance.

        Raises:
            ConnectionError: If engine initialization fails.
        """
        if not self._initialized:
            self.initialize()
        return self._engine  # type: ignore

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    def initialize(self) -> None:
        """Initialize database engine and session factory.

        Creates the SQLAlchemy engine with appropriate pooling
        configuration based on the database backend:
        - SQLite: NullPool (no pooling for thread safety)
        - MySQL/PostgreSQL: QueuePool with configurable size

        Raises:
            ConnectionError: If initialization fails.
        """
        if self._initialized:
            logger.debug("Database already initialized")
            return

        try:
            # Validate configuration
            self.config.validate()

            # Build engine arguments
            engine_kwargs = self._build_engine_kwargs()

            # Ensure SQLite directory exists
            if self.config.is_sqlite:
                self._ensure_sqlite_directory()

            # Create engine
            self._engine = create_engine(self.config.url, **engine_kwargs)

            # Configure SQLite pragmas
            if self.config.is_sqlite:
                self._configure_sqlite()

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
            )

            self._initialized = True
            logger.info(
                "Database initialized: %s (%s)",
                self.config.safe_url,
                self.config.backend_name,
            )

        except Exception as e:
            raise ConnectionError(
                f"Failed to initialize database: {e}",
                cause=e,
            ) from e

    def _build_engine_kwargs(self) -> Dict[str, Any]:
        """Build engine creation keyword arguments.

        Returns:
            Dictionary of engine configuration options.
        """
        kwargs: Dict[str, Any] = {
            "echo": self.config.echo,
        }

        if self.config.is_sqlite:
            # SQLite uses NullPool for thread safety
            kwargs["poolclass"] = NullPool
            # Enable check_same_thread=False for multi-threaded access
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # MySQL/PostgreSQL use connection pooling
            kwargs["poolclass"] = QueuePool
            kwargs["pool_size"] = self.config.pool_size
            kwargs["max_overflow"] = self.config.max_overflow
            kwargs["pool_timeout"] = self.config.pool_timeout
            kwargs["pool_pre_ping"] = True  # Verify connections

        return kwargs

    def _ensure_sqlite_directory(self) -> None:
        """Create SQLite database directory if needed."""
        db_path = self.config.get_sqlite_path()
        if db_path is not None:
            parent_dir = db_path.parent
            if parent_dir and not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
                logger.debug("Created database directory: %s", parent_dir)

    def _configure_sqlite(self) -> None:
        """Configure SQLite for optimal performance and concurrency.

        Sets the following pragmas:
        - journal_mode=WAL: Write-Ahead Logging for concurrent reads
        - foreign_keys=ON: Enforce foreign key constraints
        - synchronous=NORMAL: Balance between safety and speed
        - cache_size=-64000: 64MB cache size
        """

        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(
            dbapi_connection: Any, connection_record: Any
        ) -> None:
            cursor = dbapi_connection.cursor()
            try:
                # Enable WAL mode for concurrent reads
                cursor.execute("PRAGMA journal_mode=WAL")
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys=ON")
                # Optimize synchronous mode (NORMAL is good balance)
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Increase cache size to 64MB
                cursor.execute("PRAGMA cache_size=-64000")
                # Enable memory-mapped I/O (256MB)
                cursor.execute("PRAGMA mmap_size=268435456")
            finally:
                cursor.close()

    def create_session(self) -> Session:
        """Create a new database session.

        Returns:
            New SQLAlchemy session instance.

        Raises:
            ConnectionError: If manager not initialized.
        """
        if not self._initialized:
            self.initialize()

        if self._session_factory is None:
            raise ConnectionError("Session factory not initialized")

        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around operations.

        This context manager handles the session lifecycle:
        - Creates a new session
        - Commits on successful completion
        - Rolls back on exception
        - Always closes the session

        Yields:
            Database session for operations.

        Raises:
            DatabaseError: On database operation errors.

        Example:
            >>> with manager.session_scope() as session:
            ...     device = session.get(Device, device_id)
            ...     device.name = "New Name"
            ...     # Automatically committed on exit
        """
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Session rollback due to: %s", e)
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """Create all tables defined in models.

        Creates tables for all models that inherit from Base.
        Safe to call multiple times (uses CREATE IF NOT EXISTS).

        Raises:
            DatabaseError: If table creation fails.
        """
        try:
            from cardlink.database.models import Base

            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            raise DatabaseError(
                f"Failed to create tables: {e}",
                cause=e,
            ) from e

    def drop_tables(self) -> None:
        """Drop all tables defined in models.

        WARNING: This permanently deletes all data!

        Raises:
            DatabaseError: If table drop fails.
        """
        try:
            from cardlink.database.models import Base

            Base.metadata.drop_all(self.engine)
            logger.warning("Database tables dropped")
        except Exception as e:
            raise DatabaseError(
                f"Failed to drop tables: {e}",
                cause=e,
            ) from e

    def close(self) -> None:
        """Close database connections and dispose of engine.

        Safe to call multiple times. After calling close(),
        the manager can be re-initialized with initialize().
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            logger.info("Database connections closed")

    def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity.

        Performs a simple SELECT 1 query to verify the database
        is accessible and responding.

        Returns:
            Dictionary with health status:
            - status: 'healthy' or 'unhealthy'
            - backend: Database backend name
            - url: Redacted connection URL
            - error: Error message (if unhealthy)
        """
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))

            return {
                "status": "healthy",
                "backend": self.config.backend_name,
                "database": self.config.database_name,
                "url": self.config.safe_url,
            }
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return {
                "status": "unhealthy",
                "backend": self.config.backend_name,
                "url": self.config.safe_url,
                "error": str(e),
            }

    def get_table_names(self) -> list:
        """Get list of table names in the database.

        Returns:
            List of table names.
        """
        from sqlalchemy import inspect

        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        status = "initialized" if self._initialized else "not initialized"
        return f"DatabaseManager({self.config.safe_url}, {status})"
