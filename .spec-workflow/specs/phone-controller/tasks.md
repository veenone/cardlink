# Implementation Tasks: Phone Controller

## Task Overview

This document breaks down the Phone Controller implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Core Infrastructure

_Leverage:_ Python project structure conventions, existing CardLink module organization patterns

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

_Prompt:_ Role: Python backend developer | Task: Set up the phone controller module structure with __init__.py, models.py, and exceptions.py. Define all data models using Python dataclasses (DeviceProfile, SIMProfile, NetworkProfile, FullProfile, BIPEvent, ATResponse) and enums (DeviceState, BIPEventType). Create custom exception hierarchy (PhoneControllerError, ADBNotFoundError, DeviceNotFoundError, DeviceUnauthorizedError, ATCommandError, RootRequiredError, TimeoutError). | Restrictions: Follow Python packaging best practices, use absolute imports, use @dataclass decorator with type hints | Success: Module structure exists with all data models and exceptions defined, can be imported correctly

- [x] 1.1. Create `src/gp_ota_tester/phone/` directory structure with `__init__.py`, `models.py`, and `exceptions.py` files
- [x] 1.2. Implement DeviceProfile, SIMProfile, NetworkProfile, FullProfile, BIPEvent, ATResponse dataclasses and DeviceState, BIPEventType enums
- [x] 1.3. Implement PhoneControllerError, ADBNotFoundError, DeviceNotFoundError, DeviceUnauthorizedError, ATCommandError, RootRequiredError, TimeoutError exception classes

### 2. ADB Client Implementation

_Leverage:_ Python subprocess module, asyncio.subprocess, shutil.which for executable detection

_Requirements:_ 1, 7

_Prompt:_ Role: Python async developer | Task: Implement ADBClient class with ADB path auto-detection, async command execution with timeout support, shell command execution, device listing via `adb devices -l`, and async logcat streaming. | Restrictions: Must be async, handle TimeoutError conversion, decode bytes to UTF-8, support custom ADB paths | Success: ADBClient can execute ADB commands asynchronously, list devices, stream logcat, all with proper timeout handling

- [x] 2.1. Create ADBClient class with constructor, ADB path configuration, and `is_available()` method
- [x] 2.2. Implement async `execute(command, serial, timeout)` method with subprocess handling and timeout support
- [x] 2.3. Implement async `shell(command, serial, timeout)` method for executing shell commands on device
- [x] 2.4. Implement async `get_devices()` method that parses `adb devices -l` output
- [x] 2.5. Implement async generator `start_logcat(serial, filters)` for streaming logcat output
- [ ] 2.6. Write comprehensive unit tests for ADBClient with mocked subprocess calls

### 3. Device Manager Implementation

_Leverage:_ ADBClient for device discovery, EventEmitter pattern for notifications, asyncio.create_task for background execution

_Requirements:_ 1, 9

_Prompt:_ Role: Python async developer | Task: Implement DeviceManager class that tracks connected devices, monitors connection changes via background polling, detects device state transitions (disconnected, unauthorized, offline, connected), and emits events for device connection/disconnection/state changes. | Restrictions: Use asyncio.create_task for background monitoring, don't block caller, handle task cancellation gracefully | Success: DeviceManager discovers devices, detects connections/disconnections within 5 seconds, emits appropriate events

- [x] 3.1. Create DeviceManager class with ADBClient and EventEmitter initialization
- [x] 3.2. Implement async `scan_devices()` method to discover all connected devices
- [x] 3.3. Implement async `start_monitoring()` method with background polling task
- [x] 3.4. Implement `stop_monitoring()` method to cancel background task
- [x] 3.5. Implement device state tracking (disconnected, unauthorized, offline, connected) with state change events
- [ ] 3.6. Write unit tests for device scanning, connection detection, and state transitions

### 4. Device Information and Profiling

_Leverage:_ ADB getprop command, Android system properties, dumpsys telephony.registry, dumpsys connectivity

_Requirements:_ 2, 4, 10

_Prompt:_ Role: Python developer | Task: Implement DeviceInfo class with TTL-based caching (30s) for device hardware info (model, manufacturer, Android version, IMEI), SIM info (ICCID, IMSI, operator), and network info (network type, signal, APN). Implement get_full_profile() combining all info, export_json() for serialization, and compare() for profile diff. | Restrictions: Use cache with 30s TTL, handle missing properties gracefully, parse dumpsys output carefully | Success: Returns complete device profiles with all available information, supports JSON export and comparison

- [x] 4.1. Create DeviceInfo class with ADBClient and caching support
- [x] 4.2. Implement async `get_device_info()` method to retrieve device hardware information
- [x] 4.3. Implement async `get_sim_info()` method to retrieve SIM/UICC information
- [x] 4.4. Implement async `get_network_info()` method to retrieve network status and configuration
- [x] 4.5. Implement async `get_full_profile()` method combining all profile information
- [x] 4.6. Implement `export_json()` method to serialize profiles to JSON
- [x] 4.7. Implement `compare(profile1, profile2)` static method to identify profile differences
- [ ] 4.8. Write unit tests for device info retrieval, SIM info, network info, and profile operations

### 5. AT Command Interface

_Leverage:_ Multiple AT command transport methods (service call, dialer code, device node), regex for response parsing

_Requirements:_ 3

_Prompt:_ Role: Python developer | Task: Implement ATInterface class with auto-detection of working AT method (SERVICE_CALL, DIALER_CODE, DEVICE_NODE), async send_command() with response parsing (OK, ERROR, +CME ERROR), and helper methods for common commands (CPIN, CIMI, CCID, CSIM). | Restrictions: Try methods in order of likelihood, cache working method, timeout each attempt, extract CME error codes | Success: Sends AT commands via available method, parses responses correctly, provides typed responses for common commands

- [x] 5.1. Create ATInterface class with ADBClient and AT method auto-detection
- [x] 5.2. Implement service call, dialer code, and direct device node AT command methods
- [x] 5.3. Implement async `send_command(command, timeout)` method with automatic method detection
- [x] 5.4. Implement helper methods for common AT commands (CPIN, CIMI, CCID, CSIM)
- [x] 5.5. Implement `is_available()` and `requires_root()` methods
- [ ] 5.6. Write unit tests for AT command methods, response parsing, and method fallback

### 6. BIP Monitoring

_Leverage:_ Regular expressions for pattern matching, logcat line format parsing, async generators

_Requirements:_ 5, 7, 9

_Prompt:_ Role: Python developer | Task: Implement LogcatParser with BIP event patterns (OPEN_CHANNEL, CLOSE_CHANNEL, SEND_DATA, RECEIVE_DATA), parse_line() for structured events, and is_bip_event()/extract_bip_event() for BIP detection. Implement BIPMonitor with start()/stop() methods and background event processing that emits events via EventEmitter. | Restrictions: Support different logcat formats, return None for unparseable lines, wrap in try-except to continue on errors | Success: Identifies BIP events from logcat, extracts structured data, emits events in real-time

- [x] 6.1. Create LogcatParser class with BIP event pattern definitions
- [x] 6.2. Implement `parse_line(line)` method to extract structured logcat events
- [x] 6.3. Implement `is_bip_event(event)` and `extract_bip_event(event)` methods
- [x] 6.4. Create BIPMonitor class with ADBClient, EventEmitter initialization
- [x] 6.5. Implement async `start()` and `stop()` methods for BIP monitoring
- [x] 6.6. Implement background task that processes logcat lines and emits BIP events
- [ ] 6.7. Write unit tests for logcat parsing, BIP pattern matching, and event extraction

### 7. SMS-PP Trigger

_Leverage:_ GSM 03.40 PDU format, GlobalPlatform OTA specifications, AT+CMGS command

_Requirements:_ 6

_Prompt:_ Role: Python developer | Task: Implement SMSTrigger class with TriggerTemplate definitions (OTA_TRIGGER, RAM_COMMAND), build_pdu() following GSM 03.40 structure, send_trigger() via AT+CMGS or content provider fallback, and send_raw_pdu() for custom PDUs. | Restrictions: Follow GSM 03.40 PDU structure exactly, try AT method first, log full PDU for debugging | Success: Generates valid SMS-PP PDUs, sends triggers via available method

- [x] 7.1. Create SMSTrigger class with ADBClient and trigger template definitions
- [x] 7.2. Implement `build_pdu(template, params)` method for SMS-PP PDU construction
- [x] 7.3. Define trigger templates for OTA and RAM commands
- [x] 7.4. Implement async `send_trigger(template, params)` method to send SMS-PP triggers
- [x] 7.5. Implement async `send_raw_pdu(pdu)` method for custom PDU sending
- [ ] 7.6. Write unit tests for PDU encoding, template building, and sending logic

### 8. Network Manager

_Leverage:_ Android svc command, cmd command, content provider for APN

_Requirements:_ 4

_Prompt:_ Role: Python developer | Task: Implement NetworkManager class with WiFi control (enable/disable/connect), mobile data control (enable/disable), APN configuration via content provider, and connectivity testing via curl/wget. | Restrictions: Handle different Android versions, handle carrier APN restrictions, may require root for some operations | Success: Can control WiFi and mobile data, configure APN, verify connectivity

- [x] 8.1. Create NetworkManager class with ADBClient initialization
- [x] 8.2. Implement async `enable_wifi()` and `disable_wifi()` methods
- [x] 8.3. Implement async `connect_wifi(ssid, password)` method
- [x] 8.4. Implement async `enable_mobile_data()` and `disable_mobile_data()` methods
- [x] 8.5. Implement async `set_apn(apn_config)` method
- [x] 8.6. Implement async `test_connectivity(url)` method to verify network connectivity
- [ ] 8.7. Write unit tests for WiFi, mobile data, and connectivity operations

### 9. Profile Manager

_Leverage:_ File system for storage, JSON for serialization, aiofiles for async I/O

_Requirements:_ 10

_Prompt:_ Role: Python developer | Task: Implement ProfileManager class with storage in ~/.cardlink/profiles/, async save_profile()/load_profile() with JSON serialization, list_profiles()/delete_profile() for management, and export_profile()/import_profile() for data exchange. | Restrictions: Use aiofiles for async I/O, convert datetimes to ISO strings, raise ProfileNotFoundError if file doesn't exist | Success: Saves and loads profiles as JSON files with proper serialization

- [x] 9.1. Create ProfileManager class with storage path initialization
- [x] 9.2. Implement async `save_profile(name, profile)` and `load_profile(name)` methods
- [x] 9.3. Implement `list_profiles()` and `delete_profile(name)` methods
- [x] 9.4. Implement `export_profile(name, format)` and `import_profile(name, data)` methods
- [ ] 9.5. Write unit tests for profile save, load, list, delete, and import/export operations

### 10. Phone Controller Main Class

_Leverage:_ All previously implemented components, Facade pattern

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

_Prompt:_ Role: Python architect | Task: Implement PhoneController as main entry point that initializes all components (ADBClient, DeviceManager, EventEmitter), provides discover_devices(), get_device() returning Device facade with access to info/at/network/sms/monitor, and event callbacks (on_device_connected, on_device_disconnected, on_bip_event). | Restrictions: Verify ADB in constructor, cache Device instances, fail fast if ADB not available | Success: PhoneController provides unified API for all phone controller functionality

- [x] 10.1. Create PhoneController class with ADBClient, DeviceManager, EventEmitter initialization
- [x] 10.2. Implement async `discover_devices()` method
- [x] 10.3. Implement `get_device(serial)` method that returns Device facade object
- [x] 10.4. Implement `on_device_connected(callback)` and `on_device_disconnected(callback)` methods
- [ ] 10.5. Write unit tests for PhoneController initialization, device discovery, and event handling

### 11. CLI Integration

_Leverage:_ Click for CLI framework, PhoneController API, tabulate/rich for formatting

_Requirements:_ 8

_Prompt:_ Role: CLI developer | Task: Implement cardlink-phone CLI with commands: list (device table), info (with --device/--sim/--network/--all/--json flags), at (send AT command), trigger (with --template/--pdu options), monitor (real-time BIP events), and profile subgroup (save/load/compare/list). | Restrictions: Use Click decorators, handle async with asyncio.run(), format output nicely, handle no devices case | Success: All CLI commands work correctly with proper output formatting

- [x] 11.1. Create CLI entry point with `list` command
- [x] 11.2. Implement `info <device>` command with multiple display options
- [x] 11.3. Implement `at <device> <command>` command
- [x] 11.4. Implement `trigger <device>` command with template and PDU options
- [x] 11.5. Implement `monitor <device>` command for real-time BIP event display
- [x] 11.6. Implement profile subcommands (save, load, compare, list)
- [ ] 11.7. Write CLI integration tests

### 12. Integration Testing

_Leverage:_ pytest with skipif for device availability, real ADB connection

_Requirements:_ 1, 2, 3, 5, 7

_Prompt:_ Role: Test engineer | Task: Write integration tests that run against real Android devices for device discovery, device info retrieval, AT commands (safe read-only only), and BIP monitoring lifecycle. | Restrictions: Require real device, skip if ADB not available or no device, don't hardcode device details, test data structure not specific values | Success: Integration tests pass with real device, verify actual device interaction

- [ ] 12.1. Write device integration tests for discovery and information retrieval with real device
- [ ] 12.2. Write AT command integration tests with real device
- [ ] 12.3. Write BIP monitoring integration tests with real device

## Task Dependencies

```
Task 1 (Setup)
    └─> Task 2 (ADBClient)
            ├─> Task 3 (DeviceManager)
            ├─> Task 4 (DeviceInfo)
            ├─> Task 5 (ATInterface)
            ├─> Task 6 (BIPMonitor)
            ├─> Task 7 (SMSTrigger)
            └─> Task 8 (NetworkManager)

Task 4 (DeviceInfo)
    └─> Task 9 (ProfileManager)

Task 3 + Task 4 + Task 5 + Task 6 + Task 7 + Task 8 + Task 9
    └─> Task 10 (PhoneController)
            ├─> Task 11 (CLI)
            └─> Task 12 (Integration Tests)
```

## Summary

| Task Group | Subtasks | Completed | Pending | Description |
|------------|----------|-----------|---------|-------------|
| Task 1 | 3 | 3 | 0 | Project setup and infrastructure |
| Task 2 | 6 | 5 | 1 | ADB client implementation |
| Task 3 | 6 | 5 | 1 | Device manager implementation |
| Task 4 | 8 | 7 | 1 | Device information and profiling |
| Task 5 | 6 | 5 | 1 | AT command interface |
| Task 6 | 7 | 6 | 1 | BIP monitoring |
| Task 7 | 6 | 5 | 1 | SMS-PP trigger |
| Task 8 | 7 | 6 | 1 | Network manager |
| Task 9 | 5 | 4 | 1 | Profile manager |
| Task 10 | 5 | 4 | 1 | Phone controller main class |
| Task 11 | 7 | 6 | 1 | CLI integration |
| Task 12 | 3 | 0 | 3 | Integration testing |

**Total: 12 task groups, 69 subtasks**
**Progress: 56 completed, 13 pending**

## Requirements Mapping

- **Requirement 1** (ADB Discovery): Tasks 1, 2, 3, 10, 12
- **Requirement 2** (Device Information): Tasks 1, 4, 10, 12
- **Requirement 3** (AT Command Interface): Tasks 1, 5, 10, 12
- **Requirement 4** (Network Configuration): Tasks 1, 4, 8, 10
- **Requirement 5** (BIP Event Monitoring): Tasks 1, 6, 10, 12
- **Requirement 6** (SMS-PP Trigger): Tasks 1, 7, 10
- **Requirement 7** (Logcat Streaming): Tasks 2, 6, 12
- **Requirement 8** (CLI Integration): Tasks 10, 11
- **Requirement 9** (Event Emission): Tasks 1, 3, 6, 10
- **Requirement 10** (Profile Management): Tasks 1, 4, 9, 10
