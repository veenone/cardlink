# Network Simulator Example Scenarios

This directory contains example YAML scenarios for the CardLink network simulator integration.

## Scenarios

| File | Description | Tags |
|------|-------------|------|
| `ue_registration.yaml` | Basic UE registration test | registration, basic |
| `sms_trigger.yaml` | SMS OTA trigger delivery | sms, ota, trigger |
| `ota_session.yaml` | Complete OTA session E2E | ota, e2e, bip |
| `handover_test.yaml` | Handover during session | handover, mobility |
| `network_recovery.yaml` | RLF/TAU recovery tests | recovery, resilience |

## Running Scenarios

```bash
# Run with default variables
cardlink-netsim run-scenario examples/netsim/ue_registration.yaml

# Override variables
cardlink-netsim run-scenario examples/netsim/sms_trigger.yaml \
  --var imsi=001010123456789 \
  --var tar=B00001

# Run with verbose output
cardlink-netsim run-scenario examples/netsim/ota_session.yaml \
  --verbose \
  --var session_timeout=120
```

## Scenario Structure

Each scenario YAML file follows this structure:

```yaml
name: "Scenario Name"
description: "What this scenario tests"

tags:
  - category1
  - category2

variables:
  var_name: "default_value"

setup:
  - name: "setup_step"
    action: "action.name"
    params:
      key: value

steps:
  - name: "step_name"
    action: "action.name"
    params:
      key: "${variable}"
    timeout: 30
    save_as: "result_var"
    on_failure: "stop"  # or "continue", "skip"

teardown:
  - name: "cleanup"
    action: "log"
    params:
      message: "Done"
```

## Available Actions

### UE Actions
- `ue.list` - List all UEs
- `ue.get` - Get UE by IMSI
- `ue.wait_for_registration` - Wait for UE to register
- `ue.detach` - Detach UE

### Session Actions
- `session.list` - List sessions
- `session.get` - Get session by ID
- `session.release` - Release session

### SMS Actions
- `sms.send` - Send MT-SMS
- `sms.send_trigger` - Send OTA trigger

### Cell Actions
- `cell.start` - Start cell
- `cell.stop` - Stop cell
- `cell.status` - Get cell status
- `cell.configure` - Configure cell

### Trigger Actions
- `trigger.paging` - Trigger paging
- `trigger.handover` - Trigger handover
- `trigger.detach` - Trigger network detach

### Utility Actions
- `wait` - Wait for duration
- `log` - Log message
- `assert` - Assert condition

## Variable Substitution

Use `${variable}` syntax to reference variables:

```yaml
variables:
  imsi: "001010123456789"

steps:
  - name: "get_ue"
    action: "ue.get"
    params:
      imsi: "${imsi}"  # Resolved to "001010123456789"
```

Variables can be:
- Defined in the `variables` section
- Passed via `--var` CLI option
- Saved from step results using `save_as`

## Conditional Steps

Steps can be conditionally executed:

```yaml
- name: "optional_step"
  action: "some.action"
  condition:
    variable: "some_var"
    operator: "equals"
    value: "expected"
```

Operators: `defined`, `not_defined`, `equals`, `not_equals`, `contains`, `greater_than`, `less_than`

## Customization

Copy and modify these examples for your specific test requirements. The scenarios are designed as starting points for common OTA testing workflows.
