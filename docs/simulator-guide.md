# Mobile Simulator User Guide

## Overview

The Mobile Simulator provides a software-based mobile phone and UICC card implementation for testing the PSK-TLS Admin Server without requiring physical hardware. This guide walks you through setting up, configuring, and running the simulator.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running the Simulator](#running-the-simulator)
- [Integration with PSK-TLS Server](#integration-with-psk-tls-server)
- [Testing Scenarios](#testing-scenarios)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 100MB minimum (for single simulator instance)
- **Network**: Local network access or localhost

### Required Components

- PSK-TLS Admin Server (running on localhost or accessible network)
- Python virtual environment (recommended)

## Installation

### Step 1: Install GP OTA Tester

Install the package with simulator dependencies:

```bash
# Using pip
pip install gp-ota-tester[simulator]

# Or from source
git clone <repository-url>
cd cardlink
pip install -e ".[simulator]"
```

### Step 2: Verify Installation

Test that the simulator CLI is available:

```bash
gp-simulator --help
```

You should see the simulator command options.

### Step 3: Verify Dependencies

The following dependencies should be installed automatically:

- `sslpsk3` - PSK-TLS support
- `pyyaml` - Configuration file parsing
- `click` - CLI framework
- `rich` - Terminal formatting

Verify by checking:

```bash
python -c "import sslpsk; import yaml; import click; import rich; print('All dependencies installed')"
```

## Quick Start

### 1. Start the PSK-TLS Server

First, ensure the PSK-TLS Admin Server is running:

```bash
# In a separate terminal
gp-server start --port 8443 --psk-key 0102030405060708090A0B0C0D0E0F10
```

The server should display:

```
PSK-TLS Admin Server started
Listening on: 0.0.0.0:8443
PSK identities loaded: 1
```

### 2. Test Server Connectivity

Verify the simulator can reach the server:

```bash
gp-simulator test-connection \
  --server 127.0.0.1:8443 \
  --psk-identity test_card \
  --psk-key 0102030405060708090A0B0C0D0E0F10
```

Expected output:

```
Testing connection to 127.0.0.1:8443...
PSK Identity: test_card

Connection successful!
  Cipher: TLS_PSK_WITH_AES_128_CBC_SHA256
  Protocol: TLSv1.2
  Handshake: 45.2ms
```

### 3. Run Your First Simulation

Execute a basic simulation session:

```bash
gp-simulator run \
  --server 127.0.0.1:8443 \
  --psk-identity test_card \
  --psk-key 0102030405060708090A0B0C0D0E0F10
```

Expected output:

```
Mobile Simulator
Server: 127.0.0.1:8443
PSK Identity: test_card
Mode: normal

Session 1
  Success: 5 APDUs, 0.32s, SW=9000

Summary
  Sessions: 1
  Successful: 1
  Failed: 0
  Total APDUs sent: 5
  Total APDUs received: 5
  Avg APDU time: 18.5ms
```

## Configuration

### Configuration File Structure

Create a configuration file to avoid passing parameters on the command line:

```bash
# Generate a sample configuration file
gp-simulator config-generate --output my-simulator.yaml
```

This creates `my-simulator.yaml` with all available options:

```yaml
# Mobile Simulator Configuration
# ================================

# Server connection settings
server:
  host: "127.0.0.1"
  port: 8443
  connect_timeout: 30.0
  read_timeout: 30.0
  retry_count: 3
  retry_backoff:
    - 1.0
    - 2.0
    - 4.0

# PSK-TLS credentials
psk:
  identity: "test_card_001"
  key: "0102030405060708090A0B0C0D0E0F10"

# Virtual UICC configuration
uicc:
  iccid: "8901234567890123456"
  imsi: "310150123456789"
  msisdn: "+14155551234"

  # GlobalPlatform settings
  gp:
    version: "2.2.1"
    scp_version: "03"
    isd_aid: "A000000151000000"

  # Pre-installed applets
  applets:
    - aid: "A0000001510001"
      name: "TestApplet"
      state: "SELECTABLE"
      privileges: "00"

# Simulation behavior
behavior:
  mode: "normal"  # normal, error, timeout
  response_delay_ms: 20

  error:
    rate: 0.0
    codes:
      - "6A82"
      - "6985"
      - "6D00"

  timeout:
    probability: 0.0
    delay_range:
      min: 1000
      max: 5000

  connection:
    mode: "single"
    batch_size: 5
    reconnect_after: 3
```

### Configuration Options Explained

#### Server Settings

| Option | Description | Default |
|--------|-------------|---------|
| `host` | Server hostname or IP address | `127.0.0.1` |
| `port` | Server port number | `8443` |
| `connect_timeout` | Connection timeout in seconds | `30.0` |
| `read_timeout` | Read timeout in seconds | `30.0` |
| `retry_count` | Number of connection retry attempts | `3` |
| `retry_backoff` | Backoff delays between retries (seconds) | `[1.0, 2.0, 4.0]` |

#### PSK Credentials

| Option | Description | Format |
|--------|-------------|--------|
| `identity` | PSK identity string | String (must match server) |
| `key` | PSK key | Hex string (16 or 32 bytes) |

**Important**: The PSK identity and key must match the server's configuration.

#### UICC Profile

| Option | Description | Example |
|--------|-------------|---------|
| `iccid` | Integrated Circuit Card ID | `8901234567890123456` |
| `imsi` | International Mobile Subscriber Identity | `310150123456789` |
| `msisdn` | Mobile number | `+14155551234` |
| `gp.version` | GlobalPlatform version | `2.2.1` |
| `gp.scp_version` | Secure Channel Protocol version | `03` |
| `gp.isd_aid` | Issuer Security Domain AID | `A000000151000000` |

#### Behavior Modes

The simulator supports three behavior modes:

**1. Normal Mode** - Standard operation
```yaml
behavior:
  mode: "normal"
  response_delay_ms: 20  # Realistic response time
```

**2. Error Mode** - Inject errors for testing error handling
```yaml
behavior:
  mode: "error"
  error:
    rate: 0.2  # 20% of responses will be errors
    codes:
      - "6A82"  # File not found
      - "6985"  # Conditions not satisfied
      - "6D00"  # INS not supported
```

**3. Timeout Mode** - Simulate slow or delayed responses
```yaml
behavior:
  mode: "timeout"
  timeout:
    probability: 0.1  # 10% of responses delayed
    delay_range:
      min: 1000  # 1 second minimum
      max: 5000  # 5 seconds maximum
```

## Running the Simulator

### Basic Usage

#### Using Configuration File

```bash
gp-simulator run --config my-simulator.yaml
```

#### Using Command-Line Options

```bash
gp-simulator run \
  --server 192.168.1.100:8443 \
  --psk-identity card_001 \
  --psk-key 0102030405060708090A0B0C0D0E0F10 \
  --mode normal
```

### Running Multiple Sessions

#### Sequential Sessions

Run multiple sessions one after another:

```bash
gp-simulator run --config my-simulator.yaml --count 10
```

This runs 10 sessions sequentially, showing results for each.

#### Parallel Sessions

Run multiple sessions simultaneously:

```bash
gp-simulator run --config my-simulator.yaml --count 10 --parallel
```

This launches 10 simulator instances in parallel, useful for load testing.

### Continuous Mode

Run the simulator continuously with intervals between sessions:

```bash
gp-simulator run \
  --config my-simulator.yaml \
  --loop \
  --interval 5.0
```

This runs sessions continuously with a 5-second interval. Press `Ctrl+C` to stop.

### Verbose Output

Enable detailed logging to see APDU exchanges:

```bash
gp-simulator run --config my-simulator.yaml -v
```

Verbose output includes:

```
Session 1
  Success: 5 APDUs, 0.32s, SW=9000
    SELECT: 00A4040007A0000001... -> SW=9000
    GET STATUS: 80F28000024F00... -> SW=9000
    GET DATA: 80CA006600... -> SW=9000
```

## Integration with PSK-TLS Server

### Step-by-Step Integration

#### 1. Configure Server PSK Keys

On the server, add the simulator's PSK credentials:

```bash
# In server configuration or key store
gp-server add-key \
  --identity test_card_001 \
  --key 0102030405060708090A0B0C0D0E0F10
```

Or in the server's configuration file:

```yaml
psk_keys:
  - identity: "test_card_001"
    key: "0102030405060708090A0B0C0D0E0F10"
```

#### 2. Start the Server

```bash
gp-server start --port 8443
```

Verify the server is listening:

```
PSK-TLS Admin Server started
Listening on: 0.0.0.0:8443
PSK identities loaded: 1
Press Ctrl+C to stop
```

#### 3. Configure Simulator

Create a configuration file matching the server settings:

```yaml
# simulator-config.yaml
server:
  host: "127.0.0.1"
  port: 8443

psk:
  identity: "test_card_001"
  key: "0102030405060708090A0B0C0D0E0F10"
```

#### 4. Test Connection

```bash
gp-simulator test-connection --config simulator-config.yaml
```

#### 5. Run Simulation

```bash
gp-simulator run --config simulator-config.yaml -v
```

### Monitoring Server and Simulator

Use two terminal windows to monitor both:

**Terminal 1 - Server:**
```bash
gp-server start --port 8443 --verbose
```

**Terminal 2 - Simulator:**
```bash
gp-simulator run --config simulator-config.yaml -v
```

Watch the APDU exchanges in both terminals to verify correct operation.

## Testing Scenarios

### Scenario 1: Normal Operation Test

**Objective**: Verify basic APDU processing works correctly.

**Configuration**:
```yaml
behavior:
  mode: "normal"
  response_delay_ms: 20
```

**Run**:
```bash
gp-simulator run --config normal-test.yaml --count 5
```

**Expected Result**: All 5 sessions complete successfully with SW=9000.

### Scenario 2: Error Handling Test

**Objective**: Test server's error handling capabilities.

**Configuration**:
```yaml
behavior:
  mode: "error"
  error:
    rate: 0.3  # 30% error rate
    codes: ["6A82", "6985"]
```

**Run**:
```bash
gp-simulator run --config error-test.yaml --count 10
```

**Expected Result**: Mix of successful (SW=9000) and error responses (6A82, 6985).

### Scenario 3: Timeout Handling Test

**Objective**: Test server timeout handling.

**Configuration**:
```yaml
behavior:
  mode: "timeout"
  timeout:
    probability: 0.2  # 20% delayed
    delay_range:
      min: 2000
      max: 4000
```

**Run**:
```bash
gp-simulator run --config timeout-test.yaml --count 10
```

**Expected Result**: Some responses delayed 2-4 seconds, server handles gracefully.

### Scenario 4: Load Testing

**Objective**: Test server under load with multiple concurrent connections.

**Run**:
```bash
gp-simulator run \
  --config load-test.yaml \
  --count 50 \
  --parallel
```

**Monitor**: Watch server CPU/memory usage and response times.

### Scenario 5: Connection Retry Test

**Objective**: Test connection retry logic.

**Setup**: Stop the server temporarily.

**Run**:
```bash
gp-simulator run --config retry-test.yaml
```

**Action**: Start the server while simulator is retrying.

**Expected Result**: Simulator eventually connects after retries.

## Monitoring and Debugging

### Viewing Statistics

After a simulation run, the summary shows:

```
Summary
  Sessions: 10
  Successful: 9
  Failed: 1
  Total APDUs sent: 45
  Total APDUs received: 45
  Avg APDU time: 18.5ms
```

### Session Details

With verbose mode (`-v`), see individual APDU exchanges:

```bash
gp-simulator run --config my-config.yaml -v
```

Output includes:

```
Session 1
  Success: 5 APDUs, 0.32s, SW=9000
    SELECT ISD-R: 00A4040007A000000151000000 -> SW=9000
    GET STATUS: 80F28000024F00 -> SW=9000
    GET DATA: 80CA006600 -> SW=9000
```

### Logging to File

Redirect output to a file for analysis:

```bash
gp-simulator run --config my-config.yaml -v 2>&1 | tee simulator.log
```

### Python API for Advanced Monitoring

For programmatic access to statistics:

```python
import asyncio
from cardlink.simulator import MobileSimulator, SimulatorConfig

async def monitor_session():
    config = SimulatorConfig.from_dict({
        "server": {"host": "127.0.0.1", "port": 8443},
        "psk": {
            "identity": "test_card",
            "key": "0102030405060708090A0B0C0D0E0F10"
        }
    })

    simulator = MobileSimulator(config)
    result = await simulator.run_complete_session()

    # Access detailed results
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"APDUs: {result.apdu_count}")

    # View APDU exchanges
    for exchange in result.exchanges:
        print(f"{exchange.description}: {exchange.sw} ({exchange.duration_ms:.1f}ms)")

    # Get statistics
    stats = simulator.get_statistics()
    print(f"Avg connection time: {stats.avg_connection_time_ms:.1f}ms")
    print(f"Avg APDU time: {stats.avg_apdu_response_time_ms:.1f}ms")

asyncio.run(monitor_session())
```

## Troubleshooting

### Common Issues

#### Issue 1: Connection Refused

**Symptom**:
```
Error: Connection refused
Connection failed after 3 attempts
```

**Solutions**:

1. **Check server is running**:
   ```bash
   # Check if server process is running
   ps aux | grep gp-server

   # Or check port is listening
   netstat -an | grep 8443
   ```

2. **Verify server address**:
   ```bash
   # Test with localhost
   gp-simulator test-connection --server 127.0.0.1:8443

   # Test with IP address
   gp-simulator test-connection --server 192.168.1.100:8443
   ```

3. **Check firewall**:
   ```bash
   # On Linux, check firewall rules
   sudo iptables -L | grep 8443

   # On Windows, check Windows Firewall settings
   ```

#### Issue 2: PSK Identity Not Found

**Symptom**:
```
Error: PSK identity not found
Handshake failed (not retrying)
```

**Solutions**:

1. **Verify PSK credentials match**:
   - Check identity spelling is exact
   - Verify key is correct hex string

2. **Check server configuration**:
   ```bash
   # View server's loaded PSK identities
   gp-server status
   ```

3. **Add identity to server**:
   ```bash
   gp-server add-key \
     --identity test_card \
     --key 0102030405060708090A0B0C0D0E0F10
   ```

#### Issue 3: Connection Timeout

**Symptom**:
```
Error: Connection timeout
State: TIMEOUT
```

**Solutions**:

1. **Increase timeout**:
   ```yaml
   server:
     connect_timeout: 60.0  # Increase to 60 seconds
     read_timeout: 60.0
   ```

2. **Check network latency**:
   ```bash
   ping -c 4 <server-address>
   ```

3. **Test with local server**:
   ```bash
   # Run server locally
   gp-server start --host 127.0.0.1 --port 8443

   # Connect simulator to localhost
   gp-simulator run --server 127.0.0.1:8443
   ```

#### Issue 4: All APDUs Return Errors

**Symptom**:
```
Session 1
  Success: 0 APDUs, SW=6A82
```

**Solutions**:

1. **Check behavior mode**:
   ```yaml
   behavior:
     mode: "normal"  # Should be "normal", not "error"
   ```

2. **Disable error injection**:
   ```yaml
   behavior:
     error:
       rate: 0.0  # Set to 0 to disable
   ```

#### Issue 5: Import Errors

**Symptom**:
```
ImportError: No module named 'sslpsk'
```

**Solutions**:

1. **Install simulator dependencies**:
   ```bash
   pip install gp-ota-tester[simulator]
   ```

2. **Verify virtual environment**:
   ```bash
   which python
   pip list | grep sslpsk
   ```

3. **Reinstall dependencies**:
   ```bash
   pip install --force-reinstall sslpsk3
   ```

## Advanced Usage

### Custom UICC Profiles

Create custom virtual UICC configurations:

```yaml
uicc:
  iccid: "8901234567890123456"
  imsi: "310150987654321"
  msisdn: "+14155559999"

  applets:
    - aid: "A0000001510001"
      name: "MyCustomApplet"
      state: "SELECTABLE"
      privileges: "01"

    - aid: "A0000001510002"
      name: "SecureApplet"
      state: "LOCKED"
      privileges: "80"
```

### Scripted Testing

Create a test script for automated testing:

```bash
#!/bin/bash
# test-simulator.sh

echo "Starting PSK-TLS Server..."
gp-server start --port 8443 &
SERVER_PID=$!
sleep 2

echo "Running normal mode test..."
gp-simulator run --config normal-test.yaml --count 5

echo "Running error injection test..."
gp-simulator run --config error-test.yaml --count 10

echo "Running timeout test..."
gp-simulator run --config timeout-test.yaml --count 10

echo "Stopping server..."
kill $SERVER_PID

echo "Tests complete!"
```

### Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Simulator Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -e ".[simulator]"

      - name: Start PSK-TLS Server
        run: |
          gp-server start --port 8443 &
          sleep 5

      - name: Run simulator tests
        run: |
          gp-simulator run --config tests/configs/ci-test.yaml --count 10

      - name: Check results
        run: |
          if [ $? -eq 0 ]; then
            echo "Simulator tests passed"
          else
            echo "Simulator tests failed"
            exit 1
          fi
```

### Performance Tuning

For high-volume testing, adjust these settings:

```yaml
# Reduce delays for faster testing
behavior:
  response_delay_ms: 5  # Minimal delay

# Reduce timeouts for faster failure detection
server:
  connect_timeout: 10.0
  read_timeout: 10.0
  retry_count: 1
  retry_backoff: [0.5]
```

### Multiple Simulator Profiles

Maintain different profiles for different test scenarios:

```
configs/
├── production-test.yaml    # Production-like configuration
├── error-test.yaml          # Error injection testing
├── timeout-test.yaml        # Timeout testing
├── load-test.yaml           # Load testing
└── quick-test.yaml          # Fast testing with minimal delays
```

Run different profiles:

```bash
# Production test
gp-simulator run --config configs/production-test.yaml

# Error test
gp-simulator run --config configs/error-test.yaml

# Load test
gp-simulator run --config configs/load-test.yaml --count 100 --parallel
```

## See Also

- [PSK-TLS Server Guide](psk-tls-server-guide.md) - Server setup and configuration
- [Dashboard Guide](dashboard-guide.md) - Web dashboard for monitoring
- [Simulator README](../src/cardlink/simulator/README.md) - Technical documentation
- [User Guide](user-guide.md) - General system usage

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review example configurations in `examples/simulator/`
3. Check server logs for connection issues
4. Enable verbose mode (`-v`) for detailed debugging
5. Consult the API documentation: `python -c "from cardlink import simulator; help(simulator.MobileSimulator)"`

## Summary

The Mobile Simulator provides a powerful tool for testing PSK-TLS server functionality without physical hardware. Key capabilities:

- ✅ Software-based UICC simulation
- ✅ Configurable behavior modes (normal, error, timeout)
- ✅ Load testing with parallel instances
- ✅ Comprehensive monitoring and statistics
- ✅ Easy integration with CI/CD pipelines

Start with the [Quick Start](#quick-start) section and explore different [Testing Scenarios](#testing-scenarios) to validate your server implementation.
