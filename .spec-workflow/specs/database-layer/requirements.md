# Requirements Document: Database Layer

## Introduction

The Database Layer is the CardLink component responsible for persistent storage of device configurations, UICC card profiles, OTA session records, communication logs, test results, and server settings. It provides a unified data access layer using SQLAlchemy ORM with support for SQLite (default), MySQL, and PostgreSQL backends.

This component enables CardLink to maintain state across sessions, track test history, and support multi-user deployments with shared database backends.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Configuration persistence**: Store device profiles, card configurations, and server settings
- **Session history**: Track OTA sessions for analysis and debugging
- **Communication logs**: Persist APDU exchanges for protocol analysis
- **Test results**: Store test execution history for compliance reporting
- **Multi-backend support**: SQLite for single-user, MySQL/PostgreSQL for teams

## Requirements

### Requirement 1: Database Connection Management

**User Story:** As a developer, I want the database layer to manage connections automatically, so that I can focus on application logic without worrying about connection lifecycle.

#### Acceptance Criteria

1. WHEN the application starts THEN the database layer SHALL parse DATABASE_URL environment variable
2. WHEN DATABASE_URL is not set THEN the layer SHALL default to SQLite at `data/cardlink.db`
3. WHEN connecting to SQLite THEN the layer SHALL create the database file if it doesn't exist
4. WHEN connecting to MySQL/PostgreSQL THEN the layer SHALL validate connection parameters
5. WHEN connection fails THEN the layer SHALL provide clear error message with troubleshooting hints
6. WHEN using connection pool THEN the layer SHALL configure appropriate pool size per backend
7. WHEN the application shuts down THEN the layer SHALL close all connections gracefully

### Requirement 2: Schema Management and Migrations

**User Story:** As a developer, I want database schema changes to be managed through migrations, so that I can safely upgrade production databases without data loss.

#### Acceptance Criteria

1. WHEN initializing database THEN the layer SHALL create all required tables
2. WHEN schema changes are needed THEN developers SHALL create Alembic migrations
3. WHEN running migrations THEN the layer SHALL apply changes in order
4. WHEN downgrading THEN the layer SHALL support migration rollback
5. WHEN checking migration status THEN the layer SHALL report current version
6. WHEN migrations fail THEN the layer SHALL rollback transaction and report error
7. WHEN using SQLite THEN the layer SHALL handle ALTER TABLE limitations

### Requirement 3: Device Configuration Storage

**User Story:** As a tester, I want to save and retrieve device configurations, so that I can quickly reconnect to previously configured phones and modems.

#### Acceptance Criteria

##### Phone Device Configuration
1. WHEN saving phone config THEN the layer SHALL store:
   - Device ID (ADB serial)
   - Device name/alias
   - Manufacturer, model, Android version
   - IMEI, IMSI, ICCID
   - Connection settings (USB port, etc.)
   - Last seen timestamp
   - Custom notes

##### Modem Device Configuration
2. WHEN saving modem config THEN the layer SHALL store:
   - Device ID (serial port identifier)
   - Device name/alias
   - Manufacturer, model, firmware version
   - IMEI, IMSI, ICCID
   - Serial port settings (baud rate, etc.)
   - AT command preferences
   - Last seen timestamp

##### Common Operations
3. WHEN listing devices THEN the layer SHALL support filtering by type, status, last seen
4. WHEN updating device THEN the layer SHALL preserve creation timestamp
5. WHEN deleting device THEN the layer SHALL optionally cascade to related sessions
6. WHEN searching devices THEN the layer SHALL support partial matching on name/ID

### Requirement 4: UICC Card Profile Storage

**User Story:** As a tester, I want to store UICC card profiles in the database, so that I can manage multiple test cards and their configurations.

#### Acceptance Criteria

1. WHEN saving card profile THEN the layer SHALL store:
   - ICCID (primary identifier)
   - IMSI
   - Card type (UICC, USIM, eUICC)
   - ATR
   - PSK identity
   - PSK key (encrypted)
   - Admin server URL
   - Trigger configuration (JSON)
   - BIP configuration (JSON)
   - Security Domain info
   - Creation/modification timestamps
   - Custom notes

2. WHEN storing PSK key THEN the layer SHALL encrypt using application secret
3. WHEN listing profiles THEN the layer SHALL support filtering by card type, PSK status
4. WHEN exporting profile THEN the layer SHALL support JSON format with optional key inclusion
5. WHEN importing profile THEN the layer SHALL validate and detect conflicts by ICCID
6. WHEN associating card with device THEN the layer SHALL track which device used which card

### Requirement 5: OTA Session Storage

**User Story:** As a tester, I want OTA sessions to be recorded in the database, so that I can review session history and analyze patterns.

#### Acceptance Criteria

1. WHEN creating session THEN the layer SHALL store:
   - Session ID (UUID)
   - Device ID (phone or modem)
   - Card ICCID
   - Session type (triggered, polled)
   - Start timestamp
   - End timestamp
   - Status (pending, active, completed, failed, timeout)
   - TLS session info (cipher suite, PSK identity)
   - Error details (if failed)

2. WHEN session progresses THEN the layer SHALL update status and timestamps
3. WHEN listing sessions THEN the layer SHALL support filtering by device, card, status, date range
4. WHEN querying sessions THEN the layer SHALL support pagination for large result sets
5. WHEN session completes THEN the layer SHALL calculate and store duration
6. WHEN analyzing sessions THEN the layer SHALL provide aggregation queries (success rate, avg duration)

### Requirement 6: Communication Log Storage

**User Story:** As a developer, I want all APDU exchanges to be logged in the database, so that I can analyze protocol behavior and debug issues.

#### Acceptance Criteria

1. WHEN logging communication THEN the layer SHALL store:
   - Log entry ID
   - Session ID (foreign key)
   - Timestamp (millisecond precision)
   - Direction (command/response)
   - Raw data (hex)
   - Decoded data (optional)
   - Status word (for responses)
   - Status message
   - Latency (ms)

2. WHEN logging THEN the layer SHALL batch inserts for performance
3. WHEN querying logs THEN the layer SHALL support filtering by session, direction, status
4. WHEN exporting logs THEN the layer SHALL support JSON and CSV formats
5. WHEN purging logs THEN the layer SHALL support retention policy (delete logs older than X days)
6. WHEN searching logs THEN the layer SHALL support hex pattern matching in raw data

### Requirement 7: Test Result Storage

**User Story:** As a QA engineer, I want test results stored in the database, so that I can track test history and generate compliance reports.

#### Acceptance Criteria

1. WHEN storing test result THEN the layer SHALL store:
   - Test run ID (UUID)
   - Test suite name
   - Test case name
   - Device ID
   - Card ICCID
   - Start/end timestamps
   - Status (passed, failed, skipped, error)
   - Duration (ms)
   - Error message (if failed)
   - Assertions (JSON array)
   - Metadata (JSON)

2. WHEN running test suite THEN the layer SHALL group results by run ID
3. WHEN querying results THEN the layer SHALL support filtering by suite, status, date range
4. WHEN generating report THEN the layer SHALL calculate pass/fail/skip counts
5. WHEN comparing runs THEN the layer SHALL identify regressions (previously passed, now failed)
6. WHEN exporting results THEN the layer SHALL support JUnit XML format for CI integration

### Requirement 8: Server Settings Storage

**User Story:** As an administrator, I want server settings stored in the database, so that configuration persists across restarts.

#### Acceptance Criteria

1. WHEN storing settings THEN the layer SHALL support:
   - PSK-TLS server configuration (port, cipher suites, timeouts)
   - Dashboard configuration (port, authentication)
   - Default device settings
   - Logging configuration
   - Retention policies

2. WHEN reading settings THEN the layer SHALL provide defaults for missing values
3. WHEN updating settings THEN the layer SHALL validate before saving
4. WHEN settings change THEN the layer SHALL emit event for live reload
5. WHEN exporting settings THEN the layer SHALL support YAML format
6. WHEN importing settings THEN the layer SHALL merge with existing configuration

### Requirement 9: Repository Pattern Implementation

**User Story:** As a developer, I want a clean repository interface for data access, so that business logic is decoupled from database details.

#### Acceptance Criteria

1. WHEN accessing data THEN the layer SHALL provide repository classes per entity
2. WHEN querying THEN repositories SHALL support:
   - `get_by_id(id)` - single entity by primary key
   - `get_all()` - all entities with optional limit
   - `find_by(**kwargs)` - query by attributes
   - `create(entity)` - insert new entity
   - `update(entity)` - update existing entity
   - `delete(id)` - remove entity
   - `exists(id)` - check existence

3. WHEN filtering THEN repositories SHALL support complex queries via filter objects
4. WHEN paginating THEN repositories SHALL return page info (total, page, per_page)
5. WHEN using transactions THEN repositories SHALL support context manager pattern
6. WHEN testing THEN repositories SHALL be mockable for unit tests

### Requirement 10: Query Optimization

**User Story:** As a developer, I want database queries to be optimized, so that the application performs well with large datasets.

#### Acceptance Criteria

1. WHEN defining tables THEN the layer SHALL create appropriate indexes
2. WHEN querying THEN the layer SHALL use eager loading to prevent N+1 queries
3. WHEN bulk inserting THEN the layer SHALL use batch operations
4. WHEN counting THEN the layer SHALL use COUNT queries instead of fetching all
5. WHEN using SQLite THEN the layer SHALL configure WAL mode for concurrent reads
6. WHEN connection pool exhausted THEN the layer SHALL queue requests with timeout

### Requirement 11: Data Export and Import

**User Story:** As a tester, I want to export and import database contents, so that I can share configurations and migrate between environments.

#### Acceptance Criteria

1. WHEN exporting THEN the layer SHALL support:
   - Full database export (all tables)
   - Selective export (specific tables/entities)
   - JSON format for portability
   - YAML format for configuration

2. WHEN importing THEN the layer SHALL:
   - Validate data structure
   - Handle conflicts (skip, overwrite, merge)
   - Report import summary (created, updated, skipped)

3. WHEN backing up THEN the layer SHALL support SQLite file copy
4. WHEN restoring THEN the layer SHALL validate backup integrity

### Requirement 12: CLI Integration

**User Story:** As a developer, I want database operations available via CLI, so that I can manage the database without code.

#### Acceptance Criteria

1. WHEN running `cardlink-db init` THEN the CLI SHALL create database and tables
2. WHEN running `cardlink-db migrate` THEN the CLI SHALL run pending migrations
3. WHEN running `cardlink-db status` THEN the CLI SHALL show connection info and migration status
4. WHEN running `cardlink-db export` THEN the CLI SHALL export data to file:
   - `--format` for JSON/YAML
   - `--tables` for selective export
   - `--output` for file path
5. WHEN running `cardlink-db import` THEN the CLI SHALL import data from file
6. WHEN running `cardlink-db purge` THEN the CLI SHALL delete old data:
   - `--older-than` for retention period
   - `--tables` for selective purge (logs, sessions)
7. WHEN running `cardlink-db stats` THEN the CLI SHALL show table row counts and sizes

### Requirement 13: Event Emission for Integration

**User Story:** As a dashboard developer, I want the database layer to emit events, so that I can update the UI when data changes.

#### Acceptance Criteria

1. WHEN device is created/updated/deleted THEN the layer SHALL emit device_changed event
2. WHEN card profile is created/updated/deleted THEN the layer SHALL emit profile_changed event
3. WHEN session is created/updated THEN the layer SHALL emit session_changed event
4. WHEN settings are updated THEN the layer SHALL emit settings_changed event
5. WHEN batch operation completes THEN the layer SHALL emit batch_completed event
6. WHEN database error occurs THEN the layer SHALL emit database_error event

## Non-Functional Requirements

### Code Architecture and Modularity

- **Repository Pattern**: Separate repository classes per entity for clean data access
- **Unit of Work**: Transaction management through session context
- **Dependency Injection**: Inject database session, not hardcoded connections
- **Schema Definition**: SQLAlchemy declarative models with clear relationships

### Performance

- **Connection pooling**: Appropriate pool size per backend (SQLite: 1, MySQL/PostgreSQL: 5-20)
- **Query latency**: Simple queries < 10ms, complex queries < 100ms
- **Bulk operations**: Support batch insert of 1000+ log entries per second
- **Index coverage**: All foreign keys and commonly queried columns indexed

### Compatibility

- **SQLite**: 3.35+ (JSON functions, WAL mode)
- **MySQL**: 8.0+ (JSON type, window functions)
- **PostgreSQL**: 12+ (JSON functions, partitioning)
- **SQLAlchemy**: 2.0+ (async support, type annotations)
- **Alembic**: Latest version for migrations

### Reliability

- **Transaction safety**: All multi-statement operations in transactions
- **Connection recovery**: Automatic reconnection on transient failures
- **Data integrity**: Foreign key constraints enforced
- **Backup support**: SQLite file backup, SQL dump for others

### Security

- **Credential handling**: Database credentials from environment variables
- **Sensitive data encryption**: PSK keys encrypted at rest
- **SQL injection prevention**: Parameterized queries via ORM
- **Access logging**: Optional query logging for audit
