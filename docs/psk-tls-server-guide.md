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
- [Key Management](#key-management)
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

### Supported Cipher Suites

| Cipher Suite | Security Level | Use Case |
|--------------|----------------|----------|
| `TLS_PSK_WITH_AES_128_CBC_SHA256` | Production | Recommended default |
| `TLS_PSK_WITH_AES_256_CBC_SHA384` | Production | High security |
| `TLS_PSK_WITH_AES_128_CBC_SHA` | Legacy | Compatibility |
| `TLS_PSK_WITH_AES_256_CBC_SHA` | Legacy | Compatibility |
| `TLS_PSK_WITH_NULL_SHA` | Testing Only | No encryption |
| `TLS_PSK_WITH_NULL_SHA256` | Testing Only | No encryption |

---

## Prerequisites

### System Requirements

- Python 3.9 or higher
- Linux, macOS, or Windows
- Network access for client connections

### Required Dependencies

Install the base package and PSK-TLS support:

```bash
pip install gp-ota-tester[psk]
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
pip install gp-ota-tester

# With PSK-TLS server support
pip install gp-ota-tester[server]

# Full installation with all features
pip install gp-ota-tester[all]
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
gp-ota-server --help

# Check PSK support
python -c "from gp_ota_tester.server import HAS_PSK_SUPPORT; print(f'PSK Support: {HAS_PSK_SUPPORT}')"
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

#### ServerConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | str | `"0.0.0.0"` | Bind address |
| `port` | int | `8443` | Listen port |
| `max_connections` | int | `100` | Maximum concurrent connections |
| `session_timeout` | float | `300.0` | Session timeout in seconds |
| `handshake_timeout` | float | `30.0` | TLS handshake timeout |
| `backlog` | int | `5` | Socket listen backlog |
| `thread_pool_size` | int | `10` | Worker thread count |

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
from gp_ota_tester.server import MemoryKeyStore

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
```

#### Database Key Store

For production deployments with database backend:

```python
from gp_ota_tester.server import DatabaseKeyStore
from gp_ota_tester.database import CardRepository, get_session

# Create database session
session = get_session()
repository = CardRepository(session)

# Create key store
key_store = DatabaseKeyStore(repository)
```

---

### Cipher Suite Selection

#### Production Ciphers (Default)

Secure cipher suites for production use:

```bash
gp-ota-server start --ciphers production
```

Enables:
- `TLS_PSK_WITH_AES_128_CBC_SHA256`
- `TLS_PSK_WITH_AES_256_CBC_SHA384`

#### Legacy Ciphers

For compatibility with older clients:

```bash
gp-ota-server start --ciphers legacy
```

Adds:
- `TLS_PSK_WITH_AES_128_CBC_SHA`
- `TLS_PSK_WITH_AES_256_CBC_SHA`

#### All Ciphers

Enable all production and legacy ciphers:

```bash
gp-ota-server start --ciphers all
```

#### NULL Ciphers (Testing Only)

For debugging without encryption (traffic is in plaintext):

```bash
gp-ota-server start --enable-null-ciphers
```

Adds:
- `TLS_PSK_WITH_NULL_SHA`
- `TLS_PSK_WITH_NULL_SHA256`

**WARNING**: NULL ciphers provide NO encryption. Use only in isolated test environments.

---

## Running the Server

### Command Line Interface

#### Start Server

```bash
# Start with defaults (localhost:8443)
gp-ota-server start --keys keys.yaml -f

# Start on all interfaces
gp-ota-server start --host 0.0.0.0 --port 8443 --keys keys.yaml -f

# Start with configuration file
gp-ota-server start --config server.yaml -f

# Start with verbose logging
gp-ota-server -v start --keys keys.yaml -f

# Start with debug logging
gp-ota-server --debug start --keys keys.yaml -f

# Start with legacy cipher support
gp-ota-server start --keys keys.yaml --ciphers legacy -f

# Start with custom connection limits
gp-ota-server start --keys keys.yaml --max-connections 50 --session-timeout 600 -f
```

The `-f` (foreground) flag keeps the server running in the terminal. Press `Ctrl+C` to stop.

#### Check Server Status

```bash
gp-ota-server status
```

#### Stop Server

```bash
# Graceful shutdown
gp-ota-server stop

# Force immediate shutdown
gp-ota-server stop --force

# Custom timeout
gp-ota-server stop --timeout 10
```

### Programmatic Usage

#### Basic Server Setup

```python
from gp_ota_tester.server import (
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
)

# Create server configuration
config = ServerConfig(
    host="0.0.0.0",
    port=8443,
    max_connections=100,
    session_timeout=300.0,
    handshake_timeout=30.0,
    cipher_config=cipher_config,
)

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
from gp_ota_tester.server import (
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
)

# Create event emitter
event_emitter = EventEmitter()

# Register event handlers
@event_emitter.on(EVENT_SERVER_STARTED)
def on_server_started(event_data):
    print(f"Server started: {event_data}")

@event_emitter.on(EVENT_HANDSHAKE_COMPLETED)
def on_handshake(event_data):
    print(f"TLS handshake completed:")
    print(f"  Client: {event_data['client_address']}")
    print(f"  Identity: {event_data['psk_identity']}")
    print(f"  Cipher: {event_data['cipher_suite']}")

@event_emitter.on(EVENT_SESSION_STARTED)
def on_session_started(event_data):
    print(f"New session: {event_data['session_id']}")

@event_emitter.on(EVENT_APDU_RECEIVED)
def on_apdu_received(event_data):
    print(f"APDU received: {event_data['apdu_hex']}")

@event_emitter.on(EVENT_PSK_MISMATCH)
def on_psk_mismatch(event_data):
    print(f"PSK mismatch for identity: {event_data['identity']}")

# Start emitter
event_emitter.start()

# Use with server
server = AdminServer(config, key_store, event_emitter)
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

# Get connection count
print(f"Active connections: {server.get_connection_count()}")
print(f"Active sessions: {server.get_session_count()}")
```

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
   gp-ota-server start --host 127.0.0.1

   # Specific interface (production)
   gp-ota-server start --host 192.168.1.100
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
pip install gp-ota-tester[server]
```

#### "Failed to bind to address"

```bash
# Check if port is in use
lsof -i :8443
netstat -tlnp | grep 8443

# Use a different port
gp-ota-server start --port 9443
```

#### "Unknown PSK identity"

1. Verify identity in key store:
   ```bash
   grep "identity_name" keys.yaml
   ```

2. Check key store is loaded:
   ```bash
   gp-ota-server -v start --keys keys.yaml
   ```

3. Verify UICC PSK configuration matches

#### "TLS handshake timeout"

1. Increase timeout:
   ```bash
   gp-ota-server start --handshake-timeout 60
   ```

2. Check network connectivity
3. Verify client TLS configuration

#### "Cipher suite mismatch"

1. Enable legacy ciphers:
   ```bash
   gp-ota-server start --ciphers all
   ```

2. Check client supported ciphers
3. Verify OpenSSL PSK support

### Debug Logging

Enable verbose logging for troubleshooting:

```bash
# Verbose mode
gp-ota-server -v start --keys keys.yaml

# Debug mode (very verbose)
gp-ota-server --debug start --keys keys.yaml
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
    backlog: int = 5
    thread_pool_size: int = 10
    cipher_config: CipherConfig = field(default_factory=CipherConfig)
    enable_dashboard: bool = False
    dashboard_port: int = 8080
    key_store_path: Optional[str] = None
    log_level: str = "INFO"
```

### CipherConfig

```python
@dataclass
class CipherConfig:
    production_ciphers: List[str]  # AES-CBC-SHA256/384
    legacy_ciphers: List[str]      # AES-CBC-SHA
    null_ciphers: List[str]        # NULL ciphers (testing)
    enable_legacy: bool = False
    enable_null_ciphers: bool = False

    def get_enabled_ciphers(self) -> List[str]: ...
    def get_openssl_cipher_string(self) -> str: ...
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
    ): ...

    def start(self) -> None: ...
    def stop(self, timeout: float = 5.0) -> None: ...

    @property
    def is_running(self) -> bool: ...

    def get_active_sessions(self) -> List[Session]: ...
    def get_session_count(self) -> int: ...
    def get_connection_count(self) -> int: ...
```

### Event Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `EVENT_SERVER_STARTED` | Server started | host, port, max_connections, timestamp |
| `EVENT_SERVER_STOPPED` | Server stopped | reason, timestamp |
| `EVENT_SESSION_STARTED` | New session created | session_id, client_address, psk_identity |
| `EVENT_SESSION_ENDED` | Session closed | session_id, reason, duration |
| `EVENT_HANDSHAKE_COMPLETED` | TLS handshake success | client_address, psk_identity, cipher_suite |
| `EVENT_HANDSHAKE_FAILED` | TLS handshake failed | client_address, error, alert |
| `EVENT_APDU_RECEIVED` | APDU command received | session_id, apdu_hex |
| `EVENT_APDU_SENT` | APDU response sent | session_id, response_hex, sw |
| `EVENT_PSK_MISMATCH` | Unknown PSK identity | identity, client_address |

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
keys_file: "/etc/gp-ota-server/keys.yaml"
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
