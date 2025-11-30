# Tasks Document: Database Layer

## Task Overview

This document breaks down the Database Layer implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Dependencies

_Leverage:_ Python packaging standards, SQLAlchemy ecosystem, pytest testing framework

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

_Prompt:_ Role: Python package architect | Task: Set up the cardlink/database package structure with all required dependencies including SQLAlchemy 2.0+, Alembic for migrations, cryptography for PSK encryption, pyyaml for data export/import, and optional database drivers (mysqlclient, psycopg2-binary). Configure pytest fixtures for in-memory SQLite testing. | Restrictions: Use SQLAlchemy 2.0+ syntax, ensure all dependencies specify minimum versions, keep optional database drivers separate from core dependencies | Success: Package structure created with proper __init__.py files, all dependencies listed in pyproject.toml with version constraints, pytest fixtures available for testing with in-memory SQLite

- [x] 1.1. Create `cardlink/database/` package structure
- [x] 1.2. Add SQLAlchemy 2.0+ dependency to pyproject.toml
- [x] 1.3. Add Alembic dependency for migrations
- [x] 1.4. Add cryptography dependency for PSK encryption
- [x] 1.5. Add pyyaml dependency for YAML export/import
- [x] 1.6. Add optional database driver dependencies (mysqlclient, psycopg2-binary)
- [x] 1.7. Create pytest fixtures for database testing (in-memory SQLite)

### 2. Database Configuration

_Leverage:_ Environment variable parsing patterns, SQLAlchemy URL parsing, configuration validation best practices

_Requirements:_ 1

_Prompt:_ Role: Configuration system developer | Task: Create a DatabaseConfig class that parses DATABASE_URL environment variable or defaults to SQLite at data/cardlink.db. Implement backend detection properties (is_sqlite, is_mysql, is_postgresql) and connection pool configuration options (pool_size, max_overflow, timeout). Add SQL echo option for debugging. | Restrictions: Must support SQLite, MySQL, and PostgreSQL connection strings, must validate connection parameters before use, must not expose passwords in logs | Success: DatabaseConfig class correctly parses all supported database URLs, provides sensible defaults for missing configuration, includes comprehensive unit tests covering all backends and edge cases

- [x] 2.1. Create `config.py` with DatabaseConfig class
- [x] 2.2. Implement DATABASE_URL environment variable parsing
- [x] 2.3. Implement default SQLite path (`data/cardlink.db`)
- [x] 2.4. Add `is_sqlite`, `is_mysql`, `is_postgresql` properties
- [x] 2.5. Add pool configuration options (pool_size, max_overflow, timeout)
- [x] 2.6. Add echo option for SQL logging
- [x] 2.7. Write unit tests for configuration parsing

### 3. Database Manager Implementation

_Leverage:_ SQLAlchemy engine creation patterns, connection pooling strategies, context manager protocol

_Requirements:_ 1, 2

_Prompt:_ Role: Database connection manager developer | Task: Implement DatabaseManager class with initialize() for engine creation, backend-specific pool configuration (NullPool for SQLite, QueuePool for others), SQLite directory creation and WAL mode configuration, session factory methods, and context managers for transaction management. Include health check functionality and graceful shutdown. | Restrictions: Must use appropriate pool type per backend, must enable WAL mode for SQLite, must redact passwords in logs, must handle connection failures gracefully with clear error messages | Success: DatabaseManager successfully creates and manages connections to all supported backends, sessions are properly scoped with automatic commit/rollback, health checks work reliably, comprehensive unit tests cover all connection scenarios

- [x] 3.1. Create `manager.py` with DatabaseManager class
- [x] 3.2. Implement `initialize()` with engine creation
- [x] 3.3. Implement pool configuration per backend (NullPool for SQLite, QueuePool for others)
- [x] 3.4. Implement `_ensure_sqlite_directory()` for path creation
- [x] 3.5. Implement `_configure_sqlite()` with WAL mode and pragmas
- [x] 3.6. Implement `_get_safe_url()` for password redaction in logs
- [x] 3.7. Implement `create_session()` factory method
- [x] 3.8. Implement `session_scope()` context manager with commit/rollback
- [x] 3.9. Implement `create_tables()` using metadata.create_all()
- [x] 3.10. Implement `drop_tables()` using metadata.drop_all()
- [x] 3.11. Implement `close()` for connection disposal
- [x] 3.12. Implement `health_check()` with SELECT 1 query
- [x] 3.13. Write unit tests for DatabaseManager

### 4. Base Model Definition

_Leverage:_ SQLAlchemy declarative base, common model patterns, UUID generation

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8

_Prompt:_ Role: ORM model architect | Task: Create base model infrastructure including declarative_base for all models, TimestampMixin for automatic created_at/updated_at tracking, UUID generation helper, and common column type definitions. Establish conventions for primary keys, foreign keys, and constraints. | Restrictions: Must use SQLAlchemy 2.0 declarative syntax, timestamps must be UTC, UUIDs must be RFC4122 compliant, must define reusable mixins for common patterns | Success: Base model infrastructure supports all entity types, TimestampMixin automatically tracks creation and modification times, UUID generation works consistently across all models, well-documented with clear usage examples

- [x] 4.1. Create `models/__init__.py` with Base declarative_base
- [x] 4.2. Create `models/base.py` with TimestampMixin
- [x] 4.3. Implement `generate_uuid()` helper function
- [x] 4.4. Define common column types and constraints

### 5. Device Model Implementation

_Leverage:_ SQLAlchemy declarative models, JSON column types, relationship definitions

_Requirements:_ 3

_Prompt:_ Role: Data model developer | Task: Create Device model with DeviceType enum (phone/modem) and all required fields including device identifiers (id, name, imei, imsi, iccid), device information (manufacturer, model, firmware_version), connection_settings as JSON, status tracking (last_seen, is_active), and notes. Define indexes for common queries and relationships to sessions and test results. | Restrictions: Must support both phone and modem device types, IMEI/IMSI/ICCID must be optional for flexibility, connection_settings must be valid JSON, must enforce unique constraints on device identifiers where appropriate | Success: Device model stores all required device configuration, supports efficient querying by type and status, relationships enable cascade operations, comprehensive unit tests validate all fields and constraints

- [x] 5.1. Create `models/device.py` with DeviceType enum
- [x] 5.2. Create Device model with all columns
- [x] 5.3. Add device identifiers (id, name, imei, imsi, iccid)
- [x] 5.4. Add device info (manufacturer, model, firmware_version)
- [x] 5.5. Add connection_settings JSON column
- [x] 5.6. Add status fields (last_seen, is_active)
- [x] 5.7. Add notes Text column
- [x] 5.8. Define indexes (device_type, iccid, last_seen)
- [x] 5.9. Define relationships to sessions and test_results
- [x] 5.10. Write unit tests for Device model

### 6. Card Profile Model Implementation

_Leverage:_ SQLAlchemy models, JSON storage for complex configuration, foreign key relationships

_Requirements:_ 4

_Prompt:_ Role: Data model developer | Task: Create CardProfile model with ICCID as primary key, fields for IMSI, card_type, ATR, PSK credentials (identity and encrypted key), admin_url, and JSON columns for trigger_config, bip_config, and security_domains. Define indexes for efficient querying and relationships to sessions and test results. | Restrictions: ICCID must be primary key, PSK key must be stored encrypted, admin_url limited to 255 characters, JSON fields must be nullable for optional configurations | Success: CardProfile model stores all UICC card information, supports encrypted PSK storage, enables efficient queries by card type and PSK identity, comprehensive unit tests cover all scenarios

- [x] 6.1. Create `models/card_profile.py` with CardProfile model
- [x] 6.2. Add ICCID primary key and IMSI
- [x] 6.3. Add card_type and atr columns
- [x] 6.4. Add psk_identity and psk_key_encrypted columns
- [x] 6.5. Add admin_url column with 255 char limit
- [x] 6.6. Add trigger_config JSON column
- [x] 6.7. Add bip_config JSON column
- [x] 6.8. Add security_domains JSON column
- [x] 6.9. Define indexes (card_type, psk_identity)
- [x] 6.10. Define relationships to sessions and test_results
- [x] 6.11. Write unit tests for CardProfile model

### 7. OTA Session Model Implementation

_Leverage:_ SQLAlchemy models, enum types, timestamp handling, foreign key relationships

_Requirements:_ 5

_Prompt:_ Role: Data model developer | Task: Create OTASession model with SessionStatus enum (pending, active, completed, failed, timeout) and UUID primary key. Include foreign keys to device and card, session metadata (type, status, timestamps, duration), TLS information (cipher_suite, psk_identity), and error tracking. Define indexes for efficient querying and relationships to related entities. | Restrictions: Must use UUID for primary key, must track start/end times and calculate duration, must support all session statuses, must store TLS session details for analysis | Success: OTASession model captures complete session lifecycle, supports efficient queries by device/card/status/date, relationships enable navigation to logs and related entities, unit tests validate all state transitions

- [x] 7.1. Create `models/session.py` with SessionStatus enum
- [x] 7.2. Create OTASession model with UUID primary key
- [x] 7.3. Add device_id and card_iccid foreign keys
- [x] 7.4. Add session_type and status columns
- [x] 7.5. Add timestamp columns (started_at, ended_at, duration_ms)
- [x] 7.6. Add TLS info columns (cipher_suite, psk_identity)
- [x] 7.7. Add error columns (error_code, error_message)
- [x] 7.8. Define indexes (device_id, card_iccid, status, created_at)
- [x] 7.9. Define relationships (device, card, comm_logs)
- [x] 7.10. Write unit tests for OTASession model

### 8. Communication Log Model Implementation

_Leverage:_ SQLAlchemy models, auto-increment keys, high-precision timestamps, text storage

_Requirements:_ 6

_Prompt:_ Role: Data model developer | Task: Create CommLog model for storing APDU exchanges with auto-increment primary key, session foreign key, millisecond-precision timestamp, direction indicator (command/response), raw_data and optional decoded_data as text, status_word and status_message for responses, and latency tracking. Define indexes for efficient log retrieval. | Restrictions: Must support high-volume inserts, timestamps must have millisecond precision, raw_data must store hex strings, must index by session_id and timestamp for fast queries | Success: CommLog model efficiently stores APDU exchanges, supports batch inserts for performance, enables fast retrieval by session and filtering by direction/status, unit tests verify all fields and query performance

- [x] 8.1. Create `models/comm_log.py` with CommLog model
- [x] 8.2. Add auto-increment primary key
- [x] 8.3. Add session_id foreign key
- [x] 8.4. Add timestamp column with millisecond precision
- [x] 8.5. Add direction column (command/response)
- [x] 8.6. Add raw_data Text column
- [x] 8.7. Add decoded_data Text column (optional)
- [x] 8.8. Add status_word and status_message columns
- [x] 8.9. Add latency_ms Float column
- [x] 8.10. Define indexes (session_id, timestamp, direction)
- [x] 8.11. Write unit tests for CommLog model

### 9. Test Result Model Implementation

_Leverage:_ SQLAlchemy models, UUID keys, enum types, JSON storage for complex data

_Requirements:_ 7

_Prompt:_ Role: Data model developer | Task: Create TestResult model with TestStatus enum (passed, failed, skipped, error) and UUID primary key. Include run_id for grouping, suite_name and test_name, foreign keys to device and card, timestamp tracking with duration calculation, status and error_message, and JSON columns for assertions and metadata. Define indexes for efficient test result queries. | Restrictions: Must use UUID for primary key, must group results by run_id, must track execution time accurately, JSON fields must support complex assertion data structures | Success: TestResult model stores complete test execution information, supports efficient queries by run/suite/status, enables test result analysis and comparison, comprehensive unit tests cover all test statuses

- [x] 9.1. Create `models/test_result.py` with TestStatus enum
- [x] 9.2. Create TestResult model with UUID primary key
- [x] 9.3. Add run_id for grouping test runs
- [x] 9.4. Add suite_name and test_name columns
- [x] 9.5. Add device_id and card_iccid foreign keys
- [x] 9.6. Add timestamp columns (started_at, ended_at, duration_ms)
- [x] 9.7. Add status enum column
- [x] 9.8. Add error_message Text column
- [x] 9.9. Add assertions and metadata JSON columns
- [x] 9.10. Define indexes (run_id, suite_name, status, created_at)
- [x] 9.11. Write unit tests for TestResult model

### 10. Setting Model Implementation

_Leverage:_ SQLAlchemy models, key-value storage pattern, JSON for flexible value types

_Requirements:_ 8

_Prompt:_ Role: Data model developer | Task: Create Setting model with key as primary key, value stored as JSON for type flexibility, and description and category columns for organization. Define index on category for efficient retrieval of related settings. | Restrictions: Key must be unique primary key, value must be JSON to support any data type, category must support grouping of related settings | Success: Setting model provides flexible key-value storage, supports any value type through JSON, enables efficient queries by category, unit tests validate storage and retrieval of various data types

- [x] 10.1. Create `models/setting.py` with Setting model
- [x] 10.2. Add key primary key column
- [x] 10.3. Add value JSON column
- [x] 10.4. Add description and category columns
- [x] 10.5. Define index on category
- [x] 10.6. Write unit tests for Setting model

### 11. Unit of Work Implementation

_Leverage:_ Unit of Work pattern, context manager protocol, dependency injection

_Requirements:_ 9

_Prompt:_ Role: Transaction management developer | Task: Implement UnitOfWork class as context manager that creates database session on entry, commits on successful exit, and rolls back on exceptions. Provide repository factory method and properties for accessing all repository types (devices, cards, sessions, logs, tests, settings). | Restrictions: Must implement __enter__ and __exit__ correctly, must ensure single session per unit of work, must rollback on any exception, repositories must share the same session | Success: UnitOfWork enables clean transaction boundaries, all repositories share session within unit of work, automatic commit/rollback works correctly, comprehensive unit tests cover all transaction scenarios

- [x] 11.1. Create `unit_of_work.py` with UnitOfWork class
- [x] 11.2. Implement `__enter__` to create session
- [x] 11.3. Implement `__exit__` with rollback on exception
- [x] 11.4. Implement `commit()` method
- [x] 11.5. Implement `rollback()` method
- [x] 11.6. Implement `close()` method
- [x] 11.7. Implement `_get_repository()` factory method
- [x] 11.8. Add repository properties (devices, cards, sessions, logs, tests, settings)
- [x] 11.9. Write unit tests for UnitOfWork

### 12. Base Repository Implementation

_Leverage:_ Repository pattern, generic programming, pagination utilities

_Requirements:_ 9, 10

_Prompt:_ Role: Repository pattern architect | Task: Create BaseRepository generic class providing common CRUD operations including get_by_id, get_all, find_by, create, update, delete, exists, count, and paginate. Implement Page dataclass for pagination results. Ensure all operations use proper error handling and support bulk operations. | Restrictions: Must be generic to work with any model type, must use parameterized queries to prevent SQL injection, pagination must include total count, bulk operations must be atomic | Success: BaseRepository provides complete CRUD interface, supports filtering and pagination, handles errors gracefully, serves as foundation for entity-specific repositories, comprehensive unit tests cover all operations

- [x] 12.1. Create `repositories/base.py` with Page dataclass
- [x] 12.2. Create BaseRepository generic class
- [x] 12.3. Implement `get_by_id(id)` method
- [x] 12.4. Implement `get_all(limit)` method
- [x] 12.5. Implement `find_by(**kwargs)` method
- [x] 12.6. Implement `find_one_by(**kwargs)` method
- [x] 12.7. Implement `create(entity)` method
- [x] 12.8. Implement `create_all(entities)` for bulk insert
- [x] 12.9. Implement `update(entity)` method
- [x] 12.10. Implement `delete(entity)` method
- [x] 12.11. Implement `delete_by_id(id)` method
- [x] 12.12. Implement `exists(id)` method
- [x] 12.13. Implement `count()` method
- [x] 12.14. Implement `count_by(**kwargs)` method
- [x] 12.15. Implement `paginate(page, per_page, order_by, descending)` method
- [x] 12.16. Write unit tests for BaseRepository

### 13. Device Repository Implementation

_Leverage:_ Repository pattern inheritance, SQLAlchemy query API, pattern matching

_Requirements:_ 3, 9

_Prompt:_ Role: Repository developer | Task: Create DeviceRepository extending BaseRepository with device-specific queries including find_by_type, find_phones, find_modems, find_active, find_recent, search with pattern matching, update_last_seen, find_by_iccid, and deactivate. Optimize queries with appropriate filtering and indexing. | Restrictions: Must extend BaseRepository, search must support partial matching on name/ID/IMEI/IMSI, must update last_seen efficiently, must handle device not found errors | Success: DeviceRepository provides all device-specific queries, supports efficient filtering by type and status, search works with partial matches, unit tests cover all query methods and edge cases

- [x] 13.1. Create `repositories/device.py` with DeviceRepository class
- [x] 13.2. Implement `find_by_type(device_type)` method
- [x] 13.3. Implement `find_phones()` method
- [x] 13.4. Implement `find_modems()` method
- [x] 13.5. Implement `find_active()` method
- [x] 13.6. Implement `find_recent(hours)` method
- [x] 13.7. Implement `search(query)` with ILIKE pattern matching
- [x] 13.8. Implement `update_last_seen(device_id)` method
- [x] 13.9. Implement `find_by_iccid(iccid)` method
- [x] 13.10. Implement `deactivate(device_id)` method
- [x] 13.11. Write unit tests for DeviceRepository

### 14. Card Repository Implementation

_Leverage:_ Repository pattern, Fernet encryption, environment configuration

_Requirements:_ 4, 9

_Prompt:_ Role: Repository developer | Task: Create CardRepository extending BaseRepository with encryption support for PSK keys using Fernet cipher. Implement create_with_psk for encrypted storage, get_psk_key for decryption, update_psk, find_by_type, find_with_psk, find_by_admin_url, and export_profile with optional key inclusion. Load encryption key from environment variable. | Restrictions: Must encrypt PSK keys before storage, must never log unencrypted keys, encryption key must come from CARDLINK_ENCRYPTION_KEY environment variable, export must support excluding sensitive data | Success: CardRepository securely stores and retrieves PSK keys, encryption/decryption works correctly, provides card-specific queries, export supports both secure and full formats, comprehensive unit tests include encryption validation

- [x] 14.1. Create `repositories/card.py` with CardRepository class
- [x] 14.2. Implement `_get_encryption_key()` from environment
- [x] 14.3. Initialize Fernet cipher for encryption
- [x] 14.4. Implement `create_with_psk(profile, psk_key)` with encryption
- [x] 14.5. Implement `get_psk_key(iccid)` with decryption
- [x] 14.6. Implement `update_psk(iccid, identity, key)` method
- [x] 14.7. Implement `find_by_type(card_type)` method
- [x] 14.8. Implement `find_with_psk()` method
- [x] 14.9. Implement `find_by_admin_url(url)` method
- [x] 14.10. Implement `export_profile(iccid, include_key)` method
- [x] 14.11. Write unit tests for CardRepository with encryption

### 15. Session Repository Implementation

_Leverage:_ Repository pattern, timestamp handling, duration calculation, aggregation queries

_Requirements:_ 5, 9, 10

_Prompt:_ Role: Repository developer | Task: Create SessionRepository extending BaseRepository with session lifecycle methods (create_session, start_session, complete_session, fail_session), TLS info tracking (set_tls_info), query methods (find_by_device, find_by_card, find_by_status, find_active, find_by_date_range), and statistics aggregation (get_statistics with success rate and average duration). | Restrictions: Must calculate duration accurately from timestamps, must support session state transitions, statistics must use database aggregation not in-memory, date range queries must handle timezones correctly | Success: SessionRepository manages complete session lifecycle, provides efficient queries by device/card/status/date, statistics methods return accurate aggregated data, unit tests validate all session operations

- [x] 15.1. Create `repositories/session.py` with SessionRepository class
- [x] 15.2. Implement `create_session(device_id, card_iccid, type)` method
- [x] 15.3. Implement `start_session(session_id)` with timestamp
- [x] 15.4. Implement `complete_session(session_id)` with duration calculation
- [x] 15.5. Implement `fail_session(session_id, error_code, message)` method
- [x] 15.6. Implement `set_tls_info(session_id, cipher, psk_identity)` method
- [x] 15.7. Implement `find_by_device(device_id, limit)` method
- [x] 15.8. Implement `find_by_card(iccid, limit)` method
- [x] 15.9. Implement `find_by_status(status)` method
- [x] 15.10. Implement `find_active()` method
- [x] 15.11. Implement `find_by_date_range(start, end)` method
- [x] 15.12. Implement `get_statistics(days)` with aggregations
- [x] 15.13. Write unit tests for SessionRepository

### 16. Log Repository Implementation

_Leverage:_ Repository pattern, batch insert optimization, hex pattern matching, retention policies

_Requirements:_ 6, 9, 10

_Prompt:_ Role: Repository developer | Task: Create LogRepository extending BaseRepository with high-performance logging support including batch buffer, add_log, add_log_batch, flush_batch using bulk_save_objects, query methods (find_by_session, find_by_direction, find_commands, find_responses, find_by_status, find_errors), search_hex for pattern matching, purge_old for retention, and export_session_logs. | Restrictions: Must use batch inserts for performance, buffer size must be configurable, must flush buffer before queries, hex search must be efficient, purge must use bulk delete, export must handle large result sets | Success: LogRepository handles high-volume APDU logging efficiently, batch operations work correctly with automatic flushing, query methods provide fast log retrieval, retention policy works reliably, unit tests validate performance and correctness

- [x] 16.1. Create `repositories/log.py` with LogRepository class
- [x] 16.2. Implement batch buffer with configurable size
- [x] 16.3. Implement `add_log(session_id, direction, raw_data, ...)` method
- [x] 16.4. Implement `add_log_batch(...)` for high-throughput logging
- [x] 16.5. Implement `flush_batch()` using bulk_save_objects
- [x] 16.6. Implement `find_by_session(session_id)` method
- [x] 16.7. Implement `find_by_direction(session_id, direction)` method
- [x] 16.8. Implement `find_commands(session_id)` helper
- [x] 16.9. Implement `find_responses(session_id)` helper
- [x] 16.10. Implement `find_by_status(session_id, status_word)` method
- [x] 16.11. Implement `find_errors(session_id)` for non-9000 responses
- [x] 16.12. Implement `search_hex(pattern, session_id)` method
- [x] 16.13. Implement `purge_old(days)` for retention
- [x] 16.14. Implement `count_by_session(session_id)` method
- [x] 16.15. Implement `export_session_logs(session_id)` method
- [x] 16.16. Write unit tests for LogRepository

### 17. Test Repository Implementation

_Leverage:_ Repository pattern, test result aggregation, JUnit XML generation, regression detection

_Requirements:_ 7, 9, 11

_Prompt:_ Role: Repository developer | Task: Create TestRepository extending BaseRepository with test result management including create_result, query methods (find_by_run, find_by_suite, find_by_status, find_failures), analysis methods (get_run_summary with statistics, compare_runs for regression detection), and export_junit_xml for CI integration. | Restrictions: Must group results by run_id, statistics must be calculated in database, regression detection must compare by test name, JUnit XML must follow standard schema | Success: TestRepository manages test results efficiently, provides comprehensive query and analysis methods, statistics are accurate and performant, JUnit XML export works with CI systems, unit tests cover all operations

- [x] 17.1. Create `repositories/test.py` with TestRepository class
- [x] 17.2. Implement `create_result(...)` with all parameters
- [x] 17.3. Implement `find_by_run(run_id)` method
- [x] 17.4. Implement `find_by_suite(suite_name, limit)` method
- [x] 17.5. Implement `find_by_status(status)` method
- [x] 17.6. Implement `find_failures(run_id)` method
- [x] 17.7. Implement `get_run_summary(run_id)` with statistics
- [x] 17.8. Implement `compare_runs(run_id1, run_id2)` for regressions
- [x] 17.9. Implement `export_junit_xml(run_id)` method
- [x] 17.10. Write unit tests for TestRepository

### 18. Settings Repository Implementation

_Leverage:_ Repository pattern, default value fallback, YAML serialization, configuration management

_Requirements:_ 8, 9, 11

_Prompt:_ Role: Repository developer | Task: Create SettingsRepository extending BaseRepository with settings management including DEFAULTS dictionary, get_value with default fallback chain, set_value with validation, get_by_category, get_all_settings merged with defaults, export_yaml, import_yaml with merge support, and reset_to_defaults. | Restrictions: Must provide defaults for all core settings, must validate values before saving, must handle missing settings gracefully, YAML export must be human-readable | Success: SettingsRepository provides complete configuration management, defaults work correctly, YAML import/export preserves data, category-based organization works, unit tests cover all settings operations

- [x] 18.1. Create `repositories/settings.py` with SettingsRepository class
- [x] 18.2. Define DEFAULTS dictionary with all default settings
- [x] 18.3. Implement `get_value(key, default)` with fallback chain
- [x] 18.4. Implement `set_value(key, value, description, category)` method
- [x] 18.5. Implement `get_by_category(category)` method
- [x] 18.6. Implement `get_all_settings()` merged with defaults
- [x] 18.7. Implement `export_yaml()` method
- [x] 18.8. Implement `import_yaml(yaml_str)` method
- [x] 18.9. Implement `reset_to_defaults(category)` method
- [x] 18.10. Write unit tests for SettingsRepository

### 19. Event Emitter Implementation

_Leverage:_ Observer pattern, thread-safe event handling, dataclass for event structure

_Requirements:_ 13

_Prompt:_ Role: Event system developer | Task: Create DatabaseEvent dataclass and DatabaseEventEmitter class with event registration (on), unregistration (off), and emission (emit) methods. Support wildcard handlers for all events and thread-safe handler management using Lock. Enable integration components to subscribe to database changes. | Restrictions: Must be thread-safe for concurrent access, must support wildcard subscriptions, event emission must not block database operations, must handle handler exceptions gracefully | Success: DatabaseEventEmitter enables reliable event-driven integration, supports multiple handlers per event type, wildcard subscriptions work correctly, thread-safe operations verified, unit tests cover all event scenarios

- [x] 19.1. Create `events.py` with DatabaseEvent dataclass
- [x] 19.2. Create DatabaseEventEmitter class
- [x] 19.3. Implement `on(event_type, handler)` registration
- [x] 19.4. Implement `off(event_type, handler)` removal
- [x] 19.5. Implement `emit(event_type, entity_type, entity_id, data)` method
- [x] 19.6. Add wildcard ('*') handler support
- [x] 19.7. Add thread-safe handler management with Lock
- [x] 19.8. Write unit tests for event emission

### 20. Data Exporter Implementation

_Leverage:_ Serialization patterns, format conversion, data mapping

_Requirements:_ 11

_Prompt:_ Role: Data export developer | Task: Create DataExporter class with export_all and export_selective methods supporting JSON and YAML formats. Implement table-specific export helpers (_export_devices, _export_cards without keys by default, _export_sessions, _export_settings) and entity-to-dict converters preserving all data while handling special types. | Restrictions: Must not export PSK keys by default, must handle JSON serialization of dates and UUIDs, must support selective table export, output must be valid JSON/YAML | Success: DataExporter produces complete database exports in multiple formats, selective export works for specified tables, sensitive data excluded by default, output is valid and can be re-imported, unit tests verify all export scenarios

- [x] 20.1. Create `export_import.py` with DataExporter class
- [x] 20.2. Implement `export_all(format)` method
- [x] 20.3. Implement `export_selective(tables, format)` method
- [x] 20.4. Implement `_export_devices()` helper
- [x] 20.5. Implement `_export_cards()` helper (without keys by default)
- [x] 20.6. Implement `_export_sessions()` helper
- [x] 20.7. Implement `_export_settings()` helper
- [x] 20.8. Implement `_device_to_dict()` converter
- [x] 20.9. Implement `_session_to_dict()` converter
- [x] 20.10. Write unit tests for DataExporter

### 21. Data Importer Implementation

_Leverage:_ Data validation, conflict resolution strategies, transaction handling

_Requirements:_ 11

_Prompt:_ Role: Data import developer | Task: Create DataImporter class with import_data method supporting JSON/YAML formats and conflict resolution modes (skip, overwrite, merge). Implement table-specific import helpers (_import_devices, _import_cards, _import_settings) with validation, entity creation/update helpers, and import result reporting. | Restrictions: Must validate data structure before import, must handle conflicts according to mode, must use transactions for atomicity, must report detailed results (created/updated/skipped counts) | Success: DataImporter successfully imports exported data, conflict resolution works correctly for all modes, invalid data is rejected with clear errors, transactions ensure atomicity, unit tests cover all import scenarios

- [x] 21.1. Create DataImporter class in `export_import.py`
- [x] 21.2. Implement `import_data(data_str, format, conflict_mode)` method
- [x] 21.3. Implement `_import_devices(devices, conflict_mode, results)` helper
- [x] 21.4. Implement `_import_cards(cards, conflict_mode, results)` helper
- [x] 21.5. Implement `_import_settings(settings, results)` helper
- [x] 21.6. Implement `_create_device(data)` helper
- [x] 21.7. Implement `_update_device(device, data)` helper
- [x] 21.8. Implement `_create_card(data)` helper
- [x] 21.9. Implement `_update_card(profile, data)` helper
- [x] 21.10. Write unit tests for DataImporter

### 22. Alembic Migration Setup

_Leverage:_ Alembic migration framework, SQLAlchemy metadata, version control for schema

_Requirements:_ 2

_Prompt:_ Role: Database migration engineer | Task: Initialize Alembic with migrations directory, configure alembic.ini to support DATABASE_URL from environment, configure env.py to import all models for auto-generation, create initial migration with all tables, document migration workflow, and write helper functions for common migration tasks. | Restrictions: Must support all database backends, must handle SQLite ALTER TABLE limitations, auto-generation must detect all model changes, migrations must be reversible where possible | Success: Alembic is properly configured for all backends, initial migration creates complete schema, auto-generation detects model changes accurately, documentation enables developers to create and apply migrations, upgrade/downgrade operations work correctly

- [x] 22.1. Initialize Alembic with `alembic init migrations`
- [x] 22.2. Configure `alembic.ini` with DATABASE_URL support
- [x] 22.3. Configure `migrations/env.py` with model imports
- [x] 22.4. Create initial migration with all tables
- [x] 22.5. Document migration workflow in README
- [x] 22.6. Write migration helper functions

### 23. Exception Handling

_Leverage:_ Exception hierarchy, error context, decorator patterns

_Requirements:_ 1, 2, 9

_Prompt:_ Role: Error handling architect | Task: Create exception hierarchy with DatabaseError base class and specific exceptions (ConnectionError, MigrationError, IntegrityError, NotFoundError). Implement error handling decorators for repository methods to provide consistent error context and logging. | Restrictions: Must preserve original exception context, must provide actionable error messages, must not expose sensitive data in errors, decorators must not impact performance significantly | Success: Exception hierarchy provides clear error types, decorators ensure consistent error handling across repositories, error messages are helpful for debugging, unit tests verify exception handling paths

- [x] 23.1. Create `exceptions.py` with DatabaseError base class
- [x] 23.2. Define ConnectionError exception
- [x] 23.3. Define MigrationError exception
- [x] 23.4. Define IntegrityError exception
- [x] 23.5. Define NotFoundError exception
- [x] 23.6. Add error handling decorators for repositories
- [x] 23.7. Write tests for exception handling

### 24. CLI: Init Command

_Leverage:_ Click framework, database initialization patterns, user feedback

_Requirements:_ 12

_Prompt:_ Role: CLI developer | Task: Create cardlink/cli/db.py with Click group and implement init command that creates database and tables. Add --force flag to drop existing tables, display success message with table count, handle connection errors with helpful troubleshooting messages. | Restrictions: Must confirm before dropping tables unless --force is used, must provide clear error messages for connection failures, must display helpful next steps after initialization | Success: Init command successfully creates database and all tables, --force flag works safely with confirmation, error messages help users fix connection issues, CLI tests verify all scenarios

- [x] 24.1. Create `cardlink/cli/db.py` with Click group
- [x] 24.2. Implement `init` command
- [x] 24.3. Add `--force` flag to drop existing tables
- [x] 24.4. Display success message with table count
- [x] 24.5. Handle connection errors with helpful messages
- [x] 24.6. Write CLI tests for init command

### 25. CLI: Migrate Command

_Leverage:_ Alembic API, Click options, dry-run patterns

_Requirements:_ 2, 12

_Prompt:_ Role: CLI developer | Task: Implement migrate command that runs pending database migrations. Add --revision option for targeting specific revision, --dry-run flag to show SQL without executing, display migration status before and after, handle migration errors with rollback information. | Restrictions: Must show pending migrations before applying, must support dry-run mode for safety, must handle migration failures gracefully with rollback, must display clear success/failure messages | Success: Migrate command applies pending migrations correctly, --revision targets specific versions, --dry-run shows SQL without executing, error handling provides rollback guidance, CLI tests cover all migration scenarios

- [x] 25.1. Implement `migrate` command
- [x] 25.2. Add `--revision` option for specific revision
- [x] 25.3. Add `--dry-run` flag to show SQL without executing
- [x] 25.4. Display migration status before and after
- [x] 25.5. Handle migration errors with rollback info
- [x] 25.6. Write CLI tests for migrate command

### 26. CLI: Status Command

_Leverage:_ Database introspection, Click formatting, verbosity levels

_Requirements:_ 1, 2, 12

_Prompt:_ Role: CLI developer | Task: Implement status command that displays connection information (backend, URL with password redacted), migration status (current revision, pending migrations), and optionally table details. Add --verbose flag for table row counts and additional details. | Restrictions: Must redact passwords in connection URL, must handle connection failures gracefully, verbose mode must not impact performance significantly, output must be readable | Success: Status command provides comprehensive database information, passwords are never displayed, migration status is accurate, --verbose shows useful details, CLI tests verify all output scenarios

- [x] 26.1. Implement `status` command
- [x] 26.2. Display connection info (backend, URL with password redacted)
- [x] 26.3. Display migration status (current revision, pending)
- [x] 26.4. Add `--verbose` flag for table details
- [x] 26.5. Display table row counts in verbose mode
- [x] 26.6. Write CLI tests for status command

### 27. CLI: Export Command

_Leverage:_ Data export functionality, Click options, output handling

_Requirements:_ 11, 12

_Prompt:_ Role: CLI developer | Task: Implement export command that exports database contents to JSON or YAML. Add --format option, --tables for selective export, --output for file path (default stdout), display export summary with record counts. | Restrictions: Must support JSON and YAML formats, must handle large exports efficiently, must default to stdout for piping, selective export must validate table names | Success: Export command produces valid output files, format selection works correctly, selective export filters tables properly, summary shows useful statistics, CLI tests verify all export options

- [x] 27.1. Implement `export` command
- [x] 27.2. Add `--format` option (json, yaml)
- [x] 27.3. Add `--tables` option for selective export
- [x] 27.4. Add `--output` option for file path
- [x] 27.5. Default to stdout if no output file
- [x] 27.6. Display export summary (record counts)
- [x] 27.7. Write CLI tests for export command

### 28. CLI: Import Command

_Leverage:_ Data import functionality, Click options, confirmation patterns

_Requirements:_ 11, 12

_Prompt:_ Role: CLI developer | Task: Implement import command that imports database contents from JSON or YAML file. Add --format option with auto-detection, --conflict option for resolution strategy (skip/overwrite/merge), display import preview, add --dry-run flag, show import summary. | Restrictions: Must validate input format, must preview changes before applying, must confirm destructive operations, dry-run must not modify database, conflict resolution must be clearly explained | Success: Import command successfully imports exported data, format auto-detection works, conflict resolution applies correctly, preview shows what will change, dry-run mode is safe, CLI tests cover all scenarios

- [x] 28.1. Implement `import` command with file argument
- [x] 28.2. Add `--format` option (json, yaml, auto-detect)
- [x] 28.3. Add `--conflict` option (skip, overwrite, merge)
- [x] 28.4. Display import preview before applying
- [x] 28.5. Add `--dry-run` flag to preview without changes
- [x] 28.6. Display import summary (created, updated, skipped)
- [x] 28.7. Write CLI tests for import command

### 29. CLI: Purge Command

_Leverage:_ Retention policies, Click confirmation, bulk operations

_Requirements:_ 6, 12

_Prompt:_ Role: CLI developer | Task: Implement purge command that deletes old data from specified tables. Add --older-than option with days parameter, --tables option for selective purging (logs, sessions, tests), confirmation prompt before deletion, --yes flag to skip confirmation, display purge summary. | Restrictions: Must require confirmation for safety, must only purge specified tables, must calculate age correctly, must use bulk delete for performance, must handle empty results gracefully | Success: Purge command safely removes old data, age calculation is accurate, confirmation prevents accidents, --yes enables automation, summary shows deleted counts, CLI tests verify all purge scenarios

- [x] 29.1. Implement `purge` command
- [x] 29.2. Add `--older-than` option with days parameter
- [x] 29.3. Add `--tables` option (logs, sessions, tests)
- [x] 29.4. Add confirmation prompt before deletion
- [x] 29.5. Add `--yes` flag to skip confirmation
- [x] 29.6. Display purge summary (deleted counts)
- [x] 29.7. Write CLI tests for purge command

### 30. CLI: Stats Command

_Leverage:_ Database statistics, Click formatting, JSON output

_Requirements:_ 12

_Prompt:_ Role: CLI developer | Task: Implement stats command that displays database statistics including table row counts, database size (SQLite file size or estimated for others), and recent activity summary. Add --json flag for machine-readable output. | Restrictions: Must calculate statistics efficiently, size estimation must be reasonable for non-SQLite, recent activity must use database queries not scan, JSON output must be valid | Success: Stats command provides useful database metrics, row counts are accurate, size calculation works for all backends, --json produces valid parseable output, CLI tests verify statistics accuracy

- [x] 30.1. Implement `stats` command
- [x] 30.2. Display table row counts
- [x] 30.3. Display database size (SQLite file size, others estimated)
- [x] 30.4. Display recent activity summary
- [x] 30.5. Add `--json` flag for machine-readable output
- [x] 30.6. Write CLI tests for stats command

### 31. CLI Entry Point

_Leverage:_ Python entry points, Click global options, version management

_Requirements:_ 12

_Prompt:_ Role: CLI architect | Task: Register cardlink-db entry point in pyproject.toml, add version option to CLI group, add global --database option for DATABASE_URL override, add global --verbose option for debug logging, write integration tests for complete CLI workflows. | Restrictions: Must follow Click best practices, global options must work for all commands, version must match package version, logging must be configurable, entry point must be installable | Success: CLI is installable via pip with cardlink-db command, global options work consistently, version display is correct, verbose mode enables debug output, integration tests verify end-to-end workflows

- [x] 31.1. Register `cardlink-db` entry point in pyproject.toml
- [x] 31.2. Add version option to CLI group
- [x] 31.3. Add global `--database` option for URL override
- [x] 31.4. Add global `--verbose` option for debug logging
- [x] 31.5. Write integration tests for complete CLI workflows

### 32. Integration with Other Components

_Leverage:_ Event emission, dependency injection, integration patterns

_Requirements:_ 3, 4, 5, 6, 7, 13

_Prompt:_ Role: Integration developer | Task: Add event emission to repository create/update/delete operations, create database initialization helper for server startup, add session logging integration for PSK-TLS server, device profile integration for phone/modem controllers, test result integration for test runner, write integration tests with mock components. | Restrictions: Must not tightly couple to other components, event emission must be optional and non-blocking, initialization must handle startup errors, integrations must use dependency injection | Success: Database layer emits events on all data changes, server startup initializes database correctly, PSK-TLS server logs sessions, device controllers use device profiles, test runner stores results, integration tests verify all interactions

- [x] 32.1. Add event emission to repository create/update/delete operations
- [x] 32.2. Create database initialization helper for server startup
- [x] 32.3. Add session logging integration for PSK-TLS server
- [x] 32.4. Add device profile integration for phone/modem controllers
- [x] 32.5. Add test result integration for test runner
- [x] 32.6. Write integration tests with mock components

### 33. Performance Optimization

_Leverage:_ Indexing strategies, query optimization, caching, monitoring

_Requirements:_ 10

_Prompt:_ Role: Performance engineer | Task: Create index verification script, implement optional query performance logging, add connection pool monitoring, tune log batch size for optimal throughput, implement query result caching for settings, write performance benchmarks for critical operations. | Restrictions: Must not impact correctness, logging must be optional to avoid overhead, cache must invalidate on updates, benchmarks must use realistic data volumes, optimizations must work across all backends | Success: Index verification confirms all required indexes exist, query logging identifies slow queries, connection pool metrics help tuning, batch size optimization improves throughput, settings cache reduces database load, benchmarks demonstrate performance targets are met

- [x] 33.1. Add index creation verification script
- [x] 33.2. Implement query performance logging (optional)
- [x] 33.3. Add connection pool monitoring
- [x] 33.4. Implement log batch size tuning
- [x] 33.5. Add query result caching for settings
- [x] 33.6. Write performance benchmarks

### 34. Documentation

_Leverage:_ Python docstrings, Markdown documentation, example code

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

_Prompt:_ Role: Technical writer | Task: Write comprehensive module docstrings for all classes explaining purpose and usage, document DATABASE_URL format for each backend with examples, document migration workflow with step-by-step instructions, create CLI usage examples for all commands, document encryption key setup for PSK storage, add troubleshooting guide for common database errors. | Restrictions: Must follow Python docstring conventions, examples must be runnable, migration workflow must cover common scenarios, troubleshooting guide must address real issues, documentation must stay in sync with code | Success: All classes have clear docstrings with examples, DATABASE_URL documentation covers all backends, migration workflow is easy to follow, CLI examples demonstrate all features, encryption setup is clearly explained, troubleshooting guide helps users resolve issues quickly

- [x] 34.1. Write module docstrings for all classes
- [x] 34.2. Document DATABASE_URL format for each backend
- [x] 34.3. Document migration workflow
- [x] 34.4. Create CLI usage examples
- [x] 34.5. Document encryption key setup for PSK storage
- [x] 34.6. Add troubleshooting guide for common database errors

## Task Dependencies

```
1 (Setup)
├── 2 (Config)
│   └── 3 (Manager)
├── 4 (Base Model)
│   ├── 5 (Device Model)
│   ├── 6 (Card Model)
│   ├── 7 (Session Model)
│   ├── 8 (CommLog Model)
│   ├── 9 (TestResult Model)
│   └── 10 (Setting Model)
├── 11 (UnitOfWork) ← depends on 3, 12
├── 12 (Base Repository) ← depends on 4
│   ├── 13 (Device Repository) ← depends on 5
│   ├── 14 (Card Repository) ← depends on 6
│   ├── 15 (Session Repository) ← depends on 7
│   ├── 16 (Log Repository) ← depends on 8
│   ├── 17 (Test Repository) ← depends on 9
│   └── 18 (Settings Repository) ← depends on 10
├── 19 (Event Emitter)
├── 20-21 (Export/Import) ← depends on 11, 13-18
├── 22 (Alembic) ← depends on all models
└── 23 (Exceptions)

CLI Tasks (24-31) ← depend on corresponding components
32 (Integration) ← depends on all components
33 (Performance) ← can run after core implementation
34 (Documentation) ← finalize after implementation
```

## Estimated Effort

| Task Group | Tasks | Complexity |
|------------|-------|------------|
| Setup | 1.1-1.7 | Low |
| Config | 2.1-2.7 | Low |
| Manager | 3.1-3.13 | Medium |
| Models | 4-10 | Medium |
| Unit of Work | 11.1-11.9 | Low |
| Base Repository | 12.1-12.16 | Medium |
| Entity Repositories | 13-18 | Medium |
| Event Emitter | 19.1-19.8 | Low |
| Export/Import | 20-21 | Medium |
| Alembic | 22.1-22.6 | Medium |
| Exceptions | 23.1-23.7 | Low |
| CLI Commands | 24-31 | Medium |
| Integration | 32.1-32.6 | Medium |
| Performance | 33.1-33.6 | Medium |
| Documentation | 34.1-34.6 | Low |

## Notes

- SQLite is the default for development and single-user deployments
- MySQL/PostgreSQL recommended for team environments with concurrent access
- PSK keys must be encrypted; CARDLINK_ENCRYPTION_KEY environment variable required
- Alembic migrations should be created for any schema changes
- Log repository uses batch inserts for high-throughput APDU logging
- Event emission enables real-time dashboard updates on data changes
- JUnit XML export enables CI/CD integration for test results
