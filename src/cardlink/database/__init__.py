"""Database layer for GP OTA Tester.

This package provides database functionality including:
- SQLAlchemy ORM models
- Repository pattern for data access
- Unit of Work for transaction management
- Support for SQLite, MySQL, and PostgreSQL backends

Quick Start:
    >>> from cardlink.database import (
    ...     DatabaseConfig,
    ...     DatabaseManager,
    ...     UnitOfWork,
    ... )
    >>>
    >>> # Create manager with default SQLite
    >>> manager = DatabaseManager()
    >>> manager.initialize()
    >>> manager.create_tables()
    >>>
    >>> # Use Unit of Work for transactions
    >>> with UnitOfWork(manager) as uow:
    ...     device = Device(id="RF8M33XXXXX", device_type=DeviceType.PHONE)
    ...     uow.devices.create(device)
    ...     uow.commit()

Environment Variables:
    DATABASE_URL: Full database URL (overrides all other settings)
    CARDLINK_DB_HOST: Database host
    CARDLINK_DB_PORT: Database port
    CARDLINK_DB_NAME: Database name
    CARDLINK_DB_USER: Database username
    CARDLINK_DB_PASSWORD: Database password
    CARDLINK_DB_DRIVER: Database driver (mysql, postgresql, sqlite)
"""

from cardlink.database.config import DatabaseConfig
from cardlink.database.exceptions import (
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    EncryptionError,
    IntegrityError,
    MigrationError,
    NotFoundError,
    ValidationError,
)
from cardlink.database.manager import DatabaseManager
from cardlink.database.models import (
    Base,
    CardProfile,
    CardType,
    CommDirection,
    CommLog,
    Device,
    DeviceType,
    OTASession,
    SessionStatus,
    Setting,
    SettingKeys,
    SoftDeleteMixin,
    TestResult,
    TestStatus,
    TimestampMixin,
    generate_uuid,
)
from cardlink.database.repositories import (
    BaseRepository,
    CardRepository,
    DeviceRepository,
    LogRepository,
    Page,
    SessionRepository,
    SettingRepository,
    TestRepository,
)
from cardlink.database.unit_of_work import UnitOfWork
from cardlink.database.events import (
    DatabaseEvent,
    DatabaseEventEmitter,
    EventType,
    get_emitter,
    set_emitter,
)
from cardlink.database.export_import import (
    ConflictMode,
    DataExporter,
    DataImporter,
    ExportFormat,
    ImportResult,
)
from cardlink.database.migrate import (
    run_migrations,
    downgrade,
    get_current_revision,
    get_pending_revisions,
    get_migration_history,
    stamp,
)

__all__ = [
    # Configuration
    "DatabaseConfig",
    "DatabaseManager",
    "UnitOfWork",
    # Exceptions
    "DatabaseError",
    "ConnectionError",
    "MigrationError",
    "IntegrityError",
    "NotFoundError",
    "ValidationError",
    "EncryptionError",
    "ConfigurationError",
    # Base Model
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid",
    # Enums
    "DeviceType",
    "SessionStatus",
    "TestStatus",
    "CommDirection",
    "CardType",
    # Models
    "Device",
    "CardProfile",
    "OTASession",
    "CommLog",
    "TestResult",
    "Setting",
    "SettingKeys",
    # Repositories
    "BaseRepository",
    "Page",
    "DeviceRepository",
    "CardRepository",
    "SessionRepository",
    "LogRepository",
    "TestRepository",
    "SettingRepository",
    # Events
    "DatabaseEvent",
    "DatabaseEventEmitter",
    "EventType",
    "get_emitter",
    "set_emitter",
    # Export/Import
    "DataExporter",
    "DataImporter",
    "ExportFormat",
    "ConflictMode",
    "ImportResult",
    # Migrations
    "run_migrations",
    "downgrade",
    "get_current_revision",
    "get_pending_revisions",
    "get_migration_history",
    "stamp",
]
