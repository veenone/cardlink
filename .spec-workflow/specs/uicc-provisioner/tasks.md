# Tasks Document: UICC Provisioner

## Task Overview

This document breaks down the UICC Provisioner implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Dependencies

_Leverage:_ `pyproject.toml`, `README.md`, `tests/conftest.py`

_Requirements:_ REQ-001 (Project Structure), REQ-002 (Dependencies)

_Prompt:_ Role: Build System Engineer | Task: Set up the UICC provisioner package structure with all required dependencies including pyscard (>=2.0.0) and cryptography libraries. Create platform-specific installation documentation for PC/SC on Linux (pcscd), macOS (native), and Windows (WinSCard). Configure pytest fixtures for PC/SC mocking to enable testing without hardware. | Restrictions: Must maintain compatibility with Python 3.8+. Must not introduce platform-specific code in core modules. | Success: Package structure exists with all dependencies declared, installation docs cover all platforms, pytest fixtures allow hardware-independent testing.

- [ ] 1.1. Create `cardlink/provisioner/` package structure
- [ ] 1.2. Add pyscard dependency to pyproject.toml with version constraint (>=2.0.0)
- [ ] 1.3. Add cryptography dependency for SCP02/SCP03 operations
- [ ] 1.4. Create platform-specific installation docs (pcscd for Linux, native for macOS/Windows)
- [ ] 1.5. Add pytest fixtures for PC/SC mocking

### 2. PC/SC Client Implementation

_Leverage:_ `cardlink/provisioner/pcsc_client.py`, `smartcard` module documentation

_Requirements:_ REQ-003 (PC/SC Client), REQ-004 (Reader Management), REQ-005 (Card Connection)

_Prompt:_ Role: Smart Card Interface Developer | Task: Implement a robust PC/SC client class that handles reader enumeration, card connection with T=0/T=1 protocol support, APDU transmission with GET RESPONSE handling, and card monitoring using observers. Ensure thread-safe operations with proper resource cleanup and connection state tracking. | Restrictions: Must handle platform differences transparently. Must not block indefinitely on card operations. Must properly release resources on disconnect. | Success: PCSCClient can list readers, connect to cards with both protocols, transmit APDUs with automatic GET RESPONSE handling, monitor card insertion/removal events, and all operations are thread-safe with comprehensive unit tests.

- [ ] 2.1. Create `pcsc_client.py` with PCSCClient class
- [ ] 2.2. Implement `list_readers()` using smartcard.System.readers()
- [ ] 2.3. Implement `connect(reader_name, protocol)` with T=0/T=1 support
- [ ] 2.4. Implement `disconnect()` with proper resource cleanup
- [ ] 2.5. Implement `transmit(apdu)` with GET RESPONSE handling for T=0
- [ ] 2.6. Create ReaderInfo and CardInfo dataclasses
- [ ] 2.7. Implement card monitoring with CardMonitor and CardObserver
- [ ] 2.8. Add `start_monitoring()` and `stop_monitoring()` methods
- [ ] 2.9. Implement thread-safe transmit with threading.Lock
- [ ] 2.10. Add connection state tracking and validation
- [ ] 2.11. Write unit tests for PCSCClient with mocked smartcard module

### 3. ATR Parser Implementation

_Leverage:_ `cardlink/provisioner/atr_parser.py`, ISO 7816-3 specification

_Requirements:_ REQ-006 (ATR Parsing), REQ-007 (Card Type Detection)

_Prompt:_ Role: Smart Card Protocol Analyst | Task: Implement an ATR parser that extracts and interprets Answer-To-Reset bytes according to ISO 7816-3. Parse TS, T0, protocol bytes, historical bytes, and detect card type (UICC/USIM/eUICC) using pattern matching. Extract protocol (T=0/T=1) and convention (direct/inverse) information. | Restrictions: Must strictly follow ISO 7816-3 ATR structure. Must not assume fixed ATR lengths. Must handle malformed ATRs gracefully. | Success: ATRParser correctly extracts all ATR components, identifies common UICC card types, detects protocol and convention, with unit tests covering sample ATRs from major vendors.

- [ ] 3.1. Create `atr_parser.py` with ATRParser class
- [ ] 3.2. Implement `parse(atr)` to extract TS, T0, protocol bytes
- [ ] 3.3. Implement historical bytes extraction
- [ ] 3.4. Implement `_identify_card_type()` with pattern matching for UICC/USIM/eUICC
- [ ] 3.5. Add protocol detection (T=0, T=1) from TD bytes
- [ ] 3.6. Add convention detection (direct/inverse)
- [ ] 3.7. Write unit tests with sample ATRs from common UICC vendors

### 4. APDU Interface Implementation

_Leverage:_ `cardlink/provisioner/apdu_interface.py`, ISO 7816-4 specification, GlobalPlatform specification

_Requirements:_ REQ-008 (APDU Interface), REQ-009 (Status Word Decoding), REQ-010 (Command Helpers)

_Prompt:_ Role: APDU Protocol Developer | Task: Create a comprehensive APDU interface with command construction, response parsing, and status word decoding. Implement APDUCommand and APDUResponse dataclasses with proper Lc/Le handling. Create SWDecoder with comprehensive STATUS_WORDS dictionary covering ISO 7816 and GlobalPlatform status words. Provide helper methods for common operations like SELECT, READ BINARY, UPDATE BINARY, VERIFY PIN, and GET STATUS. | Restrictions: Must follow ISO 7816-4 APDU structure exactly. Must handle both case 1-4 APDUs correctly. Must not expose raw bytes to higher layers unnecessarily. | Success: APDU interface correctly constructs all APDU cases, parses responses with decoded status messages, provides convenient helpers for common operations, with comprehensive unit tests.

- [ ] 4.1. Create `apdu_interface.py` with APDUCommand and APDUResponse dataclasses
- [ ] 4.2. Implement INS enum with all common instruction bytes
- [ ] 4.3. Implement APDUCommand.to_bytes() with Lc/Le handling
- [ ] 4.4. Implement APDUResponse properties (sw, is_success, status_message)
- [ ] 4.5. Create SWDecoder class with STATUS_WORDS dictionary
- [ ] 4.6. Implement SWDecoder.decode() with range handling (61xx, 6Cxx, 63Cx)
- [ ] 4.7. Create APDUInterface class with send() method
- [ ] 4.8. Implement `send_raw(apdu_hex)` for raw hex input
- [ ] 4.9. Implement `select_by_aid(aid)` helper
- [ ] 4.10. Implement `select_by_path(path)` helper
- [ ] 4.11. Implement `read_binary(offset, length)` helper
- [ ] 4.12. Implement `update_binary(offset, data)` helper
- [ ] 4.13. Implement `verify_pin(pin, pin_ref)` helper
- [ ] 4.14. Implement `get_status(p1, p2, aid_filter)` for GP commands
- [ ] 4.15. Write unit tests for APDU construction and response parsing

### 5. TLV Parser Implementation

_Leverage:_ `cardlink/provisioner/tlv_parser.py`, ASN.1 BER encoding rules

_Requirements:_ REQ-011 (TLV Parsing), REQ-012 (TLV Construction)

_Prompt:_ Role: Data Structure Parser Developer | Task: Implement a robust TLV (Tag-Length-Value) parser supporting both simple and constructed TLV structures. Handle 1-byte and 2-byte tags, length parsing in short form and long form (81, 82), and recursive parsing for nested structures. Provide both parsing and construction methods. | Restrictions: Must handle malformed TLV gracefully. Must support indefinite length encoding. Must not assume tag ordering. | Success: TLVParser correctly parses simple and nested TLV structures, handles all length encodings, constructs valid TLV data, with comprehensive unit tests.

- [ ] 5.1. Create `tlv_parser.py` with TLVParser class
- [ ] 5.2. Implement `parse(data)` with 1-byte and 2-byte tag support
- [ ] 5.3. Implement length parsing (short form, 81, 82)
- [ ] 5.4. Implement `build(tag, value)` for TLV construction
- [ ] 5.5. Add recursive parsing for nested TLV structures
- [ ] 5.6. Write unit tests with various TLV structures

### 6. Security Domain Manager Implementation

_Leverage:_ `cardlink/provisioner/secure_domain.py`, GlobalPlatform specification, `apdu_interface.py`, `tlv_parser.py`

_Requirements:_ REQ-013 (Security Domain Management), REQ-014 (ISD Operations), REQ-015 (Application Management)

_Prompt:_ Role: GlobalPlatform Security Domain Developer | Task: Implement Security Domain manager for GlobalPlatform card operations including ISD selection, application listing via GET STATUS, application installation, deletion, and key management. Parse GET STATUS responses using TLV parser to extract SecurityDomainInfo including AID, lifecycle state, and privileges. Support INSTALL [for install] and DELETE commands with cascade option. | Restrictions: Must follow GlobalPlatform Card Specification v2.3+. Must validate lifecycle state transitions. Must not allow operations in incorrect states. | Success: SecureDomainManager can select ISD/SSD, list applications with full details, install and delete applications correctly, manage keys, with unit tests covering all operations.

- [ ] 6.1. Create `secure_domain.py` with SecureDomainManager class
- [ ] 6.2. Define ISD_AID constant (A000000151000000)
- [ ] 6.3. Implement LifeCycleState enum
- [ ] 6.4. Create SecurityDomainInfo dataclass
- [ ] 6.5. Implement `select_isd()` method
- [ ] 6.6. Implement `select_sd(aid)` method
- [ ] 6.7. Implement `get_status_isd()` with response parsing
- [ ] 6.8. Implement `get_status_apps()` for application listing
- [ ] 6.9. Implement `_parse_get_status_response()` TLV parser
- [ ] 6.10. Implement `install_for_install()` GP command
- [ ] 6.11. Implement `delete(aid, cascade)` GP command
- [ ] 6.12. Implement `put_key()` GP command
- [ ] 6.13. Write unit tests for SD operations

### 7. SCP02 Secure Channel Implementation

_Leverage:_ `cardlink/provisioner/scp02.py`, GlobalPlatform SCP02 specification, `cryptography` library

_Requirements:_ REQ-016 (SCP02/SCP03 Secure Channel), REQ-017 (Session Key Derivation), REQ-018 (Mutual Authentication), REQ-019 (C-MAC Calculation)

_Prompt:_ Role: Cryptographic Protocol Developer | Task: Implement SCP02 secure channel protocol according to GlobalPlatform specification. Handle INITIALIZE UPDATE and EXTERNAL AUTHENTICATE commands with Triple-DES session key derivation, card and host cryptogram calculation for mutual authentication, and C-MAC generation for command authentication. Support MAC chaining and ISO 9797-1 Method 2 padding. | Restrictions: Must implement cryptographic operations correctly per specification. Must verify card cryptogram before proceeding. Must not expose session keys. Must use constant-time operations where applicable. | Success: SCP02 implementation establishes secure channel with test keys, performs mutual authentication correctly, adds C-MAC to commands, verified with test vectors from GlobalPlatform specification.

- [ ] 7.1. Create `scp02.py` with SCP02 class
- [ ] 7.2. Create SCPKeys dataclass with enc, mac, dek fields
- [ ] 7.3. Implement `default_test_keys()` class method
- [ ] 7.4. Implement `initialize()` with INITIALIZE UPDATE command
- [ ] 7.5. Parse INITIALIZE UPDATE response (key diversification, sequence counter, card challenge, cryptogram)
- [ ] 7.6. Implement `_derive_session_keys()` using Triple-DES CBC
- [ ] 7.7. Implement `_verify_card_cryptogram()` for mutual authentication
- [ ] 7.8. Implement `_calculate_host_cryptogram()`
- [ ] 7.9. Implement EXTERNAL AUTHENTICATE with C-MAC
- [ ] 7.10. Implement `_add_cmac()` for command MAC calculation
- [ ] 7.11. Implement `_pad_iso9797()` ISO 9797-1 Method 2 padding
- [ ] 7.12. Implement `send()` for secured command transmission
- [ ] 7.13. Add MAC chaining support
- [ ] 7.14. Write unit tests with test vectors

### 8. SCP03 Secure Channel Implementation

_Leverage:_ `cardlink/provisioner/scp03.py`, GlobalPlatform SCP03 specification, `cryptography` library

_Requirements:_ REQ-016 (SCP02/SCP03 Secure Channel), REQ-017 (Session Key Derivation), REQ-018 (Mutual Authentication), REQ-020 (AES-CMAC)

_Prompt:_ Role: Advanced Cryptographic Protocol Developer | Task: Implement SCP03 secure channel protocol using AES instead of Triple-DES. Handle INITIALIZE UPDATE with AES-based session key derivation using KDF from NIST SP 800-108, card and host cryptogram verification using AES-CMAC, EXTERNAL AUTHENTICATE, and command protection with AES C-MAC and optional C-ENC. Maintain encryption counter for command encryption. | Restrictions: Must follow GlobalPlatform SCP03 specification exactly. Must use AES-128 correctly. Must verify card cryptogram before authentication. Must handle counter overflow. Must not expose session keys. | Success: SCP03 implementation establishes AES-based secure channel, performs mutual authentication with AES-CMAC, protects commands with MAC and optional encryption, verified with SCP03 test vectors.

- [ ] 8.1. Create `scp03.py` with SCP03 class
- [ ] 8.2. Implement `initialize()` with AES-based key derivation
- [ ] 8.3. Implement INITIALIZE UPDATE for SCP03
- [ ] 8.4. Implement session key derivation using AES-CMAC
- [ ] 8.5. Implement card cryptogram verification (AES-CMAC)
- [ ] 8.6. Implement host cryptogram calculation
- [ ] 8.7. Implement EXTERNAL AUTHENTICATE with AES C-MAC
- [ ] 8.8. Implement `send()` with C-MAC and optional C-ENC
- [ ] 8.9. Add counter management for encryption
- [ ] 8.10. Write unit tests with SCP03 test vectors

### 9. PSK Configuration Implementation

_Leverage:_ `cardlink/provisioner/psk_config.py`, `apdu_interface.py`, `key_manager.py`

_Requirements:_ REQ-021 (PSK Configuration), REQ-022 (Identity Management), REQ-023 (Key Storage)

_Prompt:_ Role: Security Configuration Developer | Task: Implement Pre-Shared Key (PSK) configuration system for storing TLS-PSK identity and key material on UICC. Support PSK generation with configurable key sizes, loading from hex strings, and writing to card files (EF_PSK_ID for identity, EF_PSK_KEY for key). Implement read and verify operations to validate stored configuration. Handle file creation if files don't exist. | Restrictions: Must write PSK_KEY only through secure channel. Must validate key sizes. Must not log key material. Must handle vendor-specific file locations. | Success: PSKConfiguration can generate random PSK, store identity and key on card, read current configuration, verify stored values match expected, with unit tests covering all operations.

- [ ] 9.1. Create `psk_config.py` with PSKConfiguration dataclass
- [ ] 9.2. Implement `generate(identity, key_size)` class method
- [ ] 9.3. Implement `from_hex(identity, key_hex)` class method
- [ ] 9.4. Create PSKConfig class with EF_PSK_ID and EF_PSK_KEY constants
- [ ] 9.5. Implement `configure(psk)` to write identity and key
- [ ] 9.6. Implement `_write_psk_identity()` with file selection and update
- [ ] 9.7. Implement `_write_psk_key()` with secure channel requirement
- [ ] 9.8. Implement `read_configuration()` to read current PSK identity
- [ ] 9.9. Implement `verify(psk)` to compare configurations
- [ ] 9.10. Implement `_create_psk_file()` for file creation if needed
- [ ] 9.11. Write unit tests for PSK operations

### 10. Key Manager Implementation

_Leverage:_ `cardlink/provisioner/key_manager.py`, `secrets` module, `cryptography.hazmat` library

_Requirements:_ REQ-024 (Key Management), REQ-025 (Key Derivation), REQ-026 (Secure Operations)

_Prompt:_ Role: Cryptographic Key Management Developer | Task: Implement key management utilities including cryptographically secure random key generation using secrets module, HKDF-based key derivation for creating derived keys, constant-time key comparison to prevent timing attacks, and secure memory erasure for sensitive key material. | Restrictions: Must use cryptographically secure random sources only. Must implement constant-time comparison correctly. Must not leave key material in memory longer than necessary. Must not log key values. | Success: KeyManager generates cryptographically secure random keys, derives keys using HKDF, compares keys in constant time, securely erases key material, with unit tests verifying correct operation.

- [ ] 10.1. Create `key_manager.py` with KeyManager class
- [ ] 10.2. Implement `generate_random_key(size)` using secrets module
- [ ] 10.3. Implement `derive_key()` using HKDF
- [ ] 10.4. Implement `secure_compare()` for constant-time comparison
- [ ] 10.5. Implement `secure_erase()` for memory clearing
- [ ] 10.6. Write unit tests for key operations

### 11. URL Configuration Implementation

_Leverage:_ `cardlink/provisioner/url_config.py`, `apdu_interface.py`, `tlv_parser.py`, `urllib.parse`

_Requirements:_ REQ-027 (URL/Trigger/BIP Configuration), REQ-028 (URL Storage), REQ-029 (URL Validation)

_Prompt:_ Role: Configuration Management Developer | Task: Implement URL configuration system for storing remote server URLs on UICC for profile downloads. Parse URLs using urllib.parse, validate scheme and length constraints, encode to TLV format for card storage in EF_ADMIN_URL. Provide read and validation operations to verify stored URLs. | Restrictions: Must validate URL format before storage. Must enforce maximum URL length limits. Must handle URL encoding correctly. Must not allow invalid schemes. | Success: URLConfiguration parses and validates URLs, converts to TLV format, stores on card, reads stored configuration, validates format, with unit tests covering various URL formats.

- [ ] 11.1. Create `url_config.py` with URLConfiguration dataclass
- [ ] 11.2. Implement `from_url(url)` parser using urllib.parse
- [ ] 11.3. Implement URL validation (scheme, length)
- [ ] 11.4. Implement `to_tlv()` for card storage encoding
- [ ] 11.5. Create URLConfig class with EF_ADMIN_URL constant
- [ ] 11.6. Implement `configure(config)` to store URL
- [ ] 11.7. Implement `read_configuration()` to read current URL
- [ ] 11.8. Implement `validate(url)` format checker
- [ ] 11.9. Write unit tests for URL operations

### 12. Trigger Configuration Implementation

_Leverage:_ `cardlink/provisioner/trigger_config.py`, `apdu_interface.py`, `tlv_parser.py`

_Requirements:_ REQ-027 (URL/Trigger/BIP Configuration), REQ-030 (SMS Trigger), REQ-031 (Poll Trigger), REQ-032 (Trigger Management)

_Prompt:_ Role: OTA Trigger Configuration Developer | Task: Implement trigger configuration system supporting SMS-PP and polling triggers for remote profile provisioning. Create SMSTriggerConfig with TAR, originating address, KIc, KID, and counter fields. Create PollTriggerConfig with interval and enabled flag. Encode configurations to TLV format for storage in EF_TRIGGER_CONFIG. Support reading, disabling, and parsing trigger configurations. | Restrictions: Must validate TAR format. Must validate SMS security parameters. Must enforce reasonable polling intervals. Must handle multiple trigger types. | Success: TriggerConfiguration supports SMS and poll triggers, encodes to TLV, stores on card, reads and parses configurations, enables/disables triggers, with unit tests covering all trigger types.

- [ ] 12.1. Create `trigger_config.py` with TriggerType enum
- [ ] 12.2. Create SMSTriggerConfig dataclass (TAR, originating address, KIc, KID, counter)
- [ ] 12.3. Create PollTriggerConfig dataclass (interval, enabled)
- [ ] 12.4. Create TriggerConfiguration dataclass
- [ ] 12.5. Create TriggerConfig class with EF_TRIGGER_CONFIG constant
- [ ] 12.6. Implement `configure_sms_trigger(config)` with TLV encoding
- [ ] 12.7. Implement `configure_poll_trigger(config)`
- [ ] 12.8. Implement `read_configuration()` to parse all triggers
- [ ] 12.9. Implement `disable_trigger(trigger_type)`
- [ ] 12.10. Implement `_parse_trigger_config()` TLV parser
- [ ] 12.11. Write unit tests for trigger operations

### 13. BIP Configuration Implementation

_Leverage:_ `cardlink/provisioner/bip_config.py`, `apdu_interface.py`, `tlv_parser.py`, ETSI TS 102 223

_Requirements:_ REQ-027 (URL/Trigger/BIP Configuration), REQ-033 (BIP Configuration), REQ-034 (APN Encoding), REQ-035 (Bearer Support)

_Prompt:_ Role: Bearer Independent Protocol Developer | Task: Implement BIP (Bearer Independent Protocol) configuration for managing data connections from UICC. Support bearer type selection (GPRS, UTRAN, etc.), APN configuration with DNS label encoding per RFC 1035, buffer size and timeout settings. Encode to TLV for storage in EF_BIP_CONFIG. Check terminal profile to verify BIP support before configuration. | Restrictions: Must encode APN in DNS label format correctly. Must validate bearer type against terminal capabilities. Must enforce buffer size limits. Must check terminal profile for BIP support. | Success: BIPConfiguration supports bearer selection, encodes APN correctly in DNS label format, stores configuration on card, reads current settings, validates terminal support, with unit tests covering different bearer types and APNs.

- [ ] 13.1. Create `bip_config.py` with BearerType enum
- [ ] 13.2. Create BIPConfiguration dataclass (bearer, APN, buffer, timeout)
- [ ] 13.3. Implement `to_tlv()` with APN DNS label encoding
- [ ] 13.4. Implement `_encode_apn()` for DNS label format
- [ ] 13.5. Create BIPConfig class with EF_BIP_CONFIG constant
- [ ] 13.6. Implement `configure(config)` to store BIP settings
- [ ] 13.7. Implement `read_configuration()` to read current settings
- [ ] 13.8. Implement `check_terminal_support()` to read terminal profile
- [ ] 13.9. Implement `_decode_apn()` for reading stored APN
- [ ] 13.10. Write unit tests for BIP operations

### 14. Profile Manager Implementation

_Leverage:_ `cardlink/provisioner/profile_manager.py`, `psk_config.py`, `url_config.py`, `trigger_config.py`, `bip_config.py`, `apdu_interface.py`

_Requirements:_ REQ-036 (Profile Management), REQ-037 (Profile Export/Import), REQ-038 (Profile Comparison), REQ-039 (Profile Application)

_Prompt:_ Role: Card Profile Management Developer | Task: Implement profile manager for capturing, comparing, and applying complete UICC configurations. Create CardProfile dataclass containing ICCID, ATR, PSK, URL, trigger, and BIP configurations. Support JSON export/import with optional key inclusion, profile comparison to generate diffs, and profile application to provision cards. Include ICCID BCD decoding and card information extraction. | Restrictions: Must not export keys by default. Must validate profile before application. Must check card compatibility (ICCID pattern). Must handle partial profiles gracefully. | Success: ProfileManager saves complete card profiles to JSON, loads profiles from files, compares profiles showing differences, applies profiles to cards with validation, handles ICCID correctly, with unit tests covering all operations.

- [ ] 14.1. Create `profile_manager.py` with CardProfile dataclass
- [ ] 14.2. Implement `to_json(include_keys)` export method
- [ ] 14.3. Implement `from_json(json_str)` class method
- [ ] 14.4. Create ProfileManager class with all config dependencies
- [ ] 14.5. Implement `save_profile(name, include_keys)` to capture card state
- [ ] 14.6. Implement `_get_card_info()` to read ICCID and ATR
- [ ] 14.7. Implement `_decode_iccid()` BCD decoder
- [ ] 14.8. Implement `load_profile(profile)` to generate diff
- [ ] 14.9. Implement `apply_profile(profile, psk_key)` to provision card
- [ ] 14.10. Implement `compare_profiles(profile1, profile2)`
- [ ] 14.11. Implement `export_profile(profile, path, include_keys)`
- [ ] 14.12. Implement `import_profile(path)` file loader
- [ ] 14.13. Write unit tests for profile operations

### 15. Event Emitter Implementation

_Leverage:_ `cardlink/provisioner/event_emitter.py`, `threading`, `queue`

_Requirements:_ REQ-040 (Event System), REQ-041 (Event Types), REQ-042 (Event Handlers)

_Prompt:_ Role: Event System Developer | Task: Implement event emitter system for notifying external code of provisioner operations. Create ProvisionerEvent dataclass with type, timestamp, and data fields. Implement EventEmitter with handler registration (on/off), event emission with async queue, wildcard handler support, and thread-safe operations. Support pending event retrieval for queue draining. | Restrictions: Must be thread-safe for concurrent operations. Must not block on event emission. Must handle handler exceptions gracefully. Must support handler removal. | Success: EventEmitter registers and removes handlers correctly, emits events to all registered handlers including wildcards, queues events asynchronously, operates safely across threads, with unit tests covering all scenarios.

- [ ] 15.1. Create `event_emitter.py` with ProvisionerEvent dataclass
- [ ] 15.2. Create EventEmitter class with handler registry
- [ ] 15.3. Implement `on(event_type, handler)` registration
- [ ] 15.4. Implement `off(event_type, handler)` removal
- [ ] 15.5. Implement `emit(event_type, data)` with async queue
- [ ] 15.6. Add wildcard handler support ('*')
- [ ] 15.7. Implement `get_pending_events()` for queue drain
- [ ] 15.8. Add thread-safe handler management
- [ ] 15.9. Write unit tests for event emission

### 16. APDU Logger Implementation

_Leverage:_ `cardlink/provisioner/apdu_logger.py`, `apdu_interface.py`

_Requirements:_ REQ-043 (APDU Logging), REQ-044 (Log Export), REQ-045 (Log Management)

_Prompt:_ Role: Diagnostic Logging Developer | Task: Implement APDU logger for debugging and analysis of card communication. Create APDULogEntry dataclass with timestamp, direction, APDU bytes, and decoded information. Support command and response logging with human-readable decoding, configurable entry limits with overflow handling, log retrieval, export to JSON and CSV formats, and enable/disable toggles. | Restrictions: Must limit memory usage with max entries. Must handle high-frequency logging efficiently. Must not interfere with APDU transmission. Must provide useful decoded information. | Success: APDULogger captures all APDU exchanges with timestamps, decodes commands and responses for readability, limits entries to prevent memory issues, exports to JSON/CSV formats, can be enabled/disabled, with unit tests covering all operations.

- [ ] 16.1. Create `apdu_logger.py` with APDULogEntry dataclass
- [ ] 16.2. Create APDULogger class with max_entries limit
- [ ] 16.3. Implement `log_command(apdu)` with decoding
- [ ] 16.4. Implement `log_response(response)` with SW message
- [ ] 16.5. Implement `_decode_command()` for human-readable output
- [ ] 16.6. Implement `get_entries(count)` retrieval
- [ ] 16.7. Implement `clear()` to reset log
- [ ] 16.8. Implement `export(path, format)` for JSON and CSV
- [ ] 16.9. Implement `enable()` and `disable()` toggles
- [ ] 16.10. Add overflow handling with entry limit
- [ ] 16.11. Write unit tests for logging operations

### 17. Error Handling Implementation

_Leverage:_ `cardlink/provisioner/exceptions.py`, `functools`

_Requirements:_ REQ-046 (Error Handling), REQ-047 (Exception Hierarchy), REQ-048 (User-Friendly Messages)

_Prompt:_ Role: Error Handling System Developer | Task: Implement comprehensive exception hierarchy for provisioner operations. Create ProvisionerError base class and specific exceptions for reader errors, card errors, connection errors, APDU errors with SW1/SW2, authentication errors, security errors, and profile errors. Create decorator for consistent error handling with user-friendly messages and troubleshooting hints. | Restrictions: Must preserve original exception context. Must not expose sensitive data in error messages. Must provide actionable troubleshooting information. Must maintain exception hierarchy. | Success: Exception hierarchy covers all error scenarios, each exception includes helpful context, decorator provides consistent error handling, error messages include troubleshooting hints, with clear documentation.

- [ ] 17.1. Create `exceptions.py` with ProvisionerError base class
- [ ] 17.2. Define ReaderNotFoundError exception
- [ ] 17.3. Define CardNotFoundError exception
- [ ] 17.4. Define NotConnectedError exception
- [ ] 17.5. Define APDUError exception with SW1/SW2
- [ ] 17.6. Define AuthenticationError exception
- [ ] 17.7. Define SecurityError exception
- [ ] 17.8. Define ProfileError exception
- [ ] 17.9. Create `handle_provisioner_operation` decorator
- [ ] 17.10. Implement user-friendly error messages with troubleshooting hints

### 18. CLI: List Command

_Leverage:_ `cardlink/cli/provision.py`, `pcsc_client.py`, `click`

_Requirements:_ REQ-049 (CLI Commands), REQ-050 (List Command)

_Prompt:_ Role: CLI Developer | Task: Implement "list" command to enumerate all PC/SC readers and display their status. Show reader index, name, card presence status, and ATR for inserted cards. Include helpful troubleshooting hints when no readers are found (check pcscd service, USB connections, permissions). | Restrictions: Must handle missing readers gracefully. Must format output clearly. Must not fail on partial information. Must provide platform-specific troubleshooting. | Success: List command displays all readers with indices and names, shows card status and ATR when present, provides helpful hints when no readers found, with CLI tests verifying output format.

- [ ] 18.1. Create `cardlink/cli/provision.py` with Click group
- [ ] 18.2. Implement `list` command
- [ ] 18.3. Display reader index, name, and card status
- [ ] 18.4. Display ATR for present cards
- [ ] 18.5. Add troubleshooting hints when no readers found
- [ ] 18.6. Write CLI tests for list command

### 19. CLI: Info Command

_Leverage:_ `cardlink/cli/provision.py`, `pcsc_client.py`, `atr_parser.py`, `secure_domain.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-051 (Info Command)

_Prompt:_ Role: CLI Developer | Task: Implement "info" command to display detailed card information. Support flags for ATR-only (--atr), ICCID-only (--iccid), Security Domain listing (--sd), complete info (--all, default), and JSON output (--json). Parse and display ATR analysis, read and format ICCID, list Security Domains with lifecycle states. | Restrictions: Must handle missing card gracefully. Must format output for readability. Must support machine-readable JSON output. Must not require secure channel for basic info. | Success: Info command shows complete card information including analyzed ATR, formatted ICCID, Security Domain list, supports selective output with flags, provides JSON format option, with CLI tests verifying all output modes.

- [ ] 19.1. Implement `info` command with reader argument
- [ ] 19.2. Add `--atr` flag for ATR-only output
- [ ] 19.3. Add `--iccid` flag for ICCID-only output
- [ ] 19.4. Add `--sd` flag for Security Domain listing
- [ ] 19.5. Add `--all` flag (default) for complete info
- [ ] 19.6. Add `--json` flag for JSON output
- [ ] 19.7. Implement ATR analysis display
- [ ] 19.8. Implement ICCID reading and display
- [ ] 19.9. Implement SD status display
- [ ] 19.10. Write CLI tests for info command

### 20. CLI: PSK Command

_Leverage:_ `cardlink/cli/provision.py`, `psk_config.py`, `key_manager.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-052 (PSK Command)

_Prompt:_ Role: Security Configuration CLI Developer | Task: Implement "psk" command for Pre-Shared Key configuration. Support --identity and --key options for manual PSK input, --generate option for random key generation with configurable size, and --export flag to read current PSK identity from card. Display generated keys clearly and confirm successful configuration. | Restrictions: Must not log key material. Must validate key format and size. Must require secure channel for writing keys. Must display security warnings. | Success: PSK command configures PSK identity and key on card, generates cryptographically secure random keys, exports current PSK identity, displays clear success/failure messages, with CLI tests covering all scenarios.

- [ ] 20.1. Implement `psk` command with reader argument
- [ ] 20.2. Add `--identity` option for PSK identity
- [ ] 20.3. Add `--key` option for hex key input
- [ ] 20.4. Add `--generate` option with key size parameter
- [ ] 20.5. Add `--export` flag to read current PSK identity
- [ ] 20.6. Implement key generation and display
- [ ] 20.7. Implement PSK configuration flow
- [ ] 20.8. Add success/failure messages
- [ ] 20.9. Write CLI tests for psk command

### 21. CLI: URL Command

_Leverage:_ `cardlink/cli/provision.py`, `url_config.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-053 (URL Command)

_Prompt:_ Role: Configuration CLI Developer | Task: Implement "url" command for remote server URL configuration. Accept URL as argument, validate format before storage, support --read flag to display current stored URL. Provide clear validation error messages and configuration confirmation. | Restrictions: Must validate URL format thoroughly. Must enforce length limits. Must handle read errors gracefully. Must display complete URL on read. | Success: URL command stores validated URLs on card, reads current URL configuration, validates format with helpful error messages, confirms successful configuration, with CLI tests verifying validation and storage.

- [ ] 21.1. Implement `url` command with reader and URL arguments
- [ ] 21.2. Add `--read` flag to display current URL
- [ ] 21.3. Implement URL validation before storage
- [ ] 21.4. Implement URL configuration flow
- [ ] 21.5. Add success/failure messages
- [ ] 21.6. Write CLI tests for url command

### 22. CLI: Trigger Command

_Leverage:_ `cardlink/cli/provision.py`, `trigger_config.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-054 (Trigger Command)

_Prompt:_ Role: OTA Trigger CLI Developer | Task: Implement "trigger" command for remote trigger configuration. Support --sms flag for SMS-PP trigger setup, --poll option with interval parameter for polling configuration, --tar option for TAR specification, --disable option to disable triggers by type, and --list flag to display configured triggers. Provide interactive prompts for KIc and KID values during SMS setup. | Restrictions: Must validate TAR format. Must validate security parameters. Must enforce reasonable intervals. Must handle interactive input securely. | Success: Trigger command configures SMS and poll triggers, prompts for security parameters interactively, lists configured triggers, disables triggers by type, with CLI tests covering all trigger types.

- [ ] 22.1. Implement `trigger` command with reader argument
- [ ] 22.2. Add `--sms` flag for SMS-PP trigger setup
- [ ] 22.3. Add `--poll` option with interval parameter
- [ ] 22.4. Add `--tar` option for TAR configuration
- [ ] 22.5. Add `--disable` option with trigger type
- [ ] 22.6. Add `--list` flag to show configured triggers
- [ ] 22.7. Implement interactive SMS trigger setup (KIc, KID prompts)
- [ ] 22.8. Write CLI tests for trigger command

### 23. CLI: BIP Command

_Leverage:_ `cardlink/cli/provision.py`, `bip_config.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-055 (BIP Command)

_Prompt:_ Role: Bearer Configuration CLI Developer | Task: Implement "bip" command for Bearer Independent Protocol configuration. Support --bearer option with type choices (GPRS, UTRAN, etc.), --apn option for APN string, and --read flag to display current configuration. Check and display terminal profile BIP support before configuration. | Restrictions: Must validate bearer type against terminal capabilities. Must validate APN format. Must check terminal support before proceeding. Must handle missing terminal support gracefully. | Success: BIP command configures bearer and APN settings, validates terminal BIP support, reads current configuration, displays terminal capabilities, with CLI tests verifying bearer types and APN encoding.

- [ ] 23.1. Implement `bip` command with reader argument
- [ ] 23.2. Add `--bearer` option with type choices
- [ ] 23.3. Add `--apn` option for APN string
- [ ] 23.4. Add `--read` flag to display current config
- [ ] 23.5. Implement BIP configuration flow
- [ ] 23.6. Display terminal profile BIP support
- [ ] 23.7. Write CLI tests for bip command

### 24. CLI: APDU Command

_Leverage:_ `cardlink/cli/provision.py`, `apdu_interface.py`, `apdu_logger.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-056 (APDU Command)

_Prompt:_ Role: APDU Scripting CLI Developer | Task: Implement "apdu" command for direct APDU transmission. Support single APDU as hex argument, --script option for executing APDU script files with comment support (# prefix), display response data with decoded status words, and show human-readable status messages. | Restrictions: Must validate hex format. Must handle script file errors gracefully. Must display both raw and decoded responses. Must support comments in scripts. | Success: APDU command transmits single APDUs and executes scripts, displays responses with decoded status messages, handles comments in script files, shows clear error messages for invalid APDUs, with CLI tests covering single and script modes.

- [ ] 24.1. Implement `apdu` command with reader and hex arguments
- [ ] 24.2. Add `--script` option for APDU script file
- [ ] 24.3. Implement single APDU transmission and display
- [ ] 24.4. Implement script execution with comment support (#)
- [ ] 24.5. Display response data and decoded status
- [ ] 24.6. Write CLI tests for apdu command

### 25. CLI: Auth Command

_Leverage:_ `cardlink/cli/provision.py`, `apdu_interface.py`, `scp02.py`, `scp03.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-057 (Auth Command)

_Prompt:_ Role: Authentication CLI Developer | Task: Implement "auth" command for card authentication operations. Support --pin option for PIN verification with retry display, --adm option for ADM key in hex, --scp02 and --scp03 flags for secure channel establishment. Display remaining PIN retries to prevent lockout, show authentication results with session information for secure channels. | Restrictions: Must display retry counter before PIN entry. Must not log sensitive authentication data. Must verify card cryptogram before claiming success. Must clear sensitive data after use. | Success: Auth command verifies PINs showing remaining retries, establishes SCP02/SCP03 secure channels, displays authentication results with session details, prevents accidental lockout, with CLI tests covering all authentication methods.

- [ ] 25.1. Implement `auth` command with reader argument
- [ ] 25.2. Add `--pin` option for PIN authentication
- [ ] 25.3. Add `--adm` option for ADM key (hex)
- [ ] 25.4. Add `--scp02` flag for SCP02 secure channel
- [ ] 25.5. Add `--scp03` flag for SCP03 secure channel
- [ ] 25.6. Implement PIN verification with retry display
- [ ] 25.7. Implement secure channel establishment
- [ ] 25.8. Display authentication result and session info
- [ ] 25.9. Write CLI tests for auth command

### 26. CLI: Profile Commands

_Leverage:_ `cardlink/cli/provision.py`, `profile_manager.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-058 (Profile Commands)

_Prompt:_ Role: Profile Management CLI Developer | Task: Implement "profile" command group with save, load, apply, and compare subcommands. "save" captures current card configuration with optional key inclusion (--with-keys) and output path (--output). "load" reads profile file and displays diff from current card. "apply" provisions card from profile with optional key parameter if not in profile. "compare" shows differences between two profile files. | Restrictions: Must not include keys in save by default. Must validate profile before application. Must show clear diffs for load and compare. Must confirm before applying changes. | Success: Profile commands save complete configurations to JSON, load and show diffs, apply profiles to cards with validation, compare profiles showing differences, handle keys securely, with CLI tests covering all operations.

- [ ] 26.1. Create `profile` command group
- [ ] 26.2. Implement `profile save` with name and reader arguments
- [ ] 26.3. Add `--with-keys` flag for PSK key inclusion
- [ ] 26.4. Add `--output` option for file path
- [ ] 26.5. Implement `profile load` with file argument
- [ ] 26.6. Display diff between profile and current card
- [ ] 26.7. Implement `profile apply` with reader and file arguments
- [ ] 26.8. Add `--key` option for PSK key if not in profile
- [ ] 26.9. Implement `profile compare` with two file arguments
- [ ] 26.10. Display comparison results
- [ ] 26.11. Write CLI tests for profile commands

### 27. CLI Entry Point

_Leverage:_ `pyproject.toml`, `cardlink/cli/provision.py`

_Requirements:_ REQ-049 (CLI Commands), REQ-059 (CLI Infrastructure)

_Prompt:_ Role: CLI Infrastructure Developer | Task: Configure CLI entry point registration in pyproject.toml for "cardlink-provision" command. Add version option to CLI group, implement global error handling decorator for consistent error reporting, add verbose/debug output option for troubleshooting, and create integration tests for complete CLI workflows. | Restrictions: Must handle all exception types gracefully. Must provide helpful error messages. Must support standard --version flag. Must allow debug output without breaking normal operation. | Success: CLI entry point registered and accessible as "cardlink-provision", shows version on --version, handles all errors with helpful messages, supports verbose/debug modes, integration tests verify complete workflows.

- [ ] 27.1. Register `cardlink-provision` entry point in pyproject.toml
- [ ] 27.2. Add version option to CLI group
- [ ] 27.3. Add global error handling with decorator
- [ ] 27.4. Add verbose/debug output option
- [ ] 27.5. Write integration tests for complete CLI workflows

### 28. Integration Tests

_Leverage:_ `tests/integration/`, `pcsc_client.py`, `profile_manager.py`, `pytest`

_Requirements:_ REQ-060 (Testing/Documentation), REQ-061 (Integration Testing), REQ-062 (Hardware Testing)

_Prompt:_ Role: Integration Test Developer | Task: Create comprehensive integration tests with real PC/SC reader detection. Use pytest.mark.integration marker to distinguish hardware-dependent tests. Test reader discovery, card connection with protocol negotiation, ATR reading and parsing, ICCID reading with BCD decoding, Security Domain selection and listing, and complete profile save/load cycles. Add skip conditions when hardware is unavailable. | Restrictions: Must not assume specific reader or card is present. Must clean up resources properly. Must skip gracefully when hardware missing. Must not modify card state destructively. | Success: Integration tests cover all major operations with real hardware, use appropriate markers, skip when hardware unavailable, clean up properly, verify complete workflows including profile operations.

- [ ] 28.1. Create integration test fixtures with real reader detection
- [ ] 28.2. Add pytest.mark.integration marker for hardware tests
- [ ] 28.3. Write test for reader discovery
- [ ] 28.4. Write test for card connection and ATR reading
- [ ] 28.5. Write test for ICCID reading
- [ ] 28.6. Write test for Security Domain selection
- [ ] 28.7. Write test for profile save/load cycle
- [ ] 28.8. Add skip conditions for missing hardware

### 29. Documentation

_Leverage:_ `README.md`, `docs/`, all module files

_Requirements:_ REQ-060 (Testing/Documentation), REQ-063 (API Documentation), REQ-064 (User Documentation)

_Prompt:_ Role: Technical Documentation Writer | Task: Create comprehensive documentation including module docstrings for all classes, platform-specific PC/SC setup guides (pcscd for Linux, native for macOS, WinSCard for Windows), CLI usage examples in README, list of supported card types and readers, and troubleshooting guide for common errors (no readers, connection failures, authentication errors). | Restrictions: Must be accurate and up-to-date. Must include working examples. Must cover all platforms. Must provide actionable troubleshooting steps. | Success: All classes have clear docstrings with examples, platform setup documented with step-by-step instructions, README includes CLI usage examples, supported hardware listed, troubleshooting guide addresses common issues.

- [ ] 29.1. Write module docstrings for all classes
- [ ] 29.2. Document PC/SC setup for Linux (pcscd installation)
- [ ] 29.3. Document macOS native PC/SC usage
- [ ] 29.4. Document Windows WinSCard requirements
- [ ] 29.5. Create CLI usage examples in README
- [ ] 29.6. Document supported card types and readers
- [ ] 29.7. Add troubleshooting guide for common errors

### 30. Event Integration

_Leverage:_ `event_emitter.py`, `pcsc_client.py`, `profile_manager.py`, `apdu_interface.py`

_Requirements:_ REQ-040 (Event System), REQ-065 (Event Integration)

_Prompt:_ Role: Event System Integration Developer | Task: Integrate EventEmitter throughout provisioner components. Add event emission to PCSCClient for card_connected/card_disconnected events, card monitoring for card_inserted/card_removed, provisioning operations for provisioning_started/provisioning_completed, APDU exchanges for apdu_exchange events, and error handling for provisioning_error events. Ensure events include relevant context data. | Restrictions: Must not impact performance significantly. Must handle event handler exceptions. Must not block operations on event emission. Must include useful context in event data. | Success: All major operations emit appropriate events with context, events fire for card state changes, provisioning lifecycle tracked through events, APDU exchanges logged via events, errors reported through events, with tests verifying event emission.

- [ ] 30.1. Add event emission to PCSCClient (card_connected, card_disconnected)
- [ ] 30.2. Add event emission to card monitoring (card_inserted, card_removed)
- [ ] 30.3. Add event emission to provisioning operations (provisioning_started, provisioning_completed)
- [ ] 30.4. Add event emission to APDU exchanges (apdu_exchange)
- [ ] 30.5. Add event emission for errors (provisioning_error)
- [ ] 30.6. Write tests for event emission

## Task Dependencies

```
1 (Setup)
├── 2 (PCSCClient)
│   ├── 3 (ATR Parser)
│   └── 4 (APDU Interface)
│       ├── 5 (TLV Parser)
│       ├── 6 (SD Manager)
│       │   ├── 7 (SCP02)
│       │   └── 8 (SCP03)
│       ├── 9 (PSK Config)
│       │   └── 10 (Key Manager)
│       ├── 11 (URL Config)
│       ├── 12 (Trigger Config)
│       └── 13 (BIP Config)
├── 14 (Profile Manager) ← depends on 9, 11, 12, 13
├── 15 (Event Emitter)
├── 16 (APDU Logger)
└── 17 (Exceptions)

CLI Tasks (18-27) ← depend on corresponding components
28 (Integration Tests) ← depends on all components
29 (Documentation) ← can start early, finalize after implementation
30 (Event Integration) ← depends on 15 and all components
```

## Estimated Effort

| Task Group | Tasks | Complexity |
|------------|-------|------------|
| Setup | 1.1-1.5 | Low |
| PC/SC Client | 2.1-2.11 | Medium |
| ATR Parser | 3.1-3.7 | Low |
| APDU Interface | 4.1-4.15 | Medium |
| TLV Parser | 5.1-5.6 | Low |
| Security Domain | 6.1-6.13 | Medium |
| SCP02 | 7.1-7.14 | High |
| SCP03 | 8.1-8.10 | High |
| PSK Config | 9.1-9.11 | Medium |
| Key Manager | 10.1-10.6 | Low |
| URL Config | 11.1-11.9 | Low |
| Trigger Config | 12.1-12.11 | Medium |
| BIP Config | 13.1-13.10 | Medium |
| Profile Manager | 14.1-14.13 | Medium |
| Event Emitter | 15.1-15.9 | Low |
| APDU Logger | 16.1-16.11 | Low |
| Error Handling | 17.1-17.10 | Low |
| CLI Commands | 18-27 | Medium |
| Integration Tests | 28.1-28.8 | Medium |
| Documentation | 29.1-29.7 | Low |
| Event Integration | 30.1-30.6 | Low |

## Notes

- SCP02 and SCP03 implementations are complex and require careful testing with test vectors
- Hardware integration tests require actual PC/SC reader and test cards
- PSK file locations (EF_PSK_ID, EF_PSK_KEY) are vendor-specific and may need configuration
- Some operations require secure channel establishment before execution
- PIN/ADM authentication should display remaining retries to prevent card lockout
