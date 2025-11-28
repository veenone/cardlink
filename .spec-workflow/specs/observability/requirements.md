# Requirements Document: Observability

## Introduction

The Observability component provides comprehensive monitoring, metrics, and tracing capabilities for CardLink. It exposes Prometheus-format metrics, supports OpenTelemetry for distributed tracing, and enables integration with external monitoring systems like Grafana, Prometheus, and Grafana Alloy.

This component enables operators to monitor CardLink health, track performance, analyze trends, and set up alerting for anomalies in SCP81 OTA testing workflows.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Protocol transparency**: Detailed metrics on APDU commands, TLS handshakes, and sessions
- **Performance monitoring**: Track latencies, throughput, and error rates
- **Operational visibility**: Real-time health status and resource usage
- **Integration ready**: Standard formats (Prometheus, OpenTelemetry) for existing tooling
- **Debugging support**: Trace individual requests through the system

## Requirements

### Requirement 1: Metrics Endpoint

**User Story:** As an operator, I want CardLink to expose a Prometheus-compatible metrics endpoint, so that I can scrape metrics into my monitoring system.

#### Acceptance Criteria

1. WHEN the server starts THEN it SHALL expose a `/metrics` endpoint on configurable port (default 9090)
2. WHEN scraped THEN the endpoint SHALL return metrics in Prometheus text format
3. WHEN configured THEN the endpoint SHALL support HTTP Basic authentication
4. WHEN queried THEN the endpoint SHALL respond within 100ms
5. WHEN multiple scrapers query THEN the endpoint SHALL handle concurrent requests
6. WHEN metrics are disabled THEN the endpoint SHALL return 503 Service Unavailable

### Requirement 2: APDU Command Metrics

**User Story:** As a developer, I want metrics on APDU command execution, so that I can analyze command patterns and identify issues.

#### Acceptance Criteria

1. WHEN an APDU command is sent THEN the system SHALL increment `cardlink_apdu_commands_total` counter
2. WHEN labeling commands THEN metrics SHALL include:
   - `command_type` (SELECT, GET_STATUS, INSTALL, DELETE, etc.)
   - `device_type` (phone, modem)
   - `device_id` (optional, configurable)
3. WHEN an APDU response is received THEN the system SHALL increment `cardlink_apdu_responses_total` counter
4. WHEN labeling responses THEN metrics SHALL include:
   - `status_word` (9000, 6A82, etc.)
   - `status_category` (success, warning, error)
5. WHEN measuring latency THEN the system SHALL record `cardlink_apdu_duration_seconds` histogram
6. WHEN tracking data THEN the system SHALL record `cardlink_apdu_bytes_total` counter for sent/received

### Requirement 3: TLS Session Metrics

**User Story:** As an operator, I want metrics on TLS handshakes and sessions, so that I can monitor connection health.

#### Acceptance Criteria

1. WHEN a TLS handshake completes THEN the system SHALL increment `cardlink_tls_handshakes_total` counter
2. WHEN labeling handshakes THEN metrics SHALL include:
   - `result` (success, failed)
   - `cipher_suite`
   - `failure_reason` (if failed)
3. WHEN measuring handshake time THEN the system SHALL record `cardlink_tls_handshake_duration_seconds` histogram
4. WHEN tracking active connections THEN the system SHALL update `cardlink_tls_connections_active` gauge
5. WHEN a connection closes THEN the system SHALL record connection duration

### Requirement 4: OTA Session Metrics

**User Story:** As a tester, I want metrics on OTA sessions, so that I can track success rates and performance over time.

#### Acceptance Criteria

1. WHEN a session starts THEN the system SHALL update `cardlink_sessions_active` gauge
2. WHEN a session completes THEN the system SHALL increment `cardlink_sessions_total` counter
3. WHEN labeling sessions THEN metrics SHALL include:
   - `status` (completed, failed, timeout)
   - `session_type` (triggered, polled)
   - `device_type` (phone, modem)
4. WHEN measuring duration THEN the system SHALL record `cardlink_session_duration_seconds` histogram
5. WHEN tracking triggers THEN the system SHALL increment `cardlink_triggers_sent_total` counter
6. WHEN a trigger fails THEN the system SHALL increment `cardlink_trigger_failures_total` counter

### Requirement 5: Device Connection Metrics

**User Story:** As an operator, I want metrics on device connections, so that I can monitor device health and availability.

#### Acceptance Criteria

1. WHEN devices connect/disconnect THEN the system SHALL update `cardlink_devices_connected` gauge
2. WHEN labeling devices THEN metrics SHALL include:
   - `device_type` (phone, modem)
   - `device_id`
3. WHEN a device error occurs THEN the system SHALL increment `cardlink_device_errors_total` counter
4. WHEN measuring AT command latency THEN the system SHALL record `cardlink_at_command_duration_seconds` histogram
5. WHEN tracking ADB operations THEN the system SHALL record `cardlink_adb_operation_duration_seconds` histogram

### Requirement 6: Test Execution Metrics

**User Story:** As a QA engineer, I want metrics on test execution, so that I can track test health and identify flaky tests.

#### Acceptance Criteria

1. WHEN a test runs THEN the system SHALL increment `cardlink_tests_total` counter
2. WHEN labeling tests THEN metrics SHALL include:
   - `suite_name`
   - `status` (passed, failed, skipped, error)
3. WHEN measuring duration THEN the system SHALL record `cardlink_test_duration_seconds` histogram
4. WHEN a test suite completes THEN the system SHALL record `cardlink_test_suite_duration_seconds`
5. WHEN tracking assertions THEN the system SHALL increment `cardlink_test_assertions_total` counter

### Requirement 7: System Resource Metrics

**User Story:** As an operator, I want system resource metrics, so that I can monitor CardLink resource usage.

#### Acceptance Criteria

1. WHEN collecting metrics THEN the system SHALL report `cardlink_process_cpu_seconds_total`
2. WHEN collecting metrics THEN the system SHALL report `cardlink_process_memory_bytes`
3. WHEN collecting metrics THEN the system SHALL report `cardlink_process_open_fds`
4. WHEN collecting metrics THEN the system SHALL report `cardlink_uptime_seconds`
5. WHEN using database THEN the system SHALL report `cardlink_db_connections_active` gauge
6. WHEN using database THEN the system SHALL report `cardlink_db_query_duration_seconds` histogram

### Requirement 8: OpenTelemetry Integration

**User Story:** As a DevOps engineer, I want CardLink to support OpenTelemetry, so that I can integrate with modern observability platforms.

#### Acceptance Criteria

1. WHEN OTLP is enabled THEN the system SHALL export metrics via OTLP protocol
2. WHEN configured THEN the system SHALL support gRPC and HTTP OTLP endpoints
3. WHEN exporting THEN the system SHALL include resource attributes (service.name, service.version)
4. WHEN tracing is enabled THEN the system SHALL create spans for operations
5. WHEN tracing THEN spans SHALL include:
   - APDU command/response spans
   - TLS handshake spans
   - Session spans
   - Test execution spans
6. WHEN tracing THEN the system SHALL propagate trace context across components

### Requirement 9: Distributed Tracing

**User Story:** As a developer, I want distributed tracing for debugging, so that I can trace requests through the entire system.

#### Acceptance Criteria

1. WHEN a request enters the system THEN a trace SHALL be created
2. WHEN processing continues THEN child spans SHALL be created for:
   - TLS handshake
   - Each APDU exchange
   - Database operations
   - Device communications
3. WHEN spans complete THEN they SHALL include:
   - Duration
   - Status (OK, ERROR)
   - Relevant attributes (command type, status word, etc.)
4. WHEN errors occur THEN spans SHALL record error details
5. WHEN exporting traces THEN the system SHALL support Jaeger and Zipkin formats

### Requirement 10: Health Check Endpoints

**User Story:** As an operator, I want health check endpoints, so that I can monitor CardLink availability in orchestration systems.

#### Acceptance Criteria

1. WHEN querying `/health` THEN the system SHALL return overall health status
2. WHEN healthy THEN the response SHALL be HTTP 200 with `{"status": "healthy"}`
3. WHEN unhealthy THEN the response SHALL be HTTP 503 with details
4. WHEN querying `/health/live` THEN the system SHALL return liveness status
5. WHEN querying `/health/ready` THEN the system SHALL return readiness status
6. WHEN checking readiness THEN the system SHALL verify:
   - Database connectivity
   - Metrics endpoint availability
   - Essential services running
7. WHEN health checks are performed THEN they SHALL complete within 5 seconds

### Requirement 11: Logging Integration

**User Story:** As a developer, I want structured logging integrated with tracing, so that I can correlate logs with traces.

#### Acceptance Criteria

1. WHEN logging THEN the system SHALL use structured JSON format
2. WHEN a trace is active THEN logs SHALL include trace_id and span_id
3. WHEN logging THEN entries SHALL include:
   - timestamp (ISO 8601)
   - level (DEBUG, INFO, WARNING, ERROR)
   - message
   - component
   - context fields
4. WHEN configuring THEN the system SHALL support log level configuration per component
5. WHEN exporting THEN the system SHALL support log shipping to external systems (optional)

### Requirement 12: Grafana Dashboard Templates

**User Story:** As an operator, I want pre-built Grafana dashboards, so that I can quickly visualize CardLink metrics.

#### Acceptance Criteria

1. WHEN deploying THEN the system SHALL provide dashboard JSON templates
2. WHEN viewing OTA Overview dashboard THEN it SHALL show:
   - Active sessions gauge
   - Session success rate
   - Session duration histogram
   - Trigger success rate
3. WHEN viewing APDU Analysis dashboard THEN it SHALL show:
   - Command distribution pie chart
   - Response status breakdown
   - Latency percentiles (p50, p95, p99)
   - Error rate over time
4. WHEN viewing Device Status dashboard THEN it SHALL show:
   - Connected devices count
   - Device error rates
   - AT/ADB command latencies
5. WHEN viewing Test Results dashboard THEN it SHALL show:
   - Test pass/fail rates
   - Test duration trends
   - Flaky test identification

### Requirement 13: Alerting Rules

**User Story:** As an operator, I want pre-defined alerting rules, so that I can be notified of issues.

#### Acceptance Criteria

1. WHEN deploying THEN the system SHALL provide Prometheus alerting rule templates
2. WHEN defining alerts THEN rules SHALL include:
   - High error rate (>5% APDU errors)
   - Session timeout spike
   - TLS handshake failures
   - Device disconnection
   - Database connection failures
3. WHEN alerts fire THEN they SHALL include:
   - Severity (warning, critical)
   - Description
   - Runbook link (optional)
4. WHEN configuring THEN thresholds SHALL be customizable

### Requirement 14: CLI Integration

**User Story:** As a developer, I want to view metrics from the command line, so that I can quickly check system status.

#### Acceptance Criteria

1. WHEN running `cardlink-metrics status` THEN the CLI SHALL show current metrics summary
2. WHEN running `cardlink-metrics export` THEN the CLI SHALL dump all metrics
3. WHEN running `cardlink-metrics health` THEN the CLI SHALL show health check results
4. WHEN running `cardlink-metrics config` THEN the CLI SHALL show/update metrics configuration
5. WHEN running `cardlink-metrics test` THEN the CLI SHALL verify OTLP connectivity

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: Separate classes for metrics collection, export, and health checks
- **Modular Design**: Observability usable with or without external collectors
- **Pluggable Exporters**: Support multiple export formats (Prometheus, OTLP)
- **Minimal Overhead**: Metrics collection should not impact application performance

### Performance

- **Metrics overhead**: < 1% CPU overhead for metrics collection
- **Endpoint latency**: `/metrics` response within 100ms
- **Memory usage**: Metrics storage < 50MB
- **Cardinality control**: Limit high-cardinality labels to prevent memory issues

### Compatibility

- **Prometheus**: 2.0+ text format
- **OpenTelemetry**: OTLP 1.0+ protocol
- **Grafana**: 9.0+ dashboard format
- **Grafana Alloy**: Latest version for collection
- **Python**: prometheus-client, opentelemetry-api/sdk

### Reliability

- **Graceful degradation**: Application continues if metrics export fails
- **Buffer overflow**: Drop oldest metrics if buffer full
- **Reconnection**: Auto-reconnect to OTLP collectors on failure
- **Health isolation**: Health check failures don't affect main application

### Security

- **Authentication**: Optional HTTP Basic auth for metrics endpoint
- **TLS support**: Optional HTTPS for metrics endpoint
- **Sensitive data**: Never include sensitive data (keys, credentials) in metrics/traces
- **Label sanitization**: Sanitize user-provided values in labels
