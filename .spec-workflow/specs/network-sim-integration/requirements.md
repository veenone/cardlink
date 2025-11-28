# Requirements Document: Network Simulator Integration

## Introduction

The Network Simulator Integration component provides connectivity between CardLink and network simulators like Amarisoft Callbox. It enables controlled network environment testing by communicating with simulators via WebSocket/TCP APIs, triggering network events, and coordinating test scenarios that require precise network conditions.

This component enables testers to conduct SCP81 OTA testing in controlled, reproducible network environments without relying on live mobile networks.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Controlled testing**: Use simulated networks for reproducible test conditions
- **Real hardware testing**: Connect actual devices to simulated networks
- **Protocol transparency**: Monitor network events and correlate with OTA sessions
- **Local-first design**: Connect to local network simulators via WebSocket/TCP
- **Industry-standard tools**: Support for Amarisoft and compatible simulators

## Requirements

### Requirement 1: Network Simulator Connection Management

**User Story:** As a tester, I want to connect CardLink to my network simulator, so that I can control network conditions during OTA testing.

#### Acceptance Criteria

1. WHEN configuring connection THEN the system SHALL support WebSocket protocol
2. WHEN configuring connection THEN the system SHALL support TCP fallback
3. WHEN connecting THEN the system SHALL authenticate if required (API key/token)
4. WHEN connection is established THEN the system SHALL emit `simulator_connected` event
5. WHEN connection fails THEN the system SHALL retry with configurable backoff
6. WHEN connection is lost THEN the system SHALL attempt automatic reconnection
7. WHEN disconnecting THEN the system SHALL perform graceful shutdown
8. WHEN checking status THEN the system SHALL report connection health

### Requirement 2: Amarisoft Callbox Integration

**User Story:** As a tester using Amarisoft, I want CardLink to communicate with Callbox, so that I can leverage its LTE/5G simulation capabilities.

#### Acceptance Criteria

1. WHEN connecting to Amarisoft THEN the system SHALL use Amarisoft Remote API
2. WHEN querying status THEN the system SHALL retrieve:
   - Cell status (active, inactive)
   - Connected UE list
   - Network configuration (MCC, MNC, bands)
   - Signal strength settings
3. WHEN configuring cell THEN the system SHALL support:
   - Start/stop cell
   - Change frequency/band
   - Modify signal strength
   - Configure PLMN
4. WHEN monitoring UE THEN the system SHALL track:
   - UE attachment/detachment
   - Registration status
   - PDP/PDN context activation
   - Data session status
5. WHEN sending SMS THEN the system SHALL support MT-SMS injection
6. WHEN triggering events THEN the system SHALL support network-initiated procedures

### Requirement 3: UE Registration Monitoring

**User Story:** As a tester, I want to monitor device registration on the simulated network, so that I can verify connectivity before OTA testing.

#### Acceptance Criteria

1. WHEN a UE attaches THEN the system SHALL emit `ue_attached` event
2. WHEN a UE detaches THEN the system SHALL emit `ue_detached` event
3. WHEN monitoring THEN the system SHALL track:
   - IMSI
   - IMEI
   - MSISDN (if available)
   - Registration type (initial, periodic, mobility)
   - Attached cell ID
4. WHEN querying registered UEs THEN the system SHALL return current list
5. WHEN a specific IMSI registers THEN the system SHALL allow waiting for registration
6. WHEN registration fails THEN the system SHALL report reject cause

### Requirement 4: Data Session Management

**User Story:** As a tester, I want to monitor and control data sessions, so that I can ensure BIP connectivity.

#### Acceptance Criteria

1. WHEN PDP/PDN context activates THEN the system SHALL emit `data_session_activated` event
2. WHEN PDP/PDN context deactivates THEN the system SHALL emit `data_session_deactivated` event
3. WHEN monitoring sessions THEN the system SHALL track:
   - APN
   - IP address assigned
   - QoS parameters
   - Bearer type
4. WHEN querying sessions THEN the system SHALL return active session list
5. WHEN forcing session release THEN the system SHALL support network-initiated deactivation
6. WHEN session fails THEN the system SHALL report failure cause

### Requirement 5: SMS Injection and Monitoring

**User Story:** As a tester, I want to inject SMS messages via the network simulator, so that I can trigger OTA sessions using realistic SMS delivery.

#### Acceptance Criteria

1. WHEN injecting SMS THEN the system SHALL support MT-SMS delivery
2. WHEN sending SMS-PP THEN the system SHALL support PDU format
3. WHEN configuring SMS THEN the system SHALL set:
   - Originating address
   - Destination IMSI/MSISDN
   - Protocol identifier (for SMS-PP)
   - Data coding scheme
   - User data (TP-UD)
4. WHEN SMS is delivered THEN the system SHALL emit `sms_delivered` event
5. WHEN SMS delivery fails THEN the system SHALL emit `sms_failed` event with cause
6. WHEN monitoring MO-SMS THEN the system SHALL capture outgoing messages

### Requirement 6: Network Event Triggering

**User Story:** As a tester, I want to trigger network events programmatically, so that I can test UICC behavior under various network conditions.

#### Acceptance Criteria

1. WHEN triggering paging THEN the system SHALL initiate network paging
2. WHEN triggering handover THEN the system SHALL simulate inter-cell handover
3. WHEN triggering service request THEN the system SHALL initiate network service request
4. WHEN triggering TAU/RAU THEN the system SHALL force location update
5. WHEN triggering detach THEN the system SHALL initiate network-initiated detach
6. WHEN configuring radio conditions THEN the system SHALL support:
   - Signal strength changes
   - Radio link failure simulation
   - Coverage hole simulation
7. WHEN scheduling events THEN the system SHALL support delayed execution

### Requirement 7: Network Configuration Management

**User Story:** As a tester, I want to configure the simulated network, so that I can test different network scenarios.

#### Acceptance Criteria

1. WHEN configuring PLMN THEN the system SHALL set MCC/MNC
2. WHEN configuring cell THEN the system SHALL set:
   - Cell ID
   - TAC/LAC
   - Frequency/EARFCN
   - Bandwidth
   - TX power
3. WHEN configuring APN THEN the system SHALL support multiple APN definitions
4. WHEN configuring subscribers THEN the system SHALL support:
   - IMSI provisioning
   - Authentication keys (K, OPc)
   - Subscriber profiles
5. WHEN saving configuration THEN the system SHALL persist to file
6. WHEN loading configuration THEN the system SHALL apply from file
7. WHEN validating configuration THEN the system SHALL check consistency

### Requirement 8: Test Scenario Orchestration

**User Story:** As a tester, I want to orchestrate complex test scenarios involving network events, so that I can automate end-to-end testing.

#### Acceptance Criteria

1. WHEN defining scenario THEN the system SHALL support:
   - Sequential steps
   - Parallel steps
   - Conditional branches
   - Wait conditions
   - Timeout handling
2. WHEN executing scenario THEN the system SHALL coordinate:
   - Network simulator actions
   - Device controller actions
   - Server actions
3. WHEN monitoring scenario THEN the system SHALL report:
   - Current step
   - Step results
   - Timing information
4. WHEN scenario fails THEN the system SHALL:
   - Stop execution (configurable)
   - Report failure point
   - Collect diagnostics
5. WHEN scenario completes THEN the system SHALL generate report

### Requirement 9: Event Correlation

**User Story:** As a developer, I want network events correlated with OTA sessions, so that I can debug timing-sensitive issues.

#### Acceptance Criteria

1. WHEN correlating events THEN the system SHALL match by:
   - IMSI
   - Timestamp
   - Session ID
2. WHEN logging events THEN the system SHALL include:
   - Event type
   - Timestamp (millisecond precision)
   - Source (simulator, device, server)
   - Related identifiers
3. WHEN querying events THEN the system SHALL support:
   - Time range filtering
   - Event type filtering
   - Correlation ID filtering
4. WHEN exporting events THEN the system SHALL support:
   - JSON format
   - CSV format
   - Timeline visualization data

### Requirement 10: Simulator Status Dashboard

**User Story:** As a tester, I want to see network simulator status in the CardLink dashboard, so that I can monitor network state.

#### Acceptance Criteria

1. WHEN displaying status THEN the dashboard SHALL show:
   - Connection status
   - Cell status (active/inactive)
   - Connected UE count
   - Active data sessions
2. WHEN displaying UE list THEN the dashboard SHALL show:
   - IMSI
   - Registration status
   - IP address
   - Last activity
3. WHEN displaying events THEN the dashboard SHALL show:
   - Real-time event stream
   - Event timeline
   - Filterable event log
4. WHEN controlling simulator THEN the dashboard SHALL allow:
   - Start/stop cell
   - Inject SMS
   - Trigger events

### Requirement 11: CLI Integration

**User Story:** As a developer, I want to control network simulators via command line, so that I can automate testing workflows.

#### Acceptance Criteria

1. WHEN running `cardlink-netsim connect <url>` THEN the CLI SHALL connect to simulator
2. WHEN running `cardlink-netsim status` THEN the CLI SHALL show:
   - Connection status
   - Cell status
   - Connected UEs
3. WHEN running `cardlink-netsim cell start/stop` THEN the CLI SHALL control cell
4. WHEN running `cardlink-netsim ue list` THEN the CLI SHALL list connected UEs
5. WHEN running `cardlink-netsim ue wait <imsi>` THEN the CLI SHALL wait for registration
6. WHEN running `cardlink-netsim sms send <imsi> <pdu>` THEN the CLI SHALL inject SMS
7. WHEN running `cardlink-netsim event <type>` THEN the CLI SHALL trigger event
8. WHEN running `cardlink-netsim scenario run <file>` THEN the CLI SHALL execute scenario
9. WHEN running `cardlink-netsim config show/load/save` THEN the CLI SHALL manage config

### Requirement 12: Event Emission for Integration

**User Story:** As a system integrator, I want the network simulator component to emit events, so that other components can react to network changes.

#### Acceptance Criteria

1. WHEN simulator connects THEN the system SHALL emit `simulator_connected` event
2. WHEN simulator disconnects THEN the system SHALL emit `simulator_disconnected` event
3. WHEN UE registers THEN the system SHALL emit `ue_registered` event
4. WHEN UE deregisters THEN the system SHALL emit `ue_deregistered` event
5. WHEN data session changes THEN the system SHALL emit `data_session_changed` event
6. WHEN SMS is sent/received THEN the system SHALL emit `sms_event` event
7. WHEN network event occurs THEN the system SHALL emit `network_event` event
8. WHEN error occurs THEN the system SHALL emit `simulator_error` event

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: Separate classes for connection, UE management, SMS, events
- **Modular Design**: Network simulator integration usable standalone
- **Simulator Abstraction**: Abstract interface to support different simulator vendors
- **Dependency Injection**: Inject WebSocket client, event emitter

### Performance

- **Connection latency**: Establish connection within 5 seconds
- **Event latency**: Receive events within 100ms of occurrence
- **Command latency**: Execute commands within 500ms
- **Reconnection**: Reconnect within 10 seconds on connection loss

### Compatibility

- **Amarisoft Callbox**: LTE (eNB) and 5G NR (gNB) support
- **WebSocket**: RFC 6455 compliant
- **TCP**: Fallback for environments without WebSocket
- **Protocol versions**: Support Amarisoft Remote API versions

### Reliability

- **Connection recovery**: Automatic reconnection with exponential backoff
- **Message ordering**: Preserve event ordering
- **Timeout handling**: Configurable timeouts for all operations
- **Error isolation**: Simulator failures don't crash CardLink

### Security

- **Authentication**: Support API key/token authentication
- **TLS support**: Optional TLS for WebSocket connections
- **Credential handling**: Secure storage of authentication credentials
- **Access control**: Log simulator command execution
