# GP OTA Tester User Guide

GlobalPlatform Amendment B (SCP81) UICC Test Platform with mobile phone integration.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Project Structure](#project-structure)
5. [Quick Start](#quick-start)
6. [CLI Commands](#cli-commands)
7. [Configuration](#configuration)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

GP OTA Tester is a comprehensive testing platform for GlobalPlatform SCP81 Over-The-Air (OTA) administration of UICC (Universal Integrated Circuit Card) smart cards. It provides:

- **PSK-TLS Admin Server**: Secure server for SCP81 OTA communication
- **Phone Controller**: Android device management via ADB for UICC testing
- **Modem Controller**: IoT cellular modem management for M2M testing
- **UICC Provisioner**: PC/SC smart card provisioning with SCP02/SCP03 secure channels
- **Database Layer**: SQLAlchemy-based storage for test results and PSK keys
- **Web Dashboard**: Real-time monitoring of APDU traffic and test sessions

---

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, or Windows

### Optional Hardware

- **Android Phone**: For phone-based UICC testing (with USB debugging enabled)
- **Smart Card Reader**: PC/SC compatible reader for UICC provisioning
- **IoT Modem**: Serial-connected cellular modem for M2M testing

### Software Dependencies

For Android device control:
```bash
# Install Android Debug Bridge (ADB)
# Ubuntu/Debian
sudo apt install android-tools-adb

# Arch Linux
sudo pacman -S android-tools

# macOS
brew install android-platform-tools

# Windows: Download from Android SDK Platform Tools
```

For smart card provisioning (PC/SC):
```bash
# Ubuntu/Debian
sudo apt install pcscd pcsc-tools libpcsclite-dev

# Arch Linux
sudo pacman -S pcsclite ccid

# Start PC/SC daemon
sudo systemctl start pcscd
sudo systemctl enable pcscd
```

---

## Installation

### From Source (Development)

1. **Clone the repository**:
   ```bash
   git clone git@github.com:veenone/cardlink.git
   cd cardlink
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install the package**:

   Basic installation (core features):
   ```bash
   pip install -e .
   ```

   With PSK-TLS server support:
   ```bash
   pip install -e ".[server]"
   ```

   With all features:
   ```bash
   pip install -e ".[all]"
   ```

### Installation Options

The package provides optional dependency groups:

| Group        | Description                              | Command                        |
|--------------|------------------------------------------|--------------------------------|
| `psk`        | PSK-TLS support (sslpsk3)                | `pip install -e ".[psk]"`      |
| `server`     | Full server support with validation      | `pip install -e ".[server]"`   |
| `database`   | SQLAlchemy ORM and Alembic migrations    | `pip install -e ".[database]"` |
| `mysql`      | MySQL database driver                    | `pip install -e ".[mysql]"`    |
| `postgresql` | PostgreSQL database driver               | `pip install -e ".[postgresql]"`|
| `pcsc`       | PC/SC smart card support (pyscard)       | `pip install -e ".[pcsc]"`     |
| `phone`      | Android ADB libraries                    | `pip install -e ".[phone]"`    |
| `modem`      | Serial modem support (pyserial)          | `pip install -e ".[modem]"`    |
| `dev`        | Development tools (pytest, mypy, etc.)   | `pip install -e ".[dev]"`      |
| `docs`       | Documentation generation (mkdocs)        | `pip install -e ".[docs]"`     |
| `all`        | All optional dependencies                | `pip install -e ".[all]"`      |

### Verify Installation

```bash
# Check installed CLI commands
gp-server --help
gp-phone --help
gp-modem --help
gp-db --help
gp-dashboard --help
```

---

## Project Structure

```
cardlink/
├── src/cardlink/
│   ├── __init__.py           # Package version
│   ├── cli/                   # CLI commands
│   │   ├── server.py         # gp-server / gp-ota-server
│   │   ├── phone.py          # gp-phone
│   │   ├── modem.py          # gp-modem
│   │   ├── db.py             # gp-db
│   │   └── dashboard.py      # gp-dashboard
│   ├── server/                # PSK-TLS Admin Server
│   │   ├── admin_server.py   # Main server class
│   │   ├── tls_handler.py    # TLS connection handler
│   │   ├── key_store.py      # PSK key storage backends
│   │   └── config.py         # Server configuration
│   ├── phone/                 # Android Phone Controller
│   │   ├── controller.py     # PhoneController class
│   │   ├── device.py         # Device abstraction
│   │   └── adb_client.py     # ADB communication
│   ├── modem/                 # IoT Modem Controller
│   │   ├── controller.py     # ModemController class
│   │   └── serial_client.py  # Serial AT commands
│   ├── provisioner/           # UICC Provisioner (PC/SC)
│   │   ├── pcsc_client.py    # PC/SC reader interface
│   │   ├── apdu_interface.py # APDU command helpers
│   │   ├── secure_domain.py  # GlobalPlatform Security Domain
│   │   ├── scp02.py          # SCP02 secure channel
│   │   ├── scp03.py          # SCP03 secure channel
│   │   └── tlv_parser.py     # BER-TLV parsing
│   ├── database/              # Database Layer
│   │   ├── manager.py        # DatabaseManager
│   │   └── models.py         # SQLAlchemy models
│   └── dashboard/             # Web Dashboard
│       └── server.py         # Dashboard HTTP server
├── examples/
│   └── configs/               # Example configuration files
│       ├── server_config.yaml
│       └── psk_keys.yaml
├── tests/                     # Test suite
├── docs/                      # Documentation
└── pyproject.toml            # Project configuration
```

---

## Quick Start

### 1. Start the PSK-TLS Server

```bash
# Copy example configuration
cp examples/configs/server_config.yaml config.yaml
cp examples/configs/psk_keys.yaml keys.yaml

# Start the server
gp-server start --config config.yaml --keys keys.yaml
```

### 2. List Connected Android Phones

```bash
# Ensure ADB is running
adb start-server

# List devices
gp-phone list
```

### 3. Initialize Database

```bash
# Using default SQLite
gp-db init

# Using PostgreSQL
gp-db --database postgresql://user:pass@localhost/cardlink init
```

### 4. Start Web Dashboard

```bash
gp-dashboard start --open
```

---

## CLI Commands

### gp-server / gp-ota-server

PSK-TLS Admin Server for SCP81 OTA administration.

```bash
# Start server with defaults
gp-server start

# Start with custom configuration
gp-server start --config server_config.yaml --keys psk_keys.yaml

# Start on specific host/port
gp-server start --host 0.0.0.0 --port 8443

# Enable debug logging
gp-server start --verbose

# Validate configuration without starting
gp-server validate --config server_config.yaml
```

### gp-phone

Android phone control and monitoring via ADB.

```bash
# List connected devices
gp-phone list

# Show device info
gp-phone info <serial>

# Show all info (device, SIM, network)
gp-phone info <serial> --all

# Send AT command
gp-phone at <serial> "AT+CPIN?"

# Monitor device events
gp-phone monitor <serial>

# Save device profile
gp-phone profile save <serial> my_phone

# Load device profile
gp-phone profile load my_phone

# Output as JSON
gp-phone list --json
gp-phone info <serial> --json
```

### gp-modem

IoT cellular modem control and monitoring.

```bash
# List connected modems
gp-modem list

# Show modem info
gp-modem info /dev/ttyUSB2

# Send AT command
gp-modem at /dev/ttyUSB2 "ATI"

# Monitor modem
gp-modem monitor /dev/ttyUSB2
```

### gp-db

Database management commands.

```bash
# Initialize database (create tables)
gp-db init

# Force recreate (drops existing tables)
gp-db init --force

# Check database status
gp-db status

# Export data to YAML
gp-db export --format yaml --output backup.yaml

# Export to JSON
gp-db export --format json --output backup.json

# Import data
gp-db import backup.yaml

# Use custom database URL
gp-db --database postgresql://user:pass@localhost/db status
```

### gp-dashboard

Web-based monitoring dashboard.

```bash
# Start dashboard on default port (8080)
gp-dashboard start

# Custom host and port
gp-dashboard start --host 0.0.0.0 --port 3000

# Open browser automatically
gp-dashboard start --open
```

---

## Configuration

### Server Configuration (server_config.yaml)

```yaml
# Network settings
host: "127.0.0.1"      # Bind address
port: 8443             # Listen port
backlog: 5             # Connection backlog

# Connection handling
max_connections: 10    # Max concurrent connections
read_timeout: 30.0     # HTTP read timeout (seconds)
handshake_timeout: 30.0 # TLS handshake timeout

# Session management
session_timeout: 300.0 # Idle session timeout

# PSK key store
keys_file: "psk_keys.yaml"

# Cipher suites
cipher_config:
  enable_production: true   # AES-CBC-SHA256/SHA384
  enable_legacy: false      # AES-CBC-SHA (older clients)
  enable_null_ciphers: false # DANGER: No encryption

# Logging
logging:
  level: "INFO"         # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Security monitoring
security:
  mismatch_window: 60.0      # PSK mismatch tracking window
  mismatch_threshold: 3      # Trigger warning after N mismatches
  error_rate_window: 300.0   # Error rate monitoring window
  error_rate_threshold: 10   # High error rate alert threshold

# Event emission
events:
  enabled: true
  queue_size: 1000
```

### PSK Keys Configuration (psk_keys.yaml)

```yaml
# Format: identity: hex_encoded_key

# Test cards (16-byte / 128-bit keys)
test_card_001: "0102030405060708090A0B0C0D0E0F10"
test_card_002: "1112131415161718191A1B1C1D1E1F20"

# 32-byte / 256-bit key
test_card_003: "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"

# Production cards (use secure random keys)
# card_ICCID_12345678901234567890: "YOUR_SECURE_KEY_HEX"
```

### Environment Variables

```bash
# Server configuration
export GP_OTA_SERVER_HOST="0.0.0.0"
export GP_OTA_SERVER_PORT="8443"
export GP_OTA_SERVER_CONFIG="/etc/gp-ota/config.yaml"

# Database URL
export DATABASE_URL="postgresql://user:pass@localhost/cardlink"
```

---

## Usage Examples

### Example 1: Basic OTA Server Setup

```bash
# Create configuration
mkdir -p ~/.config/gp-ota
cat > ~/.config/gp-ota/config.yaml << 'EOF'
host: "127.0.0.1"
port: 8443
keys_file: "~/.config/gp-ota/keys.yaml"
cipher_config:
  enable_production: true
EOF

# Generate PSK key
python -c "import secrets; print(f'my_card: \"{secrets.token_hex(16)}\"')" > ~/.config/gp-ota/keys.yaml

# Start server
gp-server start --config ~/.config/gp-ota/config.yaml
```

### Example 2: Android Phone Testing Workflow

```bash
# 1. Discover connected devices
gp-phone list

# 2. Get device details
gp-phone info ABC123456789 --all

# 3. Check SIM status
gp-phone at ABC123456789 "AT+CPIN?"

# 4. Monitor for OTA events
gp-phone monitor ABC123456789
```

### Example 3: Programmatic Usage

```python
import asyncio
from cardlink.phone import PhoneController

async def main():
    # Create controller
    controller = PhoneController()

    # Discover devices
    devices = await controller.discover_devices()
    print(f"Found {len(devices)} devices")

    # Get specific device
    if devices:
        phone = await controller.get_device(devices[0].serial)
        profile = await phone.info.get_full_profile()
        print(f"Model: {profile.device.model}")
        print(f"ICCID: {profile.sim.iccid}")

asyncio.run(main())
```

### Example 4: UICC Provisioning (PC/SC)

```python
from cardlink.provisioner import (
    PCSCClient, APDUInterface, SecureDomainManager,
    SCP02, SCPKeys
)

# Connect to card
client = PCSCClient()
readers = client.list_readers()
client.connect(readers[0])

# Create APDU interface
apdu = APDUInterface(client.transmit)

# Create secure domain manager
sd = SecureDomainManager(client.transmit)

# Select ISD
response = sd.select_isd()
print(f"ISD selected: SW={response.sw:04X}")

# Establish SCP02 secure channel
keys = SCPKeys(
    enc=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    mac=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    dek=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
)
scp02 = SCP02(client.transmit)
scp02.initialize(keys)

# Now all commands are secured with C-MAC
apps = sd.get_status_apps()
for app in apps:
    print(f"AID: {app.aid.hex().upper()}")

client.disconnect()
```

### Example 5: Database Integration

```python
from cardlink.database import DatabaseManager, DatabaseConfig

# Configure database
config = DatabaseConfig(url="sqlite:///data/cardlink.db")
db = DatabaseManager(config)
db.initialize()
db.create_tables()

# Use database...

db.close()
```

---

## Troubleshooting

### PSK-TLS Server Issues

**Server fails to start with "Address already in use"**:
```bash
# Check what's using the port
lsof -i :8443
# or
netstat -tlnp | grep 8443

# Use a different port
gp-server start --port 9443
```

**SSL handshake fails**:
- Ensure client and server use matching PSK identity and key
- Check cipher suite compatibility
- Verify TLS version (requires TLS 1.2)

### Android ADB Issues

**No devices shown by `gp-phone list`**:
```bash
# Check ADB server
adb devices

# Restart ADB
adb kill-server
adb start-server

# Check USB connection
lsusb | grep -i android
```

**Device shows as "unauthorized"**:
1. Enable USB debugging on phone
2. Accept the RSA fingerprint prompt on phone
3. Run `adb devices` again

### PC/SC Smart Card Issues

**No readers found**:
```bash
# Check pcscd service
sudo systemctl status pcscd

# Start pcscd
sudo systemctl start pcscd

# List readers
pcsc_scan
```

**Card not responding**:
- Ensure card is properly inserted
- Try a different reader
- Check card ATR with `pcsc_scan`

### Database Issues

**SQLite "database is locked"**:
- Close other connections to the database
- Use WAL mode for concurrent access

**PostgreSQL connection refused**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection settings
psql -h localhost -U user -d cardlink
```

### General Tips

**Enable verbose logging**:
```bash
gp-server start --verbose
gp-phone --verbose list
```

**Check Python dependencies**:
```bash
pip list | grep -E "sslpsk|pyscard|pyserial|adb"
```

**Reinstall with all dependencies**:
```bash
pip install -e ".[all]" --force-reinstall
```

---

## Additional Documentation

- [PSK-TLS Server Guide](psk-tls-server-guide.md) - Detailed PSK-TLS server setup and configuration

---

## License

This project is licensed under the MIT License.
