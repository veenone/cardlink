# Product Overview

## Product Purpose
**CardLink** is a comprehensive test platform for validating GlobalPlatform Amendment B (SCP81) implementations on UICC cards using real mobile phones and IoT modems as the test harness. The platform eliminates the need for production OTA infrastructure by providing simulated servers, device control interfaces, database-backed configuration management, and testing utilities, enabling realistic end-to-end validation without requiring access to live mobile networks or commercial OTA platforms.

## Target Users

| Persona | Need |
|---------|------|
| **UICC Developer** | Validate SCP81 implementation with real phone stack |
| **QA Engineer** | Automated regression testing with actual hardware |
| **MNO Integration Team** | Test OTA platform integration end-to-end |
| **Device Manufacturer** | Verify BIP/CAT implementation in handsets |
| **Certification Lab** | Pre-certification testing before formal submission |

### Pain Points Addressed
- No accessible test infrastructure (expensive commercial tools required)
- Complex end-to-end stack requiring mobile phone, network, and server coordination
- BIP connectivity issues with poorly documented UICC-initiated HTTPS connections
- Limited debugging in production systems that don't expose protocol-level details
- UICC provisioning complexity with manual and error-prone pre-configuration

## Key Features

1. **PSK-TLS Admin Server**: Fully compliant GP Amendment B RAM over HTTP server with PSK-TLS support for secure UICC communication
2. **Server Web Dashboard**: Web-based frontend for testers to monitor real-time communication, view and export communication logs, and perform manual RAM commands to UICC interactively
3. **Device Controllers**: Support for Android phones (via ADB) and IoT modems (via AT commands) for device management, network configuration, and BIP event monitoring
4. **UICC Provisioner**: PC/SC-based card pre-configuration for PSK keys, admin URLs, and trigger mechanisms
5. **Database-Backed Configuration**: SQLite/MySQL/PostgreSQL storage for device profiles, card configurations, session history, and communication logs
6. **Network Simulator Integration**: Connectivity with Amarisoft and similar network simulators via WebSocket/TCP
7. **SMS-PP Trigger Simulation**: Local SMS delivery simulation with PDU encoding for OTA triggers
8. **BIP Event Monitoring**: Real-time monitoring of Bearer Independent Protocol events
9. **E2E Test Orchestration**: Automated test execution coordinating server, devices, and UICC components

## Business Objectives

- Provide accessible SCP81 compliance testing without expensive commercial infrastructure
- Enable complete end-to-end validation using actual mobile devices and UICC cards
- Reduce time-to-market for UICC and OTA platform implementations
- Support pre-certification testing to reduce formal certification failures
- Create a standardized test framework for GlobalPlatform Amendment B implementations

## Success Metrics

- **Protocol Compliance**: Full SCP81 protocol compliance per GP Card Spec v2.2 Amendment B
- **Test Cycle Time**: Sub-5-second end-to-end test cycle time
- **Platform Support**: Support for Android 8.0+ phones via ADB and IoT modems via AT commands
- **Test Coverage**: Comprehensive test suites covering smoke, compliance, and E2E scenarios
- **Hardware Compatibility**: Validated on multiple phone models (Pixel, Samsung, OnePlus) and IoT modems (Quectel RG500Q-EU, EG25-G)

## Product Principles

1. **Real Hardware Testing**: Use actual mobile phones and UICC cards rather than simulators to ensure realistic validation
2. **Local-First**: All testing runs locally via USB/ADB without requiring network infrastructure or cloud dependencies
3. **Protocol Transparency**: Comprehensive logging across all protocol layers for debugging and analysis
4. **CLI + Web Dashboard**: Command-line interface for automation with integrated web dashboard for interactive monitoring and manual testing
5. **Modular Architecture**: Separate components (server, phone controller, provisioner) that can be used independently or together

## Monitoring & Visibility

- **Dashboard Type**: Web-based frontend integrated with the Admin Server
- **Real-time Updates**: Live communication monitoring via WebSocket, BIP event streaming, session tracking
- **Key Metrics Displayed**:
  - Active sessions and connection status
  - Real-time APDU command/response exchanges
  - Communication logs with timestamps and hex/decoded views
  - Test results and timing metrics
- **Interactive Features**:
  - Manual RAM command execution to UICC
  - Command builder for GP commands (GET STATUS, INSTALL, DELETE, etc.)
  - Response parsing and display
- **Sharing Capabilities**: Log exports (JSON, CSV), HTML reports, YAML test configurations

## Future Vision

### Version 1.0 Scope
- Android phones and IoT modems (Quectel) support
- SCP81 (HTTP-based OTA) only
- Local USB/Serial connection only
- CLI interface (`cardlink-server`, `cardlink-phone`, `cardlink-modem`, `cardlink-provision`, `cardlink-test`)
- Web dashboard for communication monitoring, TLS inspection, and manual RAM commands
- Database-backed configuration (SQLite default, MySQL/PostgreSQL optional)
- Network simulator integration (Amarisoft)
- Single device focus

### Potential Enhancements
- **iOS Support**: Extend phone controller for iOS devices
- **SCP80 Support**: Add SMS-based OTA testing (legacy protocol)
- **Remote Phone Control**: Cloud-based phone management for distributed testing
- **GUI Test Management**: Web-based dashboard for test configuration and results
- **Multi-Phone Parallel Testing**: Support for testing multiple devices simultaneously
- **Analytics Dashboard**: Historical test trends, compliance metrics, performance analysis
