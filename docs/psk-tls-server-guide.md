# PSK-TLS Server User Guide

This guide provides detailed instructions for setting up and running the PSK-TLS Admin Server for GlobalPlatform SCP81 Over-The-Air (OTA) UICC administration testing.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Server Configuration](#server-configuration)
  - [PSK Key Store](#psk-key-store)
  - [Cipher Suite Selection](#cipher-suite-selection)
- [Running the Server](#running-the-server)
  - [Command Line Interface](#command-line-interface)
  - [Programmatic Usage](#programmatic-usage)
  - [Database Integration for Session Persistence](#database-integration-for-session-persistence)
- [Key Management](#key-management)
- [Database-Backed Deployment](#database-backed-deployment)
  - [Complete Server Setup with Database](#complete-server-setup-with-database)
  - [Database Maintenance](#database-maintenance)
  - [Production Deployment Checklist](#production-deployment-checklist)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

---

## Overview

The PSK-TLS Admin Server implements the GlobalPlatform SCP81 specification for secure Over-The-Air UICC administration. It provides:

- TLS 1.2 with Pre-Shared Key (PSK) cipher suites
- HTTP-based GP Amendment B Remote Application Management (RAM)
- Session management with configurable timeouts
- Multiple key store backends (file, memory, database)
- Event emission for monitoring and logging
- Thread-safe concurrent connection handling
- PID file support for cross-process management

### Supported Cipher Suites

| Cipher Suite | Security Level | Use Case |
|--------------|----------------|----------|
| `TLS_PSK_WITH_AES_128_CBC_SHA256` | Production | Mandatory per GP spec |
| `TLS_PSK_WITH_AES_256_CBC_SHA384` | Production | Recommended |
| `TLS_PSK_WITH_AES_128_CBC_SHA` | Legacy | Backward compatibility |
| `TLS_PSK_WITH_AES_256_CBC_SHA` | Legacy | Backward compatibility |
| `TLS_PSK_WITH_NULL_SHA256` | Testing Only | No encryption |
| `TLS_PSK_WITH_NULL_SHA` | Testing Only | No encryption |

### Future TLS 1.3 Support

The following TLS 1.3 cipher suites are defined per GP spec but require future sslpsk3 support:

| Cipher Suite | Status |
|--------------|--------|
| `TLS_AES_128_CCM_SHA256` | Planned |
| `TLS_AES_128_GCM_SHA256` | Planned |

---

## Prerequisites

### System Requirements

- Python 3.9 or higher
- Linux, macOS, or Windows
- Network access for client connections

### Required Dependencies

Install the base package and PSK-TLS support:

```bash
pip install cardlink[psk]
```

This installs:
- `sslpsk3` - PSK-TLS support library
- `pyyaml` - Configuration file parsing
- `click` - Command-line interface
- `rich` - Console output formatting

### OpenSSL Requirements

The `sslpsk3` library requires OpenSSL with PSK cipher support. Most modern systems include this by default. Verify with:

```bash
openssl ciphers -v 'PSK' | head -5
```

Expected output should list PSK cipher suites.

---

## Installation

### From PyPI

```bash
# Basic installation
pip install cardlink

# With PSK-TLS server support
pip install cardlink[server]

# Full installation with all features
pip install cardlink[all]
```

### From Source

```bash
git clone https://github.com/veenone/cardlink.git
cd cardlink
pip install -e ".[server]"
```

### Verify Installation

```bash
# Check CLI is available
gp-server --help

# Check PSK support
python -c "from cardlink.server import HAS_PSK_SUPPORT; print(f'PSK Support: {HAS_PSK_SUPPORT}')"
```

---

## Configuration

### Server Configuration

Configuration can be provided via:
1. Command-line arguments (highest priority)
2. Environment variables
3. YAML configuration file (lowest priority)

#### Configuration File (server.yaml)

```yaml
# Server binding
host: "0.0.0.0"
port: 8443

# Connection limits
max_connections: 100
backlog: 5

# Timeouts (in seconds)
session_timeout: 300.0
handshake_timeout: 30.0
read_timeout: 30.0

# Thread pool size
thread_pool_size: 10

# PSK key store
keys_file: "/path/to/keys.yaml"

# Cipher configuration
ciphers:
  enable_legacy: false
  enable_null_ciphers: false
  enable_tls13: false  # Future: requires sslpsk3 TLS 1.3 support
  max_fragment_length: null  # RFC 6066: 512, 1024, 2048, 4096, or null

# Logging
log_level: "INFO"

# Dashboard (optional)
enable_dashboard: false
dashboard_port: 8080
```

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GP_OTA_SERVER_HOST` | Server bind address | `127.0.0.1` |
| `GP_OTA_SERVER_PORT` | Server listen port | `8443` |
| `GP_OTA_SERVER_CONFIG` | Path to config file | None |
| `GP_OTA_SERVER_PID_FILE` | Path to PID file | `/tmp/gp-ota-server.pid` |

#### ServerConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | str | `"0.0.0.0"` | Bind address |
| `port` | int | `8443` | Listen port |
| `max_connections` | int | `100` | Maximum concurrent connections |
| `session_timeout` | float | `300.0` | Session timeout in seconds |
| `handshake_timeout` | float | `30.0` | TLS handshake timeout |
| `read_timeout` | float | `30.0` | HTTP read timeout |
| `backlog` | int | `5` | Socket listen backlog |
| `thread_pool_size` | int | `10` | Worker thread count |
| `enable_dashboard` | bool | `False` | Enable web dashboard |
| `dashboard_port` | int | `8080` | Dashboard port |
| `key_store_path` | str | `None` | Path to YAML key file |
| `log_level` | str | `"INFO"` | Logging level |

---

### PSK Key Store

PSK keys map client identities to shared secrets. The server supports multiple key store backends.

#### File-Based Key Store (keys.yaml)

Create a YAML file with PSK identities and hex-encoded keys:

```yaml
keys:
  # Format: identity: hex_encoded_key

  # Card identities (ICCID-based)
  card_8901234567890123456: "0123456789ABCDEF0123456789ABCDEF"
  card_8901234567890123457: "FEDCBA9876543210FEDCBA9876543210"

  # Named identities
  test_card_001: "00112233445566778899AABBCCDDEEFF"
  development: "404142434445464748494A4B4C4D4E4F"

  # Operator identities
  operator_mno_001: "A0A1A2A3A4A5A6A7A8A9AAABACADAEAF"
```

Key requirements:
- Identities must be unique strings
- Keys must be hex-encoded (no spaces or prefixes)
- Minimum recommended key length: 16 bytes (128 bits)
- Maximum key length: typically 32 bytes (256 bits)

#### Memory Key Store (Programmatic)

For testing or dynamic key management:

```python
from cardlink.server import MemoryKeyStore

key_store = MemoryKeyStore()
key_store.add_key("test_identity", bytes.fromhex("0123456789ABCDEF"))
key_store.add_key("another_card", bytes.fromhex("FEDCBA9876543210"))

# Remove a key
key_store.remove_key("test_identity")

# Check if identity exists
if key_store.identity_exists("another_card"):
    print("Key found")

# List all identities
identities = key_store.get_all_identities()

# Clear all keys
key_store.clear()
```

#### Database Key Store

For production deployments with persistent database backend:

```python
from cardlink.server import DatabaseKeyStore
from cardlink.database.repositories import CardRepository

# Create card repository with database session
card_repo = CardRepository(session)

# Create database-backed key store
key_store = DatabaseKeyStore(card_repo)

# The key store reads PSK credentials from CardProfile records
# Keys are encrypted at rest using Fernet encryption
```

**Benefits of Database Key Store:**
- Persistent storage across server restarts
- Centralized key management with other card data
- Automatic PSK key encryption at rest (Fernet AES-128)
- Integration with card provisioning workflow
- Audit trail through database events

**Setting up Card Profiles with PSK Keys:**

```python
from cardlink.database import get_unit_of_work
from cardlink.database.models import CardProfile

# Create card profile with PSK credentials
with get_unit_of_work() as uow:
    profile = CardProfile(
        name="Production Card 001",
        psk_identity="card_8901234567890123456",
        psk_key=bytes.fromhex("0123456789ABCDEF0123456789ABCDEF"),
        admin_url="https://server.example.com:8443/admin"
    )
    uow.cards.add(profile)
    uow.commit()

    # PSK key is automatically encrypted before storage
    # Retrieve for server use
    key_store = DatabaseKeyStore(uow.cards)

    # Key is automatically decrypted when accessed
    key = key_store.get_key("card_8901234567890123456")
```

See [Database Layer Guide](database-guide.md) for complete database setup and management.

---

### Cipher Suite Selection

#### Production Ciphers (Default)

Secure cipher suites for production use:

```bash
gp-server start --ciphers production
```

Enables:
- `TLS_PSK_WITH_AES_128_CBC_SHA256` (mandatory per GP spec)
- `TLS_PSK_WITH_AES_256_CBC_SHA384` (recommended)

#### Legacy Ciphers

For compatibility with older clients:

```bash
gp-server start --ciphers legacy
```

Adds:
- `TLS_PSK_WITH_AES_128_CBC_SHA`
- `TLS_PSK_WITH_AES_256_CBC_SHA`

#### All Ciphers

Enable all production and legacy ciphers:

```bash
gp-server start --ciphers all
```

#### NULL Ciphers (Testing Only)

For debugging without encryption (traffic is in plaintext):

```bash
gp-server start --enable-null-ciphers
```

Adds:
- `TLS_PSK_WITH_NULL_SHA256`
- `TLS_PSK_WITH_NULL_SHA`

**WARNING**: NULL ciphers provide NO encryption. Use only in isolated test environments.

---

## Running the Server

### Command Line Interface

#### Start Server

```bash
# Start with defaults (localhost:8443, foreground mode)
gp-server start --keys keys.yaml -f

# Start on all interfaces
gp-server start --host 0.0.0.0 --port 8443 --keys keys.yaml -f

# Start with configuration file
gp-server start --config server.yaml -f

# Start with verbose logging
gp-server -v start --keys keys.yaml -f

# Start with debug logging
gp-server --debug start --keys keys.yaml -f

# Start with legacy cipher support
gp-server start --keys keys.yaml --ciphers legacy -f

# Start with custom connection limits
gp-server start --keys keys.yaml --max-connections 50 --session-timeout 600 -f

# Start in background (writes PID file)
gp-server start --keys keys.yaml
```

The `-f` (foreground) flag keeps the server running in the terminal. Press `Ctrl+C` to stop.

Without `-f`, the server runs in background and uses PID file for management.

#### Check Server Status

```bash
gp-server status
```

Output includes:
- Running state
- PID
- Host and port (if running in-process)
- Active connections and sessions (if running in-process)

#### Stop Server

```bash
# Graceful shutdown (SIGTERM)
gp-server stop

# Force immediate shutdown (SIGKILL)
gp-server stop --force

# Custom timeout
gp-server stop --timeout 10
```

#### Validate Configuration

```bash
# Validate config file
gp-server validate --config server.yaml

# Validate config and keys
gp-server validate --config server.yaml --keys keys.yaml
```

### Programmatic Usage

#### Basic Server Setup

```python
from cardlink.server import (
    AdminServer,
    ServerConfig,
    CipherConfig,
    FileKeyStore,
    EventEmitter,
)

# Create cipher configuration
cipher_config = CipherConfig(
    enable_legacy=True,
    enable_null_ciphers=False,
    enable_tls13=False,  # Future: requires sslpsk3 TLS 1.3 support
    max_fragment_length=None,  # Use default 16384
)

# Validate cipher configuration
cipher_config.validate()

# Create server configuration
config = ServerConfig(
    host="0.0.0.0",
    port=8443,
    max_connections=100,
    session_timeout=300.0,
    handshake_timeout=30.0,
    read_timeout=30.0,
    cipher_config=cipher_config,
)

# Validate server configuration
config.validate()

# Load PSK keys
key_store = FileKeyStore("keys.yaml")

# Create event emitter for monitoring
event_emitter = EventEmitter()

# Create and start server
server = AdminServer(
    config=config,
    key_store=key_store,
    event_emitter=event_emitter,
)

try:
    server.start()
    print(f"Server started on {config.host}:{config.port}")

    # Server runs in background threads
    # Keep main thread alive
    import time
    while server.is_running:
        time.sleep(1)

except KeyboardInterrupt:
    print("Shutting down...")
finally:
    server.stop()
```

#### Event Monitoring

```python
from cardlink.server import (
    EventEmitter,
    EVENT_SERVER_STARTED,
    EVENT_SERVER_STOPPED,
    EVENT_SESSION_STARTED,
    EVENT_SESSION_ENDED,
    EVENT_HANDSHAKE_COMPLETED,
    EVENT_HANDSHAKE_FAILED,
    EVENT_APDU_RECEIVED,
    EVENT_APDU_SENT,
    EVENT_PSK_MISMATCH,
    EVENT_CONNECTION_INTERRUPTED,
    EVENT_HIGH_ERROR_RATE,
)

# Create event emitter
event_emitter = EventEmitter()

# Register event handlers using subscribe()
def on_server_started(event_data):
    print(f"Server started: {event_data}")

def on_handshake(event_data):
    print(f"TLS handshake completed:")
    print(f"  Client: {event_data['client_address']}")
    print(f"  Identity: {event_data['psk_identity']}")
    print(f"  Cipher: {event_data['cipher_suite']}")

def on_session_started(event_data):
    print(f"New session: {event_data['session_id']}")

def on_apdu_received(event_data):
    print(f"APDU received: {event_data['apdu_hex']}")

def on_psk_mismatch(event_data):
    print(f"PSK mismatch for identity: {event_data['identity']}")

def on_connection_interrupted(event_data):
    print(f"Connection interrupted: {event_data}")

def on_high_error_rate(event_data):
    print(f"High error rate detected: {event_data}")

# Subscribe to events
event_emitter.subscribe(EVENT_SERVER_STARTED, on_server_started)
event_emitter.subscribe(EVENT_HANDSHAKE_COMPLETED, on_handshake)
event_emitter.subscribe(EVENT_SESSION_STARTED, on_session_started)
event_emitter.subscribe(EVENT_APDU_RECEIVED, on_apdu_received)
event_emitter.subscribe(EVENT_PSK_MISMATCH, on_psk_mismatch)
event_emitter.subscribe(EVENT_CONNECTION_INTERRUPTED, on_connection_interrupted)
event_emitter.subscribe(EVENT_HIGH_ERROR_RATE, on_high_error_rate)

# Subscribe to ALL events using wildcard
def log_all_events(event_data):
    print(f"[{event_data['event_type']}] {event_data}")

event_emitter.subscribe("*", log_all_events)

# Start emitter before server
event_emitter.start()

# Use with server
server = AdminServer(config, key_store, event_emitter)

# When done, unsubscribe and stop
# event_emitter.unsubscribe(subscription_id)
# event_emitter.stop()
```

#### Session Management

```python
# Get active sessions
sessions = server.get_active_sessions()
for session in sessions:
    print(f"Session: {session.session_id}")
    print(f"  Client: {session.client_address}")
    print(f"  State: {session.state.value}")
    print(f"  Identity: {session.metadata.get('psk_identity')}")
    print(f"  Duration: {session.get_duration_seconds():.2f}s")
    print(f"  Commands: {session.command_count}")

    # Get session summary
    summary = session.get_summary()
    print(f"  Summary: {summary}")

# Get connection count
print(f"Active connections: {server.get_connection_count()}")
print(f"Active sessions: {server.get_session_count()}")

# Access server components
tls_handler = server.tls_handler
session_manager = server.session_manager
error_handler = server.error_handler
command_processor = server.command_processor
http_handler = server.http_handler
```

#### Database Integration for Session Persistence

The server can automatically persist sessions and communication logs to the database:

```python
from cardlink.server import AdminServer, ServerConfig
from cardlink.database import get_unit_of_work
from cardlink.database.models import OTASession, SessionStatus, CommLog, CommDirection

# Create server with database integration
uow = get_unit_of_work()
server = AdminServer(config, key_store)

# Track session mapping (external session ID -> database session ID)
session_map = {}

# Session lifecycle with database persistence
def on_session_started(event_data):
    """Create database record when session starts"""
    with uow:
        # Find device by PSK identity
        device = uow.devices.get_by_iccid(event_data['psk_identity'])

        if device:
            # Create session record
            session = OTASession(
                device_id=device.id,
                session_type="admin",
                status=SessionStatus.IN_PROGRESS,
                metadata={
                    'client_ip': event_data['client_address'][0],
                    'client_port': event_data['client_address'][1],
                    'cipher_suite': event_data.get('cipher_suite'),
                }
            )
            uow.sessions.add(session)
            uow.commit()

            # Track mapping
            session_map[event_data['session_id']] = session.id

def on_apdu_received(event_data):
    """Log APDU exchange to database"""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            log = CommLog(
                session_id=session_map[external_id],
                direction=CommDirection.RECEIVED,
                apdu_command=bytes.fromhex(event_data['apdu_hex']),
                timestamp=datetime.utcnow()
            )
            uow.logs.add(log)
            uow.commit()

def on_apdu_sent(event_data):
    """Log APDU response to database"""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            log = CommLog(
                session_id=session_map[external_id],
                direction=CommDirection.SENT,
                apdu_response=bytes.fromhex(event_data['response_hex']),
                duration_ms=event_data.get('duration_ms', 0),
                timestamp=datetime.utcnow()
            )
            uow.logs.add(log)
            uow.commit()

def on_session_ended(event_data):
    """Update session status when complete"""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            session = uow.sessions.get(session_map[external_id])
            if session:
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.utcnow()
                session.metadata['duration_seconds'] = event_data.get('duration', 0)
                uow.sessions.update(session)
                uow.commit()

            # Clean up mapping
            del session_map[external_id]

# Subscribe handlers
event_emitter.subscribe(EVENT_SESSION_STARTED, on_session_started)
event_emitter.subscribe(EVENT_APDU_RECEIVED, on_apdu_received)
event_emitter.subscribe(EVENT_APDU_SENT, on_apdu_sent)
event_emitter.subscribe(EVENT_SESSION_ENDED, on_session_ended)
```

**Database Integration Benefits:**
- Persistent session history across server restarts
- Full APDU command/response audit trail
- Performance metrics and analytics
- Integration with test result tracking
- Compliance and regulatory audit support

**Querying Session History:**

```python
from cardlink.database import get_unit_of_work
from datetime import datetime, timedelta

with get_unit_of_work() as uow:
    # Get recent sessions
    recent_sessions = uow.sessions.find_recent(hours=24)

    for session in recent_sessions:
        print(f"Session {session.id}: {session.status.value}")
        print(f"  Device: {session.device.iccid}")
        print(f"  Started: {session.started_at}")

        # Get communication logs for this session
        logs = uow.logs.get_by_session(session.id)
        print(f"  APDU exchanges: {len(logs)}")

    # Get session statistics
    stats = uow.sessions.get_stats(hours=24)
    print(f"\n24-hour Statistics:")
    print(f"  Total sessions: {stats['total']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
```

See [Database Layer Guide](database-guide.md) for complete session management and querying capabilities.

---

## Key Management

### Generating PSK Keys

Generate secure random keys for production use:

```python
import secrets

# Generate 128-bit (16 byte) key
key_128 = secrets.token_hex(16)
print(f"128-bit key: {key_128}")

# Generate 256-bit (32 byte) key
key_256 = secrets.token_hex(32)
print(f"256-bit key: {key_256}")
```

Or using command line:

```bash
# Generate 128-bit key
openssl rand -hex 16

# Generate 256-bit key
openssl rand -hex 32
```

### Key Rotation

To rotate keys without service interruption:

1. Add new key to key store with new identity
2. Update UICC with new PSK configuration
3. Verify connectivity with new key
4. Remove old key from key store

```python
# Reload keys from file without restart
key_store.reload()
```

### Key Store Best Practices

1. **Never commit keys to version control**
   - Use `.gitignore` to exclude key files
   - Use environment variables or secret management

2. **Restrict file permissions**
   ```bash
   chmod 600 keys.yaml
   ```

3. **Use separate keys per device**
   - Each UICC should have a unique PSK identity and key
   - Avoid shared keys across multiple devices

4. **Monitor for unknown identities**
   - Log and alert on `EVENT_PSK_MISMATCH` events
   - May indicate unauthorized access attempts

---

## Security Considerations

### Network Security

1. **Bind to specific interfaces**
   ```bash
   # Only localhost (development)
   gp-server start --host 127.0.0.1

   # Specific interface (production)
   gp-server start --host 192.168.1.100
   ```

2. **Use firewall rules**
   ```bash
   # Allow only specific clients
   iptables -A INPUT -p tcp --dport 8443 -s 192.168.1.0/24 -j ACCEPT
   iptables -A INPUT -p tcp --dport 8443 -j DROP
   ```

3. **Use TLS termination proxy** (optional)
   - Place behind nginx/HAProxy for additional security
   - Enables certificate-based client authentication

### Key Security

1. **Never log PSK keys**
   - The server only logs PSK identities, never key values
   - Ensure custom handlers follow this practice

2. **Encrypt keys at rest**
   - Use encrypted filesystems for key storage
   - Consider using hardware security modules (HSM)

3. **Minimum key length**
   - Use at least 128-bit (16 byte) keys
   - 256-bit (32 byte) recommended for high security

### Cipher Selection

1. **Avoid NULL ciphers in production**
   - NULL ciphers provide authentication but no encryption
   - Use only for debugging in isolated environments

2. **Prefer SHA-256/384 cipher suites**
   - `TLS_PSK_WITH_AES_128_CBC_SHA256`
   - `TLS_PSK_WITH_AES_256_CBC_SHA384`

3. **Disable legacy ciphers when possible**
   - SHA-1 based ciphers are deprecated
   - Enable only if required for compatibility

---

## Troubleshooting

### Common Issues

#### "sslpsk3 library not installed"

```bash
# Install PSK support
pip install sslpsk3

# Or install with server extras
pip install cardlink[server]
```

#### "Failed to bind to address"

```bash
# Check if port is in use
lsof -i :8443
netstat -tlnp | grep 8443

# Use a different port
gp-server start --port 9443
```

#### "Unknown PSK identity"

1. Verify identity in key store:
   ```bash
   grep "identity_name" keys.yaml
   ```

2. Check key store is loaded:
   ```bash
   gp-server -v start --keys keys.yaml
   ```

3. Verify UICC PSK configuration matches

#### "TLS handshake timeout"

1. Increase timeout:
   ```bash
   gp-server start --handshake-timeout 60
   ```

2. Check network connectivity
3. Verify client TLS configuration

#### "Cipher suite mismatch"

1. Enable legacy ciphers:
   ```bash
   gp-server start --ciphers all
   ```

2. Check client supported ciphers
3. Verify OpenSSL PSK support

#### "Server is already running"

The server uses PID files for cross-process management:

```bash
# Check if server is running
gp-server status

# Stop existing server first
gp-server stop

# Or force stop if stuck
gp-server stop --force
```

### Debug Logging

Enable verbose logging for troubleshooting:

```bash
# Verbose mode
gp-server -v start --keys keys.yaml

# Debug mode (very verbose)
gp-server --debug start --keys keys.yaml
```

### Testing Connection

Test TLS-PSK connection using OpenSSL:

```bash
# Test with PSK
openssl s_client -connect localhost:8443 -psk_identity "test_card" -psk "0123456789ABCDEF"

# With specific cipher
openssl s_client -connect localhost:8443 -psk_identity "test_card" -psk "0123456789ABCDEF" -cipher "PSK-AES128-CBC-SHA256"
```

---

## API Reference

### ServerConfig

```python
@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8443
    max_connections: int = 100
    session_timeout: float = 300.0
    handshake_timeout: float = 30.0
    read_timeout: float = 30.0
    backlog: int = 5
    thread_pool_size: int = 10
    cipher_config: CipherConfig = field(default_factory=CipherConfig)
    enable_dashboard: bool = False
    dashboard_port: int = 8080
    key_store_path: Optional[str] = None
    log_level: str = "INFO"

    def validate(self) -> None:
        """Validate configuration values. Raises ValueError if invalid."""
```

### CipherConfig

```python
@dataclass
class CipherConfig:
    # TLS 1.2 production ciphers (mandatory per GP spec)
    production_ciphers: List[str]  # AES-CBC-SHA256/384

    # TLS 1.2 legacy ciphers (for backward compatibility)
    legacy_ciphers: List[str]      # AES-CBC-SHA

    # NULL ciphers for testing only (NO ENCRYPTION)
    null_ciphers: List[str]        # NULL ciphers

    # TLS 1.3 ciphers per GP spec (future support)
    tls13_ciphers: List[str]       # AES-CCM/GCM

    enable_legacy: bool = False
    enable_null_ciphers: bool = False
    enable_tls13: bool = False  # Not yet supported by sslpsk3

    # Maximum Fragment Length per RFC 6066 and GP spec
    # Valid values: 512, 1024, 2048, 4096, or None (default 16384)
    max_fragment_length: Optional[int] = None

    def get_enabled_ciphers(self) -> List[str]: ...
    def get_openssl_cipher_string(self) -> str: ...
    def validate(self) -> None: ...
```

### KeyStore (Abstract)

```python
class KeyStore(ABC):
    @abstractmethod
    def get_key(self, identity: str) -> Optional[bytes]: ...

    @abstractmethod
    def identity_exists(self, identity: str) -> bool: ...

    def get_all_identities(self) -> list[str]: ...
```

### AdminServer

```python
class AdminServer:
    def __init__(
        self,
        config: ServerConfig,
        key_store: KeyStore,
        event_emitter: Optional[EventEmitter] = None,
        metrics_collector: Optional[Any] = None,
    ): ...

    def start(self) -> None: ...
    def stop(self, timeout: float = 5.0) -> None: ...

    @property
    def is_running(self) -> bool: ...

    @property
    def config(self) -> ServerConfig: ...

    @property
    def tls_handler(self) -> TLSHandler: ...

    @property
    def session_manager(self) -> SessionManager: ...

    @property
    def error_handler(self) -> ErrorHandler: ...

    @property
    def command_processor(self) -> GPCommandProcessor: ...

    @property
    def http_handler(self) -> HTTPHandler: ...

    def get_active_sessions(self) -> List[Session]: ...
    def get_session_count(self) -> int: ...
    def get_connection_count(self) -> int: ...
```

### EventEmitter

```python
class EventEmitter:
    def __init__(self, queue_size: int = 1000): ...

    def start(self) -> None: ...
    def stop(self, timeout: float = 5.0) -> None: ...

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to an event type. Returns subscription ID."""

    def unsubscribe(self, subscription_id: str) -> bool: ...

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit event asynchronously (queued)."""

    def emit_sync(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit event synchronously (blocking)."""

    def get_subscriber_count(self, event_type: Optional[str] = None) -> int: ...
    def clear_subscriptions(self) -> None: ...
```

### Session

```python
@dataclass
class Session:
    session_id: str
    state: SessionState
    tls_info: Optional[TLSSessionInfo]
    created_at: datetime
    last_activity: datetime
    apdu_exchanges: List[APDUExchange]
    command_count: int
    client_address: Optional[str]
    close_reason: Optional[CloseReason]
    metadata: Dict[str, Any]

    def record_exchange(self, exchange: APDUExchange) -> None: ...
    def get_duration_seconds(self) -> float: ...
    def get_summary(self) -> Dict[str, Any]: ...
```

### Event Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `EVENT_SERVER_STARTED` | Server started | host, port, max_connections, timestamp |
| `EVENT_SERVER_STOPPED` | Server stopped | reason, timestamp |
| `EVENT_SESSION_STARTED` | New session created | session_id, client_address, psk_identity |
| `EVENT_SESSION_ENDED` | Session closed | session_id, reason, duration |
| `EVENT_HANDSHAKE_COMPLETED` | TLS handshake success | client_address, psk_identity, cipher_suite, protocol_version, handshake_duration_ms |
| `EVENT_HANDSHAKE_FAILED` | TLS handshake failed | client_address, error, alert |
| `EVENT_APDU_RECEIVED` | APDU command received | session_id, apdu_hex |
| `EVENT_APDU_SENT` | APDU response sent | session_id, response_hex, sw |
| `EVENT_PSK_MISMATCH` | Unknown PSK identity | identity, client_address |
| `EVENT_CONNECTION_INTERRUPTED` | Connection unexpectedly interrupted | session_id, error |
| `EVENT_HIGH_ERROR_RATE` | Error rate threshold exceeded | rate, threshold |

---

## Database-Backed Deployment

### Complete Server Setup with Database

This section demonstrates a complete production deployment using the database layer for PSK key management, session persistence, and audit logging.

#### Prerequisites

```bash
# Install with database support
pip install cardlink[server,database]

# Initialize database
gp-db init

# Run migrations
gp-db migrate
```

#### Step 1: Configure Database

```bash
# Set database URL (PostgreSQL recommended for production)
export DATABASE_URL="postgresql://user:pass@localhost:5432/cardlink"

# Or use SQLite for simple deployments
export DATABASE_URL="sqlite:///data/cardlink.db"

# Verify database
gp-db status
```

#### Step 2: Provision Card Profiles

```python
from cardlink.database import get_unit_of_work
from cardlink.database.models import CardProfile, Device

# Create Unit of Work
with get_unit_of_work() as uow:
    # Add devices
    device1 = Device(
        iccid="89012345678901234567",
        imsi="123456789012345",
        msisdn="+1234567890",
        device_model="Test Phone 1"
    )
    uow.devices.add(device1)

    # Create card profile with PSK credentials
    profile1 = CardProfile(
        name="Production Profile 001",
        psk_identity="card_8901234567890123456",
        psk_key=bytes.fromhex("0123456789ABCDEF0123456789ABCDEF"),
        admin_url="https://192.168.1.100:8443/admin",
        metadata={
            'environment': 'production',
            'operator': 'MNO_001'
        }
    )
    uow.cards.add(profile1)

    # Commit changes
    uow.commit()

    print(f"Created device: {device1.id}")
    print(f"Created profile: {profile1.id}")
```

#### Step 3: Start Server with Database Integration

```python
#!/usr/bin/env python3
"""Production server with database integration."""

from cardlink.server import (
    AdminServer,
    ServerConfig,
    CipherConfig,
    DatabaseKeyStore,
    EventEmitter,
    EVENT_SESSION_STARTED,
    EVENT_SESSION_ENDED,
    EVENT_APDU_RECEIVED,
    EVENT_APDU_SENT,
)
from cardlink.database import get_unit_of_work
from cardlink.database.models import OTASession, SessionStatus, CommLog, CommDirection
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database integration
uow = get_unit_of_work()

# Create event emitter
event_emitter = EventEmitter()

# Track session mapping (external session ID -> database session ID)
session_map = {}

# Event handlers for database persistence
def on_session_started(event_data):
    """Create database record when session starts."""
    with uow:
        # Find device by PSK identity
        device = uow.devices.get_by_iccid(event_data['psk_identity'])

        if device:
            # Create session record
            session = OTASession(
                device_id=device.id,
                session_type="admin",
                status=SessionStatus.IN_PROGRESS,
                metadata={
                    'external_session_id': event_data['session_id'],
                    'client_ip': event_data['client_address'][0],
                    'client_port': event_data['client_address'][1],
                }
            )
            uow.sessions.add(session)
            uow.commit()

            # Map external session ID to database ID
            session_map[event_data['session_id']] = session.id

            logger.info(f"Session {session.id} started for device {device.iccid}")

def on_apdu_received(event_data):
    """Log received APDU to database."""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            log = CommLog(
                session_id=session_map[external_id],
                direction=CommDirection.RECEIVED,
                apdu_command=bytes.fromhex(event_data['apdu_hex']),
                timestamp=datetime.utcnow()
            )
            uow.logs.add(log)
            uow.commit()

def on_apdu_sent(event_data):
    """Log sent APDU response to database."""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            log = CommLog(
                session_id=session_map[external_id],
                direction=CommDirection.SENT,
                apdu_response=bytes.fromhex(event_data['response_hex']),
                duration_ms=event_data.get('duration_ms', 0),
                timestamp=datetime.utcnow()
            )
            uow.logs.add(log)
            uow.commit()

def on_session_ended(event_data):
    """Update session when complete."""
    external_id = event_data['session_id']
    if external_id in session_map:
        with uow:
            session = uow.sessions.get(session_map[external_id])
            if session:
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.utcnow()
                uow.sessions.update(session)
                uow.commit()

            logger.info(f"Session {session.id} completed")

            # Clean up mapping
            del session_map[external_id]

# Subscribe event handlers
event_emitter.subscribe(EVENT_SESSION_STARTED, on_session_started)
event_emitter.subscribe(EVENT_APDU_RECEIVED, on_apdu_received)
event_emitter.subscribe(EVENT_APDU_SENT, on_apdu_sent)
event_emitter.subscribe(EVENT_SESSION_ENDED, on_session_ended)

# Start event emitter
event_emitter.start()

# Server configuration
cipher_config = CipherConfig(
    enable_legacy=False,
    enable_null_ciphers=False,
)

config = ServerConfig(
    host="0.0.0.0",
    port=8443,
    max_connections=500,
    session_timeout=300.0,
    handshake_timeout=30.0,
    thread_pool_size=50,
    cipher_config=cipher_config,
    log_level="INFO",
)

# Create database-backed key store
with uow:
    key_store = DatabaseKeyStore(uow.cards)

# Create and start server
server = AdminServer(
    config=config,
    key_store=key_store,
    event_emitter=event_emitter,
)

logger.info("Starting GP OTA Admin Server with database integration...")
logger.info(f"Server: {config.host}:{config.port}")
logger.info(f"Database: {uow.session.bind.url}")

try:
    server.start()
    logger.info("Server started successfully")

    # Keep running
    import time
    while server.is_running:
        time.sleep(1)

except KeyboardInterrupt:
    logger.info("Shutting down...")
finally:
    server.stop()
    event_emitter.stop()
    logger.info("Server stopped")
```

#### Step 4: Monitor Sessions

```bash
# View active sessions
gp-db stats

# Export session data
gp-db export sessions_$(date +%Y%m%d).yaml

# View session logs
python -c "
from cardlink.database import get_unit_of_work

with get_unit_of_work() as uow:
    sessions = uow.sessions.find_recent(hours=1)
    for s in sessions:
        print(f'Session {s.id}: {s.status.value}')
        logs = uow.logs.get_by_session(s.id)
        print(f'  APDU count: {len(logs)}')
"
```

### Database Maintenance

```bash
# Daily backup
gp-db export --format yaml --output backup_$(date +%Y%m%d).yaml

# Clean up old logs (keep 30 days)
gp-db cleanup --days 30 --confirm

# View statistics
gp-db stats
```

### Production Deployment Checklist

- [ ] Database initialized and migrated
- [ ] Database backups configured
- [ ] Card profiles provisioned with PSK credentials
- [ ] Server config file created (no hardcoded keys)
- [ ] Firewall rules configured
- [ ] SSL/TLS certificates installed (if using reverse proxy)
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] Event handlers tested
- [ ] Database cleanup scheduled

---

## Example Configuration Files

### Development (server-dev.yaml)

```yaml
host: "127.0.0.1"
port: 8443
max_connections: 10
session_timeout: 600.0
handshake_timeout: 60.0
keys_file: "dev-keys.yaml"
log_level: "DEBUG"

ciphers:
  enable_legacy: true
  enable_null_ciphers: true  # For debugging
```

### Production (server-prod.yaml)

```yaml
host: "0.0.0.0"
port: 8443
max_connections: 500
session_timeout: 300.0
handshake_timeout: 30.0
thread_pool_size: 50
keys_file: "/etc/cardlink/keys.yaml"
log_level: "WARNING"

ciphers:
  enable_legacy: false
  enable_null_ciphers: false
```

### Test Keys (dev-keys.yaml)

```yaml
# Development/Testing PSK Keys
# DO NOT USE IN PRODUCTION

keys:
  # Test cards
  test_card_001: "00112233445566778899AABBCCDDEEFF"
  test_card_002: "FFEEDDCCBBAA99887766554433221100"

  # GlobalPlatform default test key
  gp_default: "404142434445464748494A4B4C4D4E4F"

  # Debug identity
  debug: "00000000000000000000000000000000"
```

---

## Support

For issues and feature requests, please visit:
https://github.com/veenone/cardlink/issues
