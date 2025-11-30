# Tasks Document: Mobile Simulator

## Task Overview

This document breaks down the Mobile Simulator implementation into actionable development tasks organized by component and functionality. The Mobile Simulator is a critical testing tool that simulates mobile phone behavior for GlobalPlatform OTA testing via PSK-TLS connections.

## Tasks

### 1. Project Setup and Configuration

- [x] 1.1. Create `src/cardlink/simulator/` package directory with `__init__.py`, `config.py`, `models.py`
  - File: `src/cardlink/simulator/__init__.py`, `src/cardlink/simulator/config.py`, `src/cardlink/simulator/models.py`
  - Purpose: Establish module foundation for mobile simulator component with proper package structure
  - _Leverage: Standard Python package layout with __init__.py exports
  - _Requirements: Code Architecture and Modularity
  - _Prompt: Role: Python Developer specializing in package architecture | Task: Create the simulator module structure with proper __init__.py exports and core configuration/model files | Restrictions: Follow existing package patterns in cardlink, maintain clean imports | Success: Module imports correctly, files exist with proper organization

- [x] 1.2. Implement public API exports in `__init__.py` exposing MobileSimulator, SimulatorConfig, VirtualUICC classes
  - File: `src/cardlink/simulator/__init__.py`
  - Purpose: Define clean public API surface for simulator module consumers
  - _Leverage: Python __all__ exports for explicit API definition
  - _Requirements: API Design and Usability
  - _Prompt: Role: API Design Specialist | Task: Create __init__.py with __all__ exports exposing only public classes: MobileSimulator, SimulatorConfig, VirtualUICC, SessionResult, SimulatorStats | Restrictions: Hide internal implementation classes, provide clean imports | Success: Users can import core classes directly from cardlink.simulator

- [x] 1.3. Implement SimulatorConfig and BehaviorConfig dataclasses with fields for connection, PSK, UICC, and behavior settings
  - File: `src/cardlink/simulator/config.py`
  - Purpose: Provide strongly-typed configuration with validation for all simulator parameters
  - _Leverage: Python dataclasses with type hints, default values, field validators
  - _Requirements: 8 (Configuration)
  - _Prompt: Role: Configuration Engineer | Task: Implement SimulatorConfig and BehaviorConfig dataclasses with fields for server host/port, PSK identity/key, UICC profile, timeouts, retry counts, behavior mode, error rates, and timeout probabilities | Restrictions: Use dataclasses, provide sensible defaults, add validation for ports (1-65535), timeouts (>0), probabilities (0.0-1.0) | Success: Config objects can be created programmatically or from YAML, all fields have proper types and defaults

- [x] 1.4. Implement SessionResult, APDUExchange, SimulatorStats dataclasses for domain models
  - File: `src/cardlink/simulator/models.py`
  - Purpose: Define immutable data transfer objects for session results and statistics
  - _Leverage: Python dataclasses with frozen=True for immutability
  - _Requirements: Domain Modeling
  - _Prompt: Role: Domain Modeling Expert | Task: Create SessionResult dataclass with success flag, APDU count, final status word, exchanges list, error messages; APDUExchange with command/response bytes and timing; SimulatorStats with session counts, averages, success rates | Restrictions: Use frozen dataclasses for immutability, include timestamp fields, use Optional for nullable fields | Success: Domain objects are immutable, serialize to dict/JSON cleanly, contain all necessary session data

- [x] 1.5. Define ConnectionState enum (IDLE, CONNECTING, CONNECTED, EXCHANGING, CLOSING, ERROR, TIMEOUT) and BehaviorMode enum
  - File: `src/cardlink/simulator/models.py`
  - Purpose: Provide type-safe state machine states and behavior mode enumeration
  - _Leverage: Python Enum with string values for serialization
  - _Requirements: State Management
  - _Prompt: Role: State Machine Designer | Task: Create ConnectionState enum with values: IDLE, CONNECTING, CONNECTED, EXCHANGING, CLOSING, ERROR, TIMEOUT; BehaviorMode enum with NORMAL, ERROR_INJECTION, TIMEOUT_SIMULATION, MIXED | Restrictions: Use Python Enum, assign string values matching names for JSON serialization | Success: Enums used for state tracking, can be compared and serialized to strings

- [x] 1.6. Add sslpsk3 dependency to pyproject.toml for PSK-TLS support
  - File: `pyproject.toml`
  - Purpose: Enable PSK-TLS client functionality via sslpsk3 library
  - _Leverage: sslpsk3 library wrapping OpenSSL PSK-TLS support
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Dependency Manager | Task: Add sslpsk3>=1.0.0 to dependencies in pyproject.toml | Restrictions: Use compatible version, document purpose in inline comment | Success: sslpsk3 can be imported, PSK-TLS connections work

- [x] 1.7. Create optional dependency group `[simulator]` in pyproject.toml for simulator-specific packages
  - File: `pyproject.toml`
  - Purpose: Allow optional installation of simulator dependencies for users who don't need this component
  - _Leverage: Poetry/setuptools extras for optional dependency groups
  - _Requirements: Package Management
  - _Prompt: Role: Package Engineer | Task: Create [tool.poetry.extras] or [project.optional-dependencies] section with simulator group containing sslpsk3 and any simulator-specific testing dependencies | Restrictions: Use project's dependency management format, document installation command | Success: Users can install with pip install -e ".[simulator]"

### 2. PSK-TLS Client Implementation

- [x] 2.1. Create PSKTLSClient class with initialization accepting host, port, PSK identity/key, and timeout parameters
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Initialize PSK-TLS client with connection parameters and credentials
  - _Leverage: Python dataclasses for initialization parameters
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: TLS Client Developer | Task: Create PSKTLSClient class with __init__ accepting host: str, port: int, psk_identity: bytes, psk_key: bytes, timeout: float=30.0; store as instance variables | Restrictions: Validate port 1-65535, timeout > 0, PSK key non-empty | Success: Client can be instantiated with valid parameters, raises ValueError for invalid input

- [x] 2.2. Implement create_ssl_context() method configuring SSL context for PSK-TLS client mode
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Create properly configured SSL context for PSK-TLS client connections
  - _Leverage: sslpsk3.wrap_socket for PSK-TLS, ssl.SSLContext for configuration
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: SSL Configuration Expert | Task: Implement create_ssl_context() returning configured SSL context with TLS 1.2, client mode, PSK support enabled | Restrictions: Use ssl.PROTOCOL_TLSv1_2, disable compression, verify mode CERT_NONE (PSK auth replaces certs) | Success: Context created successfully, supports PSK authentication

- [x] 2.3. Configure PSK callback returning identity and key, set allowed cipher suites (AES-128/256-CBC-SHA256)
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Configure PSK credentials and restrict cipher suites to secure PSK options
  - _Leverage: sslpsk3 PSK callback mechanism, ssl cipher suite configuration
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Cryptography Engineer | Task: In create_ssl_context, configure PSK callback lambda returning (self.psk_identity, self.psk_key); set cipher suites to "PSK-AES128-CBC-SHA256:PSK-AES256-CBC-SHA256" | Restrictions: Only allow PSK cipher suites, ensure strong encryption (AES-128/256) | Success: PSK callback provides credentials, only PSK ciphers allowed

- [x] 2.4. Implement async connect() method creating TCP socket and wrapping with SSL context
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Establish TCP connection and upgrade to PSK-TLS with configured context
  - _Leverage: asyncio.open_connection for async TCP, sslpsk3.wrap_socket for PSK-TLS
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Async Network Engineer | Task: Implement async connect() creating TCP socket to (self.host, self.port) with timeout, wrapping with SSL context from create_ssl_context() | Restrictions: Use asyncio.wait_for for timeout, handle OSError and socket.timeout exceptions | Success: TCP connection established and upgraded to PSK-TLS, timeout raises asyncio.TimeoutError

- [x] 2.5. Perform TLS handshake with configurable timeout, return TLSConnectionInfo with cipher suite and timing
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Complete TLS handshake and capture connection details for diagnostics
  - _Leverage: ssl.SSLSocket.do_handshake, ssl.SSLSocket.cipher for connection info
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: TLS Protocol Expert | Task: In connect(), perform TLS handshake with timeout, measure handshake time; return TLSConnectionInfo dataclass with cipher_suite, protocol_version, handshake_time_ms | Restrictions: Use time.perf_counter for precise timing, handle SSL errors gracefully | Success: Handshake completes successfully, connection info captured, handshake failures raise clear exceptions

- [x] 2.6. Implement async send(data: bytes) method for writing data to TLS socket
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Send data over established PSK-TLS connection asynchronously
  - _Leverage: asyncio StreamWriter.write and drain for async sending
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Async I/O Developer | Task: Implement async send(data: bytes) using writer.write(data) and await writer.drain() to ensure data sent | Restrictions: Raise ConnectionError if not connected, handle BrokenPipeError and ConnectionResetError | Success: Data sent successfully over TLS, errors handled gracefully

- [x] 2.7. Implement async receive(max_bytes: int) method for reading from TLS socket with timeout
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Receive data from PSK-TLS connection with timeout protection
  - _Leverage: asyncio StreamReader.read with asyncio.wait_for for timeout
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Async I/O Developer | Task: Implement async receive(max_bytes: int, timeout: Optional[float] = None) using reader.read(max_bytes) wrapped with asyncio.wait_for for timeout | Restrictions: Use self.timeout as default, raise asyncio.TimeoutError on timeout, return empty bytes on EOF | Success: Data received successfully with timeout protection, EOF and timeout handled

- [x] 2.8. Implement async close() method shutting down TLS connection gracefully with close_notify
  - File: `src/cardlink/simulator/psk_tls_client.py`
  - Purpose: Cleanly close PSK-TLS connection with proper TLS close_notify alert
  - _Leverage: ssl.SSLSocket.unwrap for graceful TLS closure, socket.close
  - _Requirements: 1 (PSK-TLS Connection)
  - _Prompt: Role: Connection Lifecycle Manager | Task: Implement async close() sending TLS close_notify alert via writer.close() and await writer.wait_closed(), setting internal state to disconnected | Restrictions: Ignore errors during close (connection may already be broken), ensure idempotent (safe to call multiple times) | Success: Connection closed cleanly, resources released, no exceptions on subsequent close() calls

- [x] 2.9. Write unit tests for connection establishment, send/receive operations, and timeout handling
  - File: `tests/simulator/test_psk_tls_client.py`
  - Purpose: Verify PSK-TLS client functionality with mocked connections
  - _Leverage: pytest, pytest-asyncio, unittest.mock for async mocking
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: Test Engineer | Task: Write pytest tests for: successful connection, connection timeout, send/receive data, receive timeout, connection failure, close idempotency | Restrictions: Use pytest-asyncio for async tests, mock socket connections, verify state transitions | Success: All PSK-TLS client scenarios tested, edge cases covered

### 3. HTTP Admin Client Implementation

- [x] 3.1. Create HTTPAdminClient class with initialization accepting PSKTLSClient reference
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Initialize HTTP Admin client that uses PSK-TLS for transport
  - _Leverage: Composition pattern with PSKTLSClient for transport layer
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Protocol Layer Developer | Task: Create HTTPAdminClient class with __init__ accepting psk_client: PSKTLSClient, storing reference for HTTP over TLS communication | Restrictions: Don't manage PSK-TLS lifecycle (caller's responsibility), just use for send/receive | Success: Client initialized with PSK-TLS transport reference

- [x] 3.2. Define GP Admin Content-Type constants (request/response content types per specification)
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Define standard HTTP headers for GP Admin protocol compliance
  - _Leverage: GP Amendment B HTTP Admin specification section 4.1.2
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Protocol Standards Expert | Task: Define class constants: CONTENT_TYPE_REQUEST = "application/vnd.globalplatform.card-content-mgt-request", CONTENT_TYPE_RESPONSE = "application/vnd.globalplatform.card-content-mgt-response" | Restrictions: Use exact MIME types from GP Amendment B spec | Success: Constants defined, used in all requests/responses

- [x] 3.3. Implement build_request(body: bytes) method creating HTTP POST request with GP Admin headers
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Build compliant HTTP POST request for GP Admin protocol
  - _Leverage: HTTP 1.1 request format, Content-Type and Content-Length headers
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: HTTP Message Builder | Task: Implement build_request(body: bytes, path: str = "/admin") returning bytes of HTTP POST request with headers: Content-Type (request MIME), Content-Length, and empty body for initial request or R-APDU for subsequent | Restrictions: Use HTTP/1.1 format, include required headers, append CRLF line endings | Success: Valid HTTP POST request built, parses correctly by HTTP servers

- [x] 3.4. Implement async initial_request() method sending empty POST to /admin and receiving first C-APDU
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Initiate admin session and receive first command from server
  - _Leverage: HTTP POST with empty body to /admin endpoint per GP spec
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Session Initialization Developer | Task: Implement async initial_request() building empty POST via build_request(b""), sending via psk_client.send(), receiving response via psk_client.receive(), parsing with parse_response(), returning C-APDU bytes | Restrictions: Must handle 200 OK with C-APDU or error responses | Success: Initial request sent, first C-APDU received and returned

- [x] 3.5. Implement async send_response(r_apdu: bytes) method sending R-APDU and receiving next C-APDU or session end
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Send response APDU and receive next command in exchange loop
  - _Leverage: HTTP POST with R-APDU as body, parse response for next C-APDU or 204
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: APDU Exchange Developer | Task: Implement async send_response(r_apdu: bytes) building POST with r_apdu as body, sending, receiving response; return Optional[bytes] with C-APDU if 200 OK, None if 204 No Content (session end) | Restrictions: Handle both continuation (200) and completion (204) responses | Success: R-APDU sent, next C-APDU or None returned based on server response

- [x] 3.6. Implement parse_response(response: bytes) method parsing HTTP response into status, headers, body
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Parse HTTP response to extract status code and body data
  - _Leverage: HTTP response format parsing (status line + headers + body)
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: HTTP Parser Developer | Task: Implement parse_response(response: bytes) splitting on CRLF CRLF to separate headers and body; parse status line for code; return HTTPResponse dataclass with status_code: int, headers: dict, body: bytes | Restrictions: Handle HTTP/1.1 and HTTP/1.0 responses, case-insensitive header names | Success: Responses parsed correctly, status and body extracted

- [x] 3.7. Handle 200 OK responses extracting C-APDU, 204 No Content for session completion, 4xx/5xx for errors
  - File: `src/cardlink/simulator/http_admin_client.py`
  - Purpose: Implement proper response code handling per GP Admin specification
  - _Leverage: HTTP status code semantics for session lifecycle
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Protocol State Machine Developer | Task: In send_response and initial_request, check status_code: 200 → extract and return C-APDU from body; 204 → return None (session end); 4xx/5xx → raise ProtocolError with status and body | Restrictions: Validate Content-Type on 200 responses matches CONTENT_TYPE_RESPONSE | Success: All response codes handled correctly, session lifecycle managed

- [x] 3.8. Write unit tests for request building, response parsing, and session completion detection
  - File: `tests/simulator/test_http_admin_client.py`
  - Purpose: Verify HTTP Admin protocol implementation correctness
  - _Leverage: pytest with mocked PSK-TLS client
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: Protocol Test Engineer | Task: Write tests for: request format validation, initial request handling, APDU exchange, 204 session end detection, error response handling, Content-Type validation | Restrictions: Mock PSKTLSClient, verify exact HTTP format, test all response codes | Success: All HTTP Admin protocol scenarios tested

### 4. Virtual UICC Implementation

- [x] 4.1. Create VirtualUICC class and UICCProfile dataclass for card configuration (ICCID, IMSI, AIDs, applets)
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Define virtual UICC with configurable card profile
  - _Leverage: Dataclass for immutable card profile configuration
  - _Requirements: 5 (Virtual UICC), 8 (Configuration)
  - _Prompt: Role: Card Simulation Architect | Task: Create UICCProfile dataclass with iccid: str, imsi: str, issuer_security_domain_aid: bytes, supplementary_security_domains: List[bytes], applets: Dict[bytes, str]; VirtualUICC class with __init__(profile: UICCProfile) | Restrictions: Validate ICCID/IMSI format, AIDs as bytes, provide default ISD AID (A000000003000000) | Success: Profile configured, VirtualUICC instantiated with profile

- [x] 4.2. Initialize VirtualUICC with UICCProfile, implement APDU parsing (CLA, INS, P1, P2, Lc, Data, Le) for case 1-4 APDUs
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Parse incoming C-APDUs according to ISO 7816-4 structure
  - _Leverage: ISO 7816-4 APDU case 1-4 format specifications
  - _Requirements: 5 (Virtual UICC)
  - _Prompt: Role: APDU Protocol Expert | Task: Implement parse_apdu(apdu: bytes) parsing CLA (byte 0), INS (byte 1), P1 (byte 2), P2 (byte 3); determine case based on length; extract Lc, data, Le for cases 2-4; return APDUCommand dataclass | Restrictions: Handle all 4 APDU cases, validate minimum length (4 bytes), support extended length APDUs if needed | Success: All APDU cases parsed correctly, invalid APDUs raise ValueError

- [x] 4.3. Implement process_apdu(apdu: bytes) routing method dispatching to handlers based on INS byte
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Route APDU commands to appropriate handlers based on instruction byte
  - _Leverage: Command pattern with handler method dispatch
  - _Requirements: 5 (Virtual UICC)
  - _Prompt: Role: Command Router Developer | Task: Implement process_apdu(apdu: bytes) parsing APDU, extracting INS byte, dispatching to handler methods (handle_select for 0xA4, handle_get_status for 0xF2, etc.), returning R-APDU bytes (data + SW1 + SW2) | Restrictions: Use dict mapping INS → handler method, call default_handler for unknown INS | Success: Commands routed correctly, R-APDUs returned

- [x] 4.4. Implement SELECT command handler (INS=A4) for application selection with AID parsing and FCI response
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Handle SELECT FILE/APPLICATION commands for navigation
  - _Leverage: ISO 7816-4 SELECT command, GP FCI template
  - _Requirements: 5 (Virtual UICC), 6 (Response Generation)
  - _Prompt: Role: Card Command Developer | Task: Implement handle_select(cmd: APDUCommand) checking P1 (selection control: 0x04 for AID), extracting AID from data, checking if AID in profile.applets or matches ISD; update self.selected_application; return FCI template (tag 6F with AID tag 84) + 9000, or 6A82 if not found | Restrictions: Support SELECT by AID (P1=04), return proper FCI structure | Success: SELECT by AID works, application state updated, FCI returned

- [x] 4.5. Implement GET STATUS command handler (INS=F2) returning card content info with scope parameter support
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Return card lifecycle and application status information
  - _Leverage: GlobalPlatform GET STATUS command with TLV response
  - _Requirements: 5 (Virtual UICC), 6 (Response Generation)
  - _Prompt: Role: GP Command Developer | Task: Implement handle_get_status(cmd: APDUCommand) checking P1 for scope (0x80=ISD, 0x40=Apps), building TLV response with tag E3 containing AID (tag 4F), lifecycle state (tag 9F70, value 07=SELECTABLE), and privileges; return data + 9000 | Restrictions: Support ISD and application listing, use correct GP tag structure | Success: GET STATUS returns ISD and app info, proper TLV format

- [x] 4.6. Implement GET DATA command handler (INS=CA) returning data objects for common tags (9F7F, etc.)
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Return card data objects like CPLC, Card Data, Key Info
  - _Leverage: GlobalPlatform GET DATA with tag-based object retrieval
  - _Requirements: 5 (Virtual UICC), 6 (Response Generation)
  - _Prompt: Role: Card Data Provider | Task: Implement handle_get_data(cmd: APDUCommand) extracting requested tag from P1P2 (e.g., 0x9F7F for CPLC, 0x0066 for Card Data); return appropriate test data for known tags or 6A88 (referenced data not found) for unknown | Restrictions: Support common tags: 9F7F (CPLC), 0066 (Card Data), 00E0 (Key Info Template) | Success: GET DATA returns test data for known tags, 6A88 for unknown

- [x] 4.7. Implement INITIALIZE UPDATE handler (INS=50) for secure channel initiation with host challenge response
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Simulate secure channel initialization (SCP02/SCP03)
  - _Leverage: GlobalPlatform INITIALIZE UPDATE command structure
  - _Requirements: 5 (Virtual UICC), 6 (Response Generation)
  - _Prompt: Role: Secure Channel Developer | Task: Implement handle_initialize_update(cmd: APDUCommand) extracting host challenge (8 bytes from data), generating card challenge (8 bytes random), card cryptogram (8 bytes random); return key diversification data (10 bytes) + key version (2 bytes) + SCP ID (2 bytes, 0x0202 for SCP02) + sequence counter (2 bytes) + card challenge + card cryptogram + 9000 | Restrictions: Don't implement real crypto (test mode), return valid structure | Success: INITIALIZE UPDATE returns proper response structure

- [x] 4.8. Implement default handler for unsupported commands returning SW 6D00 (INS not supported)
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Handle unknown commands gracefully with standard error
  - _Leverage: ISO 7816-4 status word 6D00
  - _Requirements: 5 (Virtual UICC)
  - _Prompt: Role: Error Handling Developer | Task: Implement default_handler(cmd: APDUCommand) returning empty data + 6D00 status word for any unrecognized INS byte | Restrictions: Return proper SW bytes (0x6D, 0x00) | Success: Unknown commands return 6D00

- [x] 4.9. Implement status word generation supporting 9000, 61XX, 6CXX, 6A82, 6A86, 6982, 6985, 6D00
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Generate proper ISO 7816-4 status words for responses
  - _Leverage: ISO 7816-4 status word definitions
  - _Requirements: 6 (Response Generation)
  - _Prompt: Role: Status Word Expert | Task: Create StatusWord enum or constants for common SWs: 9000 (success), 61XX (more data available), 6CXX (wrong Le), 6A82 (file not found), 6A86 (incorrect P1P2), 6982 (security status not satisfied), 6985 (conditions not satisfied), 6D00 (INS not supported); implement build_response(data: bytes, sw1: int, sw2: int) → bytes | Restrictions: Use correct 2-byte SW format (SW1, SW2) | Success: All status words generated correctly

- [x] 4.10. Track selected application state, update on SELECT, clear on reset
  - File: `src/cardlink/simulator/virtual_uicc.py`
  - Purpose: Maintain card session state for context-dependent commands
  - _Leverage: State management pattern
  - _Requirements: 5 (Virtual UICC)
  - _Prompt: Role: State Management Developer | Task: Add self.selected_application: Optional[bytes] attribute; update in handle_select on successful selection; implement reset() method clearing state; use selected app context in other commands if needed | Restrictions: Initialize as None, update only on successful SELECT | Success: Application state tracked correctly, reset() clears state

- [x] 4.11. Write unit tests for APDU parsing, SELECT/GET STATUS commands, and status word generation
  - File: `tests/simulator/test_virtual_uicc.py`
  - Purpose: Verify virtual UICC command handling correctness
  - _Leverage: pytest with test APDU vectors
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: Card Testing Engineer | Task: Write 10+ tests covering: APDU case 1-4 parsing, SELECT by AID (success and failure), GET STATUS for ISD and apps, GET DATA for known/unknown tags, INITIALIZE UPDATE, unsupported command (6D00), status word generation | Restrictions: Use hex APDU test vectors, verify exact response bytes | Success: All UICC commands tested, edge cases covered (10 tests implemented)

### 5. Behavior Controller Implementation

- [x] 5.1. Create BehaviorController class and BehaviorConfig dataclass with mode, error rate, timeout probability fields
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Define behavior configuration and controller for test mode management
  - _Leverage: Dataclass for config, controller class for behavior logic
  - _Requirements: 7 (Simulation Modes), 8 (Configuration)
  - _Prompt: Role: Behavior Configuration Architect | Task: Create BehaviorConfig dataclass with mode: BehaviorMode, error_injection_rate: float (0.0-1.0), timeout_probability: float (0.0-1.0), error_codes: List[int] (default common errors), timeout_delay_range_ms: Tuple[int, int], response_delay_ms: int; BehaviorController class with __init__(config: BehaviorConfig) | Restrictions: Validate probabilities 0.0-1.0, provide defaults (normal mode, 0.1 error rate, common SW errors) | Success: Config validated, controller instantiated

- [x] 5.2. Implement should_inject_error() method using random with configured probability to decide error injection
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Probabilistically decide whether to inject an error
  - _Leverage: random.random() for probability check
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Probabilistic Behavior Developer | Task: Implement should_inject_error() → bool checking if config.mode includes error injection; if yes, return random.random() < config.error_injection_rate; else False | Restrictions: Use random.random() for reproducibility with seed, respect mode setting | Success: Errors injected at configured rate in error modes, never in normal mode

- [x] 5.3. Implement get_error_code() method returning random error SW from configured list (6A82, 6985, 6D00, etc.)
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Select which error status word to inject
  - _Leverage: random.choice for error selection
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Error Selection Developer | Task: Implement get_error_code() → Tuple[int, int] using random.choice(config.error_codes) to select error SW, converting to (SW1, SW2) tuple | Restrictions: Default error_codes should include realistic card errors: 6A82, 6A86, 6985, 6982, 6D00 | Success: Random errors selected from configured list

- [x] 5.4. Implement should_timeout() method using random with configured probability for timeout simulation
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Probabilistically decide whether to simulate a timeout
  - _Leverage: random.random() for probability check
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Timeout Simulation Developer | Task: Implement should_timeout() → bool checking if config.mode includes timeout simulation; if yes, return random.random() < config.timeout_probability; else False | Restrictions: Only apply in timeout modes, use configured probability | Success: Timeouts triggered at configured rate in timeout modes

- [x] 5.5. Implement get_timeout_delay() method returning delay duration within configured range (min/max milliseconds)
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Determine how long to delay for timeout simulation
  - _Leverage: random.uniform for delay selection
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Delay Calculation Developer | Task: Implement get_timeout_delay() → float returning random.uniform(config.timeout_delay_range_ms[0], config.timeout_delay_range_ms[1]) / 1000.0 for seconds | Restrictions: Convert ms to seconds for asyncio.sleep, use configured min/max range | Success: Random delays generated within configured range

- [x] 5.6. Implement get_response_delay() method returning normal response delay from configuration
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Add realistic response delay even in normal mode
  - _Leverage: Configured constant delay
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Timing Simulation Developer | Task: Implement get_response_delay() → float returning config.response_delay_ms / 1000.0 | Restrictions: Return configured delay, allow 0 for instant responses | Success: Consistent response delays applied

- [x] 5.7. Implement async apply_delay() and maybe_inject_behavior() orchestration methods
  - File: `src/cardlink/simulator/behavior.py`
  - Purpose: Orchestrate delay application and behavior modification
  - _Leverage: asyncio.sleep for delays
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Behavior Orchestration Developer | Task: Implement async apply_delay(delay_seconds: float) using await asyncio.sleep(delay_seconds); implement maybe_inject_behavior(normal_response: bytes) → bytes checking should_inject_error(), replacing with error SW if yes, else returning normal_response unchanged | Restrictions: Preserve command data, only modify status word on error injection | Success: Delays applied correctly, behaviors injected as configured

- [x] 5.8. Write unit tests for error injection at configured rate and timeout simulation with delay ranges
  - File: `tests/simulator/test_behavior.py`
  - Purpose: Verify behavior controller operates within configured parameters
  - _Leverage: pytest with statistical validation
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: Behavior Testing Engineer | Task: Write 11+ tests for: error injection rate accuracy (run 1000 times, verify ~10% for 0.1 rate), timeout probability, error code selection from list, delay range validation, mode respect (no errors in normal mode), response delay accuracy | Restrictions: Use large sample sizes for probability tests, allow statistical variance (±5%) | Success: All behavior scenarios tested, probabilities validated (11 tests implemented)

### 6. Mobile Simulator Main Class

- [x] 6.1. Create MobileSimulator class initialized with SimulatorConfig, creating all component instances
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Main orchestrator class coordinating all simulator components
  - _Leverage: Composition pattern with dependency injection via config
  - _Requirements: 1, 2, 8
  - _Prompt: Role: System Architect | Task: Create MobileSimulator class with __init__(config: SimulatorConfig) storing config, initializing state variables (state, session_count, total_apdus, etc.) but NOT creating components yet (lazy init in connect) | Restrictions: Store config reference, initialize statistics counters, set initial state to IDLE | Success: Simulator instantiated with config, ready to connect

- [x] 6.2. Create PSKTLSClient, HTTPAdminClient, VirtualUICC, and BehaviorController instances from configuration
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Instantiate all component dependencies with proper configuration
  - _Leverage: Factory pattern creating components from config
  - _Requirements: 1, 4, 5, 7, 8
  - _Prompt: Role: Component Factory Developer | Task: In connect() method (or separate _create_components()), instantiate PSKTLSClient with server host/port and PSK credentials from config; HTTPAdminClient with PSKTLSClient; VirtualUICC with config.uicc_profile; BehaviorController with config.behavior | Restrictions: Create components lazily on first connect, reuse if already created | Success: All components instantiated correctly from config

- [x] 6.3. Implement state property returning ConnectionState enum value
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Expose current simulator state for monitoring
  - _Leverage: Property pattern for read-only access
  - _Requirements: 2 (State Management)
  - _Prompt: Role: State Exposure Developer | Task: Implement @property state(self) → ConnectionState returning self._state; implement _set_state(new_state: ConnectionState) updating self._state with optional logging | Restrictions: Make state read-only externally, use private _set_state internally | Success: State accessible via .state property, transitions logged

- [x] 6.4. Implement async connect() method with retry logic using exponential backoff and max retry count
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Establish connection with retry for transient failures
  - _Leverage: Exponential backoff retry pattern
  - _Requirements: 1, 3 (Retry Logic)
  - _Prompt: Role: Retry Logic Developer | Task: Implement async connect() with retry loop (max config.max_retries attempts); on each attempt: set state CONNECTING, call psk_client.connect(), set state CONNECTED on success; on failure: if retryable (network error), sleep backoff_seconds = min(config.initial_backoff_seconds * (2 ** attempt), config.max_backoff_seconds), retry; if non-retryable (auth error), set ERROR state and raise immediately | Restrictions: Don't retry auth failures, use exponential backoff with cap, update state on each transition | Success: Connects successfully with retries, respects backoff, fails fast on auth errors

- [x] 6.5. Implement state transitions during connection (IDLE→CONNECTING→CONNECTED, handle ERROR/TIMEOUT)
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Maintain correct state machine transitions during connection lifecycle
  - _Leverage: State machine pattern with validation
  - _Requirements: 2 (State Management)
  - _Prompt: Role: State Machine Developer | Task: In connect(), transition IDLE → CONNECTING at start, CONNECTING → CONNECTED on success, CONNECTING → ERROR on unrecoverable failure, CONNECTING → TIMEOUT on asyncio.TimeoutError; validate transitions (e.g., can't connect from EXCHANGING state) | Restrictions: Enforce valid state transitions, log all transitions, raise StateError on invalid transitions | Success: State transitions follow correct flow, invalid transitions rejected

- [x] 6.6. Implement async run_session() method orchestrating complete APDU exchange session
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Execute complete admin session with APDU exchanges
  - _Leverage: Session orchestration pattern
  - _Requirements: 4, 5, 10
  - _Prompt: Role: Session Orchestration Developer | Task: Implement async run_session() → SessionResult requiring CONNECTED state; transition to EXCHANGING; call http_client.initial_request() to get first C-APDU; enter exchange loop processing APDUs until session ends; return SessionResult with success, APDU count, exchanges | Restrictions: Must be connected before running session, handle ProtocolError from HTTP client, ensure state cleanup | Success: Complete sessions execute successfully, SessionResult returned

- [x] 6.7. Send initial request and receive first C-APDU, transition to EXCHANGING state
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Initiate admin session and begin APDU exchange
  - _Leverage: HTTP Admin initial request
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Session Initialization Developer | Task: In run_session(), after state check, call c_apdu = await http_client.initial_request(); transition state to EXCHANGING; check if c_apdu is None (immediate 204), return early if so | Restrictions: Handle None C-APDU (empty session), transition state before loop | Success: Initial request sent, first C-APDU received, state EXCHANGING

- [x] 6.8. Loop: process C-APDUs through VirtualUICC, apply behavior modifications (errors, delays)
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Core APDU exchange loop with behavior application
  - _Leverage: While loop with behavioral modification
  - _Requirements: 5, 6, 7
  - _Prompt: Role: APDU Exchange Developer | Task: Implement exchange loop: while c_apdu is not None: 1) record exchange start time, 2) r_apdu = virtual_uicc.process_apdu(c_apdu), 3) if behavior.should_timeout(), apply delay and raise TimeoutError, 4) r_apdu = behavior.maybe_inject_behavior(r_apdu), 5) apply response delay, 6) record APDUExchange with timing | Restrictions: Apply behaviors before sending response, measure timing accurately, collect all exchanges | Success: APDUs processed correctly, behaviors applied, exchanges recorded

- [x] 6.9. Send R-APDUs and receive next C-APDUs, handle 204 No Content for session end
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Continue exchange loop until session completion
  - _Leverage: HTTP Admin response handling
  - _Requirements: 4 (HTTP Admin Protocol)
  - _Prompt: Role: Exchange Continuation Developer | Task: In loop, after processing R-APDU, call c_apdu = await http_client.send_response(r_apdu); if c_apdu is None (204 received), break loop (session complete); else continue with next iteration | Restrictions: Handle None return as session end, don't send after receiving 204 | Success: Exchange loop continues until 204, then exits cleanly

- [x] 6.10. Collect APDUExchange records for each exchange with command, response, timing
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Record all exchanges for session result and analysis
  - _Leverage: List collection with dataclass records
  - _Requirements: 10 (Test Integration)
  - _Prompt: Role: Data Collection Developer | Task: Create exchanges: List[APDUExchange] = []; in loop, append APDUExchange(c_apdu=c_apdu, r_apdu=r_apdu, processing_time_ms=(end_time - start_time) * 1000, injected_error=was_error_injected, injected_timeout=was_timeout) after each exchange | Restrictions: Use time.perf_counter for precise timing, record all exchanges including error-injected ones | Success: All exchanges recorded with accurate timing and behavior flags

- [x] 6.11. Return SessionResult on completion with success flag, APDU count, final status word, exchanges list
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Provide complete session outcome to caller
  - _Leverage: SessionResult dataclass
  - _Requirements: 10 (Test Integration)
  - _Prompt: Role: Result Builder Developer | Task: At end of run_session(), extract final_sw from last exchange.r_apdu[-2:]; return SessionResult(success=True, apdu_count=len(exchanges), final_status_word=final_sw, exchanges=exchanges, error_message=None, duration_ms=total_time); on exception, return SessionResult with success=False and error_message | Restrictions: Always return SessionResult even on failure, include all exchanges up to failure point | Success: SessionResult accurately reflects session outcome

- [x] 6.12. Implement async disconnect() method closing TLS connection with state transition (CLOSING→IDLE)
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Cleanly close connection and reset state
  - _Leverage: Connection lifecycle management
  - _Requirements: 1, 2
  - _Prompt: Role: Connection Lifecycle Developer | Task: Implement async disconnect() setting state to CLOSING, calling await psk_client.close(), setting state to IDLE; handle already-disconnected case (IDLE state); make idempotent | Restrictions: Allow disconnect from any state, ignore errors during close, always end in IDLE state | Success: Connection closed cleanly, state reset to IDLE, idempotent

- [x] 6.13. Implement async run_complete_session() method combining connect, run_session, disconnect
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Provide convenient all-in-one session execution
  - _Leverage: Convenience method pattern
  - _Requirements: 1, 2, 4
  - _Prompt: Role: Convenience API Developer | Task: Implement async run_complete_session() → SessionResult: await self.connect(), result = await self.run_session(), await self.disconnect(); return result; wrap in try/finally ensuring disconnect even on error | Restrictions: Guarantee cleanup (disconnect) via finally block, propagate exceptions after cleanup | Success: Complete session lifecycle managed, cleanup guaranteed

- [x] 6.14. Implement get_statistics() method returning SimulatorStats with session counts, averages, metrics
  - File: `src/cardlink/simulator/mobile_simulator.py`
  - Purpose: Provide session statistics for analysis and reporting
  - _Leverage: Statistics aggregation
  - _Requirements: 10 (Test Integration)
  - _Prompt: Role: Statistics Developer | Task: Track session_count, successful_sessions, failed_sessions, total_apdus, total_errors_injected, total_timeouts_injected across sessions; implement get_statistics() → SimulatorStats calculating averages (apdus_per_session, success_rate, error_rate, avg_session_duration_ms) | Restrictions: Update counters after each session, calculate averages safely (handle division by zero) | Success: Statistics accurately reflect session history

- [x] 6.15. Write unit tests for connection with retry, session execution, behavior application, and statistics
  - File: `tests/simulator/test_mobile_simulator.py`
  - Purpose: Verify main orchestrator functionality and integration
  - _Leverage: pytest-asyncio with mocked components
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: Integration Test Engineer | Task: Write tests for: successful connection, connection retry with backoff, connection failure after max retries, successful session execution, session with error injection, session with timeout, state transitions, statistics accuracy, complete session lifecycle, disconnect cleanup | Restrictions: Mock component dependencies, verify state transitions, test retry logic, validate statistics | Success: All orchestration scenarios tested, state machine verified

### 7. CLI Implementation

- [x] 7.1. Create `src/cardlink/cli/simulator.py` with Click command group for gp-simulator CLI
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Establish CLI entry point and command group structure
  - _Leverage: Click framework for CLI building
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: CLI Framework Developer | Task: Create cli() Click group decorated with @click.group(); add version option; implement main() entry point calling cli(); update pyproject.toml with console script entry gp-simulator = cardlink.cli.simulator:main | Restrictions: Use Click 8.x+ features, support --help globally | Success: gp-simulator command available, shows help

- [x] 7.2. Implement `run` command with --server, --psk-identity, --psk-key options for basic execution
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Provide basic run command with connection parameters
  - _Leverage: Click command and options decorators
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: CLI Command Developer | Task: Create @cli.command() run with options: --server (required, format host:port), --psk-identity (required), --psk-key (required, hex string); parse server into host/port, decode hex PSK key; create SimulatorConfig; run async simulation with asyncio.run() | Restrictions: Validate hex key format, parse host:port correctly, handle async execution | Success: gp-simulator run executes session with provided credentials

- [x] 7.3. Add --config FILE option for YAML configuration file loading with validation
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Support configuration file for complex setups
  - _Leverage: YAML parsing with pyyaml
  - _Requirements: 8 (Configuration)
  - _Prompt: Role: Configuration Loading Developer | Task: Add --config click.Path(exists=True) option to run command; if provided, load YAML with yaml.safe_load(); merge with CLI options (CLI overrides file); validate config structure | Restrictions: CLI options override file values, validate required fields, handle file not found gracefully | Success: Config files loaded, merged with CLI options correctly

- [x] 7.4. Add --mode option (normal, error, timeout) for behavior mode selection
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Allow behavior mode selection from CLI
  - _Leverage: Click choice option
  - _Requirements: 7 (Simulation Modes), 9 (CLI Interface)
  - _Prompt: Role: Behavior CLI Developer | Task: Add --mode click.Choice(['normal', 'error', 'timeout', 'mixed']) with default 'normal'; map to BehaviorMode enum when creating config | Restrictions: Use Click choice for validation, map strings to enum values | Success: Mode selection works, invalid modes rejected

- [x] 7.5. Add --error-rate and --timeout-probability options for behavior configuration
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Fine-tune probabilistic behavior parameters
  - _Leverage: Click float options with validation
  - _Requirements: 7 (Simulation Modes), 9 (CLI Interface)
  - _Prompt: Role: Behavior Parameter Developer | Task: Add --error-rate click.FloatRange(0.0, 1.0, clamp=True) with default 0.1; --timeout-probability click.FloatRange(0.0, 1.0, clamp=True) with default 0.05; apply to BehaviorConfig | Restrictions: Validate 0.0-1.0 range, clamp out-of-range values | Success: Probabilities configurable, validated correctly

- [x] 7.6. Add --count and --parallel options for running multiple simulator instances
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Support load testing with multiple concurrent sessions
  - _Leverage: asyncio.gather for parallel execution
  - _Requirements: 9 (CLI Interface), 10 (Test Integration)
  - _Prompt: Role: Concurrency Developer | Task: Add --count click.IntRange(min=1) default 1 for number of sessions; --parallel click.IntRange(min=1) default 1 for concurrent sessions; implement batch execution with asyncio.gather for parallel, sequential for serial | Restrictions: Respect --parallel limit, show progress for multiple sessions, collect all results | Success: Multiple sessions execute correctly, --parallel controls concurrency

- [x] 7.7. Add --loop and --interval options for continuous execution mode
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Enable continuous testing for endurance and monitoring
  - _Leverage: While loop with asyncio.sleep for interval
  - _Requirements: 9 (CLI Interface), 10 (Test Integration)
  - _Prompt: Role: Continuous Execution Developer | Task: Add --loop flag for continuous mode; --interval click.FloatRange(min=0.1) default 1.0 for seconds between sessions; implement while True loop with interval sleep, break on Ctrl+C | Restrictions: Handle KeyboardInterrupt gracefully, show iteration count, respect interval | Success: Continuous mode runs until stopped, respects interval

- [x] 7.8. Add --verbose flag for detailed output and --json flag for JSON output format
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Support different output formats for human and machine consumption
  - _Leverage: Click flags, JSON serialization
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: Output Formatting Developer | Task: Add --verbose flag showing detailed logs; --json flag outputting SessionResult as JSON; implement format_output(result: SessionResult, verbose: bool, json_format: bool) handling both formats | Restrictions: JSON must be valid and parseable, verbose shows APDU exchanges, default shows summary | Success: Both output formats work correctly

- [x] 7.9. Implement `test-connection` command for testing connectivity to PSK-TLS server
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Provide connection diagnostic command
  - _Leverage: PSKTLSClient standalone connection test
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: Diagnostic Command Developer | Task: Create @cli.command() test_connection with --server, --psk-identity, --psk-key options; create PSKTLSClient, attempt connect with timeout, report success/failure with connection info (cipher, handshake time) | Restrictions: Don't run full session, just test TLS handshake, show clear success/failure | Success: Connection test command works, shows diagnostic info

- [x] 7.10. Implement `config-generate` command creating sample YAML configuration with comments
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Help users create configuration files with documentation
  - _Leverage: YAML generation with comments
  - _Requirements: 8 (Configuration), 9 (CLI Interface)
  - _Prompt: Role: Config Generation Developer | Task: Create @cli.command() config_generate with --output click.Path() option; generate sample YAML with all options documented in comments; include examples for each mode; write to file or stdout | Restrictions: Include helpful comments explaining each option, provide sensible defaults, show examples | Success: Generated config is valid, well-documented, ready to use

- [x] 7.11. Implement output formatting with tables for session results and statistics
  - File: `src/cardlink/cli/simulator.py`
  - Purpose: Present results in readable table format
  - _Leverage: Rich library or simple ASCII tables
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: Output Presentation Developer | Task: Implement format_table(results: List[SessionResult]) creating ASCII table with columns: Session #, Success, APDUs, Final SW, Duration; format_statistics(stats: SimulatorStats) showing summary table | Restrictions: Use simple ASCII box drawing or Rich library, align columns, format numbers | Success: Tables render correctly, data aligned and readable

- [x] 7.12. Write CLI integration tests for run command and configuration loading
  - File: `tests/cli/test_simulator_cli.py`
  - Purpose: Verify CLI commands work correctly end-to-end
  - _Leverage: Click CliRunner for CLI testing
  - _Requirements: Testing and Quality Assurance
  - _Prompt: Role: CLI Testing Engineer | Task: Use Click CliRunner to test: run command with args, config file loading, mode selection, --verbose and --json output, test-connection command, config-generate command, error handling (missing args, invalid config) | Restrictions: Use CliRunner.invoke(), verify exit codes, check output strings, test error cases | Success: All CLI commands tested, inputs validated, outputs verified

### 8. Integration Testing

- [x] 8.1. Create pytest fixtures in tests/simulator/conftest.py for default_config, uicc_profile, behavior configurations
  - File: `tests/simulator/conftest.py`
  - Purpose: Provide reusable test fixtures for all simulator tests
  - _Leverage: pytest fixtures for test data
  - _Requirements: Testing Infrastructure
  - _Prompt: Role: Test Infrastructure Developer | Task: Create fixtures: default_config() returning SimulatorConfig with test server; default_uicc_profile() with test ICCID/IMSI/AIDs; behavior_configs() with normal/error/timeout/mixed configs; mock_psk_client() mocking PSKTLSClient | Restrictions: Use @pytest.fixture decorator, make fixtures reusable, provide realistic test data | Success: Fixtures available to all tests, reduce test boilerplate

- [x] 8.2. Write unit tests for VirtualUICC in test_virtual_uicc.py (10 tests) covering APDU parsing and command handlers
  - File: `tests/simulator/test_virtual_uicc.py`
  - Purpose: Thoroughly test virtual UICC command processing
  - _Leverage: pytest with hex APDU test vectors
  - _Requirements: 5 (Virtual UICC)
  - _Prompt: Role: UICC Test Engineer | Task: Write 10 tests: test_apdu_case_1_4_parsing, test_select_by_aid_success, test_select_by_aid_not_found, test_get_status_isd, test_get_status_apps, test_get_data_known_tag, test_get_data_unknown_tag, test_initialize_update, test_unsupported_command_6d00, test_status_word_generation | Restrictions: Use real APDU hex vectors, verify exact response bytes, test success and error paths | Success: 10 tests implemented and passing

- [x] 8.3. Write unit tests for BehaviorController in test_behavior.py (11 tests) covering error injection and timeout simulation
  - File: `tests/simulator/test_behavior.py`
  - Purpose: Verify behavior controller probabilistic operations
  - _Leverage: pytest with statistical validation
  - _Requirements: 7 (Simulation Modes)
  - _Prompt: Role: Behavior Test Engineer | Task: Write 11 tests: test_normal_mode_no_errors, test_error_injection_rate_10_percent (1000 iterations), test_error_injection_rate_50_percent, test_timeout_simulation_rate, test_error_code_selection_from_list, test_timeout_delay_range, test_response_delay, test_mixed_mode, test_zero_probability_no_injection, test_100_percent_always_inject, test_behavior_application_to_response | Restrictions: Use large samples (1000+) for probability tests, allow ±5% variance | Success: 11 tests implemented validating behavior logic

- [x] 8.4. Write unit tests for configuration in test_config.py (17 tests) covering validation and YAML loading
  - File: `tests/simulator/test_config.py`
  - Purpose: Ensure configuration validation and loading works correctly
  - _Leverage: pytest with valid and invalid configs
  - _Requirements: 8 (Configuration)
  - _Prompt: Role: Configuration Test Engineer | Task: Write 17 tests covering: valid config creation, invalid port validation, invalid timeout, invalid probability ranges, PSK key validation, YAML loading, YAML with missing fields, YAML with invalid types, config merging (file + CLI override), default value population, UICCProfile validation, BehaviorConfig validation | Restrictions: Test both programmatic and YAML config creation, verify all validations | Success: 17 tests implemented covering all config scenarios

- [x] 8.5. Write integration test for complete session lifecycle with APDU exchanges
  - File: `tests/simulator/test_integration.py`
  - Purpose: Test end-to-end session execution
  - _Leverage: pytest-asyncio with component integration
  - _Requirements: 1, 4, 5, 10
  - _Prompt: Role: Integration Test Engineer | Task: Write test_complete_session creating MobileSimulator, mocking server responses (initial request → SELECT → GET STATUS → 204), running full session, verifying all APDUs exchanged, SessionResult correct | Restrictions: Mock PSKTLSClient transport, use real VirtualUICC and HTTPAdminClient, verify complete exchange sequence | Success: Complete session test passes, all exchanges verified

- [x] 8.6. Write integration test for error injection mode verifying error responses
  - File: `tests/simulator/test_integration.py`
  - Purpose: Verify error injection behavior works in integrated scenario
  - _Leverage: pytest with error mode config
  - _Requirements: 7 (Simulation Modes), 10
  - _Prompt: Role: Error Injection Test Engineer | Task: Write test_error_injection_mode with BehaviorConfig(mode=ERROR_INJECTION, error_rate=1.0); run session; verify R-APDUs have error status words (not 9000); verify SessionResult indicates errors; check exchanges list shows injected errors | Restrictions: Use 100% error rate for deterministic test, verify error SWs in responses | Success: Error injection test passes, errors injected correctly

- [x] 8.7. Write integration test for timeout simulation verifying delays applied
  - File: `tests/simulator/test_integration.py`
  - Purpose: Verify timeout simulation with delays
  - _Leverage: pytest with timeout mode and timing measurements
  - _Requirements: 7 (Simulation Modes), 10
  - _Prompt: Role: Timeout Test Engineer | Task: Write test_timeout_simulation with BehaviorConfig(mode=TIMEOUT_SIMULATION, timeout_probability=1.0, timeout_delay_range_ms=(1000, 1000)); measure session duration; verify timeout delay applied (~1 second); verify SessionResult reflects timeout or delayed completion | Restrictions: Measure timing with time.perf_counter, allow timing variance (±100ms) | Success: Timeout simulation test passes, delays verified

- [x] 8.8. Write integration test for connection retry with exponential backoff
  - File: `tests/simulator/test_integration.py`
  - Purpose: Verify retry logic with backoff timing
  - _Leverage: pytest with mocked connection failures
  - _Requirements: 3 (Retry Logic), 10
  - _Prompt: Role: Retry Logic Test Engineer | Task: Write test_connection_retry mocking PSKTLSClient.connect() to fail twice then succeed; configure SimulatorConfig(max_retries=3, initial_backoff=0.1, max_backoff=1.0); measure retry timing; verify exponential backoff (0.1s, 0.2s delays); verify eventual success | Restrictions: Mock connection method, verify retry count, measure backoff delays | Success: Retry test passes, backoff timing verified

- [x] 8.9. Write integration test for multiple concurrent simulators verifying isolation
  - File: `tests/simulator/test_integration.py`
  - Purpose: Ensure concurrent simulators don't interfere
  - _Leverage: pytest-asyncio with asyncio.gather
  - _Requirements: 10 (Test Integration)
  - _Prompt: Role: Concurrency Test Engineer | Task: Write test_concurrent_simulators creating 10 MobileSimulator instances with independent configs; run all concurrently with asyncio.gather(); verify all complete successfully; verify session isolation (no shared state corruption) | Restrictions: Use separate configs for each simulator, verify all SessionResults, check for race conditions | Success: Concurrent execution test passes, no interference

- [x] 8.10. Write integration test for handshake failure handling (no retries for auth errors)
  - File: `tests/simulator/test_integration.py`
  - Purpose: Verify auth failures don't trigger retries
  - _Leverage: pytest with auth error mock
  - _Requirements: 3 (Retry Logic), 10
  - _Prompt: Role: Auth Failure Test Engineer | Task: Write test_handshake_failure mocking PSKTLSClient.connect() to raise SSL auth error; verify connect() fails immediately without retries; verify state transitions to ERROR; verify error message indicates auth failure | Restrictions: Mock SSL error, verify NO retry attempts made, check error state | Success: Auth failure test passes, no retries on auth errors

- [x] 8.11. Write integration test for statistics collection and accuracy
  - File: `tests/simulator/test_integration.py`
  - Purpose: Verify statistics tracking across multiple sessions
  - _Leverage: pytest with multiple session runs
  - _Requirements: 10 (Test Integration)
  - _Prompt: Role: Statistics Test Engineer | Task: Write test_statistics running simulator through 5 successful and 2 failed sessions; verify SimulatorStats shows correct: session_count=7, successful_sessions=5, failed_sessions=2, average APDUs, success_rate=71.4%, error counts | Restrictions: Run real sessions, verify all statistics fields, check calculations | Success: Statistics test passes, all metrics accurate

- [x] 8.12. Write integration test for parallel simulator execution
  - File: `tests/simulator/test_integration.py`
  - Purpose: Test CLI --parallel feature with real concurrent execution
  - _Leverage: pytest with simulated parallel runs
  - _Requirements: 9 (CLI Interface), 10 (Test Integration)
  - _Prompt: Role: Parallel Execution Test Engineer | Task: Write test_parallel_execution simulating --count 10 --parallel 3; run in batches of 3 concurrent sessions; verify all 10 complete; measure total time < 10 sequential sessions; verify results collected correctly | Restrictions: Use asyncio.gather with batching, verify parallelism benefit, check all results | Success: Parallel execution test passes, performance benefit verified

### 9. Documentation

- [x] 9.1. Create comprehensive user guide in docs/simulator-guide.md (7,500+ words) with installation, configuration, integration, scenarios, troubleshooting
  - File: `docs/simulator-guide.md`
  - Purpose: Provide complete user documentation for mobile simulator
  - _Leverage: Markdown with code examples and diagrams
  - _Requirements: All
  - _Prompt: Role: Technical Writer | Task: Create comprehensive guide with sections: Introduction, Installation (pip, from source), Quick Start (basic example), Configuration (all options documented), CLI Reference (all commands), Integration Guide (with PSK-TLS server), Testing Scenarios (normal, error, timeout, load testing), Troubleshooting (common issues), Advanced Topics (custom behaviors, CI/CD integration), API Reference (Python API usage) | Restrictions: 7500+ words, include code examples for each section, add troubleshooting section | Success: Guide created, all features documented (7500+ words)

- [x] 9.2. Create quick reference card in docs/simulator-quick-reference.md with commands, options, templates, workflow
  - File: `docs/simulator-quick-reference.md`
  - Purpose: Provide single-page quick reference for common operations
  - _Leverage: Markdown tables and lists
  - _Requirements: 9 (CLI Interface)
  - _Prompt: Role: Quick Reference Developer | Task: Create 1-2 page reference with: CLI command syntax table, common options table, example commands for typical scenarios, config file template, workflow diagrams (ASCII), common error codes and solutions | Restrictions: Keep concise (1-2 pages), use tables, provide copy-paste examples | Success: Quick reference created, covers common use cases

- [x] 9.3. Create examples guide in examples/simulator/README.md with workflows, customization patterns, CI/CD integration
  - File: `examples/simulator/README.md`
  - Purpose: Provide practical usage examples and patterns
  - _Leverage: Markdown with executable code examples
  - _Requirements: All
  - _Prompt: Role: Examples Developer | Task: Create examples guide with: Basic workflow example, Error injection workflow, Load testing example, Continuous monitoring example, CI/CD integration (GitHub Actions YAML), Custom behavior configuration, Python API usage examples, Multi-simulator coordination | Restrictions: Include complete runnable examples, explain each example, provide expected output | Success: Examples guide created with diverse scenarios

- [x] 9.4. Create example configurations: basic_config.yaml, error_injection_config.yaml, timeout_config.yaml, advanced_config.yaml
  - File: `examples/simulator/basic_config.yaml`, `examples/simulator/error_injection_config.yaml`, `examples/simulator/timeout_config.yaml`, `examples/simulator/advanced_config.yaml`
  - Purpose: Provide ready-to-use configuration templates
  - _Leverage: YAML with extensive inline comments
  - _Requirements: 8 (Configuration)
  - _Prompt: Role: Configuration Template Developer | Task: Create 4 YAML configs: 1) basic_config.yaml - minimal working config with comments, 2) error_injection_config.yaml - error mode with 20% error rate, 3) timeout_config.yaml - timeout mode with delay ranges, 4) advanced_config.yaml - all options demonstrated with comments explaining each | Restrictions: Include comments for every option, provide realistic values, make configs copy-paste ready | Success: 4 example configs created, well-documented

- [x] 9.5. Add comprehensive docstrings to all public classes and methods following Google/NumPy style
  - File: All source files in `src/cardlink/simulator/`
  - Purpose: Provide inline code documentation for developers
  - _Leverage: Python docstrings with type hints
  - _Requirements: Code Documentation
  - _Prompt: Role: Code Documentation Developer | Task: Add docstrings to all public classes and methods using Google or NumPy style with: one-line summary, detailed description, Args section with types, Returns section with type, Raises section for exceptions, Examples section for complex methods | Restrictions: Document all public APIs, use consistent style, include type information, add usage examples | Success: All public APIs documented, sphinx-compatible

- [x] 9.6. Create technical README in src/cardlink/simulator/README.md explaining architecture, API, usage
  - File: `src/cardlink/simulator/README.md`
  - Purpose: Provide developer-focused module documentation
  - _Leverage: Markdown with architecture diagrams
  - _Requirements: Architecture Documentation
  - _Prompt: Role: Technical Architect | Task: Create module README with: Architecture overview (component diagram), Component descriptions (PSKTLSClient, HTTPAdminClient, VirtualUICC, BehaviorController, MobileSimulator), API usage examples (Python code), State machine diagram (ASCII/Mermaid), Sequence diagram for session flow, Extension points for customization, Testing approach | Restrictions: Include diagrams, code examples, explain design decisions | Success: Technical README created, architecture documented

---

## Task Dependencies

```
Task 1 (Setup)
    └─> Task 2 (PSK-TLS Client)
            └─> Task 3 (HTTP Admin Client)
                    └─> Task 6 (Mobile Simulator)

Task 1 (Setup)
    └─> Task 4 (Virtual UICC)
            └─> Task 6 (Mobile Simulator)

Task 1 (Setup)
    └─> Task 5 (Behavior Controller)
            └─> Task 6 (Mobile Simulator)

Task 6 (Mobile Simulator)
    ├─> Task 7 (CLI)
    └─> Task 8 (Integration Tests)

Task 8 (Integration Tests) + All Components
    └─> Task 9 (Documentation)
```

## Summary

| Task Group | Tasks | Description | Status |
|------------|-------|-------------|--------|
| Task 1 | 1.1 - 1.7 | Project setup and configuration | ✅ Complete |
| Task 2 | 2.1 - 2.9 | PSK-TLS client implementation | ✅ Complete |
| Task 3 | 3.1 - 3.8 | HTTP Admin client implementation | ✅ Complete |
| Task 4 | 4.1 - 4.11 | Virtual UICC implementation | ✅ Complete |
| Task 5 | 5.1 - 5.8 | Behavior controller implementation | ✅ Complete |
| Task 6 | 6.1 - 6.15 | Mobile simulator main class | ✅ Complete |
| Task 7 | 7.1 - 7.12 | CLI implementation | ✅ Complete |
| Task 8 | 8.1 - 8.12 | Integration testing | ✅ Complete |
| Task 9 | 9.1 - 9.6 | Documentation | ✅ Complete |

**Total: 9 task groups, 88 subtasks (88 complete, 0 pending)**
