# Tasks Document: Network Simulator Integration

## Overview

This document breaks down the Network Simulator Integration implementation into discrete, actionable tasks based on the requirements and design specifications.

## Task Groups

### 1. Project Setup and Core Infrastructure

- [ ] 1.1 Create project structure for network simulator package at `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/` including `__init__.py`, `types.py`, `exceptions.py`, and `constants.py` modules.
  - **Description:** Initialize the base package structure for the network simulator integration component with core module files.
  - **Purpose:** Establish the foundational package structure to support all network simulator integration functionality.
  - **_Leverage:_** Python package standards, existing CardLink project structure patterns.
  - **_Requirements:_** 1, 2
  - **_Prompt:_** Role: Python package architect | Task: Create the cardlink/netsim package directory structure with __init__.py for package exports, types.py for data classes and enums, exceptions.py for custom exceptions, and constants.py for protocol constants. Add network-sim dependencies (websockets>=11.0, pyyaml>=6.0) to pyproject.toml. | Restrictions: Follow existing CardLink package structure conventions. Ensure __init__.py exports primary interfaces. | Success: Package is importable, all modules are created, dependencies are added to pyproject.toml.

- [ ] 1.2 Define core data types and enums in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/types.py` including SimulatorType, CellStatus, SimulatorConfig, UEInfo, DataSession, CellInfo, SMSMessage, and NetworkEvent.
  - **Description:** Create comprehensive type definitions using dataclasses and enums for all network simulator domain objects.
  - **Purpose:** Provide type-safe interfaces and data structures for network simulator operations throughout the codebase.
  - **_Leverage:_** Python dataclasses, enum module, type hints.
  - **_Requirements:_** 1, 2, 3, 4, 5, 6
  - **_Prompt:_** Role: Type system designer | Task: Define SimulatorType enum (AMARISOFT, GENERIC), CellStatus enum (INACTIVE, ACTIVE, STARTING, STOPPING), and dataclasses for SimulatorConfig, UEInfo (with IMSI, IMEI, status), DataSession (with APN, IP, QoS), CellInfo (with cell_id, status), SMSMessage (with direction, IMSI, PDU), and NetworkEvent (with type, timestamp, data). | Restrictions: Use frozen dataclasses where appropriate, include comprehensive type hints, add docstrings for each type. | Success: All types are defined with complete fields, type hints are present, dataclasses are properly configured.

- [ ] 1.3 Define custom exception hierarchy in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/exceptions.py` with NetworkSimulatorError base and specific exception types.
  - **Description:** Create a comprehensive exception hierarchy for network simulator error handling.
  - **Purpose:** Enable precise error handling and reporting throughout the network simulator integration.
  - **_Leverage:_** Python exception hierarchy, existing CardLink error patterns.
  - **_Requirements:_** 1, 19
  - **_Prompt:_** Role: Exception hierarchy designer | Task: Create NetworkSimulatorError base exception, ConnectionError for connection failures, AuthenticationError for auth failures, CommandError for command execution failures, TimeoutError for operation timeouts, and ConfigurationError for config errors. Each should accept message and optional details dict. | Restrictions: Inherit from appropriate base classes, include __str__ methods, support error context. | Success: All exception types are defined, hierarchy is logical, exceptions support message and context details.

### 2. Connection Layer

- [ ] 2.1 Create abstract connection interface in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/connection.py` with BaseConnection class defining connect(), disconnect(), send(), receive(), on_message(), and is_connected() abstract methods.
  - **Description:** Define the abstract interface for all connection types to ensure consistent connection handling.
  - **Purpose:** Provide a unified interface for WebSocket and TCP connections with pluggable implementations.
  - **_Leverage:_** Python ABC (Abstract Base Classes), async/await patterns.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Interface designer | Task: Create BaseConnection abstract class with async methods: connect(), disconnect(), send(message), receive(), on_message(callback), and property is_connected(). Use abc.ABC and @abstractmethod decorators. Include comprehensive docstrings. | Restrictions: All methods must be async, use type hints, define clear contracts in docstrings. | Success: Abstract class compiles, all methods are properly marked as abstract, docstrings describe expected behavior.

- [ ] 2.2 Implement WebSocket connection class WSConnection in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/connection.py` extending BaseConnection with websockets library integration, SSL/TLS support, keepalive ping/pong (30s interval, 10s timeout), JSON serialization, message callbacks, and connection state tracking.
  - **Description:** Implement full-featured WebSocket client supporting secure connections, automatic keepalive, and message handling.
  - **Purpose:** Provide primary connection method for Amarisoft and other WebSocket-based simulators.
  - **_Leverage:_** websockets library, asyncio, ssl module, json module.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: WebSocket client developer | Task: Implement WSConnection class with __init__(url, tls_config), connect() using websockets library with SSL context, configure ping interval=30s and pong timeout=10s, implement send() with JSON serialization, receive() with JSON deserialization, on_message() callback registration, is_connected property, _receive_loop() background task, handle ConnectionClosed exceptions, track connection state. | Restrictions: Must handle connection errors gracefully, implement proper cleanup in disconnect(), ensure thread-safe callback handling. | Success: Can connect to WebSocket server, send/receive JSON messages, handle disconnections, invoke callbacks on message receipt.

- [ ] 2.3 Implement TCP connection class TCPConnection in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/connection.py` extending BaseConnection with asyncio streams, SSL/TLS support, newline-delimited JSON protocol, and connection state tracking.
  - **Description:** Implement TCP fallback connection using asyncio streams with newline-delimited JSON protocol.
  - **Purpose:** Provide alternative connection method for environments where WebSocket is not available.
  - **_Leverage:_** asyncio.open_connection, StreamReader/StreamWriter, ssl module.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: TCP client developer | Task: Implement TCPConnection class with __init__(url_parsing), connect() using asyncio.open_connection with optional SSL context, disconnect() with writer close and drain, send() with newline-delimited JSON, receive() with readline and JSON parsing, on_message() callback registration, is_connected property, _receive_loop() background task, handle connection closed detection. | Restrictions: Parse tcp:// or tcps:// URLs to extract host/port, handle partial reads, ensure proper cleanup. | Success: Can connect to TCP server, send/receive newline-delimited JSON, detect disconnections, invoke callbacks.

- [ ] 2.4 Implement reconnection manager ReconnectManager in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/connection.py` with exponential backoff, retry loop, maximum delay cap, reconnection event callbacks, and concurrent attempt handling.
  - **Description:** Implement intelligent reconnection logic with exponential backoff for automatic connection recovery.
  - **Purpose:** Ensure reliable connection recovery when network issues occur.
  - **_Leverage:_** asyncio.sleep, exponential backoff algorithm.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Resilience engineer | Task: Create ReconnectManager class with __init__(initial_delay=1, max_delay=60, multiplier=2), calculate exponential backoff, implement reconnect() with retry loop respecting max attempts, track reconnection attempt count, implement max delay cap, implement reset() to clear state, add event callbacks for reconnection start/success/failure, handle concurrent reconnection attempts with locks. | Restrictions: Must not retry indefinitely without limit, log reconnection attempts, emit events for monitoring. | Success: Reconnects with increasing delays, caps at max delay, handles concurrent calls, emits appropriate events.

### 3. Simulator Interface

- [ ] 3.1 Create abstract simulator interface in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/interface.py` with SimulatorInterface class defining methods for authentication, cell operations, UE operations, session operations, SMS operations, event triggering, and configuration management.
  - **Description:** Define comprehensive abstract interface for all simulator operations to support multiple vendor implementations.
  - **Purpose:** Provide vendor-agnostic interface enabling support for Amarisoft, srsRAN, and other simulators.
  - **_Leverage:_** Python ABC, async/await, type hints.
  - **_Requirements:_** 2, 3, 4, 5, 6, 7
  - **_Prompt:_** Role: Interface architect | Task: Define SimulatorInterface ABC with abstract async methods: authenticate(), get_cell_status(), start_cell(), stop_cell(), configure_cell(), list_ues(), get_ue(imsi), detach_ue(imsi), list_sessions(), release_session(session_id), send_sms(imsi, pdu), trigger_event(event_type, params), get_config(), set_config(config), subscribe_events(callback). Include comprehensive docstrings. | Restrictions: All methods must be async, use proper type hints including return types, document expected parameters and return values. | Success: Interface compiles, all methods are abstract, documentation is complete.

- [ ] 3.2 Implement Amarisoft adapter core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with AmarisoftAdapter class implementing JSON-RPC 2.0 protocol, request/response handling, request ID tracking, pending request future management, error response handling, and event notification routing.
  - **Description:** Implement core JSON-RPC 2.0 communication layer for Amarisoft Remote API.
  - **Purpose:** Provide foundation for all Amarisoft simulator operations using standard JSON-RPC protocol.
  - **_Leverage:_** JSON-RPC 2.0 specification, asyncio Futures, uuid for request IDs.
  - **_Requirements:_** 2
  - **_Prompt:_** Role: JSON-RPC client developer | Task: Create AmarisoftAdapter class implementing SimulatorInterface with __init__(connection, event_emitter), implement JSON-RPC 2.0 request formatting with method/params/id, implement _handle_message() to route responses to pending futures and events to callbacks, implement _send_request(method, params, timeout=10) with Future tracking, generate unique request IDs, maintain pending_requests dict mapping ID to Future, handle error responses with code/message, handle event notifications (requests without ID). | Restrictions: Follow JSON-RPC 2.0 spec exactly, implement proper timeout handling, clean up timed-out requests. | Success: Can send JSON-RPC requests, receive responses, match responses to requests, handle errors, route events.

- [ ] 3.3 Implement Amarisoft authentication in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with authenticate() method supporting API key authentication, auth state tracking, and error handling.
  - **Description:** Implement authentication flow for Amarisoft Remote API.
  - **Purpose:** Secure access to Amarisoft simulator with API key authentication.
  - **_Leverage:_** JSON-RPC authenticate method, asyncio.
  - **_Requirements:_** 2
  - **_Prompt:_** Role: Authentication developer | Task: Implement authenticate(api_key) method sending JSON-RPC request to 'authenticate' method with api_key parameter, handle success response storing auth state, handle failure raising AuthenticationError, track authenticated state in instance variable. | Restrictions: Don't proceed with operations if not authenticated, clear auth state on disconnect. | Success: Successfully authenticates with valid key, raises error with invalid key, tracks auth state.

- [ ] 3.4 Implement Amarisoft cell operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with get_cell_status(), start_cell(), stop_cell(), and configure_cell() methods supporting both LTE (eNB) and 5G NR (gNB).
  - **Description:** Implement all cell control and status operations for Amarisoft simulator.
  - **Purpose:** Enable control of simulated cell (eNodeB/gNodeB) for test scenarios.
  - **_Leverage:_** Amarisoft Remote API enb.* methods.
  - **_Requirements:_** 2, 7
  - **_Prompt:_** Role: Cell operations developer | Task: Implement get_cell_status() calling 'enb.get_status' and parsing to CellInfo, implement start_cell() calling 'enb.start', implement stop_cell() calling 'enb.stop', implement configure_cell(params) calling 'enb.configure' with params dict, handle both LTE (eNB) and 5G NR (gNB) variants by detecting from config. | Restrictions: Parse response into proper dataclass types, handle errors with CommandError, validate parameters before sending. | Success: Can retrieve cell status, start/stop cell, configure cell parameters, works for both LTE and 5G.

- [ ] 3.5 Implement Amarisoft UE operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with list_ues(), get_ue(imsi), and detach_ue(imsi) methods.
  - **Description:** Implement UE query and control operations for Amarisoft simulator.
  - **Purpose:** Enable monitoring and control of connected UEs (devices) in test scenarios.
  - **_Leverage:_** Amarisoft Remote API ue.* methods.
  - **_Requirements:_** 2, 3
  - **_Prompt:_** Role: UE operations developer | Task: Implement list_ues() calling 'ue.list' and parsing response into List[UEInfo] with IMSI, IMEI, status fields, implement get_ue(imsi) calling 'ue.get' with imsi parameter returning UEInfo, implement detach_ue(imsi) calling 'ue.detach' with imsi parameter. | Restrictions: Handle UE not found errors gracefully, validate IMSI format, parse all relevant UE fields from response. | Success: Can list all UEs, get specific UE details, detach UE from network.

- [ ] 3.6 Implement Amarisoft session operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with list_sessions() and release_session(session_id) methods.
  - **Description:** Implement data session query and control operations for Amarisoft simulator.
  - **Purpose:** Enable monitoring and control of PDN/PDP contexts for BIP testing.
  - **_Leverage:_** Amarisoft Remote API session.* methods.
  - **_Requirements:_** 2, 4
  - **_Prompt:_** Role: Session operations developer | Task: Implement list_sessions() calling 'session.list' and parsing response into List[DataSession] with session_id, IMSI, APN, IP address, QoS fields, implement release_session(session_id) calling 'session.release' with session_id parameter. | Restrictions: Parse IP addresses correctly, handle session not found errors, include all QoS parameters. | Success: Can list active sessions with full details, release specific sessions.

- [ ] 3.7 Implement Amarisoft SMS operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with send_sms(imsi, pdu) method supporting PDU hex encoding and delivery acknowledgment.
  - **Description:** Implement MT-SMS injection for Amarisoft simulator.
  - **Purpose:** Enable SMS-based OTA trigger delivery through simulated network.
  - **_Leverage:_** Amarisoft Remote API sms.send method, PDU hex encoding.
  - **_Requirements:_** 2, 5
  - **_Prompt:_** Role: SMS operations developer | Task: Implement send_sms(imsi, pdu_bytes) method converting PDU bytes to hex string, calling 'sms.send' with imsi and pdu_hex parameters, handling delivery acknowledgment in response, returning message_id or delivery status. | Restrictions: Validate PDU format, handle IMSI routing, support both SMS-PP and regular SMS. | Success: Can inject MT-SMS to specific IMSI, PDU is delivered correctly, receive delivery confirmation.

- [ ] 3.8 Implement Amarisoft event and config operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/amarisoft.py` with trigger_event(), get_config(), set_config(), and subscribe_events() methods.
  - **Description:** Implement event triggering, configuration management, and event subscription for Amarisoft.
  - **Purpose:** Enable network event triggering, configuration changes, and event monitoring.
  - **_Leverage:_** Amarisoft Remote API various methods, callback registration.
  - **_Requirements:_** 2, 6, 7, 12
  - **_Prompt:_** Role: Event and config developer | Task: Implement trigger_event(event_type, params) with dynamic method routing based on event_type, implement get_config() calling 'config.get' returning full config dict, implement set_config(config) calling 'config.set', implement subscribe_events(callback) registering callback for event notifications from Amarisoft. | Restrictions: Support all Amarisoft event types, validate config before setting, ensure callbacks are async. | Success: Can trigger network events, get/set configuration, receive event notifications via callback.

- [ ] 3.9 Create generic simulator adapter in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/adapters/generic.py` with GenericAdapter class implementing SimulatorInterface with basic REST-like API and stub implementations.
  - **Description:** Implement generic adapter for non-Amarisoft simulators as extensibility point.
  - **Purpose:** Provide foundation for integrating other simulator vendors (srsRAN, OpenAirInterface).
  - **_Leverage:_** HTTP client libraries, abstract interface pattern.
  - **_Requirements:_** 1, 2
  - **_Prompt:_** Role: Generic adapter developer | Task: Create GenericAdapter class implementing SimulatorInterface with stub implementations for all required methods, use basic HTTP REST API communication pattern, include TODO comments for future implementation, provide clear extension points. | Restrictions: Don't make assumptions about specific vendor protocols, keep implementations minimal, document expected behavior. | Success: Class compiles, implements full interface, provides clear starting point for vendor-specific implementations.

### 4. Manager Components

- [ ] 4.1 Implement SimulatorManager initialization and connection in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/manager.py` with connect() method handling protocol selection, adapter creation, authentication, sub-manager initialization, event monitoring, and error handling.
  - **Description:** Implement primary manager class coordinating all simulator operations with connection establishment.
  - **Purpose:** Provide unified entry point for all network simulator functionality.
  - **_Leverage:_** Connection classes, adapter classes, event emitter pattern.
  - **_Requirements:_** 1, 2, 12
  - **_Prompt:_** Role: Manager architect | Task: Create SimulatorManager class with __init__(config, event_emitter), implement async connect() creating connection based on protocol (ws/wss/tcp), setup ReconnectManager if enabled, create adapter based on simulator type (Amarisoft/Generic), call authenticate() if api_key provided, initialize all sub-managers (UE, Session, SMS, Cell, Config, Event), start event monitoring, emit 'simulator_connected' event, handle connection errors with proper cleanup. | Restrictions: Validate config before connecting, ensure proper error propagation, clean up resources on failure. | Success: Successfully connects to simulator, authenticates, initializes all managers, emits connection event.

- [ ] 4.2 Implement SimulatorManager disconnect in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/manager.py` with graceful shutdown, event monitoring stop, sub-manager cleanup, and event emission.
  - **Description:** Implement clean disconnection logic for SimulatorManager.
  - **Purpose:** Ensure proper cleanup of all resources when disconnecting from simulator.
  - **_Leverage:_** Async context managers, cleanup patterns.
  - **_Requirements:_** 1, 12
  - **_Prompt:_** Role: Resource management developer | Task: Implement async disconnect() method calling connection.disconnect(), stopping event monitoring, clearing all sub-manager references, emitting 'simulator_disconnected' event, handling errors during cleanup gracefully. | Restrictions: Must complete even if some cleanup steps fail, log cleanup errors, ensure idempotent (safe to call multiple times). | Success: Cleanly disconnects, stops monitoring, clears resources, emits event, handles partial failures.

- [ ] 4.3 Implement SimulatorManager status aggregation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/manager.py` with get_status() method aggregating cell status, UE count, session count, and is_connected property.
  - **Description:** Implement status reporting combining information from all sub-managers.
  - **Purpose:** Provide unified status view for monitoring and dashboards.
  - **_Leverage:_** Sub-manager status queries, async gather for parallel queries.
  - **_Requirements:_** 10
  - **_Prompt:_** Role: Status aggregation developer | Task: Implement async get_status() method using asyncio.gather to query cell.get_status(), ue.list_ues(), sessions.list_sessions() in parallel, aggregate into status dict with connection state, cell info, ue_count, session_count, handle errors in individual queries gracefully, implement is_connected property checking connection state. | Restrictions: Don't fail entire status if one query fails, include error information in status, cache status briefly to avoid excessive queries. | Success: Returns comprehensive status dict, queries in parallel, handles partial failures, is_connected works.

- [ ] 4.4 Implement SimulatorManager properties in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/manager.py` exposing sub-managers via properties: ue, sessions, sms, cell, config, events.
  - **Description:** Implement property accessors for all sub-managers.
  - **Purpose:** Provide clean API for accessing specialized manager functionality.
  - **_Leverage:_** Python @property decorator, lazy initialization.
  - **_Requirements:_** 3, 4, 5, 6, 7, 9
  - **_Prompt:_** Role: API designer | Task: Implement @property methods for ue (returning UEManager), sessions (returning SessionManager), sms (returning SMSManager), cell (returning CellManager), config (returning ConfigManager), events (returning EventManager). Raise error if accessed before connect() called. | Restrictions: Properties should be read-only, validate manager is initialized, provide helpful error messages. | Success: All properties accessible, return correct manager types, raise errors when not connected.

### 5. UE Manager

- [ ] 5.1 Implement UEManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/ue.py` with initialization, UE cache, waiter tracking, and event subscription.
  - **Description:** Implement UE manager handling registration monitoring and UE cache management.
  - **Purpose:** Provide centralized UE registration tracking with wait-for-registration capability.
  - **_Leverage:_** Dict-based caching, asyncio.Event for waiters.
  - **_Requirements:_** 3
  - **_Prompt:_** Role: UE manager developer | Task: Create UEManager class with __init__(adapter, event_emitter), initialize _ue_cache dict (IMSI -> UEInfo), initialize _waiters dict (IMSI -> List[asyncio.Event]), subscribe to UE events from adapter via subscribe_events(). | Restrictions: Cache must be thread-safe for async access, properly clean up waiters. | Success: Manager initializes, cache is created, event subscription is established.

- [ ] 5.2 Implement UE event handling in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/ue.py` with _handle_event() processing ue_attached and ue_detached events, updating cache, notifying waiters, and emitting events.
  - **Description:** Implement event processing for UE registration and deregistration events.
  - **Purpose:** Keep UE cache synchronized with simulator state and notify waiting clients.
  - **_Leverage:_** Event pattern matching, asyncio.Event.set().
  - **_Requirements:_** 3, 12
  - **_Prompt:_** Role: Event handler developer | Task: Implement async _handle_event(event) method checking event.type, on 'ue_attached' update _ue_cache with new UEInfo, notify all waiters for that IMSI by calling event.set(), emit 'ue_registered' event with UE details, on 'ue_detached' remove from _ue_cache, emit 'ue_deregistered' event. | Restrictions: Handle missing cache entries gracefully, clear waiters after notification, ensure events are emitted asynchronously. | Success: Cache updates on attach/detach, waiters are notified, external events are emitted.

- [ ] 5.3 Implement UE query operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/ue.py` with list_ues(), get_ue(imsi), and get_cached_ues() methods.
  - **Description:** Implement UE query methods with cache management.
  - **Purpose:** Provide efficient UE queries using cache with fallback to adapter.
  - **_Leverage:_** Cache-aside pattern, adapter queries.
  - **_Requirements:_** 3
  - **_Prompt:_** Role: Query operations developer | Task: Implement async list_ues() calling adapter.list_ues() and updating _ue_cache, implement async get_ue(imsi) checking cache first then calling adapter.get_ue(imsi), implement get_cached_ues() returning list of cached UEInfo objects without adapter call. | Restrictions: Update cache on every list_ues() call, handle UE not found gracefully, don't block on cache access. | Success: list_ues updates cache, get_ue uses cache efficiently, get_cached_ues returns cached data only.

- [ ] 5.4 Implement UE wait for registration in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/ue.py` with wait_for_registration(imsi, timeout) method using asyncio.Event waiters.
  - **Description:** Implement wait capability for UE registration with timeout support.
  - **Purpose:** Enable test scripts to wait for specific UE to register before proceeding.
  - **_Leverage:_** asyncio.Event, asyncio.wait_for, timeout handling.
  - **_Requirements:_** 3
  - **_Prompt:_** Role: Async coordination developer | Task: Implement async wait_for_registration(imsi, timeout=30) checking if IMSI already in cache (return immediately), create asyncio.Event, add to _waiters[imsi] list, use asyncio.wait_for(event.wait(), timeout) to wait, clean up waiter from list on completion/timeout, return True if registered, False if timeout. | Restrictions: Clean up waiters on both success and timeout, handle multiple waiters for same IMSI, ensure thread-safe waiter management. | Success: Returns immediately if already registered, waits and returns on registration, times out correctly, cleans up waiters.

- [ ] 5.5 Implement UE detach operation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/ue.py` with detach_ue(imsi) method.
  - **Description:** Implement UE detach operation with cache update.
  - **Purpose:** Enable forced UE detachment for test scenarios.
  - **_Leverage:_** Adapter detach operation, cache management.
  - **_Requirements:_** 3
  - **_Prompt:_** Role: UE control developer | Task: Implement async detach_ue(imsi) calling adapter.detach_ue(imsi), removing IMSI from _ue_cache on success, emitting 'ue_deregistered' event. | Restrictions: Handle detach failures gracefully, update cache only on success, validate IMSI format. | Success: Successfully detaches UE, updates cache, emits event.

### 6. Session Manager

- [ ] 6.1 Implement SessionManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/session.py` with initialization, session cache, and event subscription.
  - **Description:** Implement session manager for data session monitoring and control.
  - **Purpose:** Provide centralized tracking of PDN/PDP contexts for BIP testing.
  - **_Leverage:_** Dict-based caching, event subscription.
  - **_Requirements:_** 4
  - **_Prompt:_** Role: Session manager developer | Task: Create SessionManager class with __init__(adapter, event_emitter), initialize _session_cache dict (session_id -> DataSession), subscribe to session events from adapter via subscribe_events(). | Restrictions: Cache must handle session lifecycle, support lookup by both session_id and IMSI. | Success: Manager initializes, cache is created, event subscription works.

- [ ] 6.2 Implement session event handling in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/session.py` with _handle_event() processing pdn_connected and pdn_disconnected events.
  - **Description:** Implement event processing for data session activation and deactivation.
  - **Purpose:** Keep session cache synchronized with simulator state.
  - **_Leverage:_** Event pattern matching, cache updates.
  - **_Requirements:_** 4, 12
  - **_Prompt:_** Role: Event handler developer | Task: Implement async _handle_event(event) checking event.type, on 'pdn_connected' add DataSession to _session_cache and emit 'data_session_activated' event, on 'pdn_disconnected' remove from _session_cache and emit 'data_session_deactivated' event. | Restrictions: Parse session details from event data, handle duplicate activation gracefully, include all session details in emitted events. | Success: Cache updates on session changes, external events are emitted with full details.

- [ ] 6.3 Implement session query operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/session.py` with list_sessions(), get_session(session_id), and get_sessions_by_imsi(imsi) methods.
  - **Description:** Implement session query methods with cache management.
  - **Purpose:** Provide efficient session queries for monitoring and correlation.
  - **_Leverage:_** Cache-aside pattern, filtering.
  - **_Requirements:_** 4
  - **_Prompt:_** Role: Query operations developer | Task: Implement async list_sessions() calling adapter.list_sessions() and updating _session_cache, implement async get_session(session_id) checking cache then adapter, implement get_sessions_by_imsi(imsi) filtering cached sessions by IMSI. | Restrictions: Update cache on list_sessions, handle not found gracefully, support both active and cached queries. | Success: list_sessions updates cache, get_session uses cache, get_sessions_by_imsi filters correctly.

- [ ] 6.4 Implement session control operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/session.py` with release_session(session_id) method.
  - **Description:** Implement session release operation with cache update.
  - **Purpose:** Enable forced session termination for test scenarios.
  - **_Leverage:_** Adapter release operation, cache management.
  - **_Requirements:_** 4
  - **_Prompt:_** Role: Session control developer | Task: Implement async release_session(session_id) calling adapter.release_session(session_id), removing from _session_cache on success, handling release confirmation from adapter. | Restrictions: Update cache only after confirmed release, handle session not found, validate session_id. | Success: Successfully releases session, updates cache, handles errors.

### 7. SMS Manager

- [ ] 7.1 Implement SMSManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with initialization, message history, message ID counter, and event subscription.
  - **Description:** Implement SMS manager for MT/MO SMS tracking and injection.
  - **Purpose:** Provide centralized SMS handling with history tracking for OTA triggers.
  - **_Leverage:_** List-based history, counter for message IDs.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: SMS manager developer | Task: Create SMSManager class with __init__(adapter, event_emitter), initialize _message_history list, initialize _message_id_counter int, initialize _pending_messages dict (message_id -> SMSMessage), subscribe to SMS events from adapter. | Restrictions: Limit history size to prevent memory growth, make message IDs unique. | Success: Manager initializes, history and counter are ready, event subscription works.

- [ ] 7.2 Implement SMS event handling in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with _handle_event() processing sms_delivered, sms_failed, and sms_received events.
  - **Description:** Implement event processing for SMS delivery status and mobile-originated SMS.
  - **Purpose:** Track SMS delivery status and capture MO-SMS from devices.
  - **_Leverage:_** Event pattern matching, message status updates.
  - **_Requirements:_** 5, 12
  - **_Prompt:_** Role: SMS event handler developer | Task: Implement async _handle_event(event) checking event.type, on 'sms_delivered' update message status to delivered and emit 'sms_delivered' event, on 'sms_failed' update status to failed and emit 'sms_failed' event, on 'sms_received' (MO-SMS) add to history and emit 'sms_event' event. | Restrictions: Match events to pending messages by message_id, include failure reasons, store MO-SMS in history. | Success: Updates message status, emits events with full details, captures MO-SMS.

- [ ] 7.3 Implement SMS send operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with send_mt_sms(imsi, pdu) method including message ID generation, tracking, and event emission.
  - **Description:** Implement MT-SMS sending with tracking and status reporting.
  - **Purpose:** Enable SMS injection for OTA triggers with delivery confirmation.
  - **_Leverage:_** Adapter send_sms, message tracking.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: SMS operations developer | Task: Implement async send_mt_sms(imsi, pdu_bytes) generating unique message_id, creating SMSMessage record with status='pending', sending via adapter.send_sms(), adding to _pending_messages, emitting 'sms_event' event with direction='MT', handling send failures by updating status to 'failed', returning message_id. | Restrictions: Validate IMSI and PDU, handle send errors gracefully, ensure message_id is unique. | Success: Sends SMS successfully, returns message_id, tracks in pending, emits event.

- [ ] 7.4 Implement SMS-PP PDU building in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with send_sms_pp_trigger(imsi, command_data) and _build_sms_pp_pdu() method building complete SMS-PP PDU per 3GPP TS 23.048.
  - **Description:** Implement SMS-PP (Point-to-Point) PDU construction for OTA triggers.
  - **Purpose:** Enable proper OTA trigger delivery using SMS-PP protocol.
  - **_Leverage:_** 3GPP TS 23.048 SMS-PP specification, byte manipulation.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: PDU encoding specialist | Task: Implement send_sms_pp_trigger(imsi, command_data) calling _build_sms_pp_pdu() and send_mt_sms(), implement _build_sms_pp_pdu(orig_addr, command_data) building SCA (Service Center Address) with length byte, PDU Type byte (0x41 for SMS-DELIVER), Originating Address with type and BCD digits, Protocol Identifier (0x7F for SIM Data Download), Data Coding Scheme (0xF6), timestamp (7 bytes), User Data Length, User Data containing command_data. | Restrictions: Follow 3GPP TS 23.048 exactly, handle byte padding, validate PDU structure. | Success: Builds valid SMS-PP PDU, PID is 0x7F, DCS is correct, PDU structure matches spec.

- [ ] 7.5 Implement SMS address encoding in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with _encode_address(phone_number) method for BCD encoding with type byte and padding.
  - **Description:** Implement address encoding for SMS PDU construction.
  - **Purpose:** Properly encode phone numbers in SMS PDU format.
  - **_Leverage:_** BCD encoding, SMS address format specification.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: SMS encoding specialist | Task: Implement _encode_address(phone_number) parsing digits from phone_number, determining type byte (0x91 for international starting with '+', 0x81 for national), BCD encoding digit pairs (swap nibbles), handling odd-length numbers with 0xF padding in last byte, returning bytes with length byte + type byte + BCD digits. | Restrictions: Strip non-digit characters except '+', validate phone number format, pad correctly for odd length. | Success: Encodes international and national numbers correctly, handles odd/even lengths, produces valid address field.

- [ ] 7.6 Implement OTA command packet building in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with _build_ota_command_packet(tar, command_data) method including Command Header with TAR, SPI, KIc, KID fields.
  - **Description:** Implement OTA command packet construction per 3GPP TS 31.115.
  - **Purpose:** Build properly formatted OTA commands for SIM Toolkit operations.
  - **_Leverage:_** 3GPP TS 31.115 OTA specification, byte structure.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: OTA protocol specialist | Task: Implement _build_ota_command_packet(tar, command_data) setting Command Packet Identifier, building Command Header with TAR (Toolkit Application Reference - 3 bytes), SPI (Security Parameter Indicator - 2 bytes), KIc (Cipher Key Identifier), KID (Key Identifier), concatenating with command_data payload. | Restrictions: Follow 3GPP TS 31.115 structure, handle security indicators correctly, validate TAR format (6 hex digits). | Success: Builds valid OTA command packet, TAR is included correctly, structure matches spec.

- [ ] 7.7 Implement SMS history operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/sms.py` with get_message_history(limit), get_message(message_id), and clear_history() methods.
  - **Description:** Implement SMS history query and management operations.
  - **Purpose:** Provide SMS history access for debugging and correlation.
  - **_Leverage:_** List slicing, filtering.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: History management developer | Task: Implement get_message_history(limit=100) returning last N messages from _message_history, implement get_message(message_id) searching _pending_messages and _message_history, implement clear_history() clearing both lists. | Restrictions: Limit history size to prevent unbounded growth, return copies not references, handle message not found. | Success: Returns limited history, finds messages by ID, clears history successfully.

### 8. Cell Manager

- [ ] 8.1 Implement CellManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/cell.py` with initialization and local cell status tracking.
  - **Description:** Implement cell manager for cell control and status monitoring.
  - **Purpose:** Provide centralized cell (eNodeB/gNodeB) control for test scenarios.
  - **_Leverage:_** Adapter cell operations, status caching.
  - **_Requirements:_** 6, 7
  - **_Prompt:_** Role: Cell manager developer | Task: Create CellManager class with __init__(adapter, event_emitter), initialize _cell_status to track current CellInfo locally. | Restrictions: Status should be updated on all operations, support both query and cached access. | Success: Manager initializes, status tracking is ready.

- [ ] 8.2 Implement cell control operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/cell.py` with start() and stop() methods including event emission and status waiting.
  - **Description:** Implement cell start/stop operations with status monitoring.
  - **Purpose:** Enable controlled cell activation/deactivation for test scenarios.
  - **_Leverage:_** Adapter start/stop operations, polling for status changes.
  - **_Requirements:_** 6
  - **_Prompt:_** Role: Cell control developer | Task: Implement async start() emitting 'cell_starting' event, calling adapter.start_cell(), polling get_status() until CellStatus.ACTIVE, emitting 'cell_started' event on success, implement async stop() emitting 'cell_stopping' event, calling adapter.stop_cell(), polling until CellStatus.INACTIVE, emitting 'cell_stopped' event. | Restrictions: Add timeout to status polling, handle start/stop failures, update _cell_status cache. | Success: Cell starts and stops successfully, events are emitted, status is tracked.

- [ ] 8.3 Implement cell status operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/cell.py` with get_status() method and is_active property.
  - **Description:** Implement cell status query with caching.
  - **Purpose:** Provide efficient cell status access for monitoring.
  - **_Leverage:_** Adapter get_cell_status, status caching.
  - **_Requirements:_** 6
  - **_Prompt:_** Role: Status query developer | Task: Implement async get_status() calling adapter.get_cell_status(), updating _cell_status cache, returning CellInfo object, implement is_active property checking if _cell_status.status == CellStatus.ACTIVE. | Restrictions: Cache status briefly to reduce queries, handle query failures gracefully. | Success: Returns current cell status, caches efficiently, is_active works correctly.

- [ ] 8.4 Implement cell configuration operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/cell.py` with configure(params), set_plmn(mcc, mnc), set_frequency(freq), and set_power(power) methods.
  - **Description:** Implement cell configuration operations for network parameters.
  - **Purpose:** Enable dynamic network configuration for different test scenarios.
  - **_Leverage:_** Adapter configure_cell, parameter validation.
  - **_Requirements:_** 7
  - **_Prompt:_** Role: Configuration developer | Task: Implement async configure(params) validating configuration dict and calling adapter.configure_cell(params), implement async set_plmn(mcc, mnc) building params dict and calling configure(), implement async set_frequency(freq) for frequency changes, implement async set_power(power) for TX power changes. | Restrictions: Validate MCC/MNC format (3 digits / 2-3 digits), validate frequency ranges, validate power levels. | Success: Configures cell parameters, helper methods work, validation prevents invalid configs.

### 9. Config Manager

- [ ] 9.1 Implement ConfigManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/config.py` with initialization.
  - **Description:** Implement configuration manager for simulator config access.
  - **Purpose:** Provide centralized configuration management for network simulator.
  - **_Leverage:_** Adapter config operations.
  - **_Requirements:_** 7
  - **_Prompt:_** Role: Config manager developer | Task: Create ConfigManager class with __init__(adapter) storing adapter reference. | Restrictions: Keep manager stateless, always query adapter for current config. | Success: Manager initializes with adapter reference.

- [ ] 9.2 Implement config query operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/config.py` with get(), get_cell_config(), get_subscriber_config(), and get_apn_config() methods.
  - **Description:** Implement configuration query methods for different config sections.
  - **Purpose:** Provide structured access to simulator configuration.
  - **_Leverage:_** Adapter get_config, dict filtering.
  - **_Requirements:_** 7
  - **_Prompt:_** Role: Config query developer | Task: Implement async get() calling adapter.get_config() returning full config dict, implement async get_cell_config() extracting cell-related config section, implement async get_subscriber_config() extracting subscriber section, implement async get_apn_config() extracting APN definitions. | Restrictions: Handle missing config sections gracefully, return empty dict if section not found, don't modify returned dicts. | Success: Returns full and sectional configs, handles missing sections.

- [ ] 9.3 Implement config update operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/config.py` with set(config), set_cell_config(config), set_subscriber_config(config), and set_apn_config(config) methods.
  - **Description:** Implement configuration update methods for different config sections.
  - **Purpose:** Enable configuration changes for test scenarios.
  - **_Leverage:_** Adapter set_config, config merging.
  - **_Requirements:_** 7
  - **_Prompt:_** Role: Config update developer | Task: Implement async set(config) calling adapter.set_config(config) to replace full config, implement async set_cell_config(config) merging cell config section and calling set(), implement async set_subscriber_config(config) for subscriber updates, implement async set_apn_config(config) for APN updates. | Restrictions: Validate config structure before setting, preserve unmodified sections when using sectional setters. | Success: Updates full and sectional configs, merges correctly, validates structure.

- [ ] 9.4 Implement config persistence operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/config.py` with save_to_file(path), load_from_file(path), and validate(config) methods.
  - **Description:** Implement configuration file persistence and validation.
  - **Purpose:** Enable configuration backup, restore, and sharing across test environments.
  - **_Leverage:_** JSON/YAML serialization, file I/O, schema validation.
  - **_Requirements:_** 7
  - **_Prompt:_** Role: Config persistence developer | Task: Implement async save_to_file(path) getting config via get() and serializing to JSON/YAML file, implement async load_from_file(path) deserializing file and calling set(config), implement validate(config) checking required fields and value ranges. | Restrictions: Support both JSON and YAML based on file extension, validate before loading, handle file I/O errors. | Success: Saves config to file, loads from file, validates config structure.

### 10. Event Manager

- [ ] 10.1 Implement EventManager core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with initialization, event history, event ID counter, subscribers dict, and simulator event subscription.
  - **Description:** Implement event manager for network event monitoring and correlation.
  - **Purpose:** Provide centralized event handling with history and subscription support.
  - **_Leverage:_** Event subscription pattern, history storage.
  - **_Requirements:_** 9, 12
  - **_Prompt:_** Role: Event manager developer | Task: Create EventManager class with __init__(adapter, event_emitter), initialize _event_history list, initialize _event_id_counter int, initialize _subscribers dict (event_type -> List[callback]), subscribe to all simulator events from adapter. | Restrictions: Limit history size, support wildcard '*' subscriptions, make thread-safe. | Success: Manager initializes, history and subscribers are ready, receives simulator events.

- [ ] 10.2 Implement event handling in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with _handle_simulator_event() creating NetworkEvent, adding to history, emitting to external emitter, and _notify_subscribers() for type-specific and wildcard subscribers.
  - **Description:** Implement event processing pipeline with history, external emission, and subscriber notification.
  - **Purpose:** Distribute events to all interested parties with persistence for correlation.
  - **_Leverage:_** Event pattern, async callbacks.
  - **_Requirements:_** 9, 12
  - **_Prompt:_** Role: Event handler developer | Task: Implement async _handle_simulator_event(raw_event) creating NetworkEvent with unique ID and timestamp, adding to _event_history, emitting 'network_event' to external event_emitter, calling _notify_subscribers(), implement _notify_subscribers(event) notifying type-specific subscribers and wildcard '*' subscribers. | Restrictions: Handle callback exceptions gracefully, run callbacks concurrently, limit history size (e.g., 1000 events). | Success: Events are stored in history, emitted externally, subscribers are notified.

- [ ] 10.3 Implement event subscription in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with subscribe(event_type, callback) and unsubscribe(event_type, callback) methods supporting wildcard and specific types.
  - **Description:** Implement event subscription management for internal event consumers.
  - **Purpose:** Enable components to subscribe to specific network events.
  - **_Leverage:_** Callback registration pattern, wildcard support.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Subscription developer | Task: Implement subscribe(event_type, callback) adding callback to _subscribers[event_type] list (supporting '*' wildcard), implement unsubscribe(event_type, callback=None) removing specific callback or all callbacks for event_type if callback is None. | Restrictions: Validate callback is async callable, support removing all callbacks for type, handle duplicate subscriptions. | Success: Callbacks can subscribe/unsubscribe, wildcard works, removal works correctly.

- [ ] 10.4 Implement event monitoring in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with start_monitoring() and stop_monitoring() methods tracking monitoring state.
  - **Description:** Implement event monitoring control for enabling/disabling event processing.
  - **Purpose:** Allow conditional event monitoring to reduce overhead when not needed.
  - **_Leverage:_** Boolean state flag.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Monitoring control developer | Task: Implement start_monitoring() setting _monitoring flag to True, implement stop_monitoring() setting flag to False, check flag in _handle_simulator_event() to skip processing when disabled. | Restrictions: Default to enabled, ensure thread-safe flag access. | Success: Can enable/disable monitoring, events are skipped when disabled.

- [ ] 10.5 Implement event query operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with get_event_history(event_type, start_time, end_time, limit) method with filtering.
  - **Description:** Implement event history queries with multiple filter criteria.
  - **Purpose:** Enable event analysis and debugging with flexible queries.
  - **_Leverage:_** List filtering, time-based filtering.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Query developer | Task: Implement get_event_history(event_type=None, start_time=None, end_time=None, limit=100) filtering _event_history by event_type if provided, filtering by timestamp range if start_time/end_time provided, applying limit to most recent events, returning List[NetworkEvent]. | Restrictions: Filter in order: type, time range, then limit. Return copies not references. Default limit to 100. | Success: Filters by type, time range, and limit correctly, returns expected events.

- [ ] 10.6 Implement event correlation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with correlate_events(imsi, time_window) method filtering and grouping related events.
  - **Description:** Implement event correlation by IMSI and time window for debugging.
  - **Purpose:** Enable correlation of network events related to specific device or session.
  - **_Leverage:_** Event filtering, time window calculation.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Correlation developer | Task: Implement correlate_events(imsi=None, time_window=None) filtering _event_history by IMSI field in event data if provided, filtering by time_window (tuple of start_time, end_time) if provided, returning List[NetworkEvent] sorted by timestamp. | Restrictions: Handle events without IMSI field gracefully, support None for no filtering. | Success: Correlates events by IMSI, filters by time window, returns sorted results.

- [ ] 10.7 Implement event export in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/managers/event.py` with export_events(path, format) method supporting JSON and CSV formats.
  - **Description:** Implement event export to file for analysis and sharing.
  - **Purpose:** Enable event data export for external analysis tools.
  - **_Leverage:_** JSON/CSV serialization, file I/O.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Export developer | Task: Implement async export_events(path, format='json') exporting _event_history to file, support 'json' format with JSON serialization of event list, support 'csv' format with CSV rows (id, timestamp, type, data), include all event fields. | Restrictions: Handle file write errors, validate format parameter, serialize dataclasses correctly. | Success: Exports to JSON and CSV, files are valid, all fields included.

### 11. Network Event Triggering

- [ ] 11.1 Implement event trigger operations in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/triggers.py` with trigger_paging(), trigger_handover(), trigger_service_request(), trigger_tau(), trigger_rau(), and trigger_detach() methods.
  - **Description:** Implement network event triggering methods for various 3GPP procedures.
  - **Purpose:** Enable programmatic triggering of network procedures for test scenarios.
  - **_Leverage:_** Adapter trigger_event, 3GPP procedure knowledge.
  - **_Requirements:_** 6
  - **_Prompt:_** Role: Network procedures developer | Task: Create module with functions trigger_paging(adapter, imsi), trigger_handover(adapter, imsi, target_cell), trigger_service_request(adapter, imsi), trigger_tau(adapter, imsi) for Tracking Area Update, trigger_rau(adapter, imsi) for Routing Area Update, trigger_detach(adapter, imsi, detach_type) calling adapter.trigger_event() with appropriate event types and parameters. | Restrictions: Validate parameters, document 3GPP procedure names, handle trigger failures. | Success: All trigger functions work, parameters are validated, events are triggered correctly.

- [ ] 11.2 Implement radio condition simulation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/triggers.py` with set_signal_strength(), simulate_radio_link_failure(), and simulate_coverage_hole() methods.
  - **Description:** Implement radio condition simulation for testing device behavior under poor signal.
  - **Purpose:** Enable testing of device robustness under various radio conditions.
  - **_Leverage:_** Adapter configuration, signal strength parameters.
  - **_Requirements:_** 6
  - **_Prompt:_** Role: Radio simulation developer | Task: Implement async set_signal_strength(adapter, rssi, rsrp=None) setting signal strength parameters, implement async simulate_radio_link_failure(adapter, imsi) triggering RLF condition, implement async simulate_coverage_hole(adapter, duration) simulating coverage loss for duration seconds. | Restrictions: Validate signal strength ranges, handle timing for coverage hole, restore conditions after simulation. | Success: Signal strength changes, RLF is triggered, coverage hole works with restoration.

- [ ] 11.3 Implement scheduled events in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/triggers.py` with schedule_event(delay, event_type, params) and cancel_scheduled_event(event_id) methods supporting delayed and recurring execution.
  - **Description:** Implement event scheduling for time-based test scenarios.
  - **Purpose:** Enable delayed and recurring network events for complex test scenarios.
  - **_Leverage:_** asyncio.sleep, asyncio.create_task, task cancellation.
  - **_Requirements:_** 6
  - **_Prompt:_** Role: Scheduler developer | Task: Implement schedule_event(adapter, delay, event_type, params, recurring=False) creating async task that waits delay seconds then calls adapter.trigger_event(), supports recurring execution if recurring=True, returns event_id (task ID), implement cancel_scheduled_event(event_id) cancelling scheduled task. | Restrictions: Track scheduled tasks in module-level dict, clean up completed tasks, handle cancellation gracefully. | Success: Events trigger after delay, recurring events repeat, cancellation works.

### 12. Scenario Runner

- [ ] 12.1 Define scenario data structures in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with StepStatus enum, ScenarioStep dataclass, StepResult dataclass, and Scenario dataclass.
  - **Description:** Define comprehensive data structures for scenario definition and execution tracking.
  - **Purpose:** Provide type-safe scenario representation and result tracking.
  - **_Leverage:_** Python dataclasses, enums.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Data structure designer | Task: Define StepStatus enum (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED), ScenarioStep dataclass (action, params, timeout, condition), StepResult dataclass (status, duration, error, output), Scenario dataclass (name, description, variables, steps). | Restrictions: Use frozen dataclasses where appropriate, include all necessary fields for execution tracking. | Success: All types defined, dataclasses are complete, enums have all states.

- [ ] 12.2 Implement scenario loading in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with Scenario.from_yaml() and Scenario.from_file() class methods with validation.
  - **Description:** Implement YAML scenario file parsing and validation.
  - **Purpose:** Enable scenario definition via YAML files for easy authoring.
  - **_Leverage:_** pyyaml library, file I/O, schema validation.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: YAML parser developer | Task: Implement @classmethod from_yaml(cls, yaml_str) parsing YAML string to dict, extracting name and description, extracting variables section (dict), parsing steps list into List[ScenarioStep], implement @classmethod from_file(cls, path) reading file and calling from_yaml(), validating scenario structure (required fields present, step actions valid). | Restrictions: Validate YAML structure, handle parse errors gracefully, document expected YAML schema. | Success: Parses valid YAML, creates Scenario object, validates structure, handles errors.

- [ ] 12.3 Implement ScenarioRunner core in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with initialization, running state tracking, results list, and variables dict.
  - **Description:** Implement scenario execution engine core structure.
  - **Purpose:** Provide foundation for orchestrating complex test scenarios.
  - **_Leverage:_** Async execution, state management.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Scenario engine developer | Task: Create ScenarioRunner class with __init__(simulator_manager, event_emitter), initialize _running flag (bool), initialize _results list (List[StepResult]), initialize _variables dict for scenario variables, store manager references. | Restrictions: Keep runner reusable across multiple scenarios, reset state between runs. | Success: Runner initializes, state tracking is ready, can access managers.

- [ ] 12.4 Implement scenario execution in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with run(scenario) method orchestrating step execution, condition checking, error handling, and event emission.
  - **Description:** Implement main scenario execution loop with full orchestration.
  - **Purpose:** Execute scenarios end-to-end with proper error handling and progress tracking.
  - **_Leverage:_** Async iteration, exception handling, event emission.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Execution orchestrator | Task: Implement async run(scenario: Scenario) setting _running=True, copying scenario.variables to _variables, emitting 'scenario_started' event, iterating through scenario.steps, checking _running flag for abort, evaluating step.condition if present, calling _execute_step() for each step, handling step failures based on continue_on_error, emitting 'scenario_completed' event with success/failure status, resetting _running flag. | Restrictions: Support abort via stop() method, collect all results, emit progress events. | Success: Executes all steps, handles conditions, aborts when stopped, emits events, returns results.

- [ ] 12.5 Implement step execution in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with _execute_step(step) method handling timeout, parameter resolution, action execution, and result creation.
  - **Description:** Implement individual step execution with timeout and error handling.
  - **Purpose:** Execute single scenario step with proper resource management and timing.
  - **_Leverage:_** asyncio.wait_for, exception handling, timing.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Step executor | Task: Implement async _execute_step(step: ScenarioStep) creating StepResult, resolving step.params via _resolve_params(), executing action using asyncio.wait_for(_execute_action(step.action, params), timeout=step.timeout), handling TimeoutError updating result status to FAILED, handling other exceptions, calculating duration, emitting 'scenario_step_completed' event, adding result to _results. | Restrictions: Always create result even on failure, include error details, ensure cleanup. | Success: Executes step with timeout, handles errors, creates result, emits event.

- [ ] 12.6 Implement action execution in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with _execute_action(action, params) method mapping action strings to manager method calls.
  - **Description:** Implement action dispatch to appropriate manager methods.
  - **Purpose:** Translate scenario actions to actual simulator operations.
  - **_Leverage:_** Action mapping dict, dynamic method calls.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Action dispatcher | Task: Implement async _execute_action(action: str, params: dict) creating action_map dict mapping 'simulator.start_cell' to manager.cell.start(), 'simulator.stop_cell' to stop(), 'simulator.wait_ue' to manager.ue.wait_for_registration(), 'simulator.send_sms' to manager.sms.send_mt_sms(), 'simulator.trigger_event' to triggers.trigger_*(), 'wait' to asyncio.sleep(), 'set_variable' to updating _variables, raising error for unknown actions. | Restrictions: Unpack params correctly for each action, validate required params present, handle missing params. | Success: All action types work, params are unpacked correctly, unknown actions raise error.

- [ ] 12.7 Implement parameter resolution in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with _resolve_params(params) method for variable substitution.
  - **Description:** Implement variable substitution in scenario parameters.
  - **Purpose:** Enable parameterized scenarios with variable references.
  - **_Leverage:_** String replacement, regex or template strings.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Parameter resolver | Task: Implement _resolve_params(params: dict) recursively processing dict values, detecting variable references '${var_name}', replacing with value from _variables dict, handling missing variables by raising error or using default, returning resolved params dict. | Restrictions: Support nested dicts, handle list values, preserve types (don't convert all to strings). | Success: Resolves variables correctly, handles nested structures, raises error for undefined variables.

- [ ] 12.8 Implement condition evaluation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with _evaluate_condition(condition) method supporting various condition types.
  - **Description:** Implement step condition evaluation for conditional execution.
  - **Purpose:** Enable conditional step execution based on scenario state.
  - **_Leverage:_** Condition parsing, variable checking.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Condition evaluator | Task: Implement _evaluate_condition(condition: str|dict) supporting 'defined:var_name' checking if variable exists, supporting comparison conditions like '${var} == value', supporting boolean combinations with 'and'/'or', returning True if condition passes, False otherwise. | Restrictions: Keep condition language simple, document supported syntax, handle malformed conditions gracefully. | Success: Evaluates defined conditions, comparisons work, boolean logic works.

- [ ] 12.9 Implement scenario control in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/scenario.py` with stop(), get_results(), and get_current_step() methods.
  - **Description:** Implement scenario execution control and status query methods.
  - **Purpose:** Enable external control and monitoring of running scenarios.
  - **_Leverage:_** State access, execution control.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Control interface developer | Task: Implement stop() setting _running flag to False to abort execution, implement get_results() returning copy of _results list, implement get_current_step() returning index of currently executing step or None if not running. | Restrictions: Make stop() idempotent, return copies not references for results, track current step index. | Success: stop() aborts execution, get_results() returns all results, get_current_step() returns correct index.

### 13. Event Correlation

- [ ] 13.1 Create EventCorrelator in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/correlation.py` with initialization accepting multiple event sources.
  - **Description:** Implement event correlator for combining events from multiple sources.
  - **Purpose:** Enable correlation of network simulator events with device and server events.
  - **_Leverage:_** Event collection from multiple managers.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Correlation architect | Task: Create EventCorrelator class with __init__(event_sources: List[EventManager]) storing event source references for accessing event history from network simulator, device controller, and server components. | Restrictions: Support flexible event source types, validate sources provide get_event_history() method. | Success: Correlator initializes with multiple sources.

- [ ] 13.2 Implement correlation by identifiers in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/correlation.py` with correlate_by_imsi(), correlate_by_session(), and correlate_by_timestamp() methods.
  - **Description:** Implement event correlation using different identifier and time-based strategies.
  - **Purpose:** Enable finding related events across different system components.
  - **_Leverage:_** Event filtering, merging, sorting.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Correlation logic developer | Task: Implement correlate_by_imsi(imsi, time_window=None) collecting events from all sources matching IMSI, implement correlate_by_session(session_id) matching events by session_id, implement correlate_by_timestamp(timestamp, window_seconds=60) finding events within time window, returning merged and sorted event lists. | Restrictions: Handle missing identifiers in events, support time window filtering, deduplicate events if sources overlap. | Success: Correlates by IMSI, session, and timestamp, merges from all sources correctly.

- [ ] 13.3 Implement timeline generation in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/correlation.py` with generate_timeline() method merging, sorting, and grouping events.
  - **Description:** Implement unified timeline generation from multiple event sources.
  - **Purpose:** Create chronological view of all events for debugging and analysis.
  - **_Leverage:_** Event merging, timestamp sorting, grouping.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Timeline generator | Task: Implement generate_timeline(filters=None) collecting events from all sources, applying filters (event_type, time_range, identifiers), merging into single list, sorting by timestamp, grouping by correlation_id if present, returning structured timeline data. | Restrictions: Handle events without correlation IDs, support various filter types, maintain chronological order. | Success: Generates complete timeline, filters work, events are sorted, grouping is correct.

- [ ] 13.4 Implement correlation export in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/correlation.py` with export_timeline(path, format) method supporting JSON, CSV, and visualization formats.
  - **Description:** Implement timeline export for external analysis and visualization.
  - **Purpose:** Enable timeline sharing and analysis in external tools.
  - **_Leverage:_** JSON/CSV serialization, visualization data formats.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Export specialist | Task: Implement export_timeline(timeline, path, format='json') supporting 'json' format with timeline array, 'csv' format with flattened rows, 'vis' format for timeline visualization libraries (e.g., vis.js format with start/end/content fields). | Restrictions: Handle nested event data in CSV, validate format parameter, create valid output files. | Success: Exports to JSON, CSV, and visualization formats, files are valid.

### 14. CLI Implementation

- [ ] 14.1 Setup CLI application in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with Click framework, main command group, and global options.
  - **Description:** Setup CLI framework and main command group for network simulator CLI.
  - **Purpose:** Provide command-line interface for all network simulator operations.
  - **_Leverage:_** Click library, command group pattern.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: CLI framework developer | Task: Setup Click application with main command group 'cardlink-netsim', add global options --verbose for logging level, --config for config file path, setup logging configuration, create context object for sharing state across commands. | Restrictions: Follow Click best practices, support help text, enable command auto-discovery. | Success: CLI app runs, global options work, help displays correctly.

- [ ] 14.2 Implement connect/disconnect commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with URL argument, type/api-key/tls options, and status display.
  - **Description:** Implement connection management commands for CLI.
  - **Purpose:** Enable connecting to and disconnecting from simulators via CLI.
  - **_Leverage:_** Click commands, SimulatorManager.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: CLI command developer | Task: Implement @click.command() 'connect' accepting url argument, --type option (amarisoft/generic), --api-key option, --tls flag, creating SimulatorManager and calling connect(), displaying connection status, implement 'disconnect' command calling manager.disconnect(), displaying disconnect status. | Restrictions: Handle connection errors gracefully, display clear error messages, store manager in context. | Success: connect establishes connection, disconnect closes it, status is displayed.

- [ ] 14.3 Implement status command in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` displaying connection, cell, UE, and session status with JSON option.
  - **Description:** Implement status query command for CLI.
  - **Purpose:** Enable status checking via CLI for monitoring.
  - **_Leverage:_** SimulatorManager.get_status(), JSON output.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: Status command developer | Task: Implement 'status' command calling manager.get_status(), displaying connection status (connected/disconnected), cell status (active/inactive), UE count, session count, add --json flag to output status as JSON instead of formatted text. | Restrictions: Handle disconnected state, format output clearly, ensure valid JSON output. | Success: Displays status correctly, JSON output works, handles disconnected state.

- [ ] 14.4 Implement cell commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with cell group containing start, stop, and status subcommands.
  - **Description:** Implement cell control commands for CLI.
  - **Purpose:** Enable cell start/stop operations via CLI.
  - **_Leverage:_** Click command groups, CellManager.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: Cell commands developer | Task: Create 'cell' command group, implement 'start' subcommand calling manager.cell.start() and displaying result, implement 'stop' subcommand calling manager.cell.stop(), implement 'status' subcommand calling manager.cell.get_status() with --json option. | Restrictions: Display operation progress, handle errors gracefully, support JSON output for status. | Success: Cell commands work, operations complete successfully, status displays correctly.

- [ ] 14.5 Implement UE commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with ue group containing list, get, wait, and detach subcommands.
  - **Description:** Implement UE query and control commands for CLI.
  - **Purpose:** Enable UE monitoring and control via CLI.
  - **_Leverage:_** Click command groups, UEManager, table formatting.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: UE commands developer | Task: Create 'ue' command group, implement 'list' subcommand displaying UEs in table (IMSI, status, IP), implement 'get' subcommand accepting imsi argument showing detailed UE info, implement 'wait' subcommand accepting imsi with --timeout option calling manager.ue.wait_for_registration(), implement 'detach' subcommand accepting imsi calling manager.ue.detach_ue(). | Restrictions: Format tables clearly, handle wait timeout, confirm destructive operations. | Success: Lists UEs in table, get shows details, wait works with timeout, detach works.

- [ ] 14.6 Implement SMS commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with sms group containing send and trigger subcommands.
  - **Description:** Implement SMS injection commands for CLI.
  - **Purpose:** Enable SMS sending and OTA triggers via CLI.
  - **_Leverage:_** Click command groups, SMSManager.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: SMS commands developer | Task: Create 'sms' command group, implement 'send' subcommand accepting imsi and pdu arguments calling manager.sms.send_mt_sms() displaying result, implement 'trigger' subcommand accepting imsi with --tar option calling manager.sms.send_sms_pp_trigger(). | Restrictions: Validate PDU format (hex string), validate TAR format (6 hex digits), display message ID. | Success: send delivers SMS, trigger sends OTA, message IDs are displayed.

- [ ] 14.7 Implement event commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with event group containing trigger, list, and export subcommands.
  - **Description:** Implement event triggering and query commands for CLI.
  - **Purpose:** Enable event triggering and history access via CLI.
  - **_Leverage:_** Click command groups, EventManager, triggers module.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: Event commands developer | Task: Create 'event' command group, implement 'trigger' subcommand accepting event_type argument with dynamic parameter options calling appropriate trigger function, implement 'list' subcommand with --type filter and --limit option calling manager.events.get_event_history(), implement 'export' subcommand accepting output_file with --format option (json/csv) calling manager.events.export_events(). | Restrictions: Support all trigger types, format event list clearly, validate export format. | Success: trigger works for all event types, list displays events, export creates valid files.

- [ ] 14.8 Implement scenario commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with scenario group containing run, validate, and list subcommands.
  - **Description:** Implement scenario execution and management commands for CLI.
  - **Purpose:** Enable scenario running and validation via CLI.
  - **_Leverage:_** Click command groups, ScenarioRunner, file operations.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: Scenario commands developer | Task: Create 'scenario' command group, implement 'run' subcommand accepting scenario_file argument loading scenario and executing with progress display, implement 'validate' subcommand checking YAML syntax and validating step actions, implement 'list' subcommand finding scenario files in directory and displaying table. | Restrictions: Display step-by-step progress, show validation errors clearly, support scenario directory scanning. | Success: run executes scenarios with progress, validate checks syntax, list finds scenarios.

- [ ] 14.9 Implement config commands in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/cli.py` with config group containing show, load, and save subcommands.
  - **Description:** Implement configuration management commands for CLI.
  - **Purpose:** Enable config viewing and persistence via CLI.
  - **_Leverage:_** Click command groups, ConfigManager.
  - **_Requirements:_** 11
  - **_Prompt:_** Role: Config commands developer | Task: Create 'config' command group, implement 'show' subcommand calling manager.config.get() and displaying formatted or JSON config, implement 'load' subcommand accepting config_file calling manager.config.load_from_file(), implement 'save' subcommand accepting output_file calling manager.config.save_to_file(). | Restrictions: Format config display clearly, validate files before loading, confirm destructive operations. | Success: show displays config, load updates simulator config, save creates file.

### 15. Dashboard Integration

- [ ] 15.1 Create dashboard API endpoints in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/dashboard/api/simulator.py` for simulator operations including status, connect, disconnect, UEs, sessions, events, cell control, and SMS sending.
  - **Description:** Implement REST API endpoints for dashboard simulator integration.
  - **Purpose:** Enable web dashboard to control and monitor network simulator.
  - **_Leverage:_** Web framework (Flask/FastAPI), SimulatorManager.
  - **_Requirements:_** 10
  - **_Prompt:_** Role: API endpoint developer | Task: Create router/blueprint for simulator endpoints, implement GET /api/simulator/status returning status JSON, implement POST /api/simulator/connect accepting connection config and calling manager.connect(), implement POST /api/simulator/disconnect, implement GET /api/simulator/ues listing UEs, implement GET /api/simulator/sessions listing sessions, implement GET /api/simulator/events with filters, implement POST /api/simulator/cell/start and /stop, implement POST /api/simulator/sms/send accepting IMSI and PDU. | Restrictions: Return proper HTTP status codes, handle errors with error responses, validate request bodies. | Success: All endpoints work, return correct data, handle errors gracefully.

- [ ] 15.2 Create dashboard WebSocket channel in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/dashboard/websocket.py` for real-time simulator event broadcasting.
  - **Description:** Implement WebSocket channel for real-time event updates to dashboard.
  - **Purpose:** Enable live event streaming to dashboard for monitoring.
  - **_Leverage:_** WebSocket library, event subscription.
  - **_Requirements:_** 10
  - **_Prompt:_** Role: WebSocket developer | Task: Create WebSocket channel 'simulator_events', subscribe to manager event emitter for UE registration, session changes, SMS events, cell status changes, broadcast events to all connected WebSocket clients in real-time, include event type and full data in messages. | Restrictions: Handle WebSocket disconnections, limit broadcast rate if needed, serialize events to JSON. | Success: Events broadcast in real-time, clients receive all events, handles connections/disconnections.

- [ ] 15.3 Create dashboard UI components in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/dashboard/static/` for simulator status, UE list, event stream, and control panel.
  - **Description:** Implement React/Vue components for simulator monitoring and control in dashboard.
  - **Purpose:** Provide visual interface for simulator operations in web dashboard.
  - **_Leverage:_** React/Vue, WebSocket client, API client.
  - **_Requirements:_** 10
  - **_Prompt:_** Role: UI component developer | Task: Create SimulatorStatus component displaying connection indicator (green/red) and cell status, create UEList component displaying table with IMSI/status/IP columns and refresh button, create EventStream component displaying real-time events with filtering controls (type filter, search), create ControlPanel component with connect/disconnect buttons, cell start/stop buttons, and SMS send form. | Restrictions: Update in real-time via WebSocket, handle loading states, display errors clearly. | Success: All components render, real-time updates work, controls trigger API calls, display is clear.

### 16. Event Emission

- [ ] 16.1 Define event type constants and schemas in `/home/administrator/Documents/SCP81-TestPlatform/cardlink/netsim/events.py` for all emitted event types.
  - **Description:** Define comprehensive event type constants and payload schemas for integration.
  - **Purpose:** Provide clear event contracts for other components to consume.
  - **_Leverage:_** Constants, dataclasses for schemas.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: Event schema designer | Task: Create events.py module with event type constants (SIMULATOR_CONNECTED, SIMULATOR_DISCONNECTED, UE_REGISTERED, UE_DEREGISTERED, DATA_SESSION_CHANGED, SMS_EVENT, NETWORK_EVENT, SIMULATOR_ERROR), define payload dataclasses for each event type with all required fields, include docstrings describing when each event is emitted. | Restrictions: Use consistent naming, include all necessary data, make schemas immutable. | Success: All event types defined, schemas are complete, documentation is clear.

- [ ] 16.2 Implement connection event emission in relevant components emitting simulator_connected, simulator_disconnected, and simulator_error events with appropriate payloads.
  - **Description:** Implement event emission for simulator connection lifecycle events.
  - **Purpose:** Enable other components to react to simulator connection changes.
  - **_Leverage:_** Event emitter, connection event hooks.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: Event emission developer | Task: In SimulatorManager.connect() emit 'simulator_connected' event with payload containing URL and simulator type, in disconnect() emit 'simulator_disconnected', in error handlers emit 'simulator_error' with error details, ensure events are emitted after state changes complete. | Restrictions: Include all relevant context in payloads, emit asynchronously, don't block on emission. | Success: Events emitted at correct times, payloads contain full context, emission doesn't block.

- [ ] 16.3 Implement UE event emission in UEManager emitting ue_registered and ue_deregistered events with IMSI, IMEI, and cell_id.
  - **Description:** Implement event emission for UE registration lifecycle events.
  - **Purpose:** Enable other components to react to device registration changes.
  - **_Leverage:_** Event emitter, UE event handlers.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: UE event developer | Task: In UEManager._handle_event() on ue_attached emit 'ue_registered' event with payload containing IMSI, IMEI, cell_id, timestamp, on ue_detached emit 'ue_deregistered' with IMSI and detach cause. | Restrictions: Include all available UE details, emit before waiters are notified. | Success: Events emitted on attach/detach, payloads complete, timing is correct.

- [ ] 16.4 Implement session event emission in SessionManager emitting data_session_changed events with session details and change type.
  - **Description:** Implement event emission for data session lifecycle events.
  - **Purpose:** Enable other components to react to PDN/PDP context changes.
  - **_Leverage:_** Event emitter, session event handlers.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: Session event developer | Task: In SessionManager._handle_event() emit 'data_session_changed' event on both pdn_connected and pdn_disconnected with payload containing session_id, IMSI, APN, IP address, change_type ('activated'/'deactivated'), timestamp. | Restrictions: Include full session details, indicate change type clearly. | Success: Events emitted on session changes, payloads complete, change type is correct.

- [ ] 16.5 Implement SMS event emission in SMSManager emitting sms_event for send/receive/delivery with direction, IMSI, and PDU.
  - **Description:** Implement event emission for SMS-related events.
  - **Purpose:** Enable other components to track SMS operations for OTA correlation.
  - **_Leverage:_** Event emitter, SMS event handlers.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: SMS event developer | Task: In SMSManager.send_mt_sms() emit 'sms_event' with direction='MT', IMSI, PDU, message_id, status='sent', in _handle_event() emit on sms_delivered with status='delivered', emit on sms_failed with status='failed' and cause, emit on sms_received with direction='MO'. | Restrictions: Include message_id for tracking, include status and cause, include full PDU. | Success: Events emitted for all SMS operations, payloads complete, direction is correct.

- [ ] 16.6 Implement network event emission in EventManager emitting network_event for all simulator events with event type and full data.
  - **Description:** Implement event emission for all network simulator events.
  - **Purpose:** Enable other components to receive all simulator events for correlation.
  - **_Leverage:_** Event emitter, event forwarding.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: Network event developer | Task: In EventManager._handle_simulator_event() emit 'network_event' with payload containing event_type, event_id, timestamp, source ('simulator'), data (full event data), ensure all simulator events are forwarded to external emitter. | Restrictions: Include complete event data, don't filter events, emit after storing in history. | Success: All simulator events emitted externally, payloads complete, timing is correct.

### 17. Testing

- [ ] 17.1 Create unit tests for connection layer in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_connection.py` testing WSConnection, TCPConnection, and ReconnectManager.
  - **Description:** Implement comprehensive unit tests for all connection classes.
  - **Purpose:** Ensure connection layer reliability and error handling.
  - **_Leverage:_** pytest, pytest-asyncio, mock WebSocket/TCP servers.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Test developer | Task: Create test module with tests for WSConnection.connect()/disconnect(), send()/receive(), message callbacks, connection error handling, tests for TCPConnection connect/disconnect, send/receive, message callbacks, tests for ReconnectManager backoff calculation, retry logic, max attempts, use mock servers and asyncio test patterns. | Restrictions: Test both success and failure cases, use mocks for external dependencies, ensure tests are isolated. | Success: All connection behaviors tested, edge cases covered, tests pass reliably.

- [ ] 17.2 Create unit tests for Amarisoft adapter in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_amarisoft.py` testing JSON-RPC protocol, request/response handling, all operations, and error handling.
  - **Description:** Implement comprehensive unit tests for Amarisoft adapter.
  - **Purpose:** Ensure Amarisoft protocol compliance and operation correctness.
  - **_Leverage:_** pytest, mock connection, JSON-RPC fixtures.
  - **_Requirements:_** 2
  - **_Prompt:_** Role: Adapter test developer | Task: Create test module with tests for request ID generation uniqueness, JSON-RPC request formatting correctness, response routing to correct futures, error response handling, event notification routing, authentication flow, cell/UE/session/SMS operations, use mock connection returning predefined responses. | Restrictions: Test all operation types, validate JSON-RPC format exactly, test timeout handling. | Success: All adapter operations tested, JSON-RPC compliance verified, error cases covered.

- [ ] 17.3 Create unit tests for managers in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_managers.py` testing SimulatorManager, UEManager, SessionManager, SMSManager, EventManager.
  - **Description:** Implement comprehensive unit tests for all manager classes.
  - **Purpose:** Ensure manager logic, caching, and event handling work correctly.
  - **_Leverage:_** pytest, mock adapter, asyncio testing.
  - **_Requirements:_** 3, 4, 5, 9
  - **_Prompt:_** Role: Manager test developer | Task: Create test module with tests for SimulatorManager.connect()/disconnect(), status aggregation, tests for UEManager event handling, cache updates, wait_for_registration with timeout, tests for SessionManager cache and queries, tests for SMSManager send operations, PDU building, history, tests for EventManager subscription, correlation, export. | Restrictions: Mock adapter responses, test cache behavior, test async coordination (waiters). | Success: All manager logic tested, caching works correctly, async patterns tested.

- [ ] 17.4 Create unit tests for scenario runner in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_scenario.py` testing YAML parsing, step execution, timeout handling, condition evaluation, variable resolution.
  - **Description:** Implement comprehensive unit tests for scenario execution engine.
  - **Purpose:** Ensure scenario orchestration works reliably.
  - **_Leverage:_** pytest, mock managers, YAML fixtures.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Scenario test developer | Task: Create test module with tests for Scenario.from_yaml() parsing valid and invalid YAML, tests for step execution with success/failure, tests for timeout handling, tests for condition evaluation (defined, comparisons), tests for variable resolution (${var}), tests for action mapping, tests for stop() aborting execution. | Restrictions: Test all condition types, test variable edge cases, test abort mechanism. | Success: All scenario features tested, parsing works, execution orchestration is correct.

- [ ] 17.5 Create unit tests for SMS PDU building in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_sms_pdu.py` testing address encoding, SMS-PP structure, OTA packet building.
  - **Description:** Implement comprehensive unit tests for SMS PDU encoding.
  - **Purpose:** Ensure SMS-PP and OTA PDU correctness per 3GPP specifications.
  - **_Leverage:_** pytest, PDU parsing utilities, 3GPP test vectors.
  - **_Requirements:_** 5
  - **_Prompt:_** Role: PDU test developer | Task: Create test module with tests for _encode_address() with international/national numbers and odd/even lengths, tests for _build_sms_pp_pdu() validating PID=0x7F, DCS=0xF6, structure correctness, tests for _build_ota_command_packet() validating TAR inclusion and structure, use known test vectors from 3GPP specs. | Restrictions: Validate byte-level correctness, test edge cases (empty, max length), compare against reference implementations. | Success: All PDU formats correct, matches 3GPP specs, handles edge cases.

- [ ] 17.6 Create integration tests in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/test_integration.py` testing full connect/disconnect cycle, UE registration monitoring, SMS injection, event correlation, scenario execution.
  - **Description:** Implement integration tests using mock simulator or real Amarisoft.
  - **Purpose:** Validate end-to-end functionality with realistic workflows.
  - **_Leverage:_** pytest, mock/real simulator, integration test patterns.
  - **_Requirements:_** 1, 2, 3, 5, 8, 9
  - **_Prompt:_** Role: Integration test developer | Task: Create test module with test_full_connection_cycle connecting, querying status, disconnecting, test_ue_registration simulating UE attach and verifying wait_for_registration, test_sms_injection sending SMS and verifying delivery, test_event_correlation generating events and verifying correlation, test_scenario_execution running full scenario and checking results. | Restrictions: Use mock simulator for CI, support real simulator for manual testing, test realistic workflows. | Success: End-to-end workflows work, integration points verified, can test against real simulator.

- [ ] 17.7 Create mock Amarisoft simulator in `/home/administrator/Documents/SCP81-TestPlatform/tests/netsim/mock_simulator.py` with WebSocket server, basic API responses, and event generation.
  - **Description:** Implement mock Amarisoft simulator for testing without real hardware.
  - **Purpose:** Enable testing and CI without dependency on real Amarisoft Callbox.
  - **_Leverage:_** websockets server, JSON-RPC server implementation, asyncio.
  - **_Requirements:_** 2
  - **_Prompt:_** Role: Mock server developer | Task: Create MockAmarisoftSimulator class with WebSocket server accepting connections, implementing JSON-RPC 2.0 server, handling authenticate/enb.*/ue.*/session.*/sms.* methods with realistic responses, simulating UE attach/detach events, simulating session events, allowing programmatic event triggering for testing. | Restrictions: Follow JSON-RPC 2.0 exactly, return realistic response structures, support async operation. | Success: Mock server accepts connections, handles all operations, generates events, works with real client code.

### 18. Documentation

- [ ] 18.1 Write API documentation in `/home/administrator/Documents/SCP81-TestPlatform/docs/netsim/api.md` documenting SimulatorManager class, SimulatorInterface methods, connection configuration, and event types and payloads.
  - **Description:** Create comprehensive API reference documentation.
  - **Purpose:** Enable developers to integrate and use network simulator component.
  - **_Leverage:_** Markdown, code examples, type signatures.
  - **_Requirements:_** All
  - **_Prompt:_** Role: API documentation writer | Task: Document SimulatorManager class with all methods, parameters, return types, examples, document SimulatorInterface abstract methods for adapter authors, document connection configuration options (URL formats, TLS, auth), document all event types with payload schemas and when they're emitted, include code examples for common use cases. | Restrictions: Keep documentation up-to-date with code, include complete examples, document all parameters. | Success: API is fully documented, examples work, developers can use component from docs alone.

- [ ] 18.2 Write usage documentation in `/home/administrator/Documents/SCP81-TestPlatform/docs/netsim/usage.md` with connection setup guide, Amarisoft integration guide, CLI usage guide, and scenario authoring guide.
  - **Description:** Create user-focused usage guides and tutorials.
  - **Purpose:** Enable testers to use network simulator integration for OTA testing.
  - **_Leverage:_** Markdown, step-by-step guides, screenshots.
  - **_Requirements:_** All
  - **_Prompt:_** Role: Technical writer | Task: Write connection setup guide showing how to connect to Amarisoft Callbox, write Amarisoft integration guide explaining configuration and features, write CLI usage guide with examples for all commands, write scenario authoring guide explaining YAML format and available actions with complete scenario examples. | Restrictions: Use clear step-by-step instructions, include troubleshooting sections, provide working examples. | Success: Testers can successfully connect and use simulator from guides, scenarios work as documented.

- [ ] 18.3 Create example scenarios in `/home/administrator/Documents/SCP81-TestPlatform/examples/scenarios/` for basic UE registration, SMS trigger, OTA session, and network event testing.
  - **Description:** Create example scenario YAML files demonstrating common use cases.
  - **Purpose:** Provide starting points for scenario authoring and demonstrate capabilities.
  - **_Leverage:_** YAML, scenario runner features.
  - **_Requirements:_** 8
  - **_Prompt:_** Role: Scenario author | Task: Create ue_registration.yaml scenario starting cell, waiting for UE with timeout, verifying registration, create sms_trigger.yaml scenario sending SMS-PP trigger and waiting for response, create ota_session.yaml scenario orchestrating full OTA session with network, create network_events.yaml scenario testing handover, paging, detach events. | Restrictions: Include comments explaining each step, use realistic parameters, ensure examples work with mock simulator. | Success: All example scenarios are valid, executable, well-documented, demonstrate key features.

### 19. Error Handling and Resilience

- [ ] 19.1 Implement connection error handling in connection classes handling connection refused, timeout, reset, and TLS/SSL errors with appropriate exceptions.
  - **Description:** Implement comprehensive connection error handling with specific exception types.
  - **Purpose:** Provide clear error reporting and recovery paths for connection issues.
  - **_Leverage:_** Exception handling, error classification.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Error handling developer | Task: In WSConnection and TCPConnection handle connection refused (raise ConnectionError with clear message), handle connection timeout (raise TimeoutError), handle connection reset (raise ConnectionError), handle TLS/SSL errors (raise AuthenticationError for cert issues, ConnectionError for others), include error context (URL, error details) in exception messages, log errors with full context. | Restrictions: Classify errors correctly, include actionable error messages, don't expose sensitive data in errors. | Success: All connection error types handled, exceptions include context, error messages are clear.

- [ ] 19.2 Implement command error handling in adapters handling command timeout, invalid response, authentication, and rate limiting errors.
  - **Description:** Implement comprehensive command execution error handling.
  - **Purpose:** Provide clear error reporting for simulator command failures.
  - **_Leverage:_** Exception handling, JSON-RPC error codes.
  - **_Requirements:_** 2
  - **_Prompt:_** Role: Command error handler | Task: In AmarisoftAdapter handle command timeout in _send_request (raise TimeoutError with command details), handle invalid JSON responses (raise CommandError), handle authentication errors from responses (raise AuthenticationError), handle rate limiting if simulator supports it (raise CommandError with retry-after), include command name and parameters in error context. | Restrictions: Parse JSON-RPC error codes correctly, include response details in errors, suggest remediation. | Success: All command error types handled, errors include command context, messages suggest fixes.

- [ ] 19.3 Implement recovery mechanisms with automatic reconnection, request retry logic, circuit breaker pattern, and graceful degradation.
  - **Description:** Implement resilience patterns for robust operation under failure conditions.
  - **Purpose:** Ensure system continues operating despite transient failures.
  - **_Leverage:_** ReconnectManager, retry decorators, circuit breaker pattern.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Resilience engineer | Task: Enhance ReconnectManager with circuit breaker (stop retrying after N consecutive failures until manual reset), implement request retry logic for idempotent operations (with exponential backoff), implement graceful degradation (return cached data when simulator unavailable), add health check before operations to fail-fast when disconnected, emit events for recovery state changes. | Restrictions: Don't retry non-idempotent operations, respect circuit breaker state, log all recovery attempts. | Success: Reconnects automatically, retries transient failures, circuit breaker prevents cascading failures.

- [ ] 19.4 Implement error reporting with contextual logging, command error logs, error event emission, and user-friendly error messages.
  - **Description:** Implement comprehensive error reporting for debugging and monitoring.
  - **Purpose:** Enable effective debugging and monitoring of simulator integration.
  - **_Leverage:_** Python logging, event emission, error formatting.
  - **_Requirements:_** 12
  - **_Prompt:_** Role: Error reporting developer | Task: Add structured logging for connection errors with URL, timestamp, error type, add logging for command errors with method, params, response, emit 'simulator_error' events with error category, message, context for monitoring systems, create user-friendly error messages avoiding technical jargon, include troubleshooting hints in error messages. | Restrictions: Don't log sensitive data (API keys, PDUs with personal data), structure logs for parsing, include correlation IDs. | Success: All errors logged with context, error events emitted, error messages are actionable.

### 20. Performance and Optimization

- [ ] 20.1 Implement connection optimization with connection pooling (if needed), optimized keepalive intervals, and message batching (if beneficial).
  - **Description:** Optimize connection performance for efficiency and responsiveness.
  - **Purpose:** Minimize connection overhead and maximize throughput.
  - **_Leverage:_** Connection reuse, protocol optimization.
  - **_Requirements:_** 1
  - **_Prompt:_** Role: Performance optimizer | Task: Evaluate need for connection pooling (likely not needed for single simulator), optimize keepalive intervals based on network conditions (default 30s ping, 10s pong timeout), implement message batching if simulator supports batch operations, implement connection warmup (pre-authenticate on connect), measure and log connection latency. | Restrictions: Don't over-optimize prematurely, measure before optimizing, maintain protocol correctness. | Success: Connection is efficient, latency is minimized, throughput is maximized.

- [ ] 20.2 Implement event processing optimization with event buffering, async event dispatch, history size limits, and event deduplication.
  - **Description:** Optimize event processing for high-throughput scenarios.
  - **Purpose:** Handle high event rates without memory or CPU issues.
  - **_Leverage:_** Buffering, async processing, deduplication.
  - **_Requirements:_** 9
  - **_Prompt:_** Role: Event processing optimizer | Task: Implement event buffering (collect events in batches before processing), implement async event dispatch (process callbacks concurrently), limit event history size (e.g., 10000 events with FIFO eviction), implement event deduplication (skip duplicate events within time window), add event processing metrics (events/sec, queue depth). | Restrictions: Don't lose events during buffering, maintain event ordering, make limits configurable. | Success: Handles high event rates efficiently, memory usage is bounded, no event loss.

- [ ] 20.3 Implement memory management with cache size limits, eviction policies, and periodic cleanup.
  - **Description:** Implement memory management to prevent unbounded growth.
  - **Purpose:** Ensure long-running operation without memory leaks.
  - **_Leverage:_** LRU eviction, size limits, garbage collection.
  - **_Requirements:_** 3, 4, 5
  - **_Prompt:_** Role: Memory management developer | Task: Limit UE cache size (e.g., 1000 UEs with LRU eviction), limit session cache size (e.g., 1000 sessions), limit message history size (e.g., 1000 messages), implement periodic cleanup task removing stale entries, add memory usage metrics, make limits configurable via config. | Restrictions: Don't evict active/recent entries, log evictions, ensure thread-safe cache operations. | Success: Memory usage is bounded, caches don't grow indefinitely, cleanup works correctly.

## Implementation Order

### Phase 1: Core Infrastructure (Task Groups 1-3)
1. Project setup and types
2. Connection layer (WebSocket, TCP, Reconnect)
3. Simulator interface and Amarisoft adapter

### Phase 2: Manager Components (Task Groups 4-10)
4. Simulator Manager
5. UE Manager
6. Session Manager
7. SMS Manager
8. Cell Manager
9. Config Manager
10. Event Manager

### Phase 3: Advanced Features (Task Groups 11-13)
11. Network event triggering
12. Scenario runner
13. Event correlation

### Phase 4: Interface Integration (Task Groups 14-16)
14. CLI implementation
15. Dashboard integration
16. Event emission

### Phase 5: Quality Assurance (Task Groups 17-20)
17. Testing
18. Documentation
19. Error handling
20. Performance optimization

## Dependencies

### External Dependencies
- `websockets>=11.0` - WebSocket client
- `pyyaml>=6.0` - YAML scenario parsing

### Internal Dependencies
- Core event emitter from CardLink
- Dashboard API framework
- Configuration management

## Notes

- Amarisoft Remote API documentation required for accurate implementation
- Test with actual Amarisoft Callbox for integration validation
- Consider future support for other simulator vendors (srsRAN, OpenAirInterface)
- SMS-PP PDU encoding should follow 3GPP TS 23.048 and TS 31.115
