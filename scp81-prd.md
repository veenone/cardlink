# Product Requirements Document (PRD)
# GlobalPlatform SCP81 UICC Test Platform

**Version:** 1.1  
**Date:** November 2025  
**Author:** Solutions Architecture Team  
**Project Codename:** GP-OTA-Tester

---

## 1. Executive Summary

### 1.1 Purpose
Develop a comprehensive test platform for validating GlobalPlatform Amendment B (SCP81) implementations on UICC cards using real mobile phones as the test harness. The platform eliminates the need for production OTA infrastructure by providing simulated servers, phone control interfaces, and testing utilities.

### 1.2 Vision
Enable UICC developers, MNOs, and card manufacturers to perform complete SCP81 compliance testing using actual mobile devices with pre-configured UICC cards, providing realistic end-to-end validation without requiring access to live mobile networks or commercial OTA platforms.

### 1.3 Target Test Configuration
```
┌─────────────┐      USB/ADB       ┌─────────────┐
│   Test PC   │◄──────────────────►│   Mobile    │
│             │                    │   Phone     │
│ ┌─────────┐ │    WiFi/Network    │ ┌─────────┐ │
│ │GP Server│◄├───────────────────►│ │  UICC   │ │
│ └─────────┘ │   (HTTPS/PSK-TLS)  │ │(SCP81)  │ │
│ ┌─────────┐ │                    │ └─────────┘ │
│ │Phone Ctl│ │                    │             │
│ └─────────┘ │                    └─────────────┘
└─────────────┘
```

### 1.4 Success Criteria
- Full SCP81 protocol compliance per GP Card Spec v2.2 Amendment B
- Support for Android phones via ADB interface
- Automated test execution with real UICC cards
- BIP (Bearer Independent Protocol) connection handling
- Push SMS trigger simulation
- Sub-5-second end-to-end test cycle time

---

## 2. Problem Statement

### 2.1 Current Challenges
1. **No accessible test infrastructure**: Testing SCP81 requires expensive commercial tools or production OTA servers
2. **Complex end-to-end stack**: Real testing needs mobile phone, network, and server coordination
3. **BIP connectivity issues**: Triggering UICC-initiated HTTPS connections is poorly documented
4. **Limited debugging**: Production systems don't expose protocol-level details
5. **UICC provisioning complexity**: Pre-configuring cards for test servers is manual and error-prone

### 2.2 Target Users
| Persona | Need |
|---------|------|
| UICC Developer | Validate SCP81 implementation with real phone stack |
| QA Engineer | Automated regression testing with actual hardware |
| MNO Integration Team | Test OTA platform integration end-to-end |
| Device Manufacturer | Verify BIP/CAT implementation in handsets |
| Certification Lab | Pre-certification testing before formal submission |

### 2.3 Test Environment Requirements
| Component | Specification |
|-----------|---------------|
| Mobile Phone | Android 8.0+ with USB debugging enabled |
| UICC Card | Pre-configured with test PSK keys and server URL |
| Network | WiFi AP or local network (phone and PC on same subnet) |
| Test PC | Linux/macOS/Windows with Python 3.9+, ADB installed |

---

## 3. Goals & Objectives

### 3.1 Primary Goals
1. **G1**: Implement fully compliant GP Amendment B RAM over HTTP server
2. **G2**: Provide ADB-based mobile phone control interface
3. **G3**: Support BIP connection triggering via multiple methods (SMS, AT, proactive)
4. **G4**: Enable UICC pre-provisioning with test credentials
5. **G5**: Deliver automated test execution with real hardware
6. **G6**: Comprehensive protocol logging across all layers

### 3.2 Non-Goals (Out of Scope v1.0)
- iOS device support - Android only for v1.0
- SCP80 (SMS-based OTA) - future version
- Remote phone control (cloud) - local USB only
- GUI-based test management - CLI first
- Multi-phone parallel testing - single device focus

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              TEST PC                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   CLI Layer  │    │  Test Runner │    │   Reporter   │              │
│  │  gp-server   │    │  Test Cases  │    │  Logs/HTML   │              │
│  │  gp-phone    │    │  Assertions  │    │              │              │
│  │  gp-test     │    │              │    │              │              │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘              │
│         │                   │                                           │
│  ┌──────┴───────────────────┴───────────────────────────────┐          │
│  │                    Service Layer                          │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │          │
│  │  │AdminServer  │  │PhoneControl │  │UICCProvisio │       │          │
│  │  │- HTTP/TLS   │  │- ADB Bridge │  │- Key Inject │       │          │
│  │  │- Sessions   │  │- AT Commands│  │- URL Config │       │          │
│  │  │- Scripts    │  │- SMS Trigger│  │- Card Setup │       │          │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘       │          │
│  └─────────┼────────────────┼───────────────────────────────┘          │
│            │                │                                           │
├────────────┼────────────────┼───────────────────────────────────────────┤
│   Network  │       USB      │                                           │
│   :8443    │       ADB      │                                           │
└────────────┼────────────────┼───────────────────────────────────────────┘
             │                │
             ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           MOBILE PHONE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   WiFi      │    │   Modem     │    │  ADB Daemon │                 │
│  │  Interface  │    │  (RIL/AT)   │    │             │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                   │                        │
│         │           ┌──────┴──────┐            │                        │
│         │           │  BIP/CAT    │            │                        │
│         │           │  Handler    │◄───────────┘                        │
│         │           └──────┬──────┘                                     │
│         │                  │                                            │
│         │           ┌──────┴──────┐                                     │
│         └──────────►│    UICC     │                                     │
│       HTTPS/TLS     │   (SCP81)   │                                     │
│                     │ ┌─────────┐ │                                     │
│                     │ │  ISD-R  │ │                                     │
│                     │ │ PSK Keys│ │                                     │
│                     │ │Admin URL│ │                                     │
│                     │ └─────────┘ │                                     │
│                     └─────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Connection Flow

```
1. Test Setup
   PC ──[ADB]──► Phone: Enable WiFi, connect to test network
   PC ──[ADB]──► Phone: Verify UICC present and configured

2. Trigger Admin Session  
   PC ──[ADB/AT]──► Phone ──► UICC: Send trigger (SMS-PP or EVENT_DOWNLOAD)
   
3. UICC Initiates Connection
   UICC ──[BIP OPEN CHANNEL]──► Phone Modem
   Phone ──[TCP/TLS-PSK]──► PC Server:8443
   
4. Admin Protocol Exchange
   Server ◄──[HTTPS POST]──► UICC (via Phone): C-APDU/R-APDU exchange
   
5. Session End
   UICC ──[BIP CLOSE CHANNEL]──► Phone
   Server: Log results, generate report
```

### 4.3 Component Descriptions

#### 4.3.1 Admin Server (Enhanced)
- PSK-TLS HTTPS server for SCP81
- Configurable to bind to specific network interface
- Support for phone's expected cipher suites
- Session timeout handling for mobile network delays

#### 4.3.2 Phone Controller (New)
- ADB-based device control
- AT command interface via ADB shell
- WiFi network management
- SMS sending capability (for triggers)
- Logcat monitoring for BIP events
- Screen capture for debugging

#### 4.3.3 UICC Provisioner (New)
- PC/SC interface for card pre-configuration
- PSK key injection
- Admin URL provisioning
- BIP APN configuration
- Trigger mechanism setup (SMS or event-based)

#### 4.3.4 SMS Gateway Simulator (New)
- Local SMS-PP delivery simulation
- AT+CMGS command generation
- PDU encoding for OTA triggers
- Support for concatenated SMS

---

## 5. Functional Requirements

### 5.1 Phone Controller (FR-500 Series)

#### FR-501: ADB Device Management
- **Priority**: P0 (Critical)
- **Description**: Manage Android phone via ADB
- **Acceptance Criteria**:
  - Device discovery and connection
  - USB debugging verification
  - Device info retrieval (model, Android version, IMEI)
  - Multiple device support (select by serial)
  - Connection health monitoring

#### FR-502: Network Configuration
- **Priority**: P0 (Critical)  
- **Description**: Configure phone network for test server access
- **Acceptance Criteria**:
  - WiFi enable/disable
  - WiFi network connection (SSID, password)
  - IP address retrieval
  - Connectivity verification (ping test server)
  - Mobile data disable (force WiFi)

#### FR-503: AT Command Interface
- **Priority**: P0 (Critical)
- **Description**: Send AT commands to modem via ADB
- **Acceptance Criteria**:
  - Access to `/dev/smd0` or equivalent modem device
  - AT command send/receive
  - Response parsing
  - Timeout handling
  - Common commands: AT+CPIN, AT+CSIM, AT+CGLA

#### FR-504: UICC Status Monitoring  
- **Priority**: P1 (High)
- **Description**: Monitor UICC state via phone
- **Acceptance Criteria**:
  - SIM presence detection
  - SIM ready state verification
  - ICCID retrieval
  - Carrier/PLMN information
  - Signal strength (if on network)

#### FR-505: BIP Event Monitoring
- **Priority**: P0 (Critical)
- **Description**: Monitor Bearer Independent Protocol events
- **Acceptance Criteria**:
  - Logcat filtering for STK/BIP events
  - OPEN CHANNEL detection
  - SEND DATA tracking
  - CLOSE CHANNEL detection
  - Channel status monitoring

#### FR-506: Trigger Mechanisms
- **Priority**: P0 (Critical)
- **Description**: Trigger UICC to initiate admin session
- **Acceptance Criteria**:
  - SMS-PP push trigger via AT commands
  - EVENT_DOWNLOAD (Data Available) trigger
  - Proactive UICC polling trigger
  - Timer-based trigger support
  - Manual trigger via STK menu (if available)

### 5.2 UICC Provisioning (FR-600 Series)

#### FR-601: Card Detection & Info
- **Priority**: P1 (High)
- **Description**: Detect and identify UICC card
- **Acceptance Criteria**:
  - PC/SC reader connection
  - ATR parsing
  - ICCID/IMSI retrieval
  - Card profile identification
  - GP registry enumeration

#### FR-602: PSK Key Provisioning
- **Priority**: P0 (Critical)
- **Description**: Configure PSK-TLS credentials
- **Acceptance Criteria**:
  - PUT KEY command for PSK keys
  - Support for 128/256-bit keys
  - Key version management
  - PSK identity configuration
  - Secure key injection workflow

#### FR-603: Admin URL Configuration
- **Priority**: P0 (Critical)
- **Description**: Set HTTP Admin server URL
- **Acceptance Criteria**:
  - STORE DATA for admin URL
  - Support for IP and hostname
  - Port configuration
  - Path configuration
  - URL validation

#### FR-604: BIP Configuration
- **Priority**: P1 (High)
- **Description**: Configure Bearer Independent Protocol settings
- **Acceptance Criteria**:
  - Default bearer selection (WiFi preferred)
  - APN configuration (if cellular)
  - Buffer size configuration
  - Connection timeout settings
  - Retry policy configuration

#### FR-605: Trigger Configuration
- **Priority**: P1 (High)
- **Description**: Configure session trigger mechanism
- **Acceptance Criteria**:
  - SMS trigger TAR configuration
  - Event trigger setup
  - Polling interval (if timer-based)
  - Trigger security settings

### 5.3 Enhanced Server (FR-100 Series - Updated)

#### FR-106: Mobile-Optimized TLS
- **Priority**: P0 (Critical)
- **Description**: TLS configuration for mobile clients
- **Acceptance Criteria**:
  - Support TLS 1.2 PSK cipher suites used by UICCs
  - Handle mobile network latency (longer timeouts)
  - Session resumption for reliability
  - Configurable MTU-aware chunking

#### FR-107: Network Interface Binding
- **Priority**: P1 (High)
- **Description**: Bind to specific network interface
- **Acceptance Criteria**:
  - Bind to WiFi interface IP
  - Avoid binding to VPN/other interfaces
  - Display accessible URL for phone
  - mDNS/Bonjour announcement (optional)

### 5.4 Test Framework (FR-300 Series - Updated)

#### FR-304: Hardware Test Cases
- **Priority**: P1 (High)
- **Description**: Test cases for real device testing
- **Acceptance Criteria**:
  - Phone connection prerequisites
  - UICC prerequisite checks
  - Network connectivity assertions
  - BIP event assertions
  - Timing assertions for mobile delays

#### FR-305: End-to-End Test Orchestration
- **Priority**: P0 (Critical)
- **Description**: Coordinate multi-component tests
- **Acceptance Criteria**:
  - Start server before triggering phone
  - Send trigger and wait for connection
  - Execute script and collect responses
  - Verify card state after test
  - Clean up and reset

---

## 6. Data Models (Updated)

```python
# Phone and UICC related models

@dataclass
class PhoneDevice:
    serial: str
    model: str
    android_version: str
    wifi_ip: Optional[str]
    sim_state: str  # READY, ABSENT, PIN_REQUIRED, etc.
    iccid: Optional[str]

@dataclass
class UICCConfig:
    iccid: str
    psk_identity: bytes
    psk_key: bytes
    admin_url: str
    trigger_type: TriggerType  # SMS_PP, EVENT_DOWNLOAD, POLLING
    bearer: BearerType  # WIFI, CELLULAR, DEFAULT

@dataclass  
class BIPChannel:
    channel_id: int
    bearer: str
    buffer_size: int
    state: ChannelState  # CLOSED, OPEN, LISTENING
    bytes_sent: int
    bytes_received: int

@dataclass
class TriggerConfig:
    type: TriggerType
    tar: bytes  # Target Application Reference (for SMS)
    sms_destination: str  # Usually the phone's own number
    event_list: List[int]  # Event download event list
    polling_interval: int  # Seconds

@dataclass
class TestEnvironment:
    server: AdminServer
    phone: PhoneDevice
    uicc_config: UICCConfig
    network_config: NetworkConfig
    trigger_config: TriggerConfig
```

---

## 7. Directory Structure (Updated)

```
gp-ota-tester/
├── src/
│   └── gp_ota_tester/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── server.py          # gp-server CLI
│       │   ├── phone.py           # gp-phone CLI (NEW)
│       │   ├── provision.py       # gp-provision CLI (NEW)
│       │   └── test.py            # gp-test CLI
│       ├── server/
│       │   ├── __init__.py
│       │   ├── admin_server.py
│       │   ├── tls_handler.py
│       │   └── session_manager.py
│       ├── phone/                  # NEW MODULE
│       │   ├── __init__.py
│       │   ├── adb_controller.py  # ADB device control
│       │   ├── at_interface.py    # AT command interface
│       │   ├── network_manager.py # WiFi/network control
│       │   ├── bip_monitor.py     # BIP event monitoring
│       │   ├── sms_trigger.py     # SMS-PP trigger
│       │   └── logcat_parser.py   # Android log parsing
│       ├── provision/              # NEW MODULE
│       │   ├── __init__.py
│       │   ├── card_manager.py    # PC/SC card access
│       │   ├── key_injector.py    # PSK key provisioning
│       │   ├── url_config.py      # Admin URL setup
│       │   └── bip_config.py      # BIP settings
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── apdu.py
│       │   ├── tlv.py
│       │   ├── gp_commands.py
│       │   ├── http_protocol.py
│       │   ├── sms_pdu.py         # SMS PDU encoding (NEW)
│       │   └── bip_commands.py    # BIP proactive cmds (NEW)
│       ├── testing/
│       │   ├── __init__.py
│       │   ├── runner.py
│       │   ├── assertions.py
│       │   ├── phone_fixtures.py  # Phone test fixtures (NEW)
│       │   └── e2e_orchestrator.py # End-to-end coordinator (NEW)
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           ├── network.py         # Network utilities (NEW)
│           └── adb_utils.py       # ADB helpers (NEW)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                       # End-to-end tests (NEW)
├── examples/
│   ├── test_suites/
│   │   ├── smoke.yaml
│   │   ├── compliance.yaml
│   │   └── e2e_basic.yaml        # E2E test suite (NEW)
│   └── configs/
│       ├── uicc_template.yaml    # UICC config template (NEW)
│       └── phone_setup.yaml      # Phone setup guide (NEW)
├── docs/
│   ├── setup_guide.md            # Hardware setup guide (NEW)
│   ├── uicc_provisioning.md      # Card provisioning guide (NEW)
│   └── troubleshooting.md        # Common issues (NEW)
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── CLAUDE.md
```

---

## 8. Implementation Phases (Updated)

### Phase 1: Foundation (Week 1-2)
**Milestone: M1 - Core Protocol**
- APDU/TLV classes
- GP command builders
- SMS PDU encoding
- Unit tests

### Phase 2: Server Core (Week 2-3)
**Milestone: M2 - Admin Server**
- PSK-TLS server
- HTTP protocol handler
- Session management
- Mobile-optimized timeouts

### Phase 3: Phone Controller (Week 3-4)
**Milestone: M3 - Phone Interface** ⭐ NEW
- ADB controller
- AT command interface
- Network management
- BIP event monitoring
- SMS trigger mechanism

### Phase 4: UICC Provisioning (Week 4-5)
**Milestone: M4 - Card Setup** ⭐ NEW
- PC/SC interface
- Key injection
- URL configuration
- BIP settings

### Phase 5: Test Framework (Week 5-6)
**Milestone: M5 - Automated Testing**
- Test case loader
- Phone fixtures
- E2E orchestrator
- Report generation

### Phase 6: Polish & Documentation (Week 6-7)
**Milestone: M6 - Release v1.0**
- CLI refinement
- Setup documentation
- Troubleshooting guide
- Example test suites

---

## 9. Test Environment Setup

### 9.1 Hardware Requirements
| Component | Requirement | Notes |
|-----------|-------------|-------|
| Android Phone | Android 8.0+, USB debugging | Pixel, Samsung, etc. |
| USB Cable | Data-capable USB cable | Not charge-only |
| UICC Card | GP 2.2 Amd B compliant | With SCP81 support |
| PC/SC Reader | USB smart card reader | For provisioning |
| WiFi Network | 2.4GHz or 5GHz | Phone & PC same network |

### 9.2 Software Requirements
| Component | Version | Installation |
|-----------|---------|--------------|
| Python | 3.9+ | System package manager |
| ADB | Latest | Android SDK Platform Tools |
| PC/SC Lite | 1.9+ | `apt install pcscd` (Linux) |
| OpenSSL | 1.1.1+ | System package manager |

### 9.3 Phone Preparation
```bash
# 1. Enable Developer Options
#    Settings > About Phone > Tap "Build Number" 7 times

# 2. Enable USB Debugging  
#    Settings > Developer Options > USB Debugging ON

# 3. Verify ADB connection
adb devices

# 4. Grant permissions when prompted on phone

# 5. Disable mobile data (force WiFi)
adb shell svc data disable
```

### 9.4 UICC Card Preparation
```bash
# 1. Insert card in PC/SC reader
gp-provision detect

# 2. Provision test credentials
gp-provision setup \
  --psk-identity "TEST_UICC_001" \
  --psk-key "000102030405060708090A0B0C0D0E0F" \
  --admin-url "https://192.168.1.100:8443/admin" \
  --trigger sms

# 3. Verify configuration
gp-provision verify

# 4. Insert card in phone
# 5. Verify phone detects SIM
adb shell getprop gsm.sim.state
# Should return: READY
```

---

## 10. Example Test Workflow

### 10.1 Basic Connectivity Test
```yaml
# examples/test_suites/e2e_basic.yaml
name: Basic E2E Connectivity
description: Verify server-phone-UICC communication

prerequisites:
  - phone_connected
  - sim_ready
  - wifi_connected
  - server_reachable

setup:
  - start_server:
      port: 8443
      psk_identity: "TEST_UICC_001"
      psk_key: "000102030405060708090A0B0C0D0E0F"
  - start_bip_monitor

tests:
  - id: E2E-001
    name: Trigger and Connect
    steps:
      - queue_script:
          commands:
            - get_status: {scope: 0x80}
      - send_trigger:
          type: sms_pp
          tar: "000001"
      - wait_for_connection:
          timeout: 30s
      - assert_response:
          sw: "9000"
    
  - id: E2E-002
    name: Install Application
    steps:
      - queue_script:
          commands:
            - install_for_load: {pkg_aid: "A0000001"}
            - load: {cap_file: "test.cap"}
            - install: {instance_aid: "A000000101"}
      - send_trigger
      - wait_for_connection
      - assert_all_success

teardown:
  - stop_server
  - collect_logs
```

### 10.2 CLI Usage
```bash
# Start server
gp-server start --port 8443 --psk-key $PSK_KEY &

# Connect to phone
gp-phone connect
gp-phone wifi connect "TestNetwork" "password123"
gp-phone sim status

# Run E2E test
gp-test run examples/test_suites/e2e_basic.yaml

# Interactive phone control
gp-phone shell
> trigger sms
> monitor bip
> status
```

---

## 11. Risks & Mitigations (Updated)

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ADB access varies by phone | High | Medium | Document tested phone models |
| AT modem access restricted | High | Medium | Root-based alternative, document requirements |
| BIP not working on some phones | High | Medium | Fallback to cellular bearer |
| WiFi connectivity unstable | Medium | Medium | Add retry logic, connection monitoring |
| UICC provisioning requires ADM keys | High | High | Document key requirements, provide test card specs |
| Phone USB disconnects | Medium | Low | Auto-reconnect, state recovery |

---

## 12. Appendix: Tested Phone Models

| Manufacturer | Model | Android | Notes |
|--------------|-------|---------|-------|
| Google | Pixel 6/7/8 | 12-14 | Recommended, full ADB access |
| Samsung | Galaxy S21+ | 12-13 | May need additional permissions |
| OnePlus | 9 Pro | 12 | Good AT command access |
| Xiaomi | Mi 11 | 12 | MIUI may restrict some features |

---

## 13. Appendix: UICC Requirements

The test UICC card must support:
- GlobalPlatform Card Spec 2.2 or later
- Amendment B (RAM over HTTP / SCP81)
- PSK-TLS cipher suites (TLS_PSK_WITH_AES_128_CBC_SHA minimum)
- Bearer Independent Protocol (BIP)
- Proactive UICC (OPEN CHANNEL, SEND DATA, CLOSE CHANNEL)
- CAT/STK for trigger handling

Recommended test cards:
- Gemalto IDPrime (with OTA option)
- G+D StarSign (OTA enabled)
- Valid (with HTTPS admin feature)

---

*End of PRD v1.1*
