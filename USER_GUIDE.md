# CardLink User Guide

**Version 1.0.0**

A comprehensive GlobalPlatform Amendment B (SCP81) UICC test platform with mobile phone integration.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Installation](#installation)
4. [Architecture Overview](#architecture-overview)
5. [Configuration](#configuration)
6. [CLI Reference](#cli-reference)
7. [Component Guides](#component-guides)
8. [Workflows](#workflows)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)
11. [API Reference](#api-reference)
12. [Appendices](#appendices)

---

## Introduction

### What is CardLink?

CardLink is a GlobalPlatform Amendment B (SCP81) test platform designed for testing UICC Over-The-Air (OTA) functionality using real mobile devices. It provides:

- **PSK-TLS Server**: Secure communication with UICC cards using PSK-TLS
- **Mobile Simulator**: Virtual UICC for testing without physical hardware
- **Phone Controller**: ADB-based control of Android devices
- **Database Layer**: Persistent storage for sessions, logs, and test results
- **Web Dashboard**: Real-time monitoring and interactive testing
- **Observability**: Comprehensive metrics, tracing, and health monitoring

### Key Features

✅ **PSK-TLS Authentication** - Secure pre-shared key TLS connections
✅ **Real Device Testing** - Control Android phones via ADB
✅ **Virtual Simulation** - Test without physical hardware
✅ **Database Persistence** - SQLite, MySQL, PostgreSQL support
✅ **Real-time Dashboard** - WebSocket-based monitoring
✅ **Comprehensive Logging** - APDU-level communication logs
✅ **Test Automation** - Automated test execution and reporting

### Who Should Use This?

- **UICC Developers**: Testing GlobalPlatform card applications
- **Mobile Network Operators**: Validating OTA provisioning
- **Security Researchers**: Analyzing UICC communication protocols
- **Test Engineers**: Automated testing of card applets

---

## Getting Started

### Prerequisites

**Required:**
- Python 3.9 or higher
- Git

**For Physical Device Testing:**
- Android phone with USB debugging enabled
- ADB (Android Debug Bridge) installed
- USB cable

**For Card Provisioning:**
- PC/SC-compatible smart card reader
- pyscard library dependencies

### Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/cardlink.git
cd cardlink

# 2. Install CardLink
pip install -e .

# 3. Initialize the database
gp-db init

# 4. Start the mobile simulator
gp-simulator start --config examples/simulator/basic_config.yaml

# 5. Open the web dashboard
gp-dashboard start
# Open http://localhost:8080 in your browser
```

You should now see the dashboard monitoring the virtual UICC simulator!

### Your First Test Session

```bash
# Start the PSK-TLS admin server
gp-server start --port 8443 --psk-key 000102030405060708090A0B0C0D0E0F

# In another terminal, send a test trigger
gp-simulator trigger --session-id test-001

# View the APDU logs
gp-db export --format json --tables comm_logs | jq
```

---

## Installation

### Standard Installation

```bash
# Basic installation
pip install cardlink

# Install with all optional dependencies
pip install cardlink[all]

# Install for development
git clone https://github.com/yourusername/cardlink.git
cd cardlink
pip install -e ".[dev]"
```

### Component-Specific Installation

Install only what you need:

```bash
# Server components only
pip install cardlink[psk,server,database]

# Mobile simulation
pip install cardlink[simulator]

# Phone control
pip install cardlink[phone]

# Card provisioning
pip install cardlink[pcsc]

# Database with MySQL
pip install cardlink[database,mysql]

# Database with PostgreSQL
pip install cardlink[database,postgresql]
```

### Verifying Installation

```bash
# Check CLI tools are available
gp-server --version
gp-db --version
gp-simulator --version
gp-dashboard --version

# Test database connectivity
gp-db status

# Test server configuration
gp-server --help
```

### System Dependencies

**Linux (Ubuntu/Debian):**
```bash
# For PC/SC card reader support
sudo apt-get install pcscd libpcsclite-dev

# For ADB support
sudo apt-get install adb

# For development
sudo apt-get install python3-dev build-essential
```

**macOS:**
```bash
# Using Homebrew
brew install pcsc-lite
brew install android-platform-tools

# For development
brew install python@3.9
```

**Windows:**
- Download and install [Python 3.9+](https://www.python.org/downloads/)
- Install [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- PC/SC support is built into Windows

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CardLink Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  PSK-TLS     │    │   Mobile     │    │     Web      │  │
│  │   Server     │◄───┤  Simulator   │───►│  Dashboard   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Database Layer (SQLite/MySQL/PG)          │ │
│  └────────────────────────────────────────────────────────┘ │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    Phone     │    │    Modem     │    │ Provisioner  │  │
│  │  Controller  │    │  Controller  │    │   (PC/SC)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
└─────────┼────────────────────┼────────────────────┼──────────┘
          │                    │                    │
          ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Android  │        │   IoT    │        │   UICC   │
    │  Phone   │        │  Modem   │        │   Card   │
    └──────────┘        └──────────┘        └──────────┘
```

### Component Overview

| Component | Purpose | Technology |
|-----------|---------|------------|
| **PSK-TLS Server** | Secure UICC communication | sslpsk3, asyncio |
| **Mobile Simulator** | Virtual UICC testing | Python, HTTP/TLS |
| **Phone Controller** | Android device control | ADB, AT commands |
| **Database Layer** | Data persistence | SQLAlchemy, Alembic |
| **Web Dashboard** | Monitoring UI | HTML/CSS/JS, WebSocket |
| **Provisioner** | Card configuration | PC/SC, pyscard |
| **Observability** | Metrics & monitoring | Prometheus, OpenTelemetry |

### Data Flow

1. **Session Initialization**: UICC (real or virtual) connects to PSK-TLS server
2. **Authentication**: PSK-TLS handshake establishes secure channel
3. **Command Exchange**: APDU commands flow between server and UICC
4. **Logging**: All communications logged to database
5. **Dashboard Updates**: Real-time updates via WebSocket
6. **Metrics**: Prometheus metrics track performance and health

---

## Configuration

### Environment Variables

CardLink uses environment variables for configuration:

#### Database Configuration

```bash
# Database URL (overrides all other DB settings)
export DATABASE_URL="sqlite:///data/cardlink.db"
# or
export DATABASE_URL="mysql://user:password@localhost/cardlink"
# or
export DATABASE_URL="postgresql://user:password@localhost/cardlink"

# Component-based configuration (if DATABASE_URL not set)
export CARDLINK_DB_HOST="localhost"
export CARDLINK_DB_PORT="3306"
export CARDLINK_DB_NAME="cardlink"
export CARDLINK_DB_USER="cardlink_user"
export CARDLINK_DB_PASSWORD="secure_password"
export CARDLINK_DB_DRIVER="mysql"  # or postgresql, sqlite
```

#### Server Configuration

```bash
# PSK-TLS Server
export CARDLINK_SERVER_HOST="0.0.0.0"
export CARDLINK_SERVER_PORT="8443"
export CARDLINK_PSK_KEY="000102030405060708090A0B0C0D0E0F"

# Dashboard
export CARDLINK_DASHBOARD_PORT="8080"
export CARDLINK_DASHBOARD_HOST="0.0.0.0"
```

#### Security Configuration

```bash
# Encryption key for PSK storage (REQUIRED for card provisioning)
export CARDLINK_ENCRYPTION_KEY="your-32-byte-base64-key-here"

# Generate a new encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Configuration Files

#### Simulator Configuration

`simulator_config.yaml`:
```yaml
simulator:
  iccid: "8944501234567890123"
  imsi: "234501234567890"

  psk:
    identity: "test-uicc-001"
    key: "000102030405060708090A0B0C0D0E0F"

  admin_url: "https://localhost:8443/admin"

  behavior:
    auto_connect: true
    retry_interval: 5
    max_retries: 3

  security_domains:
    - aid: "A000000151000000"
      type: "ISD"
```

#### Database Configuration

Create `database.yaml` for non-environment configuration:
```yaml
database:
  url: "sqlite:///data/cardlink.db"
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  echo: false
```

### CLI Configuration Commands

```bash
# View current database configuration
gp-db status

# Export configuration
gp-db export --format yaml --output config_backup.yaml

# Import configuration
gp-db import config_backup.yaml --conflict merge
```

---

## CLI Reference

### Server Commands

#### `gp-server`

Start and manage the PSK-TLS admin server.

```bash
# Start server with default settings
gp-server start

# Start with custom port and PSK key
gp-server start --port 8443 --psk-key 000102030405060708090A0B0C0D0E0F

# Start with configuration file
gp-server start --config server_config.yaml

# Options:
#   --host TEXT           Bind address (default: 0.0.0.0)
#   --port INTEGER        Port number (default: 8443)
#   --psk-key TEXT       PSK key in hex format (required)
#   --cert FILE          TLS certificate file
#   --key FILE           TLS private key file
#   --config FILE        Configuration file
#   --daemon             Run as daemon
#   --pid-file FILE      PID file location
```

### Database Commands

#### `gp-db`

Manage the CardLink database.

```bash
# Initialize database (create tables)
gp-db init

# Initialize with force (drop existing tables)
gp-db init --force

# Show database status
gp-db status

# Show verbose status with table row counts
gp-db status --verbose

# Export data
gp-db export --format yaml --output backup.yaml
gp-db export --format json --tables devices,sessions

# Import data
gp-db import backup.yaml --conflict merge
gp-db import backup.json --dry-run

# Clean up old data
gp-db cleanup --days 30 --yes

# Show statistics
gp-db stats

# Run migrations
gp-db migrate --revision head
gp-db migrate --dry-run

# Rollback migration
gp-db rollback --revision -1 --yes

# Show migration history
gp-db history
```

### Simulator Commands

#### `gp-simulator`

Control the mobile UICC simulator.

```bash
# Start simulator
gp-simulator start --config simulator_config.yaml

# Start with inline configuration
gp-simulator start --iccid 8944501234567890123 --psk-key 000102...

# Send trigger (initiate session)
gp-simulator trigger --session-id test-001

# Show simulator status
gp-simulator status

# Stop simulator
gp-simulator stop

# Options for start:
#   --config FILE         Configuration file
#   --iccid TEXT         ICCID of the virtual card
#   --imsi TEXT          IMSI of the virtual card
#   --psk-identity TEXT  PSK identity
#   --psk-key TEXT       PSK key in hex
#   --admin-url TEXT     Admin server URL
#   --behavior FILE      Behavior configuration
```

### Phone Commands

#### `gp-phone`

Control Android devices via ADB.

```bash
# Connect to phone
gp-phone connect

# Connect to specific device
gp-phone connect --serial ABC123456

# Check SIM status
gp-phone sim-status

# WiFi management
gp-phone wifi connect "SSID" "password"
gp-phone wifi status
gp-phone wifi scan

# Send trigger SMS
gp-phone trigger --tar 000001

# Monitor BIP events
gp-phone monitor --timeout 30

# Execute AT command
gp-phone at "AT+CIMI"

# Options:
#   --serial TEXT        Device serial number
#   --timeout INTEGER    Command timeout in seconds
```

### Provisioner Commands

#### `gp-provision`

Provision UICC cards via PC/SC reader.

```bash
# List available readers
gp-provision readers

# Provision card with PSK
gp-provision setup --psk-key 000102... --admin-url https://server:8443/admin

# Read card information
gp-provision info

# Inject PSK credentials
gp-provision psk --identity test-uicc-001 --key 000102...

# Configure admin URL
gp-provision url --admin-url https://server:8443/admin

# Options:
#   --reader TEXT        Reader name (default: first available)
#   --iccid TEXT        ICCID for verification
```

### Dashboard Commands

#### `gp-dashboard`

Manage the web dashboard.

```bash
# Start dashboard server
gp-dashboard start

# Start on custom port
gp-dashboard start --port 8080 --host 0.0.0.0

# Check dashboard status
gp-dashboard status

# Open dashboard in browser
gp-dashboard open

# Options:
#   --host TEXT          Bind address (default: 0.0.0.0)
#   --port INTEGER       Port number (default: 8080)
#   --daemon            Run as daemon
```

### Test Commands

#### `gp-test`

Run automated tests.

```bash
# Run all tests
gp-test run

# Run specific test suite
gp-test run examples/test_suites/basic.yaml

# Run with verbose output
gp-test run --verbose

# Generate test report
gp-test report --run-id abc123 --format html --output report.html

# Options:
#   --suite FILE         Test suite file
#   --device TEXT        Device to use for testing
#   --parallel INTEGER   Number of parallel tests
#   --output DIR         Output directory for results
```

---

## Component Guides

### PSK-TLS Server

#### Starting the Server

```bash
# Basic start
gp-server start --port 8443 --psk-key 000102030405060708090A0B0C0D0E0F

# With custom certificate
gp-server start --cert server.crt --key server.key --psk-key 000102...

# With PID file for management
gp-server start --daemon --pid-file /var/run/cardlink-server.pid
```

#### Server Configuration

Create `server_config.yaml`:
```yaml
server:
  host: "0.0.0.0"
  port: 8443

  psk:
    default_key: "000102030405060708090A0B0C0D0E0F"

  tls:
    cert_file: "certs/server.crt"
    key_file: "certs/server.key"
    cipher_suites:
      - "TLS-PSK-WITH-AES-256-GCM-SHA384"
      - "TLS-PSK-WITH-AES-128-GCM-SHA256"

  sessions:
    timeout: 300  # 5 minutes
    max_concurrent: 100

  logging:
    level: "INFO"
    apdu_logging: true
```

#### Monitoring Sessions

```bash
# View active sessions
gp-db export --format json --tables ota_sessions | jq '.[] | select(.status == "active")'

# View session logs
gp-db export --format json --tables comm_logs | jq

# Real-time monitoring via dashboard
gp-dashboard open
```

### Mobile Simulator

#### Configuration

`simulator_config.yaml`:
```yaml
simulator:
  # Card identification
  iccid: "8944501234567890123"
  imsi: "234501234567890"
  card_type: "UICC"
  atr: "3B9F95801FC78031E073FE211B674A357E8AB400"

  # PSK credentials
  psk:
    identity: "test-uicc-001"
    key: "000102030405060708090A0B0C0D0E0F"

  # Server connection
  admin_url: "https://localhost:8443/admin"

  # Behavior configuration
  behavior:
    auto_connect: true          # Auto-connect on startup
    retry_interval: 5           # Retry interval in seconds
    max_retries: 3             # Max connection retries
    session_timeout: 300        # Session timeout in seconds
    response_delay_ms: 50       # Simulated processing delay

  # Security domains
  security_domains:
    - aid: "A000000151000000"
      type: "ISD"
      keys:
        - type: "AES"
          version: 0x01
          id: 0x01
          value: "404142434445464748494A4B4C4D4E4F"

    - aid: "A0000001515350"
      type: "Supplementary"

  # Trigger configuration
  trigger:
    tar: "000001"
    sms_config:
      format: "SMS-PP"
      udhi: true
```

#### Running the Simulator

```bash
# Start with configuration file
gp-simulator start --config examples/simulator/basic_config.yaml

# Monitor simulator logs
tail -f logs/simulator.log

# Send trigger
gp-simulator trigger --session-id test-001

# Check simulator status
gp-simulator status
```

#### Simulator Behavior Modes

The simulator supports different behavior profiles:

**Normal Mode** (default):
- Standard APDU processing
- Realistic response times
- Proper status words

**Error Mode**:
```yaml
behavior:
  error_rate: 0.1  # 10% of commands fail
  error_types:
    - "6A82"  # File not found
    - "6985"  # Conditions not satisfied
```

**Slow Mode**:
```yaml
behavior:
  response_delay_ms: 500  # 500ms delay per command
  timeout_rate: 0.05      # 5% of commands timeout
```

### Database Layer

#### Database Backends

**SQLite** (Default):
```bash
export DATABASE_URL="sqlite:///data/cardlink.db"
gp-db init
```

**MySQL**:
```bash
# Install MySQL driver
pip install cardlink[mysql]

# Configure connection
export DATABASE_URL="mysql://cardlink:password@localhost/cardlink"
gp-db init
```

**PostgreSQL**:
```bash
# Install PostgreSQL driver
pip install cardlink[postgresql]

# Configure connection
export DATABASE_URL="postgresql://cardlink:password@localhost/cardlink"
gp-db init
```

#### Database Migrations

```bash
# Check current migration status
gp-db history

# Run pending migrations
gp-db migrate

# Rollback one migration
gp-db rollback --revision -1

# Rollback to specific revision
gp-db rollback --revision abc123
```

#### Data Export/Import

```bash
# Export all data
gp-db export --format yaml --output backup.yaml

# Export specific tables
gp-db export --format json --tables devices,sessions,comm_logs --output session_data.json

# Import with conflict resolution
gp-db import backup.yaml --conflict merge

# Preview import (dry run)
gp-db import backup.yaml --dry-run
```

#### PSK Encryption

PSK keys are encrypted at rest:

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set encryption key
export CARDLINK_ENCRYPTION_KEY="your-generated-key"

# PSK keys are automatically encrypted when stored
```

### Web Dashboard

#### Accessing the Dashboard

```bash
# Start dashboard
gp-dashboard start --port 8080

# Open in browser
gp-dashboard open
# or visit http://localhost:8080
```

#### Dashboard Features

**Session Monitoring**:
- Real-time session list
- Active/completed/failed status
- Session details and timeline

**APDU Log Viewer**:
- Color-coded by direction (command/response)
- Hex/ASCII toggle
- Filtering by session, command, status
- Copy to clipboard

**Command Builder**:
- Manual APDU construction
- Command templates (SELECT, GET STATUS, etc.)
- Real-time hex preview
- Send through active session

**Settings**:
- Theme (light/dark)
- Hex format (uppercase/lowercase/grouped)
- Timestamp format (relative/local/UTC)
- Auto-scroll toggle
- Max entries limit

#### Dashboard Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Open command builder |
| `Ctrl+L` | Clear APDU log |
| `Ctrl+,` | Open settings |
| `Ctrl+R` | Refresh session list |
| `/` | Focus search filter |
| `Esc` | Close modal/clear selection |

---

## Workflows

### Workflow 1: Virtual UICC Testing

Test OTA functionality without physical hardware.

```bash
# Step 1: Initialize database
gp-db init

# Step 2: Start PSK-TLS server
gp-server start --port 8443 --psk-key 000102030405060708090A0B0C0D0E0F

# Step 3: Start dashboard (optional, in new terminal)
gp-dashboard start

# Step 4: Start mobile simulator (in new terminal)
gp-simulator start --config examples/simulator/basic_config.yaml

# Step 5: Monitor via dashboard
# Open http://localhost:8080

# Step 6: Send trigger to initiate session
gp-simulator trigger --session-id test-001

# Step 7: View results
gp-db export --format json --tables ota_sessions,comm_logs | jq
```

### Workflow 2: Physical Phone Testing

Test with real Android device and UICC.

```bash
# Prerequisites:
# - Android phone with USB debugging enabled
# - Phone connected via USB
# - UICC provisioned with PSK credentials

# Step 1: Verify phone connection
adb devices
gp-phone connect

# Step 2: Check SIM status
gp-phone sim-status

# Step 3: Connect phone to WiFi network
gp-phone wifi connect "TestNetwork" "password"

# Step 4: Start PSK-TLS server
gp-server start --port 8443 --psk-key <your-psk-key>

# Step 5: Send SMS trigger to initiate session
gp-phone trigger --tar 000001

# Step 6: Monitor BIP events
gp-phone monitor --timeout 60

# Step 7: View session in dashboard
gp-dashboard open
```

### Workflow 3: Card Provisioning

Configure a UICC card for OTA testing.

```bash
# Prerequisites:
# - PC/SC smart card reader
# - UICC card with GlobalPlatform support
# - Encryption key configured

# Step 1: Set encryption key
export CARDLINK_ENCRYPTION_KEY="your-encryption-key"

# Step 2: List available readers
gp-provision readers

# Step 3: Read card information
gp-provision info

# Step 4: Provision PSK credentials
gp-provision psk \
  --identity test-uicc-001 \
  --key 000102030405060708090A0B0C0D0E0F

# Step 5: Configure admin URL
gp-provision url --admin-url https://192.168.1.100:8443/admin

# Step 6: Verify configuration
gp-provision info

# Step 7: Store card profile in database
# (automatically done during provisioning)

# Step 8: Export card profile for backup
gp-db export --format yaml --tables card_profiles --output card_backup.yaml
```

### Workflow 4: Automated Testing

Run automated test suites.

```bash
# Step 1: Create test suite
cat > my_test_suite.yaml << EOF
name: "Basic OTA Test Suite"
description: "Tests basic OTA functionality"

tests:
  - name: "SELECT ISD"
    description: "Select Issuer Security Domain"
    apdu: "00A4040000"
    expected_sw: "9000"

  - name: "GET STATUS"
    description: "Get card status"
    apdu: "80F21000024F0000"
    expected_sw: "9000"
EOF

# Step 2: Run test suite
gp-test run my_test_suite.yaml --verbose

# Step 3: Generate HTML report
gp-test report --run-id $(date +%Y%m%d_%H%M%S) --format html --output test_report.html

# Step 4: View test results in database
gp-db stats
```

### Workflow 5: Production Monitoring

Set up monitoring for production deployment.

```bash
# Step 1: Configure metrics
export CARDLINK_METRICS_ENABLED=true
export CARDLINK_METRICS_PORT=9090

# Step 2: Start server with metrics
gp-server start --enable-metrics

# Step 3: Verify metrics endpoint
curl http://localhost:9090/metrics

# Step 4: Configure health checks
export CARDLINK_HEALTH_ENABLED=true
export CARDLINK_HEALTH_PORT=8081

# Step 5: Check health endpoints
curl http://localhost:8081/health
curl http://localhost:8081/health/live
curl http://localhost:8081/health/ready

# Step 6: Set up Prometheus scraping
# Add to prometheus.yml:
# scrape_configs:
#   - job_name: 'cardlink'
#     static_configs:
#       - targets: ['localhost:9090']

# Step 7: Import Grafana dashboards
# (Dashboard JSON files in observability/dashboards/)
```

---

## Troubleshooting

### Common Issues

#### Issue: Database connection fails

**Symptoms:**
```
DatabaseError: Failed to initialize database: (OperationalError) ...
```

**Solutions:**
```bash
# 1. Check DATABASE_URL is set correctly
echo $DATABASE_URL

# 2. For MySQL/PostgreSQL, verify server is running
# MySQL:
systemctl status mysql
# PostgreSQL:
systemctl status postgresql

# 3. Test connection manually
# MySQL:
mysql -h localhost -u cardlink -p
# PostgreSQL:
psql -h localhost -U cardlink -d cardlink

# 4. Initialize database if needed
gp-db init

# 5. Check database status
gp-db status --verbose
```

#### Issue: PSK-TLS handshake fails

**Symptoms:**
```
TLS handshake failed: PSK identity not found
```

**Solutions:**
```bash
# 1. Verify PSK key is correct
gp-server start --psk-key 000102030405060708090A0B0C0D0E0F

# 2. Check PSK identity matches
# In simulator config:
cat simulator_config.yaml | grep -A 2 "psk:"

# 3. Enable TLS debugging
export SSLKEYLOGFILE=/tmp/sslkeys.log
gp-server start --verbose

# 4. Check supported cipher suites
openssl ciphers -v 'PSK'
```

#### Issue: ADB device not found

**Symptoms:**
```
RuntimeError: No ADB devices found
```

**Solutions:**
```bash
# 1. Check ADB is installed
adb version

# 2. Check USB debugging is enabled on phone
adb devices

# 3. Restart ADB server
adb kill-server
adb start-server
adb devices

# 4. Check USB connection
lsusb  # Linux
system_profiler SPUSBDataType  # macOS

# 5. Verify device authorization
# Check phone screen for authorization prompt
```

#### Issue: PC/SC reader not detected

**Symptoms:**
```
No readers found
```

**Solutions:**
```bash
# 1. Check pcscd service is running
# Linux:
systemctl status pcscd
systemctl start pcscd

# 2. List readers
pcsc_scan

# 3. Check reader connection
lsusb | grep -i smart

# 4. Install required libraries
# Ubuntu/Debian:
sudo apt-get install pcscd libpcsclite-dev

# 5. Test with gp-provision
gp-provision readers
```

#### Issue: Dashboard not loading

**Symptoms:**
- Dashboard shows blank page
- WebSocket connection fails

**Solutions:**
```bash
# 1. Check dashboard server is running
gp-dashboard status

# 2. Verify port is not in use
lsof -i :8080  # Linux/macOS
netstat -ano | findstr :8080  # Windows

# 3. Check firewall rules
# Allow port 8080 inbound

# 4. Test WebSocket connection
wscat -c ws://localhost:8080/ws

# 5. Check browser console for errors
# Open DevTools (F12) -> Console
```

### Error Messages

#### Database Errors

**Error: "PSK key encryption failed"**
```bash
# Solution: Set CARDLINK_ENCRYPTION_KEY
export CARDLINK_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

**Error: "Migration failed: version conflict"**
```bash
# Solution: Check migration history and resolve conflicts
gp-db history
gp-db rollback --revision -1
gp-db migrate
```

#### Server Errors

**Error: "Address already in use"**
```bash
# Solution: Find and kill process using the port
lsof -ti:8443 | xargs kill -9  # Linux/macOS
netstat -ano | findstr :8443   # Windows (note PID and kill)

# Or use a different port
gp-server start --port 8444
```

**Error: "SSL certificate verification failed"**
```bash
# Solution: Use self-signed cert or disable verification
gp-server start --cert server.crt --key server.key

# For testing only:
export PYTHONHTTPSVERIFY=0
```

### Debugging

#### Enable Debug Logging

```bash
# Set log level to DEBUG
export CARDLINK_LOG_LEVEL=DEBUG

# Enable SQL echo
export CARDLINK_DB_ECHO=true

# Enable APDU logging
gp-server start --apdu-logging

# View logs
tail -f logs/cardlink.log
```

#### Trace APDU Communication

```bash
# Export APDU logs
gp-db export --format json --tables comm_logs | jq

# Filter by session
gp-db export --format json --tables comm_logs | jq '.[] | select(.session_id == "abc123")'

# View in dashboard with detailed view
gp-dashboard open
```

#### Network Debugging

```bash
# Capture TLS traffic
sudo tcpdump -i any -s 0 -w cardlink.pcap port 8443

# Analyze with Wireshark
wireshark cardlink.pcap

# Test connectivity
curl -k https://localhost:8443/health
```

### Performance Issues

#### High Memory Usage

```bash
# Check database connection pool
gp-db status --verbose

# Reduce pool size in DATABASE_URL or config

# Clean up old logs
gp-db cleanup --days 7

# Monitor with observability
curl http://localhost:9090/metrics | grep memory
```

#### Slow APDU Response

```bash
# Check database performance
gp-db stats

# Enable query logging
export CARDLINK_DB_ECHO=true

# Check system resources
top
htop

# Review dashboard performance
# Open DevTools -> Performance tab
```

---

## Advanced Topics

### Custom Security Domains

Configure multiple security domains:

```yaml
security_domains:
  - aid: "A000000151000000"
    type: "ISD"
    keys:
      - type: "AES"
        version: 0x01
        id: 0x01
        value: "404142434445464748494A4B4C4D4E4F"
      - type: "AES"
        version: 0x01
        id: 0x02
        value: "505152535455565758595A5B5C5D5E5F"

  - aid: "A0000001515350"
    type: "Supplementary"
    privileges: "0x80"  # Security Domain
```

### Multi-Device Testing

Test with multiple devices simultaneously:

```bash
# Start server
gp-server start

# Connect device 1
gp-phone connect --serial ABC123

# Connect device 2 (in another terminal)
gp-phone connect --serial DEF456

# Monitor all devices
gp-dashboard open
```

### Custom Test Assertions

Create custom test assertions:

```python
# my_assertions.py
from cardlink.testing import Assertion

class CustomAssertion(Assertion):
    def evaluate(self, response):
        # Custom validation logic
        return response.data.startswith(b'\x61')
```

### Extending the Dashboard

Add custom dashboard widgets:

```javascript
// custom_widget.js
class CustomWidget {
    constructor(container) {
        this.container = container;
    }

    render(data) {
        // Custom visualization
    }
}

// Register widget
app.registerWidget('custom', CustomWidget);
```

---

## API Reference

### Python API

#### Database Access

```python
from cardlink.database import DatabaseManager, UnitOfWork

# Initialize database
manager = DatabaseManager()
manager.initialize()

# Use Unit of Work pattern
with UnitOfWork(manager) as uow:
    # Query devices
    devices = uow.devices.find_by_type('phone')

    # Query sessions
    sessions = uow.sessions.find_active()

    # Query logs
    logs = uow.logs.find_by_session(session_id)

    # Commit changes
    uow.commit()
```

#### Simulator Control

```python
from cardlink.simulator import MobileSimulator, SimulatorConfig

# Create simulator
config = SimulatorConfig(
    iccid="8944501234567890123",
    imsi="234501234567890",
    psk_identity="test-uicc-001",
    psk_key=bytes.fromhex("000102030405060708090A0B0C0D0E0F"),
    admin_url="https://localhost:8443/admin"
)

simulator = MobileSimulator(config)

# Start simulator
await simulator.start()

# Send trigger
await simulator.send_trigger()

# Get status
status = simulator.get_status()

# Stop simulator
await simulator.stop()
```

#### Server Integration

```python
from cardlink.server import AdminServer, ServerConfig

# Create server
config = ServerConfig(
    host="0.0.0.0",
    port=8443,
    psk_key=bytes.fromhex("000102030405060708090A0B0C0D0E0F")
)

server = AdminServer(config)

# Start server
await server.start()

# Handle custom events
@server.on_session_start
async def handle_session(session):
    print(f"Session started: {session.id}")

# Stop server
await server.stop()
```

### REST API

#### Session Endpoints

```bash
# List all sessions
GET /api/sessions
Response: [
  {
    "id": "abc123",
    "status": "active",
    "device_id": "phone-001",
    "started_at": "2025-01-15T10:30:00Z"
  }
]

# Get session details
GET /api/sessions/{id}
Response: {
  "id": "abc123",
  "status": "active",
  "cipher_suite": "TLS-PSK-WITH-AES-256-GCM-SHA384",
  "psk_identity": "test-uicc-001"
}

# Get session APDUs
GET /api/sessions/{id}/apdus
Response: [
  {
    "timestamp": "2025-01-15T10:30:01.123Z",
    "direction": "command",
    "data": "00A4040000",
    "decoded": "SELECT"
  }
]
```

#### Device Endpoints

```bash
# List devices
GET /api/devices
Response: [
  {
    "id": "phone-001",
    "type": "phone",
    "manufacturer": "Samsung",
    "model": "Galaxy S21"
  }
]

# Get device status
GET /api/devices/{id}/status
Response: {
  "connected": true,
  "last_seen": "2025-01-15T10:35:00Z"
}
```

---

## Appendices

### Appendix A: PSK Cipher Suites

Supported PSK-TLS cipher suites:

| Cipher Suite | Key Exchange | Encryption | MAC |
|--------------|--------------|------------|-----|
| TLS-PSK-WITH-AES-256-GCM-SHA384 | PSK | AES-256-GCM | SHA-384 |
| TLS-PSK-WITH-AES-128-GCM-SHA256 | PSK | AES-128-GCM | SHA-256 |
| TLS-PSK-WITH-AES-256-CBC-SHA384 | PSK | AES-256-CBC | SHA-384 |
| TLS-PSK-WITH-AES-128-CBC-SHA256 | PSK | AES-128-CBC | SHA-256 |

### Appendix B: APDU Status Words

Common status words:

| SW | Meaning |
|----|---------|
| 9000 | Success |
| 6282 | End of file reached |
| 6300 | Verification failed |
| 6581 | Memory failure |
| 6700 | Wrong length |
| 6882 | Secure messaging not supported |
| 6982 | Security status not satisfied |
| 6985 | Conditions of use not satisfied |
| 6A80 | Incorrect parameters |
| 6A82 | File not found |
| 6A86 | Incorrect P1 P2 |
| 6D00 | Instruction not supported |
| 6E00 | Class not supported |

### Appendix C: Environment Variables

Complete list of environment variables:

#### Database
- `DATABASE_URL` - Complete database URL
- `CARDLINK_DB_HOST` - Database host
- `CARDLINK_DB_PORT` - Database port
- `CARDLINK_DB_NAME` - Database name
- `CARDLINK_DB_USER` - Database username
- `CARDLINK_DB_PASSWORD` - Database password
- `CARDLINK_DB_DRIVER` - Database driver (mysql/postgresql/sqlite)
- `CARDLINK_DB_ECHO` - Enable SQL logging (true/false)
- `CARDLINK_ENCRYPTION_KEY` - Fernet encryption key for PSK storage

#### Server
- `CARDLINK_SERVER_HOST` - Server bind address
- `CARDLINK_SERVER_PORT` - Server port
- `CARDLINK_PSK_KEY` - Default PSK key (hex)
- `CARDLINK_TLS_CERT` - TLS certificate file path
- `CARDLINK_TLS_KEY` - TLS private key file path

#### Dashboard
- `CARDLINK_DASHBOARD_HOST` - Dashboard bind address
- `CARDLINK_DASHBOARD_PORT` - Dashboard port

#### Observability
- `CARDLINK_METRICS_ENABLED` - Enable Prometheus metrics
- `CARDLINK_METRICS_PORT` - Metrics endpoint port
- `CARDLINK_HEALTH_ENABLED` - Enable health checks
- `CARDLINK_HEALTH_PORT` - Health check port
- `CARDLINK_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

#### Simulator
- `CARDLINK_SIMULATOR_AUTO_START` - Auto-start simulator (true/false)
- `CARDLINK_SIMULATOR_CONFIG` - Default config file path

### Appendix D: File Locations

Default file and directory locations:

```
cardlink/
├── data/                    # Database and data files
│   ├── cardlink.db         # Default SQLite database
│   └── logs/               # Application logs
├── config/                 # Configuration files
│   ├── server.yaml
│   ├── simulator.yaml
│   └── database.yaml
├── certs/                  # TLS certificates
│   ├── server.crt
│   └── server.key
├── examples/               # Example configurations
│   ├── simulator/
│   └── test_suites/
└── logs/                   # Log files
    ├── cardlink.log
    ├── server.log
    └── simulator.log
```

### Appendix E: Glossary

**ADB** - Android Debug Bridge, tool for communicating with Android devices

**APDU** - Application Protocol Data Unit, command/response format for smart cards

**BIP** - Bearer Independent Protocol, protocol for card-initiated connections

**GlobalPlatform** - Standard for secure element management

**ICCID** - Integrated Circuit Card Identifier, unique SIM card number

**IMSI** - International Mobile Subscriber Identity, identifies mobile subscriber

**ISD** - Issuer Security Domain, primary security domain on UICC

**OTA** - Over-The-Air, remote card management protocol

**PC/SC** - Personal Computer/Smart Card, standard API for smart card readers

**PSK** - Pre-Shared Key, symmetric key authentication method

**SCP81** - Secure Channel Protocol 81, GlobalPlatform Amendment B protocol

**SMS-PP** - SMS Point-to-Point, message delivery to SIM card

**TAR** - Toolkit Application Reference, identifies card application

**TLS** - Transport Layer Security, cryptographic protocol

**UICC** - Universal Integrated Circuit Card, secure element in mobile devices

---

## Support and Contributing

### Getting Help

- **Documentation**: See `docs/` directory for detailed guides
- **Issues**: Report bugs at [GitHub Issues](https://github.com/yourusername/cardlink/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/yourusername/cardlink/discussions)

### Contributing

We welcome contributions! See `CONTRIBUTING.md` for guidelines.

### License

CardLink is released under the MIT License. See `LICENSE` file for details.

---

**CardLink User Guide v1.0.0**
*Last Updated: 2025-01-15*
