# Network Simulator Integration User Guide

## Overview

The Network Simulator Integration module enables control and monitoring of network simulators like Amarisoft Callbox for OTA (Over-The-Air) testing. This guide covers setup, CLI usage, and scenario authoring.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Scenario Authoring](#scenario-authoring)
- [Python API Usage](#python-api-usage)
- [Integration with PSK-TLS Server](#integration-with-psk-tls-server)
- [Monitoring and Events](#monitoring-and-events)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

- **Network Simulator**: Amarisoft Callbox or compatible LTE/5G simulator
- **Test Phone**: Android device with UICC card
- **Network**: Connectivity between test PC and simulator

### Software Requirements

- **Python**: 3.9 or higher
- **Simulator Access**: WebSocket or TCP access to simulator API
- **API Key**: Authentication credentials for simulator

### Network Simulator Setup

Ensure your Amarisoft Callbox or simulator:
1. Has the Remote API enabled
2. Is accessible via WebSocket (typically port 9001)
3. Has an API key configured for authentication

## Installation

### Step 1: Install Package

```bash
# Install with network simulator support
pip install cardlink[netsim]

# Or from source
git clone <repository-url>
cd cardlink
pip install -e ".[netsim]"
```

### Step 2: Verify Installation

```bash
# Check CLI is available
gp-netsim --help
```

### Step 3: Configure Environment

Set environment variables for convenience:

```bash
# Linux/macOS
export NETSIM_URL="wss://callbox.local:9001"
export NETSIM_API_KEY="your-api-key"

# Windows PowerShell
$env:NETSIM_URL = "wss://callbox.local:9001"
$env:NETSIM_API_KEY = "your-api-key"
```

## Quick Start

### 1. Test Connectivity

```bash
gp-netsim connect \
  --url wss://callbox.local:9001 \
  --api-key your-api-key
```

Expected output:
```
Connecting to Network Simulator
URL: wss://callbox.local:9001
Type: amarisoft

Connected successfully!
  Simulator: amarisoft
  Connected: True
  Authenticated: Yes
```

### 2. Check Simulator Status

```bash
gp-netsim --url wss://callbox.local:9001 status
```

### 3. List Connected UEs

```bash
gp-netsim --url $NETSIM_URL ue list
```

Output:
```
┌─────────────────┬────────────┬─────────┬─────────────┐
│ IMSI            │ Status     │ Cell ID │ IP Address  │
├─────────────────┼────────────┼─────────┼─────────────┤
│ 001010123456789 │ registered │ 1       │ 10.0.0.100  │
│ 001010987654321 │ registered │ 1       │ 10.0.0.101  │
└─────────────────┴────────────┴─────────┴─────────────┘

Total: 2 UE(s)
```

### 4. Send OTA Trigger

```bash
gp-netsim --url $NETSIM_URL sms trigger 001010123456789 --tar B00000
```

## CLI Reference

### Global Options

```bash
gp-netsim [OPTIONS] COMMAND [ARGS]

Options:
  -v, --verbose     Enable verbose output
  --url TEXT        Simulator WebSocket URL (or NETSIM_URL env var)
  --type TEXT       Simulator type: amarisoft, generic
  --api-key TEXT    API key (or NETSIM_API_KEY env var)
```

### Connection Commands

#### connect

Test connection to simulator.

```bash
gp-netsim connect --url wss://host:port --api-key KEY
```

Options:
- `--url` - Simulator WebSocket URL (required)
- `--type` - Simulator type (default: amarisoft)
- `--api-key` - Authentication key
- `-c, --config` - YAML configuration file

#### status

Show simulator status.

```bash
gp-netsim --url $NETSIM_URL status
```

### UE Commands

#### ue list

List all connected UEs.

```bash
gp-netsim --url $NETSIM_URL ue list
```

#### ue show

Show details for specific UE.

```bash
gp-netsim --url $NETSIM_URL ue show 001010123456789
```

#### ue wait

Wait for UE registration.

```bash
gp-netsim --url $NETSIM_URL ue wait 001010123456789 --timeout 60
```

Options:
- `-t, --timeout` - Maximum wait time in seconds (default: 30)

#### ue detach

Force detach UE from network.

```bash
gp-netsim --url $NETSIM_URL ue detach 001010123456789 --cause reattach_required
```

### Session Commands

#### session list

List active data sessions.

```bash
gp-netsim --url $NETSIM_URL session list
gp-netsim --url $NETSIM_URL session list --imsi 001010123456789
```

#### session show

Show session details.

```bash
gp-netsim --url $NETSIM_URL session show sess_abc123
```

#### session release

Release a data session.

```bash
gp-netsim --url $NETSIM_URL session release sess_abc123
```

### SMS Commands

#### sms send

Send raw SMS PDU.

```bash
gp-netsim --url $NETSIM_URL sms send 001010123456789 \
  0011000B911234567890F00000AA05C8329BFD06
```

#### sms trigger

Send OTA trigger SMS.

```bash
gp-netsim --url $NETSIM_URL sms trigger 001010123456789 --tar B00000
```

Options:
- `--tar` - Toolkit Application Reference in hex (default: 000001)

#### sms history

Show SMS message history.

```bash
gp-netsim --url $NETSIM_URL sms history --limit 20
```

### Cell Commands

#### cell start

Start the cell.

```bash
gp-netsim --url $NETSIM_URL cell start
```

#### cell stop

Stop the cell.

```bash
gp-netsim --url $NETSIM_URL cell stop
```

#### cell status

Show cell status.

```bash
gp-netsim --url $NETSIM_URL cell status
```

#### cell config

Configure cell parameters.

```bash
gp-netsim --url $NETSIM_URL cell config \
  --plmn 310-150 \
  --frequency 1950 \
  --bandwidth 20 \
  --power 23
```

### Scenario Commands

#### run-scenario

Execute a test scenario from YAML file.

```bash
gp-netsim --url $NETSIM_URL run-scenario scenario.yaml
gp-netsim --url $NETSIM_URL run-scenario scenario.yaml -V imsi=001010123456789
```

Options:
- `-V, --var` - Variable in name=value format (can be repeated)

## Scenario Authoring

### Scenario File Structure

```yaml
name: ota_trigger_test
description: Test OTA trigger and admin session

# Initial variables
variables:
  imsi: "001010123456789"
  tar: "B00000"
  timeout: 60

# Tags for categorization
tags:
  - smoke
  - ota

# Setup steps (run before main steps)
setup:
  - name: ensure_cell_active
    action: cell.start

# Main test steps
steps:
  - name: wait_for_ue
    action: ue.wait_for_registration
    params:
      imsi: "${imsi}"
      timeout: "${timeout}"
    save_as: ue_info

  - name: verify_session
    action: session.list
    params:
      imsi: "${imsi}"
    save_as: sessions

  - name: send_trigger
    action: sms.send_trigger
    params:
      imsi: "${imsi}"
      tar: "${tar}"
    save_as: trigger_result

  - name: wait_for_response
    action: wait
    params:
      seconds: 5

# Teardown steps (always run)
teardown:
  - name: cleanup
    action: log
    params:
      message: "Test completed"
```

### Step Structure

```yaml
- name: step_name           # Required: Unique step name
  action: action.name       # Required: Action to execute
  params:                   # Optional: Action parameters
    key: value
    key2: "${variable}"
  timeout: 30               # Optional: Step timeout in seconds
  save_as: result_var       # Optional: Save result to variable
  on_failure: stop          # Optional: stop, continue, or skip
  condition:                # Optional: Conditional execution
    variable: var_name
    operator: equals
    value: expected_value
```

### Available Actions

#### UE Actions

```yaml
# List UEs
- action: ue.list

# Get UE by IMSI
- action: ue.get
  params:
    imsi: "001010123456789"

# Wait for registration
- action: ue.wait_for_registration
  params:
    imsi: "001010123456789"
    timeout: 60

# Detach UE
- action: ue.detach
  params:
    imsi: "001010123456789"
```

#### Session Actions

```yaml
# List sessions
- action: session.list
  params:
    imsi: "001010123456789"  # Optional filter

# Get session
- action: session.get
  params:
    session_id: "sess_abc123"

# Release session
- action: session.release
  params:
    session_id: "sess_abc123"
```

#### SMS Actions

```yaml
# Send raw PDU
- action: sms.send
  params:
    imsi: "001010123456789"
    pdu: "0011000B91..."

# Send OTA trigger
- action: sms.send_trigger
  params:
    imsi: "001010123456789"
    tar: "B00000"
```

#### Cell Actions

```yaml
# Start cell
- action: cell.start

# Stop cell
- action: cell.stop

# Get status
- action: cell.status

# Configure
- action: cell.configure
  params:
    plmn: "310-150"
    frequency: 1950
```

#### Trigger Actions

```yaml
# Trigger paging
- action: trigger.paging
  params:
    imsi: "001010123456789"
    paging_type: ps

# Trigger handover
- action: trigger.handover
  params:
    imsi: "001010123456789"
    target_cell: 2

# Trigger detach
- action: trigger.detach
  params:
    imsi: "001010123456789"
    cause: reattach_required
```

#### Utility Actions

```yaml
# Wait
- action: wait
  params:
    seconds: 5

# Log message
- action: log
  params:
    message: "Step completed"
    level: info  # debug, info, warning, error

# Assert condition
- action: assert
  params:
    condition: true
    message: "Assertion failed"
```

### Variable Substitution

Use `${variable}` syntax to reference variables:

```yaml
variables:
  imsi: "001010123456789"

steps:
  - action: ue.get
    params:
      imsi: "${imsi}"
    save_as: ue_result

  - action: log
    params:
      message: "UE status: ${ue_result.status}"
```

### Conditional Steps

Skip steps based on conditions:

```yaml
- name: conditional_step
  action: ue.detach
  params:
    imsi: "${imsi}"
  condition:
    variable: ue_registered
    operator: equals
    value: true
```

Operators:
- `defined` - Variable exists
- `not_defined` - Variable doesn't exist
- `equals` - Equals value
- `not_equals` - Not equals value
- `contains` - String/list contains value
- `not_contains` - Doesn't contain value
- `greater_than` - Numeric comparison
- `less_than` - Numeric comparison

### Error Handling

Control behavior on step failure:

```yaml
# Stop scenario on failure (default)
- action: ue.get
  on_failure: stop

# Continue with remaining steps
- action: ue.get
  on_failure: continue

# Skip remaining steps
- action: ue.get
  on_failure: skip
```

## Python API Usage

### Basic Connection

```python
import asyncio
from cardlink.netsim import SimulatorManager, SimulatorConfig, SimulatorType

async def main():
    config = SimulatorConfig(
        url="wss://callbox.local:9001",
        simulator_type=SimulatorType.AMARISOFT,
        api_key="your-api-key"
    )

    manager = SimulatorManager(config)
    await manager.connect()

    try:
        # Your operations here
        ues = await manager.ue.list_ues()
        print(f"Connected UEs: {len(ues)}")
    finally:
        await manager.disconnect()

asyncio.run(main())
```

### Event Monitoring

```python
async def monitor_events():
    async def on_event(event):
        print(f"Event: {event.event_type}")
        print(f"IMSI: {event.imsi}")
        print(f"Data: {event.data}")

    # Subscribe to all events
    unsubscribe = manager.events.subscribe(on_event)

    # Or specific event type
    from cardlink.netsim import NetworkEventType
    unsubscribe = manager.events.subscribe(
        on_event,
        NetworkEventType.UE_ATTACHED
    )

    # Run for a while
    await asyncio.sleep(60)

    # Cleanup
    unsubscribe()
```

### Running Scenarios Programmatically

```python
from cardlink.netsim import Scenario, ScenarioRunner

async def run_test():
    scenario = Scenario.from_file("test.yaml")
    runner = ScenarioRunner(manager)

    result = await runner.run(
        scenario,
        variables={"imsi": "001010123456789"}
    )

    if result.passed:
        print(f"Test PASSED in {result.duration_ms}ms")
    else:
        print("Test FAILED")
        for step in result.step_results:
            if step.status.value == "failed":
                print(f"  {step.step_name}: {step.error}")
```

## Integration with PSK-TLS Server

### Complete OTA Test Flow

```yaml
name: complete_ota_test
description: Full OTA session test with PSK-TLS server

variables:
  imsi: "001010123456789"
  tar: "B00000"
  server_url: "https://192.168.1.100:8443"

setup:
  - name: start_cell
    action: cell.start

  - name: start_psk_server
    action: log
    params:
      message: "Ensure PSK-TLS server is running"

steps:
  - name: wait_for_registration
    action: ue.wait_for_registration
    params:
      imsi: "${imsi}"
      timeout: 120
    save_as: ue

  - name: verify_data_session
    action: session.list
    params:
      imsi: "${imsi}"
    save_as: sessions

  - name: send_ota_trigger
    action: sms.send_trigger
    params:
      imsi: "${imsi}"
      tar: "${tar}"
    save_as: trigger

  - name: wait_for_connection
    action: wait
    params:
      seconds: 10

  - name: log_result
    action: log
    params:
      message: "OTA trigger sent, check server logs"

teardown:
  - name: cleanup
    action: ue.detach
    params:
      imsi: "${imsi}"
    on_failure: continue
```

## Monitoring and Events

### Event Correlation

Track related events during a test:

```python
# Start correlation
correlation_id = await manager.events.start_correlation("ota_test")

# Perform operations
await manager.sms.send_ota_trigger(imsi, tar)
await asyncio.sleep(5)

# Get correlated events
events = await manager.events.end_correlation(correlation_id)
for event in events:
    print(f"{event.timestamp}: {event.event_type}")
```

### Event Export

Export events for analysis:

```python
# Export to JSON
json_data = manager.events.export_events(format="json")

# Export to CSV file
manager.events.export_events(
    format="csv",
    file_path="events.csv"
)
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to simulator
```
ConnectionError: Connection refused
```

**Solutions**:
1. Verify simulator is running and API is enabled
2. Check URL and port are correct
3. Ensure firewall allows connection
4. Try TCP instead of WebSocket: `tcp://host:port`

### Authentication Failures

**Problem**: Authentication error
```
AuthenticationError: Invalid API key
```

**Solutions**:
1. Verify API key is correct
2. Check API key is enabled in simulator config
3. Ensure no special characters need escaping

### UE Not Found

**Problem**: UE operations fail
```
ResourceNotFoundError: UE not found: 001010123456789
```

**Solutions**:
1. Verify UE is powered on and has signal
2. Check IMSI is correct (15 digits)
3. Wait for UE registration: `ue wait <imsi>`
4. Check cell is active: `cell status`

### SMS Delivery Failures

**Problem**: SMS not delivered
```
CommandError: SMS delivery failed
```

**Solutions**:
1. Verify UE is registered
2. Check PDU format is valid
3. Ensure data session is established
4. Try OTA trigger instead of raw PDU

### Scenario Failures

**Problem**: Scenario steps fail
```
Step 'wait_for_ue' failed: Timeout after 30s
```

**Solutions**:
1. Increase step timeout in YAML
2. Check UE is attempting to register
3. Verify cell configuration matches UE
4. Check variable substitution is correct

### Debug Mode

Enable verbose output for debugging:

```bash
gp-netsim -v --url $NETSIM_URL ue list
```

Or in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Error Codes

| Error | Description | Resolution |
|-------|-------------|------------|
| `CONNECTION_REFUSED` | Simulator not accepting connections | Check simulator status |
| `AUTH_FAILED` | Invalid credentials | Verify API key |
| `TIMEOUT` | Operation timed out | Increase timeout, check network |
| `NOT_CONNECTED` | No active connection | Call connect() first |
| `RESOURCE_NOT_FOUND` | UE/session not found | Verify resource exists |
| `COMMAND_ERROR` | Simulator rejected command | Check command parameters |
