# Requirements Document: Mobile Simulator

## Introduction

The Mobile Simulator is a software component that simulates the behavior of a mobile phone with a UICC card initiating SCP81 (GlobalPlatform Amendment B) connections to the PSK-TLS Admin Server. This enables:

- Testing the PSK-TLS server without physical mobile hardware
- Automated integration and regression testing
- Development and debugging of server-side protocol handling
- Load testing with multiple simulated connections

This component is essential for the GP OTA Tester platform as it provides the ability to validate server functionality in isolation without requiring physical devices or network carriers.

## Alignment with Product Vision

This feature directly supports the GP OTA Tester's mission of comprehensive SCP81 compliance testing:

- **Hardware-free testing**: Enables server validation without physical UICC cards
- **Automated testing**: Supports CI/CD pipelines with scriptable test scenarios
- **Protocol transparency**: Full visibility into APDU exchanges and TLS handshakes
- **Scenario flexibility**: Supports normal operation, error injection, and timeout simulation
- **Local-first design**: Runs entirely on developer's machine without external dependencies

## Requirements

### Requirement 1: PSK-TLS Client Connection

**User Story:** As a tester, I want the simulator to establish PSK-TLS connections to the admin server, so that I can test server TLS handling without physical UICC hardware.

#### Acceptance Criteria

1. WHEN the simulator initiates a connection THEN it SHALL use TLS 1.2 with PSK cipher suites
2. WHEN configuring the simulator THEN it SHALL support the following PSK cipher suites:
   - TLS_PSK_WITH_AES_128_CBC_SHA256 (mandatory)
   - TLS_PSK_WITH_AES_256_CBC_SHA384
   - TLS_PSK_WITH_AES_128_CBC_SHA (legacy)
3. WHEN the PSK identity and key are configured THEN the simulator SHALL use them in the TLS handshake
4. WHEN the TLS handshake succeeds THEN the simulator SHALL transition to CONNECTED state
5. WHEN the TLS handshake fails THEN the simulator SHALL log the failure reason and retry if configured
6. IF the connection timeout is exceeded THEN the simulator SHALL close the connection and emit a timeout event

### Requirement 2: Connection State Management

**User Story:** As a developer, I want the simulator to manage connection lifecycle properly, so that I can track and debug connection behavior.

#### Acceptance Criteria

1. WHEN the simulator starts THEN it SHALL be in IDLE state
2. WHEN initiating a connection THEN the simulator SHALL transition to CONNECTING state
3. WHEN the TLS handshake completes THEN the simulator SHALL transition to CONNECTED state
4. WHEN HTTP exchanges begin THEN the simulator SHALL transition to EXCHANGING state
5. WHEN closing the connection THEN the simulator SHALL transition to CLOSING then IDLE state
6. IF an error occurs THEN the simulator SHALL transition to ERROR state with diagnostic information
7. IF a timeout occurs THEN the simulator SHALL transition to TIMEOUT state

### Requirement 3: Connection Retry Logic

**User Story:** As a tester, I want the simulator to retry failed connections, so that I can test server behavior under transient network conditions.

#### Acceptance Criteria

1. WHEN a connection attempt fails THEN the simulator SHALL retry according to configuration (default: 3 retries)
2. WHEN retrying THEN the simulator SHALL use exponential backoff (default: 1s, 2s, 4s)
3. WHEN a connection is refused or times out THEN the simulator SHALL retry
4. WHEN a PSK mismatch occurs THEN the simulator SHALL NOT retry (authentication failure)
5. WHEN all retries are exhausted THEN the simulator SHALL transition to ERROR state

### Requirement 4: HTTP Admin Protocol Client

**User Story:** As a tester, I want the simulator to implement the GP Amendment B HTTP Admin protocol, so that I can test server protocol handling.

#### Acceptance Criteria

1. WHEN connected THEN the simulator SHALL send HTTP/1.1 POST requests to /admin endpoint
2. WHEN sending a request THEN the Content-Type SHALL be application/vnd.globalplatform.card-content-mgt-response;version=1.0
3. WHEN sending a request THEN the Accept header SHALL be application/vnd.globalplatform.card-content-mgt;version=1.0
4. WHEN receiving a 200 OK response THEN the simulator SHALL extract the C-APDU from the body
5. WHEN receiving a 204 No Content response THEN the simulator SHALL consider the session complete
6. WHEN receiving 4xx/5xx responses THEN the simulator SHALL handle errors appropriately
7. WHEN the server returns chunked transfer encoding THEN the simulator SHALL handle it correctly

### Requirement 5: Virtual UICC Simulation

**User Story:** As a tester, I want the simulator to emulate UICC behavior, so that I can test server APDU command processing.

#### Acceptance Criteria

1. WHEN receiving a C-APDU THEN the virtual UICC SHALL parse and process it according to ISO 7816-4
2. WHEN receiving a SELECT command (INS=A4) THEN the virtual UICC SHALL select the specified application
3. WHEN receiving a GET STATUS command (INS=F2) THEN the virtual UICC SHALL return card status
4. WHEN receiving a supported GP command THEN the virtual UICC SHALL generate appropriate R-APDU
5. WHEN receiving an unsupported command THEN the virtual UICC SHALL return SW 6D00 (INS not supported)
6. WHEN processing commands THEN the virtual UICC SHALL track selected application state

### Requirement 6: Response Generation

**User Story:** As a tester, I want the simulator to generate realistic UICC responses, so that server-side response handling can be validated.

#### Acceptance Criteria

1. WHEN a command succeeds THEN the virtual UICC SHALL return SW 9000
2. WHEN more data is available THEN the virtual UICC SHALL return SW 61XX
3. WHEN the Le field is incorrect THEN the virtual UICC SHALL return SW 6CXX
4. WHEN a file is not found THEN the virtual UICC SHALL return SW 6A82
5. WHEN P1P2 is incorrect THEN the virtual UICC SHALL return SW 6A86
6. WHEN security conditions are not satisfied THEN the virtual UICC SHALL return SW 6982
7. WHEN conditions are not satisfied THEN the virtual UICC SHALL return SW 6985

### Requirement 7: Simulation Modes

**User Story:** As a tester, I want to configure different simulation behaviors, so that I can test server handling of various UICC scenarios.

#### Acceptance Criteria

1. WHEN in normal mode THEN the simulator SHALL process all valid commands successfully
2. WHEN in error mode THEN the simulator SHALL inject errors at configurable rate
3. WHEN in timeout mode THEN the simulator SHALL delay responses at configurable probability
4. WHEN configured THEN the simulator SHALL support different connection patterns:
   - `single`: One connection processes all commands
   - `per-command`: New connection per command
   - `batch`: Multiple commands per connection
   - `reconnect`: Disconnect and reconnect mid-session

### Requirement 8: Configuration

**User Story:** As a user, I want to configure the simulator via CLI and YAML files, so that I can adapt it to different testing scenarios.

#### Acceptance Criteria

1. WHEN starting the simulator THEN it SHALL accept configuration via CLI arguments
2. WHEN a config file is specified THEN the simulator SHALL load settings from YAML
3. WHEN configuring connection THEN the simulator SHALL support host, port, and timeout settings
4. WHEN configuring PSK THEN the simulator SHALL support identity and key (hex) settings
5. WHEN configuring UICC THEN the simulator SHALL support ICCID, IMSI, and applet configuration
6. WHEN configuring behavior THEN the simulator SHALL support mode, delay, and error rate settings
7. IF configuration is invalid THEN the simulator SHALL fail fast with clear error message

### Requirement 9: CLI Interface

**User Story:** As a developer, I want to control the simulator via command line, so that I can easily run tests and automation scripts.

#### Acceptance Criteria

1. WHEN running `gp-simulator run` THEN the simulator SHALL start with default config
2. WHEN running with `--server HOST:PORT` THEN the simulator SHALL connect to specified server
3. WHEN running with `--psk-identity` and `--psk-key` THEN the simulator SHALL use specified credentials
4. WHEN running with `--config FILE` THEN the simulator SHALL load configuration from YAML
5. WHEN running with `--mode error` THEN the simulator SHALL enable error injection
6. WHEN running with `--count N` THEN the simulator SHALL simulate N devices
7. WHEN running with `--loop` THEN the simulator SHALL run continuously
8. WHEN running `gp-simulator config generate` THEN the simulator SHALL output sample config

### Requirement 10: Integration with Test Framework

**User Story:** As a test developer, I want pytest fixtures for the simulator, so that I can write automated tests against the PSK-TLS server.

#### Acceptance Criteria

1. WHEN using the `simulator` fixture THEN pytest SHALL provide a configured simulator instance
2. WHEN using the `connected_simulator` fixture THEN pytest SHALL provide a connected simulator
3. WHEN the test completes THEN the fixture SHALL clean up simulator resources
4. WHEN configuring test fixtures THEN the simulator SHALL integrate with admin_server fixture

## Non-Functional Requirements

### Performance

- **Connection establishment**: Simulator SHALL establish TLS connection within 5 seconds
- **APDU processing**: Simulator SHALL process and respond to APDUs within 100ms
- **Concurrent instances**: System SHALL support at least 10 concurrent simulator instances
- **Memory usage**: Each simulator instance SHALL not exceed 20MB memory

### Reliability

- **Error recovery**: Simulator SHALL recover from transient errors without restart
- **Graceful shutdown**: Simulator SHALL clean up resources on termination
- **Logging**: All errors and state transitions SHALL be logged with sufficient context

### Usability

- **Clear output**: CLI output SHALL clearly indicate connection status and progress
- **Helpful errors**: Error messages SHALL indicate cause and potential resolution
- **Examples**: Configuration options SHALL be documented with examples
