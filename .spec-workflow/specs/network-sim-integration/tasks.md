# Tasks Document: Network Simulator Integration

## Task Overview

This document breaks down the Network Simulator Integration implementation into actionable development tasks organized by component and functionality. The integration provides connection management, UE monitoring, SMS injection, and test orchestration for network simulators like Amarisoft Callbox.

## Tasks

### 1. Project Setup and Core Infrastructure

- [x] 1.1. Create `src/cardlink/netsim/` package structure with `__init__.py`, `types.py`, `exceptions.py`, and `constants.py`
  - File: src/cardlink/netsim/__init__.py, src/cardlink/netsim/types.py, src/cardlink/netsim/exceptions.py, src/cardlink/netsim/constants.py
  - Initialize the base package structure for network simulator integration
  - Purpose: Establish foundational package structure for all simulator functionality
  - _Leverage: Python package standards, existing CardLink project structure_
  - _Requirements: 1, 2_
  - _Prompt: Role: Python package architect | Task: Create cardlink/netsim package with __init__.py exports, types.py for dataclasses/enums, exceptions.py for custom exceptions, constants.py for protocol constants. Add websockets>=11.0 to pyproject.toml | Restrictions: Follow existing CardLink conventions, ensure proper exports | Success: Package is importable, all modules created_

- [x] 1.2. Define core data types and enums in `types.py`
  - File: src/cardlink/netsim/types.py
  - Create comprehensive type definitions using dataclasses and enums for all domain objects
  - Purpose: Provide type-safe interfaces and data structures throughout the codebase
  - _Leverage: Python dataclasses, enum module, type hints_
  - _Requirements: 1, 2, 3, 4, 5, 6_
  - _Prompt: Role: Type system designer | Task: Define SimulatorType enum (AMARISOFT, GENERIC), CellStatus enum, dataclasses for SimulatorConfig, UEInfo, DataSession, CellInfo, SMSMessage, NetworkEvent with comprehensive fields and type hints | Restrictions: Use frozen dataclasses where appropriate, include docstrings | Success: All types defined with complete fields and type hints_

- [x] 1.3. Define custom exception hierarchy in `exceptions.py`
  - File: src/cardlink/netsim/exceptions.py
  - Create comprehensive exception hierarchy for error handling
  - Purpose: Enable precise error handling throughout the integration
  - _Leverage: Python exception hierarchy, existing CardLink error patterns_
  - _Requirements: 1, 19_
  - _Prompt: Role: Exception hierarchy designer | Task: Create NetworkSimulatorError base, ConnectionError, AuthenticationError, CommandError, TimeoutError, ConfigurationError, NotConnectedError, ResourceNotFoundError with message and optional details dict | Restrictions: Inherit from appropriate base classes, support error context | Success: All exception types defined with proper hierarchy_

### 2. Connection Layer

- [x] 2.1. Create abstract connection interface `BaseConnection` in `connection.py`
  - File: src/cardlink/netsim/connection.py
  - Define abstract interface for all connection types
  - Purpose: Provide unified interface for WebSocket and TCP connections
  - _Leverage: Python ABC, async/await patterns_
  - _Requirements: 1_
  - _Prompt: Role: Interface designer | Task: Create BaseConnection ABC with async methods connect(), disconnect(), send(), receive(), on_message(), is_connected property. Use abc.ABC and @abstractmethod | Restrictions: All methods must be async, use type hints | Success: Abstract class compiles, all methods properly marked abstract_

- [x] 2.2. Implement `WSConnection` class for WebSocket connections
  - File: src/cardlink/netsim/connection.py
  - Implement WebSocket client with SSL/TLS, keepalive, JSON serialization
  - Purpose: Provide primary connection method for Amarisoft simulators
  - _Leverage: websockets library, asyncio, ssl module_
  - _Requirements: 1_
  - _Prompt: Role: WebSocket client developer | Task: Implement WSConnection with connect() using websockets with SSL context, ping interval=30s, pong timeout=10s, send() with JSON serialization, receive() with JSON deserialization, on_message() callbacks, _receive_loop() background task | Restrictions: Handle connection errors gracefully, implement proper cleanup | Success: Can connect, send/receive JSON, handle disconnections_

- [x] 2.3. Implement `TCPConnection` class for TCP connections
  - File: src/cardlink/netsim/connection.py
  - Implement TCP fallback with asyncio streams and newline-delimited JSON
  - Purpose: Provide alternative connection for non-WebSocket environments
  - _Leverage: asyncio.open_connection, StreamReader/StreamWriter_
  - _Requirements: 1_
  - _Prompt: Role: TCP client developer | Task: Implement TCPConnection with connect() using asyncio.open_connection, optional SSL, send() with newline-delimited JSON, receive() with readline, on_message() callbacks, _receive_loop() | Restrictions: Parse tcp:// URLs, handle partial reads | Success: Can connect, send/receive newline-delimited JSON_

- [x] 2.4. Implement `ReconnectManager` with exponential backoff
  - File: src/cardlink/netsim/connection.py
  - Implement intelligent reconnection logic for automatic recovery
  - Purpose: Ensure reliable connection recovery on network issues
  - _Leverage: asyncio.sleep, exponential backoff algorithm_
  - _Requirements: 1_
  - _Prompt: Role: Resilience engineer | Task: Create ReconnectManager with initial_delay, max_delay, multiplier, calculate backoff, implement reconnect() with retry loop, reset(), event callbacks for start/success/failure | Restrictions: Cap at max delay, handle concurrent attempts with locks | Success: Reconnects with increasing delays, emits events_

- [x] 2.5. Implement `create_connection()` factory function
  - File: src/cardlink/netsim/connection.py
  - Create factory function for protocol-based connection creation
  - Purpose: Simplify connection instantiation based on URL scheme
  - _Leverage: URL parsing, connection classes_
  - _Requirements: 1_
  - _Prompt: Role: Factory pattern developer | Task: Implement create_connection(url, tls_config) parsing URL scheme (ws/wss/tcp/tcps), returning appropriate connection instance | Restrictions: Validate URL format, support all schemes | Success: Returns correct connection type for URL_

### 3. Simulator Interface

- [x] 3.1. Create abstract `SimulatorInterface` in `interface.py`
  - File: src/cardlink/netsim/interface.py
  - Define comprehensive abstract interface for all simulator operations
  - Purpose: Enable vendor-agnostic support for multiple simulators
  - _Leverage: Python ABC, async/await, type hints_
  - _Requirements: 2, 3, 4, 5, 6, 7_
  - _Prompt: Role: Interface architect | Task: Define SimulatorInterface ABC with async methods: authenticate(), get_cell_status(), start_cell(), stop_cell(), configure_cell(), list_ues(), get_ue(), detach_ue(), list_sessions(), release_session(), send_sms(), trigger_event(), get_config(), set_config(), subscribe_events() | Restrictions: All methods async, comprehensive docstrings | Success: Interface compiles, all methods abstract_

- [x] 3.2. Implement `AmarisoftAdapter` core with JSON-RPC 2.0 protocol
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement JSON-RPC 2.0 communication layer for Amarisoft Remote API
  - Purpose: Provide foundation for all Amarisoft operations
  - _Leverage: JSON-RPC 2.0 spec, asyncio Futures, uuid_
  - _Requirements: 2_
  - _Prompt: Role: JSON-RPC client developer | Task: Create AmarisoftAdapter implementing SimulatorInterface with JSON-RPC request formatting, _handle_message() for response/event routing, _send_request() with Future tracking, request ID generation, pending_requests dict, error response handling | Restrictions: Follow JSON-RPC 2.0 exactly, implement timeout handling | Success: Can send requests, receive responses, route events_

- [x] 3.3. Implement Amarisoft authentication
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement API key authentication flow
  - Purpose: Secure access to Amarisoft simulator
  - _Leverage: JSON-RPC authenticate method_
  - _Requirements: 2_
  - _Prompt: Role: Authentication developer | Task: Implement authenticate(api_key) sending JSON-RPC to 'authenticate' method, handle success/failure, track authenticated state | Restrictions: Don't proceed if not authenticated, clear state on disconnect | Success: Authenticates with valid key, raises error on invalid_

- [x] 3.4. Implement Amarisoft cell operations
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement get_cell_status(), start_cell(), stop_cell(), configure_cell()
  - Purpose: Enable cell control for test scenarios
  - _Leverage: Amarisoft Remote API enb.* methods_
  - _Requirements: 2, 7_
  - _Prompt: Role: Cell operations developer | Task: Implement cell operations calling enb.get_status, enb.start, enb.stop, enb.configure, parse responses to CellInfo, handle LTE/5G variants | Restrictions: Parse to dataclass types, handle errors | Success: Can control cell start/stop/configure_

- [x] 3.5. Implement Amarisoft UE operations
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement list_ues(), get_ue(), detach_ue()
  - Purpose: Enable UE monitoring and control
  - _Leverage: Amarisoft Remote API ue.* methods_
  - _Requirements: 2, 3_
  - _Prompt: Role: UE operations developer | Task: Implement list_ues() calling ue.list returning List[UEInfo], get_ue(imsi) calling ue.get, detach_ue(imsi) calling ue.detach | Restrictions: Handle not found gracefully, validate IMSI | Success: Can list, get, detach UEs_

- [x] 3.6. Implement Amarisoft session operations
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement list_sessions(), release_session()
  - Purpose: Enable data session monitoring for BIP testing
  - _Leverage: Amarisoft Remote API session.* methods_
  - _Requirements: 2, 4_
  - _Prompt: Role: Session operations developer | Task: Implement list_sessions() returning List[DataSession], release_session(session_id) | Restrictions: Parse IP addresses, handle not found | Success: Can list and release sessions_

- [x] 3.7. Implement Amarisoft SMS operations
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement send_sms() with PDU hex encoding
  - Purpose: Enable SMS-based OTA trigger delivery
  - _Leverage: Amarisoft Remote API sms.send, PDU encoding_
  - _Requirements: 2, 5_
  - _Prompt: Role: SMS operations developer | Task: Implement send_sms(imsi, pdu_bytes) converting PDU to hex, calling sms.send, handling delivery ack | Restrictions: Validate PDU format, support SMS-PP | Success: Can inject MT-SMS, receive confirmation_

- [x] 3.8. Implement Amarisoft event and config operations
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Implement trigger_event(), get_config(), set_config(), subscribe_events()
  - Purpose: Enable event triggering and configuration management
  - _Leverage: Amarisoft Remote API config.* methods_
  - _Requirements: 2, 6, 7, 12_
  - _Prompt: Role: Event/config developer | Task: Implement trigger_event() with dynamic routing, get_config(), set_config(), subscribe_events() for callback registration | Restrictions: Support all event types, validate config | Success: Can trigger events, manage config, receive notifications_

- [x] 3.9. Create `GenericAdapter` for extensibility
  - File: src/cardlink/netsim/adapters/generic.py
  - Implement generic adapter with stub implementations
  - Purpose: Provide foundation for other simulator vendors
  - _Leverage: HTTP client, abstract interface pattern_
  - _Requirements: 1, 2_
  - _Prompt: Role: Generic adapter developer | Task: Create GenericAdapter with stub implementations for all interface methods, clear extension points, TODO comments | Restrictions: Don't assume vendor protocols, document expected behavior | Success: Compiles, provides clear extension points_

### 4. Manager Components

- [x] 4.1. Implement `SimulatorManager` initialization and connection
  - File: src/cardlink/netsim/manager.py
  - Create primary manager coordinating all simulator operations
  - Purpose: Provide unified entry point for simulator functionality
  - _Leverage: Connection classes, adapter classes, event emitter_
  - _Requirements: 1, 2, 12_
  - _Prompt: Role: Manager architect | Task: Create SimulatorManager with connect() creating connection by protocol, setup ReconnectManager, create adapter by type, authenticate if api_key provided, initialize sub-managers, emit 'simulator_connected' | Restrictions: Validate config, handle errors with cleanup | Success: Connects, authenticates, initializes managers_

- [x] 4.2. Implement `SimulatorManager` disconnect
  - File: src/cardlink/netsim/manager.py
  - Implement graceful shutdown with cleanup
  - Purpose: Ensure proper resource cleanup on disconnect
  - _Leverage: Async context managers, cleanup patterns_
  - _Requirements: 1, 12_
  - _Prompt: Role: Resource management developer | Task: Implement disconnect() calling connection.disconnect(), clearing sub-managers, emitting 'simulator_disconnected' | Restrictions: Complete even if cleanup fails, idempotent | Success: Cleanly disconnects, clears resources_

- [x] 4.3. Implement `SimulatorManager` status aggregation
  - File: src/cardlink/netsim/manager.py
  - Implement get_status() combining all sub-manager status
  - Purpose: Provide unified status view for monitoring
  - _Leverage: Sub-manager queries, asyncio.gather_
  - _Requirements: 10_
  - _Prompt: Role: Status aggregation developer | Task: Implement get_status() using asyncio.gather for parallel queries, aggregate to status dict, implement is_connected property | Restrictions: Don't fail if one query fails, cache briefly | Success: Returns comprehensive status, handles partial failures_

- [x] 4.4. Implement `SimulatorManager` sub-manager properties
  - File: src/cardlink/netsim/manager.py
  - Expose sub-managers via properties: ue, sessions, sms, cell
  - Purpose: Provide clean API for specialized functionality
  - _Leverage: Python @property decorator_
  - _Requirements: 3, 4, 5, 6, 7, 9_
  - _Prompt: Role: API designer | Task: Implement @property for ue, sessions, sms, cell returning respective managers, raise error if not connected | Restrictions: Read-only properties, helpful error messages | Success: Properties accessible, return correct types_

### 5. UE Manager

- [x] 5.1. Implement `UEManager` core
  - File: src/cardlink/netsim/managers/ue.py
  - Create UE manager with cache and event subscription
  - Purpose: Provide centralized UE tracking with wait capability
  - _Leverage: Dict-based caching, asyncio.Event for waiters_
  - _Requirements: 3_
  - _Prompt: Role: UE manager developer | Task: Create UEManager with _ue_cache dict, _waiters dict, subscribe to UE events | Restrictions: Thread-safe cache, clean up waiters | Success: Manager initializes, cache ready_

- [x] 5.2. Implement UE event handling
  - File: src/cardlink/netsim/managers/ue.py
  - Process ue_attached/ue_detached events
  - Purpose: Keep cache synchronized, notify waiters
  - _Leverage: Event pattern matching, asyncio.Event.set()_
  - _Requirements: 3, 12_
  - _Prompt: Role: Event handler developer | Task: Implement _handle_event() updating cache on attach, notifying waiters, emitting external events | Restrictions: Handle missing entries, emit async | Success: Cache updates, waiters notified_

- [x] 5.3. Implement UE query operations
  - File: src/cardlink/netsim/managers/ue.py
  - Implement list_ues(), get_ue(), get_cached_ues()
  - Purpose: Provide efficient UE queries with caching
  - _Leverage: Cache-aside pattern, adapter queries_
  - _Requirements: 3_
  - _Prompt: Role: Query operations developer | Task: Implement list_ues() updating cache, get_ue() checking cache first, get_cached_ues() without adapter call | Restrictions: Update cache on list, handle not found | Success: Queries work with cache_

- [x] 5.4. Implement `wait_for_registration()`
  - File: src/cardlink/netsim/managers/ue.py
  - Wait for UE registration with timeout
  - Purpose: Enable test scripts to wait for specific UE
  - _Leverage: asyncio.Event, asyncio.wait_for_
  - _Requirements: 3_
  - _Prompt: Role: Async coordination developer | Task: Implement wait_for_registration(imsi, timeout) checking cache, creating Event, waiting with timeout, cleaning up | Restrictions: Clean up on timeout, handle multiple waiters | Success: Returns immediately if cached, waits correctly_

- [x] 5.5. Implement UE detach operation
  - File: src/cardlink/netsim/managers/ue.py
  - Implement detach_ue() with cache update
  - Purpose: Enable forced UE detachment
  - _Leverage: Adapter detach, cache management_
  - _Requirements: 3_
  - _Prompt: Role: UE control developer | Task: Implement detach_ue(imsi) calling adapter, updating cache, emitting event | Restrictions: Update cache on success only | Success: Detaches UE, updates cache_

### 6. Session Manager

- [x] 6.1. Implement `SessionManager` core
  - File: src/cardlink/netsim/managers/session.py
  - Create session manager with cache and events
  - Purpose: Provide centralized session tracking for BIP testing
  - _Leverage: Dict-based caching, event subscription_
  - _Requirements: 4_
  - _Prompt: Role: Session manager developer | Task: Create SessionManager with _session_cache, subscribe to session events | Restrictions: Support lookup by session_id and IMSI | Success: Manager initializes, cache ready_

- [x] 6.2. Implement session event handling
  - File: src/cardlink/netsim/managers/session.py
  - Process pdn_connected/pdn_disconnected events
  - Purpose: Keep cache synchronized with simulator
  - _Leverage: Event pattern matching, cache updates_
  - _Requirements: 4, 12_
  - _Prompt: Role: Event handler developer | Task: Implement _handle_event() adding/removing from cache, emitting external events | Restrictions: Include all session details in events | Success: Cache updates on changes_

- [x] 6.3. Implement session query operations
  - File: src/cardlink/netsim/managers/session.py
  - Implement list_sessions(), get_session(), get_sessions_by_imsi()
  - Purpose: Provide efficient session queries
  - _Leverage: Cache-aside pattern, filtering_
  - _Requirements: 4_
  - _Prompt: Role: Query operations developer | Task: Implement list_sessions() updating cache, get_session() with cache, get_sessions_by_imsi() filtering | Restrictions: Update cache on list | Success: Queries work with filtering_

- [x] 6.4. Implement session release operation
  - File: src/cardlink/netsim/managers/session.py
  - Implement release_session() with cache update
  - Purpose: Enable forced session termination
  - _Leverage: Adapter release, cache management_
  - _Requirements: 4_
  - _Prompt: Role: Session control developer | Task: Implement release_session(session_id) calling adapter, updating cache | Restrictions: Update after confirmed release | Success: Releases session, updates cache_

### 7. SMS Manager

- [x] 7.1. Implement `SMSManager` core
  - File: src/cardlink/netsim/managers/sms.py
  - Create SMS manager with history and event subscription
  - Purpose: Provide centralized SMS handling for OTA triggers
  - _Leverage: List-based history, message ID counter_
  - _Requirements: 5_
  - _Prompt: Role: SMS manager developer | Task: Create SMSManager with _message_history, _message_id_counter, _pending_messages, subscribe to SMS events | Restrictions: Limit history size, unique message IDs | Success: Manager initializes, ready for SMS_

- [x] 7.2. Implement SMS event handling
  - File: src/cardlink/netsim/managers/sms.py
  - Process sms_delivered, sms_failed, sms_received events
  - Purpose: Track delivery status and capture MO-SMS
  - _Leverage: Event pattern matching, status updates_
  - _Requirements: 5, 12_
  - _Prompt: Role: SMS event handler | Task: Implement _handle_event() updating status on delivery/failure, storing MO-SMS, emitting events | Restrictions: Match by message_id, include failure reasons | Success: Updates status, captures MO-SMS_

- [x] 7.3. Implement `send_mt_sms()` operation
  - File: src/cardlink/netsim/managers/sms.py
  - Send MT-SMS with tracking and events
  - Purpose: Enable SMS injection with delivery confirmation
  - _Leverage: Adapter send_sms, message tracking_
  - _Requirements: 5_
  - _Prompt: Role: SMS operations developer | Task: Implement send_mt_sms(imsi, pdu) generating message_id, tracking, sending via adapter, emitting event | Restrictions: Validate IMSI/PDU, unique IDs | Success: Sends SMS, returns message_id_

- [x] 7.4. Implement SMS-PP PDU building
  - File: src/cardlink/netsim/managers/sms.py
  - Build SMS-PP PDU per 3GPP TS 23.048
  - Purpose: Enable proper OTA trigger delivery
  - _Leverage: 3GPP TS 23.048 SMS-PP specification_
  - _Requirements: 5_
  - _Prompt: Role: PDU encoding specialist | Task: Implement send_sms_pp_trigger() and _build_sms_pp_pdu() with SCA, PDU Type, Originating Address, PID=0x7F, DCS=0xF6, timestamp, User Data | Restrictions: Follow 3GPP TS 23.048 exactly | Success: Builds valid SMS-PP PDU_

- [x] 7.5. Implement SMS address encoding
  - File: src/cardlink/netsim/managers/sms.py
  - Implement BCD address encoding
  - Purpose: Properly encode phone numbers in PDU format
  - _Leverage: BCD encoding, SMS address format_
  - _Requirements: 5_
  - _Prompt: Role: SMS encoding specialist | Task: Implement _encode_address() with type byte (0x91/0x81), BCD encoding with nibble swap, odd-length padding | Restrictions: Strip non-digits except '+', pad correctly | Success: Encodes international/national numbers_

- [x] 7.6. Implement OTA command packet building
  - File: src/cardlink/netsim/managers/sms.py
  - Build OTA command packet per 3GPP TS 31.115
  - Purpose: Build formatted OTA commands for STK
  - _Leverage: 3GPP TS 31.115 specification_
  - _Requirements: 5_
  - _Prompt: Role: OTA protocol specialist | Task: Implement _build_ota_command_packet() with TAR, SPI, KIc, KID, command_data | Restrictions: Follow 3GPP TS 31.115, validate TAR | Success: Builds valid OTA packet_

- [x] 7.7. Implement SMS history operations
  - File: src/cardlink/netsim/managers/sms.py
  - Implement get_message_history(), get_message(), clear_history()
  - Purpose: Provide SMS history for debugging
  - _Leverage: List slicing, filtering_
  - _Requirements: 5_
  - _Prompt: Role: History management developer | Task: Implement history queries with limit, find by message_id, clear operations | Restrictions: Limit history size, return copies | Success: History queries work_

### 8. Cell Manager

- [x] 8.1. Implement `CellManager` core
  - File: src/cardlink/netsim/managers/cell.py
  - Create cell manager with status tracking
  - Purpose: Provide centralized cell control
  - _Leverage: Adapter cell operations, status caching_
  - _Requirements: 6, 7_
  - _Prompt: Role: Cell manager developer | Task: Create CellManager with _cell_status tracking | Restrictions: Update status on all operations | Success: Manager initializes_

- [x] 8.2. Implement cell control operations
  - File: src/cardlink/netsim/managers/cell.py
  - Implement start() and stop() with status polling
  - Purpose: Enable controlled cell activation/deactivation
  - _Leverage: Adapter operations, polling_
  - _Requirements: 6_
  - _Prompt: Role: Cell control developer | Task: Implement start() emitting events, calling adapter, polling for ACTIVE, implement stop() similarly for INACTIVE | Restrictions: Add timeout to polling | Success: Cell starts/stops with events_

- [x] 8.3. Implement cell status operations
  - File: src/cardlink/netsim/managers/cell.py
  - Implement get_status() and is_active property
  - Purpose: Provide efficient cell status access
  - _Leverage: Adapter status, caching_
  - _Requirements: 6_
  - _Prompt: Role: Status query developer | Task: Implement get_status() updating cache, is_active property | Restrictions: Cache briefly | Success: Returns status, is_active works_

- [x] 8.4. Implement cell configuration operations
  - File: src/cardlink/netsim/managers/cell.py
  - Implement configure(), set_plmn(), set_frequency(), set_power()
  - Purpose: Enable dynamic network configuration
  - _Leverage: Adapter configure_cell_
  - _Requirements: 7_
  - _Prompt: Role: Config operations developer | Task: Implement configure(params), convenience methods for PLMN/frequency/power | Restrictions: Validate parameters | Success: Can configure cell parameters_

### 9. Event Manager

- [x] 9.1. Implement `EventManager` core
  - File: src/cardlink/netsim/managers/event.py
  - Create event manager with history and correlation
  - Purpose: Provide event tracking and test correlation
  - _Leverage: List-based history, event filtering_
  - _Requirements: 9_
  - _Prompt: Role: Event manager developer | Task: Create EventManager with _event_history, _event_listeners dict, _correlation_id tracking | Restrictions: Limit history size, efficient filtering | Success: Manager initializes_

- [x] 9.2. Implement event subscription and emission
  - File: src/cardlink/netsim/managers/event.py
  - Implement subscribe(), unsubscribe(), emit()
  - Purpose: Enable event-driven patterns
  - _Leverage: Observer pattern, async callbacks_
  - _Requirements: 9_
  - _Prompt: Role: Event subscription developer | Task: Implement subscribe(callback) returning unsubscribe function, emit(event) calling all subscribers | Restrictions: Handle subscriber errors, async dispatch | Success: Subscribers receive events_

- [x] 9.3. Implement event history operations
  - File: src/cardlink/netsim/managers/event.py
  - Implement get_event_history(), find_events(), clear_history()
  - Purpose: Provide event history for analysis
  - _Leverage: List filtering, time ranges_
  - _Requirements: 9_
  - _Prompt: Role: History developer | Task: Implement get_event_history(limit, event_type), find_events() with filters, clear_history() | Restrictions: Support time range filtering | Success: History queries work with filters_

- [x] 9.4. Implement event correlation
  - File: src/cardlink/netsim/managers/event.py
  - Implement start_correlation(), end_correlation(), get_correlated_events()
  - Purpose: Enable grouping related events
  - _Leverage: Correlation ID tracking_
  - _Requirements: 9_
  - _Prompt: Role: Correlation developer | Task: Implement correlation ID generation, track events within correlation window, retrieve correlated events | Restrictions: Handle overlapping correlations | Success: Events grouped by correlation_

- [x] 9.5. Implement event export
  - File: src/cardlink/netsim/managers/event.py
  - Implement export_events() supporting JSON and CSV formats
  - Purpose: Enable event data export for analysis
  - _Leverage: json, csv modules_
  - _Requirements: 9_
  - _Prompt: Role: Export developer | Task: Implement export_events(format, file_path) supporting JSON and CSV | Restrictions: Include all event fields | Success: Exports to valid files_

### 10. Config Manager

- [x] 10.1. Implement `ConfigManager` core
  - File: src/cardlink/netsim/managers/config.py
  - Create config manager with state tracking
  - Purpose: Provide centralized configuration management
  - _Leverage: Adapter config operations, local cache_
  - _Requirements: 7_
  - _Prompt: Role: Config manager developer | Task: Create ConfigManager with _config_cache tracking current simulator config | Restrictions: Validate before applying | Success: Manager initializes_

- [x] 10.2. Implement config query and update operations
  - File: src/cardlink/netsim/managers/config.py
  - Implement get(), set(), reload()
  - Purpose: Enable configuration viewing and modification
  - _Leverage: Adapter config methods_
  - _Requirements: 7_
  - _Prompt: Role: Config operations developer | Task: Implement get() returning cached/fresh config, set(params) applying changes, reload() refreshing cache | Restrictions: Emit events on changes | Success: Config operations work_

- [x] 10.3. Implement config file operations
  - File: src/cardlink/netsim/managers/config.py
  - Implement load_from_file(), save_to_file()
  - Purpose: Enable config persistence to YAML files
  - _Leverage: pyyaml library_
  - _Requirements: 7_
  - _Prompt: Role: Config file developer | Task: Implement load_from_file(path) loading YAML and applying, save_to_file(path) exporting current config | Restrictions: Validate YAML syntax | Success: Can load/save config files_

### 11. Network Event Triggers

- [x] 11.1. Implement `TriggerManager` core
  - File: src/cardlink/netsim/triggers.py
  - Create trigger manager for network events
  - Purpose: Enable programmatic network event triggering
  - _Leverage: Adapter trigger operations_
  - _Requirements: 6_
  - _Prompt: Role: Trigger manager developer | Task: Create TriggerManager with adapter reference, trigger validation | Restrictions: Validate parameters before sending | Success: Manager initializes_

- [x] 11.2. Implement UE triggers
  - File: src/cardlink/netsim/triggers.py
  - Implement trigger_paging(), trigger_detach()
  - Purpose: Enable UE-related network events
  - _Leverage: Adapter trigger_event_
  - _Requirements: 6_
  - _Prompt: Role: UE trigger developer | Task: Implement trigger_paging(imsi), trigger_detach(imsi, cause) | Restrictions: Validate IMSI format | Success: Can trigger paging/detach_

- [x] 11.3. Implement cell triggers
  - File: src/cardlink/netsim/triggers.py
  - Implement trigger_handover(), trigger_cell_outage()
  - Purpose: Enable cell-related network events
  - _Leverage: Adapter trigger_event_
  - _Requirements: 6_
  - _Prompt: Role: Cell trigger developer | Task: Implement trigger_handover(imsi, target_cell), trigger_cell_outage(duration) | Restrictions: Validate cell parameters | Success: Can trigger handover/outage_

### 12. Scenario Runner

- [x] 12.1. Create scenario schema and parser
  - File: src/cardlink/netsim/scenario.py
  - Define YAML schema and parsing for test scenarios
  - Purpose: Enable declarative test scenario definition
  - _Leverage: pyyaml, dataclasses_
  - _Requirements: 8_
  - _Prompt: Role: Schema designer | Task: Define Scenario dataclass with name, description, steps list, define Step dataclass with action, params, timeout, condition, implement from_yaml() parsing | Restrictions: Validate schema, clear error messages | Success: Can parse valid YAML scenarios_

- [x] 12.2. Implement `ScenarioRunner` execution engine
  - File: src/cardlink/netsim/scenario.py
  - Implement step execution with action mapping
  - Purpose: Execute test scenarios step-by-step
  - _Leverage: SimulatorManager, action mapping_
  - _Requirements: 8_
  - _Prompt: Role: Execution engine developer | Task: Create ScenarioRunner with run() executing steps, action mapping to manager operations, step timeout handling, result collection | Restrictions: Execute sequentially, handle failures | Success: Runs scenarios to completion_

- [x] 12.3. Implement scenario conditions
  - File: src/cardlink/netsim/scenario.py
  - Implement condition evaluation for steps
  - Purpose: Enable conditional step execution
  - _Leverage: Expression evaluation_
  - _Requirements: 8_
  - _Prompt: Role: Condition developer | Task: Implement evaluate_condition() supporting 'defined', 'equals', 'contains' operations on variables | Restrictions: Safe evaluation, no code injection | Success: Conditions evaluate correctly_

- [x] 12.4. Implement scenario variables
  - File: src/cardlink/netsim/scenario.py
  - Implement variable resolution in step params
  - Purpose: Enable parameterized scenarios
  - _Leverage: String substitution_
  - _Requirements: 8_
  - _Prompt: Role: Variable developer | Task: Implement resolve_variables() substituting ${var} in params, support step result variables | Restrictions: Handle undefined variables | Success: Variables resolve in params_

### 13. Constants and Protocol

- [x] 13.1. Define protocol constants
  - File: src/cardlink/netsim/constants.py
  - Define all protocol-related constants
  - Purpose: Centralize protocol values
  - _Leverage: Python constants, enums_
  - _Requirements: All_
  - _Prompt: Role: Constants developer | Task: Define connection timeouts, keepalive intervals, event type strings, JSON-RPC version | Restrictions: Document each constant | Success: All constants defined_

### 14. CLI Integration

- [x] 14.1. Create CLI entry point
  - File: src/cardlink/netsim/cli.py
  - Create main CLI group with connect, status, disconnect commands
  - Purpose: Enable command-line access to simulator
  - _Leverage: Click library, SimulatorManager_
  - _Requirements: 11_
  - _Prompt: Role: CLI developer | Task: Create main CLI group with --url, --type, --api-key options, implement connect, status, disconnect commands | Restrictions: Follow existing CardLink CLI patterns | Success: CLI commands work_

- [x] 14.2. Implement UE commands
  - File: src/cardlink/netsim/cli.py
  - Implement ue list, ue show, ue wait, ue detach commands
  - Purpose: Enable UE management via CLI
  - _Leverage: Click command groups, UEManager_
  - _Requirements: 11_
  - _Prompt: Role: UE commands developer | Task: Create 'ue' group with list, show, wait, detach subcommands | Restrictions: Format output as tables | Success: UE commands display correctly_

- [x] 14.3. Implement session commands
  - File: src/cardlink/netsim/cli.py
  - Implement session list, session show, session release commands
  - Purpose: Enable session management via CLI
  - _Leverage: Click command groups, SessionManager_
  - _Requirements: 11_
  - _Prompt: Role: Session commands developer | Task: Create 'session' group with list, show, release subcommands | Restrictions: Include QoS details in show | Success: Session commands work_

- [x] 14.4. Implement SMS commands
  - File: src/cardlink/netsim/cli.py
  - Implement sms send, sms trigger, sms history commands
  - Purpose: Enable SMS operations via CLI
  - _Leverage: Click command groups, SMSManager_
  - _Requirements: 11_
  - _Prompt: Role: SMS commands developer | Task: Create 'sms' group with send (PDU), trigger (OTA), history subcommands | Restrictions: Support hex PDU input | Success: SMS commands send correctly_

- [x] 14.5. Implement cell commands
  - File: src/cardlink/netsim/cli.py
  - Implement cell start, cell stop, cell status, cell config commands
  - Purpose: Enable cell management via CLI
  - _Leverage: Click command groups, CellManager_
  - _Requirements: 11_
  - _Prompt: Role: Cell commands developer | Task: Create 'cell' group with start, stop, status, config subcommands | Restrictions: Show progress for start/stop | Success: Cell commands control cell_

### 15. Dashboard Integration

- [x] 15.1. Create dashboard API endpoints for simulator operations
  - File: src/cardlink/dashboard/server.py
  - Implement REST API endpoints for dashboard integration
  - Purpose: Enable web dashboard to control and monitor simulator
  - _Leverage: Dashboard server, SimulatorManager_
  - _Requirements: 10_
  - _Prompt: Role: API endpoint developer | Task: Add GET /api/simulator/status, POST /api/simulator/connect, POST /api/simulator/disconnect, GET /api/simulator/ues, GET /api/simulator/sessions, GET /api/simulator/events, POST /api/simulator/cell/start, POST /api/simulator/cell/stop, POST /api/simulator/sms/send | Restrictions: Return proper HTTP status codes, handle errors | Success: All endpoints work_

- [x] 15.2. Create dashboard WebSocket channel for real-time events
  - File: src/cardlink/dashboard/server.py
  - Implement WebSocket event broadcasting
  - Purpose: Enable live event streaming to dashboard
  - _Leverage: WebSocket handler, event subscription_
  - _Requirements: 10_
  - _Prompt: Role: WebSocket developer | Task: Subscribe to manager events, broadcast to WebSocket clients in real-time | Restrictions: Handle disconnections, serialize to JSON | Success: Events broadcast in real-time_

- [x] 15.3. Create dashboard UI components for simulator
  - File: src/cardlink/dashboard/static/js/components/simulator-panel.js
  - Implement UI components for status, UE list, controls
  - Purpose: Provide visual interface in web dashboard
  - _Leverage: Dashboard component patterns, API client_
  - _Requirements: 10_
  - _Prompt: Role: UI component developer | Task: Create SimulatorPanel with connection form, status display, UE list, cell controls, SMS sender | Restrictions: Update via WebSocket, handle loading states | Success: Components render, real-time updates work_

### 16. Event Emission

- [x] 16.1. Define event type constants and schemas
  - File: src/cardlink/netsim/events.py
  - Define all event types and payload schemas
  - Purpose: Provide clear event contracts
  - _Leverage: Constants, dataclasses_
  - _Requirements: 12_
  - _Prompt: Role: Event schema designer | Task: Define SIMULATOR_CONNECTED, UE_REGISTERED, DATA_SESSION_CHANGED, SMS_EVENT, NETWORK_EVENT constants, payload dataclasses | Restrictions: Consistent naming, immutable schemas | Success: All event types defined_

- [x] 16.2. Implement connection event emission
  - File: src/cardlink/netsim/manager.py
  - Emit simulator_connected, simulator_disconnected events
  - Purpose: Enable reaction to connection changes
  - _Leverage: Event emitter, connection hooks_
  - _Requirements: 12_
  - _Prompt: Role: Event emission developer | Task: Emit events in connect(), disconnect(), error handlers with full context | Restrictions: Emit after state changes, async | Success: Events emitted at correct times_

- [x] 16.3. Implement UE event emission
  - File: src/cardlink/netsim/managers/ue.py
  - Emit ue_registered, ue_deregistered events
  - Purpose: Enable reaction to UE changes
  - _Leverage: Event emitter, UE event handlers_
  - _Requirements: 12_
  - _Prompt: Role: UE event developer | Task: Emit events with IMSI, IMEI, cell_id on attach/detach | Restrictions: Include all available details | Success: Events emitted on UE changes_

- [x] 16.4. Implement session event emission
  - File: src/cardlink/netsim/managers/session.py
  - Emit data_session_changed events
  - Purpose: Enable reaction to session changes
  - _Leverage: Event emitter, session handlers_
  - _Requirements: 12_
  - _Prompt: Role: Session event developer | Task: Emit events with session_id, IMSI, APN, IP, change_type | Restrictions: Include full session details | Success: Events emitted on session changes_

- [x] 16.5. Implement SMS event emission
  - File: src/cardlink/netsim/managers/sms.py
  - Emit sms_event for send/receive/delivery
  - Purpose: Enable SMS tracking
  - _Leverage: Event emitter, SMS handlers_
  - _Requirements: 12_
  - _Prompt: Role: SMS event developer | Task: Emit events with direction, IMSI, PDU, status | Restrictions: Include message_id for tracking | Success: Events emitted for all SMS operations_

### 17. Testing

- [x] 17.1. Create unit tests for connection layer
  - File: tests/netsim/test_connection.py
  - Test WSConnection, TCPConnection, ReconnectManager
  - Purpose: Ensure connection reliability
  - _Leverage: pytest, pytest-asyncio, mocks_
  - _Requirements: 1_
  - _Prompt: Role: Test developer | Task: Test connect/disconnect, send/receive, callbacks, error handling, reconnect logic | Restrictions: Use mock servers, isolated tests | Success: All connection behaviors tested_

- [x] 17.2. Create unit tests for Amarisoft adapter
  - File: tests/netsim/test_amarisoft.py
  - Test JSON-RPC protocol and operations
  - Purpose: Ensure protocol compliance
  - _Leverage: pytest, mock connection_
  - _Requirements: 2_
  - _Prompt: Role: Adapter test developer | Task: Test request formatting, response routing, error handling, all operations | Restrictions: Validate JSON-RPC format exactly | Success: Adapter operations tested_

- [x] 17.3. Create unit tests for managers
  - File: tests/netsim/test_managers.py
  - Test all manager classes
  - Purpose: Ensure manager logic correctness
  - _Leverage: pytest, mock adapter_
  - _Requirements: 3, 4, 5, 9_
  - _Prompt: Role: Manager test developer | Task: Test caching, event handling, wait operations, history | Restrictions: Test async coordination | Success: All manager logic tested_

- [x] 17.4. Create integration tests
  - File: tests/netsim/test_integration.py
  - Test end-to-end workflows
  - Purpose: Validate complete functionality
  - _Leverage: pytest, mock simulator_
  - _Requirements: 1, 2, 3, 5, 8, 9_
  - _Prompt: Role: Integration test developer | Task: Test full connection cycle, UE registration, SMS injection, event correlation | Restrictions: Use mock for CI | Success: End-to-end workflows work_

- [x] 17.5. Create mock Amarisoft simulator
  - File: tests/netsim/mock_simulator.py
  - Implement mock simulator for testing
  - Purpose: Enable testing without real hardware
  - _Leverage: websockets server, JSON-RPC_
  - _Requirements: 2_
  - _Prompt: Role: Mock server developer | Task: Create WebSocket server with JSON-RPC handling, realistic responses, event generation | Restrictions: Follow JSON-RPC 2.0 exactly | Success: Mock works with real client code_

### 18. Documentation

- [x] 18.1. Write API documentation
  - File: docs/netsim-api.md
  - Document SimulatorManager, interfaces, events
  - Purpose: Enable developer integration
  - _Leverage: Markdown, code examples_
  - _Requirements: All_
  - _Prompt: Role: API documentation writer | Task: Document all classes, methods, parameters, events with examples | Restrictions: Keep up-to-date, complete examples | Success: API fully documented_

- [x] 18.2. Write usage documentation
  - File: docs/netsim-usage.md
  - Create user-focused guides and tutorials
  - Purpose: Enable tester usage
  - _Leverage: Markdown, step-by-step guides_
  - _Requirements: All_
  - _Prompt: Role: Technical writer | Task: Write connection setup, CLI usage, scenario authoring guides | Restrictions: Clear instructions, troubleshooting sections | Success: Users can follow guides_

- [x] 18.3. Create example scenarios
  - File: examples/netsim/
  - Create example YAML scenarios
  - Purpose: Provide starting points
  - _Leverage: YAML, scenario runner_
  - _Requirements: 8_
  - _Prompt: Role: Scenario author | Task: Create ue_registration.yaml, sms_trigger.yaml, ota_session.yaml examples | Restrictions: Include comments, realistic parameters | Success: Examples are valid and documented_

### 19. Error Handling and Resilience

- [x] 19.1. Implement connection error handling
  - File: src/cardlink/netsim/connection.py
  - Handle all connection error types
  - Purpose: Provide clear error reporting
  - _Leverage: Exception handling, error classification_
  - _Requirements: 1_
  - _Prompt: Role: Error handling developer | Task: Handle connection refused, timeout, reset, TLS errors with specific exceptions | Restrictions: Include context, actionable messages | Success: All errors handled with context_

- [x] 19.2. Implement command error handling
  - File: src/cardlink/netsim/adapters/amarisoft.py
  - Handle command execution errors
  - Purpose: Provide clear command failure reporting
  - _Leverage: JSON-RPC error codes_
  - _Requirements: 2_
  - _Prompt: Role: Command error handler | Task: Handle timeout, invalid response, auth errors, rate limiting | Restrictions: Include command context, suggest fixes | Success: Command errors handled clearly_

- [x] 19.3. Implement recovery mechanisms
  - File: src/cardlink/netsim/connection.py
  - Add circuit breaker and graceful degradation
  - Purpose: Ensure operation under failures
  - _Leverage: Circuit breaker pattern_
  - _Requirements: 1_
  - _Prompt: Role: Resilience engineer | Task: Add circuit breaker, request retry for idempotent ops, graceful degradation with cache | Restrictions: Don't retry non-idempotent, respect breaker | Success: Recovers from transient failures_

### 20. Performance Optimization

- [x] 20.1. Implement connection optimization
  - File: src/cardlink/netsim/performance.py
  - Optimize keepalive and message handling
  - Purpose: Minimize overhead and latency
  - _Leverage: Connection reuse, batching_
  - _Requirements: 1_
  - _Prompt: Role: Performance optimizer | Task: Optimize keepalive intervals, implement batching if beneficial, add latency logging | Restrictions: Measure before optimizing | Success: Connection is efficient_

- [x] 20.2. Implement event processing optimization
  - File: src/cardlink/netsim/performance.py
  - Optimize event buffering and dispatch
  - Purpose: Handle high event volumes
  - _Leverage: Event buffering, async dispatch_
  - _Requirements: 9_
  - _Prompt: Role: Event optimizer | Task: Implement event buffering, async dispatch, history limits, deduplication | Restrictions: Don't drop events, limit memory | Success: Handles high event rates_

## Task Dependencies

```
1 (Infrastructure)
├── 2 (Connection Layer)
│   └── 3 (Simulator Interface)
│       └── 4 (SimulatorManager)
│           ├── 5 (UE Manager)
│           ├── 6 (Session Manager)
│           ├── 7 (SMS Manager)
│           └── 8 (Cell Manager)
│
├── 9 (Event Manager) ← depends on 4
├── 10 (Config Manager) ← depends on 4
├── 11 (Triggers) ← depends on 4
└── 12 (Scenario Runner) ← depends on 4-11

13 (Constants) ← parallel with 1
14 (CLI) ← depends on 4-11
15 (Dashboard) ← depends on 4-11
16 (Event Emission) ← depends on 4-8
17 (Testing) ← depends on all components
18 (Documentation) ← depends on all components
19 (Error Handling) ← parallel with 2-4
20 (Performance) ← after 17
```

## Summary

| Task Group | Tasks | Description | Status |
|------------|-------|-------------|--------|
| Task 1 | 1.1 - 1.3 | Project setup and infrastructure | ✅ Complete |
| Task 2 | 2.1 - 2.5 | Connection layer | ✅ Complete |
| Task 3 | 3.1 - 3.9 | Simulator interface and adapters | ✅ Complete |
| Task 4 | 4.1 - 4.4 | SimulatorManager | ✅ Complete |
| Task 5 | 5.1 - 5.5 | UE Manager | ✅ Complete |
| Task 6 | 6.1 - 6.4 | Session Manager | ✅ Complete |
| Task 7 | 7.1 - 7.7 | SMS Manager | ✅ Complete |
| Task 8 | 8.1 - 8.4 | Cell Manager | ✅ Complete |
| Task 9 | 9.1 - 9.5 | Event Manager | ✅ Complete |
| Task 10 | 10.1 - 10.3 | Config Manager | ✅ Complete |
| Task 11 | 11.1 - 11.3 | Network Event Triggers | ✅ Complete |
| Task 12 | 12.1 - 12.4 | Scenario Runner | ✅ Complete |
| Task 13 | 13.1 | Constants and Protocol | ✅ Complete |
| Task 14 | 14.1 - 14.5 | CLI Integration | ✅ Complete |
| Task 15 | 15.1 - 15.3 | Dashboard Integration | ✅ Complete |
| Task 16 | 16.1 - 16.5 | Event Emission | ✅ Complete |
| Task 17 | 17.1 - 17.5 | Testing | ✅ Complete |
| Task 18 | 18.1 - 18.3 | Documentation | ✅ Complete |
| Task 19 | 19.1 - 19.3 | Error Handling and Resilience | ✅ Complete |
| Task 20 | 20.1 - 20.2 | Performance Optimization | ✅ Complete |

**Total: 20 task groups, 71 subtasks - ALL COMPLETE ✅**
