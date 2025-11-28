# Requirements Document: Modem Controller

## Introduction

The Modem Controller is the CardLink component responsible for managing IoT cellular modems (such as Quectel RG500Q-EU and EG25-G) used as test harnesses for SCP81 OTA testing. It provides device control via serial/USB AT commands, network configuration, BIP event monitoring, QXDM diagnostic integration, and SMS-PP trigger simulation.

This component enables testers to use dedicated IoT modems for UICC-to-server connections, offering more direct modem access and diagnostic capabilities compared to smartphone-based testing.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Real hardware testing**: Uses actual IoT modems with direct AT command access
- **Local-first design**: Serial/USB connection without network infrastructure
- **Protocol transparency**: Full AT command logging and QXDM diagnostics
- **Direct modem access**: No Android OS layer between tester and modem
- **Industry-standard modules**: Support for Quectel and compatible modems

## Requirements

### Requirement 1: Modem Discovery and Connection

**User Story:** As a tester, I want the controller to discover connected IoT modems, so that I can quickly start testing without manual serial port configuration.

#### Acceptance Criteria

1. WHEN the controller starts THEN it SHALL scan for connected modems on serial/USB ports
2. WHEN a modem is connected THEN the controller SHALL detect it within 5 seconds
3. WHEN a modem is detected THEN it SHALL identify the modem type (Quectel, Sierra, etc.)
4. WHEN a modem is disconnected THEN the controller SHALL detect disconnection within 5 seconds
5. WHEN multiple modems are connected THEN the controller SHALL list all with port identifiers
6. IF no modem is found THEN the controller SHALL display helpful troubleshooting message

### Requirement 2: Device Information Retrieval and Profiling

**User Story:** As a tester, I want to query comprehensive information about connected modems and UICC cards, so that I can create device profiles and verify I'm testing on the correct modem/card combination.

#### Acceptance Criteria

##### Modem Information
1. WHEN querying modem info THEN the controller SHALL return:
   - Manufacturer (ATI or AT+CGMI)
   - Model (ATI or AT+CGMM)
   - Firmware version (AT+CGMR)
   - IMEI (AT+CGSN)
   - Serial number
   - Module type (LTE Cat 4, 5G, etc.)
   - Supported bands

##### UICC/SIM Information
2. WHEN querying UICC info THEN the controller SHALL return:
   - SIM status (AT+CPIN?)
   - ICCID (AT+CCID or AT+QCCID)
   - IMSI (AT+CIMI)
   - MSISDN (AT+CNUM, if available)
   - SPN (Service Provider Name)
   - MCC/MNC

##### Network Information
3. WHEN querying network info THEN the controller SHALL return:
   - Registration status (AT+CREG?, AT+CEREG?)
   - Current operator (AT+COPS?)
   - Network type (LTE, 5G NR)
   - Signal strength (AT+CSQ, AT+QCSQ)
   - Cell ID and LAC/TAC
   - APN configuration (AT+CGDCONT?)

##### Profiling Features
4. WHEN creating a modem profile THEN the controller SHALL store all queryable information
5. WHEN comparing profiles THEN the controller SHALL highlight differences
6. WHEN the UICC is changed THEN the controller SHALL detect the change within 10 seconds
7. WHEN exporting profile THEN the controller SHALL support JSON format

### Requirement 3: AT Command Interface

**User Story:** As a UICC developer, I want to send AT commands directly to the modem, so that I can interact with the UICC and configure modem settings.

#### Acceptance Criteria

1. WHEN sending an AT command THEN the controller SHALL write to the serial port
2. WHEN receiving a response THEN the controller SHALL parse and return the result
3. WHEN sending commands THEN the controller SHALL support all standard 3GPP AT commands
4. WHEN sending commands THEN the controller SHALL support Quectel-specific AT commands (AT+Q*)
5. WHEN a command times out THEN the controller SHALL return timeout error
6. WHEN sending AT+CSIM THEN the controller SHALL support raw APDU exchange with UICC

### Requirement 4: Network Configuration

**User Story:** As a tester, I want to configure the modem's network settings, so that I can establish data connections and route traffic to my test server.

#### Acceptance Criteria

1. WHEN configuring PDP context THEN the controller SHALL support AT+CGDCONT
2. WHEN activating PDP THEN the controller SHALL support AT+CGACT
3. WHEN configuring APN THEN the controller SHALL support authentication (PAP/CHAP)
4. WHEN checking registration THEN the controller SHALL monitor AT+CREG/AT+CEREG
5. WHEN establishing data THEN the controller SHALL verify IP address assignment
6. WHEN testing connectivity THEN the controller SHALL support ping via AT+QPING

### Requirement 5: BIP Event Monitoring

**User Story:** As a UICC developer, I want to monitor Bearer Independent Protocol events on the modem, so that I can debug UICC-initiated data connections.

#### Acceptance Criteria

1. WHEN BIP events occur THEN the controller SHALL capture them via URC (Unsolicited Result Code)
2. WHEN monitoring STK/USAT THEN the controller SHALL enable AT+QSTK notifications
3. WHEN a BIP OPEN CHANNEL occurs THEN the controller SHALL log channel parameters
4. WHEN a BIP SEND DATA occurs THEN the controller SHALL log data details
5. WHEN BIP events are captured THEN the controller SHALL emit events for dashboard
6. WHEN monitoring THEN the controller SHALL correlate events with OTA sessions

### Requirement 6: SMS-PP Trigger Simulation

**User Story:** As a tester, I want to send SMS-PP trigger messages via the modem, so that I can initiate OTA sessions.

#### Acceptance Criteria

1. WHEN sending SMS-PP THEN the controller SHALL use AT+CMGS with PDU mode
2. WHEN encoding PDU THEN the controller SHALL support OTA trigger formats
3. WHEN sending THEN the controller SHALL log PDU bytes and delivery status
4. WHEN configuring THEN the controller SHALL support AT+CMGF=0 (PDU mode)
5. WHEN receiving delivery report THEN the controller SHALL parse and log status

### Requirement 7: QXDM Diagnostic Integration

**User Story:** As a developer, I want to use QXDM diagnostics with Qualcomm-based modems, so that I can capture low-level diagnostic data for debugging.

#### Acceptance Criteria

1. WHEN QXDM is available THEN the controller SHALL detect the DM port
2. WHEN enabling diagnostics THEN the controller SHALL configure diagnostic messages
3. WHEN capturing THEN the controller SHALL log relevant diagnostic packets
4. WHEN exporting THEN the controller SHALL support ISF/DLF file format
5. IF QXDM is not available THEN the controller SHALL continue without diagnostics
6. WHEN configuring THEN the controller SHALL support Quectel-specific diag commands

### Requirement 8: CLI Integration

**User Story:** As a developer, I want to control modems via command line, so that I can automate testing workflows.

#### Acceptance Criteria

1. WHEN running `cardlink-modem list` THEN the CLI SHALL display all connected modems
2. WHEN running `cardlink-modem info <modem>` THEN the CLI SHALL show modem details:
   - Use `--modem` for modem info only
   - Use `--sim` for UICC/SIM info only
   - Use `--network` for network info only
   - Use `--all` (default) for complete profile
   - Use `--json` for JSON output format
3. WHEN running `cardlink-modem at <modem> <command>` THEN the CLI SHALL send AT command
4. WHEN running `cardlink-modem trigger <modem>` THEN the CLI SHALL send OTA trigger
5. WHEN running `cardlink-modem monitor <modem>` THEN the CLI SHALL start BIP/URC monitoring
6. WHEN running `cardlink-modem profile save/load/compare` THEN the CLI SHALL manage profiles
7. WHEN running `cardlink-modem diag <modem>` THEN the CLI SHALL start QXDM capture

### Requirement 9: Event Emission for Integration

**User Story:** As a dashboard developer, I want the modem controller to emit events, so that I can display modem status and BIP events in real-time.

#### Acceptance Criteria

1. WHEN a modem is connected THEN the controller SHALL emit `modem_connected` event
2. WHEN a modem is disconnected THEN the controller SHALL emit `modem_disconnected` event
3. WHEN a BIP event is detected THEN the controller SHALL emit `bip_event` with details
4. WHEN an SMS trigger is sent THEN the controller SHALL emit `sms_trigger_sent` event
5. WHEN network status changes THEN the controller SHALL emit `network_status_changed` event
6. WHEN an error occurs THEN the controller SHALL emit `modem_error` event

### Requirement 10: Quectel-Specific Features

**User Story:** As a tester using Quectel modems, I want access to Quectel-specific features, so that I can leverage the full capabilities of the module.

#### Acceptance Criteria

1. WHEN using Quectel modem THEN the controller SHALL support AT+QCFG commands
2. WHEN checking signal THEN the controller SHALL use AT+QCSQ for detailed info
3. WHEN monitoring STK THEN the controller SHALL use AT+QSTK for USAT events
4. WHEN accessing UICC THEN the controller SHALL support AT+CSIM and AT+CRSM
5. WHEN configuring bands THEN the controller SHALL support AT+QCFG="band"
6. WHEN enabling TCP/IP THEN the controller SHALL support AT+QIACT for data

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: Separate classes for serial communication, AT parsing, BIP monitoring, QXDM
- **Modular Design**: Modem controller usable standalone without server or database
- **Modem Abstraction**: Abstract interface to support different modem vendors (Quectel, Sierra, etc.)
- **Dependency Injection**: Inject serial port, timeout settings, event emitter

### Performance

- **Modem detection**: Detect connected modems within 5 seconds
- **AT command latency**: Return AT response within 2 seconds for simple commands
- **AT command timeout**: Support up to 180 seconds for long operations (network registration)
- **URC processing**: Process unsolicited result codes with < 100ms latency

### Compatibility

- **Quectel modems**: RG500Q-EU (5G), EG25-G (LTE Cat 4), BG96 (LTE Cat M1)
- **Serial interfaces**: Support USB CDC-ACM, USB serial, hardware serial
- **Baud rates**: Support 9600 to 921600 baud (default 115200)
- **Operating systems**: Linux, macOS, Windows serial port access

### Reliability

- **Connection recovery**: Automatically reconnect on USB disconnect/reconnect
- **Error handling**: Graceful handling of serial communication errors
- **Timeout management**: Configurable timeouts for all AT operations
- **Buffer management**: Handle partial responses and multi-line outputs

### Security

- **No credentials stored**: Do not persist SIM PIN codes
- **Logging**: Do not log IMSI, keys, or sensitive data in plaintext
- **Port access**: Require appropriate permissions for serial port access
