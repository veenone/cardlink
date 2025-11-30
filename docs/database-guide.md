# Database Layer User Guide

**Version:** 1.0.0
**Last Updated:** November 29, 2024

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Database Configuration](#database-configuration)
5. [Data Models](#data-models)
6. [Repository Pattern](#repository-pattern)
7. [Unit of Work](#unit-of-work)
8. [Migrations](#migrations)
9. [Event System](#event-system)
10. [Data Export/Import](#data-exportimport)
11. [CLI Commands](#cli-commands)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)

---

## Introduction

The Database Layer provides persistent storage for the CardLink GP OTA Tester platform. It uses SQLAlchemy 2.0 for ORM functionality and supports multiple database backends.

### Features

- **Multiple Database Backends**: SQLite, MySQL, PostgreSQL
- **Repository Pattern**: Clean data access abstraction
- **Unit of Work**: Transaction management
- **Alembic Migrations**: Version-controlled schema changes
- **Event System**: Real-time change notifications
- **Data Export/Import**: JSON and YAML formats
- **Encrypted PSK Storage**: Secure credential management
- **CLI Tools**: Database management commands

### Architecture

```
┌───────────────────────────────────────┐
│         Application Layer             │
│   (Server, Controllers, Tests)        │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│       Unit of Work Pattern            │
│  (Transaction Management)             │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      Repository Pattern               │
│  Devices │ Cards │ Sessions │ Logs    │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      SQLAlchemy ORM Models            │
│  Device │ CardProfile │ OTASession    │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│      Database Backend                 │
│  SQLite │ MySQL │ PostgreSQL          │
└───────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.8+
- One of: SQLite (default), MySQL, or PostgreSQL

### Install Package

```bash
# Basic installation (includes SQLite support)
pip install gp-ota-tester

# With MySQL support
pip install gp-ota-tester[mysql]

# With PostgreSQL support
pip install gp-ota-tester[postgresql]

# With all database backends
pip install gp-ota-tester[database]
```

### Setup Encryption Key

For PSK credential storage, set an encryption key:

```bash
# Generate a Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set environment variable
export CARDLINK_ENCRYPTION_KEY="your-generated-key-here"
```

**⚠️ Important**: Keep this key secure! Store it in a secure vault in production.

---

## Quick Start

### 5-Minute Tutorial

```python
from cardlink.database import (
    DatabaseManager,
    UnitOfWork,
    Device,
    DeviceType,
    CardProfile,
    CardType,
)

# 1. Initialize database
manager = DatabaseManager()
manager.initialize()
manager.create_tables()

# 2. Create a device
with UnitOfWork(manager) as uow:
    device = Device(
        id="RF8M33XXXXX",
        device_type=DeviceType.PHONE,
        name="Test Phone",
        manufacturer="Samsung",
        model="Galaxy S21",
        imei="123456789012345",
    )
    uow.devices.create(device)
    uow.commit()
    print(f"Created device: {device.id}")

# 3. Create a card profile
with UnitOfWork(manager) as uow:
    card = CardProfile(
        iccid="89011234567890123456",
        imsi="310120987654321",
        card_type=CardType.USIM,
        psk_identity="card_001",
        admin_url="https://admin.example.com:8443/api",
    )
    # Store PSK with encryption
    uow.cards.create_with_psk(card, b"my_secret_psk_key_16")
    uow.commit()
    print(f"Created card: {card.iccid}")

# 4. Query devices
with UnitOfWork(manager) as uow:
    # Find all phones
    phones = uow.devices.find_phones()
    print(f"Found {len(phones)} phone(s)")

    # Search devices
    results = uow.devices.search("Samsung")
    for device in results:
        print(f"  - {device.name}: {device.model}")

# 5. Query sessions
with UnitOfWork(manager) as uow:
    # Get recent sessions
    sessions = uow.sessions.find_by_date_range(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now()
    )
    print(f"Sessions in last 7 days: {len(sessions)}")

    # Get statistics
    stats = uow.sessions.get_statistics(days=30)
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Avg duration: {stats['avg_duration_ms']:.0f}ms")

# 6. Export database
from cardlink.database import DataExporter, ExportFormat

with UnitOfWork(manager) as uow:
    exporter = DataExporter(uow)
    data = exporter.export_all(ExportFormat.JSON)

    with open("backup.json", "w") as f:
        f.write(data)
    print("Database exported to backup.json")

# Cleanup
manager.close()
```

---

## Database Configuration

### Environment Variables

Configure the database using environment variables:

```bash
# Option 1: Full DATABASE_URL
export DATABASE_URL="sqlite:///data/cardlink.db"
export DATABASE_URL="mysql://user:pass@localhost:3306/cardlink"
export DATABASE_URL="postgresql://user:pass@localhost:5432/cardlink"

# Option 2: Individual components
export CARDLINK_DB_DRIVER="mysql"
export CARDLINK_DB_HOST="localhost"
export CARDLINK_DB_PORT="3306"
export CARDLINK_DB_NAME="cardlink"
export CARDLINK_DB_USER="cardlink_user"
export CARDLINK_DB_PASSWORD="secure_password"

# Encryption key (required for PSK storage)
export CARDLINK_ENCRYPTION_KEY="your-fernet-key-here"
```

### Programmatic Configuration

```python
from cardlink.database import DatabaseConfig, DatabaseManager

# Using defaults (SQLite)
config = DatabaseConfig()
print(f"Database URL: {config.database_url}")

# Custom SQLite path
config = DatabaseConfig.from_sqlite_path("my_database.db")

# MySQL
config = DatabaseConfig(
    database_url="mysql://user:pass@localhost/cardlink"
)

# Check backend
if config.is_mysql:
    print("Using MySQL backend")

# Create manager
manager = DatabaseManager(config)
manager.initialize()
```

### Connection Pooling

```python
config = DatabaseConfig(
    database_url="postgresql://user:pass@localhost/cardlink",
    pool_size=10,         # Maximum connections in pool
    max_overflow=20,      # Additional connections when pool full
    pool_timeout=30,      # Seconds to wait for connection
)
```

---

## Data Models

### Device Model

Stores mobile phones and modems.

```python
from cardlink.database import Device, DeviceType

device = Device(
    id="RF8M33XXXXX",             # Device serial/IMEI
    device_type=DeviceType.PHONE, # PHONE or MODEM
    name="Test Phone 1",
    manufacturer="Samsung",
    model="Galaxy S21",
    firmware_version="Android 12",

    # Optional identifiers
    imei="123456789012345",
    imsi="310120987654321",
    iccid="89011234567890123456",

    # Connection settings (JSON)
    connection_settings={
        "adb_serial": "RF8M33XXXXX",
        "port": 5037,
    },

    # Status tracking
    is_active=True,
    last_seen=datetime.now(),

    notes="Primary test device",
)
```

**Fields:**
- `id` (PK): Device identifier (serial/IMEI)
- `device_type`: PHONE or MODEM enum
- `name`: Human-readable name
- `manufacturer`, `model`, `firmware_version`: Device info
- `imei`, `imsi`, `iccid`: Optional identifiers
- `connection_settings`: JSON config (ADB, modem port, etc.)
- `is_active`, `last_seen`: Status tracking
- `notes`: Additional information

### CardProfile Model

Stores UICC card configurations.

```python
from cardlink.database import CardProfile, CardType

card = CardProfile(
    iccid="89011234567890123456",  # Primary key
    imsi="310120987654321",
    card_type=CardType.USIM,        # SIM, USIM, ISIM, EUICC
    atr="3B9F96801F478031E073...",  # Card ATR

    # PSK credentials (encrypted)
    psk_identity="card_001",
    # psk_key_encrypted stored via repository method

    # OTA configuration
    admin_url="https://admin.example.com:8443/api",

    # JSON configurations
    trigger_config={
        "sms": {
            "tar": "000001",
            "kic": "01",
            "kid": "01",
        }
    },
    bip_config={
        "bearer": "GPRS",
        "apn": "internet",
        "buffer_size": 1024,
    },
    security_domains={
        "isd_aid": "A000000151000000",
    },
)
```

**Fields:**
- `iccid` (PK): Card identifier
- `imsi`: Mobile subscriber identity
- `card_type`: SIM, USIM, ISIM, or EUICC
- `atr`: Answer-To-Reset bytes
- `psk_identity`, `psk_key_encrypted`: TLS-PSK credentials
- `admin_url`: OTA server URL
- `trigger_config`, `bip_config`, `security_domains`: JSON configs

### OTASession Model

Tracks OTA sessions.

```python
from cardlink.database import OTASession, SessionStatus
import uuid

session = OTASession(
    id=uuid.uuid4(),
    device_id="RF8M33XXXXX",
    card_iccid="89011234567890123456",
    session_type="profile_download",
    status=SessionStatus.ACTIVE,

    # TLS information
    cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
    psk_identity="card_001",

    # Timestamps
    started_at=datetime.now(),
    # ended_at set on completion
    # duration_ms calculated automatically

    # Error tracking
    error_code=None,
    error_message=None,
)
```

**Fields:**
- `id` (PK): UUID
- `device_id`, `card_iccid`: Foreign keys
- `session_type`: Session purpose
- `status`: PENDING, ACTIVE, COMPLETED, FAILED, TIMEOUT
- `cipher_suite`, `psk_identity`: TLS details
- `started_at`, `ended_at`, `duration_ms`: Timing
- `error_code`, `error_message`: Error tracking

### CommLog Model

APDU exchange logs.

```python
from cardlink.database import CommLog, CommDirection

log = CommLog(
    session_id=session.id,
    timestamp=datetime.now(),
    direction=CommDirection.COMMAND,

    raw_data="00A4040008A000000151000000",
    decoded_data="SELECT ISD AID=A000000151000000",

    # Response fields (for responses only)
    status_word="9000",
    status_message="Success",
    latency_ms=15.2,
)
```

**Fields:**
- `id` (PK): Auto-increment
- `session_id`: Foreign key to OTASession
- `timestamp`: Millisecond precision
- `direction`: COMMAND or RESPONSE
- `raw_data`, `decoded_data`: APDU hex and human-readable
- `status_word`, `status_message`: Response SW
- `latency_ms`: Response time

### TestResult Model

Test execution results.

```python
from cardlink.database import TestResult, TestStatus
import uuid

result = TestResult(
    id=uuid.uuid4(),
    run_id="test_run_2024_11_29_001",
    suite_name="integration_tests",
    test_name="test_profile_download",

    device_id="RF8M33XXXXX",
    card_iccid="89011234567890123456",

    status=TestStatus.PASSED,

    started_at=datetime.now(),
    # ended_at, duration_ms set on completion

    assertions={
        "connection_established": True,
        "profile_downloaded": True,
        "apdu_count": 15,
    },
    metadata={
        "test_env": "staging",
        "test_runner": "pytest",
    },
)
```

**Fields:**
- `id` (PK): UUID
- `run_id`: Groups results from same test run
- `suite_name`, `test_name`: Test identification
- `device_id`, `card_iccid`: Test targets
- `status`: PASSED, FAILED, SKIPPED, ERROR
- `error_message`: Failure details
- `assertions`, `metadata`: JSON data

### Setting Model

Key-value configuration storage.

```python
from cardlink.database import Setting

setting = Setting(
    key="max_sessions_per_device",
    value=10,
    description="Maximum concurrent sessions per device",
    category="limits",
)
```

---

## Repository Pattern

Repositories provide data access abstraction.

### Base Repository

All repositories extend `BaseRepository`:

```python
# Common CRUD operations
device = repository.get_by_id("RF8M33XXXXX")
all_devices = repository.get_all(limit=100)
phones = repository.find_by(device_type=DeviceType.PHONE)
phone = repository.find_one_by(name="Test Phone")

# Create/Update/Delete
repository.create(device)
repository.create_all([device1, device2, device3])
repository.update(device)
repository.delete(device)
repository.delete_by_id("RF8M33XXXXX")

# Utilities
exists = repository.exists("RF8M33XXXXX")
count = repository.count()
count_phones = repository.count_by(device_type=DeviceType.PHONE)

# Pagination
page = repository.paginate(
    page=1,
    per_page=20,
    order_by="created_at",
    descending=True
)
print(f"Page {page.page} of {page.total_pages}")
print(f"Total: {page.total_items}")
for item in page.items:
    print(item)
```

### Device Repository

```python
with UnitOfWork(manager) as uow:
    # Find by type
    phones = uow.devices.find_phones()
    modems = uow.devices.find_modems()

    # Find active devices
    active = uow.devices.find_active()

    # Find recently seen (within hours)
    recent = uow.devices.find_recent(hours=24)

    # Search (name, ID, IMEI, IMSI)
    results = uow.devices.search("Samsung")

    # Update last seen
    uow.devices.update_last_seen("RF8M33XXXXX")

    # Find by ICCID
    device = uow.devices.find_by_iccid("89011234567890123456")

    # Deactivate
    uow.devices.deactivate("RF8M33XXXXX")
    uow.commit()
```

### Card Repository

```python
with UnitOfWork(manager) as uow:
    # Create with encrypted PSK
    card = CardProfile(iccid="8901...", psk_identity="card_001")
    uow.cards.create_with_psk(card, b"my_16_byte_psk_key")

    # Get decrypted PSK key
    psk_key = uow.cards.get_psk_key("8901...")
    print(f"PSK Key: {psk_key.hex()}")

    # Update PSK
    uow.cards.update_psk(
        "8901...",
        identity="new_identity",
        key=b"new_psk_key_here"
    )

    # Find by type
    usim_cards = uow.cards.find_by_type(CardType.USIM)

    # Find cards with PSK configured
    cards_with_psk = uow.cards.find_with_psk()

    # Find by admin URL
    cards = uow.cards.find_by_admin_url("https://admin.example.com")

    # Export profile (without key by default)
    profile_dict = uow.cards.export_profile("8901...", include_key=False)

    uow.commit()
```

### Session Repository

```python
with UnitOfWork(manager) as uow:
    # Create session
    session = uow.sessions.create_session(
        device_id="RF8M33XXXXX",
        card_iccid="8901...",
        session_type="profile_download"
    )

    # Start session (sets timestamp)
    uow.sessions.start_session(session.id)

    # Set TLS info
    uow.sessions.set_tls_info(
        session.id,
        cipher="TLS_PSK_WITH_AES_128_CBC_SHA256",
        psk_identity="card_001"
    )

    # Complete session (calculates duration)
    uow.sessions.complete_session(session.id)

    # Or mark as failed
    uow.sessions.fail_session(
        session.id,
        error_code="E001",
        message="Connection timeout"
    )

    # Query sessions
    device_sessions = uow.sessions.find_by_device("RF8M33XXXXX", limit=10)
    card_sessions = uow.sessions.find_by_card("8901...", limit=10)
    active = uow.sessions.find_active()
    failed = uow.sessions.find_by_status(SessionStatus.FAILED)

    # Date range
    sessions = uow.sessions.find_by_date_range(
        start=datetime(2024, 11, 1),
        end=datetime(2024, 11, 30)
    )

    # Statistics
    stats = uow.sessions.get_statistics(days=30)
    print(f"Total: {stats['total']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Avg duration: {stats['avg_duration_ms']:.0f}ms")

    uow.commit()
```

### Log Repository

```python
with UnitOfWork(manager) as uow:
    # Add single log
    uow.logs.add_log(
        session_id=session.id,
        direction=CommDirection.COMMAND,
        raw_data="00A4040008A000000151000000",
        decoded_data="SELECT ISD",
    )

    # Batch logging (high performance)
    logs = [
        (session.id, CommDirection.COMMAND, "00A4...", "SELECT"),
        (session.id, CommDirection.RESPONSE, "9000", "Success"),
    ]
    uow.logs.add_log_batch(logs)
    uow.logs.flush_batch()  # Explicit flush

    # Query logs
    all_logs = uow.logs.find_by_session(session.id)
    commands = uow.logs.find_commands(session.id)
    responses = uow.logs.find_responses(session.id)

    # Find by status word
    success_logs = uow.logs.find_by_status(session.id, "9000")

    # Find errors (non-9000)
    errors = uow.logs.find_errors(session.id)

    # Search hex pattern
    select_commands = uow.logs.search_hex("A4", session_id=session.id)

    # Purge old logs (retention policy)
    deleted_count = uow.logs.purge_old(days=90)
    print(f"Deleted {deleted_count} old logs")

    # Export session logs
    log_data = uow.logs.export_session_logs(session.id)

    uow.commit()
```

### Test Repository

```python
with UnitOfWork(manager) as uow:
    # Create test result
    result = uow.tests.create_result(
        run_id="test_run_001",
        suite_name="integration",
        test_name="test_ota_session",
        device_id="RF8M33XXXXX",
        card_iccid="8901...",
        status=TestStatus.PASSED,
        started_at=datetime.now(),
        ended_at=datetime.now(),
        duration_ms=1500,
        assertions={"connected": True},
        metadata={"env": "staging"}
    )

    # Query results
    run_results = uow.tests.find_by_run("test_run_001")
    suite_results = uow.tests.find_by_suite("integration", limit=50)
    failures = uow.tests.find_failures("test_run_001")

    # Get run summary
    summary = uow.tests.get_run_summary("test_run_001")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")

    # Compare runs (regression detection)
    comparison = uow.tests.compare_runs("run_001", "run_002")
    print(f"New failures: {len(comparison['new_failures'])}")
    print(f"Fixed tests: {len(comparison['fixed'])}")

    # Export JUnit XML
    junit_xml = uow.tests.export_junit_xml("test_run_001")
    with open("results.xml", "w") as f:
        f.write(junit_xml)

    uow.commit()
```

### Settings Repository

```python
with UnitOfWork(manager) as uow:
    # Get setting with default fallback
    max_sessions = uow.settings.get_value(
        "max_sessions_per_device",
        default=10
    )

    # Set setting
    uow.settings.set_value(
        key="log_retention_days",
        value=90,
        description="Days to retain APDU logs",
        category="retention"
    )

    # Get by category
    retention_settings = uow.settings.get_by_category("retention")

    # Get all settings (merged with defaults)
    all_settings = uow.settings.get_all_settings()

    # Export to YAML
    yaml_str = uow.settings.export_yaml()
    with open("settings.yaml", "w") as f:
        f.write(yaml_str)

    # Import from YAML
    with open("settings.yaml") as f:
        yaml_str = f.read()
    uow.settings.import_yaml(yaml_str)

    # Reset to defaults
    uow.settings.reset_to_defaults(category="retention")

    uow.commit()
```

---

## Unit of Work

Unit of Work provides transaction boundaries:

```python
from cardlink.database import UnitOfWork

# Context manager (recommended)
with UnitOfWork(manager) as uow:
    device = Device(id="RF8M...", device_type=DeviceType.PHONE)
    uow.devices.create(device)

    card = CardProfile(iccid="8901...")
    uow.cards.create_with_psk(card, b"psk_key")

    uow.commit()  # Commit transaction
# Automatic rollback on exception

# Manual management
uow = UnitOfWork(manager)
try:
    uow.devices.create(device)
    uow.commit()
except Exception as e:
    uow.rollback()
    raise
finally:
    uow.close()
```

**Repository Access:**
- `uow.devices` - DeviceRepository
- `uow.cards` - CardRepository
- `uow.sessions` - SessionRepository
- `uow.logs` - LogRepository
- `uow.tests` - TestRepository
- `uow.settings` - SettingRepository

---

## Migrations

Database schema versioning with Alembic.

### Run Migrations

```bash
# Apply all pending migrations
cardlink-db migrate

# Migrate to specific revision
cardlink-db migrate --revision ae1234

# Dry run (show SQL)
cardlink-db migrate --dry-run
```

### Create Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add user column"

# Manual migration
alembic revision -m "Custom changes"
```

Edit `migrations/versions/XXX_description.py`:

```python
def upgrade():
    op.add_column('devices', sa.Column('user', sa.String(50)))

def downgrade():
    op.drop_column('devices', 'user')
```

### Migration Commands

```python
from cardlink.database import (
    run_migrations,
    downgrade,
    get_current_revision,
    get_pending_revisions,
)

# Run migrations programmatically
run_migrations()

# Downgrade one version
downgrade(steps=1)

# Check current version
current = get_current_revision()
print(f"Current revision: {current}")

# Check pending
pending = get_pending_revisions()
print(f"Pending migrations: {len(pending)}")
```

---

## Event System

Subscribe to database changes:

```python
from cardlink.database import (
    get_emitter,
    EventType,
    DatabaseEvent,
)

# Get global emitter
emitter = get_emitter()

# Define event handler
def on_device_created(event: DatabaseEvent):
    print(f"Device created: {event.entity_id}")
    print(f"Data: {event.data}")

# Register handler
emitter.on(EventType.DEVICE_CREATED, on_device_created)

# Wildcard handler (all events)
def log_all_events(event: DatabaseEvent):
    print(f"Event: {event.event_type} - {event.entity_type}")

emitter.on("*", log_all_events)

# Now create a device
with UnitOfWork(manager) as uow:
    device = Device(id="RF8M...", device_type=DeviceType.PHONE)
    uow.devices.create(device)  # Triggers DEVICE_CREATED event
    uow.commit()

# Unregister handler
emitter.off(EventType.DEVICE_CREATED, on_device_created)
```

**Event Types:**
- `DEVICE_CREATED`, `DEVICE_UPDATED`, `DEVICE_DELETED`
- `CARD_CREATED`, `CARD_UPDATED`, `CARD_DELETED`
- `SESSION_CREATED`, `SESSION_UPDATED`, `SESSION_COMPLETED`
- `LOG_CREATED`
- `TEST_RESULT_CREATED`
- `SETTING_UPDATED`

---

## Data Export/Import

### Export Database

```python
from cardlink.database import DataExporter, ExportFormat

with UnitOfWork(manager) as uow:
    exporter = DataExporter(uow)

    # Export all tables
    json_data = exporter.export_all(ExportFormat.JSON)
    yaml_data = exporter.export_all(ExportFormat.YAML)

    # Selective export
    device_data = exporter.export_selective(
        tables=["devices", "cards"],
        format=ExportFormat.JSON
    )

    # Save to file
    with open("backup.json", "w") as f:
        f.write(json_data)
```

### Import Database

```python
from cardlink.database import (
    DataImporter,
    ConflictMode,
    ExportFormat,
)

with UnitOfWork(manager) as uow:
    importer = DataImporter(uow)

    # Read backup
    with open("backup.json") as f:
        data = f.read()

    # Import with conflict resolution
    result = importer.import_data(
        data,
        format=ExportFormat.JSON,
        conflict_mode=ConflictMode.SKIP  # or OVERWRITE, MERGE
    )

    print(f"Created: {result.created}")
    print(f"Updated: {result.updated}")
    print(f"Skipped: {result.skipped}")
    print(f"Errors: {result.errors}")

    uow.commit()
```

**Conflict Modes:**
- `SKIP`: Skip existing records
- `OVERWRITE`: Replace existing records
- `MERGE`: Update existing with new data

---

## CLI Commands

### Database Initialization

```bash
# Initialize database and create tables
cardlink-db init

# Force recreate (drops existing tables)
cardlink-db init --force
```

### Migration Management

```bash
# Run pending migrations
cardlink-db migrate

# Migrate to specific revision
cardlink-db migrate --revision ae1234

# Show migration SQL without executing
cardlink-db migrate --dry-run
```

### Database Status

```bash
# Show database info
cardlink-db status

# Verbose mode (includes table details)
cardlink-db status --verbose
```

**Output:**
```
Database Status
===============
Backend: SQLite
URL: sqlite:///data/cardlink.db
Current Revision: ae12345678
Pending Migrations: 0

Tables:
  devices: 5 rows
  cards: 12 rows
  sessions: 48 rows
  logs: 1,234 rows
```

### Data Export

```bash
# Export to JSON (stdout)
cardlink-db export

# Export to file
cardlink-db export --output backup.json

# Export to YAML
cardlink-db export --format yaml --output backup.yaml

# Selective export
cardlink-db export --tables devices,cards
```

### Data Import

```bash
# Import with auto-format detection
cardlink-db import backup.json

# Specify format
cardlink-db import --format yaml backup.yaml

# Conflict resolution
cardlink-db import --conflict skip backup.json
cardlink-db import --conflict overwrite backup.json
cardlink-db import --conflict merge backup.json

# Dry run (preview)
cardlink-db import --dry-run backup.json
```

### Data Purge

```bash
# Purge old logs (90 days)
cardlink-db purge --older-than 90 --tables logs

# Purge old sessions and logs
cardlink-db purge --older-than 30 --tables sessions,logs

# Skip confirmation
cardlink-db purge --older-than 90 --tables logs --yes
```

### Statistics

```bash
# Show database statistics
cardlink-db stats

# JSON output
cardlink-db stats --json
```

**Output:**
```json
{
  "tables": {
    "devices": 5,
    "cards": 12,
    "sessions": 48,
    "logs": 1234,
    "tests": 96,
    "settings": 15
  },
  "database_size_mb": 2.4,
  "recent_activity": {
    "sessions_last_24h": 8,
    "tests_last_24h": 16
  }
}
```

---

## Best Practices

### Transaction Management

✅ **DO**: Use Unit of Work for transactions
```python
with UnitOfWork(manager) as uow:
    uow.devices.create(device)
    uow.cards.create(card)
    uow.commit()
```

❌ **DON'T**: Create sessions manually
```python
session = manager.create_session()
# Hard to manage, no auto-rollback
```

### Resource Cleanup

✅ **DO**: Close database manager
```python
try:
    manager = DatabaseManager()
    manager.initialize()
    # Use database
finally:
    manager.close()
```

### Error Handling

✅ **DO**: Handle specific exceptions
```python
from cardlink.database import NotFoundError, IntegrityError

try:
    device = uow.devices.get_by_id("invalid")
except NotFoundError:
    print("Device not found")
except IntegrityError as e:
    print(f"Constraint violation: {e}")
```

### Encryption

✅ **DO**: Always use encrypted PSK storage
```python
# Use repository method
uow.cards.create_with_psk(card, psk_key)

# NOT direct assignment
# card.psk_key_encrypted = psk_key  # WRONG!
```

✅ **DO**: Set encryption key
```bash
export CARDLINK_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

### Performance

✅ **DO**: Use batch operations
```python
# Batch log inserts
uow.logs.add_log_batch(logs)
uow.logs.flush_batch()
```

✅ **DO**: Use pagination for large results
```python
page = uow.devices.paginate(page=1, per_page=50)
```

❌ **DON'T**: Load all data at once
```python
all_logs = uow.logs.find_by_session(session_id)  # Could be thousands!
```

### Migrations

✅ **DO**: Test migrations before production
```bash
# On staging database
cardlink-db migrate --dry-run
cardlink-db migrate
```

✅ **DO**: Backup before migrations
```bash
cardlink-db export --output backup_before_migration.json
cardlink-db migrate
```

---

## Troubleshooting

### Connection Errors

**Problem**: `ConnectionError: Unable to connect to database`

**Solutions:**
1. Check DATABASE_URL:
   ```bash
   echo $DATABASE_URL
   ```
2. Verify database server is running:
   ```bash
   # MySQL
   systemctl status mysql

   # PostgreSQL
   systemctl status postgresql
   ```
3. Test connection:
   ```python
   from cardlink.database import DatabaseManager

   manager = DatabaseManager()
   try:
       manager.initialize()
       print("Connection successful!")
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

### Migration Errors

**Problem**: `MigrationError: Target revision not found`

**Solutions:**
1. Check current revision:
   ```bash
   cardlink-db status
   ```
2. List available revisions:
   ```bash
   alembic history
   ```
3. Stamp to correct revision:
   ```bash
   alembic stamp head
   ```

### Encryption Errors

**Problem**: `EncryptionError: CARDLINK_ENCRYPTION_KEY not set`

**Solution:**
```bash
# Generate key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set environment variable
export CARDLINK_ENCRYPTION_KEY="generated-key-here"
```

**Problem**: `EncryptionError: Invalid key or corrupted data`

**Solution:**
- Key changed - data cannot be decrypted
- Restore original key or re-encrypt data with new key

### Performance Issues

**Problem**: Slow queries

**Solutions:**
1. Enable query logging:
   ```python
   config = DatabaseConfig(echo=True)  # Logs all SQL
   ```
2. Check indexes:
   ```python
   # Indexes should exist on:
   # - devices: device_type, iccid, last_seen
   # - cards: card_type, psk_identity
   # - sessions: device_id, card_iccid, status, created_at
   # - logs: session_id, timestamp, direction
   ```
3. Use pagination:
   ```python
   page = repository.paginate(page=1, per_page=50)
   ```

### Import Errors

**Problem**: Import fails with integrity errors

**Solution:**
```bash
# Use SKIP mode to avoid duplicates
cardlink-db import --conflict skip backup.json

# Or clean database first
cardlink-db init --force
cardlink-db import backup.json
```

---

## Advanced Usage

### Custom Queries

```python
from sqlalchemy import select, and_, or_

with UnitOfWork(manager) as uow:
    # Raw SQLAlchemy query
    stmt = select(Device).where(
        and_(
            Device.device_type == DeviceType.PHONE,
            Device.is_active == True,
            Device.manufacturer.like('%Samsung%')
        )
    )
    results = uow.session.execute(stmt).scalars().all()
```

### Bulk Operations

```python
# Bulk insert
devices = [
    Device(id=f"device_{i}", device_type=DeviceType.PHONE)
    for i in range(100)
]
uow.devices.create_all(devices)
uow.commit()
```

### Statistics Queries

```python
from sqlalchemy import func

with UnitOfWork(manager) as uow:
    # Count by type
    stats = uow.session.query(
        Device.device_type,
        func.count(Device.id)
    ).group_by(Device.device_type).all()

    for device_type, count in stats:
        print(f"{device_type}: {count}")
```

---

## API Reference

See [database-quick-reference.md](database-quick-reference.md) for complete API documentation.

---

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/your-org/cardlink/issues
- **Documentation**: https://docs.cardlink.dev
- **Discord**: https://discord.gg/cardlink

---

**End of Database Layer User Guide**
