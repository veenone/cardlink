# Tasks Document: PSK-TLS Admin Server

## Task Overview

This document breaks down the PSK-TLS Admin Server implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Configuration

- [x] 1. Create `cardlink/server/` package directory structure
  - _Leverage:_ Python package structure conventions
  - _Requirements:_ 5
  - _Prompt:_ Role: Python developer | Task: Create the cardlink/server/ package directory with __init__.py following Python package conventions | Restrictions: Use standard Python package layout with __init__.py, maintain consistent naming | Success: Directory structure created, importable as Python package

- [x] 2. Create `__init__.py` with public API exports
  - _Leverage:_ Python module exports best practices
  - _Requirements:_ 5
  - _Prompt:_ Role: API designer | Task: Define public API exports in __init__.py exposing AdminServer, ServerConfig, and KeyStore classes | Restrictions: Only export public interfaces, keep implementation details private | Success: Clean public API, imports work correctly

- [x] 3. Create `config.py` with ServerConfig and CipherConfig dataclasses
  - _Leverage:_ Python dataclasses for configuration
  - _Requirements:_ 5
  - _Prompt:_ Role: Configuration architect | Task: Implement ServerConfig and CipherConfig dataclasses with fields for port, timeouts, cipher suites | Restrictions: Use Python dataclasses with type hints, provide sensible defaults | Success: Configuration classes defined, validated, documented

- [x] 4. Create `models.py` with TLSSessionInfo, Session, APDUExchange dataclasses
  - _Leverage:_ Domain modeling with dataclasses
  - _Requirements:_ 1, 4
  - _Prompt:_ Role: Data modeler | Task: Define TLSSessionInfo, Session, and APDUExchange dataclasses to represent server domain models | Restrictions: Use immutable dataclasses where appropriate, include all required fields from requirements | Success: All domain models defined with proper types

- [x] 5. Define SessionState enum (HANDSHAKING, CONNECTED, ACTIVE, CLOSED)
  - _Leverage:_ Python Enum for type safety
  - _Requirements:_ 4
  - _Prompt:_ Role: State machine designer | Task: Create SessionState enum with states HANDSHAKING, CONNECTED, ACTIVE, CLOSED | Restrictions: Use Python Enum, ensure states align with session lifecycle | Success: SessionState enum defined, states documented

- [x] 6. Define CloseReason enum (NORMAL, TIMEOUT, ERROR, CLIENT_DISCONNECT)
  - _Leverage:_ Python Enum for type safety
  - _Requirements:_ 4, 8
  - _Prompt:_ Role: Error handling designer | Task: Create CloseReason enum with values NORMAL, TIMEOUT, ERROR, CLIENT_DISCONNECT | Restrictions: Use Python Enum, cover all termination scenarios | Success: CloseReason enum defined, covers all cases

- [x] 7. Define HandshakeState enum for partial handshake tracking
  - _Leverage:_ TLS handshake state machine knowledge
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: TLS protocol expert | Task: Define HandshakeState enum to track partial TLS handshake progress for diagnostics | Restrictions: Include states like CLIENT_HELLO, SERVER_HELLO, etc., align with TLS 1.2 spec | Success: Handshake states defined, enables diagnostic logging

- [x] 8. Define TLSAlert enum with standard TLS alert codes
  - _Leverage:_ TLS RFC specifications
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: TLS protocol implementer | Task: Create TLSAlert enum with standard TLS alert codes (handshake_failure, decrypt_error, etc.) | Restrictions: Use standard RFC 5246 alert codes | Success: TLS alerts defined per specification

- [x] 9. Add `sslpsk3` dependency to pyproject.toml
  - _Leverage:_ Python packaging with Poetry/pip
  - _Requirements:_ 1
  - _Prompt:_ Role: Dependency manager | Task: Add sslpsk3 library to pyproject.toml dependencies for PSK-TLS support | Restrictions: Specify compatible version range | Success: Dependency added, installation works

- [x] 10. Add `pyyaml` dependency to pyproject.toml
  - _Leverage:_ Python packaging standards
  - _Requirements:_ 5
  - _Prompt:_ Role: Dependency manager | Task: Add pyyaml library to pyproject.toml for YAML configuration parsing | Restrictions: Use stable version | Success: PyYAML dependency added

- [x] 11. Create optional dependency group `[server]` for server-specific packages
  - _Leverage:_ Poetry/setuptools extras feature
  - _Requirements:_ 5
  - _Prompt:_ Role: Package architect | Task: Define [server] extra in pyproject.toml grouping server-specific dependencies | Restrictions: Include sslpsk3, pyyaml in extras | Success: Optional dependency group created, installable separately

- [x] 12. Verify sslpsk3 installation works on target platform
  - _Leverage:_ Platform compatibility testing
  - _Requirements:_ 1
  - _Prompt:_ Role: QA engineer | Task: Test sslpsk3 installation and basic functionality on target Linux platform | Restrictions: Verify on Python 3.8+, test basic SSL context creation | Success: sslpsk3 works, no platform issues

### 2. Key Store Implementation

- [x] 13. Create `key_store.py` with KeyStore abstract base class
  - _Leverage:_ Abstract base classes for extensibility
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Interface designer | Task: Define KeyStore ABC with methods for PSK key retrieval | Restrictions: Use Python ABC, define clear interface contract | Success: Abstract interface defined, extensible

- [x] 14. Define `get_key(identity: str) -> Optional[bytes]` abstract method
  - _Leverage:_ Python typing for contract clarity
  - _Requirements:_ 1
  - _Prompt:_ Role: API designer | Task: Define get_key abstract method signature returning PSK key bytes for given identity | Restrictions: Return Optional[bytes], use type hints | Success: Method signature defined clearly

- [x] 15. Define `identity_exists(identity: str) -> bool` abstract method
  - _Leverage:_ Separation of concerns (existence vs retrieval)
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: API designer | Task: Define identity_exists abstract method to check PSK identity presence without retrieving key | Restrictions: Return boolean, no side effects | Success: Method enables identity validation

- [x] 16. Add docstrings with usage examples
  - _Leverage:_ Python documentation standards
  - _Requirements:_ 5
  - _Prompt:_ Role: Technical writer | Task: Write comprehensive docstrings for KeyStore interface with usage examples | Restrictions: Follow Google/NumPy docstring style, include examples | Success: Clear documentation, examples provided

- [x] 17. Implement FileKeyStore class extending KeyStore
  - _Leverage:_ File-based configuration pattern
  - _Requirements:_ 5
  - _Prompt:_ Role: Storage implementer | Task: Implement FileKeyStore loading PSK keys from YAML file | Restrictions: Extend KeyStore ABC, handle file I/O errors | Success: File-based key store functional

- [x] 18. Load keys from YAML file on initialization
  - _Leverage:_ PyYAML library
  - _Requirements:_ 5
  - _Prompt:_ Role: Configuration loader | Task: Parse YAML file containing PSK identities and keys in __init__ | Restrictions: Use pyyaml safely, handle file not found | Success: Keys loaded from YAML successfully

- [x] 19. Parse hex-encoded keys to bytes
  - _Leverage:_ Python bytes.fromhex()
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Data parser | Task: Convert hex-encoded PSK key strings from YAML to bytes | Restrictions: Validate hex format, handle invalid input gracefully | Success: Hex keys converted to bytes correctly

- [x] 20. Cache keys in memory after load
  - _Leverage:_ In-memory caching for performance
  - _Requirements:_ 1
  - _Prompt:_ Role: Performance optimizer | Task: Store parsed keys in dictionary for O(1) lookup performance | Restrictions: Use dict for storage, maintain thread safety if needed | Success: Fast key lookup implemented

- [x] 21. Add file validation and error handling for malformed files
  - _Leverage:_ Defensive programming practices
  - _Requirements:_ 5, 8
  - _Prompt:_ Role: Error handling specialist | Task: Validate YAML structure and handle malformed files with clear error messages | Restrictions: Fail fast on startup with descriptive errors | Success: Invalid files detected, clear error messages

- [x] 22. Ensure key values are never logged in plaintext
  - _Leverage:_ Security logging best practices
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Security engineer | Task: Audit all logging statements to ensure PSK keys never appear in logs | Restrictions: Log identities only, mask or omit key values | Success: No key values in logs, verified

- [x] 23. Implement DatabaseKeyStore class extending KeyStore
  - _Leverage:_ Database integration pattern
  - _Requirements:_ 5
  - _Prompt:_ Role: Database integrator | Task: Implement DatabaseKeyStore retrieving PSK keys from database via CardRepository | Restrictions: Extend KeyStore ABC, handle DB connection errors | Success: Database-backed key store works

- [x] 24. Integrate with CardRepository from database layer
  - _Leverage:_ Existing database layer
  - _Requirements:_ 5
  - _Prompt:_ Role: Integration developer | Task: Use CardRepository to query card profiles and extract PSK keys | Restrictions: Follow existing repository patterns, handle None returns | Success: Integration with CardRepository functional

- [x] 25. Query card profiles by PSK identity
  - _Leverage:_ Database query patterns
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Database developer | Task: Implement query to find card profile matching PSK identity string | Restrictions: Use efficient queries, handle case sensitivity appropriately | Success: Identity lookup works correctly

- [x] 26. Handle database connection errors gracefully
  - _Leverage:_ Resilient error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Reliability engineer | Task: Catch and handle database connection failures without crashing server | Restrictions: Log errors, return None for unavailable keys, don't crash | Success: Server survives DB outages

- [x] 27. Write unit tests for FileKeyStore with valid YAML file
  - _Leverage:_ pytest framework
  - _Requirements:_ 5
  - _Prompt:_ Role: Test engineer | Task: Write pytest test loading valid YAML file and verifying key retrieval | Restrictions: Use temp files, verify correct parsing | Success: Valid YAML test passes

- [x] 28. Write unit tests for FileKeyStore with missing file
  - _Leverage:_ Error case testing
  - _Requirements:_ 5, 8
  - _Prompt:_ Role: Test engineer | Task: Test FileKeyStore behavior when YAML file doesn't exist | Restrictions: Verify appropriate exception raised | Success: Missing file test passes

- [x] 29. Write unit tests for FileKeyStore with malformed YAML
  - _Leverage:_ Negative testing practices
  - _Requirements:_ 5, 8
  - _Prompt:_ Role: Test engineer | Task: Test FileKeyStore with invalid YAML syntax and structure | Restrictions: Verify clear error messages | Success: Malformed YAML test passes

- [x] 30. Write unit tests for key retrieval (existing and non-existent identity)
  - _Leverage:_ Boundary testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test get_key with valid identity returns key, invalid returns None | Restrictions: Test both positive and negative cases | Success: Retrieval tests pass

- [x] 31. Create MockKeyStore for other component tests
  - _Leverage:_ Test doubles pattern
  - _Requirements:_ 1
  - _Prompt:_ Role: Test infrastructure developer | Task: Implement MockKeyStore with configurable key responses for testing | Restrictions: Extend KeyStore, allow test configuration | Success: Mock available for integration tests

### 3. Event Emitter Implementation

- [x] 32. Create `event_emitter.py` with EventEmitter class
  - _Leverage:_ Observer pattern
  - _Requirements:_ 7
  - _Prompt:_ Role: Event system architect | Task: Implement EventEmitter class for pub/sub event distribution | Restrictions: Thread-safe implementation, support multiple subscribers | Success: EventEmitter class created

- [x] 33. Implement `emit(event_type: str, data: Dict)` method
  - _Leverage:_ Publisher pattern
  - _Requirements:_ 7
  - _Prompt:_ Role: Event publisher | Task: Implement emit method to send events to all subscribers | Restrictions: Non-blocking, handle subscriber errors gracefully | Success: Events emitted to subscribers

- [x] 34. Implement `subscribe(event_type: str, callback: Callable) -> str` method
  - _Leverage:_ Callback registration pattern
  - _Requirements:_ 7
  - _Prompt:_ Role: Subscription manager | Task: Implement subscribe method registering callbacks and returning subscription ID | Restrictions: Generate unique IDs, store callbacks safely | Success: Subscription works, ID returned

- [x] 35. Implement `unsubscribe(subscription_id: str)` method
  - _Leverage:_ Resource cleanup pattern
  - _Requirements:_ 7
  - _Prompt:_ Role: Subscription manager | Task: Implement unsubscribe method removing callback by subscription ID | Restrictions: Handle invalid IDs gracefully | Success: Unsubscription works correctly

- [x] 36. Use thread-safe queue for event distribution
  - _Leverage:_ Python queue.Queue for thread safety
  - _Requirements:_ 7
  - _Prompt:_ Role: Concurrency engineer | Task: Use thread-safe queue to distribute events to subscribers | Restrictions: Use queue.Queue, handle full queue scenarios | Success: Thread-safe event distribution

- [x] 37. Support wildcard subscriptions for all events
  - _Leverage:_ Pattern matching for flexibility
  - _Requirements:_ 7
  - _Prompt:_ Role: Event filtering designer | Task: Support wildcard ('*') subscription to receive all event types | Restrictions: Implement efficiently, don't duplicate logic | Success: Wildcard subscriptions work

- [x] 38. Define all 11 event types as constants
  - _Leverage:_ Constants for type safety
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Event schema designer | Task: Define constants for tls_handshake_start, tls_handshake_complete, apdu_received, apdu_sent, session_ended, connection_interrupted, psk_mismatch, handshake_interrupted, high_error_rate, server_started, server_stopped | Restrictions: Use clear naming, document each type | Success: All 11 event types defined

- [x] 39. Create Pydantic schemas for event data validation
  - _Leverage:_ Pydantic for data validation
  - _Requirements:_ 7
  - _Prompt:_ Role: Data validator | Task: Define Pydantic models validating event data structure for each event type | Restrictions: One model per event type, validate all fields | Success: Event data validated automatically

- [x] 40. Document event data fields for each type
  - _Leverage:_ API documentation standards
  - _Requirements:_ 7
  - _Prompt:_ Role: Technical writer | Task: Document expected fields and types for each event's data dictionary | Restrictions: Include examples, specify required vs optional fields | Success: Events fully documented

- [x] 41. Write unit tests for event emission to single subscriber
  - _Leverage:_ Basic functionality testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test that emitted events reach single subscriber callback | Restrictions: Verify callback called with correct data | Success: Single subscriber test passes

- [x] 42. Write unit tests for event emission to multiple subscribers
  - _Leverage:_ Fan-out testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test events delivered to all registered subscribers | Restrictions: Verify all callbacks invoked | Success: Multiple subscriber test passes

- [x] 43. Write unit tests for subscription and unsubscription
  - _Leverage:_ Lifecycle testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test subscribe returns ID, unsubscribe stops events | Restrictions: Verify cleanup works correctly | Success: Subscription lifecycle test passes

- [x] 44. Write unit tests for thread safety with concurrent emissions
  - _Leverage:_ Concurrency testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Concurrency test engineer | Task: Test multiple threads emitting events simultaneously without race conditions | Restrictions: Use threading, verify no lost events | Success: Thread safety test passes

- [x] 45. Create MockEventEmitter for other component tests
  - _Leverage:_ Test isolation
  - _Requirements:_ 7
  - _Prompt:_ Role: Test infrastructure developer | Task: Implement MockEventEmitter recording events without actual callbacks | Restrictions: Store emitted events for verification | Success: Mock emitter available for tests

### 4. TLS Handler Implementation

- [x] 46. Create `tls_handler.py` with TLSHandler class
  - _Leverage:_ TLS protocol knowledge
  - _Requirements:_ 1
  - _Prompt:_ Role: TLS implementer | Task: Create TLSHandler class managing PSK-TLS handshakes | Restrictions: Use sslpsk3 library, support TLS 1.2 | Success: TLSHandler class created

- [x] 47. Implement `__init__` with KeyStore and CipherConfig parameters
  - _Leverage:_ Dependency injection
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Class designer | Task: Initialize TLSHandler with KeyStore and CipherConfig dependencies | Restrictions: Store references, validate inputs | Success: Initialization works with dependencies

- [x] 48. Implement `create_ssl_context()` method
  - _Leverage:_ Python ssl module
  - _Requirements:_ 1
  - _Prompt:_ Role: SSL context builder | Task: Create SSL context configured for PSK-TLS server mode | Restrictions: Use sslpsk3.wrap_context, set server mode | Success: SSL context created successfully

- [x] 49. Configure sslpsk3 with PSK callback function
  - _Leverage:_ sslpsk3 library API
  - _Requirements:_ 1
  - _Prompt:_ Role: PSK configurator | Task: Register PSK identity callback with sslpsk3 context | Restrictions: Callback must return key bytes or None | Success: PSK callback registered

- [x] 50. Set allowed cipher suites based on CipherConfig
  - _Leverage:_ SSL context cipher configuration
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Cipher suite manager | Task: Configure SSL context with allowed PSK cipher suites from config | Restrictions: Build cipher string correctly, validate ciphers | Success: Cipher suites configured per config

- [x] 51. Set TLS 1.2 as protocol version
  - _Leverage:_ SSL context protocol configuration
  - _Requirements:_ 1
  - _Prompt:_ Role: Protocol configurator | Task: Set SSL context to require TLS 1.2 (required for PSK) | Restrictions: Use ssl.PROTOCOL_TLSv1_2 or equivalent | Success: TLS 1.2 enforced

- [x] 52. Implement PSK identity callback function
  - _Leverage:_ sslpsk3 callback mechanism
  - _Requirements:_ 1
  - _Prompt:_ Role: PSK callback implementer | Task: Implement callback receiving identity string and returning PSK key bytes | Restrictions: Query KeyStore, return None for unknown | Success: Callback retrieves keys correctly

- [x] 53. Look up key from KeyStore in callback
  - _Leverage:_ KeyStore abstraction
  - _Requirements:_ 1
  - _Prompt:_ Role: Key retrieval integrator | Task: Call KeyStore.get_key(identity) in PSK callback | Restrictions: Handle None returns, no exceptions | Success: KeyStore integration works

- [x] 54. Return None for unknown identities (triggers handshake failure)
  - _Leverage:_ TLS handshake failure mechanism
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Authentication enforcer | Task: Return None from callback when identity not found to trigger TLS handshake_failure | Restrictions: Don't raise exceptions, let TLS handle it | Success: Unknown identities rejected

- [x] 55. Log PSK identity (but never key values)
  - _Leverage:_ Secure logging practices
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Security-conscious logger | Task: Log PSK identity on lookup, never log key bytes | Restrictions: Audit all log statements, mask keys | Success: Identity logged, keys never logged

- [x] 56. Implement `wrap_socket(sock, client_addr)` method
  - _Leverage:_ SSL socket wrapping
  - _Requirements:_ 1
  - _Prompt:_ Role: Socket wrapper | Task: Wrap plain socket with SSL context to create TLS connection | Restrictions: Use context.wrap_socket, handle errors | Success: Socket wrapped with TLS

- [x] 57. Perform TLS handshake with configurable timeout
  - _Leverage:_ Socket timeout mechanism
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Handshake orchestrator | Task: Execute TLS handshake with timeout from config | Restrictions: Set socket timeout, handle timeout exceptions | Success: Handshake with timeout control

- [x] 58. Track handshake duration for metrics
  - _Leverage:_ Time measurement
  - _Requirements:_ 1, 7
  - _Prompt:_ Role: Metrics collector | Task: Measure and record handshake duration in milliseconds | Restrictions: Use time.perf_counter for precision | Success: Handshake timing captured

- [x] 59. Return TLSSessionInfo with cipher suite, identity, timing
  - _Leverage:_ Domain model for session info
  - _Requirements:_ 1
  - _Prompt:_ Role: Session info builder | Task: Create TLSSessionInfo dataclass with negotiated cipher, PSK identity, and timing | Restrictions: Extract from SSL socket, populate all fields | Success: Complete session info returned

- [x] 60. Handle handshake exceptions appropriately
  - _Leverage:_ Exception handling best practices
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Error handler | Task: Catch SSL handshake exceptions and map to appropriate error responses | Restrictions: Distinguish timeout, auth failure, protocol errors | Success: Exceptions handled gracefully

- [x] 61. Log warning at initialization when NULL ciphers enabled
  - _Leverage:_ Security warning patterns
  - _Requirements:_ 1
  - _Prompt:_ Role: Security auditor | Task: Log prominent warning when NULL (unencrypted) ciphers are enabled | Restrictions: Use WARNING level, make message clear | Success: Warning logged on NULL cipher enable

- [x] 62. Log each connection using NULL cipher suite
  - _Leverage:_ Per-connection security audit
  - _Requirements:_ 1
  - _Prompt:_ Role: Security logger | Task: Log whenever a connection negotiates NULL cipher | Restrictions: Include session ID, log at WARNING level | Success: NULL cipher usage logged

- [x] 63. Include prominent "UNENCRYPTED TRAFFIC" message for NULL ciphers
  - _Leverage:_ Clear security messaging
  - _Requirements:_ 1
  - _Prompt:_ Role: Security communicator | Task: Add "UNENCRYPTED TRAFFIC" to log messages for NULL cipher connections | Restrictions: Make highly visible, impossible to miss | Success: Unencrypted traffic clearly marked

- [x] 64. Implement `handle_handshake_error()` method
  - _Leverage:_ Centralized error handling
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Error handling specialist | Task: Create method handling various handshake failure scenarios | Restrictions: Log appropriately, return diagnostic info | Success: Handshake errors handled systematically

- [x] 65. Track partial handshake state using HandshakeState dataclass
  - _Leverage:_ State tracking for diagnostics
  - _Requirements:_ 8
  - _Prompt:_ Role: Diagnostic implementer | Task: Track which handshake messages were received before failure | Restrictions: Use HandshakeState enum, update on each message | Success: Partial state tracked for diagnostics

- [x] 66. Map exceptions to appropriate TLS alerts
  - _Leverage:_ TLS specification alert mapping
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: TLS protocol expert | Task: Map Python exceptions to TLS alert codes (timeout→close_notify, auth fail→decrypt_error) | Restrictions: Follow TLS 1.2 alert semantics | Success: Correct TLS alerts sent

- [x] 67. Log partial state on timeout
  - _Leverage:_ Diagnostic logging for network issues
  - _Requirements:_ 8
  - _Prompt:_ Role: Network diagnostician | Task: Log partial handshake state when timeout occurs | Restrictions: Include last message received, timestamp | Success: Timeout diagnostics logged

- [x] 68. Write unit tests for SSL context creation with default ciphers
  - _Leverage:_ Configuration testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test SSL context created with default cipher suite configuration | Restrictions: Verify correct ciphers set | Success: Default cipher test passes

- [x] 69. Write unit tests for SSL context creation with legacy ciphers
  - _Leverage:_ Compatibility testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test SSL context with legacy cipher configuration enabled | Restrictions: Verify legacy ciphers included | Success: Legacy cipher test passes

- [x] 70. Write unit tests for SSL context creation with NULL ciphers
  - _Leverage:_ Test mode validation
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test SSL context with NULL cipher configuration and warning logging | Restrictions: Verify NULL ciphers enabled, warning logged | Success: NULL cipher test passes

- [x] 71. Write unit tests for PSK callback with valid identity
  - _Leverage:_ Authentication testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test PSK callback returns correct key bytes for known identity | Restrictions: Use MockKeyStore, verify key bytes | Success: Valid identity test passes

- [x] 72. Write unit tests for PSK callback with invalid identity
  - _Leverage:_ Negative authentication testing
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Test engineer | Task: Test PSK callback returns None for unknown identity | Restrictions: Verify handshake fails appropriately | Success: Invalid identity test passes

- [x] 73. Write unit tests for handshake error mapping
  - _Leverage:_ Error scenario testing
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Test engineer | Task: Test various handshake exceptions map to correct TLS alerts | Restrictions: Test timeout, PSK mismatch, protocol errors | Success: Error mapping tests pass

### 5. Session Manager Implementation

- [x] 74. Create `session_manager.py` with SessionManager class
  - _Leverage:_ Session management patterns
  - _Requirements:_ 4
  - _Prompt:_ Role: Session architect | Task: Create SessionManager class managing OTA session lifecycle | Restrictions: Thread-safe implementation, support concurrent sessions | Success: SessionManager class created

- [x] 75. Implement `__init__` with EventEmitter parameter
  - _Leverage:_ Event-driven architecture
  - _Requirements:_ 4, 7
  - _Prompt:_ Role: Integration developer | Task: Initialize SessionManager with EventEmitter for event emission | Restrictions: Store emitter reference, initialize session storage | Success: Initialization with EventEmitter works

- [x] 76. Store sessions in thread-safe dictionary
  - _Leverage:_ Thread-safe collections
  - _Requirements:_ 4
  - _Prompt:_ Role: Concurrency engineer | Task: Use threading.Lock and dict to store sessions safely | Restrictions: Lock access to session dict, prevent race conditions | Success: Thread-safe session storage

- [x] 77. Implement `create_session()` method with UUID generation
  - _Leverage:_ UUID for unique IDs
  - _Requirements:_ 4
  - _Prompt:_ Role: Session creator | Task: Generate unique session ID using UUID and create Session object | Restrictions: Use uuid.uuid4(), initialize session state | Success: Unique sessions created

- [x] 78. Implement `get_session(session_id)` method
  - _Leverage:_ Dictionary lookup pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Session retriever | Task: Implement thread-safe session retrieval by ID | Restrictions: Return None if not found, use locking | Success: Session retrieval works safely

- [x] 79. Implement `close_session(session_id, reason)` method
  - _Leverage:_ Resource cleanup pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Session lifecycle manager | Task: Close session, generate summary, emit event, remove from storage | Restrictions: Handle missing sessions gracefully | Success: Session closure complete

- [x] 80. Generate session summary on close
  - _Leverage:_ Summary generation pattern
  - _Requirements:_ 4, 7
  - _Prompt:_ Role: Summary generator | Task: Create session summary with duration, command count, final status | Restrictions: Calculate from session data, include all metrics | Success: Complete summary generated

- [x] 81. Define state transitions (HANDSHAKING → CONNECTED → ACTIVE → CLOSED)
  - _Leverage:_ State machine design
  - _Requirements:_ 4
  - _Prompt:_ Role: State machine designer | Task: Define valid state transition rules for session lifecycle | Restrictions: Enforce one-way transitions, document flow | Success: State transitions defined clearly

- [x] 82. Implement state change method with validation
  - _Leverage:_ State transition validation
  - _Requirements:_ 4
  - _Prompt:_ Role: State validator | Task: Implement method changing session state with validation of valid transitions | Restrictions: Reject invalid transitions, log state changes | Success: State changes validated

- [x] 83. Emit events on state transitions
  - _Leverage:_ Event-driven state changes
  - _Requirements:_ 4, 7
  - _Prompt:_ Role: Event integrator | Task: Emit appropriate events when session state changes | Restrictions: Include session ID and new state in event | Success: State change events emitted

- [x] 84. Prevent invalid state transitions
  - _Leverage:_ State machine enforcement
  - _Requirements:_ 4
  - _Prompt:_ Role: State enforcer | Task: Raise exception or log error when invalid state transition attempted | Restrictions: Don't allow backward transitions | Success: Invalid transitions prevented

- [x] 85. Create background timer thread for expiration checking
  - _Leverage:_ Background thread pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Background task designer | Task: Create daemon thread running periodic session expiration checks | Restrictions: Use threading.Thread, make daemon | Success: Background timer thread running

- [x] 86. Run expiration check every 30 seconds
  - _Leverage:_ Periodic task execution
  - _Requirements:_ 4
  - _Prompt:_ Role: Scheduler | Task: Implement loop in timer thread checking sessions every 30 seconds | Restrictions: Use time.sleep(30), handle shutdown signal | Success: Periodic checks execute correctly

- [x] 87. Implement `cleanup_expired()` method
  - _Leverage:_ Batch cleanup pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Cleanup implementer | Task: Iterate sessions, close those exceeding timeout threshold | Restrictions: Check last_activity timestamp, use configured timeout | Success: Expired sessions cleaned up

- [x] 88. Close sessions exceeding timeout (default 300s)
  - _Leverage:_ Timeout-based lifecycle
  - _Requirements:_ 4
  - _Prompt:_ Role: Timeout enforcer | Task: Close sessions with last_activity older than timeout value | Restrictions: Default 300s, configurable, use CloseReason.TIMEOUT | Success: Timed out sessions closed

- [x] 89. Emit session_ended event with timeout reason
  - _Leverage:_ Event notification
  - _Requirements:_ 4, 7
  - _Prompt:_ Role: Event emitter | Task: Emit session_ended event when timeout causes closure | Restrictions: Include session summary and TIMEOUT reason | Success: Timeout events emitted

- [x] 90. Add method to record APDU exchange in session
  - _Leverage:_ Exchange tracking pattern
  - _Requirements:_ 3, 4
  - _Prompt:_ Role: Exchange recorder | Task: Implement method adding APDUExchange to session history | Restrictions: Create APDUExchange object, append to session list | Success: APDU exchanges recorded

- [x] 91. Track command, response, timestamp, duration per exchange
  - _Leverage:_ Detailed exchange tracking
  - _Requirements:_ 3, 4
  - _Prompt:_ Role: Metrics tracker | Task: Record command bytes, response bytes, timestamp, and duration for each APDU | Restrictions: Capture all fields in APDUExchange | Success: Complete exchange data tracked

- [x] 92. Increment command_count on each exchange
  - _Leverage:_ Counter pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Counter maintainer | Task: Increment session command_count field each time APDU recorded | Restrictions: Thread-safe increment | Success: Command count accurate

- [x] 93. Update last_activity timestamp on each exchange
  - _Leverage:_ Activity tracking for timeout
  - _Requirements:_ 4
  - _Prompt:_ Role: Activity tracker | Task: Update session last_activity to current time on each APDU exchange | Restrictions: Use time.time() or datetime.now() | Success: Activity timestamp updated

- [x] 94. Write unit tests for session creation with unique IDs
  - _Leverage:_ Uniqueness testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test multiple sessions created have unique IDs | Restrictions: Create multiple, verify no collisions | Success: Unique ID test passes

- [x] 95. Write unit tests for session retrieval
  - _Leverage:_ CRUD testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test get_session returns correct session, None for invalid ID | Restrictions: Test both found and not found cases | Success: Retrieval tests pass

- [x] 96. Write unit tests for valid state transitions
  - _Leverage:_ State machine testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test all valid state transitions work correctly | Restrictions: Test HANDSHAKING→CONNECTED→ACTIVE→CLOSED | Success: Valid transition tests pass

- [x] 97. Write unit tests for invalid state transitions
  - _Leverage:_ Negative state testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test invalid state transitions are rejected | Restrictions: Try backward transitions, verify rejection | Success: Invalid transition tests pass

- [x] 98. Write unit tests for session timeout expiration
  - _Leverage:_ Timeout testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test sessions exceeding timeout are closed automatically | Restrictions: Mock time, verify cleanup_expired works | Success: Timeout test passes

- [x] 99. Write unit tests for APDU exchange tracking
  - _Leverage:_ Exchange tracking verification
  - _Requirements:_ 3, 4
  - _Prompt:_ Role: Test engineer | Task: Test APDU exchanges recorded with all fields correct | Restrictions: Verify command_count increments, last_activity updates | Success: Exchange tracking tests pass

- [x] 100. Write unit tests for concurrent session access
  - _Leverage:_ Concurrency testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Concurrency test engineer | Task: Test multiple threads accessing sessions simultaneously without corruption | Restrictions: Use threading, verify thread safety | Success: Concurrent access tests pass

### 6. Error Handler Implementation

- [x] 101. Create `error_handler.py` with ErrorHandler class
  - _Leverage:_ Centralized error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Error handling architect | Task: Create ErrorHandler class managing all error scenarios | Restrictions: Integrate with EventEmitter for alerting | Success: ErrorHandler class created

- [x] 102. Initialize with EventEmitter and MetricsCollector
  - _Leverage:_ Dependency injection
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Integration developer | Task: Initialize ErrorHandler with EventEmitter and optional MetricsCollector | Restrictions: Store references, allow None for MetricsCollector | Success: Initialization with dependencies works

- [x] 103. Configure mismatch threshold and time window
  - _Leverage:_ Configurable detection thresholds
  - _Requirements:_ 8
  - _Prompt:_ Role: Configuration designer | Task: Add parameters for PSK mismatch threshold (count) and time window (seconds) | Restrictions: Provide defaults (3 mismatches, 60s window) | Success: Thresholds configurable

- [x] 104. Implement `handle_connection_interrupted()` method
  - _Leverage:_ Connection error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Connection error handler | Task: Handle mid-session connection interruptions with logging and cleanup | Restrictions: Log session_id, last command, timestamp | Success: Interruption handling implemented

- [x] 105. Log session_id, last_command, timestamp on interruption
  - _Leverage:_ Diagnostic logging
  - _Requirements:_ 8
  - _Prompt:_ Role: Diagnostic logger | Task: Log complete interruption context for troubleshooting | Restrictions: Include all relevant session state | Success: Complete diagnostic info logged

- [x] 106. Emit `connection_interrupted` event
  - _Leverage:_ Event notification
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Event emitter | Task: Emit connection_interrupted event with diagnostic details | Restrictions: Include session ID, last command in event data | Success: Interruption events emitted

- [x] 107. Trigger session cleanup on interruption
  - _Leverage:_ Resource cleanup
  - _Requirements:_ 4, 8
  - _Prompt:_ Role: Cleanup coordinator | Task: Call SessionManager to close interrupted session | Restrictions: Use CloseReason.ERROR, cleanup within 5s | Success: Interrupted sessions cleaned up

- [x] 108. Implement `handle_psk_mismatch()` method
  - _Leverage:_ Authentication error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Auth error handler | Task: Handle PSK key mismatch scenarios with tracking and alerting | Restrictions: Never log key values, log identity only | Success: PSK mismatch handling implemented

- [x] 109. Implement MismatchTracker for per-IP tracking
  - _Leverage:_ Per-source error tracking
  - _Requirements:_ 8
  - _Prompt:_ Role: Tracking system designer | Task: Track PSK mismatches per client IP with timestamps in time window | Restrictions: Use deque or list with time-based filtering | Success: Per-IP mismatch tracking works

- [x] 110. Log identity and client_addr (never key values)
  - _Leverage:_ Secure logging
  - _Requirements:_ 8
  - _Prompt:_ Role: Security-aware logger | Task: Log PSK identity and client address on mismatch, never keys | Restrictions: Audit all logs, ensure no key leakage | Success: Secure mismatch logging

- [x] 111. Emit `psk_mismatch` event
  - _Leverage:_ Security event notification
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Security event emitter | Task: Emit psk_mismatch event for monitoring and alerting | Restrictions: Include identity, client_addr in event | Success: Mismatch events emitted

- [x] 112. Log warning when multiple mismatches from same source in window
  - _Leverage:_ Anomaly detection
  - _Requirements:_ 8
  - _Prompt:_ Role: Anomaly detector | Task: Log warning when client has multiple mismatches within time window | Restrictions: Check threshold, log at WARNING level | Success: Repeated mismatch warnings logged

- [x] 113. Return TLS Alert 51 (decrypt_error) on mismatch
  - _Leverage:_ TLS protocol compliance
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: TLS alert sender | Task: Return TLS decrypt_error alert (51) when PSK mismatch detected | Restrictions: Follow TLS 1.2 specification | Success: Correct TLS alert sent

- [x] 114. Implement `handle_handshake_interrupted()` method
  - _Leverage:_ Handshake error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Handshake error handler | Task: Handle interrupted TLS handshakes with diagnostic logging | Restrictions: Log partial state, reason, client_addr | Success: Handshake interruption handled

- [x] 115. Log client_addr, partial_state, reason
  - _Leverage:_ Handshake diagnostics
  - _Requirements:_ 8
  - _Prompt:_ Role: Handshake diagnostician | Task: Log complete handshake interruption context | Restrictions: Include which messages were received | Success: Complete handshake diagnostics logged

- [x] 116. Emit `handshake_interrupted` event
  - _Leverage:_ Handshake event notification
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Event emitter | Task: Emit handshake_interrupted event with failure details | Restrictions: Include partial state in event data | Success: Handshake interruption events emitted

- [x] 117. Log as "potential network issue" if only ClientHello received
  - _Leverage:_ Network diagnosis
  - _Requirements:_ 8
  - _Prompt:_ Role: Network diagnostician | Task: Detect when only ClientHello received and log as likely network issue | Restrictions: Check partial state, use specific message | Success: Network issues identified in logs

- [x] 118. Implement `check_error_rate()` method
  - _Leverage:_ Rate-based anomaly detection
  - _Requirements:_ 8
  - _Prompt:_ Role: Rate monitor | Task: Track error rates over time and detect threshold exceedance | Restrictions: Use rolling window, configurable threshold | Success: Error rate checking implemented

- [x] 119. Track error counts over rolling time window
  - _Leverage:_ Time-windowed counters
  - _Requirements:_ 8
  - _Prompt:_ Role: Time-series tracker | Task: Maintain error counts in sliding time window for rate calculation | Restrictions: Use efficient data structure, prune old entries | Success: Rolling window tracking works

- [x] 120. Emit `high_error_rate` event when threshold exceeded
  - _Leverage:_ Threshold-based alerting
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Alert emitter | Task: Emit high_error_rate event when error rate crosses threshold | Restrictions: Include error type, rate, threshold in event | Success: High error rate alerts emitted

- [x] 121. Include error_type, rate, threshold in event
  - _Leverage:_ Rich event data
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Event data designer | Task: Populate high_error_rate event with error type, calculated rate, and threshold | Restrictions: Include all diagnostic fields | Success: Complete error rate event data

- [x] 122. Write unit tests for connection interruption handling
  - _Leverage:_ Interruption scenario testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Test engineer | Task: Test handle_connection_interrupted logs correctly and emits event | Restrictions: Verify all fields logged, event emitted | Success: Interruption handling test passes

- [x] 123. Write unit tests for PSK mismatch with single occurrence
  - _Leverage:_ Single mismatch testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Test engineer | Task: Test single PSK mismatch logged and emitted without warning | Restrictions: Verify no threshold warning for single occurrence | Success: Single mismatch test passes

- [x] 124. Write unit tests for PSK mismatch warning with multiple occurrences
  - _Leverage:_ Threshold testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Test engineer | Task: Test multiple mismatches from same IP trigger warning | Restrictions: Verify warning logged when threshold exceeded | Success: Multiple mismatch test passes

- [x] 125. Write unit tests for handshake interruption with various partial states
  - _Leverage:_ State-based testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Test engineer | Task: Test handshake interruption handling with different partial states | Restrictions: Test ClientHello-only, mid-handshake scenarios | Success: Partial state tests pass

- [x] 126. Write unit tests for error rate threshold detection
  - _Leverage:_ Rate monitoring testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Test engineer | Task: Test error rate tracking and threshold event emission | Restrictions: Mock time, inject errors, verify event | Success: Error rate detection test passes

### 7. HTTP Handler Implementation

- [x] 127. Create `http_handler.py` with HTTPHandler class
  - _Leverage:_ HTTP protocol handling
  - _Requirements:_ 2
  - _Prompt:_ Role: HTTP protocol implementer | Task: Create HTTPHandler class parsing and building GP Admin HTTP messages | Restrictions: Follow GP Amendment B HTTP protocol | Success: HTTPHandler class created

- [x] 128. Define CONTENT_TYPE constant for GP Admin protocol
  - _Leverage:_ Protocol constants
  - _Requirements:_ 2
  - _Prompt:_ Role: Protocol constant definer | Task: Define constant for application/vnd.globalplatform.card-content-mgt;version=1.0 | Restrictions: Match exact GP specification string | Success: Content-type constant defined

- [x] 129. Initialize with GPCommandProcessor reference
  - _Leverage:_ Handler composition
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Integration designer | Task: Initialize HTTPHandler with GPCommandProcessor for command routing | Restrictions: Store reference, validate not None | Success: Initialization with processor works

- [x] 130. Implement `parse_admin_request()` method
  - _Leverage:_ HTTP parsing
  - _Requirements:_ 2
  - _Prompt:_ Role: Request parser | Task: Parse raw bytes into HTTP headers and body | Restrictions: Handle malformed requests gracefully | Success: Request parsing implemented

- [x] 131. Parse HTTP headers from raw bytes
  - _Leverage:_ HTTP header parsing
  - _Requirements:_ 2
  - _Prompt:_ Role: Header parser | Task: Extract HTTP headers from request bytes | Restrictions: Split on \r\n, parse name:value pairs | Success: Headers parsed correctly

- [x] 132. Validate Content-Type header
  - _Leverage:_ Protocol compliance validation
  - _Requirements:_ 2
  - _Prompt:_ Role: Protocol validator | Task: Verify Content-Type matches GP Admin protocol | Restrictions: Case-insensitive comparison, reject mismatches | Success: Content-Type validated

- [x] 133. Return 415 Unsupported Media Type for invalid content-type
  - _Leverage:_ HTTP error responses
  - _Requirements:_ 2
  - _Prompt:_ Role: Error responder | Task: Return HTTP 415 when Content-Type is incorrect | Restrictions: Build proper HTTP error response | Success: 415 response sent correctly

- [x] 134. Extract body as GP Admin request
  - _Leverage:_ Body extraction
  - _Requirements:_ 2
  - _Prompt:_ Role: Body extractor | Task: Extract HTTP body bytes containing GP Admin request | Restrictions: Use Content-Length if present, handle chunked | Success: Request body extracted

- [x] 135. Parse GP Admin request body for APDU extraction
  - _Leverage:_ GP Admin protocol parsing
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: GP protocol parser | Task: Parse GP Admin request format to extract APDUs | Restrictions: Follow GP Amendment B specification | Success: GP Admin request parsed

- [x] 136. Extract APDU commands from request
  - _Leverage:_ APDU extraction
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: APDU extractor | Task: Extract one or more APDU command bytes from GP request | Restrictions: Handle TLV encoding, validate structure | Success: APDUs extracted correctly

- [x] 137. Handle multiple APDUs in single request
  - _Leverage:_ Batch processing
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Batch handler | Task: Support processing multiple APDUs in one GP Admin request | Restrictions: Process in order, collect responses | Success: Multiple APDU handling works

- [x] 138. Validate APDU structure
  - _Leverage:_ APDU validation
  - _Requirements:_ 3
  - _Prompt:_ Role: APDU validator | Task: Validate APDU has valid CLA, INS, P1, P2, length fields | Restrictions: Check minimum length, structure correctness | Success: APDU validation implemented

- [x] 139. Implement `build_admin_response()` method
  - _Leverage:_ Response construction
  - _Requirements:_ 2
  - _Prompt:_ Role: Response builder | Task: Build GP Admin HTTP response from APDU responses | Restrictions: Follow GP Amendment B response format | Success: Response building implemented

- [x] 140. Wrap APDU responses in GP Admin format
  - _Leverage:_ GP protocol wrapping
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Protocol wrapper | Task: Wrap APDU response bytes in GP Admin response structure | Restrictions: Use correct TLV encoding | Success: APDU responses wrapped correctly

- [x] 141. Build HTTP response with proper headers
  - _Leverage:_ HTTP response construction
  - _Requirements:_ 2
  - _Prompt:_ Role: HTTP response builder | Task: Construct HTTP response with status line, headers, body | Restrictions: Include Content-Type, Content-Length | Success: HTTP response built correctly

- [x] 142. Handle keep-alive for session continuity
  - _Leverage:_ HTTP keep-alive mechanism
  - _Requirements:_ 2, 4
  - _Prompt:_ Role: Connection manager | Task: Support Connection: keep-alive for multiple requests per session | Restrictions: Parse Connection header, maintain socket | Success: Keep-alive working

- [x] 143. Implement `handle_request(ssl_socket, session)` method
  - _Leverage:_ Request handling orchestration
  - _Requirements:_ 2, 3, 4
  - _Prompt:_ Role: Request orchestrator | Task: Coordinate full request handling: read, parse, process, respond | Restrictions: Handle each step, propagate errors | Success: Full request handling works

- [x] 144. Read HTTP request from socket
  - _Leverage:_ Socket reading
  - _Requirements:_ 2
  - _Prompt:_ Role: Socket reader | Task: Read HTTP request bytes from SSL socket | Restrictions: Handle partial reads, use timeouts | Success: Request reading works

- [x] 145. Parse and validate request
  - _Leverage:_ Request validation pipeline
  - _Requirements:_ 2
  - _Prompt:_ Role: Request validator | Task: Parse request and validate all protocol requirements | Restrictions: Return error responses for invalid requests | Success: Request validation complete

- [x] 146. Route to command processor
  - _Leverage:_ Command routing
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Request router | Task: Pass validated APDUs to GPCommandProcessor for execution | Restrictions: Collect responses, maintain order | Success: Routing to processor works

- [x] 147. Send response back on socket
  - _Leverage:_ Socket writing
  - _Requirements:_ 2
  - _Prompt:_ Role: Socket writer | Task: Send HTTP response bytes back on SSL socket | Restrictions: Handle write errors, flush buffers | Success: Response sending works

- [x] 148. Write unit tests for request parsing with valid GP Admin request
  - _Leverage:_ Positive parsing tests
  - _Requirements:_ 2
  - _Prompt:_ Role: Test engineer | Task: Test parsing valid GP Admin request extracts APDUs correctly | Restrictions: Use sample valid requests | Success: Valid request parsing test passes

- [x] 149. Write unit tests for content-type validation
  - _Leverage:_ Validation testing
  - _Requirements:_ 2
  - _Prompt:_ Role: Test engineer | Task: Test content-type validation rejects invalid types with 415 | Restrictions: Test correct and incorrect content types | Success: Content-type validation test passes

- [x] 150. Write unit tests for APDU extraction from request body
  - _Leverage:_ Extraction testing
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Test engineer | Task: Test APDU extraction from GP Admin request body | Restrictions: Verify correct APDU bytes extracted | Success: APDU extraction test passes

- [x] 151. Write unit tests for response building
  - _Leverage:_ Response construction testing
  - _Requirements:_ 2
  - _Prompt:_ Role: Test engineer | Task: Test GP Admin response building from APDU responses | Restrictions: Verify correct HTTP and GP format | Success: Response building test passes

- [x] 152. Write unit tests for HTTP keep-alive handling
  - _Leverage:_ Connection persistence testing
  - _Requirements:_ 2, 4
  - _Prompt:_ Role: Test engineer | Task: Test keep-alive allows multiple requests on same connection | Restrictions: Simulate multiple requests, verify socket reuse | Success: Keep-alive test passes

### 8. GP Command Processor Implementation

- [x] 153. Create `gp_command_processor.py` with GPCommandProcessor class
  - _Leverage:_ Command pattern
  - _Requirements:_ 3
  - _Prompt:_ Role: Command processor architect | Task: Create GPCommandProcessor routing APDUs to handlers | Restrictions: Use handler registry pattern | Success: GPCommandProcessor class created

- [x] 154. Initialize with response handlers dict and EventEmitter
  - _Leverage:_ Handler registry pattern
  - _Requirements:_ 3, 7
  - _Prompt:_ Role: Processor initializer | Task: Initialize with handler registry and EventEmitter for events | Restrictions: Use dict[int, Callable] for handlers | Success: Initialization with handlers works

- [x] 155. Implement `register_handler(ins_code, handler)` method
  - _Leverage:_ Dynamic handler registration
  - _Requirements:_ 3
  - _Prompt:_ Role: Handler registrar | Task: Allow dynamic registration of APDU INS handlers | Restrictions: Validate INS code, store handler callable | Success: Handler registration works

- [x] 156. Implement `process_command(apdu)` routing method
  - _Leverage:_ Command routing pattern
  - _Requirements:_ 3
  - _Prompt:_ Role: Command router | Task: Route APDU to appropriate handler based on INS byte | Restrictions: Extract INS, lookup handler, invoke | Success: Command routing works

- [x] 157. Implement SelectHandler (INS 0xA4)
  - _Leverage:_ GP SELECT command knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP command implementer | Task: Implement handler for SELECT (0xA4) command | Restrictions: Parse SELECT parameters, return appropriate response | Success: SELECT handler works

- [x] 158. Implement InstallHandler (INS 0xE6)
  - _Leverage:_ GP INSTALL command knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP command implementer | Task: Implement handler for INSTALL (0xE6) command | Restrictions: Parse INSTALL parameters, simulate installation | Success: INSTALL handler works

- [x] 159. Implement DeleteHandler (INS 0xE4)
  - _Leverage:_ GP DELETE command knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP command implementer | Task: Implement handler for DELETE (0xE4) command | Restrictions: Parse DELETE parameters, simulate deletion | Success: DELETE handler works

- [x] 160. Implement GetStatusHandler (INS 0xF2)
  - _Leverage:_ GP GET STATUS command knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP command implementer | Task: Implement handler for GET STATUS (0xF2) command | Restrictions: Return card content status information | Success: GET STATUS handler works

- [x] 161. Implement InitUpdateHandler (INS 0x50)
  - _Leverage:_ GP INIT UPDATE command knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP secure channel implementer | Task: Implement handler for INITIALIZE UPDATE (0x50) command | Restrictions: Generate appropriate cryptographic response | Success: INIT UPDATE handler works

- [x] 162. Implement ExtAuthHandler (INS 0x82)
  - _Leverage:_ GP EXTERNAL AUTHENTICATE knowledge
  - _Requirements:_ 3
  - _Prompt:_ Role: GP authentication implementer | Task: Implement handler for EXTERNAL AUTHENTICATE (0x82) command | Restrictions: Validate authentication data | Success: EXT AUTH handler works

- [x] 163. Return SW 6D00 for unknown INS codes
  - _Leverage:_ GP error handling
  - _Requirements:_ 3
  - _Prompt:_ Role: Error responder | Task: Return status word 6D00 (INS not supported) for unknown commands | Restrictions: Follow GP specification for unknown INS | Success: Unknown INS handling correct

- [x] 164. Log command bytes on receipt
  - _Leverage:_ Protocol-level logging
  - _Requirements:_ 3
  - _Prompt:_ Role: Command logger | Task: Log received APDU command bytes in hex format | Restrictions: Use DEBUG level, include CLA, INS, P1, P2, Lc | Success: Commands logged correctly

- [x] 165. Log response bytes on send
  - _Leverage:_ Response logging
  - _Requirements:_ 3
  - _Prompt:_ Role: Response logger | Task: Log APDU response bytes and status word in hex | Restrictions: Use DEBUG level, include data and SW | Success: Responses logged correctly

- [x] 166. Log status word
  - _Leverage:_ Status tracking
  - _Requirements:_ 3
  - _Prompt:_ Role: Status logger | Task: Log APDU status word (SW1 SW2) for each response | Restrictions: Interpret status words, use INFO level | Success: Status words logged

- [x] 167. Log timing (duration in ms)
  - _Leverage:_ Performance tracking
  - _Requirements:_ 3
  - _Prompt:_ Role: Timing logger | Task: Log APDU processing duration in milliseconds | Restrictions: Use time.perf_counter for precision | Success: Timing logged correctly

- [x] 168. Emit `apdu_received` event
  - _Leverage:_ Event notification
  - _Requirements:_ 3, 7
  - _Prompt:_ Role: Event emitter | Task: Emit apdu_received event when command arrives | Restrictions: Include command bytes, INS, timestamp | Success: APDU received events emitted

- [x] 169. Emit `apdu_sent` event
  - _Leverage:_ Response event notification
  - _Requirements:_ 3, 7
  - _Prompt:_ Role: Event emitter | Task: Emit apdu_sent event when response sent | Restrictions: Include response bytes, status word, duration | Success: APDU sent events emitted

- [x] 170. Write unit tests for command routing to correct handler
  - _Leverage:_ Routing verification
  - _Requirements:_ 3
  - _Prompt:_ Role: Test engineer | Task: Test APDUs routed to correct handler based on INS | Restrictions: Test each INS code, verify handler called | Success: Routing tests pass

- [x] 171. Write unit tests for unknown command handling (SW 6D00)
  - _Leverage:_ Error case testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Test engineer | Task: Test unknown INS returns 6D00 status word | Restrictions: Use unregistered INS, verify response | Success: Unknown command test passes

- [x] 172. Write unit tests for event emission for APDU exchanges
  - _Leverage:_ Event testing
  - _Requirements:_ 3, 7
  - _Prompt:_ Role: Test engineer | Task: Test apdu_received and apdu_sent events emitted correctly | Restrictions: Use MockEventEmitter, verify event data | Success: APDU event tests pass

- [x] 173. Write unit tests for timing measurement
  - _Leverage:_ Timing verification
  - _Requirements:_ 3
  - _Prompt:_ Role: Test engineer | Task: Test APDU processing timing captured in events/logs | Restrictions: Verify duration field present and reasonable | Success: Timing measurement test passes

- [x] 174. Write unit tests for each handler with sample commands
  - _Leverage:_ Handler functionality testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Test engineer | Task: Test each GP command handler with valid sample APDUs | Restrictions: Test SELECT, INSTALL, DELETE, GET STATUS, etc. | Success: Handler tests pass

### 9. Admin Server Implementation

- [x] 175. Create `admin_server.py` with AdminServer class
  - _Leverage:_ Server architecture patterns
  - _Requirements:_ 1, 2, 3, 4, 5
  - _Prompt:_ Role: Server architect | Task: Create AdminServer orchestrating all components for PSK-TLS admin server | Restrictions: Integrate all handlers and managers | Success: AdminServer class created

- [x] 176. Initialize with ServerConfig, KeyStore, EventEmitter
  - _Leverage:_ Dependency injection
  - _Requirements:_ 1, 5, 7
  - _Prompt:_ Role: Server initializer | Task: Initialize AdminServer with required dependencies | Restrictions: Validate all dependencies, store references | Success: Initialization with dependencies works

- [x] 177. Accept optional MetricsCollector parameter
  - _Leverage:_ Optional feature integration
  - _Requirements:_ 5
  - _Prompt:_ Role: Optional dependency handler | Task: Support optional MetricsCollector for metrics integration | Restrictions: Allow None, use if present | Success: Optional metrics integration works

- [x] 178. Create TLSHandler instance
  - _Leverage:_ Component composition
  - _Requirements:_ 1
  - _Prompt:_ Role: Component builder | Task: Instantiate TLSHandler with KeyStore and cipher config | Restrictions: Pass required dependencies | Success: TLSHandler created in server

- [x] 179. Create HTTPHandler instance
  - _Leverage:_ Component composition
  - _Requirements:_ 2
  - _Prompt:_ Role: Component builder | Task: Instantiate HTTPHandler with GPCommandProcessor | Restrictions: Create after command processor | Success: HTTPHandler created in server

- [x] 180. Create SessionManager instance
  - _Leverage:_ Component composition
  - _Requirements:_ 4
  - _Prompt:_ Role: Component builder | Task: Instantiate SessionManager with EventEmitter | Restrictions: Start expiration timer thread | Success: SessionManager created in server

- [x] 181. Create ErrorHandler instance
  - _Leverage:_ Component composition
  - _Requirements:_ 8
  - _Prompt:_ Role: Component builder | Task: Instantiate ErrorHandler with EventEmitter and MetricsCollector | Restrictions: Configure error thresholds from config | Success: ErrorHandler created in server

- [x] 182. Implement `is_running` property
  - _Leverage:_ State query pattern
  - _Requirements:_ 6
  - _Prompt:_ Role: State accessor | Task: Implement property returning True if server is running | Restrictions: Check internal state flag | Success: is_running property works

- [x] 183. Implement `start()` method
  - _Leverage:_ Server lifecycle management
  - _Requirements:_ 6
  - _Prompt:_ Role: Server startup orchestrator | Task: Implement start method initializing all components and accepting connections | Restrictions: Set up socket, start threads, begin accepting | Success: Server starts successfully

- [x] 184. Create server socket and bind to configured port
  - _Leverage:_ Socket programming
  - _Requirements:_ 5, 6
  - _Prompt:_ Role: Socket initializer | Task: Create TCP socket and bind to configured host:port | Restrictions: Handle bind errors (port in use, etc.) | Success: Socket bound to port

- [x] 185. Set socket options (SO_REUSEADDR)
  - _Leverage:_ Socket configuration
  - _Requirements:_ 5
  - _Prompt:_ Role: Socket configurator | Task: Set SO_REUSEADDR option for quick server restart | Restrictions: Use socket.setsockopt correctly | Success: Socket options set

- [x] 186. Start listening for connections
  - _Leverage:_ Server socket listen
  - _Requirements:_ 6
  - _Prompt:_ Role: Connection listener | Task: Call socket.listen() to begin accepting connections | Restrictions: Use reasonable backlog (e.g., 5) | Success: Socket listening

- [x] 187. Create ThreadPoolExecutor for connection handling
  - _Leverage:_ Concurrent connection handling
  - _Requirements:_ 1, 6
  - _Prompt:_ Role: Concurrency manager | Task: Create ThreadPoolExecutor for parallel connection handling | Restrictions: Configure max_workers based on config | Success: Thread pool created

- [x] 188. Emit `server_started` event
  - _Leverage:_ Lifecycle event notification
  - _Requirements:_ 7
  - _Prompt:_ Role: Lifecycle event emitter | Task: Emit server_started event when server ready | Restrictions: Include listening address and port | Success: Server started event emitted

- [x] 189. Log listening address and port
  - _Leverage:_ User feedback
  - _Requirements:_ 6
  - _Prompt:_ Role: User communicator | Task: Log clear message showing server listening on host:port | Restrictions: Use INFO level, make easily visible | Success: Listening logged clearly

- [x] 190. Accept connections in main thread
  - _Leverage:_ Accept loop pattern
  - _Requirements:_ 1, 6
  - _Prompt:_ Role: Connection acceptor | Task: Loop calling socket.accept() to receive new connections | Restrictions: Handle interrupts, check shutdown flag | Success: Connections accepted

- [x] 191. Submit connection handling to thread pool
  - _Leverage:_ Work queue pattern
  - _Requirements:_ 1, 6
  - _Prompt:_ Role: Work distributor | Task: Submit each accepted connection to thread pool for handling | Restrictions: Use executor.submit, pass socket and address | Success: Connections dispatched to threads

- [x] 192. Handle accept errors gracefully
  - _Leverage:_ Error resilience
  - _Requirements:_ 8
  - _Prompt:_ Role: Accept error handler | Task: Catch and handle socket.accept() errors without crashing | Restrictions: Log error, continue accepting if recoverable | Success: Accept errors handled

- [x] 193. Check for shutdown signal in accept loop
  - _Leverage:_ Graceful shutdown
  - _Requirements:_ 6
  - _Prompt:_ Role: Shutdown responder | Task: Check shutdown flag in accept loop to exit cleanly | Restrictions: Break loop when shutdown requested | Success: Shutdown signal respected

- [x] 194. Implement `_handle_connection()` method
  - _Leverage:_ Connection handling pattern
  - _Requirements:_ 1, 2, 3, 4
  - _Prompt:_ Role: Connection handler | Task: Handle full connection lifecycle: TLS, session, requests, cleanup | Restrictions: Orchestrate all components, handle errors | Success: Connection handling complete

- [x] 195. Wrap socket with TLS via TLSHandler
  - _Leverage:_ TLS wrapping
  - _Requirements:_ 1
  - _Prompt:_ Role: TLS integrator | Task: Use TLSHandler to wrap socket and perform handshake | Restrictions: Handle handshake failures, log session info | Success: TLS wrapping works

- [x] 196. Create session via SessionManager
  - _Leverage:_ Session lifecycle integration
  - _Requirements:_ 4
  - _Prompt:_ Role: Session integrator | Task: Create session after successful TLS handshake | Restrictions: Store TLS session info, generate session ID | Success: Session created for connection

- [x] 197. Loop handling HTTP requests via HTTPHandler
  - _Leverage:_ Request loop pattern
  - _Requirements:_ 2, 4
  - _Prompt:_ Role: Request loop orchestrator | Task: Loop handling HTTP requests while connection alive | Restrictions: Support keep-alive, break on close | Success: Request loop works

- [x] 198. Handle connection errors via ErrorHandler
  - _Leverage:_ Centralized error handling
  - _Requirements:_ 8
  - _Prompt:_ Role: Error integrator | Task: Route all connection errors to ErrorHandler | Restrictions: Distinguish error types, trigger appropriate handling | Success: Errors routed to handler

- [x] 199. Close session on disconnect
  - _Leverage:_ Session cleanup
  - _Requirements:_ 4
  - _Prompt:_ Role: Cleanup coordinator | Task: Close session via SessionManager when connection ends | Restrictions: Use appropriate CloseReason, cleanup resources | Success: Session closed on disconnect

- [x] 200. Implement `stop(timeout)` method
  - _Leverage:_ Graceful shutdown pattern
  - _Requirements:_ 6
  - _Prompt:_ Role: Shutdown orchestrator | Task: Implement graceful shutdown closing all connections and resources | Restrictions: Wait for active sessions, respect timeout | Success: Graceful shutdown works

- [x] 201. Signal shutdown to accept loop
  - _Leverage:_ Shutdown signaling
  - _Requirements:_ 6
  - _Prompt:_ Role: Shutdown signaler | Task: Set shutdown flag to stop accept loop | Restrictions: Use thread-safe flag (Event or bool with lock) | Success: Accept loop stops

- [x] 202. Close all active sessions gracefully
  - _Leverage:_ Bulk session cleanup
  - _Requirements:_ 4, 6
  - _Prompt:_ Role: Session closer | Task: Close all active sessions via SessionManager | Restrictions: Use CloseReason.NORMAL, allow time for cleanup | Success: All sessions closed

- [x] 203. Shutdown ThreadPoolExecutor
  - _Leverage:_ Thread pool shutdown
  - _Requirements:_ 6
  - _Prompt:_ Role: Thread pool manager | Task: Shutdown thread pool waiting for tasks to complete | Restrictions: Use executor.shutdown(wait=True), respect timeout | Success: Thread pool shutdown cleanly

- [x] 204. Close server socket
  - _Leverage:_ Socket cleanup
  - _Requirements:_ 6
  - _Prompt:_ Role: Socket closer | Task: Close server listening socket | Restrictions: Handle close errors gracefully | Success: Server socket closed

- [x] 205. Emit `server_stopped` event
  - _Leverage:_ Lifecycle event notification
  - _Requirements:_ 7
  - _Prompt:_ Role: Lifecycle event emitter | Task: Emit server_stopped event when shutdown complete | Restrictions: Include shutdown reason, duration | Success: Server stopped event emitted

- [x] 206. Ensure cleanup completes within timeout
  - _Leverage:_ Timeout enforcement
  - _Requirements:_ 6
  - _Prompt:_ Role: Timeout enforcer | Task: Ensure all cleanup completes within specified timeout | Restrictions: Force close if timeout exceeded | Success: Timeout respected

- [x] 207. Implement `get_active_sessions()` method
  - _Leverage:_ Session query pattern
  - _Requirements:_ 4, 6
  - _Prompt:_ Role: Session query implementer | Task: Return list of currently active sessions | Restrictions: Query SessionManager, return thread-safely | Success: Active sessions returned

- [x] 208. Return list of active Session objects
  - _Leverage:_ Data access pattern
  - _Requirements:_ 4
  - _Prompt:_ Role: Data accessor | Task: Return list of Session objects for active sessions | Restrictions: Return copies or immutable views | Success: Session list returned safely

- [x] 209. Ensure thread-safe access to session manager
  - _Leverage:_ Thread safety
  - _Requirements:_ 4
  - _Prompt:_ Role: Thread safety enforcer | Task: Use SessionManager's thread-safe methods for access | Restrictions: Don't directly access internal state | Success: Thread-safe session access

- [x] 210. Write unit tests for server start and stop
  - _Leverage:_ Lifecycle testing
  - _Requirements:_ 6
  - _Prompt:_ Role: Test engineer | Task: Test server starts, accepts connections, and stops gracefully | Restrictions: Test start, verify listening, call stop | Success: Lifecycle tests pass

- [x] 211. Write unit tests for connection acceptance
  - _Leverage:_ Connection testing
  - _Requirements:_ 1, 6
  - _Prompt:_ Role: Test engineer | Task: Test server accepts and handles client connections | Restrictions: Create test client, connect, verify handling | Success: Connection acceptance test passes

- [x] 212. Write unit tests for graceful shutdown with active sessions
  - _Leverage:_ Shutdown testing
  - _Requirements:_ 4, 6
  - _Prompt:_ Role: Test engineer | Task: Test server shutdown with active sessions closes them gracefully | Restrictions: Create sessions, call stop, verify closure | Success: Graceful shutdown test passes

- [x] 213. Write unit tests for max connections limit
  - _Leverage:_ Capacity testing
  - _Requirements:_ 6
  - _Prompt:_ Role: Test engineer | Task: Test server respects max concurrent connections limit | Restrictions: Configure limit, exceed it, verify rejection | Success: Connection limit test passes

### 10. CLI Integration

- [x] 214. Create `cardlink/cli/server.py` with Click commands
  - _Leverage:_ Click CLI framework
  - _Requirements:_ 6
  - _Prompt:_ Role: CLI developer | Task: Create Click command group for server CLI interface | Restrictions: Use Click decorators, follow CLI conventions | Success: Server CLI module created

- [x] 215. Implement `start` command
  - _Leverage:_ Click command pattern
  - _Requirements:_ 6
  - _Prompt:_ Role: CLI command implementer | Task: Implement 'cardlink-server start' command | Restrictions: Initialize server, handle errors, run until stopped | Success: Start command works

- [x] 216. Add `--port` option (default 8443)
  - _Leverage:_ Click options
  - _Requirements:_ 5, 6
  - _Prompt:_ Role: CLI option designer | Task: Add --port option with default 8443 | Restrictions: Validate port range (1-65535) | Success: Port option works

- [x] 217. Add `--config` option for YAML config file path
  - _Leverage:_ Configuration file support
  - _Requirements:_ 5, 6
  - _Prompt:_ Role: Config option implementer | Task: Add --config option accepting YAML file path | Restrictions: Validate file exists, parse YAML | Success: Config file option works

- [x] 218. Add `--dashboard` flag to enable web dashboard
  - _Leverage:_ Feature flags
  - _Requirements:_ 6
  - _Prompt:_ Role: Feature flag implementer | Task: Add --dashboard boolean flag to enable dashboard | Restrictions: Default False, start dashboard if True | Success: Dashboard flag works

- [x] 219. Add `--ciphers` option for cipher suite selection
  - _Leverage:_ Security configuration
  - _Requirements:_ 1, 5, 6
  - _Prompt:_ Role: Cipher option implementer | Task: Add --ciphers option for cipher suite selection (default, legacy, all) | Restrictions: Validate choice, configure TLSHandler | Success: Cipher selection works

- [x] 220. Add `--enable-null-ciphers` flag with prominent warning
  - _Leverage:_ Security warning pattern
  - _Requirements:_ 1, 6
  - _Prompt:_ Role: Security option implementer | Task: Add --enable-null-ciphers flag with warning confirmation | Restrictions: Require confirmation, log warnings | Success: NULL cipher flag works with warning

- [x] 221. Implement `stop` command
  - _Leverage:_ Process control
  - _Requirements:_ 6
  - _Prompt:_ Role: CLI command implementer | Task: Implement 'cardlink-server stop' command | Restrictions: Send shutdown signal, wait for graceful shutdown | Success: Stop command works

- [x] 222. Send shutdown signal to running server
  - _Leverage:_ Inter-process communication
  - _Requirements:_ 6
  - _Prompt:_ Role: IPC implementer | Task: Send signal to running server process to initiate shutdown | Restrictions: Use signal, socket, or file-based IPC | Success: Shutdown signal sent

- [x] 223. Wait for graceful shutdown
  - _Leverage:_ Shutdown monitoring
  - _Requirements:_ 6
  - _Prompt:_ Role: Shutdown monitor | Task: Wait for server to complete graceful shutdown | Restrictions: Timeout after reasonable period (30s) | Success: Graceful shutdown monitored

- [x] 224. Report shutdown status
  - _Leverage:_ User feedback
  - _Requirements:_ 6
  - _Prompt:_ Role: Status reporter | Task: Display shutdown status (success, timeout, error) to user | Restrictions: Clear messaging, appropriate exit codes | Success: Shutdown status reported

- [x] 225. Implement configuration loading from YAML file
  - _Leverage:_ YAML configuration pattern
  - _Requirements:_ 5
  - _Prompt:_ Role: Config loader | Task: Load server configuration from YAML file | Restrictions: Use pyyaml, validate structure | Success: YAML config loading works

- [x] 226. Support environment variable overrides
  - _Leverage:_ Environment variable configuration
  - _Requirements:_ 5
  - _Prompt:_ Role: Config override implementer | Task: Allow environment variables to override config file values | Restrictions: Use CARDLINK_* prefix, document variables | Success: Environment overrides work

- [x] 227. Validate configuration on load
  - _Leverage:_ Configuration validation
  - _Requirements:_ 5
  - _Prompt:_ Role: Config validator | Task: Validate loaded configuration has all required fields and valid values | Restrictions: Use Pydantic or manual validation | Success: Config validation works

- [x] 228. Fail fast with clear error message on invalid config
  - _Leverage:_ Fail-fast principle
  - _Requirements:_ 5
  - _Prompt:_ Role: Error communicator | Task: Exit immediately with clear error on invalid configuration | Restrictions: Display specific validation errors | Success: Invalid config errors clear

- [x] 229. Write CLI integration tests for `cardlink-server start`
  - _Leverage:_ CLI testing
  - _Requirements:_ 6
  - _Prompt:_ Role: CLI test engineer | Task: Test 'cardlink-server start' command starts server successfully | Restrictions: Use Click testing utilities | Success: Start command test passes

- [x] 230. Write CLI integration tests for `cardlink-server start --port 9443`
  - _Leverage:_ Option testing
  - _Requirements:_ 5, 6
  - _Prompt:_ Role: CLI test engineer | Task: Test --port option changes server listening port | Restrictions: Verify server binds to specified port | Success: Port option test passes

- [x] 231. Write CLI integration tests for `cardlink-server stop`
  - _Leverage:_ Command testing
  - _Requirements:_ 6
  - _Prompt:_ Role: CLI test engineer | Task: Test 'cardlink-server stop' command stops running server | Restrictions: Start server, call stop, verify shutdown | Success: Stop command test passes

- [x] 232. Write CLI integration tests for configuration file loading
  - _Leverage:_ Config file testing
  - _Requirements:_ 5
  - _Prompt:_ Role: CLI test engineer | Task: Test --config option loads configuration from YAML file | Restrictions: Create test config, verify values used | Success: Config file test passes

- [x] 233. Write CLI integration tests for invalid configuration handling
  - _Leverage:_ Error handling testing
  - _Requirements:_ 5
  - _Prompt:_ Role: CLI test engineer | Task: Test server fails fast with clear error on invalid config | Restrictions: Use invalid config, verify error message | Success: Invalid config test passes

### 11. Integration Testing

- [x] 234. Write test for full PSK-TLS handshake with valid key
  - _Leverage:_ End-to-end TLS testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Integration test engineer | Task: Test complete PSK-TLS handshake with valid identity and key | Restrictions: Use real TLS client, verify successful handshake | Success: Valid handshake integration test passes

- [x] 235. Write test for handshake failure with wrong key
  - _Leverage:_ Negative TLS testing
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Integration test engineer | Task: Test handshake fails when client uses wrong PSK key | Restrictions: Verify appropriate TLS alert, handshake rejection | Success: Wrong key test passes

- [x] 236. Write test for handshake with each supported cipher suite
  - _Leverage:_ Cipher suite compatibility testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Integration test engineer | Task: Test handshake succeeds with each configured cipher suite | Restrictions: Test default, legacy, NULL ciphers separately | Success: Cipher suite tests pass

- [x] 237. Write test for NULL cipher handshake (when enabled)
  - _Leverage:_ Unencrypted mode testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Integration test engineer | Task: Test NULL cipher handshake works when enabled | Restrictions: Enable NULL ciphers, verify warning logged | Success: NULL cipher test passes

- [x] 238. Write test for session creation on connection
  - _Leverage:_ Session lifecycle testing
  - _Requirements:_ 1, 4
  - _Prompt:_ Role: Integration test engineer | Task: Test session created after successful TLS connection | Restrictions: Verify session ID assigned, state correct | Success: Session creation test passes

- [x] 239. Write test for session timeout expiration
  - _Leverage:_ Timeout behavior testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Integration test engineer | Task: Test inactive session times out after configured period | Restrictions: Mock time or wait, verify session closed | Success: Session timeout test passes

- [x] 240. Write test for session state transitions during operation
  - _Leverage:_ State machine testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Integration test engineer | Task: Test session transitions through states during normal operation | Restrictions: Verify HANDSHAKING→CONNECTED→ACTIVE→CLOSED | Success: State transition test passes

- [x] 241. Write test for concurrent sessions
  - _Leverage:_ Concurrency testing
  - _Requirements:_ 1, 4
  - _Prompt:_ Role: Integration test engineer | Task: Test multiple concurrent client sessions handled correctly | Restrictions: Create multiple clients, verify isolation | Success: Concurrent sessions test passes

- [x] 242. Write test for connection interruption mid-session
  - _Leverage:_ Interruption testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Integration test engineer | Task: Test connection interruption detected and handled | Restrictions: Simulate disconnect, verify cleanup and event | Success: Interruption test passes

- [x] 243. Write test for PSK mismatch detection and alerting
  - _Leverage:_ Authentication error testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Integration test engineer | Task: Test PSK mismatch triggers event and appropriate handling | Restrictions: Use wrong key, verify event emitted | Success: PSK mismatch test passes

- [x] 244. Write test for handshake timeout handling
  - _Leverage:_ Timeout testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Integration test engineer | Task: Test handshake timeout handled with partial state logging | Restrictions: Simulate slow client, verify timeout behavior | Success: Handshake timeout test passes

- [x] 245. Write test for error rate threshold alerting
  - _Leverage:_ Rate monitoring testing
  - _Requirements:_ 8
  - _Prompt:_ Role: Integration test engineer | Task: Test high error rate triggers alert event | Restrictions: Generate multiple errors, verify threshold event | Success: Error rate test passes

- [x] 246. Write test for SELECT command processing
  - _Leverage:_ GP command testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Integration test engineer | Task: Test SELECT command sent via HTTP processed correctly | Restrictions: Use valid SELECT APDU, verify response | Success: SELECT command test passes

- [x] 247. Write test for INSTALL command processing
  - _Leverage:_ GP command testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Integration test engineer | Task: Test INSTALL command processed with appropriate response | Restrictions: Use valid INSTALL APDU, verify status word | Success: INSTALL command test passes

- [x] 248. Write test for DELETE command processing
  - _Leverage:_ GP command testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Integration test engineer | Task: Test DELETE command processed correctly | Restrictions: Use valid DELETE APDU, verify response | Success: DELETE command test passes

- [x] 249. Write test for GET STATUS command processing
  - _Leverage:_ GP command testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Integration test engineer | Task: Test GET STATUS returns card content information | Restrictions: Use valid GET STATUS APDU, verify data | Success: GET STATUS test passes

- [x] 250. Write test for full GP Admin HTTP exchange
  - _Leverage:_ End-to-end protocol testing
  - _Requirements:_ 2, 3
  - _Prompt:_ Role: Integration test engineer | Task: Test complete GP Admin HTTP request/response cycle | Restrictions: Send GP Admin HTTP request, verify response format | Success: Full HTTP exchange test passes

### 12. Documentation and Examples

- [x] 251. Create `examples/configs/server_config.yaml` with all options documented
  - _Leverage:_ Example-driven documentation
  - _Requirements:_ 5
  - _Prompt:_ Role: Documentation writer | Task: Create example server_config.yaml with all configuration options | Restrictions: Include comments explaining each option | Success: Complete config example created

- [x] 252. Create `examples/configs/psk_keys.yaml` with example keys
  - _Leverage:_ Configuration examples
  - _Requirements:_ 1, 5
  - _Prompt:_ Role: Documentation writer | Task: Create example psk_keys.yaml with sample PSK identities and keys | Restrictions: Use non-production keys, add warnings | Success: PSK keys example created

- [x] 253. Add comments explaining each configuration option
  - _Leverage:_ Inline documentation
  - _Requirements:_ 5
  - _Prompt:_ Role: Technical writer | Task: Add detailed comments to example configs explaining each option | Restrictions: Include types, defaults, valid ranges | Success: All options documented

- [x] 254. Add docstrings to all public classes and methods
  - _Leverage:_ API documentation
  - _Requirements:_ All
  - _Prompt:_ Role: API documenter | Task: Write comprehensive docstrings for all public interfaces | Restrictions: Follow Google/NumPy style, include examples | Success: All public APIs documented

- [x] 255. Create README in `cardlink/server/` explaining module usage
  - _Leverage:_ Module documentation
  - _Requirements:_ All
  - _Prompt:_ Role: Module documenter | Task: Write README explaining PSK-TLS server module architecture and usage | Restrictions: Include quick start, architecture overview | Success: Module README created

- [x] 256. Document event types and data schemas
  - _Leverage:_ Event API documentation
  - _Requirements:_ 7
  - _Prompt:_ Role: Event schema documenter | Task: Document all 11 event types with data field descriptions | Restrictions: Include examples, specify required fields | Success: Event documentation complete

## Task Dependencies

```
1 (Setup)
├── 2 (KeyStore)
├── 3 (EventEmitter)
├── 4 (TLSHandler) ← depends on 1, 2
├── 5 (SessionManager) ← depends on 3
├── 6 (ErrorHandler) ← depends on 3
├── 7 (HTTPHandler) ← depends on 8
├── 8 (GPCommandProcessor) ← depends on 3
└── 9 (AdminServer) ← depends on 2, 3, 4, 5, 6, 7, 8

10 (CLI) ← depends on 9
11 (Integration Tests) ← depends on all components
12 (Documentation) ← finalize after implementation
```

## Summary

| Task Group | Tasks | Completed | Pending | Description |
|------------|-------|-----------|---------|-------------|
| Task 1 | 12 | 12 | 0 | Project setup and configuration |
| Task 2 | 19 | 19 | 0 | Key store implementation |
| Task 3 | 14 | 14 | 0 | Event emitter implementation |
| Task 4 | 28 | 28 | 0 | TLS handler implementation |
| Task 5 | 27 | 27 | 0 | Session manager implementation |
| Task 6 | 26 | 26 | 0 | Error handler implementation |
| Task 7 | 26 | 26 | 0 | HTTP handler implementation |
| Task 8 | 22 | 22 | 0 | GP command processor implementation |
| Task 9 | 39 | 39 | 0 | Admin server implementation |
| Task 10 | 20 | 20 | 0 | CLI integration |
| Task 11 | 17 | 17 | 0 | Integration testing |
| Task 12 | 6 | 6 | 0 | Documentation and examples |

**Total: 12 task groups, 256 subtasks**
**Progress: 256 completed, 0 pending**

## Requirements Mapping

- **Requirement 1** (PSK-TLS): Tasks 1, 2, 4, 9, 10, 11
- **Requirement 2** (GP Admin HTTP): Tasks 7, 8, 9, 11
- **Requirement 3** (APDU Processing): Tasks 5, 7, 8, 9, 11
- **Requirement 4** (Session Management): Tasks 1, 5, 6, 7, 9, 10, 11
- **Requirement 5** (Configuration): Tasks 1, 2, 7, 9, 10, 12
- **Requirement 6** (Server Lifecycle): Tasks 9, 10, 11
- **Requirement 7** (Event Emission): Tasks 3, 4, 5, 6, 8, 9, 12
- **Requirement 8** (Error Handling): Tasks 1, 4, 5, 6, 9, 11

## Notes

- sslpsk3 library provides PSK-TLS support for Python ssl module
- NULL ciphers are for testing only and should never be enabled in production
- PSK keys must never be logged; only log identity strings
- Session timeout default is 300 seconds (5 minutes)
- TLS 1.2 is required for PSK cipher suites per SCP81 specification
- ThreadPoolExecutor provides concurrent connection handling
- Event emission enables real-time dashboard updates and metrics collection
