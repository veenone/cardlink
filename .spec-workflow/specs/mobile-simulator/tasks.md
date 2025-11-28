# Tasks Document: Mobile Simulator

## Task Overview

This document breaks down the Mobile Simulator implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Configuration

- [ ] 1. Create `gp_ota_tester/simulator/` package directory structure
  - _Leverage:_ Python package structure conventions
  - _Requirements:_ 8
  - _Prompt:_ Role: Python developer | Task: Create the gp_ota_tester/simulator/ package directory with __init__.py following Python package conventions | Restrictions: Use standard Python package layout with __init__.py, maintain consistent naming | Success: Directory structure created, importable as Python package

- [ ] 2. Create `__init__.py` with public API exports
  - _Leverage:_ Python module exports best practices
  - _Requirements:_ 8
  - _Prompt:_ Role: API designer | Task: Define public API exports in __init__.py exposing MobileSimulator, SimulatorConfig, and VirtualUICC classes | Restrictions: Only export public interfaces, keep implementation details private | Success: Clean public API, imports work correctly

- [ ] 3. Create `config.py` with SimulatorConfig and BehaviorConfig dataclasses
  - _Leverage:_ Python dataclasses for configuration
  - _Requirements:_ 8
  - _Prompt:_ Role: Configuration architect | Task: Implement SimulatorConfig and BehaviorConfig dataclasses with fields for connection, PSK, UICC, and behavior settings | Restrictions: Use Python dataclasses with type hints, provide sensible defaults | Success: Configuration classes defined, validated, documented

- [ ] 4. Create `models.py` with SessionResult, APDUExchange, SimulatorStats dataclasses
  - _Leverage:_ Domain modeling with dataclasses
  - _Requirements:_ 1, 2
  - _Prompt:_ Role: Data modeler | Task: Define SessionResult, APDUExchange, and SimulatorStats dataclasses to represent simulator domain models | Restrictions: Use immutable dataclasses where appropriate, include all required fields from requirements | Success: All domain models defined with proper types

- [ ] 5. Define ConnectionState enum (IDLE, CONNECTING, CONNECTED, EXCHANGING, CLOSING, ERROR, TIMEOUT)
  - _Leverage:_ Python Enum for type safety
  - _Requirements:_ 2
  - _Prompt:_ Role: State machine designer | Task: Create ConnectionState enum with states IDLE, CONNECTING, CONNECTED, EXCHANGING, CLOSING, ERROR, TIMEOUT | Restrictions: Use Python Enum, ensure states align with connection lifecycle | Success: ConnectionState enum defined, states documented

- [ ] 6. Add `sslpsk3` dependency to pyproject.toml
  - _Leverage:_ Python packaging standards
  - _Requirements:_ 1
  - _Prompt:_ Role: Dependency manager | Task: Add sslpsk3 library to pyproject.toml dependencies for PSK-TLS support | Restrictions: Specify compatible version range | Success: Dependency added, installation works

- [ ] 7. Create optional dependency group `[simulator]` for simulator-specific packages
  - _Leverage:_ Poetry/setuptools extras feature
  - _Requirements:_ 8
  - _Prompt:_ Role: Package architect | Task: Define [simulator] extra in pyproject.toml grouping simulator-specific dependencies | Restrictions: Include sslpsk3, asyncio extras in group | Success: Optional dependency group created, installable separately

### 2. PSK-TLS Client Implementation

- [ ] 8. Create `psk_tls_client.py` with PSKTLSClient class
  - _Leverage:_ TLS protocol knowledge
  - _Requirements:_ 1
  - _Prompt:_ Role: TLS implementer | Task: Create PSKTLSClient class managing PSK-TLS client connections | Restrictions: Use sslpsk3 library, support TLS 1.2 | Success: PSKTLSClient class created

- [ ] 9. Implement `__init__` with host, port, PSK identity/key parameters
  - _Leverage:_ Dependency injection
  - _Requirements:_ 1, 8
  - _Prompt:_ Role: Class designer | Task: Initialize PSKTLSClient with host, port, PSK credentials, and timeout | Restrictions: Store references, validate inputs | Success: Initialization works with all parameters

- [ ] 10. Implement `create_ssl_context()` method for client mode
  - _Leverage:_ Python ssl module
  - _Requirements:_ 1
  - _Prompt:_ Role: SSL context builder | Task: Create SSL context configured for PSK-TLS client mode | Restrictions: Use sslpsk3 for PSK support, set client mode | Success: SSL context created successfully

- [ ] 11. Configure PSK callback to provide identity and key
  - _Leverage:_ sslpsk3 library API
  - _Requirements:_ 1
  - _Prompt:_ Role: PSK configurator | Task: Register PSK callback that returns configured identity and key | Restrictions: Callback must return (identity, key) tuple | Success: PSK callback registered

- [ ] 12. Set allowed cipher suites (AES-128/256-CBC-SHA256)
  - _Leverage:_ SSL context cipher configuration
  - _Requirements:_ 1
  - _Prompt:_ Role: Cipher suite manager | Task: Configure SSL context with PSK cipher suites | Restrictions: Support TLS_PSK_WITH_AES_128_CBC_SHA256, TLS_PSK_WITH_AES_256_CBC_SHA384 | Success: Cipher suites configured

- [ ] 13. Implement async `connect()` method
  - _Leverage:_ asyncio socket operations
  - _Requirements:_ 1
  - _Prompt:_ Role: Connection implementer | Task: Implement async connect method establishing TLS-PSK connection | Restrictions: Use asyncio, handle timeouts | Success: Connection establishment works

- [ ] 14. Create TCP socket and wrap with SSL context
  - _Leverage:_ Socket and SSL wrapping
  - _Requirements:_ 1
  - _Prompt:_ Role: Socket implementer | Task: Create TCP socket and wrap with PSK SSL context | Restrictions: Handle socket errors appropriately | Success: Socket created and wrapped

- [ ] 15. Perform TLS handshake with configurable timeout
  - _Leverage:_ TLS handshake handling
  - _Requirements:_ 1
  - _Prompt:_ Role: Handshake implementer | Task: Execute TLS handshake with timeout from configuration | Restrictions: Set socket timeout, handle timeout exceptions | Success: Handshake with timeout control

- [ ] 16. Return TLSConnectionInfo with cipher suite and timing
  - _Leverage:_ Connection info extraction
  - _Requirements:_ 1
  - _Prompt:_ Role: Connection info builder | Task: Create TLSConnectionInfo dataclass with negotiated cipher and timing | Restrictions: Extract from SSL socket, populate all fields | Success: Complete connection info returned

- [ ] 17. Implement async `send(data: bytes)` method
  - _Leverage:_ Async socket writing
  - _Requirements:_ 1
  - _Prompt:_ Role: Socket writer | Task: Implement async send method writing data to TLS socket | Restrictions: Handle write errors, use asyncio | Success: Data sending works

- [ ] 18. Implement async `receive(max_bytes: int)` method
  - _Leverage:_ Async socket reading
  - _Requirements:_ 1
  - _Prompt:_ Role: Socket reader | Task: Implement async receive method reading from TLS socket | Restrictions: Handle partial reads, timeouts | Success: Data receiving works

- [ ] 19. Implement async `close()` method
  - _Leverage:_ Connection cleanup
  - _Requirements:_ 1
  - _Prompt:_ Role: Cleanup implementer | Task: Implement close method shutting down TLS connection gracefully | Restrictions: Send TLS close_notify, close socket | Success: Clean connection closure

- [ ] 20. Write unit tests for connection establishment
  - _Leverage:_ Connection testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test PSKTLSClient connects successfully to mock server | Restrictions: Use test fixtures, verify handshake | Success: Connection tests pass

- [ ] 21. Write unit tests for send/receive operations
  - _Leverage:_ I/O testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test send and receive work correctly over TLS | Restrictions: Use mock data, verify integrity | Success: Send/receive tests pass

- [ ] 22. Write unit tests for connection timeout handling
  - _Leverage:_ Timeout testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Test engineer | Task: Test connection timeout is handled correctly | Restrictions: Mock slow server, verify timeout exception | Success: Timeout tests pass

### 3. HTTP Admin Client Implementation

- [ ] 23. Create `http_client.py` with HTTPAdminClient class
  - _Leverage:_ HTTP protocol handling
  - _Requirements:_ 4
  - _Prompt:_ Role: HTTP protocol implementer | Task: Create HTTPAdminClient class implementing GP Admin HTTP protocol | Restrictions: Follow GP Amendment B specification | Success: HTTPAdminClient class created

- [ ] 24. Define GP Admin Content-Type constants
  - _Leverage:_ Protocol constants
  - _Requirements:_ 4
  - _Prompt:_ Role: Protocol constant definer | Task: Define constants for GP Admin request/response content types | Restrictions: Match exact GP specification strings | Success: Content-type constants defined

- [ ] 25. Initialize with PSKTLSClient reference
  - _Leverage:_ Client composition
  - _Requirements:_ 4
  - _Prompt:_ Role: Integration designer | Task: Initialize HTTPAdminClient with PSKTLSClient for TLS transport | Restrictions: Store reference, validate not None | Success: Initialization with TLS client works

- [ ] 26. Implement `build_request(body: bytes)` method
  - _Leverage:_ HTTP request construction
  - _Requirements:_ 4
  - _Prompt:_ Role: Request builder | Task: Build HTTP POST request with GP Admin headers | Restrictions: Include Content-Type, Accept, Content-Length | Success: Request building works

- [ ] 27. Implement async `initial_request()` method
  - _Leverage:_ Session initiation
  - _Requirements:_ 4
  - _Prompt:_ Role: Session initiator | Task: Send initial empty POST to /admin and receive first C-APDU | Restrictions: Handle empty body case, parse response | Success: Initial request works

- [ ] 28. Implement async `send_response(r_apdu: bytes)` method
  - _Leverage:_ APDU exchange
  - _Requirements:_ 4
  - _Prompt:_ Role: Exchange implementer | Task: Send R-APDU and receive next C-APDU or session end | Restrictions: Build POST with R-APDU body, parse response | Success: APDU exchange works

- [ ] 29. Implement `parse_response(response: bytes)` method
  - _Leverage:_ HTTP response parsing
  - _Requirements:_ 4
  - _Prompt:_ Role: Response parser | Task: Parse HTTP response into status code, headers, body | Restrictions: Handle chunked encoding, validate status | Success: Response parsing works

- [ ] 30. Handle 200 OK responses (extract C-APDU)
  - _Leverage:_ Response handling
  - _Requirements:_ 4
  - _Prompt:_ Role: Response handler | Task: Extract C-APDU from 200 OK response body | Restrictions: Validate Content-Type, extract bytes | Success: C-APDU extraction works

- [ ] 31. Handle 204 No Content responses (session complete)
  - _Leverage:_ Session termination
  - _Requirements:_ 4
  - _Prompt:_ Role: Session terminator | Task: Detect 204 No Content and signal session completion | Restrictions: Return None to indicate end | Success: Session completion detected

- [ ] 32. Handle 4xx/5xx error responses
  - _Leverage:_ Error handling
  - _Requirements:_ 4
  - _Prompt:_ Role: Error handler | Task: Handle HTTP error responses appropriately | Restrictions: Log error, raise exception with details | Success: Error responses handled

- [ ] 33. Write unit tests for request building
  - _Leverage:_ Request construction testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test HTTP request building produces valid GP Admin requests | Restrictions: Verify headers, body format | Success: Request building tests pass

- [ ] 34. Write unit tests for response parsing
  - _Leverage:_ Response parsing testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test response parsing extracts correct data | Restrictions: Test various response formats | Success: Response parsing tests pass

- [ ] 35. Write unit tests for session completion detection
  - _Leverage:_ Session lifecycle testing
  - _Requirements:_ 4
  - _Prompt:_ Role: Test engineer | Task: Test 204 response correctly signals session end | Restrictions: Verify None returned | Success: Session completion tests pass

### 4. Virtual UICC Implementation

- [ ] 36. Create `virtual_uicc.py` with VirtualUICC class
  - _Leverage:_ UICC simulation knowledge
  - _Requirements:_ 5
  - _Prompt:_ Role: UICC simulator | Task: Create VirtualUICC class simulating UICC card behavior | Restrictions: Follow ISO 7816-4 for APDU format | Success: VirtualUICC class created

- [ ] 37. Create UICCProfile dataclass for card configuration
  - _Leverage:_ Profile configuration
  - _Requirements:_ 5, 8
  - _Prompt:_ Role: Profile designer | Task: Create UICCProfile dataclass with ICCID, IMSI, AIDs, applets | Restrictions: Provide sensible defaults, support applet list | Success: UICCProfile defined

- [ ] 38. Initialize with UICCProfile
  - _Leverage:_ Profile-based initialization
  - _Requirements:_ 5
  - _Prompt:_ Role: Initialization implementer | Task: Initialize VirtualUICC with profile configuration | Restrictions: Store profile, initialize state | Success: Initialization works

- [ ] 39. Implement APDU parsing (CLA, INS, P1, P2, Lc, Data, Le)
  - _Leverage:_ ISO 7816-4 APDU format
  - _Requirements:_ 5
  - _Prompt:_ Role: APDU parser | Task: Parse APDU bytes into components | Restrictions: Handle case 1-4 APDUs, validate structure | Success: APDU parsing works

- [ ] 40. Implement `process_apdu(apdu: bytes)` routing method
  - _Leverage:_ Command routing pattern
  - _Requirements:_ 5
  - _Prompt:_ Role: Command router | Task: Route APDU to appropriate handler based on INS | Restrictions: Lookup handler, invoke, return R-APDU | Success: APDU routing works

- [ ] 41. Implement SELECT command handler (INS=A4)
  - _Leverage:_ GP SELECT command
  - _Requirements:_ 5
  - _Prompt:_ Role: SELECT implementer | Task: Handle SELECT command for application selection | Restrictions: Parse AID, update selected state, return FCI | Success: SELECT handling works

- [ ] 42. Implement GET STATUS command handler (INS=F2)
  - _Leverage:_ GP GET STATUS command
  - _Requirements:_ 5
  - _Prompt:_ Role: GET STATUS implementer | Task: Handle GET STATUS returning card content info | Restrictions: Support scope parameter, return TLV data | Success: GET STATUS handling works

- [ ] 43. Implement GET DATA command handler (INS=CA)
  - _Leverage:_ GP GET DATA command
  - _Requirements:_ 5
  - _Prompt:_ Role: GET DATA implementer | Task: Handle GET DATA returning data objects | Restrictions: Support common tags (9F7F, etc.) | Success: GET DATA handling works

- [ ] 44. Implement INITIALIZE UPDATE handler (INS=50)
  - _Leverage:_ GP secure channel
  - _Requirements:_ 5
  - _Prompt:_ Role: INIT UPDATE implementer | Task: Handle INITIALIZE UPDATE for secure channel | Restrictions: Generate host challenge response | Success: INIT UPDATE handling works

- [ ] 45. Implement default handler for unsupported commands (SW 6D00)
  - _Leverage:_ Error response generation
  - _Requirements:_ 5, 6
  - _Prompt:_ Role: Default handler | Task: Return 6D00 for unknown INS codes | Restrictions: Log unsupported command | Success: Default handler works

- [ ] 46. Implement status word generation
  - _Leverage:_ Status word knowledge
  - _Requirements:_ 6
  - _Prompt:_ Role: Status word generator | Task: Generate appropriate SW for various conditions | Restrictions: Support 9000, 61XX, 6CXX, 6A82, 6A86, 6982, 6985, 6D00 | Success: Status words generated correctly

- [ ] 47. Track selected application state
  - _Leverage:_ Application state management
  - _Requirements:_ 5
  - _Prompt:_ Role: State tracker | Task: Track currently selected AID and application state | Restrictions: Update on SELECT, clear on reset | Success: Application state tracked

- [ ] 48. Write unit tests for APDU parsing
  - _Leverage:_ Parsing testing
  - _Requirements:_ 5
  - _Prompt:_ Role: Test engineer | Task: Test APDU parsing with various formats | Restrictions: Test case 1-4 APDUs | Success: APDU parsing tests pass

- [ ] 49. Write unit tests for SELECT command
  - _Leverage:_ Command testing
  - _Requirements:_ 5
  - _Prompt:_ Role: Test engineer | Task: Test SELECT command handling | Restrictions: Test valid and invalid AIDs | Success: SELECT tests pass

- [ ] 50. Write unit tests for GET STATUS command
  - _Leverage:_ Command testing
  - _Requirements:_ 5
  - _Prompt:_ Role: Test engineer | Task: Test GET STATUS returns correct data | Restrictions: Test different scope values | Success: GET STATUS tests pass

- [ ] 51. Write unit tests for status word generation
  - _Leverage:_ Status testing
  - _Requirements:_ 6
  - _Prompt:_ Role: Test engineer | Task: Test status words generated for various conditions | Restrictions: Verify correct SW for each scenario | Success: Status word tests pass

### 5. Behavior Controller Implementation

- [ ] 52. Create `behavior.py` with BehaviorController class
  - _Leverage:_ Behavior pattern
  - _Requirements:_ 7
  - _Prompt:_ Role: Behavior architect | Task: Create BehaviorController managing simulation modes | Restrictions: Support normal, error, timeout modes | Success: BehaviorController class created

- [ ] 53. Implement BehaviorConfig dataclass
  - _Leverage:_ Configuration pattern
  - _Requirements:_ 7, 8
  - _Prompt:_ Role: Config designer | Task: Create BehaviorConfig with mode, error rate, timeout probability | Restrictions: Provide defaults, validate ranges | Success: BehaviorConfig defined

- [ ] 54. Implement `should_inject_error()` method
  - _Leverage:_ Probabilistic injection
  - _Requirements:_ 7
  - _Prompt:_ Role: Error injector | Task: Determine if error should be injected based on rate | Restrictions: Use random with configured probability | Success: Error injection decision works

- [ ] 55. Implement `get_error_code()` method
  - _Leverage:_ Error code selection
  - _Requirements:_ 7
  - _Prompt:_ Role: Error code selector | Task: Return random error SW from configured list | Restrictions: Support configurable error codes | Success: Error code selection works

- [ ] 56. Implement `should_timeout()` method
  - _Leverage:_ Probabilistic timeout
  - _Requirements:_ 7
  - _Prompt:_ Role: Timeout injector | Task: Determine if timeout should be simulated | Restrictions: Use random with configured probability | Success: Timeout decision works

- [ ] 57. Implement `get_timeout_delay()` method
  - _Leverage:_ Delay calculation
  - _Requirements:_ 7
  - _Prompt:_ Role: Delay calculator | Task: Return delay duration for timeout simulation | Restrictions: Use configured range (min/max) | Success: Timeout delay works

- [ ] 58. Implement `get_response_delay()` method
  - _Leverage:_ Normal delay
  - _Requirements:_ 7
  - _Prompt:_ Role: Response delay | Task: Return normal response delay | Restrictions: Use configured response_delay_ms | Success: Response delay works

- [ ] 59. Write unit tests for error injection
  - _Leverage:_ Injection testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test error injection at configured rate | Restrictions: Use statistical validation | Success: Error injection tests pass

- [ ] 60. Write unit tests for timeout simulation
  - _Leverage:_ Timeout testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test timeout simulation at configured probability | Restrictions: Verify delay ranges | Success: Timeout simulation tests pass

### 6. Mobile Simulator Main Class

- [ ] 61. Create `client.py` with MobileSimulator class
  - _Leverage:_ Orchestrator pattern
  - _Requirements:_ 1, 2, 4, 5
  - _Prompt:_ Role: Simulator architect | Task: Create MobileSimulator orchestrating all components | Restrictions: Manage lifecycle, coordinate components | Success: MobileSimulator class created

- [ ] 62. Initialize with SimulatorConfig
  - _Leverage:_ Configuration injection
  - _Requirements:_ 8
  - _Prompt:_ Role: Initialization designer | Task: Initialize simulator with configuration | Restrictions: Create all sub-components | Success: Initialization works

- [ ] 63. Create PSKTLSClient instance
  - _Leverage:_ Component composition
  - _Requirements:_ 1
  - _Prompt:_ Role: Component builder | Task: Instantiate PSKTLSClient with config | Restrictions: Pass host, port, PSK credentials | Success: TLS client created

- [ ] 64. Create HTTPAdminClient instance
  - _Leverage:_ Component composition
  - _Requirements:_ 4
  - _Prompt:_ Role: Component builder | Task: Instantiate HTTPAdminClient with TLS client | Restrictions: Pass TLS client reference | Success: HTTP client created

- [ ] 65. Create VirtualUICC instance
  - _Leverage:_ Component composition
  - _Requirements:_ 5
  - _Prompt:_ Role: Component builder | Task: Instantiate VirtualUICC with UICC profile | Restrictions: Use profile from config | Success: Virtual UICC created

- [ ] 66. Create BehaviorController instance
  - _Leverage:_ Component composition
  - _Requirements:_ 7
  - _Prompt:_ Role: Component builder | Task: Instantiate BehaviorController with behavior config | Restrictions: Use behavior settings from config | Success: Behavior controller created

- [ ] 67. Implement state property returning ConnectionState
  - _Leverage:_ State accessor
  - _Requirements:_ 2
  - _Prompt:_ Role: State accessor | Task: Implement property returning current connection state | Restrictions: Return ConnectionState enum | Success: State property works

- [ ] 68. Implement async `connect()` method with retry logic
  - _Leverage:_ Retry pattern
  - _Requirements:_ 1, 3
  - _Prompt:_ Role: Connection implementer | Task: Implement connect with retry on failure | Restrictions: Use exponential backoff, max retries | Success: Connect with retry works

- [ ] 69. Implement state transitions during connection
  - _Leverage:_ State machine
  - _Requirements:_ 2
  - _Prompt:_ Role: State manager | Task: Transition states IDLE→CONNECTING→CONNECTED | Restrictions: Handle ERROR, TIMEOUT states | Success: State transitions work

- [ ] 70. Implement async `run_session()` method
  - _Leverage:_ Session orchestration
  - _Requirements:_ 4, 5
  - _Prompt:_ Role: Session runner | Task: Run complete APDU exchange session | Restrictions: Loop until 204, collect results | Success: Session execution works

- [ ] 71. Send initial request and receive first C-APDU
  - _Leverage:_ Session initiation
  - _Requirements:_ 4
  - _Prompt:_ Role: Session initiator | Task: Send initial POST, receive first command | Restrictions: Transition to EXCHANGING state | Success: Session starts correctly

- [ ] 72. Process C-APDUs through VirtualUICC
  - _Leverage:_ APDU processing
  - _Requirements:_ 5
  - _Prompt:_ Role: APDU processor | Task: Pass C-APDUs to VirtualUICC, get R-APDUs | Restrictions: Apply behavior modifications | Success: APDU processing works

- [ ] 73. Apply behavior modifications (errors, delays)
  - _Leverage:_ Behavior application
  - _Requirements:_ 7
  - _Prompt:_ Role: Behavior applier | Task: Check behavior controller, inject errors/delays | Restrictions: Replace response if error, add delay if timeout | Success: Behavior modifications applied

- [ ] 74. Send R-APDUs and receive next C-APDUs
  - _Leverage:_ Exchange loop
  - _Requirements:_ 4
  - _Prompt:_ Role: Exchange implementer | Task: Send R-APDU, receive next C-APDU | Restrictions: Handle 204 for session end | Success: APDU exchange works

- [ ] 75. Collect APDUExchange records
  - _Leverage:_ Exchange tracking
  - _Requirements:_ 10
  - _Prompt:_ Role: Exchange recorder | Task: Create APDUExchange for each exchange | Restrictions: Record command, response, timing | Success: Exchanges recorded

- [ ] 76. Return SessionResult on completion
  - _Leverage:_ Result generation
  - _Requirements:_ 10
  - _Prompt:_ Role: Result builder | Task: Build SessionResult with all exchange data | Restrictions: Include success, count, final SW | Success: Session result returned

- [ ] 77. Implement async `disconnect()` method
  - _Leverage:_ Disconnection handling
  - _Requirements:_ 1, 2
  - _Prompt:_ Role: Disconnect implementer | Task: Close TLS connection gracefully | Restrictions: Transition to CLOSING→IDLE | Success: Disconnect works

- [ ] 78. Implement `get_statistics()` method
  - _Leverage:_ Statistics collection
  - _Requirements:_ 10
  - _Prompt:_ Role: Statistics provider | Task: Return SimulatorStats with all metrics | Restrictions: Calculate averages, collect counts | Success: Statistics provided

- [ ] 79. Write unit tests for connection with retry
  - _Leverage:_ Retry testing
  - _Requirements:_ 1, 3
  - _Prompt:_ Role: Test engineer | Task: Test connection retries on failure | Restrictions: Mock failures, verify retry count | Success: Retry tests pass

- [ ] 80. Write unit tests for session execution
  - _Leverage:_ Session testing
  - _Requirements:_ 4, 5
  - _Prompt:_ Role: Test engineer | Task: Test complete session runs successfully | Restrictions: Use mock server, verify exchanges | Success: Session tests pass

- [ ] 81. Write unit tests for behavior application
  - _Leverage:_ Behavior testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Test engineer | Task: Test error injection and delays applied | Restrictions: Configure behaviors, verify application | Success: Behavior tests pass

### 7. CLI Implementation

- [ ] 82. Create `gp_ota_tester/cli/simulator.py` with Click commands
  - _Leverage:_ Click CLI framework
  - _Requirements:_ 9
  - _Prompt:_ Role: CLI developer | Task: Create Click command group for simulator CLI | Restrictions: Use Click decorators, follow CLI conventions | Success: Simulator CLI module created

- [ ] 83. Implement `run` command
  - _Leverage:_ Click command pattern
  - _Requirements:_ 9
  - _Prompt:_ Role: CLI command implementer | Task: Implement 'gp-simulator run' command | Restrictions: Initialize simulator, run session | Success: Run command works

- [ ] 84. Add `--server HOST:PORT` option
  - _Leverage:_ Click options
  - _Requirements:_ 8, 9
  - _Prompt:_ Role: CLI option designer | Task: Add --server option for target server | Restrictions: Parse host:port format, validate | Success: Server option works

- [ ] 85. Add `--psk-identity` and `--psk-key` options
  - _Leverage:_ Credential options
  - _Requirements:_ 8, 9
  - _Prompt:_ Role: Credential option implementer | Task: Add PSK identity and key options | Restrictions: Key in hex format | Success: PSK options work

- [ ] 86. Add `--config FILE` option for YAML configuration
  - _Leverage:_ Configuration file support
  - _Requirements:_ 8, 9
  - _Prompt:_ Role: Config option implementer | Task: Add --config option for YAML file | Restrictions: Validate file exists, parse YAML | Success: Config file option works

- [ ] 87. Add `--mode` option (normal, error, timeout)
  - _Leverage:_ Mode selection
  - _Requirements:_ 7, 9
  - _Prompt:_ Role: Mode option implementer | Task: Add --mode option for behavior mode | Restrictions: Validate choices | Success: Mode option works

- [ ] 88. Add `--error-rate` option
  - _Leverage:_ Error configuration
  - _Requirements:_ 7, 9
  - _Prompt:_ Role: Error option implementer | Task: Add --error-rate option (0.0-1.0) | Restrictions: Validate range | Success: Error rate option works

- [ ] 89. Add `--count` and `--parallel` options for multiple instances
  - _Leverage:_ Multi-instance support
  - _Requirements:_ 9
  - _Prompt:_ Role: Instance option implementer | Task: Add --count and --parallel for multiple simulators | Restrictions: Create N instances, run parallel if flag | Success: Multi-instance options work

- [ ] 90. Add `--loop` and `--interval` options for continuous mode
  - _Leverage:_ Continuous execution
  - _Requirements:_ 9
  - _Prompt:_ Role: Loop option implementer | Task: Add --loop and --interval for continuous runs | Restrictions: Loop with configurable interval | Success: Continuous mode options work

- [ ] 91. Implement `status` command
  - _Leverage:_ Status reporting
  - _Requirements:_ 9
  - _Prompt:_ Role: Status command implementer | Task: Implement status command showing simulator state | Restrictions: Display connection status, statistics | Success: Status command works

- [ ] 92. Implement `config generate` command
  - _Leverage:_ Config generation
  - _Requirements:_ 8, 9
  - _Prompt:_ Role: Config generator | Task: Generate sample YAML configuration file | Restrictions: Include all options with comments | Success: Config generation works

- [ ] 93. Write CLI integration tests for `gp-simulator run`
  - _Leverage:_ CLI testing
  - _Requirements:_ 9
  - _Prompt:_ Role: CLI test engineer | Task: Test run command with various options | Restrictions: Use Click testing utilities | Success: Run command tests pass

- [ ] 94. Write CLI integration tests for configuration loading
  - _Leverage:_ Config testing
  - _Requirements:_ 8
  - _Prompt:_ Role: CLI test engineer | Task: Test --config loads YAML correctly | Restrictions: Create test configs, verify values | Success: Config loading tests pass

### 8. Integration Testing

- [ ] 95. Write test for full PSK-TLS connection to server
  - _Leverage:_ End-to-end testing
  - _Requirements:_ 1
  - _Prompt:_ Role: Integration test engineer | Task: Test simulator connects to running PSK-TLS server | Restrictions: Use test server fixture | Success: Connection integration test passes

- [ ] 96. Write test for complete GP Admin session
  - _Leverage:_ Session testing
  - _Requirements:_ 4, 5
  - _Prompt:_ Role: Integration test engineer | Task: Test complete session with APDU exchanges | Restrictions: Verify all exchanges complete | Success: Session integration test passes

- [ ] 97. Write test for error injection mode
  - _Leverage:_ Error mode testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Integration test engineer | Task: Test error injection affects server behavior | Restrictions: Configure error mode, verify handling | Success: Error mode test passes

- [ ] 98. Write test for timeout simulation
  - _Leverage:_ Timeout testing
  - _Requirements:_ 7
  - _Prompt:_ Role: Integration test engineer | Task: Test timeout simulation triggers server timeout | Restrictions: Configure timeout mode, verify behavior | Success: Timeout simulation test passes

- [ ] 99. Write test for connection retry
  - _Leverage:_ Retry testing
  - _Requirements:_ 3
  - _Prompt:_ Role: Integration test engineer | Task: Test retry logic with intermittent failures | Restrictions: Mock network issues, verify retries | Success: Retry integration test passes

- [ ] 100. Write test for multiple concurrent simulators
  - _Leverage:_ Concurrency testing
  - _Requirements:_ 9
  - _Prompt:_ Role: Integration test engineer | Task: Test multiple simulators against server | Restrictions: Run N instances, verify isolation | Success: Concurrent simulator test passes

- [ ] 101. Create pytest fixtures for simulator
  - _Leverage:_ Pytest fixtures
  - _Requirements:_ 10
  - _Prompt:_ Role: Fixture developer | Task: Create simulator and connected_simulator fixtures | Restrictions: Clean up resources after test | Success: Fixtures work correctly

- [ ] 102. Create example tests using fixtures
  - _Leverage:_ Example test code
  - _Requirements:_ 10
  - _Prompt:_ Role: Example developer | Task: Write example tests demonstrating fixture usage | Restrictions: Include basic and advanced examples | Success: Example tests documented

### 9. Documentation

- [ ] 103. Create `examples/configs/simulator_config.yaml` with documented options
  - _Leverage:_ Example configuration
  - _Requirements:_ 8
  - _Prompt:_ Role: Documentation writer | Task: Create example simulator config with comments | Restrictions: Document all options | Success: Example config created

- [ ] 104. Add docstrings to all public classes and methods
  - _Leverage:_ API documentation
  - _Requirements:_ All
  - _Prompt:_ Role: API documenter | Task: Write docstrings for all public interfaces | Restrictions: Follow Google/NumPy style | Success: All public APIs documented

- [ ] 105. Create README in `gp_ota_tester/simulator/` explaining module usage
  - _Leverage:_ Module documentation
  - _Requirements:_ All
  - _Prompt:_ Role: Module documenter | Task: Write README explaining simulator architecture and usage | Restrictions: Include quick start, examples | Success: Module README created

## Task Dependencies

```
1 (Setup)
├── 2 (PSK-TLS Client) ← depends on 1
├── 3 (HTTP Admin Client) ← depends on 2
├── 4 (Virtual UICC) ← depends on 1
├── 5 (Behavior Controller) ← depends on 1
└── 6 (Mobile Simulator) ← depends on 2, 3, 4, 5

7 (CLI) ← depends on 6
8 (Integration Tests) ← depends on all components
9 (Documentation) ← finalize after implementation
```

## Summary

| Task Group | Tasks | Completed | Pending | Description |
|------------|-------|-----------|---------|-------------|
| Task 1 | 7 | 0 | 7 | Project setup and configuration |
| Task 2 | 15 | 0 | 15 | PSK-TLS client implementation |
| Task 3 | 13 | 0 | 13 | HTTP Admin client implementation |
| Task 4 | 16 | 0 | 16 | Virtual UICC implementation |
| Task 5 | 9 | 0 | 9 | Behavior controller implementation |
| Task 6 | 21 | 0 | 21 | Mobile simulator main class |
| Task 7 | 13 | 0 | 13 | CLI implementation |
| Task 8 | 8 | 0 | 8 | Integration testing |
| Task 9 | 3 | 0 | 3 | Documentation |

**Total: 9 task groups, 105 subtasks**
**Progress: 0 completed, 105 pending**

## Requirements Mapping

- **Requirement 1** (PSK-TLS Connection): Tasks 1, 2, 6, 8
- **Requirement 2** (State Management): Tasks 1, 6
- **Requirement 3** (Retry Logic): Tasks 6, 8
- **Requirement 4** (HTTP Admin): Tasks 3, 6, 8
- **Requirement 5** (Virtual UICC): Tasks 4, 6, 8
- **Requirement 6** (Response Generation): Tasks 4
- **Requirement 7** (Simulation Modes): Tasks 5, 6, 7, 8
- **Requirement 8** (Configuration): Tasks 1, 4, 5, 7, 9
- **Requirement 9** (CLI Interface): Tasks 7, 8
- **Requirement 10** (Test Integration): Tasks 6, 8

## Notes

- sslpsk3 library provides PSK-TLS support for Python ssl module
- Asyncio used for non-blocking I/O operations
- Virtual UICC follows ISO 7816-4 APDU format
- Behavior modes enable testing various UICC scenarios
- pytest fixtures enable easy integration testing
