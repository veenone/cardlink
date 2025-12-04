# Implementation Tasks: Phone Controller

## Task Overview

This document breaks down the Phone Controller implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Core Infrastructure

_Leverage:_ Python project structure conventions, existing CardLink module organization patterns

_Requirements:_ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

_Prompt:_ Role: Python backend developer | Task: Set up the phone controller module structure with __init__.py, models.py, and exceptions.py. Define all data models using Python dataclasses (DeviceProfile, SIMProfile, NetworkProfile, FullProfile, BIPEvent, ATResponse) and enums (DeviceState, BIPEventType). Create custom exception hierarchy (PhoneControllerError, ADBNotFoundError, DeviceNotFoundError, DeviceUnauthorizedError, ATCommandError, RootRequiredError, TimeoutError). | Restrictions: Follow Python packaging best practices, use absolute imports, use @dataclass decorator with type hints | Success: Module structure exists with all data models and exceptions defined, can be imported correctly

- [x] 1.1. Create `src/cardlink/phone/` directory structure with `__init__.py`, `models.py`, and `exceptions.py` files
- [x] 1.2. Implement DeviceProfile, SIMProfile, NetworkProfile, FullProfile, BIPEvent, ATResponse dataclasses and DeviceState, BIPEventType enums
- [x] 1.3. Implement PhoneControllerError, ADBNotFoundError, DeviceNotFoundError, DeviceUnauthorizedError, ATCommandError, RootRequiredError, TimeoutError exception classes

### 2. ADB Client Implementation

_Leverage:_ Python subprocess module, synchronous execution for compatibility

_Requirements:_ 1, 7

_Prompt:_ Role: Python developer | Task: Implement ADBController class with ADB path auto-detection, synchronous command execution with timeout support, shell command execution, device listing via `adb devices`, file transfer (push/pull), and device property access. | Restrictions: Use subprocess.run with timeout, handle TimeoutError, decode bytes to UTF-8, provide clear error messages | Success: ADBController can execute ADB commands synchronously, list devices, transfer files, all with proper timeout handling

- [x] 2.1. Create `adb_controller.py` with ADBController and DeviceInfo dataclass
  - File: src/cardlink/phone/adb_controller.py
  - Implement DeviceInfo dataclass and ADBController class with ADB verification
  - Purpose: Provide synchronous ADB command execution for Android device control
  - _Leverage: subprocess module, dataclasses_
  - _Requirements: REQ-001 (ADB Discovery), REQ-007 (Synchronous execution)_
  - _Prompt: Role: Python developer | Task: Create ADBController class with ADB path verification (_verify_adb), DeviceInfo dataclass (serial, model, android_version, sdk_version, manufacturer), and initialization with optional serial number | Restrictions: Verify ADB is installed on initialization, raise RuntimeError if not found | Success: ADBController initializes correctly, verifies ADB availability_

- [x] 2.2. Implement `_adb()` method with subprocess handling and timeout support
  - File: src/cardlink/phone/adb_controller.py
  - Implement core ADB command execution with serial targeting and error handling
  - Purpose: Execute ADB commands with proper error handling and timeout
  - _Leverage: subprocess.run with capture_output and timeout_
  - _Requirements: REQ-007 (Command execution with timeout)_
  - _Prompt: Role: Python developer | Task: Implement _adb(*args, timeout=30) method that builds ADB command with optional -s serial flag, executes via subprocess.run, handles timeouts, and raises RuntimeError on errors | Restrictions: Log commands at debug level, capture both stdout and stderr, handle subprocess.TimeoutExpired | Success: Executes ADB commands with timeout, returns stdout, raises on errors_

- [x] 2.3. Implement `shell()` method for executing shell commands on device
  - File: src/cardlink/phone/adb_controller.py
  - Implement shell command execution wrapper
  - Purpose: Execute shell commands on Android device
  - _Leverage: _adb() method_
  - _Requirements: REQ-001 (Device shell access)_
  - _Prompt: Role: Python developer | Task: Implement shell(command, timeout=30) method that executes 'adb shell' commands and returns output | Restrictions: Use _adb() internally, maintain timeout parameter | Success: Executes shell commands successfully, returns command output_

- [x] 2.4. Implement `list_devices()` classmethod that parses `adb devices` output
  - File: src/cardlink/phone/adb_controller.py
  - Implement device discovery and listing
  - Purpose: List all connected Android devices
  - _Leverage: subprocess module, string parsing_
  - _Requirements: REQ-001 (ADB Discovery)_
  - _Prompt: Role: Python developer | Task: Implement list_devices() classmethod that runs 'adb devices', parses output (skipping header line), extracts serial numbers from lines containing '\tdevice' | Restrictions: Return empty list on errors, log device count at debug level | Success: Returns list of device serial numbers, handles no devices gracefully_

- [x] 2.5. Implement `get_device_info()` method to retrieve device information
  - File: src/cardlink/phone/adb_controller.py
  - Implement device information retrieval via getprop commands
  - Purpose: Get comprehensive device hardware and software information
  - _Leverage: shell() method, Android system properties_
  - _Requirements: REQ-002 (Device Information)_
  - _Prompt: Role: Python developer | Task: Implement get_device_info() that retrieves model (ro.product.model), manufacturer (ro.product.manufacturer), Android version (ro.build.version.release), SDK version (ro.build.version.sdk), and serial via getprop commands | Restrictions: Parse SDK version to int, handle missing properties gracefully | Success: Returns complete DeviceInfo object with all fields populated_

- [x] 2.6. Implement utility methods (screen control, file transfer, properties, reboot)
  - File: src/cardlink/phone/adb_controller.py
  - Implement helper methods for common device operations
  - Purpose: Provide convenient access to common ADB operations
  - _Leverage: _adb() and shell() methods_
  - _Requirements: REQ-001 (Device control), REQ-004 (File transfer)_
  - _Prompt: Role: Python developer | Task: Implement is_screen_on() (check mScreenState), wake_screen() (input keyevent WAKEUP), push_file(local, remote), pull_file(remote, local), get_property(prop), and reboot(mode=None) methods | Restrictions: Handle different Android versions for screen detection, log operations at debug level | Success: All utility methods work correctly, provide useful device control capabilities_

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

_Leverage:_ Android svc command, cmd wifi command for WiFi management, ip commands for network status

_Requirements:_ 4

_Prompt:_ Role: Python developer | Task: Implement NetworkManager class with WiFi control (enable/disable/connect), mobile data control (enable/disable), network status monitoring, and connectivity testing. | Restrictions: Handle different Android versions, provide fallback methods, handle network configuration timeouts | Success: Can control WiFi and mobile data, monitor network status, verify connectivity

- [x] 8.1. Create `network_manager.py` with NetworkManager, NetworkStatus, and WiFiNetwork dataclasses
  - File: src/cardlink/phone/network_manager.py
  - Implement NetworkStatus (wifi_enabled, connected, ssid, ip_address, gateway) and WiFiNetwork (ssid, bssid, signal, security) dataclasses
  - Purpose: Provide structured network state and WiFi network information
  - _Leverage: dataclasses, typing.Optional_
  - _Requirements: REQ-004 (Network status monitoring)_
  - _Prompt: Role: Python developer | Task: Create NetworkManager class with ADBController initialization, NetworkStatus dataclass (wifi_enabled, connected, ssid, ip_address, gateway), WiFiNetwork dataclass (ssid, bssid, signal, security) | Restrictions: Use Optional for nullable fields | Success: Data structures defined, NetworkManager initializes with ADB controller_

- [x] 8.2. Implement `get_status()` method to retrieve current network state
  - File: src/cardlink/phone/network_manager.py
  - Implement network status retrieval via dumpsys wifi and ip addr
  - Purpose: Get complete network status including WiFi state and IP configuration
  - _Leverage: dumpsys wifi, ip addr show wlan0, regex parsing_
  - _Requirements: REQ-004 (Network status)_
  - _Prompt: Role: Python developer | Task: Implement get_status() that queries 'dumpsys wifi' for WiFi state and SSID, 'ip addr show wlan0' for IP address, parses with regex, returns NetworkStatus | Restrictions: Handle disconnected state, check for '<unknown ssid>', gracefully handle errors | Success: Returns accurate network status, handles all connection states_

- [x] 8.3. Implement `enable_wifi()` and `disable_wifi()` methods
  - File: src/cardlink/phone/network_manager.py
  - Implement WiFi radio control via svc command
  - Purpose: Enable or disable WiFi radio
  - _Leverage: svc wifi enable/disable commands_
  - _Requirements: REQ-004 (WiFi control)_
  - _Prompt: Role: Python developer | Task: Implement enable_wifi() using 'svc wifi enable' with 2-second sleep for initialization, disable_wifi() using 'svc wifi disable' | Restrictions: Log operations, handle command failures | Success: WiFi can be enabled and disabled reliably_

- [x] 8.4. Implement `connect_wifi(ssid, password, security)` method
  - File: src/cardlink/phone/network_manager.py
  - Implement WiFi network connection with credential handling
  - Purpose: Connect to WiFi networks with password authentication
  - _Leverage: cmd wifi connect-network command (Android 10+)_
  - _Requirements: REQ-004 (WiFi connection)_
  - _Prompt: Role: Python developer | Task: Implement connect_wifi(ssid, password, security="WPA") using 'cmd wifi connect-network', wait up to 30 seconds for connection, verify via get_status() | Restrictions: Handle connection timeout (15s for command), verify SSID matches | Success: Connects to WiFi networks successfully, returns boolean result_

- [x] 8.5. Implement `disable_mobile_data()` method
  - File: src/cardlink/phone/network_manager.py
  - Implement mobile data control
  - Purpose: Disable mobile data to force WiFi usage
  - _Leverage: svc data disable command_
  - _Requirements: REQ-004 (Mobile data control)_
  - _Prompt: Role: Python developer | Task: Implement disable_mobile_data() using 'svc data disable', handle potential permission errors | Restrictions: Log warnings on failure, don't raise exceptions | Success: Disables mobile data when permissions allow_

- [x] 8.6. Implement `ping()` method to test network connectivity
  - File: src/cardlink/phone/network_manager.py
  - Implement connectivity testing via ping
  - Purpose: Verify network connectivity to hosts
  - _Leverage: ping command with count and timeout_
  - _Requirements: REQ-004 (Connectivity testing)_
  - _Prompt: Role: Python developer | Task: Implement ping(host, count=3) using 'ping -c count -W 2 host', check for 'packets transmitted' in output | Restrictions: Use 15s timeout, return boolean, handle command errors | Success: Tests connectivity reliably, returns accurate results_

- [x] 8.7. Implement helper methods (_get_gateway())
  - File: src/cardlink/phone/network_manager.py
  - Implement gateway IP detection
  - Purpose: Retrieve default gateway for network diagnostics
  - _Leverage: ip route command, regex parsing_
  - _Requirements: REQ-004 (Network diagnostics)_
  - _Prompt: Role: Python developer | Task: Implement _get_gateway() that runs 'ip route | grep default', extracts gateway IP via regex | Restrictions: Return None on errors or if not found | Success: Returns gateway IP when available_

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
