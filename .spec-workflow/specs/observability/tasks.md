# Tasks Document: Observability

## Task Overview

This document breaks down the Observability component implementation into actionable development tasks organized by component and functionality.

## Tasks

### 1. Project Setup and Dependencies

_Leverage:_ Python package management, pytest framework
_Requirements:_ R1, R2, R3, R4, R5, R6, R7, R8, R9
_Prompt:_ Role: Python developer | Task: Set up the observability package structure with all required dependencies including prometheus-client, opentelemetry SDK, psutil, and create pytest fixtures for testing metrics and tracing functionality | Restrictions: Use versions prometheus-client>=0.17.0, opentelemetry>=1.20.0; ensure all dependencies are properly specified in pyproject.toml | Success: Package structure exists at cardlink/observability/, all dependencies install without conflicts, pytest fixtures are available for testing

- [ ] 1.1. Create `cardlink/observability/` package structure
- [ ] 1.2. Add prometheus-client dependency to pyproject.toml (>=0.17.0)
- [ ] 1.3. Add opentelemetry-api and opentelemetry-sdk dependencies (>=1.20.0)
- [ ] 1.4. Add opentelemetry-exporter-otlp dependency
- [ ] 1.5. Add psutil dependency for system metrics
- [ ] 1.6. Add optional jaeger and zipkin exporter dependencies
- [ ] 1.7. Create pytest fixtures for metrics and tracing testing

### 2. Observability Configuration

_Leverage:_ Python dataclasses, environment variable parsing
_Requirements:_ R1, R3, R8, R10, R11
_Prompt:_ Role: Configuration engineer | Task: Implement ObservabilityConfig dataclass with comprehensive configuration options for metrics (port, path, auth), tracing (OTLP endpoint, protocol), health checks (port, enabled), and logging (level, format, trace correlation) with environment variable parsing support | Restrictions: All configuration must be environment-variable configurable; provide sensible defaults; include validation | Success: Configuration can be instantiated from environment variables, all fields have proper defaults, unit tests verify configuration parsing and validation

- [ ] 2.1. Create `config.py` with ObservabilityConfig dataclass
- [ ] 2.2. Add metrics configuration (enabled, port, path, auth)
- [ ] 2.3. Add tracing configuration (enabled, otlp_endpoint, protocol)
- [ ] 2.4. Add health configuration (port, enabled)
- [ ] 2.5. Add logging configuration (level, format, trace_correlation)
- [ ] 2.6. Implement environment variable parsing for configuration
- [ ] 2.7. Write unit tests for configuration

### 3. Observability Manager Implementation

_Leverage:_ Singleton pattern, Python threading, context management
_Requirements:_ R1, R8, R10, R11
_Prompt:_ Role: Software architect | Task: Create ObservabilityManager singleton class that coordinates initialization and shutdown of all observability components (metrics, tracing, health checks, logging) with thread-safe initialization and global accessor function | Restrictions: Must use thread-safe singleton implementation; provide clean shutdown handling; expose metrics, tracer, health, and logger properties | Success: Manager initializes all components correctly, shutdown cleans up resources, singleton access is thread-safe, unit tests verify lifecycle management

- [ ] 3.1. Create `manager.py` with ObservabilityManager class
- [ ] 3.2. Implement singleton pattern with thread-safe initialization
- [ ] 3.3. Implement `initialize()` to start all components
- [ ] 3.4. Implement `shutdown()` to stop all components
- [ ] 3.5. Add `metrics` property for MetricsCollector access
- [ ] 3.6. Add `tracer` property for TracingProvider access
- [ ] 3.7. Add `health` property for HealthChecker access
- [ ] 3.8. Add `logger` property for StructuredLogger access
- [ ] 3.9. Implement `get_observability()` global accessor
- [ ] 3.10. Write unit tests for ObservabilityManager

### 4. Metrics Registry Implementation

_Leverage:_ Python enums and dataclasses, Prometheus metric types
_Requirements:_ R1, R2, R3, R4, R5, R6, R7
_Prompt:_ Role: Metrics engineer | Task: Define comprehensive metrics registry with MetricType enum and MetricDefinition dataclass covering all CardLink operations: APDU commands/responses, TLS sessions, OTA sessions, device connections, test execution, and system resources | Restrictions: Follow Prometheus naming conventions; use appropriate metric types (Counter, Histogram, Gauge, Info); include proper help text and labels for each metric | Success: All required metrics defined with correct types, labels properly specified, registry is easily extensible, unit tests verify metric definitions

- [ ] 4.1. Create `metrics/registry.py` with MetricType enum
- [ ] 4.2. Create MetricDefinition dataclass
- [ ] 4.3. Define APDU metrics (commands_total, responses_total, duration, bytes)
- [ ] 4.4. Define TLS metrics (handshakes_total, duration, connections_active)
- [ ] 4.5. Define session metrics (active, total, duration, triggers)
- [ ] 4.6. Define device metrics (connected, errors, at_duration, adb_duration)
- [ ] 4.7. Define test metrics (total, duration)
- [ ] 4.8. Define system metrics (cpu, memory, db_connections, uptime)
- [ ] 4.9. Define build_info metric
- [ ] 4.10. Write unit tests for registry definitions

### 5. Metrics Collector Implementation

_Leverage:_ Prometheus Python client library, psutil
_Requirements:_ R1, R2, R3, R4, R5, R6, R7
_Prompt:_ Role: Metrics collection engineer | Task: Implement MetricsCollector class that registers all metrics from the registry and provides convenient recording methods for APDU operations, TLS sessions, OTA sessions, device operations, test execution, and system metrics using psutil | Restrictions: Ensure thread-safe metric updates; validate label values; handle metric recording errors gracefully; keep recording overhead minimal (<1% CPU) | Success: All metrics can be recorded via type-safe methods, system metrics are accurately collected, unit tests verify correct metric updates and label handling

- [ ] 5.1. Create `metrics/collector.py` with MetricsCollector class
- [ ] 5.2. Implement `__init__` with CollectorRegistry setup
- [ ] 5.3. Implement `_register_metrics()` to create all metrics from registry
- [ ] 5.4. Implement `_create_metric()` for Counter, Histogram, Gauge, Info types
- [ ] 5.5. Implement `get_metric(name)` accessor
- [ ] 5.6. Implement APDU recording methods:
  - [ ] 5.6.1. `record_apdu_command(command_type, device_type)`
  - [ ] 5.6.2. `record_apdu_response(status_word, status_category)`
  - [ ] 5.6.3. `record_apdu_duration(command_type, duration)`
  - [ ] 5.6.4. `record_apdu_bytes(direction, byte_count)`
- [ ] 5.7. Implement TLS recording methods:
  - [ ] 5.7.1. `record_tls_handshake(result, cipher_suite, duration)`
  - [ ] 5.7.2. `set_tls_connections(count)`
  - [ ] 5.7.3. `inc_tls_connections()` / `dec_tls_connections()`
- [ ] 5.8. Implement session recording methods:
  - [ ] 5.8.1. `set_active_sessions(count, device_type)`
  - [ ] 5.8.2. `record_session_complete(status, type, device_type, duration)`
  - [ ] 5.8.3. `record_trigger_sent(trigger_type)`
- [ ] 5.9. Implement device recording methods:
  - [ ] 5.9.1. `set_devices_connected(count, device_type)`
  - [ ] 5.9.2. `record_device_error(device_type, error_type)`
  - [ ] 5.9.3. `record_at_command_duration(command, duration)`
  - [ ] 5.9.4. `record_adb_operation_duration(operation, duration)`
- [ ] 5.10. Implement test recording methods:
  - [ ] 5.10.1. `record_test_result(suite_name, status, duration)`
- [ ] 5.11. Implement system metrics:
  - [ ] 5.11.1. `update_system_metrics()` using psutil
  - [ ] 5.11.2. `set_build_info(version, python_version, platform)`
- [ ] 5.12. Write unit tests for MetricsCollector

### 6. Metrics HTTP Server Implementation

_Leverage:_ Python http.server, Prometheus text format
_Requirements:_ R1
_Prompt:_ Role: Backend engineer | Task: Implement HTTP server for exposing Prometheus metrics endpoint with configurable port and path, supporting optional HTTP Basic authentication, and providing <100ms response times | Restrictions: Use Python's http.server; properly handle concurrent requests; support graceful shutdown; suppress request logging to avoid log spam | Success: /metrics endpoint serves Prometheus-format metrics within 100ms, authentication works when configured, server starts/stops cleanly, integration tests verify endpoint behavior

- [ ] 6.1. Implement `start_server(port, path)` method
- [ ] 6.2. Create MetricsHandler HTTP request handler
- [ ] 6.3. Implement `/metrics` endpoint with Prometheus format
- [ ] 6.4. Add optional HTTP Basic authentication
- [ ] 6.5. Implement `stop_server()` method
- [ ] 6.6. Implement `get_metrics_text()` for direct access
- [ ] 6.7. Add request logging suppression
- [ ] 6.8. Write integration tests for metrics endpoint

### 7. Tracing Provider Implementation

_Leverage:_ OpenTelemetry Python SDK, OTLP exporters
_Requirements:_ R8, R9
_Prompt:_ Role: Observability engineer | Task: Implement TracingProvider class supporting OpenTelemetry with OTLP export (gRPC and HTTP), BatchSpanProcessor for efficient span batching, context propagation, and decorator support for easy span creation | Restrictions: Support both gRPC and HTTP OTLP protocols; include proper resource attributes (service.name, service.version); handle exporter failures gracefully; provide both context manager and decorator interfaces | Success: Traces export to OTLP endpoint, spans include proper attributes, context propagation works, decorator simplifies instrumentation, unit tests verify tracing functionality

- [ ] 7.1. Create `tracing/provider.py` with TracingProvider class
- [ ] 7.2. Implement `__init__` with service name, version, OTLP config
- [ ] 7.3. Implement `initialize()` with Resource and TracerProvider setup
- [ ] 7.4. Implement OTLP exporter configuration (gRPC and HTTP)
- [ ] 7.5. Implement BatchSpanProcessor setup
- [ ] 7.6. Implement `shutdown()` for clean shutdown
- [ ] 7.7. Implement `get_tracer()` accessor
- [ ] 7.8. Implement `start_span(name, kind, attributes)` context manager
- [ ] 7.9. Implement `current_span()` accessor
- [ ] 7.10. Implement `inject_context(carrier)` for propagation
- [ ] 7.11. Implement `extract_context(carrier)` for propagation
- [ ] 7.12. Implement `trace_decorator(name, kind)` function decorator
- [ ] 7.13. Write unit tests for TracingProvider

### 8. Span Manager Implementation

_Leverage:_ OpenTelemetry span API, context managers
_Requirements:_ R9
_Prompt:_ Role: Tracing engineer | Task: Create SpanManager class providing convenient context managers for creating spans for common CardLink operations (APDU exchanges, TLS handshakes, sessions, database queries, test execution) with proper attributes and error handling | Restrictions: Use context managers for automatic span lifecycle management; include relevant operation attributes; set error status on exceptions; follow OpenTelemetry semantic conventions where applicable | Success: Span context managers simplify instrumentation, spans include operation-specific attributes, errors are properly recorded, unit tests verify span creation and attributes

- [ ] 8.1. Create `tracing/spans.py` with SpanManager class
- [ ] 8.2. Implement `apdu_span(command_type, device_id)` context manager
- [ ] 8.3. Implement `tls_handshake_span(client_address)` context manager
- [ ] 8.4. Implement `session_span(session_id, session_type)` context manager
- [ ] 8.5. Implement `db_span(operation, table)` context manager
- [ ] 8.6. Implement `test_span(suite_name, test_name)` context manager
- [ ] 8.7. Implement `add_apdu_response(span, status_word, duration_ms)`
- [ ] 8.8. Add error status handling for spans
- [ ] 8.9. Write unit tests for SpanManager

### 9. Health Checker Implementation

_Leverage:_ Python dataclasses, HTTP status codes
_Requirements:_ R10
_Prompt:_ Role: Reliability engineer | Task: Implement HealthChecker class supporting pluggable health checks with HealthStatus enum (healthy, degraded, unhealthy), aggregated health reporting, and separate liveness/readiness checks completing within 5 seconds | Restrictions: Health checks must timeout within 5 seconds; provide detailed failure information; aggregate multiple check results into overall health; support dynamic registration/unregistration of checks | Success: Health checks can be registered and run, overall health correctly aggregates individual checks, liveness and readiness checks work as expected, unit tests verify check execution and aggregation

- [ ] 9.1. Create `health/checker.py` with HealthStatus enum
- [ ] 9.2. Create HealthCheckResult dataclass
- [ ] 9.3. Create OverallHealth dataclass
- [ ] 9.4. Create HealthChecker class
- [ ] 9.5. Implement `register_check(name, check_fn)` method
- [ ] 9.6. Implement `unregister_check(name)` method
- [ ] 9.7. Implement `run_check(name)` with timing and error handling
- [ ] 9.8. Implement `run_all_checks()` with aggregated status
- [ ] 9.9. Implement `check_liveness()` basic check
- [ ] 9.10. Implement `check_readiness()` comprehensive check
- [ ] 9.11. Write unit tests for HealthChecker

### 10. Pre-defined Health Checks

_Leverage:_ Database connections, HTTP requests, psutil
_Requirements:_ R10
_Prompt:_ Role: Operations engineer | Task: Create factory functions for common health checks including database connectivity, metrics endpoint availability, disk space monitoring, and memory usage monitoring with configurable thresholds | Restrictions: Checks must complete within 5 seconds; handle connection failures gracefully; provide informative error messages; support threshold configuration | Success: Factory functions create working health checks, database check verifies connectivity, disk/memory checks respect thresholds, unit tests verify check behavior

- [ ] 10.1. Create `health/checks.py` with check factories
- [ ] 10.2. Implement `create_database_check(db_manager)` factory
- [ ] 10.3. Implement `create_metrics_check(metrics_port)` factory
- [ ] 10.4. Implement `create_disk_space_check(path, threshold)` factory
- [ ] 10.5. Implement `create_memory_check(threshold)` factory
- [ ] 10.6. Write unit tests for pre-defined checks

### 11. Health HTTP Server Implementation

_Leverage:_ Python http.server, JSON serialization
_Requirements:_ R10
_Prompt:_ Role: API developer | Task: Implement HTTP server exposing health check endpoints (/health for overall health, /health/live for liveness, /health/ready for readiness) returning JSON responses with appropriate HTTP status codes (200 for healthy, 503 for unhealthy) | Restrictions: Return proper HTTP status codes; use JSON format for responses; complete checks within 5 seconds; support graceful shutdown | Success: Health endpoints return correct status codes and JSON, liveness checks basic availability, readiness verifies all dependencies, integration tests verify endpoint behavior

- [ ] 11.1. Implement `start_server(port)` method
- [ ] 11.2. Create HealthHandler HTTP request handler
- [ ] 11.3. Implement `/health` endpoint (overall health)
- [ ] 11.4. Implement `/health/live` endpoint (liveness)
- [ ] 11.5. Implement `/health/ready` endpoint (readiness)
- [ ] 11.6. Implement JSON response formatting
- [ ] 11.7. Implement `stop_server()` method
- [ ] 11.8. Write integration tests for health endpoints

### 12. Structured Logger Implementation

_Leverage:_ Python logging module, JSON serialization, OpenTelemetry context
_Requirements:_ R11
_Prompt:_ Role: Logging engineer | Task: Create StructuredFormatter for JSON-formatted logs and StructuredLogger class that integrates with OpenTelemetry tracing by including trace_id and span_id in log entries, supporting per-component log level configuration | Restrictions: Use JSON format with ISO 8601 timestamps; extract trace context when available; include all required fields (timestamp, level, message, component, context); support exception formatting | Success: Logs output in structured JSON format, trace IDs correlate with spans when tracing is active, log levels can be configured per component, unit tests verify formatting and context extraction

- [ ] 12.1. Create `logging/structured.py` with StructuredFormatter class
- [ ] 12.2. Implement JSON formatting with all fields
- [ ] 12.3. Implement trace context extraction (trace_id, span_id)
- [ ] 12.4. Implement exception formatting
- [ ] 12.5. Create StructuredLogger class
- [ ] 12.6. Implement `_configure_root()` for root logger setup
- [ ] 12.7. Implement `get_logger(name)` accessor
- [ ] 12.8. Implement `set_level(name, level)` method
- [ ] 12.9. Write unit tests for StructuredLogger

### 13. Component Logger Implementation

_Leverage:_ Python logging, context management
_Requirements:_ R11
_Prompt:_ Role: Developer experience engineer | Task: Create ComponentLogger class providing convenient logging methods (debug, info, warning, error, exception) with context enrichment capability via with_context() method for adding persistent contextual fields to log entries | Restrictions: Support standard log levels; maintain context across log calls; include traceback for exception logging; make context immutable to prevent cross-contamination | Success: Component loggers provide easy-to-use logging interface, context enrichment works correctly, exception logging includes tracebacks, unit tests verify logging and context handling

- [ ] 13.1. Create ComponentLogger class
- [ ] 13.2. Implement `with_context(**kwargs)` for adding context
- [ ] 13.3. Implement `_log(level, message, **kwargs)` internal method
- [ ] 13.4. Implement `debug()`, `info()`, `warning()`, `error()` methods
- [ ] 13.5. Implement `exception()` method with traceback
- [ ] 13.6. Write unit tests for ComponentLogger

### 14. Dashboard Templates Implementation

_Leverage:_ Grafana dashboard JSON format, Prometheus queries
_Requirements:_ R12
_Prompt:_ Role: Visualization engineer | Task: Create DashboardTemplates class generating Grafana-compatible dashboard JSON files for OTA overview (sessions, triggers), APDU analysis (commands, latencies), device status (connections, errors), and test results (pass/fail rates, duration trends) | Restrictions: Generate valid Grafana 9.0+ JSON; use appropriate visualization types; include proper Prometheus queries; support export to files | Success: Dashboard templates generate valid Grafana JSON, dashboards import successfully into Grafana, visualizations display correct metrics, unit tests verify JSON structure

- [ ] 14.1. Create `dashboards/templates.py` with DashboardTemplates class
- [ ] 14.2. Implement `ota_overview()` dashboard definition
- [ ] 14.3. Implement `apdu_analysis()` dashboard definition
- [ ] 14.4. Implement `device_status()` dashboard definition
- [ ] 14.5. Implement `test_results()` dashboard definition
- [ ] 14.6. Implement `export_all(output_dir)` method
- [ ] 14.7. Add proper Grafana panel configurations
- [ ] 14.8. Write unit tests for dashboard generation

### 15. Alerting Rules Implementation

_Leverage:_ Prometheus alerting rules, YAML format
_Requirements:_ R13
_Prompt:_ Role: SRE engineer | Task: Create AlertingRules class defining Prometheus-compatible alerting rules for error conditions (high APDU error rate, session timeouts, TLS failures, device disconnections, database failures) and performance issues (high latency, long durations) with customizable thresholds | Restrictions: Generate valid Prometheus alerting rules YAML; include severity levels (warning, critical); provide descriptive alert messages; make thresholds configurable | Success: Alerting rules generate valid YAML format, rules import into Prometheus, alerts fire correctly when conditions are met, unit tests verify rule generation

- [ ] 15.1. Create `alerting/rules.py` with AlertingRules class
- [ ] 15.2. Define error alerting rules:
  - [ ] 15.2.1. HighAPDUErrorRate alert
  - [ ] 15.2.2. SessionTimeoutSpike alert
  - [ ] 15.2.3. TLSHandshakeFailures alert
  - [ ] 15.2.4. DeviceDisconnected alert
  - [ ] 15.2.5. DatabaseConnectionFailure alert
- [ ] 15.3. Define performance alerting rules:
  - [ ] 15.3.1. HighAPDULatency alert
  - [ ] 15.3.2. LongSessionDuration alert
- [ ] 15.4. Implement `get_rules()` method
- [ ] 15.5. Implement `export_yaml(output_path)` method
- [ ] 15.6. Write unit tests for alerting rules

### 16. CLI: Status Command

_Leverage:_ Click CLI framework, metrics collector
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics status' command that displays a summary of current metric values with optional JSON output format for programmatic consumption | Restrictions: Use Click framework; present human-readable output by default; support --json flag for structured output; handle metrics server unavailability gracefully | Success: Status command displays current metrics summary, JSON output is valid and parseable, command handles errors gracefully, CLI tests verify output format

- [ ] 16.1. Create `cardlink/cli/metrics.py` with Click group
- [ ] 16.2. Implement `status` command
- [ ] 16.3. Display current metric values summary
- [ ] 16.4. Add `--json` flag for JSON output
- [ ] 16.5. Write CLI tests for status command

### 17. CLI: Export Command

_Leverage:_ Click CLI framework, Prometheus text format
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics export' command that exports all metrics in Prometheus or JSON format with optional file output, defaulting to stdout for easy piping | Restrictions: Support --format option (prometheus, json); support --output option for file path; default to stdout; validate format option | Success: Export command outputs metrics in specified format, file output works correctly, stdout output is pipeable, CLI tests verify export functionality

- [ ] 17.1. Implement `export` command
- [ ] 17.2. Add `--format` option (prometheus, json)
- [ ] 17.3. Add `--output` option for file path
- [ ] 17.4. Default to stdout if no output specified
- [ ] 17.5. Write CLI tests for export command

### 18. CLI: Health Command

_Leverage:_ Click CLI framework, health checker, colored output
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics health' command displaying overall health status with optional verbose mode showing detailed check results, using colored output to indicate status (green=healthy, yellow=degraded, red=unhealthy) | Restrictions: Use colored output for status indication; support --verbose flag for detailed results; exit with non-zero status code if unhealthy; handle health endpoint unavailability | Success: Health command displays status with appropriate colors, verbose mode shows check details, exit codes reflect health status, CLI tests verify output and exit codes

- [ ] 18.1. Implement `health` command
- [ ] 18.2. Display overall health status
- [ ] 18.3. Add `--verbose` flag for detailed check results
- [ ] 18.4. Display colored output based on status
- [ ] 18.5. Write CLI tests for health command

### 19. CLI: Config Command

_Leverage:_ Click CLI framework, configuration management
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics config' command group with 'show' subcommand to display current configuration and 'set' subcommand to update configuration values, persisting changes appropriately | Restrictions: Use Click command groups; validate configuration keys and values; persist configuration changes; display current values clearly | Success: Config show displays all current settings, config set updates values correctly, invalid keys/values are rejected, CLI tests verify configuration management

- [ ] 19.1. Implement `config` command group
- [ ] 19.2. Implement `config show` subcommand
- [ ] 19.3. Implement `config set <key> <value>` subcommand
- [ ] 19.4. Display current configuration values
- [ ] 19.5. Write CLI tests for config command

### 20. CLI: Test Command

_Leverage:_ Click CLI framework, HTTP requests, OTLP connectivity
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics test' command with flags to test connectivity to OTLP endpoint, metrics endpoint, and health endpoint, displaying clear success/failure results for each | Restrictions: Support --otlp, --metrics, --health flags; attempt actual connectivity tests; provide clear success/failure messages; include error details on failure | Success: Test command verifies connectivity to specified endpoints, displays clear results, handles connection failures gracefully, CLI tests verify connectivity checking

- [ ] 20.1. Implement `test` command
- [ ] 20.2. Add `--otlp` flag to test OTLP connectivity
- [ ] 20.3. Add `--metrics` flag to test metrics endpoint
- [ ] 20.4. Add `--health` flag to test health endpoint
- [ ] 20.5. Display connectivity results
- [ ] 20.6. Write CLI tests for test command

### 21. CLI: Dashboards Command

_Leverage:_ Click CLI framework, dashboard templates
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Implement 'cardlink-metrics dashboards' command group with 'export' subcommand that exports all Grafana dashboard JSON files to a specified directory, displaying summary of exported dashboards | Restrictions: Validate output directory existence/permissions; create directory if needed; display clear export summary with file paths; handle export errors gracefully | Success: Dashboards export command creates JSON files in specified directory, displays export summary, handles errors appropriately, CLI tests verify file creation

- [ ] 21.1. Implement `dashboards` command group
- [ ] 21.2. Implement `dashboards export <dir>` subcommand
- [ ] 21.3. Export all Grafana dashboard JSON files
- [ ] 21.4. Display export summary
- [ ] 21.5. Write CLI tests for dashboards command

### 22. CLI Entry Point

_Leverage:_ Python entry points, Click CLI framework
_Requirements:_ R14
_Prompt:_ Role: CLI developer | Task: Register 'cardlink-metrics' entry point in pyproject.toml, add version option to CLI group, implement global error handling for clean error messages, and create integration tests for complete CLI workflows | Restrictions: Use proper entry point configuration; display version from package metadata; provide user-friendly error messages; handle KeyboardInterrupt and other common exceptions | Success: CLI is installable and accessible via 'cardlink-metrics' command, version option displays correct version, errors are handled gracefully, integration tests verify end-to-end CLI functionality

- [ ] 22.1. Register `cardlink-metrics` entry point in pyproject.toml
- [ ] 22.2. Add version option to CLI group
- [ ] 22.3. Add global error handling
- [ ] 22.4. Write integration tests for complete CLI workflows

### 23. Integration with PSK-TLS Server

_Leverage:_ Existing PSK-TLS server code, metrics collector, tracing
_Requirements:_ R2, R3, R9
_Prompt:_ Role: Integration engineer | Task: Integrate observability into PSK-TLS server by adding metrics recording for TLS handshakes and APDU exchanges, tracing spans for session handling, and health check for server status verification | Restrictions: Minimize performance impact on TLS operations; handle observability failures gracefully without affecting server function; use existing spans and metrics methods; add health check without blocking server operations | Success: TLS handshakes and APDU exchanges are recorded in metrics, tracing spans capture session flows, health check verifies server status, integration tests confirm observability without performance degradation

- [ ] 23.1. Add metrics recording to TLS handshake
- [ ] 23.2. Add metrics recording to APDU exchanges
- [ ] 23.3. Add tracing spans to session handling
- [ ] 23.4. Add health check for server status
- [ ] 23.5. Write integration tests

### 24. Integration with Phone Controller

_Leverage:_ Existing phone controller code, ADB operations, metrics
_Requirements:_ R5, R9
_Prompt:_ Role: Integration engineer | Task: Integrate observability into phone controller by adding metrics recording for ADB operations and device connections, tracing spans for device operations, and health check for ADB availability verification | Restrictions: Handle ADB operation failures without affecting metrics; avoid overhead on time-critical operations; use appropriate metric labels for device identification; health check must not interfere with device operations | Success: ADB operations and device connections are metered, tracing captures device operation flows, health check verifies ADB availability, integration tests confirm proper instrumentation

- [ ] 24.1. Add metrics recording to ADB operations
- [ ] 24.2. Add device connection metrics
- [ ] 24.3. Add tracing spans to device operations
- [ ] 24.4. Add health check for ADB availability
- [ ] 24.5. Write integration tests

### 25. Integration with Modem Controller

_Leverage:_ Existing modem controller code, AT commands, metrics
_Requirements:_ R5, R9
_Prompt:_ Role: Integration engineer | Task: Integrate observability into modem controller by adding metrics recording for AT commands and modem connections, tracing spans for modem operations, and health check for serial port availability verification | Restrictions: Minimize latency impact on AT command execution; handle serial communication failures gracefully; use appropriate labels for modem identification; health check must complete quickly (<1s) | Success: AT commands and modem connections are recorded in metrics, tracing spans capture modem operation flows, health check verifies serial port availability, integration tests confirm instrumentation correctness

- [ ] 25.1. Add metrics recording to AT commands
- [ ] 25.2. Add device connection metrics for modems
- [ ] 25.3. Add tracing spans to modem operations
- [ ] 25.4. Add health check for serial port availability
- [ ] 25.5. Write integration tests

### 26. Integration with Database Layer

_Leverage:_ Existing database code, connection pool, query execution
_Requirements:_ R7, R9, R10
_Prompt:_ Role: Integration engineer | Task: Integrate observability into database layer by adding metrics for query execution and connection pool usage, tracing spans for database operations, and health check for database connectivity verification | Restrictions: Instrument without modifying query semantics; record metrics for all query types; include table/operation in labels; health check must verify actual connectivity; handle database errors in instrumentation | Success: Database queries and connection pool are metered, tracing spans capture database operations with proper attributes, health check verifies connectivity, integration tests confirm complete instrumentation

- [ ] 26.1. Add metrics recording to database queries
- [ ] 26.2. Add connection pool metrics
- [ ] 26.3. Add tracing spans to database operations
- [ ] 26.4. Add health check for database connectivity
- [ ] 26.5. Write integration tests

### 27. Integration with Test Runner

_Leverage:_ Existing test runner code, pytest framework
_Requirements:_ R6, R9
_Prompt:_ Role: Test infrastructure engineer | Task: Integrate observability into test runner by recording metrics for test execution and results, adding tracing spans to test cases for distributed debugging, and ensuring proper lifecycle management | Restrictions: Use pytest hooks for instrumentation; record metrics for all test outcomes (passed, failed, skipped, error); include suite and test names in labels; minimize test performance impact | Success: Test execution is recorded in metrics with proper status, tracing spans enable debugging individual test runs, integration tests verify correct metric recording and span creation

- [ ] 27.1. Add metrics recording to test execution
- [ ] 27.2. Add tracing spans to test cases
- [ ] 27.3. Record test results metrics
- [ ] 27.4. Write integration tests

### 28. System Metrics Collection

_Leverage:_ psutil library, Python threading, background tasks
_Requirements:_ R7
_Prompt:_ Role: System monitoring engineer | Task: Implement background thread that periodically collects system resource metrics (CPU usage, memory, open file descriptors, uptime) using psutil at configurable intervals without impacting application performance | Restrictions: Run collection in background thread; use configurable collection interval (default 15s); handle psutil errors gracefully; ensure thread cleanup on shutdown; keep collection overhead minimal | Success: System metrics are collected periodically and available via metrics endpoint, collection thread starts/stops cleanly, metrics accurately reflect system state, unit tests verify metric collection

- [ ] 28.1. Implement background thread for system metrics collection
- [ ] 28.2. Collect CPU usage at intervals
- [ ] 28.3. Collect memory usage at intervals
- [ ] 28.4. Collect open file descriptors
- [ ] 28.5. Calculate and record uptime
- [ ] 28.6. Write unit tests for system metrics

### 29. Documentation

_Leverage:_ Python docstrings, Markdown documentation
_Requirements:_ R1, R8, R10, R11, R12, R13, R14
_Prompt:_ Role: Technical writer | Task: Create comprehensive documentation including module docstrings for all classes, configuration guides for metrics endpoint and OTLP export, customization guides for health checks and alerting rules, Grafana dashboard import instructions, and CLI usage examples | Restrictions: Follow Google docstring style; include code examples; document all configuration options with defaults; provide step-by-step setup guides; include troubleshooting sections | Success: All modules have complete docstrings, configuration is fully documented with examples, guides enable users to set up observability stack, CLI usage is clearly explained

- [ ] 29.1. Write module docstrings for all classes
- [ ] 29.2. Document metrics endpoint configuration
- [ ] 29.3. Document OTLP export configuration
- [ ] 29.4. Document health check customization
- [ ] 29.5. Create Grafana dashboard import guide
- [ ] 29.6. Document alerting rules customization
- [ ] 29.7. Add CLI usage examples

### 30. Performance Testing

_Leverage:_ Python profiling tools, load testing, benchmarking
_Requirements:_ R1, R8, R9
_Prompt:_ Role: Performance engineer | Task: Conduct comprehensive performance testing of observability components including metrics collection overhead, tracing overhead, high-cardinality label handling, and metrics endpoint response time under load, documenting performance characteristics and acceptable limits | Restrictions: Test under realistic load conditions; measure CPU overhead (<1% requirement); test with varying label cardinality; benchmark endpoint latency (<100ms requirement); document all findings with recommendations | Success: Performance benchmarks completed for all components, overhead is within acceptable limits (<1% CPU for metrics, <100ms endpoint latency), high-cardinality handling documented, performance characteristics documented with recommendations

- [ ] 30.1. Benchmark metrics collection overhead
- [ ] 30.2. Benchmark tracing overhead
- [ ] 30.3. Test high-cardinality label handling
- [ ] 30.4. Test metrics endpoint response time under load
- [ ] 30.5. Document performance characteristics

## Task Dependencies

```
1 (Setup)
├── 2 (Config)
│   └── 3 (Manager)
├── 4 (Registry)
│   └── 5-6 (Collector + Server)
├── 7-8 (Tracing Provider + Span Manager)
├── 9-11 (Health Checker + Checks + Server)
├── 12-13 (Structured Logger + Component Logger)
├── 14 (Dashboard Templates)
└── 15 (Alerting Rules)

CLI Tasks (16-22) ← depend on corresponding components
Integration Tasks (23-27) ← depend on core implementation
28 (System Metrics) ← depends on 5
29 (Documentation) ← finalize after implementation
30 (Performance) ← after core implementation
```

## Estimated Effort

| Task Group | Tasks | Complexity |
|------------|-------|------------|
| Setup | 1.1-1.7 | Low |
| Config | 2.1-2.7 | Low |
| Manager | 3.1-3.10 | Medium |
| Registry | 4.1-4.10 | Low |
| Collector | 5.1-5.12 | Medium |
| Metrics Server | 6.1-6.8 | Medium |
| Tracing Provider | 7.1-7.13 | High |
| Span Manager | 8.1-8.9 | Medium |
| Health Checker | 9.1-9.11 | Medium |
| Pre-defined Checks | 10.1-10.6 | Low |
| Health Server | 11.1-11.8 | Medium |
| Structured Logger | 12.1-12.9 | Medium |
| Component Logger | 13.1-13.6 | Low |
| Dashboards | 14.1-14.8 | Medium |
| Alerting Rules | 15.1-15.6 | Low |
| CLI Commands | 16-22 | Medium |
| Integrations | 23-27 | Medium |
| System Metrics | 28.1-28.6 | Low |
| Documentation | 29.1-29.7 | Low |
| Performance | 30.1-30.5 | Medium |

## Notes

- OpenTelemetry tracing is optional but recommended for debugging complex issues
- Metrics collection should have minimal performance impact (<1% CPU overhead)
- Health checks should complete within 5 seconds to avoid timeout issues
- Dashboard templates are Grafana-compatible JSON exports
- Alerting rules are Prometheus-compatible YAML format
- Structured logging with trace correlation enables log-trace correlation in observability platforms
- Label cardinality should be controlled to prevent memory issues (avoid high-cardinality device_id labels in production)
