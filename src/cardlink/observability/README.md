# Observability Module

Comprehensive observability implementation for CardLink, providing metrics collection, distributed tracing, health checks, and structured logging.

## Components Implemented

### 1. Configuration (`config.py`) ✅
- **ObservabilityConfig**: Main configuration class
- **MetricsConfig**: Prometheus metrics configuration
- **TracingConfig**: OpenTelemetry tracing configuration
- **HealthConfig**: Health check configuration
- **LoggingConfig**: Structured logging configuration

Environment variables support with `GP_*` prefix.

### 2. Manager (`manager.py`) ✅
- **ObservabilityManager**: Singleton manager for all observability components
- Thread-safe initialization and shutdown
- Component lifecycle management
- Accessor properties for metrics, tracer, health, logger

### 3. Metrics Module (`metrics/`) ✅ (IN PROGRESS)
- **MetricsRegistry**: Prometheus metrics definitions
  - APDU operation metrics (commands, responses, errors, timing)
  - Session metrics (active sessions, duration, errors)
  - BIP connection metrics (connections, data transfer, duration)
  - System metrics (CPU, memory, disk, network, uptime)
  - Database metrics (connections, query duration, operations)

- **MetricsCollector**: High-level metrics collection API
  - `record_apdu_command()`, `record_apdu_response()`
  - `record_session_start()`, `record_session_end()`
  - `record_bip_connection_open()`, `record_bip_data_transfer()`
  - `record_database_connection_change()`, `time_database_query()`
  - Context managers for timing operations
  - Automatic system metrics collection in background thread

- **MetricsServer**: HTTP server for Prometheus `/metrics` endpoint
  - HTTP Basic authentication support
  - Configurable port and path
  - Background thread execution

### 4. Dependencies ✅
Added to `pyproject.toml`:
```toml
[project.optional-dependencies]
observability = [
    "prometheus-client>=0.17.0",
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp>=1.20.0",
    "psutil>=5.9.0",
]
```

## Installation

```bash
# Install observability dependencies
pip install -e ".[observability]"

# Or install all dependencies
pip install -e ".[all]"
```

## Quick Start

```python
from cardlink.observability import get_observability
from cardlink.observability.config import ObservabilityConfig, MetricsConfig

# Initialize with default configuration (from environment)
obs = get_observability()
obs.initialize()

# Or with custom configuration
config = ObservabilityConfig(
    metrics=MetricsConfig(
        enabled=True,
        port=9090,
        path="/metrics",
    )
)
obs.initialize(config)

# Record metrics
obs.metrics.record_apdu_command("SELECT", "physical")
obs.metrics.record_apdu_response(0x9000, 150, True)

# Time operations
with obs.metrics.time_apdu_command("SELECT"):
    # Your APDU command here
    pass

# Shutdown
obs.shutdown()
```

## Environment Variables

### Metrics
- `GP_METRICS_ENABLED`: Enable metrics (default: true)
- `GP_METRICS_PORT`: Metrics HTTP port (default: 9090)
- `GP_METRICS_PATH`: Metrics endpoint path (default: /metrics)
- `GP_METRICS_AUTH_USERNAME`: HTTP Basic auth username
- `GP_METRICS_AUTH_PASSWORD`: HTTP Basic auth password
- `GP_METRICS_INTERVAL`: System metrics collection interval in seconds (default: 15)

### Tracing
- `GP_TRACING_ENABLED`: Enable tracing (default: false)
- `GP_OTLP_ENDPOINT`: OTLP collector endpoint (e.g., localhost:4317)
- `GP_OTLP_PROTOCOL`: OTLP protocol - grpc or http (default: grpc)
- `GP_SERVICE_NAME`: Service name for traces (default: cardlink)
- `GP_SERVICE_VERSION`: Service version (default: 1.0.0)
- `GP_TRACE_SAMPLE_RATE`: Trace sampling rate 0.0-1.0 (default: 1.0)

### Health
- `GP_HEALTH_ENABLED`: Enable health checks (default: true)
- `GP_HEALTH_PORT`: Health check HTTP port (default: 8080)
- `GP_HEALTH_TIMEOUT`: Health check timeout in seconds (default: 5.0)

### Logging
- `GP_LOG_LEVEL`: Log level - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `GP_LOG_FORMAT`: Log format - json or text (default: json)
- `GP_LOG_TRACE_CORRELATION`: Include trace IDs in logs (default: true)
- `GP_LOG_FILE`: Log file path (optional, defaults to stdout)

## Metrics Exposed

All metrics are prefixed with `cardlink_`.

### APDU Metrics
- `cardlink_apdu_commands_total`: Total APDU commands sent (labels: command, interface)
- `cardlink_apdu_responses_total`: Total APDU responses received (labels: status_word, success)
- `cardlink_apdu_errors_total`: Total APDU errors (labels: error_type, command)
- `cardlink_apdu_response_time_seconds`: APDU response time histogram (labels: command)
- `cardlink_apdu_data_bytes`: APDU data size histogram (labels: direction)

### Session Metrics
- `cardlink_active_sessions`: Currently active sessions (labels: session_type)
- `cardlink_session_duration_seconds`: Session duration histogram (labels: session_type, status)
- `cardlink_session_errors_total`: Session errors (labels: session_type, error_type)
- `cardlink_sessions_total`: Total sessions started (labels: session_type, protocol)

### BIP Metrics
- `cardlink_bip_connections_active`: Active BIP connections (labels: bearer_type)
- `cardlink_bip_bytes_transferred_total`: BIP data transferred (labels: direction, bearer_type)
- `cardlink_bip_connection_duration_seconds`: BIP connection duration (labels: bearer_type, status)
- `cardlink_bip_errors_total`: BIP errors (labels: error_type, bearer_type)

### System Metrics
- `cardlink_system_cpu_usage_percent`: CPU usage percentage
- `cardlink_system_memory_usage_bytes`: Memory usage in bytes
- `cardlink_system_disk_usage_bytes`: Disk usage (labels: path)
- `cardlink_system_network_bytes_total`: Network bytes (labels: direction, interface)
- `cardlink_system_process_uptime_seconds`: Process uptime
- `cardlink_system_threads_active`: Active thread count

### Database Metrics
- `cardlink_database_connections_active`: Active database connections
- `cardlink_database_query_duration_seconds`: Query execution time (labels: operation, table)
- `cardlink_database_operations_total`: Database operations (labels: operation, table, status)
- `cardlink_database_errors_total`: Database errors (labels: error_type, operation)

## Pending Implementation

### Tracing Module
- TracingProvider (OpenTelemetry provider setup)
- Span management
- Trace context propagation
- OTLP exporter configuration

### Health Module
- HealthChecker (health check orchestrator)
- Pre-defined health checks (database, server, system)
- Health HTTP endpoint

### Logging Module
- LoggerManager (structured logging setup)
- JSON formatter with trace correlation
- Component-specific loggers
- Log rotation configuration

### Dashboards and Alerting
- Grafana dashboard templates
- Prometheus alerting rules

### CLI Commands
- `gp-observe metrics` - View metrics
- `gp-observe traces` - View traces
- `gp-observe health` - Run health checks
- `gp-observe logs` - View logs

## Integration with Existing Components

The observability module is designed to integrate with:
- **Server** (`cardlink.server`): Session tracking, connection metrics
- **Database** (`cardlink.database`): Query timing, connection pooling metrics
- **Phone** (`cardlink.phone`): BIP connection metrics
- **Simulator** (`cardlink.simulator`): APDU operation metrics

## Testing

```bash
# Run observability tests
pytest tests/observability/ -v

# Run with coverage
pytest tests/observability/ --cov=cardlink.observability
```

## Architecture

```
cardlink.observability/
├── __init__.py           # Public API exports
├── config.py             # ✅ Configuration classes
├── manager.py            # ✅ Singleton manager
├── README.md             # This file
├── metrics/              # Prometheus metrics
│   ├── __init__.py       # ✅ Metrics exports
│   ├── registry.py       # ✅ Metric definitions (needs syntax fix)
│   ├── collector.py      # ✅ High-level collection API
│   └── server.py         # ✅ HTTP server
├── tracing/              # OpenTelemetry tracing (TODO)
│   ├── __init__.py
│   ├── provider.py       # Tracing provider
│   └── span.py           # Span management
├── health/               # Health checks (TODO)
│   ├── __init__.py
│   ├── checker.py        # Health checker
│   ├── checks.py         # Pre-defined checks
│   └── server.py         # Health HTTP endpoint
├── logging/              # Structured logging (TODO)
│   ├── __init__.py
│   ├── manager.py        # Logger manager
│   └── formatters.py     # JSON formatters
├── dashboards/           # Grafana dashboards (TODO)
│   └── cardlink.json
└── alerting/             # Prometheus alerts (TODO)
    └── rules.yml
```

## Status Summary

- ✅ **Configuration**: Fully implemented
- ✅ **Manager**: Fully implemented
- ⚠️  **Metrics**: Implementation complete, minor syntax errors to fix
- ❌ **Tracing**: Not started
- ❌ **Health**: Not started
- ❌ **Logging**: Not started
- ❌ **Dashboards**: Not started
- ❌ **Alerting**: Not started
- ❌ **CLI**: Not started

## Next Steps

1. Fix syntax errors in `metrics/registry.py`
2. Run and fix tests in `tests/observability/test_metrics.py`
3. Implement TracingProvider
4. Implement HealthChecker
5. Implement LoggerManager
6. Create Grafana dashboards
7. Create Prometheus alerting rules
8. Add CLI commands for observability
9. Integration with existing components
10. End-to-end testing
