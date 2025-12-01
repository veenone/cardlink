# Mobile Simulator Quick Reference

## Installation

```bash
pip install gp-ota-tester[simulator]
```

## Basic Commands

### Test Connection
```bash
gp-simulator test-connection \
  --server 127.0.0.1:8443 \
  --psk-identity test_card \
  --psk-key 0102030405060708090A0B0C0D0E0F10
```

### Run Single Session
```bash
gp-simulator run \
  --server 127.0.0.1:8443 \
  --psk-identity test_card \
  --psk-key 0102030405060708090A0B0C0D0E0F10
```

### Run with Config File
```bash
gp-simulator run --config simulator.yaml
```

### Generate Config
```bash
gp-simulator config-generate --output my-config.yaml
```

### Verbose Output
```bash
gp-simulator run --config simulator.yaml -v
```

## Advanced Commands

### Multiple Sessions (Sequential)
```bash
gp-simulator run --config simulator.yaml --count 10
```

### Multiple Sessions (Parallel)
```bash
gp-simulator run --config simulator.yaml --count 10 --parallel
```

### Continuous Mode
```bash
gp-simulator run --config simulator.yaml --loop --interval 5
```

### Error Injection Mode
```bash
gp-simulator run \
  --config simulator.yaml \
  --mode error \
  --error-rate 0.2
```

### Timeout Simulation Mode
```bash
gp-simulator run \
  --config simulator.yaml \
  --mode timeout \
  --timeout-probability 0.3
```

## Configuration Template

```yaml
# Minimal configuration
server:
  host: "127.0.0.1"
  port: 8443

psk:
  identity: "test_card"
  key: "0102030405060708090A0B0C0D0E0F10"

behavior:
  mode: "normal"
```

### Using ICCID as PSK Identity

```yaml
# Use ICCID as PSK identity for dashboard display
server:
  host: "127.0.0.1"
  port: 8443

psk:
  key: "0102030405060708090A0B0C0D0E0F10"
  use_iccid_as_identity: true  # ICCID becomes PSK identity

uicc:
  iccid: "8901234567890123456"  # Displayed in dashboard sessions
  imsi: "310150123456789"

behavior:
  mode: "normal"
```

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server HOST:PORT` | Server address | `127.0.0.1:8443` |
| `--psk-identity ID` | PSK identity | `test_card` |
| `--psk-key KEY` | PSK key (hex) | Required |
| `--use-iccid` | Use ICCID as PSK identity | `false` |
| `--config FILE` | Config file | None |
| `--mode MODE` | Behavior mode | `normal` |
| `--error-rate RATE` | Error rate (0.0-1.0) | `0.0` |
| `--timeout-probability PROB` | Timeout probability | `0.0` |
| `--count N` | Number of sessions | `1` |
| `--parallel` | Run in parallel | `false` |
| `--loop` | Continuous mode | `false` |
| `--interval SEC` | Loop interval | `5.0` |
| `-v, --verbose` | Verbose output | `false` |

## Behavior Modes

### Normal Mode
```yaml
behavior:
  mode: "normal"
  response_delay_ms: 20
```

### Error Mode
```yaml
behavior:
  mode: "error"
  error:
    rate: 0.2  # 20% errors
    codes: ["6A82", "6985", "6D00"]
```

### Timeout Mode
```yaml
behavior:
  mode: "timeout"
  timeout:
    probability: 0.1  # 10% delayed
    delay_range:
      min: 1000  # 1 second
      max: 5000  # 5 seconds
```

## Status Codes

| SW | Description |
|----|-------------|
| `9000` | Success |
| `61XX` | More data available |
| `6A82` | File not found |
| `6A86` | Incorrect P1P2 |
| `6982` | Security not satisfied |
| `6985` | Conditions not satisfied |
| `6CXX` | Wrong Le |
| `6D00` | INS not supported |

## Troubleshooting

### Connection Refused
```bash
# Check server is running
gp-server status

# Test with localhost
gp-simulator test-connection --server 127.0.0.1:8443
```

### PSK Mismatch
```bash
# Verify credentials match server
gp-server list-keys

# Add key to server
gp-server add-key --identity test_card --key <KEY>
```

### Timeout Issues
```yaml
# Increase timeouts
server:
  connect_timeout: 60.0
  read_timeout: 60.0
```

## Python API

```python
import asyncio
from cardlink.simulator import MobileSimulator, SimulatorConfig, UICCProfile

async def main():
    config = SimulatorConfig(
        server_host="127.0.0.1",
        server_port=8443,
        psk_identity="test_card",
        psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10"),
        use_iccid_as_identity=True,  # Use ICCID as PSK identity
        uicc_profile=UICCProfile(
            iccid="8901234567890123456",
            imsi="310150123456789"
        )
    )

    simulator = MobileSimulator(config)
    result = await simulator.run_complete_session()

    print(f"Success: {result.success}")
    print(f"APDUs: {result.apdu_count}")
    print(f"Final SW: {result.final_sw}")

    # Access ICCID from session result
    summary = result.get_summary()
    print(f"ICCID: {summary['iccid']}")
    print(f"PSK Identity: {summary['psk_identity']}")

asyncio.run(main())
```

## Quick Start Workflow

1. **Start Server**
   ```bash
   gp-server start --port 8443
   ```

2. **Test Connection**
   ```bash
   gp-simulator test-connection --server 127.0.0.1:8443
   ```

3. **Generate Config**
   ```bash
   gp-simulator config-generate --output test.yaml
   ```

4. **Edit Config** (update PSK credentials)

5. **Run Simulation**
   ```bash
   gp-simulator run --config test.yaml -v
   ```

## Example Configurations

See `examples/simulator/` for complete examples:

- `basic_config.yaml` - Simple local testing
- `error_injection_config.yaml` - Error testing
- `timeout_config.yaml` - Timeout testing
- `advanced_config.yaml` - Full-featured configuration

## Resources

- Full Guide: [docs/simulator-guide.md](simulator-guide.md)
- Server Guide: [docs/psk-tls-server-guide.md](psk-tls-server-guide.md)
- Technical Docs: [src/cardlink/simulator/README.md](../src/cardlink/simulator/README.md)
