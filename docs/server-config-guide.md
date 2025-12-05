# PSK-TLS Server Configuration Guide

This guide explains how to configure and use the PSK-TLS Admin Server using configuration files.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration File Format](#configuration-file-format)
- [PSK Keys File Format](#psk-keys-file-format)
- [Configuration Priority](#configuration-priority)
- [Command-Line Options](#command-line-options)
- [Environment Variables](#environment-variables)
- [Examples](#examples)
- [Validation](#validation)

---

## Quick Start

### 1. Install with PSK-TLS Support

The PSK-TLS server requires the `sslpsk3` library:

```bash
# Install with PSK-TLS support
pip install cardlink[server]

# Or install with all optional dependencies
pip install cardlink[all]

# Or install only PSK support (minimal)
pip install cardlink[psk]
```

### 2. Create Configuration Files

Copy the example configuration files:

```bash
# Server configuration
cp examples/configs/server_config.yaml my_server.yaml

# PSK keys
cp examples/configs/psk_keys.yaml my_keys.yaml
```

### 3. Edit Your Keys File

Edit `my_keys.yaml` and add your PSK identities and keys:

```yaml
# PSK Keys Configuration
keys:
  # Format: identity: key (hex string, 16-32 bytes)
  "uicc001": "000102030405060708090A0B0C0D0E0F"
  "uicc002": "0F0E0D0C0B0A09080706050403020100"
```

### 4. Start the Server

```bash
# With config file
gp-server start --config my_server.yaml --keys my_keys.yaml

# Or with CLI options only
gp-server start --port 8443 --keys my_keys.yaml
```

---

## Configuration File Format

The server configuration file is a YAML file containing all server settings.

### Complete Example

```yaml
# Server Network Configuration
host: "127.0.0.1"         # Bind address (use 0.0.0.0 for all interfaces)
port: 8443                # Listen port
backlog: 5                # TCP listen backlog

# Connection Handling
max_connections: 10       # Maximum concurrent connections
read_timeout: 30.0        # HTTP request read timeout (seconds)
handshake_timeout: 30.0   # TLS handshake timeout (seconds)

# Session Management
session_timeout: 300.0    # Session inactivity timeout (seconds)

# PSK Key Store
keys_file: "psk_keys.yaml"  # Path to PSK keys file

# Cipher Suite Configuration
cipher_config:
  enable_production: true     # Enable AES-CBC-SHA256/384 ciphers
  enable_legacy: false        # Enable AES-CBC-SHA ciphers
  enable_null_ciphers: false  # DANGER: Enable NULL ciphers (no encryption!)

# Logging Configuration
logging:
  level: "INFO"             # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  # file: "/var/log/gp-server/server.log"  # Optional log file

# Security Settings
security:
  mismatch_window: 60.0         # PSK mismatch tracking window (seconds)
  mismatch_threshold: 3         # Mismatches to trigger brute-force warning
  error_rate_window: 300.0      # Error rate monitoring window (seconds)
  error_rate_threshold: 10      # Errors to trigger high error rate alert

# Event Emission
events:
  enabled: true             # Enable event emission
  queue_size: 1000         # Event queue size
```

### Configuration Sections

#### Network Configuration

```yaml
host: "127.0.0.1"    # Bind address
port: 8443           # Listen port
backlog: 5           # TCP backlog queue size
```

**Options:**
- `host`: IP address to bind to
  - `"127.0.0.1"` - localhost only (most secure)
  - `"0.0.0.0"` - all interfaces (use with firewall)
- `port`: TCP port (default 8443)
- `backlog`: Pending connection queue size

#### Connection Settings

```yaml
max_connections: 10       # Thread pool size
read_timeout: 30.0        # HTTP read timeout
handshake_timeout: 30.0   # TLS handshake timeout
```

**Options:**
- `max_connections`: Maximum concurrent client connections (each uses one thread)
- `read_timeout`: Timeout for reading HTTP requests
- `handshake_timeout`: Timeout for TLS handshake completion

#### Session Management

```yaml
session_timeout: 300.0    # 5 minutes
```

**Options:**
- `session_timeout`: Inactive sessions are closed after this time (seconds)

#### Cipher Configuration

```yaml
cipher_config:
  enable_production: true      # AES-128/256-CBC-SHA256/384
  enable_legacy: false         # AES-128/256-CBC-SHA
  enable_null_ciphers: false   # NULL ciphers (NO ENCRYPTION!)
```

**Cipher Suites by Category:**

| Category | Cipher Suites | Use Case |
|----------|---------------|----------|
| Production | TLS_PSK_WITH_AES_128_CBC_SHA256<br>TLS_PSK_WITH_AES_256_CBC_SHA384 | Production deployment |
| Legacy | TLS_PSK_WITH_AES_128_CBC_SHA<br>TLS_PSK_WITH_AES_256_CBC_SHA | Older clients |
| NULL | TLS_PSK_WITH_NULL_SHA256<br>TLS_PSK_WITH_NULL_SHA | **TESTING ONLY** |

⚠️ **WARNING:** NULL ciphers transmit data in plaintext with no encryption!

---

## PSK Keys File Format

The PSK keys file contains PSK identities and their corresponding keys.

### Example

```yaml
# PSK Keys Configuration
#
# Format:
#   identity: key
#
# Where:
#   - identity: UTF-8 string identifying the client
#   - key: Hex-encoded pre-shared key (16-32 bytes recommended)

keys:
  # Test keys
  "test_uicc": "000102030405060708090A0B0C0D0E0F"
  "debug_client": "FFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0"

  # Production keys (example format)
  "uicc_89123456789012345678": "0123456789ABCDEF0123456789ABCDEF"
  "uicc_89987654321098765432": "FEDCBA9876543210FEDCBA9876543210"
```

### Key Format Requirements

- **Identity**: UTF-8 string (typically ICCID or unique identifier)
- **Key**: Hex-encoded string (32-64 hex characters = 16-32 bytes)
  - Minimum: 16 bytes (32 hex chars) - AES-128
  - Recommended: 32 bytes (64 hex chars) - AES-256

### Key Generation

Generate secure random keys using Python:

```python
import secrets

# Generate 16-byte (128-bit) key
key_16 = secrets.token_hex(16)
print(f"AES-128 Key: {key_16}")

# Generate 32-byte (256-bit) key
key_32 = secrets.token_hex(32)
print(f"AES-256 Key: {key_32}")
```

Or using OpenSSL:

```bash
# 16-byte key
openssl rand -hex 16

# 32-byte key
openssl rand -hex 32
```

---

## Configuration Priority

Settings are applied in the following order (highest priority first):

1. **CLI Options** - `--port 9443`, `--host 0.0.0.0`, etc.
2. **Environment Variables** - `GP_OTA_SERVER_PORT`, `GP_OTA_SERVER_HOST`
3. **Configuration File** - `--config server.yaml`
4. **Built-in Defaults** - Hardcoded defaults in the code

### Example Priority

If you have:
- Config file: `port: 8443`
- Environment: `export GP_OTA_SERVER_PORT=9000`
- CLI option: `--port 9443`

The server will use port **9443** (CLI option wins).

---

## Command-Line Options

### Start Command

```bash
gp-server start [OPTIONS]
```

**Required:**
- None (can run with all defaults)

**Network Options:**
- `--host HOST` - Host to bind to (default: 127.0.0.1)
- `--port PORT` / `-p PORT` - Port to listen on (default: 8443)

**Configuration Options:**
- `--config FILE` / `-c FILE` - Path to YAML config file
- `--keys FILE` / `-k FILE` - Path to PSK keys YAML file

**Cipher Options:**
- `--ciphers {production|legacy|all}` - Cipher suite selection (default: production)
- `--enable-null-ciphers` - Enable NULL ciphers (NO ENCRYPTION!)

**Connection Options:**
- `--max-connections N` - Max concurrent connections (default: 10)
- `--session-timeout SECS` - Session timeout (default: 300)
- `--handshake-timeout SECS` - TLS handshake timeout (default: 30)

**Runtime Options:**
- `--foreground` / `-f` - Run in foreground (don't background)
- `--dashboard` - Enable web dashboard (requires dashboard module)

**Global Options:**
- `-v` / `--verbose` - Enable verbose logging
- `--debug` - Enable debug logging

### Other Commands

```bash
# Stop the server
gp-server stop [--timeout SECS] [--force]

# Check status
gp-server status

# Validate configuration
gp-server validate --config server.yaml [--keys keys.yaml]
```

---

## Environment Variables

Override configuration with environment variables:

```bash
# Set host
export GP_OTA_SERVER_HOST="0.0.0.0"

# Set port
export GP_OTA_SERVER_PORT="9443"

# Set default config file
export GP_OTA_SERVER_CONFIG="/etc/gp-server/server.yaml"

# Start server (uses environment variables)
gp-server start
```

---

## Examples

### Example 1: Basic Localhost Server

Minimal setup for local testing:

```bash
# Create minimal keys file
cat > keys.yaml << EOF
keys:
  "test": "000102030405060708090A0B0C0D0E0F"
EOF

# Start server
gp-server start --keys keys.yaml --foreground
```

### Example 2: Production Server with Config File

Create production config:

```yaml
# production.yaml
host: "0.0.0.0"
port: 8443
max_connections: 50
session_timeout: 600.0
keys_file: "production_keys.yaml"

cipher_config:
  enable_production: true
  enable_legacy: false
  enable_null_ciphers: false

logging:
  level: "WARNING"
  file: "/var/log/gp-server/server.log"
```

Start server:

```bash
gp-server start --config production.yaml
```

### Example 3: Debug Server with NULL Ciphers

For protocol debugging (NO ENCRYPTION):

```bash
gp-server start \
  --enable-null-ciphers \
  --foreground \
  --keys test_keys.yaml \
  --debug
```

### Example 4: Using Environment Variables

```bash
# Set environment
export GP_OTA_SERVER_HOST="192.168.1.100"
export GP_OTA_SERVER_PORT="8443"
export GP_OTA_SERVER_CONFIG="my_server.yaml"

# Start server
gp-server start
```

### Example 5: Multiple Cipher Suites

Support both modern and legacy clients:

```bash
gp-server start \
  --ciphers all \
  --keys keys.yaml \
  --max-connections 20
```

---

## Validation

Always validate configuration before deployment:

```bash
# Validate config file
gp-server validate --config server.yaml

# Validate config and keys
gp-server validate --config server.yaml --keys keys.yaml
```

**Output Example:**

```
Validating configuration: server.yaml
Configuration valid!
  Host: 0.0.0.0
  Port: 8443
  Max connections: 10
  Session timeout: 300.0s
  Handshake timeout: 30.0s

Validating key store: keys.yaml
Key store valid!
  Loaded 5 PSK identities
```

**Error Example:**

```
Validating configuration: bad_server.yaml
Configuration error: Invalid YAML in config file: ...
```

---

## Security Best Practices

### 1. Key Management

- ✅ Generate keys with cryptographically secure random generators
- ✅ Use minimum 16-byte (128-bit) keys
- ✅ Rotate keys regularly
- ❌ Never commit keys to version control
- ❌ Never use predictable or weak keys

### 2. Network Configuration

- ✅ Use `host: "127.0.0.1"` for localhost-only access
- ✅ Use firewall rules when binding to `0.0.0.0`
- ✅ Use reverse proxy (nginx) for production
- ❌ Don't expose server directly to internet without firewall

### 3. Cipher Configuration

- ✅ Use `enable_production: true` for production
- ✅ Disable NULL ciphers in production
- ⚠️ Only enable `enable_null_ciphers` for isolated debugging

### 4. Timeouts

- ✅ Set reasonable session timeouts (5-10 minutes)
- ✅ Set handshake timeouts (30 seconds is good)
- ❌ Don't use very long timeouts (resource exhaustion)

### 5. Logging

- ✅ Log to file in production
- ✅ Use appropriate log levels (WARNING/ERROR in prod)
- ✅ Rotate log files regularly
- ❌ Don't log sensitive data (keys, full APDUs)

---

## Troubleshooting

### Server Won't Start

**Problem:** `sslpsk3 library not installed`

**Solution:**
```bash
pip install sslpsk3
# or
pip install cardlink[server]
```

---

**Problem:** `Configuration error: Invalid YAML`

**Solution:**
```bash
# Validate YAML syntax
gp-server validate --config server.yaml
```

---

**Problem:** `Failed to set cipher suites`

**Solution:**
- Ensure sslpsk3 is installed correctly
- Check OpenSSL version supports PSK ciphers
- Don't mix standard SSL configuration with PSK

---

**Problem:** `Address already in use`

**Solution:**
```bash
# Check if server is already running
gp-server status

# Stop existing server
gp-server stop

# Or use different port
gp-server start --port 9443
```

---

**Problem:** `Permission denied (port < 1024)`

**Solution:**
```bash
# Use port >= 1024 (e.g., 8443)
gp-server start --port 8443

# Or run as root (not recommended)
sudo gp-server start --port 443
```

---

### Connection Issues

**Problem:** Client can't connect from remote host

**Solution:**
```yaml
# In config file, change:
host: "0.0.0.0"  # Accept from all interfaces

# Or use CLI:
gp-server start --host 0.0.0.0
```

---

**Problem:** TLS handshake timeout

**Solution:**
```yaml
# Increase handshake timeout
handshake_timeout: 60.0
```

---

**Problem:** PSK authentication failure

**Solution:**
- Verify key exists in keys file
- Check identity matches exactly
- Verify key is correct hex format
- Use `gp-server validate --keys keys.yaml`

---

## Additional Resources

- [PSK-TLS Server Guide](psk-tls-server-guide.md) - Detailed server documentation
- [User Guide](user-guide.md) - Overall platform usage
- [Example Configs](../examples/configs/) - More configuration examples
- GlobalPlatform SCP81 Specification - Official specification

---

## Quick Reference

### Install
```bash
pip install cardlink[server]
```

### Validate
```bash
gp-server validate --config server.yaml --keys keys.yaml
```

### Start
```bash
# With config file
gp-server start --config server.yaml

# With CLI options
gp-server start --port 8443 --keys keys.yaml

# Debug mode
gp-server start --enable-null-ciphers --foreground --debug
```

### Stop
```bash
gp-server stop
```

### Status
```bash
gp-server status
```
