# Mobile Simulator

The Mobile Simulator simulates a mobile phone with a UICC card initiating SCP81 (GlobalPlatform Amendment B) connections to the PSK-TLS Admin Server.

## Overview

The simulator enables testing the PSK-TLS server without requiring physical mobile hardware or UICC cards. It implements:

- **PSK-TLS Client**: Establishes TLS 1.2 connections using Pre-Shared Keys
- **HTTP Admin Protocol**: Implements GP Amendment B HTTP Admin protocol
- **Virtual UICC**: Simulates UICC card behavior and APDU processing
- **Behavior Modes**: Supports error injection and timeout simulation for testing

## Quick Start

### Installation

```bash
# Install with simulator dependencies
pip install gp-ota-tester[simulator]

# Or install from source
pip install -e ".[simulator]"
```

### Basic Usage

```python
import asyncio
from cardlink.simulator import MobileSimulator, SimulatorConfig

async def main():
    # Create configuration
    config = SimulatorConfig(
        server_host="127.0.0.1",
        server_port=8443,
        psk_identity="test_card",
        psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10"),
    )

    # Run complete session
    simulator = MobileSimulator(config)
    result = await simulator.run_complete_session()

    print(f"Success: {result.success}")
    print(f"APDUs exchanged: {result.apdu_count}")
    print(f"Final SW: {result.final_sw}")

asyncio.run(main())
```

### CLI Usage

```bash
# Run with default configuration
gp-simulator run

# Run with custom server and credentials
gp-simulator run \
  --server 192.168.1.100:8443 \
  --psk-identity card_001 \
  --psk-key 0102030405060708090A0B0C0D0E0F10

# Run with configuration file
gp-simulator run --config simulator.yaml

# Test server connectivity
gp-simulator test-connection --server 127.0.0.1:8443

# Generate sample configuration
gp-simulator config-generate --output my-config.yaml
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Mobile Simulator                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ PSK-TLS     │──►│ HTTP Admin   │──►│ Virtual UICC     │ │
│  │ Client      │   │ Client       │   │                  │ │
│  └─────────────┘   └──────────────┘   │  - APDU Router   │ │
│                                        │  - GP Commands   │ │
│                                        │  - Response Gen  │ │
│                                        └──────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Behavior Controller                          │   │
│  │  - Error Injection                                   │   │
│  │  - Timeout Simulation                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ TLS-PSK HTTPS
                           ▼
                  ┌────────────────┐
                  │  PSK-TLS       │
                  │  Admin Server  │
                  └────────────────┘
```

## Configuration

### YAML Configuration File

```yaml
# Server connection settings
server:
  host: "127.0.0.1"
  port: 8443
  connect_timeout: 30.0
  read_timeout: 30.0
  retry_count: 3
  retry_backoff: [1.0, 2.0, 4.0]

# PSK-TLS credentials
psk:
  identity: "test_card_001"
  key: "0102030405060708090A0B0C0D0E0F10"

# Virtual UICC configuration
uicc:
  iccid: "8901234567890123456"
  imsi: "310150123456789"
  msisdn: "+14155551234"

  gp:
    version: "2.2.1"
    scp_version: "03"
    isd_aid: "A000000151000000"

  applets:
    - aid: "A0000001510001"
      name: "TestApplet"
      state: "SELECTABLE"

# Simulation behavior
behavior:
  mode: "normal"  # normal, error, timeout
  response_delay_ms: 20

  error:
    rate: 0.0
    codes: ["6A82", "6985", "6D00"]

  timeout:
    probability: 0.0
    delay_range:
      min: 1000
      max: 5000
```

### Programmatic Configuration

```python
from cardlink.simulator import (
    SimulatorConfig,
    BehaviorConfig,
    UICCProfile,
    BehaviorMode,
    VirtualApplet,
)

# Create custom UICC profile
uicc_profile = UICCProfile(
    iccid="8901234567890123456",
    imsi="310150123456789",
    applets=[
        VirtualApplet(
            aid="A0000001510001",
            name="MyApplet",
            state="SELECTABLE",
        )
    ],
)

# Create behavior configuration
behavior = BehaviorConfig(
    mode=BehaviorMode.ERROR,
    error_rate=0.1,  # 10% error rate
    error_codes=["6A82", "6985"],
)

# Create simulator configuration
config = SimulatorConfig(
    server_host="192.168.1.100",
    server_port=8443,
    psk_identity="card_001",
    psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10"),
    uicc_profile=uicc_profile,
    behavior=behavior,
)
```

## Simulation Modes

### Normal Mode

Processes all commands correctly with realistic timing:

```python
config = SimulatorConfig(
    behavior=BehaviorConfig(mode=BehaviorMode.NORMAL)
)
```

### Error Injection Mode

Injects random error status words at configured rate:

```python
config = SimulatorConfig(
    behavior=BehaviorConfig(
        mode=BehaviorMode.ERROR,
        error_rate=0.2,  # 20% of responses will be errors
        error_codes=["6A82", "6985", "6D00"],
    )
)
```

### Timeout Simulation Mode

Simulates slow responses or timeouts:

```python
config = SimulatorConfig(
    behavior=BehaviorConfig(
        mode=BehaviorMode.TIMEOUT,
        timeout_probability=0.1,  # 10% of responses delayed
        timeout_delay_min_ms=1000,
        timeout_delay_max_ms=5000,
    )
)
```

## Advanced Usage

### Manual Connection Management

```python
async def manual_session():
    config = SimulatorConfig(...)
    simulator = MobileSimulator(config)

    try:
        # Connect
        if not await simulator.connect():
            print("Connection failed")
            return

        # Run session
        result = await simulator.run_session()

        # Get statistics
        stats = simulator.get_statistics()
        print(f"Total APDUs: {stats.total_apdus_sent}")

    finally:
        # Always disconnect
        await simulator.disconnect()
```

### Async Context Manager

```python
async def context_manager_session():
    config = SimulatorConfig(...)

    async with MobileSimulator(config) as simulator:
        result = await simulator.run_session()
        print(f"Session result: {result.success}")

    # Automatically disconnected
```

### Multiple Simulators

```python
async def parallel_simulators():
    config = SimulatorConfig(...)

    # Run 10 simulators in parallel
    tasks = [
        MobileSimulator(config).run_complete_session()
        for _ in range(10)
    ]

    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.success)
    print(f"Success rate: {success_count}/10")
```

### Continuous Loop Mode

```python
async def continuous_mode():
    config = SimulatorConfig(...)
    simulator = MobileSimulator(config)

    while True:
        result = await simulator.run_complete_session()
        print(f"Session: {result.apdu_count} APDUs, SW={result.final_sw}")

        # Wait before next session
        await asyncio.sleep(5.0)
```

## Testing Integration

### Pytest Fixtures

```python
import pytest
from cardlink.simulator import MobileSimulator, SimulatorConfig

@pytest.fixture
async def simulator(admin_server):
    """Create simulator connected to test server."""
    config = SimulatorConfig(
        server_host="127.0.0.1",
        server_port=admin_server.port,
        psk_identity="test_card",
        psk_key=admin_server.test_psk_key,
    )

    sim = MobileSimulator(config)
    yield sim

    # Cleanup
    await sim.disconnect()

@pytest.fixture
async def connected_simulator(simulator):
    """Simulator with established connection."""
    await simulator.connect()
    return simulator
```

### Example Tests

```python
@pytest.mark.asyncio
async def test_basic_session(connected_simulator):
    """Test basic admin session completes successfully."""
    result = await connected_simulator.run_session()

    assert result.success
    assert result.apdu_count > 0
    assert result.final_sw == "9000"

@pytest.mark.asyncio
async def test_select_isd(connected_simulator):
    """Test SELECT ISD-R command processing."""
    result = await connected_simulator.run_session()

    # Verify SELECT was processed
    select_exchanges = [
        ex for ex in result.exchanges
        if ex.ins == 0xA4 and ex.sw == "9000"
    ]

    assert len(select_exchanges) > 0
```

## Monitoring and Debugging

### Session Results

```python
result = await simulator.run_complete_session()

print(f"Success: {result.success}")
print(f"Session ID: {result.session_id}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"APDU Count: {result.apdu_count}")
print(f"Final SW: {result.final_sw}")

# View APDU exchanges
for exchange in result.exchanges:
    print(f"{exchange.description}: C={exchange.command[:20]}... SW={exchange.sw}")
```

### Statistics

```python
stats = simulator.get_statistics()

print(f"Connections attempted: {stats.connections_attempted}")
print(f"Connections succeeded: {stats.connections_succeeded}")
print(f"Sessions completed: {stats.sessions_completed}")
print(f"Total APDUs sent: {stats.total_apdus_sent}")
print(f"Avg connection time: {stats.avg_connection_time_ms:.1f}ms")
print(f"Avg APDU time: {stats.avg_apdu_response_time_ms:.1f}ms")

# Error statistics
for sw, count in stats.error_responses.items():
    print(f"Error {sw}: {count} times")
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger("cardlink.simulator")
logger.setLevel(logging.DEBUG)
```

## Supported APDU Commands

The Virtual UICC supports these GlobalPlatform commands:

| INS  | Command                  | Description                |
|------|--------------------------|----------------------------|
| 0xA4 | SELECT                   | Select application/file    |
| 0xF2 | GET STATUS               | Query card status          |
| 0xCA | GET DATA                 | Retrieve data objects      |
| 0x50 | INITIALIZE UPDATE        | Begin secure channel       |
| 0x82 | EXTERNAL AUTHENTICATE    | Complete secure channel    |
| 0xE6 | INSTALL                  | Install applet (simulated) |
| 0xE4 | DELETE                   | Delete package/applet      |
| 0xD8 | PUT KEY                  | Key management             |
| 0xE2 | STORE DATA               | Store data objects         |

Unsupported commands return `SW 6D00` (INS not supported).

## Status Words

The simulator generates realistic status words:

- `9000`: Success
- `61XX`: More data available
- `6CXX`: Incorrect Le field
- `6A82`: File not found
- `6A86`: Incorrect P1P2
- `6982`: Security conditions not satisfied
- `6985`: Conditions not satisfied
- `6D00`: INS not supported

## Performance

Typical performance characteristics:

- **Connection time**: 50-100ms (TLS handshake)
- **APDU processing**: <10ms per APDU
- **Session duration**: 100-500ms (5-10 APDUs)
- **Memory per instance**: <20MB
- **Concurrent instances**: 100+ on modern hardware

## Troubleshooting

### Connection Failures

```
Error: Connection refused
```

**Solution**: Ensure the PSK-TLS server is running and accessible.

```bash
# Test server connectivity
gp-simulator test-connection --server 127.0.0.1:8443
```

### Handshake Failures

```
Error: PSK identity not found
```

**Solution**: Verify PSK identity and key match server configuration.

### Timeout Issues

```
Error: Connection timeout
```

**Solution**: Increase connection timeout in configuration:

```python
config = SimulatorConfig(
    connect_timeout=60.0,  # Increase to 60 seconds
    read_timeout=60.0,
)
```

## See Also

- [PSK-TLS Server Guide](../../docs/psk-tls-server-guide.md)
- [Dashboard Guide](../../docs/dashboard-guide.md)
- [User Guide](../../docs/user-guide.md)
- [SCP81 PRD](../../scp81-prd.md)

## API Reference

See the module docstrings for detailed API documentation:

```python
from cardlink import simulator
help(simulator.MobileSimulator)
help(simulator.SimulatorConfig)
help(simulator.VirtualUICC)
```
