# Design Document: Database Layer

## Introduction

This document describes the technical design for the Database Layer component of CardLink. The database layer provides persistent storage using SQLAlchemy ORM with support for SQLite, MySQL, and PostgreSQL backends, implementing the repository pattern for clean data access.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                               │
│         (PSK-TLS Server, Phone Controller, Modem Controller, etc.)          │
├─────────────────────────────────────────────────────────────────────────────┤
│                            Repository Layer                                  │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │DeviceRepository│ │CardRepository │ │SessionRepository│ │LogRepository │   │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                      │
│  │TestRepository │ │SettingsRepo   │ │ QueryBuilder  │                      │
│  └───────────────┘ └───────────────┘ └───────────────┘                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Unit of Work Layer                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        UnitOfWork                                    │   │
│  │  - Transaction management                                            │   │
│  │  - Session lifecycle                                                 │   │
│  │  - Repository factory                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                             Model Layer                                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │  Device   │ │CardProfile│ │  Session  │ │CommLog    │ │TestResult │    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
│  ┌───────────┐ ┌───────────┐                                               │
│  │  Setting  │ │ BaseModel │                                               │
│  └───────────┘ └───────────┘                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                            Database Engine                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      DatabaseManager                                 │   │
│  │  - Connection management                                             │   │
│  │  - Engine configuration                                              │   │
│  │  - Session factory                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Migration Layer                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Alembic Migrations                               │   │
│  │  - Version control                                                   │   │
│  │  - Schema upgrades/downgrades                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                          Database Backends                                   │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐              │
│  │    SQLite     │    │     MySQL     │    │  PostgreSQL   │              │
│  │  (Default)    │    │   (Team)      │    │ (Enterprise)  │              │
│  └───────────────┘    └───────────────┘    └───────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility |
|-----------|----------------|
| **DatabaseManager** | Connection management, engine configuration, session factory |
| **UnitOfWork** | Transaction management, repository access, commit/rollback |
| **BaseModel** | SQLAlchemy declarative base with common fields |
| **Device** | Phone and modem device configuration model |
| **CardProfile** | UICC card profile model with encrypted PSK |
| **Session** | OTA session record model |
| **CommLog** | Communication log entry model |
| **TestResult** | Test execution result model |
| **Setting** | Server configuration setting model |
| **DeviceRepository** | Device CRUD operations |
| **CardRepository** | Card profile CRUD operations |
| **SessionRepository** | Session CRUD and queries |
| **LogRepository** | Communication log operations |
| **TestRepository** | Test result operations |
| **SettingsRepository** | Settings CRUD operations |
| **QueryBuilder** | Dynamic query construction |

## Component Design

### 1. DatabaseManager

Manages database connections and session lifecycle.

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from contextlib import contextmanager
from typing import Optional, Generator
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration."""

    def __init__(self,
                 url: Optional[str] = None,
                 pool_size: int = 5,
                 max_overflow: int = 10,
                 pool_timeout: int = 30,
                 echo: bool = False):
        self.url = url or os.environ.get('DATABASE_URL', 'sqlite:///data/cardlink.db')
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.echo = echo

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith('sqlite')

    @property
    def is_mysql(self) -> bool:
        return self.url.startswith('mysql')

    @property
    def is_postgresql(self) -> bool:
        return self.url.startswith('postgresql')


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine = None
        self._session_factory = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return

        engine_kwargs = {
            'echo': self.config.echo
        }

        # Configure pool based on backend
        if self.config.is_sqlite:
            # SQLite uses NullPool for thread safety
            engine_kwargs['poolclass'] = NullPool
            # Ensure directory exists
            self._ensure_sqlite_directory()
        else:
            # MySQL/PostgreSQL use connection pooling
            engine_kwargs['poolclass'] = QueuePool
            engine_kwargs['pool_size'] = self.config.pool_size
            engine_kwargs['max_overflow'] = self.config.max_overflow
            engine_kwargs['pool_timeout'] = self.config.pool_timeout

        self._engine = create_engine(self.config.url, **engine_kwargs)

        # Configure SQLite for better concurrency
        if self.config.is_sqlite:
            self._configure_sqlite()

        self._session_factory = sessionmaker(bind=self._engine)
        self._initialized = True

        logger.info(f"Database initialized: {self._get_safe_url()}")

    def _ensure_sqlite_directory(self) -> None:
        """Create SQLite database directory if needed."""
        if ':///' in self.config.url:
            db_path = self.config.url.split(':///')[-1]
            if db_path != ':memory:':
                os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

    def _configure_sqlite(self) -> None:
        """Configure SQLite for optimal performance."""
        @event.listens_for(self._engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable WAL mode for concurrent reads
            cursor.execute('PRAGMA journal_mode=WAL')
            # Enable foreign keys
            cursor.execute('PRAGMA foreign_keys=ON')
            # Optimize synchronous mode
            cursor.execute('PRAGMA synchronous=NORMAL')
            # Increase cache size
            cursor.execute('PRAGMA cache_size=-64000')  # 64MB
            cursor.close()

    def _get_safe_url(self) -> str:
        """Get URL with password redacted."""
        url = self.config.url
        if '@' in url:
            # Redact password
            parts = url.split('@')
            prefix = parts[0].rsplit(':', 1)[0]
            return f"{prefix}:***@{parts[1]}"
        return url

    @property
    def engine(self):
        """Get database engine."""
        if not self._initialized:
            self.initialize()
        return self._engine

    def create_session(self) -> Session:
        """Create a new database session."""
        if not self._initialized:
            self.initialize()
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around operations."""
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """Create all tables defined in models."""
        from .models import Base
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def drop_tables(self) -> None:
        """Drop all tables (use with caution)."""
        from .models import Base
        Base.metadata.drop_all(self.engine)
        logger.warning("Database tables dropped")

    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")

    def health_check(self) -> dict:
        """Check database health."""
        try:
            with self.session_scope() as session:
                session.execute('SELECT 1')
            return {
                'status': 'healthy',
                'backend': self._get_backend_name(),
                'url': self._get_safe_url()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def _get_backend_name(self) -> str:
        """Get human-readable backend name."""
        if self.config.is_sqlite:
            return 'SQLite'
        elif self.config.is_mysql:
            return 'MySQL'
        elif self.config.is_postgresql:
            return 'PostgreSQL'
        return 'Unknown'
```

### 2. Model Definitions

SQLAlchemy models for all entities.

```python
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, Index, JSON, LargeBinary
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import enum
import uuid

Base = declarative_base()

def generate_uuid() -> str:
    """Generate UUID string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin for created/updated timestamps."""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class DeviceType(enum.Enum):
    """Device type enumeration."""
    PHONE = 'phone'
    MODEM = 'modem'


class SessionStatus(enum.Enum):
    """OTA session status enumeration."""
    PENDING = 'pending'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'


class TestStatus(enum.Enum):
    """Test result status enumeration."""
    PASSED = 'passed'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    ERROR = 'error'


class Device(Base, TimestampMixin):
    """Device configuration model (phones and modems)."""

    __tablename__ = 'devices'

    id = Column(String(64), primary_key=True)  # ADB serial or serial port
    name = Column(String(128), nullable=True)  # User-friendly alias
    device_type = Column(Enum(DeviceType), nullable=False)

    # Device info
    manufacturer = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    firmware_version = Column(String(64), nullable=True)

    # Identifiers
    imei = Column(String(20), nullable=True)
    imsi = Column(String(20), nullable=True)
    iccid = Column(String(22), nullable=True)

    # Connection settings (JSON for flexibility)
    connection_settings = Column(JSON, nullable=True)

    # Status
    last_seen = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    sessions = relationship('OTASession', back_populates='device')
    test_results = relationship('TestResult', back_populates='device')

    __table_args__ = (
        Index('idx_device_type', 'device_type'),
        Index('idx_device_iccid', 'iccid'),
        Index('idx_device_last_seen', 'last_seen'),
    )


class CardProfile(Base, TimestampMixin):
    """UICC card profile model."""

    __tablename__ = 'card_profiles'

    iccid = Column(String(22), primary_key=True)
    imsi = Column(String(20), nullable=True)
    card_type = Column(String(20), default='UICC')  # UICC, USIM, eUICC
    atr = Column(String(128), nullable=True)  # Hex encoded

    # PSK configuration
    psk_identity = Column(String(128), nullable=True)
    psk_key_encrypted = Column(LargeBinary, nullable=True)  # Encrypted key

    # Server configuration
    admin_url = Column(String(255), nullable=True)

    # Trigger configuration (JSON)
    trigger_config = Column(JSON, nullable=True)

    # BIP configuration (JSON)
    bip_config = Column(JSON, nullable=True)

    # Security Domain info (JSON)
    security_domains = Column(JSON, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    sessions = relationship('OTASession', back_populates='card')
    test_results = relationship('TestResult', back_populates='card')

    __table_args__ = (
        Index('idx_card_type', 'card_type'),
        Index('idx_card_psk_identity', 'psk_identity'),
    )


class OTASession(Base, TimestampMixin):
    """OTA session record model."""

    __tablename__ = 'ota_sessions'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_id = Column(String(64), ForeignKey('devices.id'), nullable=True)
    card_iccid = Column(String(22), ForeignKey('card_profiles.iccid'), nullable=True)

    # Session info
    session_type = Column(String(20), nullable=True)  # triggered, polled
    status = Column(Enum(SessionStatus), default=SessionStatus.PENDING)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # TLS info
    tls_cipher_suite = Column(String(64), nullable=True)
    tls_psk_identity = Column(String(128), nullable=True)

    # Error info
    error_code = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    device = relationship('Device', back_populates='sessions')
    card = relationship('CardProfile', back_populates='sessions')
    comm_logs = relationship('CommLog', back_populates='session', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_session_device', 'device_id'),
        Index('idx_session_card', 'card_iccid'),
        Index('idx_session_status', 'status'),
        Index('idx_session_created', 'created_at'),
    )


class CommLog(Base):
    """Communication log entry model."""

    __tablename__ = 'comm_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('ota_sessions.id'), nullable=False)

    # Timing
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    latency_ms = Column(Float, nullable=True)

    # Data
    direction = Column(String(10), nullable=False)  # command, response
    raw_data = Column(Text, nullable=False)  # Hex encoded
    decoded_data = Column(Text, nullable=True)

    # Response info
    status_word = Column(String(4), nullable=True)  # Hex SW1SW2
    status_message = Column(String(128), nullable=True)

    # Relationships
    session = relationship('OTASession', back_populates='comm_logs')

    __table_args__ = (
        Index('idx_log_session', 'session_id'),
        Index('idx_log_timestamp', 'timestamp'),
        Index('idx_log_direction', 'direction'),
    )


class TestResult(Base, TimestampMixin):
    """Test execution result model."""

    __tablename__ = 'test_results'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), nullable=False)  # Groups results by test run

    # Test info
    suite_name = Column(String(128), nullable=False)
    test_name = Column(String(256), nullable=False)

    # Device and card
    device_id = Column(String(64), ForeignKey('devices.id'), nullable=True)
    card_iccid = Column(String(22), ForeignKey('card_profiles.iccid'), nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Result
    status = Column(Enum(TestStatus), nullable=False)
    error_message = Column(Text, nullable=True)

    # Details (JSON)
    assertions = Column(JSON, nullable=True)  # Array of assertion results
    metadata = Column(JSON, nullable=True)  # Additional test metadata

    # Relationships
    device = relationship('Device', back_populates='test_results')
    card = relationship('CardProfile', back_populates='test_results')

    __table_args__ = (
        Index('idx_test_run', 'run_id'),
        Index('idx_test_suite', 'suite_name'),
        Index('idx_test_status', 'status'),
        Index('idx_test_created', 'created_at'),
    )


class Setting(Base, TimestampMixin):
    """Server configuration setting model."""

    __tablename__ = 'settings'

    key = Column(String(128), primary_key=True)
    value = Column(JSON, nullable=True)
    description = Column(String(256), nullable=True)
    category = Column(String(64), default='general')

    __table_args__ = (
        Index('idx_setting_category', 'category'),
    )
```

### 3. Unit of Work

Transaction management and repository factory.

```python
from typing import TypeVar, Type, Optional
from sqlalchemy.orm import Session

T = TypeVar('T')

class UnitOfWork:
    """Unit of Work pattern implementation."""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager
        self._session: Optional[Session] = None
        self._repositories: dict = {}

    def __enter__(self) -> 'UnitOfWork':
        self._session = self._db_manager.create_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.close()

    @property
    def session(self) -> Session:
        """Get current session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        return self._session

    def commit(self) -> None:
        """Commit current transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self._session.rollback()

    def close(self) -> None:
        """Close session."""
        if self._session:
            self._session.close()
            self._session = None
            self._repositories.clear()

    def _get_repository(self, repo_class: Type[T]) -> T:
        """Get or create repository instance."""
        if repo_class not in self._repositories:
            self._repositories[repo_class] = repo_class(self._session)
        return self._repositories[repo_class]

    @property
    def devices(self) -> 'DeviceRepository':
        """Device repository."""
        return self._get_repository(DeviceRepository)

    @property
    def cards(self) -> 'CardRepository':
        """Card profile repository."""
        return self._get_repository(CardRepository)

    @property
    def sessions(self) -> 'SessionRepository':
        """Session repository."""
        return self._get_repository(SessionRepository)

    @property
    def logs(self) -> 'LogRepository':
        """Communication log repository."""
        return self._get_repository(LogRepository)

    @property
    def tests(self) -> 'TestRepository':
        """Test result repository."""
        return self._get_repository(TestRepository)

    @property
    def settings(self) -> 'SettingsRepository':
        """Settings repository."""
        return self._get_repository(SettingsRepository)
```

### 4. Base Repository

Generic repository implementation.

```python
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Page:
    """Pagination result."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        self._session = session
        self._model_class = model_class

    def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by primary key."""
        return self._session.get(self._model_class, id)

    def get_all(self, limit: Optional[int] = None) -> List[T]:
        """Get all entities with optional limit."""
        query = self._session.query(self._model_class)
        if limit:
            query = query.limit(limit)
        return query.all()

    def find_by(self, **kwargs) -> List[T]:
        """Find entities by attributes."""
        query = self._session.query(self._model_class)
        for key, value in kwargs.items():
            if hasattr(self._model_class, key):
                query = query.filter(getattr(self._model_class, key) == value)
        return query.all()

    def find_one_by(self, **kwargs) -> Optional[T]:
        """Find single entity by attributes."""
        results = self.find_by(**kwargs)
        return results[0] if results else None

    def create(self, entity: T) -> T:
        """Create new entity."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def create_all(self, entities: List[T]) -> List[T]:
        """Create multiple entities."""
        self._session.add_all(entities)
        self._session.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update existing entity."""
        self._session.merge(entity)
        self._session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity."""
        self._session.delete(entity)
        self._session.flush()

    def delete_by_id(self, id: Any) -> bool:
        """Delete entity by ID."""
        entity = self.get_by_id(id)
        if entity:
            self.delete(entity)
            return True
        return False

    def exists(self, id: Any) -> bool:
        """Check if entity exists."""
        return self.get_by_id(id) is not None

    def count(self) -> int:
        """Count all entities."""
        return self._session.query(self._model_class).count()

    def count_by(self, **kwargs) -> int:
        """Count entities matching criteria."""
        query = self._session.query(self._model_class)
        for key, value in kwargs.items():
            if hasattr(self._model_class, key):
                query = query.filter(getattr(self._model_class, key) == value)
        return query.count()

    def paginate(self, page: int = 1, per_page: int = 20,
                 order_by: Optional[str] = None,
                 descending: bool = False) -> Page:
        """Get paginated results."""
        query = self._session.query(self._model_class)

        # Apply ordering
        if order_by and hasattr(self._model_class, order_by):
            column = getattr(self._model_class, order_by)
            query = query.order_by(column.desc() if descending else column)

        # Count total
        total = query.count()

        # Calculate pagination
        pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page

        # Fetch items
        items = query.offset(offset).limit(per_page).all()

        return Page(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
```

### 5. Device Repository

Device-specific repository operations.

```python
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import or_

class DeviceRepository(BaseRepository[Device]):
    """Repository for device operations."""

    def __init__(self, session: Session):
        super().__init__(session, Device)

    def find_by_type(self, device_type: DeviceType) -> List[Device]:
        """Find devices by type."""
        return self._session.query(Device).filter(
            Device.device_type == device_type
        ).all()

    def find_phones(self) -> List[Device]:
        """Find all phone devices."""
        return self.find_by_type(DeviceType.PHONE)

    def find_modems(self) -> List[Device]:
        """Find all modem devices."""
        return self.find_by_type(DeviceType.MODEM)

    def find_active(self) -> List[Device]:
        """Find all active devices."""
        return self._session.query(Device).filter(
            Device.is_active == True
        ).all()

    def find_recent(self, hours: int = 24) -> List[Device]:
        """Find devices seen recently."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self._session.query(Device).filter(
            Device.last_seen >= cutoff
        ).all()

    def search(self, query: str) -> List[Device]:
        """Search devices by name or ID."""
        pattern = f'%{query}%'
        return self._session.query(Device).filter(
            or_(
                Device.id.ilike(pattern),
                Device.name.ilike(pattern),
                Device.model.ilike(pattern)
            )
        ).all()

    def update_last_seen(self, device_id: str) -> None:
        """Update device last seen timestamp."""
        self._session.query(Device).filter(
            Device.id == device_id
        ).update({'last_seen': datetime.utcnow()})

    def find_by_iccid(self, iccid: str) -> List[Device]:
        """Find devices with specific ICCID."""
        return self._session.query(Device).filter(
            Device.iccid == iccid
        ).all()

    def deactivate(self, device_id: str) -> bool:
        """Deactivate a device."""
        result = self._session.query(Device).filter(
            Device.id == device_id
        ).update({'is_active': False})
        return result > 0
```

### 6. Card Repository

Card profile repository with encryption support.

```python
from typing import List, Optional
from cryptography.fernet import Fernet
import os

class CardRepository(BaseRepository[CardProfile]):
    """Repository for card profile operations."""

    def __init__(self, session: Session, encryption_key: Optional[bytes] = None):
        super().__init__(session, CardProfile)
        self._encryption_key = encryption_key or self._get_encryption_key()
        self._cipher = Fernet(self._encryption_key) if self._encryption_key else None

    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key from environment."""
        key = os.environ.get('CARDLINK_ENCRYPTION_KEY')
        if key:
            return key.encode()
        return None

    def create_with_psk(self, profile: CardProfile, psk_key: bytes) -> CardProfile:
        """Create profile with encrypted PSK key."""
        if self._cipher:
            profile.psk_key_encrypted = self._cipher.encrypt(psk_key)
        else:
            # Warning: storing without encryption
            profile.psk_key_encrypted = psk_key
        return self.create(profile)

    def get_psk_key(self, iccid: str) -> Optional[bytes]:
        """Get decrypted PSK key."""
        profile = self.get_by_id(iccid)
        if profile and profile.psk_key_encrypted:
            if self._cipher:
                return self._cipher.decrypt(profile.psk_key_encrypted)
            return profile.psk_key_encrypted
        return None

    def update_psk(self, iccid: str, psk_identity: str, psk_key: bytes) -> bool:
        """Update PSK configuration."""
        profile = self.get_by_id(iccid)
        if not profile:
            return False

        profile.psk_identity = psk_identity
        if self._cipher:
            profile.psk_key_encrypted = self._cipher.encrypt(psk_key)
        else:
            profile.psk_key_encrypted = psk_key

        self._session.flush()
        return True

    def find_by_type(self, card_type: str) -> List[CardProfile]:
        """Find profiles by card type."""
        return self._session.query(CardProfile).filter(
            CardProfile.card_type == card_type
        ).all()

    def find_with_psk(self) -> List[CardProfile]:
        """Find profiles with PSK configured."""
        return self._session.query(CardProfile).filter(
            CardProfile.psk_identity.isnot(None)
        ).all()

    def find_by_admin_url(self, url: str) -> List[CardProfile]:
        """Find profiles by admin URL."""
        return self._session.query(CardProfile).filter(
            CardProfile.admin_url == url
        ).all()

    def export_profile(self, iccid: str, include_key: bool = False) -> Optional[dict]:
        """Export profile as dictionary."""
        profile = self.get_by_id(iccid)
        if not profile:
            return None

        data = {
            'iccid': profile.iccid,
            'imsi': profile.imsi,
            'card_type': profile.card_type,
            'atr': profile.atr,
            'psk_identity': profile.psk_identity,
            'admin_url': profile.admin_url,
            'trigger_config': profile.trigger_config,
            'bip_config': profile.bip_config,
            'notes': profile.notes
        }

        if include_key and profile.psk_key_encrypted:
            key = self.get_psk_key(iccid)
            if key:
                data['psk_key'] = key.hex()

        return data
```

### 7. Session Repository

OTA session repository with query capabilities.

```python
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_

class SessionRepository(BaseRepository[OTASession]):
    """Repository for OTA session operations."""

    def __init__(self, session: Session):
        super().__init__(session, OTASession)

    def create_session(self, device_id: str = None,
                      card_iccid: str = None,
                      session_type: str = None) -> OTASession:
        """Create new OTA session."""
        ota_session = OTASession(
            device_id=device_id,
            card_iccid=card_iccid,
            session_type=session_type,
            status=SessionStatus.PENDING
        )
        return self.create(ota_session)

    def start_session(self, session_id: str) -> bool:
        """Mark session as started."""
        result = self._session.query(OTASession).filter(
            OTASession.id == session_id
        ).update({
            'status': SessionStatus.ACTIVE,
            'started_at': datetime.utcnow()
        })
        return result > 0

    def complete_session(self, session_id: str) -> bool:
        """Mark session as completed."""
        ota_session = self.get_by_id(session_id)
        if not ota_session:
            return False

        now = datetime.utcnow()
        duration = None
        if ota_session.started_at:
            duration = int((now - ota_session.started_at).total_seconds() * 1000)

        self._session.query(OTASession).filter(
            OTASession.id == session_id
        ).update({
            'status': SessionStatus.COMPLETED,
            'ended_at': now,
            'duration_ms': duration
        })
        return True

    def fail_session(self, session_id: str, error_code: str,
                    error_message: str) -> bool:
        """Mark session as failed."""
        ota_session = self.get_by_id(session_id)
        if not ota_session:
            return False

        now = datetime.utcnow()
        duration = None
        if ota_session.started_at:
            duration = int((now - ota_session.started_at).total_seconds() * 1000)

        self._session.query(OTASession).filter(
            OTASession.id == session_id
        ).update({
            'status': SessionStatus.FAILED,
            'ended_at': now,
            'duration_ms': duration,
            'error_code': error_code,
            'error_message': error_message
        })
        return True

    def set_tls_info(self, session_id: str, cipher_suite: str,
                    psk_identity: str) -> bool:
        """Set TLS session information."""
        result = self._session.query(OTASession).filter(
            OTASession.id == session_id
        ).update({
            'tls_cipher_suite': cipher_suite,
            'tls_psk_identity': psk_identity
        })
        return result > 0

    def find_by_device(self, device_id: str,
                      limit: int = 100) -> List[OTASession]:
        """Find sessions for device."""
        return self._session.query(OTASession).filter(
            OTASession.device_id == device_id
        ).order_by(OTASession.created_at.desc()).limit(limit).all()

    def find_by_card(self, iccid: str, limit: int = 100) -> List[OTASession]:
        """Find sessions for card."""
        return self._session.query(OTASession).filter(
            OTASession.card_iccid == iccid
        ).order_by(OTASession.created_at.desc()).limit(limit).all()

    def find_by_status(self, status: SessionStatus) -> List[OTASession]:
        """Find sessions by status."""
        return self._session.query(OTASession).filter(
            OTASession.status == status
        ).all()

    def find_active(self) -> List[OTASession]:
        """Find currently active sessions."""
        return self.find_by_status(SessionStatus.ACTIVE)

    def find_by_date_range(self, start: datetime,
                          end: datetime) -> List[OTASession]:
        """Find sessions in date range."""
        return self._session.query(OTASession).filter(
            and_(
                OTASession.created_at >= start,
                OTASession.created_at <= end
            )
        ).order_by(OTASession.created_at.desc()).all()

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get session statistics."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total sessions
        total = self._session.query(OTASession).filter(
            OTASession.created_at >= cutoff
        ).count()

        # By status
        by_status = {}
        for status in SessionStatus:
            count = self._session.query(OTASession).filter(
                and_(
                    OTASession.created_at >= cutoff,
                    OTASession.status == status
                )
            ).count()
            by_status[status.value] = count

        # Average duration for completed
        avg_duration = self._session.query(
            func.avg(OTASession.duration_ms)
        ).filter(
            and_(
                OTASession.created_at >= cutoff,
                OTASession.status == SessionStatus.COMPLETED
            )
        ).scalar()

        # Success rate
        completed = by_status.get('completed', 0)
        failed = by_status.get('failed', 0)
        success_rate = completed / (completed + failed) if (completed + failed) > 0 else 0

        return {
            'period_days': days,
            'total_sessions': total,
            'by_status': by_status,
            'avg_duration_ms': avg_duration,
            'success_rate': success_rate
        }
```

### 8. Log Repository

Communication log repository with batch operations.

```python
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_

class LogRepository(BaseRepository[CommLog]):
    """Repository for communication log operations."""

    def __init__(self, session: Session):
        super().__init__(session, CommLog)
        self._batch: List[CommLog] = []
        self._batch_size = 100

    def add_log(self, session_id: str, direction: str, raw_data: str,
                decoded_data: str = None, status_word: str = None,
                status_message: str = None, latency_ms: float = None) -> CommLog:
        """Add single log entry."""
        log = CommLog(
            session_id=session_id,
            direction=direction,
            raw_data=raw_data,
            decoded_data=decoded_data,
            status_word=status_word,
            status_message=status_message,
            latency_ms=latency_ms
        )
        return self.create(log)

    def add_log_batch(self, session_id: str, direction: str, raw_data: str,
                      **kwargs) -> None:
        """Add log to batch (for high-throughput logging)."""
        log = CommLog(
            session_id=session_id,
            direction=direction,
            raw_data=raw_data,
            **kwargs
        )
        self._batch.append(log)

        if len(self._batch) >= self._batch_size:
            self.flush_batch()

    def flush_batch(self) -> int:
        """Flush batch to database."""
        if not self._batch:
            return 0

        count = len(self._batch)
        self._session.bulk_save_objects(self._batch)
        self._session.flush()
        self._batch.clear()
        return count

    def find_by_session(self, session_id: str) -> List[CommLog]:
        """Find all logs for session."""
        return self._session.query(CommLog).filter(
            CommLog.session_id == session_id
        ).order_by(CommLog.timestamp).all()

    def find_by_direction(self, session_id: str,
                         direction: str) -> List[CommLog]:
        """Find logs by direction."""
        return self._session.query(CommLog).filter(
            and_(
                CommLog.session_id == session_id,
                CommLog.direction == direction
            )
        ).order_by(CommLog.timestamp).all()

    def find_commands(self, session_id: str) -> List[CommLog]:
        """Find command logs."""
        return self.find_by_direction(session_id, 'command')

    def find_responses(self, session_id: str) -> List[CommLog]:
        """Find response logs."""
        return self.find_by_direction(session_id, 'response')

    def find_by_status(self, session_id: str, status_word: str) -> List[CommLog]:
        """Find logs by status word."""
        return self._session.query(CommLog).filter(
            and_(
                CommLog.session_id == session_id,
                CommLog.status_word == status_word
            )
        ).all()

    def find_errors(self, session_id: str) -> List[CommLog]:
        """Find error responses (non-9000 status)."""
        return self._session.query(CommLog).filter(
            and_(
                CommLog.session_id == session_id,
                CommLog.direction == 'response',
                CommLog.status_word.isnot(None),
                CommLog.status_word != '9000'
            )
        ).all()

    def search_hex(self, pattern: str,
                  session_id: str = None) -> List[CommLog]:
        """Search logs by hex pattern."""
        query = self._session.query(CommLog).filter(
            CommLog.raw_data.ilike(f'%{pattern}%')
        )
        if session_id:
            query = query.filter(CommLog.session_id == session_id)
        return query.all()

    def purge_old(self, days: int) -> int:
        """Delete logs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = self._session.query(CommLog).filter(
            CommLog.timestamp < cutoff
        ).delete()
        return result

    def count_by_session(self, session_id: str) -> int:
        """Count logs for session."""
        return self._session.query(CommLog).filter(
            CommLog.session_id == session_id
        ).count()

    def export_session_logs(self, session_id: str) -> List[dict]:
        """Export logs as dictionaries."""
        logs = self.find_by_session(session_id)
        return [
            {
                'timestamp': log.timestamp.isoformat(),
                'direction': log.direction,
                'raw_data': log.raw_data,
                'decoded_data': log.decoded_data,
                'status_word': log.status_word,
                'status_message': log.status_message,
                'latency_ms': log.latency_ms
            }
            for log in logs
        ]
```

### 9. Test Repository

Test result repository with reporting capabilities.

```python
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import xml.etree.ElementTree as ET

class TestRepository(BaseRepository[TestResult]):
    """Repository for test result operations."""

    def __init__(self, session: Session):
        super().__init__(session, TestResult)

    def create_result(self, run_id: str, suite_name: str, test_name: str,
                     status: TestStatus, started_at: datetime,
                     device_id: str = None, card_iccid: str = None,
                     ended_at: datetime = None, duration_ms: int = None,
                     error_message: str = None, assertions: list = None,
                     metadata: dict = None) -> TestResult:
        """Create test result."""
        result = TestResult(
            run_id=run_id,
            suite_name=suite_name,
            test_name=test_name,
            device_id=device_id,
            card_iccid=card_iccid,
            status=status,
            started_at=started_at,
            ended_at=ended_at or datetime.utcnow(),
            duration_ms=duration_ms,
            error_message=error_message,
            assertions=assertions,
            metadata=metadata
        )
        return self.create(result)

    def find_by_run(self, run_id: str) -> List[TestResult]:
        """Find all results for a test run."""
        return self._session.query(TestResult).filter(
            TestResult.run_id == run_id
        ).order_by(TestResult.started_at).all()

    def find_by_suite(self, suite_name: str,
                     limit: int = 100) -> List[TestResult]:
        """Find results by suite."""
        return self._session.query(TestResult).filter(
            TestResult.suite_name == suite_name
        ).order_by(TestResult.created_at.desc()).limit(limit).all()

    def find_by_status(self, status: TestStatus) -> List[TestResult]:
        """Find results by status."""
        return self._session.query(TestResult).filter(
            TestResult.status == status
        ).all()

    def find_failures(self, run_id: str = None) -> List[TestResult]:
        """Find failed tests."""
        query = self._session.query(TestResult).filter(
            TestResult.status == TestStatus.FAILED
        )
        if run_id:
            query = query.filter(TestResult.run_id == run_id)
        return query.all()

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get summary for test run."""
        results = self.find_by_run(run_id)

        if not results:
            return {}

        summary = {
            'run_id': run_id,
            'total': len(results),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0,
            'duration_ms': 0,
            'started_at': None,
            'ended_at': None
        }

        for result in results:
            summary[result.status.value] += 1
            if result.duration_ms:
                summary['duration_ms'] += result.duration_ms

            if summary['started_at'] is None or result.started_at < summary['started_at']:
                summary['started_at'] = result.started_at
            if summary['ended_at'] is None or result.ended_at > summary['ended_at']:
                summary['ended_at'] = result.ended_at

        summary['pass_rate'] = summary['passed'] / summary['total'] if summary['total'] > 0 else 0

        return summary

    def compare_runs(self, run_id1: str, run_id2: str) -> Dict[str, Any]:
        """Compare two test runs for regressions."""
        results1 = {r.test_name: r for r in self.find_by_run(run_id1)}
        results2 = {r.test_name: r for r in self.find_by_run(run_id2)}

        regressions = []
        improvements = []
        new_tests = []
        removed_tests = []

        for name, r2 in results2.items():
            if name in results1:
                r1 = results1[name]
                if r1.status == TestStatus.PASSED and r2.status == TestStatus.FAILED:
                    regressions.append(name)
                elif r1.status == TestStatus.FAILED and r2.status == TestStatus.PASSED:
                    improvements.append(name)
            else:
                new_tests.append(name)

        for name in results1:
            if name not in results2:
                removed_tests.append(name)

        return {
            'regressions': regressions,
            'improvements': improvements,
            'new_tests': new_tests,
            'removed_tests': removed_tests
        }

    def export_junit_xml(self, run_id: str) -> str:
        """Export test run as JUnit XML."""
        results = self.find_by_run(run_id)

        # Group by suite
        suites: Dict[str, List[TestResult]] = {}
        for result in results:
            if result.suite_name not in suites:
                suites[result.suite_name] = []
            suites[result.suite_name].append(result)

        # Build XML
        testsuites = ET.Element('testsuites')

        for suite_name, suite_results in suites.items():
            testsuite = ET.SubElement(testsuites, 'testsuite')
            testsuite.set('name', suite_name)
            testsuite.set('tests', str(len(suite_results)))
            testsuite.set('failures', str(sum(1 for r in suite_results if r.status == TestStatus.FAILED)))
            testsuite.set('errors', str(sum(1 for r in suite_results if r.status == TestStatus.ERROR)))
            testsuite.set('skipped', str(sum(1 for r in suite_results if r.status == TestStatus.SKIPPED)))

            total_time = sum(r.duration_ms or 0 for r in suite_results) / 1000
            testsuite.set('time', f'{total_time:.3f}')

            for result in suite_results:
                testcase = ET.SubElement(testsuite, 'testcase')
                testcase.set('name', result.test_name)
                testcase.set('classname', suite_name)
                if result.duration_ms:
                    testcase.set('time', f'{result.duration_ms / 1000:.3f}')

                if result.status == TestStatus.FAILED:
                    failure = ET.SubElement(testcase, 'failure')
                    if result.error_message:
                        failure.set('message', result.error_message)
                elif result.status == TestStatus.ERROR:
                    error = ET.SubElement(testcase, 'error')
                    if result.error_message:
                        error.set('message', result.error_message)
                elif result.status == TestStatus.SKIPPED:
                    ET.SubElement(testcase, 'skipped')

        return ET.tostring(testsuites, encoding='unicode', xml_declaration=True)
```

### 10. Settings Repository

Settings repository with defaults and validation.

```python
from typing import Any, Dict, Optional, List
import json
import yaml

class SettingsRepository(BaseRepository[Setting]):
    """Repository for settings operations."""

    DEFAULTS = {
        'server.port': 8443,
        'server.timeout': 60,
        'dashboard.port': 8080,
        'dashboard.enabled': True,
        'metrics.port': 9090,
        'metrics.enabled': True,
        'retention.logs_days': 30,
        'retention.sessions_days': 90,
    }

    def __init__(self, session: Session):
        super().__init__(session, Setting)

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get setting value with default."""
        setting = self.get_by_id(key)
        if setting and setting.value is not None:
            return setting.value
        return default if default is not None else self.DEFAULTS.get(key)

    def set_value(self, key: str, value: Any,
                  description: str = None,
                  category: str = 'general') -> Setting:
        """Set setting value."""
        setting = self.get_by_id(key)
        if setting:
            setting.value = value
            if description:
                setting.description = description
            if category:
                setting.category = category
            self._session.flush()
        else:
            setting = Setting(
                key=key,
                value=value,
                description=description,
                category=category
            )
            self.create(setting)
        return setting

    def get_by_category(self, category: str) -> Dict[str, Any]:
        """Get all settings in category."""
        settings = self._session.query(Setting).filter(
            Setting.category == category
        ).all()
        return {s.key: s.value for s in settings}

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as dictionary."""
        settings = self.get_all()
        result = dict(self.DEFAULTS)  # Start with defaults
        for setting in settings:
            result[setting.key] = setting.value
        return result

    def export_yaml(self) -> str:
        """Export settings as YAML."""
        settings = self.get_all_settings()
        return yaml.dump(settings, default_flow_style=False)

    def import_yaml(self, yaml_str: str) -> int:
        """Import settings from YAML."""
        data = yaml.safe_load(yaml_str)
        count = 0
        for key, value in data.items():
            self.set_value(key, value)
            count += 1
        return count

    def reset_to_defaults(self, category: str = None) -> int:
        """Reset settings to defaults."""
        if category:
            query = self._session.query(Setting).filter(
                Setting.category == category
            )
        else:
            query = self._session.query(Setting)

        count = query.delete()
        return count
```

### 11. Event Emitter Integration

Event emission for data changes.

```python
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import threading

@dataclass
class DatabaseEvent:
    """Database event data."""
    event_type: str
    entity_type: str
    entity_id: Any
    timestamp: str
    data: Dict[str, Any]


class DatabaseEventEmitter:
    """Event emitter for database changes."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def on(self, event_type: str, handler: Callable[[DatabaseEvent], None]) -> None:
        """Register event handler."""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable = None) -> None:
        """Remove event handler."""
        with self._lock:
            if event_type in self._handlers:
                if handler:
                    self._handlers[event_type].remove(handler)
                else:
                    del self._handlers[event_type]

    def emit(self, event_type: str, entity_type: str,
             entity_id: Any, data: Dict[str, Any] = None) -> None:
        """Emit database event."""
        event = DatabaseEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow().isoformat(),
            data=data or {}
        )

        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
            handlers += list(self._handlers.get('*', []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors break the flow
```

### 12. Data Export/Import

Export and import functionality.

```python
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import yaml
from datetime import datetime

class DataExporter:
    """Export database data."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def export_all(self, format: str = 'json') -> str:
        """Export all data."""
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'devices': self._export_devices(),
            'card_profiles': self._export_cards(),
            'sessions': self._export_sessions(),
            'settings': self._export_settings()
        }

        if format == 'yaml':
            return yaml.dump(data, default_flow_style=False)
        return json.dumps(data, indent=2, default=str)

    def export_selective(self, tables: List[str], format: str = 'json') -> str:
        """Export specific tables."""
        data = {'exported_at': datetime.utcnow().isoformat()}

        if 'devices' in tables:
            data['devices'] = self._export_devices()
        if 'card_profiles' in tables:
            data['card_profiles'] = self._export_cards()
        if 'sessions' in tables:
            data['sessions'] = self._export_sessions()
        if 'settings' in tables:
            data['settings'] = self._export_settings()

        if format == 'yaml':
            return yaml.dump(data, default_flow_style=False)
        return json.dumps(data, indent=2, default=str)

    def _export_devices(self) -> List[dict]:
        """Export devices."""
        with self._uow:
            devices = self._uow.devices.get_all()
            return [self._device_to_dict(d) for d in devices]

    def _export_cards(self) -> List[dict]:
        """Export card profiles (without keys)."""
        with self._uow:
            cards = self._uow.cards.get_all()
            return [self._uow.cards.export_profile(c.iccid, include_key=False)
                    for c in cards]

    def _export_sessions(self) -> List[dict]:
        """Export sessions."""
        with self._uow:
            sessions = self._uow.sessions.get_all(limit=1000)
            return [self._session_to_dict(s) for s in sessions]

    def _export_settings(self) -> Dict[str, Any]:
        """Export settings."""
        with self._uow:
            return self._uow.settings.get_all_settings()

    def _device_to_dict(self, device: Device) -> dict:
        """Convert device to dictionary."""
        return {
            'id': device.id,
            'name': device.name,
            'device_type': device.device_type.value,
            'manufacturer': device.manufacturer,
            'model': device.model,
            'imei': device.imei,
            'imsi': device.imsi,
            'iccid': device.iccid,
            'connection_settings': device.connection_settings,
            'notes': device.notes
        }

    def _session_to_dict(self, session: OTASession) -> dict:
        """Convert session to dictionary."""
        return {
            'id': session.id,
            'device_id': session.device_id,
            'card_iccid': session.card_iccid,
            'session_type': session.session_type,
            'status': session.status.value,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            'duration_ms': session.duration_ms,
            'tls_cipher_suite': session.tls_cipher_suite
        }


class DataImporter:
    """Import database data."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def import_data(self, data_str: str, format: str = 'json',
                   conflict_mode: str = 'skip') -> Dict[str, int]:
        """Import data from string."""
        if format == 'yaml':
            data = yaml.safe_load(data_str)
        else:
            data = json.loads(data_str)

        results = {
            'devices_created': 0,
            'devices_updated': 0,
            'devices_skipped': 0,
            'cards_created': 0,
            'cards_updated': 0,
            'cards_skipped': 0,
            'settings_updated': 0
        }

        with self._uow:
            if 'devices' in data:
                self._import_devices(data['devices'], conflict_mode, results)
            if 'card_profiles' in data:
                self._import_cards(data['card_profiles'], conflict_mode, results)
            if 'settings' in data:
                self._import_settings(data['settings'], results)

            self._uow.commit()

        return results

    def _import_devices(self, devices: List[dict],
                       conflict_mode: str, results: dict) -> None:
        """Import devices."""
        for device_data in devices:
            existing = self._uow.devices.get_by_id(device_data['id'])

            if existing:
                if conflict_mode == 'skip':
                    results['devices_skipped'] += 1
                elif conflict_mode == 'overwrite':
                    self._update_device(existing, device_data)
                    results['devices_updated'] += 1
            else:
                self._create_device(device_data)
                results['devices_created'] += 1

    def _import_cards(self, cards: List[dict],
                     conflict_mode: str, results: dict) -> None:
        """Import card profiles."""
        for card_data in cards:
            existing = self._uow.cards.get_by_id(card_data['iccid'])

            if existing:
                if conflict_mode == 'skip':
                    results['cards_skipped'] += 1
                elif conflict_mode == 'overwrite':
                    self._update_card(existing, card_data)
                    results['cards_updated'] += 1
            else:
                self._create_card(card_data)
                results['cards_created'] += 1

    def _import_settings(self, settings: Dict[str, Any], results: dict) -> None:
        """Import settings."""
        for key, value in settings.items():
            self._uow.settings.set_value(key, value)
            results['settings_updated'] += 1

    def _create_device(self, data: dict) -> None:
        """Create device from data."""
        device = Device(
            id=data['id'],
            name=data.get('name'),
            device_type=DeviceType(data['device_type']),
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            imei=data.get('imei'),
            imsi=data.get('imsi'),
            iccid=data.get('iccid'),
            connection_settings=data.get('connection_settings'),
            notes=data.get('notes')
        )
        self._uow.devices.create(device)

    def _update_device(self, device: Device, data: dict) -> None:
        """Update device from data."""
        device.name = data.get('name', device.name)
        device.manufacturer = data.get('manufacturer', device.manufacturer)
        device.model = data.get('model', device.model)
        device.connection_settings = data.get('connection_settings', device.connection_settings)
        device.notes = data.get('notes', device.notes)

    def _create_card(self, data: dict) -> None:
        """Create card profile from data."""
        profile = CardProfile(
            iccid=data['iccid'],
            imsi=data.get('imsi'),
            card_type=data.get('card_type', 'UICC'),
            atr=data.get('atr'),
            psk_identity=data.get('psk_identity'),
            admin_url=data.get('admin_url'),
            trigger_config=data.get('trigger_config'),
            bip_config=data.get('bip_config'),
            notes=data.get('notes')
        )
        self._uow.cards.create(profile)

    def _update_card(self, profile: CardProfile, data: dict) -> None:
        """Update card profile from data."""
        profile.imsi = data.get('imsi', profile.imsi)
        profile.atr = data.get('atr', profile.atr)
        profile.psk_identity = data.get('psk_identity', profile.psk_identity)
        profile.admin_url = data.get('admin_url', profile.admin_url)
        profile.trigger_config = data.get('trigger_config', profile.trigger_config)
        profile.bip_config = data.get('bip_config', profile.bip_config)
        profile.notes = data.get('notes', profile.notes)
```

## CLI Design

### Command Structure

```
cardlink-db
├── init                    # Initialize database
│   └── --force            # Drop existing tables first
├── migrate                 # Run migrations
│   ├── --revision <rev>   # Migrate to specific revision
│   └── --dry-run          # Show SQL without executing
├── status                  # Show database status
│   └── --verbose          # Include table details
├── export                  # Export data
│   ├── --format <fmt>     # json or yaml
│   ├── --tables <list>    # Comma-separated table names
│   └── --output <file>    # Output file path
├── import                  # Import data
│   ├── --format <fmt>     # json or yaml
│   ├── --conflict <mode>  # skip, overwrite, merge
│   └── <file>             # Input file
├── purge                   # Delete old data
│   ├── --older-than <days># Retention period
│   └── --tables <list>    # Tables to purge
└── stats                   # Show statistics
    └── --json             # JSON output
```

## Error Handling

```python
class DatabaseError(Exception):
    """Base database exception."""
    pass

class ConnectionError(DatabaseError):
    """Connection failed."""
    pass

class MigrationError(DatabaseError):
    """Migration failed."""
    pass

class IntegrityError(DatabaseError):
    """Data integrity violation."""
    pass

class NotFoundError(DatabaseError):
    """Entity not found."""
    pass
```

## Dependencies

### Required Packages

```
sqlalchemy>=2.0.0          # ORM
alembic>=1.12.0            # Migrations
cryptography>=41.0.0       # Key encryption
pyyaml>=6.0                # YAML export/import
```

### Database Drivers

```
# SQLite - built into Python
# MySQL
mysqlclient>=2.0.0         # or PyMySQL

# PostgreSQL
psycopg2-binary>=2.9.0     # or asyncpg for async
```
