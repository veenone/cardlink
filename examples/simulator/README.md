# Mobile Simulator Examples

This directory contains example configurations and scripts for the Mobile Simulator.

## Quick Start

### 1. Basic Local Testing

Use the basic configuration for simple local testing:

```bash
# Start the PSK-TLS server
gp-server start --port 8443 --psk-key 00000000000000000000000000000000

# In another terminal, run the simulator
gp-simulator run --config examples/simulator/basic_config.yaml
```

Expected output:
```
Mobile Simulator
Server: 127.0.0.1:8443
PSK Identity: test_card
Mode: normal

Session 1
  Success: 5 APDUs, 0.28s, SW=9000

Summary
  Sessions: 1
  Successful: 1
  Failed: 0
```

### 2. Error Injection Testing

Test how the server handles UICC errors:

```bash
gp-simulator run --config examples/simulator/error_injection_config.yaml --count 10
```

This injects errors in 20% of responses to verify the server handles errors gracefully.

### 3. Timeout Testing

Test server timeout handling:

```bash
gp-simulator run --config examples/simulator/timeout_config.yaml --count 10
```

This delays 30% of responses by 1-5 seconds.

### 4. Advanced Configuration

Full-featured configuration with multiple applets:

```bash
gp-simulator run --config examples/simulator/advanced_config.yaml -v
```

## Configuration Files

### basic_config.yaml

Simple configuration for local testing with default settings.

**Use case**: Initial setup and verification

**Features**:
- Localhost connection
- Default PSK credentials
- Normal behavior mode
- No pre-installed applets

### error_injection_config.yaml

Configuration for testing error handling.

**Use case**: Server error handling validation

**Features**:
- 20% error injection rate
- Common error codes (6A82, 6985, 6D00, 6A86)
- Error mode enabled

**Expected behavior**: Mix of successful (9000) and error responses

### timeout_config.yaml

Configuration for testing timeout handling.

**Use case**: Server timeout and performance testing

**Features**:
- 30% timeout probability
- 1-5 second delay range
- Timeout mode enabled

**Expected behavior**: Some responses delayed, server handles gracefully

### advanced_config.yaml

Complete configuration demonstrating all features.

**Use case**: Production-like testing, comprehensive validation

**Features**:
- Multiple pre-installed applets
- 32-byte PSK key
- Combined error (5%) and timeout (2%) injection
- Custom UICC profile (ICCID, IMSI, MSISDN)

## Example Workflows

### Workflow 1: Development Testing

During development, use quick iterations:

```bash
# Terminal 1: Run server with auto-reload
gp-server start --port 8443 --reload

# Terminal 2: Run simulator in loop mode
gp-simulator run \
  --config examples/simulator/basic_config.yaml \
  --loop \
  --interval 2
```

Make code changes, and the simulator automatically tests them every 2 seconds.

### Workflow 2: Integration Testing

For comprehensive integration testing:

```bash
#!/bin/bash
# integration-test.sh

echo "Starting server..."
gp-server start --port 8443 &
SERVER_PID=$!
sleep 2

echo "Test 1: Normal operation (10 sessions)"
gp-simulator run --config examples/simulator/basic_config.yaml --count 10

echo "Test 2: Error handling (10 sessions)"
gp-simulator run --config examples/simulator/error_injection_config.yaml --count 10

echo "Test 3: Timeout handling (10 sessions)"
gp-simulator run --config examples/simulator/timeout_config.yaml --count 10

echo "Test 4: Load test (50 parallel sessions)"
gp-simulator run --config examples/simulator/basic_config.yaml --count 50 --parallel

echo "Stopping server..."
kill $SERVER_PID

echo "All tests complete!"
```

### Workflow 3: Performance Benchmarking

Measure server performance under load:

```bash
# Create performance test config
cat > perf-test.yaml <<EOF
server:
  host: "127.0.0.1"
  port: 8443
psk:
  identity: "test_card"
  key: "00000000000000000000000000000000"
behavior:
  mode: "normal"
  response_delay_ms: 5  # Minimal delay for max throughput
EOF

# Run performance test
time gp-simulator run \
  --config perf-test.yaml \
  --count 100 \
  --parallel
```

Analyze the output for average APDU response times and session durations.

### Workflow 4: Continuous Monitoring

Monitor server health continuously:

```bash
# Create monitoring script
cat > monitor.sh <<EOF
#!/bin/bash
while true; do
  clear
  date
  echo "Running health check..."

  gp-simulator run \
    --config examples/simulator/basic_config.yaml \
    --count 1 \
    2>&1 | grep -E "(Success|Failed|Error)"

  sleep 60
done
EOF

chmod +x monitor.sh
./monitor.sh
```

## Customizing Configurations

### Create Your Own Config

Start with the basic template:

```bash
# Generate a new config
gp-simulator config-generate --output my-config.yaml

# Edit as needed
nano my-config.yaml

# Test it
gp-simulator run --config my-config.yaml
```

### Common Customizations

#### Change Server Address

```yaml
server:
  host: "192.168.1.100"  # Remote server
  port: 9443             # Different port
```

#### Add Custom Applets

```yaml
uicc:
  applets:
    - aid: "A0000001510001"
      name: "MyApplet"
      state: "SELECTABLE"
      privileges: "00"

    - aid: "A0000001510002"
      name: "SecureApplet"
      state: "LOCKED"
      privileges: "80"
```

#### Adjust Error Rates

```yaml
behavior:
  mode: "error"
  error:
    rate: 0.5  # 50% error rate (very aggressive)
    codes:
      - "6A82"  # Only file not found errors
```

#### Change Timeouts

```yaml
server:
  connect_timeout: 10.0  # Faster failure detection
  read_timeout: 10.0
  retry_count: 1         # Less retries
  retry_backoff: [0.5]   # Shorter backoff
```

## Testing Patterns

### Pattern 1: Smoke Test

Quick sanity check:

```bash
gp-simulator run --config examples/simulator/basic_config.yaml --count 1
```

### Pattern 2: Regression Test

Verify nothing broke:

```bash
gp-simulator run --config examples/simulator/basic_config.yaml --count 10
```

### Pattern 3: Stress Test

Push the limits:

```bash
gp-simulator run --config examples/simulator/basic_config.yaml --count 100 --parallel
```

### Pattern 4: Chaos Test

Random errors and timeouts:

```yaml
behavior:
  mode: "error"  # Can combine both in implementation
  error:
    rate: 0.3
  timeout:
    probability: 0.2
```

## Troubleshooting Examples

### Debug Connection Issues

```bash
# Enable verbose output
gp-simulator run --config examples/simulator/basic_config.yaml -v

# Test connection only
gp-simulator test-connection \
  --server 127.0.0.1:8443 \
  --psk-identity test_card \
  --psk-key 00000000000000000000000000000000

# Check server logs
gp-server logs --tail 50
```

### Compare Configurations

```bash
# Run basic config
gp-simulator run --config examples/simulator/basic_config.yaml > basic.log

# Run advanced config
gp-simulator run --config examples/simulator/advanced_config.yaml > advanced.log

# Compare results
diff basic.log advanced.log
```

## CI/CD Integration

### Example: GitHub Actions

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

      - name: Install
        run: pip install -e ".[simulator]"

      - name: Start Server
        run: |
          gp-server start --port 8443 &
          sleep 5

      - name: Run Basic Test
        run: gp-simulator run --config examples/simulator/basic_config.yaml --count 5

      - name: Run Error Test
        run: gp-simulator run --config examples/simulator/error_injection_config.yaml --count 5
```

### Example: Docker Compose

```yaml
version: '3.8'

services:
  server:
    image: gp-ota-tester
    command: gp-server start --port 8443
    ports:
      - "8443:8443"

  simulator:
    image: gp-ota-tester
    depends_on:
      - server
    command: >
      gp-simulator run
      --server server:8443
      --psk-identity test_card
      --psk-key 00000000000000000000000000000000
      --loop
      --interval 10
```

## Additional Resources

- [Simulator Guide](../../docs/simulator-guide.md) - Complete user guide
- [Quick Reference](../../docs/simulator-quick-reference.md) - Command reference
- [Technical README](../../src/cardlink/simulator/README.md) - API documentation
- [Server Guide](../../docs/psk-tls-server-guide.md) - Server setup

## Tips

1. **Start Simple**: Begin with `basic_config.yaml` and verify it works
2. **Use Verbose Mode**: Add `-v` to see what's happening
3. **Test Incrementally**: Test one feature at a time
4. **Monitor Both Sides**: Watch both server and simulator logs
5. **Save Logs**: Redirect output to files for analysis
6. **Iterate Quickly**: Use loop mode during development
7. **Automate Testing**: Create scripts for common test scenarios
8. **Version Configs**: Keep configuration files in version control

## Contributing

To add new examples:

1. Create a descriptive YAML file
2. Test it thoroughly
3. Document the use case
4. Add it to this README
5. Submit a pull request

## Support

For issues or questions:

- Check the [troubleshooting section](../../docs/simulator-guide.md#troubleshooting)
- Review existing configurations for patterns
- Enable verbose mode for detailed diagnostics
- Check server logs for connection issues
