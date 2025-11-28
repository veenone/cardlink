# Requirements Document: UICC Provisioner

## Introduction

The UICC Provisioner is the CardLink component responsible for pre-configuring UICC cards for SCP81 OTA testing. It provides PC/SC-based smart card access to configure PSK keys, admin server URLs, trigger mechanisms, and other parameters required before cards can participate in OTA test sessions.

This component enables testers to prepare test cards with proper SCP81 credentials and configuration without relying on production OTA infrastructure or manual card personalization processes.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Real hardware testing**: Configures actual UICC cards for real-world testing
- **Local-first design**: PC/SC reader access without network infrastructure
- **Protocol transparency**: Full APDU logging during provisioning operations
- **Self-service setup**: Testers can prepare their own test cards
- **Standards compliance**: Follows GlobalPlatform card personalization procedures

## Requirements

### Requirement 1: PC/SC Reader Discovery and Connection

**User Story:** As a tester, I want the provisioner to discover connected smart card readers, so that I can select a reader and access my UICC card.

#### Acceptance Criteria

1. WHEN the provisioner starts THEN it SHALL scan for available PC/SC readers
2. WHEN readers are found THEN the provisioner SHALL list all with names and connection status
3. WHEN a card is inserted THEN the provisioner SHALL detect it within 2 seconds
4. WHEN a card is removed THEN the provisioner SHALL detect removal within 2 seconds
5. WHEN no reader is found THEN the provisioner SHALL display troubleshooting message
6. WHEN multiple readers are present THEN the provisioner SHALL allow reader selection
7. WHEN pcscd is not running THEN the provisioner SHALL display service activation instructions

### Requirement 2: Card Discovery and ATR Analysis

**User Story:** As a tester, I want to identify inserted UICC cards and understand their capabilities, so that I can verify I'm working with the correct card type.

#### Acceptance Criteria

1. WHEN a card is detected THEN the provisioner SHALL read and display the ATR (Answer To Reset)
2. WHEN analyzing ATR THEN the provisioner SHALL identify:
   - Card type (UICC, SIM, eUICC)
   - Supported protocols (T=0, T=1)
   - Historical bytes interpretation
3. WHEN querying EF_ICCID THEN the provisioner SHALL display the ICCID
4. WHEN querying EF_IMSI THEN the provisioner SHALL display the IMSI (if accessible)
5. WHEN analyzing card THEN the provisioner SHALL detect GlobalPlatform support
6. WHEN card doesn't respond THEN the provisioner SHALL report communication error

### Requirement 3: Security Domain Management

**User Story:** As a UICC developer, I want to manage Security Domains on the card, so that I can configure administrative access for OTA testing.

#### Acceptance Criteria

1. WHEN selecting ISD THEN the provisioner SHALL use SELECT by AID (A000000151000000)
2. WHEN authenticating THEN the provisioner SHALL support SCP02 and SCP03 protocols
3. WHEN listing SDs THEN the provisioner SHALL use GET STATUS command
4. WHEN querying SD THEN the provisioner SHALL return:
   - AID
   - Life cycle state
   - Privileges
   - Associated Security Domain
5. WHEN creating SD THEN the provisioner SHALL support INSTALL [for install] command
6. WHEN deleting SD THEN the provisioner SHALL support DELETE command with proper cascade handling
7. WHEN updating SD THEN the provisioner SHALL support PUT KEY and SET STATUS commands

### Requirement 4: PSK Key Management

**User Story:** As a tester, I want to configure PSK keys on the UICC, so that the card can establish secure TLS connections with my test server.

#### Acceptance Criteria

1. WHEN configuring PSK THEN the provisioner SHALL store PSK identity in EF_PSK_ID
2. WHEN configuring PSK THEN the provisioner SHALL store PSK key in EF_PSK_KEY
3. WHEN storing PSK THEN the provisioner SHALL support key sizes of 16, 32, and 64 bytes
4. WHEN generating PSK THEN the provisioner SHALL support random key generation
5. WHEN importing PSK THEN the provisioner SHALL accept hex string input
6. WHEN exporting PSK THEN the provisioner SHALL output hex string (for server configuration)
7. WHEN verifying PSK THEN the provisioner SHALL read back and compare stored values
8. WHEN PSK files don't exist THEN the provisioner SHALL create them with proper structure
9. WHEN PSK storage fails THEN the provisioner SHALL report specific error condition

### Requirement 5: Admin Server URL Configuration

**User Story:** As a tester, I want to configure the OTA admin server URL on the UICC, so that the card knows where to connect for OTA sessions.

#### Acceptance Criteria

1. WHEN configuring URL THEN the provisioner SHALL store in EF_ADMIN_URL or equivalent
2. WHEN storing URL THEN the provisioner SHALL support HTTPS URLs up to 255 bytes
3. WHEN storing URL THEN the provisioner SHALL encode as TLV with proper tags
4. WHEN reading URL THEN the provisioner SHALL display current configured URL
5. WHEN URL is invalid THEN the provisioner SHALL validate format before storing
6. WHEN URL contains port THEN the provisioner SHALL parse and store correctly
7. WHEN URL is too long THEN the provisioner SHALL report maximum length exceeded

### Requirement 6: OTA Trigger Configuration

**User Story:** As a tester, I want to configure OTA trigger mechanisms on the UICC, so that the card can respond to push notifications.

#### Acceptance Criteria

1. WHEN configuring trigger THEN the provisioner SHALL support SMS-PP trigger setup
2. WHEN configuring trigger THEN the provisioner SHALL set TAR (Toolkit Application Reference)
3. WHEN configuring SMS trigger THEN the provisioner SHALL configure:
   - Originating address filter
   - Security parameters (KIc, KID)
   - Counter settings
4. WHEN configuring poll trigger THEN the provisioner SHALL set polling interval
5. WHEN listing triggers THEN the provisioner SHALL show all configured trigger types
6. WHEN disabling trigger THEN the provisioner SHALL support trigger deactivation
7. WHEN trigger requires keys THEN the provisioner SHALL prompt for OTA keys (KIc, KID)

### Requirement 7: BIP/CAT Configuration

**User Story:** As a tester, I want to configure BIP (Bearer Independent Protocol) settings on the UICC, so that the card can initiate data connections.

#### Acceptance Criteria

1. WHEN configuring BIP THEN the provisioner SHALL set default bearer parameters
2. WHEN configuring BIP THEN the provisioner SHALL configure:
   - Default bearer type (GPRS, EUTRAN, etc.)
   - APN settings
   - Buffer sizes
   - Connection timeout
3. WHEN enabling BIP THEN the provisioner SHALL verify CAT terminal profile compatibility
4. WHEN reading BIP config THEN the provisioner SHALL display all BIP parameters
5. WHEN BIP is not supported THEN the provisioner SHALL report card capability limitation

### Requirement 8: Card Profile Management

**User Story:** As a tester, I want to save and load complete card configurations as profiles, so that I can quickly provision multiple cards with the same settings.

#### Acceptance Criteria

1. WHEN saving profile THEN the provisioner SHALL export all configurable parameters
2. WHEN saving profile THEN the provisioner SHALL support JSON export format
3. WHEN saving profile THEN the provisioner SHALL optionally include PSK keys
4. WHEN loading profile THEN the provisioner SHALL validate before applying
5. WHEN loading profile THEN the provisioner SHALL show diff with current card state
6. WHEN applying profile THEN the provisioner SHALL provision all parameters
7. WHEN comparing profiles THEN the provisioner SHALL highlight differences
8. WHEN profile is incompatible THEN the provisioner SHALL report specific incompatibilities

### Requirement 9: APDU Command Interface

**User Story:** As a developer, I want to send raw APDU commands to the card, so that I can perform custom operations and debugging.

#### Acceptance Criteria

1. WHEN sending APDU THEN the provisioner SHALL transmit raw command bytes
2. WHEN receiving response THEN the provisioner SHALL display data and status word
3. WHEN chaining commands THEN the provisioner SHALL support command scripting
4. WHEN using macros THEN the provisioner SHALL support named APDU sequences
5. WHEN logging APDUs THEN the provisioner SHALL record all command/response pairs
6. WHEN interpreting status THEN the provisioner SHALL decode common SW1SW2 values
7. WHEN using T=0 THEN the provisioner SHALL handle GET RESPONSE automatically
8. WHEN using T=1 THEN the provisioner SHALL handle chaining properly

### Requirement 10: Authentication and Key Management

**User Story:** As a tester, I want to authenticate to the card with proper credentials, so that I can access protected areas and perform administrative operations.

#### Acceptance Criteria

1. WHEN authenticating THEN the provisioner SHALL support PIN verification (VERIFY command)
2. WHEN authenticating THEN the provisioner SHALL support ADM key authentication
3. WHEN using SCP02 THEN the provisioner SHALL implement proper key derivation
4. WHEN using SCP03 THEN the provisioner SHALL implement AES-based secure channel
5. WHEN keys are incorrect THEN the provisioner SHALL report authentication failure
6. WHEN PIN is blocked THEN the provisioner SHALL report blocked status and remaining tries
7. WHEN session is established THEN the provisioner SHALL maintain secure channel state
8. WHEN session expires THEN the provisioner SHALL re-authenticate automatically

### Requirement 11: CLI Integration

**User Story:** As a developer, I want to control provisioning via command line, so that I can automate card preparation workflows.

#### Acceptance Criteria

1. WHEN running `cardlink-provision list` THEN the CLI SHALL display all connected readers and cards
2. WHEN running `cardlink-provision info <reader>` THEN the CLI SHALL show card details:
   - ATR and analysis
   - ICCID, IMSI
   - Security Domain status
   - Current PSK/URL configuration
3. WHEN running `cardlink-provision psk <reader>` THEN the CLI SHALL configure PSK:
   - `--identity` for PSK identity string
   - `--key` for PSK key (hex)
   - `--generate` for random key generation
   - `--export` to output configured values
4. WHEN running `cardlink-provision url <reader> <url>` THEN the CLI SHALL set admin URL
5. WHEN running `cardlink-provision trigger <reader>` THEN the CLI SHALL configure triggers:
   - `--sms` for SMS-PP trigger setup
   - `--poll` for polling trigger setup
   - `--tar` for TAR configuration
6. WHEN running `cardlink-provision apdu <reader> <hex>` THEN the CLI SHALL send raw APDU
7. WHEN running `cardlink-provision profile save/load/apply` THEN the CLI SHALL manage profiles
8. WHEN running `cardlink-provision auth <reader>` THEN the CLI SHALL authenticate:
   - `--pin` for PIN authentication
   - `--adm` for ADM key authentication
   - `--scp02`/`--scp03` for secure channel

### Requirement 12: Event Emission for Integration

**User Story:** As a dashboard developer, I want the provisioner to emit events, so that I can display provisioning status in real-time.

#### Acceptance Criteria

1. WHEN a reader is connected THEN the provisioner SHALL emit `reader_connected` event
2. WHEN a reader is disconnected THEN the provisioner SHALL emit `reader_disconnected` event
3. WHEN a card is inserted THEN the provisioner SHALL emit `card_inserted` event with ATR
4. WHEN a card is removed THEN the provisioner SHALL emit `card_removed` event
5. WHEN provisioning starts THEN the provisioner SHALL emit `provisioning_started` event
6. WHEN provisioning completes THEN the provisioner SHALL emit `provisioning_completed` event
7. WHEN an error occurs THEN the provisioner SHALL emit `provisioning_error` event
8. WHEN APDU is exchanged THEN the provisioner SHALL emit `apdu_exchange` event

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: Separate classes for PC/SC communication, APDU handling, profile management
- **Modular Design**: Provisioner usable standalone without server or database
- **Card Abstraction**: Abstract interface to support different card types (UICC, eUICC)
- **Dependency Injection**: Inject PC/SC context, key providers, event emitter

### Performance

- **Reader detection**: Detect connected readers within 2 seconds
- **Card detection**: Detect card insertion/removal within 2 seconds
- **APDU latency**: Single APDU exchange within 1 second
- **Profile application**: Complete profile provisioning within 30 seconds

### Compatibility

- **PC/SC Readers**: Support standard PC/SC compliant readers (ACR, Omnikey, etc.)
- **Card Types**: UICC cards with GlobalPlatform support
- **Operating Systems**: Linux (pcscd), macOS (native), Windows (WinSCard)
- **PC/SC Lite**: Version 1.8+ on Linux

### Reliability

- **Transaction handling**: Rollback on provisioning failure
- **Card state preservation**: Never leave card in inconsistent state
- **Connection recovery**: Handle card removal during operation gracefully
- **Error reporting**: Clear, actionable error messages for all failure modes

### Security

- **Key handling**: Never log sensitive keys in plaintext
- **Secure memory**: Clear key buffers after use
- **ADM protection**: Warn before operations that could brick the card
- **PIN attempts**: Display remaining tries before authentication
