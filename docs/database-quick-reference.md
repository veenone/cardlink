# Database Layer Quick Reference

Quick reference guide for the GP-OTA-Tester database layer.

---

## Installation

```bash
# Install with database support
pip install -e ".[database]"

# Initialize database
gp-db init

# Run migrations
gp-db migrate upgrade head
```

---

## Configuration

### Environment Variables

```bash
# SQLite (default)
export GP_DB_URL="sqlite:///gp_ota.db"

# PostgreSQL
export GP_DB_URL="postgresql://user:pass@localhost:5432/gp_ota"

# MySQL
export GP_DB_URL="mysql+pymysql://user:pass@localhost:3306/gp_ota"
```

### Programmatic Configuration

```python
from cardlink.database import DatabaseConfig

# SQLite
config = DatabaseConfig(url="sqlite:///gp_ota.db")

# With connection pool
config = DatabaseConfig(
    url="postgresql://user:pass@localhost:5432/gp_ota",
    pool_size=10,
    max_overflow=20,
    echo=False
)
```

---

## Common Operations

### Basic Setup

```python
from cardlink.database import get_unit_of_work

# Get Unit of Work instance
uow = get_unit_of_work()
```

### Create Records

```python
from cardlink.database.models import Device, CardProfile

# Create device
with uow:
    device = Device(
        iccid="89012345678901234567",
        imsi="123456789012345",
        msisdn="+1234567890",
        device_model="Pixel 6"
    )
    uow.devices.add(device)
    uow.commit()
    device_id = device.id

# Create card profile
with uow:
    profile = CardProfile(
        name="Production Profile",
        psk_key=b"\x00\x01\x02...",
        psk_identity="card_001",
        admin_url="https://server.example.com:8443/admin"
    )
    uow.card_profiles.add(profile)
    uow.commit()
```

### Query Records

```python
# Get by ID
with uow:
    device = uow.devices.get(device_id)

# Get by ICCID
with uow:
    device = uow.devices.get_by_iccid("89012345678901234567")

# Get all
with uow:
    all_devices = uow.devices.get_all()

# Get active sessions
with uow:
    active = uow.ota_sessions.get_active_sessions()

# Filter
with uow:
    filtered = uow.devices.filter(device_model="Pixel 6")
```

### Update Records

```python
# Update device
with uow:
    device = uow.devices.get(device_id)
    device.device_model = "Pixel 7"
    device.updated_at = datetime.utcnow()
    uow.devices.update(device)
    uow.commit()
```

### Delete Records

```python
# Delete by ID
with uow:
    uow.devices.delete(device_id)
    uow.commit()

# Delete object
with uow:
    device = uow.devices.get(device_id)
    uow.devices.remove(device)
    uow.commit()
```

### OTA Sessions

```python
from cardlink.database.models import OTASession, SessionStatus

# Create session
with uow:
    session = OTASession(
        device_id=device_id,
        session_type="admin",
        status=SessionStatus.PENDING
    )
    uow.ota_sessions.add(session)
    uow.commit()
    session_id = session.id

# Update status
with uow:
    session = uow.ota_sessions.get(session_id)
    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()
    uow.ota_sessions.update(session)
    uow.commit()

# Get by device
with uow:
    sessions = uow.ota_sessions.get_by_device(device_id)
```

### Communication Logs

```python
from cardlink.database.models import CommLog, CommDirection

# Log APDU exchange
with uow:
    log = CommLog(
        session_id=session_id,
        direction=CommDirection.SENT,
        apdu_command=bytes.fromhex("00A4040000"),
        apdu_response=bytes.fromhex("9000"),
        duration_ms=25
    )
    uow.comm_logs.add(log)
    uow.commit()

# Get session logs
with uow:
    logs = uow.comm_logs.get_by_session(session_id)
```

### Test Results

```python
from cardlink.database.models import TestResult, TestStatus

# Create test result
with uow:
    result = TestResult(
        session_id=session_id,
        test_name="E2E Basic Flow",
        status=TestStatus.PASSED,
        duration_ms=1250,
        assertions_passed=5,
        assertions_failed=0
    )
    uow.test_results.add(result)
    uow.commit()

# Get failed tests
with uow:
    failed = uow.test_results.get_failed_tests()
```

### Settings

```python
# Set value
with uow:
    uow.settings.set("server.port", "8443")
    uow.commit()

# Get value
with uow:
    port = uow.settings.get("server.port")

# Get with default
with uow:
    timeout = uow.settings.get("server.timeout", "30")

# Get all
with uow:
    all_settings = uow.settings.get_all()
```

---

## Event System

### Subscribe to Events

```python
from cardlink.database.events import EventEmitter, DatabaseEvent

emitter = EventEmitter()

@emitter.on(DatabaseEvent.DEVICE_CREATED)
def on_device_created(device_id, **kwargs):
    print(f"New device: {device_id}")

@emitter.on(DatabaseEvent.SESSION_COMPLETED)
def on_session_completed(session_id, **kwargs):
    print(f"Session completed: {session_id}")
```

### Event Types

| Event | When Emitted | Payload |
|-------|--------------|---------|
| `DEVICE_CREATED` | New device added | `device_id` |
| `DEVICE_UPDATED` | Device modified | `device_id` |
| `DEVICE_DELETED` | Device removed | `device_id` |
| `PROFILE_CREATED` | New profile added | `profile_id` |
| `SESSION_STARTED` | Session begins | `session_id`, `device_id` |
| `SESSION_COMPLETED` | Session finishes | `session_id`, `status` |
| `TEST_COMPLETED` | Test finishes | `test_id`, `status` |
| `COMM_LOGGED` | APDU logged | `log_id`, `session_id` |

---

## Data Export/Import

### Export Data

```python
from cardlink.database.export_import import DataExporter

# Export to JSON
with uow:
    exporter = DataExporter(uow.session)
    data = exporter.export_all()

with open("backup.json", "w") as f:
    json.dump(data, f, indent=2)

# Export specific tables
with uow:
    data = exporter.export_tables(["devices", "card_profiles"])
```

### Import Data

```python
from cardlink.database.export_import import DataImporter

# Import from JSON
with open("backup.json") as f:
    data = json.load(f)

with uow:
    importer = DataImporter(uow.session)
    result = importer.import_all(data)
    uow.commit()

print(f"Imported: {result.created} records")
print(f"Conflicts: {len(result.conflicts)}")

# Handle conflicts
with uow:
    result = importer.import_all(data, on_conflict="update")
    uow.commit()
```

---

## CLI Commands

### Database Management

```bash
# Initialize database
gp-db init

# Initialize with force (drop existing tables)
gp-db init --force

# Show database status
gp-db status

# Show verbose status with table counts
gp-db status --verbose

# Show database statistics
gp-db stats
```

### Migrations

```bash
# Run migrations to latest
gp-db migrate

# Migrate to specific revision
gp-db migrate --revision abc123

# Dry run (show pending migrations)
gp-db migrate --dry-run

# Rollback one step
gp-db rollback

# Rollback to specific revision
gp-db rollback --revision abc123

# Skip confirmation
gp-db rollback --confirm

# Show migration history
gp-db history
```

### Data Management

```bash
# Export to YAML (default)
gp-db export --output backup.yaml

# Export to JSON
gp-db export --format json --output backup.json

# Export specific tables
gp-db export --tables devices --tables card_profiles

# Export to stdout
gp-db export

# Include PSK keys (CAUTION)
gp-db export --include-psk --output backup.yaml

# Import from YAML
gp-db import backup.yaml

# Import from JSON
gp-db import backup.json --format json

# Import with conflict resolution
gp-db import backup.yaml --conflict overwrite

# Import with merge strategy
gp-db import backup.yaml --conflict merge

# Dry run import
gp-db import backup.yaml --dry-run
```

### Cleanup

```bash
# Clean up old data (30 days default)
gp-db cleanup

# Clean up data older than 7 days
gp-db cleanup --days 7

# Skip confirmation
gp-db cleanup --confirm
```

### Database URL Override

```bash
# Use custom database URL
gp-db --database sqlite:///custom.db status

# Use environment variable
export DATABASE_URL="postgresql://user:pass@localhost/gp_ota"
gp-db status
```

---

## Repository Methods

### Common Methods (All Repositories)

```python
# Add record
repo.add(entity)

# Get by ID
entity = repo.get(id)

# Get all
entities = repo.get_all()

# Update
repo.update(entity)

# Delete by ID
repo.delete(id)

# Remove entity
repo.remove(entity)

# Filter
entities = repo.filter(field=value)

# Count
count = repo.count()

# Exists
exists = repo.exists(id)
```

### Device Repository

```python
# Get by ICCID
device = uow.devices.get_by_iccid(iccid)

# Get by IMSI
device = uow.devices.get_by_imsi(imsi)

# Get by MSISDN
device = uow.devices.get_by_msisdn(msisdn)

# Search by model
devices = uow.devices.filter(device_model="Pixel 6")
```

### OTA Session Repository

```python
# Get by device
sessions = uow.ota_sessions.get_by_device(device_id)

# Get active sessions
active = uow.ota_sessions.get_active_sessions()

# Get by status
pending = uow.ota_sessions.get_by_status(SessionStatus.PENDING)

# Get by type
admin_sessions = uow.ota_sessions.get_by_type("admin")
```

### Communication Log Repository

```python
# Get by session
logs = uow.comm_logs.get_by_session(session_id)

# Get sent commands
sent = uow.comm_logs.get_by_direction(CommDirection.SENT)

# Get with errors
errors = uow.comm_logs.filter(has_error=True)
```

### Test Result Repository

```python
# Get by session
results = uow.test_results.get_by_session(session_id)

# Get passed tests
passed = uow.test_results.get_by_status(TestStatus.PASSED)

# Get failed tests
failed = uow.test_results.get_failed_tests()

# Get by test name
results = uow.test_results.get_by_test_name("E2E Basic Flow")
```

### Settings Repository

```python
# Set value
uow.settings.set(key, value)

# Get value
value = uow.settings.get(key)

# Get with default
value = uow.settings.get(key, default)

# Delete setting
uow.settings.delete(key)

# Get all
all_settings = uow.settings.get_all()
```

---

## Database Models

### Device

```python
Device(
    iccid="89012345678901234567",  # Required, unique
    imsi="123456789012345",
    msisdn="+1234567890",
    device_model="Pixel 6",
    metadata={"carrier": "Verizon"}
)
```

### CardProfile

```python
CardProfile(
    name="Production Profile",  # Required
    psk_key=b"\x00\x01...",     # Encrypted at rest
    psk_identity="card_001",
    admin_url="https://server:8443/admin",
    metadata={"environment": "prod"}
)
```

### OTASession

```python
OTASession(
    device_id=1,                      # Required
    session_type="admin",             # "admin" or "dl"
    status=SessionStatus.PENDING,     # PENDING/IN_PROGRESS/COMPLETED/FAILED
    started_at=datetime.utcnow(),
    completed_at=None,
    error_message=None,
    metadata={"trigger": "sms"}
)
```

### CommLog

```python
CommLog(
    session_id=1,                        # Required
    direction=CommDirection.SENT,        # SENT/RECEIVED
    apdu_command=bytes.fromhex("00A4"),
    apdu_response=bytes.fromhex("9000"),
    duration_ms=25,
    error_message=None
)
```

### TestResult

```python
TestResult(
    session_id=1,                    # Required
    test_name="E2E Basic Flow",      # Required
    status=TestStatus.PASSED,        # PASSED/FAILED/SKIPPED/ERROR
    duration_ms=1250,
    assertions_passed=5,
    assertions_failed=0,
    error_message=None,
    metadata={"test_suite": "e2e"}
)
```

### Setting

```python
Setting(
    key="server.port",     # Required, unique
    value="8443",          # Required
    description="Admin server port"
)
```

---

## Migrations

### Common Commands

```bash
# Create new migration
alembic revision -m "description"

# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current

# Show history
alembic history
```

### Migration File Structure

```python
"""Description of changes

Revision ID: abc123
Revises: xyz789
Create Date: 2024-01-15 10:30:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'xyz789'
branch_labels = None
depends_on = None

def upgrade():
    # Upgrade schema
    op.create_table('new_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
    )

def downgrade():
    # Rollback changes
    op.drop_table('new_table')
```

---

## Troubleshooting

### Connection Issues

```python
# Test database connection
from cardlink.database import test_connection

if test_connection():
    print("Database connected")
else:
    print("Connection failed")
```

### Check Configuration

```bash
# Show database URL
echo $GP_DB_URL

# Test with sqlite
export GP_DB_URL="sqlite:///test.db"
gp-db init
```

### Migration Issues

```bash
# Show current version
alembic current

# Reset to specific version
alembic downgrade <revision>

# Stamp without running migrations
alembic stamp head
```

### Lock Issues

```python
# For PostgreSQL/MySQL, check locks
SELECT * FROM pg_locks WHERE NOT granted;

# Kill blocking query
SELECT pg_terminate_backend(pid);
```

### Performance Issues

```python
# Enable query logging
config = DatabaseConfig(
    url="postgresql://...",
    echo=True  # Log all SQL queries
)

# Increase pool size
config = DatabaseConfig(
    url="postgresql://...",
    pool_size=20,
    max_overflow=40
)
```

---

## Best Practices

### Always Use Unit of Work

```python
# ✅ Good - automatic transaction management
with uow:
    device = Device(iccid="...")
    uow.devices.add(device)
    uow.commit()

# ❌ Bad - no transaction safety
device = Device(iccid="...")
uow.devices.add(device)
# Missing commit!
```

### Handle Errors Gracefully

```python
try:
    with uow:
        device = Device(iccid="...")
        uow.devices.add(device)
        uow.commit()
except IntegrityError:
    print("Device already exists")
except Exception as e:
    print(f"Database error: {e}")
```

### Use Filters for Complex Queries

```python
# ✅ Good - use repository filters
with uow:
    devices = uow.devices.filter(device_model="Pixel 6")

# ❌ Bad - load all and filter in Python
with uow:
    all_devices = uow.devices.get_all()
    devices = [d for d in all_devices if d.device_model == "Pixel 6"]
```

### Close Long-Running Sessions

```python
# For long-running operations
with uow:
    devices = uow.devices.get_all()
    # Process devices
    uow.commit()
# Session closed automatically
```

### Use Events for Decoupling

```python
# ✅ Good - use events for side effects
@emitter.on(DatabaseEvent.DEVICE_CREATED)
def send_notification(device_id, **kwargs):
    # Send notification

# ❌ Bad - tight coupling
with uow:
    device = Device(...)
    uow.devices.add(device)
    uow.commit()
    send_notification(device.id)  # Coupled
```

---

## Common Patterns

### Bulk Insert

```python
with uow:
    devices = [
        Device(iccid=f"890123456789{i:08d}")
        for i in range(100)
    ]
    for device in devices:
        uow.devices.add(device)
    uow.commit()
```

### Update or Create

```python
with uow:
    device = uow.devices.get_by_iccid(iccid)
    if device:
        device.msisdn = new_msisdn
        uow.devices.update(device)
    else:
        device = Device(iccid=iccid, msisdn=new_msisdn)
        uow.devices.add(device)
    uow.commit()
```

### Transaction Rollback

```python
try:
    with uow:
        device = Device(iccid="...")
        uow.devices.add(device)

        # Error occurs here
        raise ValueError("Something went wrong")

        uow.commit()
except ValueError:
    # Transaction automatically rolled back
    pass
```

### Cascading Deletes

```python
# Delete device and all related sessions/logs
with uow:
    device = uow.devices.get(device_id)
    uow.devices.remove(device)  # Cascades to sessions and logs
    uow.commit()
```

---

## Quick Diagnostics

```bash
# Check database exists
gp-db info

# Count records
gp-db stats

# Verify migrations
gp-db migrate current

# Test connection
python -c "from cardlink.database import test_connection; print(test_connection())"

# Export for backup
gp-db export backup_$(date +%Y%m%d).json
```

---

## Environment Setup

### Development

```bash
export GP_DB_URL="sqlite:///dev.db"
export GP_DB_ECHO="true"
gp-db init
```

### Testing

```bash
export GP_DB_URL="sqlite:///:memory:"
pytest tests/database/
```

### Production

```bash
export GP_DB_URL="postgresql://user:pass@prod-db:5432/gp_ota"
export GP_DB_POOL_SIZE="20"
export GP_DB_MAX_OVERFLOW="40"
gp-db migrate upgrade head
```

---

For detailed information, see the [Database Layer User Guide](database-guide.md).
