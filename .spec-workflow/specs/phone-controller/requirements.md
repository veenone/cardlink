# Requirements Document: Phone Controller

## Introduction

The Phone Controller is the CardLink component responsible for managing Android smartphones used as test harnesses for SCP81 OTA testing. It provides device control via ADB (Android Debug Bridge), AT command interface for modem access, network configuration, BIP event monitoring, and SMS-PP trigger simulation.

This component enables testers to use real Android phones to initiate UICC-to-server connections, monitoring the complete OTA flow from SMS trigger through BIP channel establishment to HTTPS communication.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Real hardware testing**: Uses actual Android phones rather than simulators
- **Local-first design**: USB/ADB connection without network infrastructure
- **Protocol transparency**: Full visibility into BIP events, AT responses, and logcat
- **End-to-end validation**: Complete flow from SMS trigger to OTA session
- **Multi-device support**: Tested on Pixel, Samsung, OnePlus devices

## Requirements

### Requirement 1: ADB Device Discovery and Connection

**User Story:** As a tester, I want the controller to automatically discover connected Android phones, so that I can quickly start testing without manual configuration.

#### Acceptance Criteria

1. WHEN the controller starts THEN it SHALL scan for connected ADB devices
2. WHEN a device is connected via USB THEN the controller SHALL detect it within 5 seconds
3. WHEN a device is detected THEN the controller SHALL retrieve device info (model, serial, Android version)
4. WHEN a device is disconnected THEN the controller SHALL detect disconnection within 5 seconds
5. WHEN multiple devices are connected THEN the controller SHALL list all devices with identifiers
6. IF ADB is not installed or not in PATH THEN the controller SHALL display helpful error message

### Requirement 2: Device Information Retrieval and Profiling

**User Story:** As a tester, I want to query comprehensive information about connected phones and UICC cards, so that I can create device profiles and verify I'm testing on the correct device/card combination.

#### Acceptance Criteria

##### Device Information
1. WHEN querying device info THEN the controller SHALL return:
   - Device model name
   - Manufacturer
   - Android version and API level
   - Build number
   - Serial number
   - IMEI (International Mobile Equipment Identity)
   - Baseband/modem firmware version
   - Kernel version

##### UICC/SIM Information
2. WHEN querying UICC info THEN the controller SHALL return:
   - SIM/UICC status (present/absent/locked/ready)
   - ICCID (Integrated Circuit Card Identifier)
   - IMSI (International Mobile Subscriber Identity)
   - MSISDN (phone number, if available)
   - SPN (Service Provider Name)
   - MCC/MNC (Mobile Country Code / Mobile Network Code)
   - SIM slot information (for dual-SIM devices)

##### Network Information
3. WHEN querying network info THEN the controller SHALL return:
   - Current network operator name
   - Network type (LTE, 5G, etc.)
   - Signal strength
   - Data connection state
   - APN configuration

##### Profiling Features
4. WHEN creating a device profile THEN the controller SHALL store all queryable information as a snapshot
5. WHEN comparing profiles THEN the controller SHALL highlight differences between current state and saved profile
6. WHEN the UICC is changed THEN the controller SHALL detect the change within 10 seconds
7. WHEN device info is requested THEN the controller SHALL support both cached retrieval and forced refresh
8. WHEN exporting profile THEN the controller SHALL support JSON format for external tools

### Requirement 3: AT Command Interface

**User Story:** As a UICC developer, I want to send AT commands to the phone's modem, so that I can interact with the UICC and monitor modem status.

#### Acceptance Criteria

1. WHEN sending an AT command THEN the controller SHALL route it through the appropriate modem interface
2. WHEN receiving an AT response THEN the controller SHALL parse and return the result
3. WHEN sending AT commands THEN the controller SHALL support common commands:
   - AT+CPIN? (SIM status)
   - AT+CIMI (IMSI)
   - AT+CCID (ICCID)
   - AT+CGDCONT (PDP context)
   - AT+CSIM (generic SIM access)
4. WHEN AT access requires root THEN the controller SHALL detect and report the requirement
5. WHEN AT interface is unavailable THEN the controller SHALL provide alternative methods or clear error

### Requirement 4: Network Configuration

**User Story:** As a tester, I want to configure the phone's network settings, so that I can direct OTA traffic to my local test server.

#### Acceptance Criteria

1. WHEN configuring network THEN the controller SHALL support WiFi enable/disable
2. WHEN configuring network THEN the controller SHALL support WiFi network connection by SSID
3. WHEN configuring network THEN the controller SHALL support mobile data enable/disable
4. WHEN configuring APN THEN the controller SHALL support custom APN settings
5. WHEN routing traffic THEN the controller SHALL support proxy configuration for HTTP traffic
6. WHEN verifying connectivity THEN the controller SHALL test connection to admin server URL

### Requirement 5: BIP Event Monitoring

**User Story:** As a UICC developer, I want to monitor Bearer Independent Protocol events, so that I can debug UICC-initiated data connections.

#### Acceptance Criteria

1. WHEN BIP events occur THEN the controller SHALL capture them via logcat monitoring
2. WHEN a BIP OPEN CHANNEL event is detected THEN the controller SHALL log channel parameters
3. WHEN a BIP SEND DATA event is detected THEN the controller SHALL log data details
4. WHEN a BIP RECEIVE DATA event is detected THEN the controller SHALL log response details
5. WHEN a BIP CLOSE CHANNEL event is detected THEN the controller SHALL log closure reason
6. WHEN monitoring BIP THEN the controller SHALL emit events for dashboard integration
7. WHEN BIP events are captured THEN the controller SHALL correlate with OTA sessions

### Requirement 6: SMS-PP Trigger Simulation

**User Story:** As a tester, I want to send SMS-PP trigger messages to the UICC, so that I can initiate OTA sessions without a real mobile network.

#### Acceptance Criteria

1. WHEN sending SMS-PP THEN the controller SHALL encode the message as proper PDU format
2. WHEN sending SMS-PP THEN the controller SHALL support OTA trigger formats (GP Amendment B)
3. WHEN sending SMS-PP THEN the controller SHALL route via AT+CMGS or equivalent method
4. WHEN SMS-PP is sent THEN the controller SHALL log the PDU bytes and delivery status
5. IF direct SMS injection is not possible THEN the controller SHALL provide alternative trigger methods
6. WHEN configuring triggers THEN the controller SHALL support custom PDU templates

### Requirement 7: Logcat Monitoring and Parsing

**User Story:** As a developer, I want to monitor Android logcat for relevant events, so that I can debug issues in the OTA flow.

#### Acceptance Criteria

1. WHEN monitoring logcat THEN the controller SHALL filter for relevant tags (Telephony, SIM, BIP, CAT)
2. WHEN parsing logcat THEN the controller SHALL extract structured events from log lines
3. WHEN relevant events occur THEN the controller SHALL emit parsed events
4. WHEN monitoring THEN the controller SHALL support starting/stopping log capture
5. WHEN exporting THEN the controller SHALL support saving logcat to file
6. WHEN monitoring THEN the controller SHALL handle log buffer overflow gracefully

### Requirement 8: CLI Integration

**User Story:** As a developer, I want to control phones via command line, so that I can automate testing workflows.

#### Acceptance Criteria

1. WHEN running `cardlink-phone list` THEN the CLI SHALL display all connected devices with basic info
2. WHEN running `cardlink-phone info <device>` THEN the CLI SHALL show comprehensive device details:
   - Use `--device` for device info only
   - Use `--sim` for UICC/SIM info only
   - Use `--network` for network info only
   - Use `--all` (default) for complete profile
   - Use `--json` for JSON output format
3. WHEN running `cardlink-phone at <device> <command>` THEN the CLI SHALL send AT command
4. WHEN running `cardlink-phone trigger <device>` THEN the CLI SHALL send OTA trigger
5. WHEN running `cardlink-phone monitor <device>` THEN the CLI SHALL start BIP/logcat monitoring
6. WHEN running `cardlink-phone profile save <name>` THEN the CLI SHALL save current device state as profile
7. WHEN running `cardlink-phone profile load <name>` THEN the CLI SHALL apply saved profile settings
8. WHEN running `cardlink-phone profile compare <name>` THEN the CLI SHALL compare current state to saved profile
9. WHEN running commands THEN the CLI SHALL support `--device` flag for multi-device selection

### Requirement 9: Event Emission for Integration

**User Story:** As a dashboard developer, I want the phone controller to emit events, so that I can display phone status and BIP events in real-time.

#### Acceptance Criteria

1. WHEN a device is connected THEN the controller SHALL emit `device_connected` event
2. WHEN a device is disconnected THEN the controller SHALL emit `device_disconnected` event
3. WHEN a BIP event is detected THEN the controller SHALL emit `bip_event` with details
4. WHEN an SMS trigger is sent THEN the controller SHALL emit `sms_trigger_sent` event
5. WHEN an error occurs THEN the controller SHALL emit `device_error` event with details

### Requirement 10: Device Profile Management

**User Story:** As a tester, I want to save device configurations, so that I can quickly set up devices for repeated testing.

#### Acceptance Criteria

1. WHEN creating a profile THEN the controller SHALL store device settings (APN, WiFi, trigger config)
2. WHEN applying a profile THEN the controller SHALL configure the device automatically
3. WHEN listing profiles THEN the controller SHALL show available configurations
4. WHEN a profile is applied THEN the controller SHALL verify settings were applied successfully
5. WHEN storing profiles THEN the controller SHALL persist to database or file

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: Separate classes for ADB control, AT interface, BIP monitoring, SMS encoding
- **Modular Design**: Phone controller usable standalone without server or database
- **Abstraction Layer**: Abstract device interface to support future iOS extension
- **Dependency Injection**: Inject ADB path, timeout settings, event emitter

### Performance

- **Device detection**: Detect connected devices within 5 seconds
- **AT command latency**: Return AT command response within 2 seconds
- **Logcat processing**: Process logcat lines with < 100ms latency
- **Memory efficiency**: Handle continuous logcat monitoring without memory leaks

### Compatibility

- **Android versions**: Support Android 8.0 (API 26) and higher
- **Tested devices**: Validated on Google Pixel, Samsung Galaxy, OnePlus
- **ADB versions**: Support ADB version 1.0.41 and higher
- **Root requirement**: Document which features require root access

### Reliability

- **Connection recovery**: Automatically reconnect on USB disconnect/reconnect
- **Error handling**: Graceful handling of device not responding
- **Timeout management**: Configurable timeouts for all operations
- **Resource cleanup**: Properly release ADB connections on shutdown

### Security

- **USB debugging**: Require USB debugging enabled (user must authorize)
- **No credentials stored**: Do not store device unlock PINs or passwords
- **Logging**: Do not log sensitive AT command data (IMSI, keys) in plaintext
