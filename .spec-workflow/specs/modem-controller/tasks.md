# Implementation Tasks: Modem Controller

## Task Overview

This document breaks down the Modem Controller implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Core Infrastructure

_Leverage:_ Python package structure, dataclasses, type hints, exception inheritance
_Requirements:_ 1, 2, 3, 5, 8, 9
_Prompt:_ Role: Python package architect | Task: Create modem controller module structure with models, exceptions, and dependencies for serial communication | Restrictions: Follow Python package conventions, use relative imports, use @dataclass decorator with type hints | Success: Module structure exists with all data models and exceptions defined, can be imported correctly

- [x] 1.1. Create `src/cardlink/modem/` directory structure with `__init__.py`, `models.py`, `exceptions.py`, and `vendors/` subdirectory
- [x] 1.2. Implement dataclasses for ModemProfile, SIMProfile, NetworkProfile, FullModemProfile, ATResponse, ATResult, URCEvent, BIPEvent, and PortInfo
- [x] 1.3. Implement exception hierarchy: ModemControllerError, ModemNotFoundError, SerialPortError, ATCommandError, ATTimeoutError, CMEError, CMSError with error code lookup
- [x] 1.4. Add pyserial dependency to pyproject.toml with optional `[modem]` dependency group

### 2. Serial Client Implementation

_Leverage:_ pyserial Serial class, asyncio for timeout handling, pyserial.tools.list_ports
_Requirements:_ 1, 3
_Prompt:_ Role: Serial communication engineer | Task: Implement SerialClient class with async port operations, read/write methods, and port enumeration | Restrictions: Use pyserial library, support async operations, handle serial port errors, cross-platform compatibility | Success: SerialClient can open/close ports, read/write with timeouts, list available ports

- [x] 2.1. Create SerialClient class with constructor accepting port, baudrate, and timeout parameters
- [x] 2.2. Implement async open() and close() methods with serial port configuration (8N1, no flow control) and is_open property
- [x] 2.3. Implement async write(), read(), read_line(), and read_until() methods with timeout handling
- [x] 2.4. Implement static list_ports() method using pyserial.tools.list_ports, returning PortInfo objects
- [ ] 2.5. Write comprehensive unit tests for SerialClient covering port operations

### 3. AT Interface Implementation

_Leverage:_ asyncio Queue for command serialization, regex for response parsing, callback registry for URCs
_Requirements:_ 3, 5, 6, 9
_Prompt:_ Role: AT command protocol engineer | Task: Implement ATInterface class with command sending, response parsing, URC monitoring, and handler registration | Restrictions: Thread-safe command queue, support concurrent URC handling, handle command echo | Success: ATInterface sends commands, parses all response types, monitors URCs in background

- [x] 3.1. Create ATInterface class with SerialClient integration, URC handler registry, and command queue
- [x] 3.2. Implement async send_command() method with AT command formatting, response reading, and parsing
- [x] 3.3. Implement comprehensive AT response parsing for OK, ERROR, CME ERROR, and CMS ERROR results
- [x] 3.4. Implement send_raw() method for PDU mode data transmission
- [x] 3.5. Implement start_urc_monitoring() and stop_urc_monitoring() with background URC reading task
- [x] 3.6. Implement register_urc_handler() method with pattern matching and callback invocation
- [ ] 3.7. Write comprehensive unit tests for ATInterface covering command handling and parsing

### 4. URC Parser Implementation

_Leverage:_ Regular expressions, pattern-to-parser mapping, URCEvent dataclass
_Requirements:_ 5, 9, 10
_Prompt:_ Role: Protocol parser engineer | Task: Implement URCParser class with pattern registry, detection, and parsing for common URC types (CREG, CEREG, CPIN, QSTK, QIND) | Restrictions: Support both compiled and string patterns, extensible design, handle parse failures gracefully | Success: URCParser identifies URCs and extracts structured data for all common types

- [x] 4.1. Create URCParser class with pattern registry and common URC pattern definitions
- [x] 4.2. Implement is_urc() and parse() methods for URC detection and data extraction
- [x] 4.3. Implement register_pattern() method for custom URC pattern registration
- [x] 4.4. Implement parser functions for CREG, CEREG, CPIN, QSTK, and QIND URCs
- [ ] 4.5. Write comprehensive unit tests for URCParser covering all URC types

### 5. Modem Manager Implementation

_Leverage:_ EventEmitter for modem events, SerialClient.list_ports(), known USB VID:PID database, asyncio background task
_Requirements:_ 1, 2, 9
_Prompt:_ Role: Device manager engineer | Task: Implement ModemManager class with modem discovery, identification, and background monitoring for connect/disconnect events | Restrictions: Thread-safe registry access, support multiple simultaneous modems, handle scan failures gracefully | Success: ModemManager discovers modems, detects connects/disconnects within 5 seconds, emits events

- [x] 5.1. Create ModemManager class with EventEmitter integration and modem registry
- [x] 5.2. Implement scan_modems() method with USB filtering and modem identification
- [x] 5.3. Implement _identify_modem() method for vendor and model detection via ATI/AT+CGMM
- [x] 5.4. Implement start_monitoring() with background polling for modem connect/disconnect events
- [x] 5.5. Implement stop_monitoring() method with clean background task cancellation
- [ ] 5.6. Write comprehensive unit tests for ModemManager covering discovery and monitoring

### 6. Modem Information and Profiling

_Leverage:_ ATInterface for queries, TTL-based cache, AT+CGMI/CGMM/CGMR/CGSN, AT+CPIN/CCID/CIMI/CNUM, AT+CREG/COPS/CSQ/CGDCONT
_Requirements:_ 2
_Prompt:_ Role: Information retrieval engineer | Task: Implement ModemInfo class with caching and methods for modem, SIM, and network information retrieval, plus profile export and comparison | Restrictions: Thread-safe cache access, configurable TTL, handle missing responses gracefully | Success: ModemInfo returns complete profiles, exports to JSON, compares profiles for differences

- [x] 6.1. Create ModemInfo class with ATInterface integration and caching infrastructure (60s TTL)
- [x] 6.2. Implement get_modem_info() method querying modem identification AT commands
- [x] 6.3. Implement get_sim_info() method querying SIM/UICC identification AT commands
- [x] 6.4. Implement get_network_info() method querying network status AT commands (10s TTL)
- [x] 6.5. Implement get_full_profile(), export_json(), and compare_profiles() methods
- [ ] 6.6. Write comprehensive unit tests for ModemInfo covering all query methods

### 7. BIP Monitoring

_Leverage:_ ATInterface URC handlers, EventEmitter for BIP events, TLV parsing, vendor-specific AT commands
_Requirements:_ 5, 10
_Prompt:_ Role: STK event monitoring engineer | Task: Implement BIPMonitor class with STK notification enabling, URC handler registration, and proactive command parsing for BIP operations | Restrictions: Non-blocking event processing, detect modem vendor, handle invalid TLV gracefully | Success: BIPMonitor enables STK notifications, parses BIP commands, emits events with parameters

- [x] 7.1. Create BIPMonitor class with ATInterface and EventEmitter integration
- [x] 7.2. Implement enable_stk_notifications() method for vendor-specific STK enabling (AT+QSTK=1)
- [x] 7.3. Implement start() and stop() methods with URC handler registration
- [x] 7.4. Implement _process_stk_event() method parsing STK proactive commands (OPEN_CHANNEL, CLOSE_CHANNEL, SEND_DATA, RECEIVE_DATA)
- [ ] 7.5. Write comprehensive unit tests for BIPMonitor covering STK parsing

### 8. SMS Trigger Implementation

_Leverage:_ AT+CMGS command in PDU mode, GSM 03.40 PDU format, template parameter substitution
_Requirements:_ 6
_Prompt:_ Role: SMS protocol engineer | Task: Implement SMSTrigger class with PDU mode configuration, SMS sending, and trigger templates for OTA session initiation | Restrictions: Support SMS-PP Data Download type, handle PDU encoding, validate parameters | Success: SMSTrigger configures PDU mode, sends triggers via templates or raw PDU, returns message reference

- [x] 8.1. Create SMSTrigger class with ATInterface integration and trigger template definitions
- [x] 8.2. Implement configure_pdu_mode() method (AT+CMGF=0)
- [x] 8.3. Implement _send_pdu() method for SMS PDU transmission with AT+CMGS and Ctrl+Z
- [x] 8.4. Implement send_trigger() and send_raw_pdu() methods with template system
- [ ] 8.5. Write comprehensive unit tests for SMSTrigger covering PDU operations

### 9. Network Manager Implementation

_Leverage:_ AT+CGDCONT/CGACT/CGAUTH/CGPADDR commands, AT+CREG/CEREG, AT+QPING for Quectel
_Requirements:_ 4
_Prompt:_ Role: Network configuration engineer | Task: Implement NetworkManager class with APN configuration, PDP activation, registration checking, and connectivity testing | Restrictions: Support multiple PDP contexts, long timeout for activation (180s), detect modem vendor for ping | Success: NetworkManager configures APN, activates PDP, retrieves IP, checks registration, runs ping tests

- [x] 9.1. Create NetworkManager class with ATInterface integration
- [x] 9.2. Implement configure_apn() method for PDP context and authentication setup
- [x] 9.3. Implement activate_pdp(), deactivate_pdp(), and get_ip_address() methods
- [x] 9.4. Implement check_registration() method querying network registration status
- [x] 9.5. Implement ping() method using vendor-specific ping commands (AT+QPING)
- [ ] 9.6. Write comprehensive unit tests for NetworkManager covering network operations

### 10. Vendor-Specific Implementation

_Leverage:_ ABC (Abstract Base Class), Quectel AT command documentation, AT+QCSQ/QCFG/QSTK/QENG
_Requirements:_ 1, 10
_Prompt:_ Role: Object-oriented design engineer | Task: Implement base Modem abstract class and QuectelModem with vendor-specific signal parsing, band configuration, and STK enabling | Restrictions: Use ABC and abstractmethod decorators, handle different Quectel module variations | Success: Base class defines vendor interface, QuectelModem implements all vendor-specific features

- [x] 10.1. Create abstract base Modem class defining vendor interface with common and abstract methods
- [x] 10.2. Create QuectelModem class implementing get_detailed_signal(), configure_bands(), enable_stk(), get_qeng_info()
- [x] 10.3. Implement _parse_qcsq() for Quectel signal information parsing (LTE, NR5G)
- [ ] 10.4. Write comprehensive unit tests for QuectelModem

### 11. QXDM Interface (Optional)

_Leverage:_ Qualcomm DM protocol, USB interface enumeration, ISF/DLF format
_Requirements:_ 7
_Prompt:_ Role: Diagnostics interface engineer | Task: Implement QXDMInterface class with DM port detection, connection management, and diagnostic logging control | Restrictions: Optional feature with graceful degradation, Qualcomm-based modems only, cross-platform compatibility | Success: QXDMInterface detects DM port, connects/disconnects, captures and exports diagnostic logs

- [x] 11.1. Create QXDMInterface class with DM port detection
- [x] 11.2. Implement connect(), disconnect(), and is_available() methods
- [x] 11.3. Implement start_logging(), stop_logging(), and export_log() methods
- [x] 11.4. Implement get_dm_port() method for Quectel DM port identification

### 12. Modem Controller Main Class

_Leverage:_ ModemManager, EventEmitter, component composition, modem factory pattern
_Requirements:_ 1, 8, 9
_Prompt:_ Role: System integration engineer | Task: Implement ModemController main class integrating all components with modem discovery, instance caching, and event callback registration | Restrictions: Thread-safe access, support multiple modems, lazy initialization | Success: ModemController discovers modems, returns configured instances, registers callbacks for events

- [x] 12.1. Create ModemController main class integrating all components
- [x] 12.2. Implement get_modem() method with modem instance caching and component initialization
- [x] 12.3. Implement event callback registration methods (on_modem_connected, on_modem_disconnected, on_bip_event, on_error)
- [ ] 12.4. Write comprehensive unit tests for ModemController integration

### 13. CLI Integration

_Leverage:_ Click framework, ModemController API, tabulate/rich for formatting
_Requirements:_ 8
_Prompt:_ Role: CLI development engineer | Task: Implement cardlink-modem CLI with commands for listing, info, AT commands, triggers, monitoring, diagnostics, and profile management | Restrictions: Use Click framework, format output as table, handle no modems found, support --json flag | Success: All CLI commands work correctly with proper output formatting

- [x] 13.1. Create CLI module with `list` command showing connected modems
- [x] 13.2. Implement `info` command with filtering options (--modem, --sim, --network, --all, --json)
- [x] 13.3. Implement `at` command for direct AT command execution
- [x] 13.4. Implement `trigger` command with --template and --pdu options
- [x] 13.5. Implement `monitor` command for real-time BIP/URC monitoring with Ctrl+C handling
- [x] 13.6. Implement `diag` command for QXDM diagnostic capture
- [x] 13.7. Implement `profile` subcommands (save, load, compare, list, delete)
- [ ] 13.8. Write CLI integration tests

### 14. Integration Testing

_Leverage:_ pytest markers for hardware tests, real modem with SIM card
_Requirements:_ 1, 2, 3, 4
_Prompt:_ Role: Hardware integration test engineer | Task: Write integration tests for modem discovery, AT commands, modem info, and network operations with real hardware | Restrictions: Skip if no modem connected, use pytest-asyncio, configurable modem port via env var, restore original config after tests | Success: All tests pass with real modem, skip gracefully without hardware

- [ ] 14.1. Write modem integration tests for discovery and information retrieval with real device
- [ ] 14.2. Write network integration tests for registration, signal, APN, and PDP operations

## Task Dependencies

```
Task 1 (Setup)
    └─> Task 2 (SerialClient)
            └─> Task 3 (ATInterface)
                    ├─> Task 4 (URCParser)
                    ├─> Task 6 (ModemInfo)
                    ├─> Task 8 (SMSTrigger)
                    └─> Task 9 (NetworkManager)

Task 3 (ATInterface) + Task 4 (URCParser)
    └─> Task 5 (ModemManager)
    └─> Task 7 (BIPMonitor)

Task 10 (Vendor-Specific) ─> Uses Task 3 (ATInterface)

Task 11 (QXDM) ─> Independent (optional feature)

Task 5 (ModemManager) + Task 6 (ModemInfo) + Task 7 (BIPMonitor) + Task 8 (SMSTrigger) + Task 9 (NetworkManager)
    └─> Task 12 (ModemController)
            ├─> Task 13 (CLI)
            └─> Task 14 (Integration Tests)
```

## Summary

| Task Group | Subtasks | Completed | Pending | Description |
|------------|----------|-----------|---------|-------------|
| Task 1 | 4 | 4 | 0 | Project setup and infrastructure |
| Task 2 | 5 | 4 | 1 | Serial client implementation |
| Task 3 | 7 | 6 | 1 | AT interface implementation |
| Task 4 | 5 | 4 | 1 | URC parser implementation |
| Task 5 | 6 | 5 | 1 | Modem manager implementation |
| Task 6 | 6 | 5 | 1 | Modem information and profiling |
| Task 7 | 5 | 4 | 1 | BIP monitoring |
| Task 8 | 5 | 4 | 1 | SMS trigger implementation |
| Task 9 | 6 | 5 | 1 | Network manager implementation |
| Task 10 | 4 | 3 | 1 | Vendor-specific (Quectel) |
| Task 11 | 4 | 4 | 0 | QXDM interface (optional) |
| Task 12 | 4 | 3 | 1 | Modem controller main class |
| Task 13 | 8 | 7 | 1 | CLI integration |
| Task 14 | 2 | 0 | 2 | Integration testing |

**Total: 14 task groups, 71 subtasks**
**Progress: 58 completed, 13 pending**

## Requirements Mapping

- **Requirement 1** (Modem Discovery): Tasks 1, 2, 5, 10, 12
- **Requirement 2** (Device Information): Tasks 1, 5, 6
- **Requirement 3** (AT Command Interface): Tasks 1, 2, 3
- **Requirement 4** (Network Configuration): Tasks 9, 14
- **Requirement 5** (BIP Event Monitoring): Tasks 1, 3, 4, 7
- **Requirement 6** (SMS-PP Trigger): Tasks 3, 8
- **Requirement 7** (QXDM Integration): Task 11
- **Requirement 8** (CLI Integration): Tasks 1, 12, 13
- **Requirement 9** (Event Emission): Tasks 1, 3, 4, 5, 12
- **Requirement 10** (Quectel Features): Tasks 4, 7, 10
