# Observability Guide

Comprehensive guide for the GP-OTA-Tester observability system including metrics, tracing, health checks, and structured logging.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Metrics](#metrics)
  - [Metrics Registry](#metrics-registry)
  - [Recording Metrics](#recording-metrics)
  - [Metrics Endpoint](#metrics-endpoint)
- [Distributed Tracing](#distributed-tracing)
  - [Tracing Setup](#tracing-setup)
  - [Creating Spans](#creating-spans)
  - [Context Propagation](#context-propagation)
- [Health Checks](#health-checks)
  - [Built-in Checks](#built-in-checks)
  - [Custom Checks](#custom-checks)
  - [Health Endpoints](#health-endpoints)
- [Structured Logging](#structured-logging)
  - [JSON Logging](#json-logging)
  - [Trace Correlation](#trace-correlation)
  - [Component Loggers](#component-loggers)
- [Dashboards](#dashboards)
  - [Grafana Dashboards](#grafana-dashboards)
  - [Dashboard Templates](#dashboard-templates)
- [Alerting](#alerting)
  - [Prometheus Alerting Rules](#prometheus-alerting-rules)
  - [Alert Customization](#alert-customization)
- [CLI Commands](#cli-commands)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The GP-OTA-Tester observability system provides comprehensive monitoring and debugging capabilities:

**Metrics (Prometheus)**
- APDU command/response rates and latencies
- TLS session metrics and connection tracking
- OTA session lifecycle and status
- Device connection states and errors
- Test execution results and duration
- System resources (CPU, memory, connections)

**Distributed Tracing (OpenTelemetry)**
- End-to-end request tracing across components
- APDU exchange tracking
- Session lifecycle visualization
- Database query profiling
- Test execution traces

**Health Checks**
- Liveness probes for basic availability
- Readiness probes for dependency verification
- Custom health check registration
- Database connectivity checks
- External service availability

**Structured Logging**
- JSON-formatted log entries
- Trace ID correlation with OpenTelemetry
- Component-level log filtering
- Contextual field enrichment
- Exception tracking with stack traces

---

## Installation

```bash
# Install with observability support
pip install gp-ota-tester[observability]

# Full installation including all dependencies
pip install gp-ota-tester[all]
```

Dependencies installed:
- `prometheus-client>=0.17.0` - Metrics collection and exposition
- `opentelemetry-api>=1.20.0` - Tracing API
- `opentelemetry-sdk>=1.20.0` - Tracing SDK
- `opentelemetry-exporter-otlp>=1.20.0` - OTLP exporter for traces
- `psutil>=5.9.0` - System metrics collection

---

## Quick Start

### 5-Minute Tutorial

```python
from cardlink.observability import get_observability, ObservabilityConfig

# 1. Create configuration
config = ObservabilityConfig.from_env()

# 2. Initialize observability
obs = get_observability()
obs.initialize(config)

# 3. Record metrics
obs.metrics.record_apdu_command(
    command_type="SELECT",
    device_type="physical"
)

obs.metrics.record_apdu_response(
    status_word="9000",
    status_category="success"
)

# 4. Create trace spans
with obs.tracer.start_span("process_session") as span:
    span.set_attribute("session_id", "session_123")
    span.set_attribute("device_type", "physical")

    # Your code here
    process_apdu_commands()

    span.set_attribute("commands_processed", 10)

# 5. Check health
health_result = obs.health.run_all_checks()
print(f"Health status: {health_result.status}")

# 6. Log with context
logger = obs.logger.get_logger("my_component")
logger.info("Session completed", session_id="session_123", duration_ms=1250)

# 7. Shutdown
obs.shutdown()
```

### View Metrics

```bash
# Metrics are exposed at http://localhost:9090/metrics
curl http://localhost:9090/metrics

# Health status at http://localhost:8080/health
curl http://localhost:8080/health
```

---

## Configuration

### Environment Variables

```bash
# Metrics
export GP_METRICS_ENABLED="true"
export GP_METRICS_PORT="9090"
export GP_METRICS_PATH="/metrics"
export GP_METRICS_INTERVAL="15"  # System metrics collection interval

# Tracing
export GP_TRACING_ENABLED="true"
export GP_OTLP_ENDPOINT="localhost:4317"  # Jaeger/Tempo endpoint
export GP_OTLP_PROTOCOL="grpc"  # or "http"
export GP_SERVICE_NAME="gp-ota-tester"
export GP_TRACE_SAMPLE_RATE="1.0"  # 100% sampling

# Health Checks
export GP_HEALTH_ENABLED="true"
export GP_HEALTH_PORT="8080"
export GP_HEALTH_TIMEOUT="5.0"

# Logging
export GP_LOG_LEVEL="INFO"
export GP_LOG_FORMAT="json"  # or "text"
export GP_LOG_TRACE_CORRELATION="true"
export GP_LOG_FILE="/var/log/gp-ota/app.log"  # Optional
```

### Programmatic Configuration

```python
from cardlink.observability import ObservabilityConfig
from cardlink.observability.config import (
    MetricsConfig,
    TracingConfig,
    HealthConfig,
    LoggingConfig,
)

config = ObservabilityConfig(
    metrics=MetricsConfig(
        enabled=True,
        port=9090,
        path="/metrics",
        auth_username="admin",  # Optional HTTP Basic auth
        auth_password="secret",
        collection_interval=15,
    ),
    tracing=TracingConfig(
        enabled=True,
        otlp_endpoint="localhost:4317",
        otlp_protocol="grpc",
        service_name="gp-ota-tester",
        service_version="1.0.0",
        sample_rate=1.0,
    ),
    health=HealthConfig(
        enabled=True,
        port=8080,
        check_timeout=5.0,
    ),
    logging=LoggingConfig(
        level="INFO",
        format="json",
        trace_correlation=True,
        output_file=None,  # stdout
    ),
)

# Validate configuration
config.validate()
```

---

## Metrics

### Metrics Registry

All metrics are defined in the metrics registry with proper types, labels, and descriptions:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `apdu_commands_total` | Counter | command_type, device_type | Total APDU commands sent |
| `apdu_responses_total` | Counter | status_word, status_category | Total APDU responses received |
| `apdu_duration_seconds` | Histogram | command_type | APDU command duration |
| `apdu_bytes_total` | Counter | direction | APDU bytes transferred |
| `tls_handshakes_total` | Counter | result, cipher_suite | TLS handshakes completed |
| `tls_handshake_duration_seconds` | Histogram | - | TLS handshake duration |
| `tls_connections_active` | Gauge | - | Active TLS connections |
| `ota_sessions_active` | Gauge | device_type | Active OTA sessions |
| `ota_sessions_total` | Counter | status, type, device_type | Total OTA sessions |
| `ota_session_duration_seconds` | Histogram | type | OTA session duration |
| `ota_triggers_total` | Counter | trigger_type | OTA triggers sent |
| `devices_connected` | Gauge | device_type | Connected devices |
| `device_errors_total` | Counter | device_type, error_type | Device errors |
| `at_command_duration_seconds` | Histogram | command | AT command duration |
| `adb_operation_duration_seconds` | Histogram | operation | ADB operation duration |
| `test_total` | Counter | suite_name, status | Tests executed |
| `test_duration_seconds` | Histogram | suite_name | Test duration |
| `system_cpu_usage_percent` | Gauge | - | CPU usage percentage |
| `system_memory_usage_bytes` | Gauge | type | Memory usage (rss, vms) |
| `database_connections_active` | Gauge | - | Active database connections |
| `system_uptime_seconds` | Gauge | - | System uptime |
| `build_info` | Info | version, python_version, platform | Build information |

### Recording Metrics

```python
from cardlink.observability import get_observability

obs = get_observability()

# APDU metrics
obs.metrics.record_apdu_command(
    command_type="SELECT",
    device_type="physical"
)

obs.metrics.record_apdu_response(
    status_word="9000",
    status_category="success"
)

obs.metrics.record_apdu_duration(
    command_type="SELECT",
    duration=0.025  # seconds
)

obs.metrics.record_apdu_bytes(
    direction="sent",
    byte_count=10
)

# TLS metrics
obs.metrics.record_tls_handshake(
    result="success",
    cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA256",
    duration=0.150
)

obs.metrics.inc_tls_connections()  # Increment active connections
obs.metrics.dec_tls_connections()  # Decrement when closed

# Session metrics
obs.metrics.set_active_sessions(
    count=5,
    device_type="physical"
)

obs.metrics.record_session_complete(
    status="completed",
    type="admin",
    device_type="physical",
    duration=12.5
)

obs.metrics.record_trigger_sent(trigger_type="sms")

# Device metrics
obs.metrics.set_devices_connected(
    count=3,
    device_type="physical"
)

obs.metrics.record_device_error(
    device_type="physical",
    error_type="connection_timeout"
)

obs.metrics.record_at_command_duration(
    command="AT+CIMI",
    duration=0.050
)

obs.metrics.record_adb_operation_duration(
    operation="shell",
    duration=0.100
)

# Test metrics
obs.metrics.record_test_result(
    suite_name="e2e_basic",
    status="passed",
    duration=5.25
)

# System metrics (automatically collected every 15 seconds)
obs.metrics.update_system_metrics()

# Build info (set once at startup)
obs.metrics.set_build_info(
    version="1.0.0",
    python_version="3.9.7",
    platform="Linux"
)
```

### Metrics Endpoint

The metrics HTTP server exposes Prometheus-format metrics:

```bash
# Access metrics endpoint
curl http://localhost:9090/metrics

# With authentication
curl -u admin:secret http://localhost:9090/metrics

# Sample output
# HELP apdu_commands_total Total APDU commands sent
# TYPE apdu_commands_total counter
apdu_commands_total{command_type="SELECT",device_type="physical"} 1250
apdu_commands_total{command_type="READ",device_type="physical"} 850

# HELP apdu_duration_seconds APDU command duration in seconds
# TYPE apdu_duration_seconds histogram
apdu_duration_seconds_bucket{command_type="SELECT",le="0.005"} 100
apdu_duration_seconds_bucket{command_type="SELECT",le="0.01"} 450
apdu_duration_seconds_bucket{command_type="SELECT",le="0.025"} 1200
apdu_duration_seconds_sum{command_type="SELECT"} 12.5
apdu_duration_seconds_count{command_type="SELECT"} 1250
```

**Configure Prometheus scrape:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'gp-ota-tester'
    static_configs:
      - targets: ['localhost:9090']
    basic_auth:
      username: 'admin'
      password: 'secret'
```

---

## Distributed Tracing

### Tracing Setup

Configure OpenTelemetry tracing to export to Jaeger, Tempo, or other OTLP-compatible backends:

```python
from cardlink.observability import ObservabilityConfig

# Enable tracing
config = ObservabilityConfig.from_env()
config.tracing.enabled = True
config.tracing.otlp_endpoint = "localhost:4317"  # Jaeger or Tempo
config.tracing.otlp_protocol = "grpc"

obs = get_observability()
obs.initialize(config)
```

**Run Jaeger for local development:**

```bash
# Start Jaeger all-in-one
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# Access UI: http://localhost:16686
```

### Creating Spans

```python
from cardlink.observability import get_observability

obs = get_observability()

# Context manager (recommended)
with obs.tracer.start_span("process_session", kind="internal") as span:
    span.set_attribute("session_id", "session_123")
    span.set_attribute("device_id", "device_456")

    # Your code here
    result = process_session()

    span.set_attribute("result", result)
    span.set_attribute("commands_processed", 10)

# Decorator for functions
@obs.tracer.trace_decorator("process_apdu", kind="internal")
def process_apdu(command):
    # Function automatically traced
    return send_command(command)

# Nested spans
with obs.tracer.start_span("parent_operation") as parent:
    parent.set_attribute("operation_type", "full_session")

    with obs.tracer.start_span("child_operation") as child:
        child.set_attribute("step", "handshake")
        do_handshake()

    with obs.tracer.start_span("child_operation") as child:
        child.set_attribute("step", "data_transfer")
        transfer_data()
```

### Pre-built Span Managers

```python
from cardlink.observability.tracing.spans import SpanManager

span_mgr = SpanManager(obs.tracer)

# APDU span
with span_mgr.apdu_span("SELECT", device_id="device_123") as span:
    response = send_apdu(command)
    span_mgr.add_apdu_response(span, status_word="9000", duration_ms=25)

# TLS handshake span
with span_mgr.tls_handshake_span(client_address=("192.168.1.100", 54321)) as span:
    perform_handshake()

# OTA session span
with span_mgr.session_span(session_id="session_123", session_type="admin") as span:
    run_session()

# Database operation span
with span_mgr.db_span(operation="SELECT", table="devices") as span:
    rows = db.execute(query)

# Test execution span
with span_mgr.test_span(suite_name="e2e_basic", test_name="test_apdu_select") as span:
    run_test()
```

### Context Propagation

Propagate trace context across process boundaries:

```python
# Inject context into headers (HTTP, message queue, etc.)
carrier = {}
obs.tracer.inject_context(carrier)

# Carrier now contains: {"traceparent": "00-trace_id-span_id-01"}
send_request(headers=carrier)

# Extract context from headers
carrier = request.headers
obs.tracer.extract_context(carrier)

# New spans will be children of extracted trace
with obs.tracer.start_span("handle_request") as span:
    # This span is part of the distributed trace
    process_request()
```

---

## Health Checks

### Built-in Checks

```python
from cardlink.observability import get_observability

obs = get_observability()

# Liveness check (basic availability)
liveness = obs.health.check_liveness()
print(f"Liveness: {liveness.status}")  # healthy/unhealthy

# Readiness check (all dependencies ready)
readiness = obs.health.check_readiness()
print(f"Readiness: {readiness.status}")
print(f"Details: {readiness.details}")

# Run all checks
health = obs.health.run_all_checks()
print(f"Overall: {health.status}")  # healthy/degraded/unhealthy
print(f"Checks passed: {health.checks_passed}/{health.checks_total}")

for check_name, result in health.checks.items():
    print(f"{check_name}: {result.status} ({result.duration_ms}ms)")
    if result.error:
        print(f"  Error: {result.error}")
```

### Custom Checks

```python
from cardlink.observability.health.checks import (
    create_database_check,
    create_metrics_check,
    create_disk_space_check,
    create_memory_check,
)

# Register database check
db_check = create_database_check(database_manager)
obs.health.register_check("database", db_check)

# Register metrics endpoint check
metrics_check = create_metrics_check(metrics_port=9090)
obs.health.register_check("metrics", metrics_check)

# Register disk space check (warn at 80%, fail at 90%)
disk_check = create_disk_space_check(path="/var/lib/gp-ota", threshold=0.9)
obs.health.register_check("disk_space", disk_check)

# Register memory check (fail at 90% usage)
memory_check = create_memory_check(threshold=0.9)
obs.health.register_check("memory", memory_check)

# Custom check function
def check_external_api():
    """Check external API availability."""
    try:
        response = requests.get("https://api.example.com/health", timeout=2)
        if response.status_code == 200:
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

obs.health.register_check("external_api", check_external_api)

# Unregister check
obs.health.unregister_check("external_api")
```

### Health Endpoints

Health checks are exposed via HTTP endpoints:

```bash
# Overall health (all checks)
curl http://localhost:8080/health

# Response (JSON)
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "duration_ms": 5
    },
    "metrics": {
      "status": "healthy",
      "duration_ms": 2
    },
    "disk_space": {
      "status": "healthy",
      "duration_ms": 1
    }
  },
  "checks_passed": 3,
  "checks_total": 3
}

# Liveness probe (Kubernetes)
curl http://localhost:8080/health/live

# Readiness probe (Kubernetes)
curl http://localhost:8080/health/ready
```

**Kubernetes integration:**

```yaml
# deployment.yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: gp-ota-tester
    image: gp-ota-tester:1.0.0
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
```

---

## Structured Logging

### JSON Logging

```python
from cardlink.observability import get_observability

obs = get_observability()
logger = obs.logger.get_logger("session_manager")

# Basic logging
logger.info("Session started")

# With context fields
logger.info("APDU command sent",
    command_type="SELECT",
    device_id="device_123",
    apdu_hex="00A4040000"
)

# Log levels
logger.debug("Detailed debug information", data=raw_data)
logger.info("Informational message", status="ok")
logger.warning("Warning condition", retry_count=3)
logger.error("Error occurred", error_code="E001")

# Exception logging with traceback
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed", operation="risky")
```

**JSON output:**

```json
{
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "level": "INFO",
  "logger": "session_manager",
  "message": "APDU command sent",
  "command_type": "SELECT",
  "device_id": "device_123",
  "apdu_hex": "00A4040000",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

### Trace Correlation

When tracing is enabled, log entries automatically include trace and span IDs:

```python
# Logs within a span include trace context
with obs.tracer.start_span("process_session") as span:
    logger = obs.logger.get_logger("session")
    logger.info("Processing session", session_id="123")
    # Log entry includes trace_id and span_id from active span
```

This enables correlation between logs and traces in observability platforms (Grafana Loki + Tempo, Elastic APM, etc.).

### Component Loggers

```python
# Create logger with persistent context
logger = obs.logger.get_logger("device_manager")

# Add context that persists across log calls
contextual_logger = logger.with_context(
    device_id="device_456",
    device_type="physical"
)

# All logs from this logger include device_id and device_type
contextual_logger.info("Device connected")
contextual_logger.info("Sending command")
contextual_logger.warning("Timeout occurred", timeout_seconds=5)

# Set component log level
obs.logger.set_level("device_manager", "DEBUG")
obs.logger.set_level("database", "WARNING")
```

---

## Dashboards

### Grafana Dashboards

The observability system includes pre-built Grafana dashboards:

1. **OTA Overview** - Session metrics, triggers, success rates
2. **APDU Analysis** - Command types, latencies, error rates
3. **Device Status** - Connected devices, errors, operation durations
4. **Test Results** - Pass/fail rates, duration trends, flaky tests

### Dashboard Templates

```python
from cardlink.observability.dashboards import DashboardTemplates

templates = DashboardTemplates()

# Generate all dashboards
templates.export_all(output_dir="./dashboards")

# Files created:
# - dashboards/ota_overview.json
# - dashboards/apdu_analysis.json
# - dashboards/device_status.json
# - dashboards/test_results.json

# Generate specific dashboard
ota_dashboard = templates.ota_overview()
with open("ota_dashboard.json", "w") as f:
    f.write(ota_dashboard)
```

**Import into Grafana:**

```bash
# Via UI
# 1. Open Grafana (http://localhost:3000)
# 2. Navigate to Dashboards → Import
# 3. Upload JSON file or paste JSON
# 4. Select Prometheus data source
# 5. Click Import

# Via API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @dashboards/ota_overview.json
```

---

## Alerting

### Prometheus Alerting Rules

Pre-defined alerting rules for common error conditions:

```python
from cardlink.observability.alerting import AlertingRules

rules = AlertingRules()

# Export Prometheus-compatible YAML
rules.export_yaml("alerts.yml")
```

**Generated alerts:**

```yaml
# alerts.yml
groups:
  - name: gp_ota_errors
    interval: 30s
    rules:
      - alert: HighAPDUErrorRate
        expr: |
          rate(apdu_responses_total{status_category="error"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High APDU error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: SessionTimeoutSpike
        expr: |
          rate(ota_sessions_total{status="timeout"}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Session timeout rate increasing"

      - alert: TLSHandshakeFailures
        expr: |
          rate(tls_handshakes_total{result="failure"}[5m]) > 0.01
        for: 2m
        labels:
          severity: warning

      - alert: DeviceDisconnected
        expr: |
          devices_connected == 0
        for: 1m
        labels:
          severity: critical

      - alert: DatabaseConnectionFailure
        expr: |
          up{job="gp-ota-tester-health"} == 0
        for: 1m
        labels:
          severity: critical

      - alert: HighAPDULatency
        expr: |
          histogram_quantile(0.95, rate(apdu_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile APDU latency above 100ms"

      - alert: LongSessionDuration
        expr: |
          histogram_quantile(0.95, rate(ota_session_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
```

### Alert Customization

```python
# Customize thresholds
rules = AlertingRules(
    high_error_rate_threshold=0.05,  # 5% instead of 10%
    latency_threshold_seconds=0.050,  # 50ms instead of 100ms
)

# Get rules programmatically
all_rules = rules.get_rules()
for rule in all_rules:
    print(f"Alert: {rule['alert']}")
    print(f"  Expression: {rule['expr']}")
    print(f"  Severity: {rule['labels']['severity']}")
```

**Configure Prometheus Alertmanager:**

```yaml
# prometheus.yml
rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

---

## CLI Commands

### Metrics CLI

```bash
# Show current metrics summary
cardlink-metrics status

# Export metrics to file
cardlink-metrics export --format prometheus --output metrics.txt
cardlink-metrics export --format json --output metrics.json

# Health status
cardlink-metrics health
cardlink-metrics health --verbose

# Test connectivity
cardlink-metrics test --otlp --metrics --health

# Configuration
cardlink-metrics config show
cardlink-metrics config set metrics.port 9100

# Export Grafana dashboards
cardlink-metrics dashboards export ./dashboards

# Show version
cardlink-metrics --version
```

---

## Integration Examples

### PSK-TLS Server Integration

```python
from cardlink.server import AdminServer, ServerConfig
from cardlink.observability import get_observability

# Initialize observability
obs = get_observability()
obs.initialize()

# Create server with observability
server = AdminServer(config, key_store)

# Add metrics to TLS handshake
@server.on_handshake_complete
def on_handshake(event):
    obs.metrics.record_tls_handshake(
        result="success",
        cipher_suite=event.cipher_suite,
        duration=event.duration
    )
    obs.metrics.inc_tls_connections()

# Add metrics to APDU exchange
@server.on_apdu_received
def on_apdu(event):
    with obs.tracer.start_span("apdu_exchange") as span:
        span.set_attribute("command", event.apdu_hex[:4])

        obs.metrics.record_apdu_command(
            command_type=parse_command_type(event.apdu),
            device_type="physical"
        )

@server.on_apdu_sent
def on_response(event):
    obs.metrics.record_apdu_response(
        status_word=event.sw_hex,
        status_category=categorize_status(event.sw_hex)
    )

# Add health check
def check_server_status():
    if server.is_running:
        return {"status": "healthy", "connections": server.connection_count}
    return {"status": "unhealthy", "error": "Server not running"}

obs.health.register_check("psk_tls_server", check_server_status)
```

### Database Integration

```python
from cardlink.database import get_unit_of_work
from cardlink.observability import get_observability

obs = get_observability()
uow = get_unit_of_work()

# Add metrics to database operations
original_execute = uow.session.execute

def instrumented_execute(statement, *args, **kwargs):
    with obs.tracer.start_span("db_query") as span:
        span.set_attribute("query_type", "SELECT")  # Parse from statement

        start = time.time()
        result = original_execute(statement, *args, **kwargs)
        duration = time.time() - start

        obs.metrics.record_db_query_duration(
            operation="SELECT",
            duration=duration
        )

        return result

uow.session.execute = instrumented_execute

# Add health check
def check_database():
    try:
        with uow:
            uow.session.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

obs.health.register_check("database", check_database)
```

### Test Runner Integration

```python
import pytest
from cardlink.observability import get_observability

obs = get_observability()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Record test execution metrics."""
    with obs.tracer.start_span(f"test_{item.name}") as span:
        span.set_attribute("test_suite", item.parent.name)
        span.set_attribute("test_name", item.name)

        start = time.time()
        outcome = yield
        duration = time.time() - start

        status = "passed" if outcome.get_result() else "failed"

        obs.metrics.record_test_result(
            suite_name=item.parent.name,
            status=status,
            duration=duration
        )

        span.set_attribute("status", status)
        span.set_attribute("duration_seconds", duration)
```

---

## Best Practices

### Metrics

1. **Use appropriate metric types**
   - Counters for cumulative values (total requests, errors)
   - Histograms for distributions (latencies, sizes)
   - Gauges for current values (active connections, queue depth)
   - Info for static metadata (version, build info)

2. **Control label cardinality**
   ```python
   # ❌ Bad - unbounded cardinality
   obs.metrics.record_apdu_command(
       command_type="SELECT",
       device_id="device_12345678"  # Unique per device!
   )

   # ✅ Good - bounded cardinality
   obs.metrics.record_apdu_command(
       command_type="SELECT",
       device_type="physical"  # Limited set of values
   )
   ```

3. **Use consistent naming**
   - Follow Prometheus conventions: `component_metric_name_unit`
   - Use base units (seconds, bytes, not milliseconds, kilobytes)
   - Use suffixes: `_total` for counters, `_seconds` for durations

### Tracing

1. **Trace meaningful operations**
   - Trace user requests end-to-end
   - Trace expensive operations (database queries, external API calls)
   - Don't trace every function call

2. **Add meaningful attributes**
   ```python
   with obs.tracer.start_span("process_session") as span:
       span.set_attribute("session_id", session_id)
       span.set_attribute("device_type", device_type)
       span.set_attribute("command_count", len(commands))
   ```

3. **Use sampling in production**
   ```python
   # Sample 10% of traces in high-volume environments
   config.tracing.sample_rate = 0.1
   ```

### Health Checks

1. **Keep checks fast (<5s)**
   ```python
   # ❌ Bad - slow check
   def check_external_service():
       return requests.get("https://slow-api.com/health", timeout=30)

   # ✅ Good - fast check with timeout
   def check_external_service():
       return requests.get("https://api.com/health", timeout=2)
   ```

2. **Distinguish liveness from readiness**
   - Liveness: Is the application running?
   - Readiness: Is the application ready to serve traffic?

3. **Provide actionable information**
   ```python
   return {
       "status": "unhealthy",
       "error": "Database connection failed: timeout after 5s",
       "action": "Check database connectivity and credentials"
   }
   ```

### Logging

1. **Use structured fields**
   ```python
   # ❌ Bad - unstructured
   logger.info(f"Session {session_id} completed in {duration}ms")

   # ✅ Good - structured
   logger.info("Session completed", session_id=session_id, duration_ms=duration)
   ```

2. **Include context**
   ```python
   logger = obs.logger.get_logger("component").with_context(
       request_id=request_id,
       user_id=user_id
   )
   ```

3. **Choose appropriate log levels**
   - DEBUG: Detailed diagnostic information
   - INFO: General operational events
   - WARNING: Unexpected but handled situations
   - ERROR: Error conditions requiring attention
   - CRITICAL: System failure requiring immediate action

---

## Troubleshooting

### Metrics Not Appearing

```bash
# Check metrics endpoint is accessible
curl http://localhost:9090/metrics

# Check Prometheus configuration
cat prometheus.yml

# Verify service discovery
curl http://localhost:9090/api/v1/targets

# Check Prometheus logs
docker logs prometheus
```

### Traces Not Exporting

```bash
# Verify OTLP endpoint is reachable
telnet localhost 4317

# Check application logs for export errors
grep -i "otlp" /var/log/gp-ota/app.log

# Verify Jaeger is receiving traces
curl http://localhost:16686/api/services

# Check trace sampling rate
echo $GP_TRACE_SAMPLE_RATE
```

### Health Checks Failing

```python
# Run individual checks
result = obs.health.run_check("database")
print(f"Status: {result.status}")
print(f"Error: {result.error}")
print(f"Duration: {result.duration_ms}ms")

# Increase check timeout
config.health.check_timeout = 10.0

# Check health endpoint directly
curl -v http://localhost:8080/health
```

### High CPU Usage from Metrics

```python
# Reduce system metrics collection frequency
config.metrics.collection_interval = 60  # Every 60 seconds instead of 15

# Reduce label cardinality
# Review metrics with high cardinality labels
```

### Missing Trace Context in Logs

```python
# Verify trace correlation is enabled
config.logging.trace_correlation = True

# Ensure logging is initialized after tracing
obs.initialize(config)  # Initializes tracing first, then logging

# Check active span exists
from opentelemetry import trace
current_span = trace.get_current_span()
print(f"Trace ID: {current_span.get_span_context().trace_id}")
```

---

## Next Steps

- **Set up Prometheus**: [Download Prometheus](https://prometheus.io/download/)
- **Set up Grafana**: [Grafana Installation](https://grafana.com/docs/grafana/latest/setup-grafana/installation/)
- **Set up Jaeger**: [Jaeger Getting Started](https://www.jaegertracing.io/docs/latest/getting-started/)
- **Configure Alertmanager**: [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)

For detailed implementation, see the [Observability Quick Reference](observability-quick-reference.md).
