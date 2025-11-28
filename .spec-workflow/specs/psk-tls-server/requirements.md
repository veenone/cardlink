# Requirements Document: PSK-TLS Admin Server

## Introduction

The PSK-TLS Admin Server is the core component of CardLink that implements a GlobalPlatform Amendment B compliant Remote Application Management (RAM) over HTTP server. This server enables secure communication with UICC cards using Pre-Shared Key TLS (PSK-TLS) for authentication, allowing testers to send GP commands to cards via the Bearer Independent Protocol (BIP) initiated HTTPS connections from the UICC.

This component is foundational to CardLink as it serves as the endpoint that UICC cards connect to during OTA testing, simulating a production OTA server in a controlled local environment.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Eliminates need for production OTA infrastructure**: Provides a fully functional admin server locally
- **Enables real hardware testing**: Accepts actual UICC-initiated connections
- **Protocol transparency**: Full logging of TLS handshakes and APDU exchanges
- **Local-first design**: Runs on developer's machine without cloud dependencies
- **Modular architecture**: Server component can operate independently or with other CardLink components

## Requirements

### Requirement 1: PSK-TLS Connection Handling

**User Story:** As a UICC developer, I want the server to accept PSK-TLS connections from UICC cards, so that I can test secure OTA communication without requiring certificate-based PKI infrastructure.

#### Acceptance Criteria

1. WHEN a UICC initiates a TLS connection with PSK identity THEN the server SHALL look up the corresponding PSK key from the configured key store
2. WHEN the PSK identity is found AND the key matches THEN the server SHALL complete the TLS handshake successfully
3. WHEN the PSK identity is not found THEN the server SHALL reject the connection with appropriate TLS alert
4. WHEN the TLS handshake completes THEN the server SHALL log the PSK identity, cipher suite, and session parameters
5. IF the connection uses an unsupported cipher suite THEN the server SHALL reject with handshake_failure alert
6. WHEN configuring cipher suites THEN the server SHALL support the following PSK cipher suites:
   - TLS_PSK_WITH_AES_128_CBC_SHA256 (default, production-grade)
   - TLS_PSK_WITH_AES_256_CBC_SHA384 (default, production-grade)
   - TLS_PSK_WITH_AES_128_CBC_SHA (legacy compatibility)
   - TLS_PSK_WITH_AES_256_CBC_SHA (legacy compatibility)
   - TLS_PSK_WITH_NULL_SHA (testing only, no encryption)
   - TLS_PSK_WITH_NULL_SHA256 (testing only, no encryption)
7. WHEN NULL cipher suites are enabled THEN the server SHALL log a warning indicating unencrypted traffic
8. WHEN starting the server THEN the administrator SHALL be able to configure allowed cipher suites via configuration file or CLI flag

### Requirement 2: HTTP Admin Protocol Implementation

**User Story:** As a QA engineer, I want the server to implement the GP Amendment B HTTP Admin protocol, so that I can send standard RAM commands to UICC cards.

#### Acceptance Criteria

1. WHEN receiving an HTTP POST to /admin THEN the server SHALL parse the request as GP Admin protocol
2. WHEN a valid command packet is received THEN the server SHALL extract and decode the APDU commands
3. WHEN processing a command THEN the server SHALL wrap responses in proper GP Admin response format
4. IF the request content-type is not application/vnd.globalplatform.card-content-mgt;version=1.0 THEN the server SHALL respond with 415 Unsupported Media Type
5. WHEN a session is established THEN the server SHALL maintain session state for the configured timeout period (default 300 seconds)

### Requirement 3: GP Command Processing

**User Story:** As a UICC developer, I want to send standard GlobalPlatform commands through the server, so that I can perform card content management operations.

#### Acceptance Criteria

1. WHEN receiving a SELECT command THEN the server SHALL forward it to the appropriate response handler
2. WHEN receiving an INSTALL command THEN the server SHALL process installation parameters and return appropriate status
3. WHEN receiving a DELETE command THEN the server SHALL process deletion parameters and return appropriate status
4. WHEN receiving a GET STATUS command THEN the server SHALL return card content information
5. WHEN receiving any GP command THEN the server SHALL log command bytes, response bytes, status word, and timing

### Requirement 4: Session Management

**User Story:** As a tester, I want the server to manage OTA sessions properly, so that I can handle multiple sequential test operations within a single session.

#### Acceptance Criteria

1. WHEN a new TLS connection is established THEN the server SHALL create a unique session identifier
2. WHEN a session is active THEN the server SHALL track all APDU exchanges within that session
3. WHEN a session exceeds the configured timeout (default 300s) THEN the server SHALL terminate the session gracefully
4. WHEN a session is terminated THEN the server SHALL log session summary including duration, command count, and final status
5. IF the client disconnects unexpectedly THEN the server SHALL clean up session resources within 5 seconds

### Requirement 5: Server Configuration

**User Story:** As an administrator, I want to configure the server parameters, so that I can adapt it to different testing environments.

#### Acceptance Criteria

1. WHEN the server starts THEN it SHALL load configuration from file (YAML) or environment variables
2. WHEN configuring PSK keys THEN the server SHALL support loading keys from file or database
3. WHEN configuring ports THEN the server SHALL allow customization of TLS port (default 8443)
4. WHEN configuring timeouts THEN the server SHALL support socket timeout (default 60s) and session timeout (default 300s)
5. IF configuration is invalid THEN the server SHALL fail fast with clear error message

### Requirement 6: CLI Integration

**User Story:** As a developer, I want to control the server via command line, so that I can easily start, stop, and configure it for testing.

#### Acceptance Criteria

1. WHEN running `cardlink-server start` THEN the server SHALL start and listen on configured port
2. WHEN running `cardlink-server start --port 9443` THEN the server SHALL use the specified port
3. WHEN running `cardlink-server start --dashboard` THEN the server SHALL also start the web dashboard
4. WHEN running `cardlink-server stop` THEN the server SHALL gracefully shutdown active sessions
5. WHEN the server starts successfully THEN it SHALL display listening address and port

### Requirement 7: Event Emission for Integration

**User Story:** As a dashboard developer, I want the server to emit events for key activities, so that I can display real-time updates to users.

#### Acceptance Criteria

1. WHEN a TLS handshake begins THEN the server SHALL emit a `tls_handshake_start` event
2. WHEN a TLS handshake completes THEN the server SHALL emit a `tls_handshake_complete` event with details
3. WHEN an APDU command is received THEN the server SHALL emit an `apdu_received` event
4. WHEN an APDU response is sent THEN the server SHALL emit an `apdu_sent` event
5. WHEN a session ends THEN the server SHALL emit a `session_ended` event with summary

### Requirement 8: Negative Case and Error Handling

**User Story:** As a QA engineer, I want the server to handle error conditions gracefully and provide detailed diagnostics, so that I can test UICC behavior under adverse network conditions and configuration mismatches.

#### Acceptance Criteria

##### Connection Interruption Handling
1. WHEN a TCP connection is interrupted mid-session THEN the server SHALL detect the disconnection within 5 seconds
2. WHEN a connection interruption is detected THEN the server SHALL log the interruption with session ID, last successful command, and timestamp
3. WHEN a connection interruption occurs THEN the server SHALL emit a `connection_interrupted` event with diagnostic details
4. WHEN a connection is interrupted THEN the server SHALL clean up all session resources and release memory

##### PSK Mismatch Handling
5. WHEN the UICC presents a PSK identity that exists but the key value does not match THEN the server SHALL reject with TLS alert `decrypt_error` (51)
6. WHEN a PSK mismatch occurs THEN the server SHALL log the PSK identity (but NOT the key values) and source IP address
7. WHEN a PSK mismatch occurs THEN the server SHALL emit a `psk_mismatch` event for monitoring and alerting
8. WHEN multiple PSK mismatches occur from the same source within 60 seconds THEN the server SHALL log a warning indicating potential misconfiguration

##### Handshake Interruption Handling
9. WHEN a TLS handshake is interrupted by network jitter or packet loss THEN the server SHALL wait for the configured handshake timeout (default 30s) before closing
10. WHEN a handshake times out THEN the server SHALL log the partial handshake state including last received message type
11. WHEN a handshake is interrupted THEN the server SHALL emit a `handshake_interrupted` event with failure reason
12. WHEN a ClientHello is received but no subsequent messages arrive THEN the server SHALL log as potential network issue

##### General Error Recovery
13. WHEN any TLS-level error occurs THEN the server SHALL send the appropriate TLS alert before closing the connection
14. WHEN an unexpected error occurs THEN the server SHALL NOT crash but log the error and continue accepting new connections
15. WHEN error rates exceed configurable thresholds THEN the server SHALL emit a `high_error_rate` event for monitoring

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: Separate classes for TLS handling, HTTP protocol, GP command processing, and session management
- **Modular Design**: Server module should be usable standalone without dashboard or database dependencies
- **Dependency Management**: Use dependency injection for key store, session store, and event emitter
- **Clear Interfaces**: Define abstract interfaces for extensibility (e.g., different key store backends)

### Performance

- **Connection handling**: Server SHALL handle at least 10 concurrent TLS connections
- **Response latency**: Server SHALL respond to APDU commands within 100ms (excluding network latency)
- **Memory efficiency**: Server SHALL not exceed 100MB memory for typical operation
- **Startup time**: Server SHALL be ready to accept connections within 3 seconds

### Security

- **TLS version**: Server SHALL support TLS 1.2 with PSK cipher suites
- **Production cipher suites**: Default enabled: TLS_PSK_WITH_AES_128_CBC_SHA256, TLS_PSK_WITH_AES_256_CBC_SHA384
- **Legacy cipher suites**: Optional: TLS_PSK_WITH_AES_128_CBC_SHA, TLS_PSK_WITH_AES_256_CBC_SHA
- **Testing cipher suites**: Optional (disabled by default): TLS_PSK_WITH_NULL_SHA, TLS_PSK_WITH_NULL_SHA256 - enables unencrypted PSK-TLS for handshake debugging
- **NULL cipher warning**: When NULL cipher suites are enabled, server SHALL display prominent warning at startup and log all NULL cipher connections
- **Key protection**: PSK keys SHALL NOT be logged in plaintext
- **Session isolation**: Each session SHALL be isolated; one session cannot access another's data
- **Input validation**: All incoming data SHALL be validated before processing

### Reliability

- **Graceful degradation**: Server SHALL continue operating if non-critical components fail
- **Error recovery**: Server SHALL recover from transient errors without restart
- **Resource cleanup**: Server SHALL properly release all resources on shutdown
- **Logging**: All errors SHALL be logged with sufficient context for debugging

### Usability

- **Clear logging**: Server logs SHALL include timestamps, log levels, and structured data
- **Helpful errors**: Error messages SHALL indicate cause and potential resolution
- **Status visibility**: Server SHALL provide health check endpoint for monitoring
- **Documentation**: All configuration options SHALL be documented with examples
