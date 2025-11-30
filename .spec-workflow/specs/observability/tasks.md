# Tasks Document: Observability

## Task Overview

This document breaks down the Observability component implementation into actionable development tasks. The observability module provides Prometheus metrics, OpenTelemetry tracing, health checks, and structured logging for the CardLink platform.

## Tasks

### 1. Project Setup and Dependencies

- [x] 1.1. Create `cardlink/observability/` package structure with `__init__.py`
  - File: src/cardlink/observability/__init__.py
  - Create directory structure for observability module with metrics/, tracing/, health/, logging/ subdirectories
  - Purpose: Establish module foundation for observability components
  - _Leverage: src/cardlink/ package structure_
  - _Requirements: R1, R2, R3, R4, R5, R6, R7, R8, R9_
  - _Prompt: Role: Python Developer | Task: Create the observability module structure with proper __init__.py exports and subdirectories for metrics, tracing, health, and logging | Restrictions: Follow existing package patterns, maintain clean imports | Success: Module imports correctly, all subdirectories exist_

- [x] 1.2. Add prometheus-client dependency to pyproject.toml (>=0.17.0)
  - File: pyproject.toml
  - Add prometheus-client>=0.17.0 to observability optional dependencies
  - Purpose: Enable Prometheus metrics collection and exposition
  - _Leverage: pyproject.toml optional-dependencies pattern_
  - _Requirements: R1_
  - _Prompt: Role: Python Developer | Task: Add prometheus-client dependency to pyproject.toml observability extras | Restrictions: Use version >=0.17.0, add to observability optional group | Success: Dependency installs without conflicts_

- [x] 1.3. Add opentelemetry-api and opentelemetry-sdk dependencies (>=1.20.0)
  - File: pyproject.toml
  - Add opentelemetry-api>=1.20.0 and opentelemetry-sdk>=1.20.0 to observability dependencies
  - Purpose: Enable distributed tracing with OpenTelemetry
  - _Leverage: pyproject.toml optional-dependencies pattern_
  - _Requirements: R8, R9_
  - _Prompt: Role: Python Developer | Task: Add OpenTelemetry API and SDK dependencies | Restrictions: Use version >=1.20.0 | Success: Dependencies install without conflicts_

- [x] 1.4. Add opentelemetry-exporter-otlp dependency
  - File: pyproject.toml
  - Add opentelemetry-exporter-otlp>=1.20.0 for OTLP export support
  - Purpose: Enable trace export to OTLP-compatible collectors
  - _Leverage: pyproject.toml optional-dependencies pattern_
  - _Requirements: R8_
  - _Prompt: Role: Python Developer | Task: Add OTLP exporter dependency | Restrictions: Version compatible with SDK | Success: OTLP export works_

- [x] 1.5. Add psutil dependency for system metrics
  - File: pyproject.toml
  - Add psutil>=5.9.0 for system resource monitoring
  - Purpose: Enable CPU, memory, and disk usage metrics collection
  - _Leverage: pyproject.toml optional-dependencies pattern_
  - _Requirements: R7_
  - _Prompt: Role: Python Developer | Task: Add psutil dependency for system metrics | Restrictions: Use version >=5.9.0 | Success: System metrics collection works_

- [x] 1.6. Add optional jaeger and zipkin exporter dependencies
  - File: pyproject.toml
  - Add optional opentelemetry-exporter-jaeger and opentelemetry-exporter-zipkin
  - Purpose: Enable alternative trace export destinations
  - _Leverage: pyproject.toml optional-dependencies pattern_
  - _Requirements: R8_
  - _Prompt: Role: Python Developer | Task: Add optional Jaeger and Zipkin exporters | Restrictions: Make these optional extras | Success: Exporters install when requested_

- [x] 1.7. Create pytest fixtures for metrics and tracing testing
  - File: tests/observability/conftest.py
  - Create fixtures for isolated metrics registry, mock tracers, and test configurations
  - Purpose: Enable reliable unit testing of observability components
  - _Leverage: pytest fixture patterns, tests/conftest.py_
  - _Requirements: R1, R8_
  - _Prompt: Role: QA Engineer | Task: Create pytest fixtures for metrics and tracing testing with isolated registries | Restrictions: Ensure test isolation, no global state pollution | Success: Tests run reliably in parallel_

### 2. Observability Configuration

- [x] 2.1. Create `config.py` with ObservabilityConfig dataclass
  - File: src/cardlink/observability/config.py
  - Create main ObservabilityConfig dataclass aggregating all sub-configurations
  - Purpose: Provide unified configuration for all observability components
  - _Leverage: Python dataclasses, existing config patterns_
  - _Requirements: R1, R3, R8, R10, R11_
  - _Prompt: Role: Configuration Engineer | Task: Create ObservabilityConfig dataclass with metrics, tracing, health, and logging sub-configs | Restrictions: Use dataclasses, support from_env() class method | Success: Config instantiates from environment variables_

- [x] 2.2. Add MetricsConfig (enabled, port, path, auth)
  - File: src/cardlink/observability/config.py
  - Create MetricsConfig dataclass with enabled, port, path, auth_username, auth_password, collection_interval
  - Purpose: Configure Prometheus metrics endpoint behavior
  - _Leverage: Python dataclasses_
  - _Requirements: R1_
  - _Prompt: Role: Configuration Engineer | Task: Create MetricsConfig with port (default 9090), path (default /metrics), optional auth | Restrictions: Include from_env() method, validate port range | Success: Metrics endpoint configurable via environment_

- [x] 2.3. Add TracingConfig (enabled, otlp_endpoint, protocol)
  - File: src/cardlink/observability/config.py
  - Create TracingConfig with enabled, otlp_endpoint, otlp_protocol, service_name, service_version, sample_rate
  - Purpose: Configure OpenTelemetry tracing behavior
  - _Leverage: Python dataclasses_
  - _Requirements: R8_
  - _Prompt: Role: Configuration Engineer | Task: Create TracingConfig with OTLP endpoint, protocol (grpc/http), sampling | Restrictions: Require endpoint when enabled, validate sample_rate 0-1 | Success: Tracing configurable via environment_

- [x] 2.4. Add HealthConfig (port, enabled)
  - File: src/cardlink/observability/config.py
  - Create HealthConfig with enabled, port, check_timeout
  - Purpose: Configure health check endpoint behavior
  - _Leverage: Python dataclasses_
  - _Requirements: R10_
  - _Prompt: Role: Configuration Engineer | Task: Create HealthConfig with port (default 8080), timeout | Restrictions: Validate port range, timeout positive | Success: Health endpoint configurable_

- [x] 2.5. Add LoggingConfig (level, format, trace_correlation)
  - File: src/cardlink/observability/config.py
  - Create LoggingConfig with level, format (json/text), trace_correlation, output_file
  - Purpose: Configure structured logging behavior
  - _Leverage: Python dataclasses_
  - _Requirements: R11_
  - _Prompt: Role: Configuration Engineer | Task: Create LoggingConfig with level, format, trace correlation | Restrictions: Validate level values, format options | Success: Logging configurable via environment_

- [x] 2.6. Implement environment variable parsing (GP_* prefix)
  - File: src/cardlink/observability/config.py
  - Add from_env() class methods to all config classes reading GP_* environment variables
  - Purpose: Enable configuration via environment variables for containerized deployments
  - _Leverage: os.getenv(), existing env parsing patterns_
  - _Requirements: R1, R8, R10, R11_
  - _Prompt: Role: Configuration Engineer | Task: Implement from_env() methods reading GP_METRICS_*, GP_TRACING_*, GP_HEALTH_*, GP_LOG_* | Restrictions: Provide sensible defaults, handle type conversion | Success: All config reads from environment_

- [x] 2.7. Write unit tests for configuration
  - File: tests/observability/test_config.py
  - Test configuration parsing, validation, defaults, and environment variable loading
  - Purpose: Ensure configuration reliability
  - _Leverage: pytest, tests/observability/conftest.py_
  - _Requirements: R1_
  - _Prompt: Role: QA Engineer | Task: Write tests for config validation, env parsing, defaults | Restrictions: Test edge cases, invalid values | Success: Full config coverage_

### 3. Observability Manager Implementation

- [x] 3.1. Create `manager.py` with ObservabilityManager class
  - File: src/cardlink/observability/manager.py
  - Create ObservabilityManager class as central coordinator for all observability components
  - Purpose: Provide unified lifecycle management for metrics, tracing, health, logging
  - _Leverage: Singleton pattern, Python threading_
  - _Requirements: R1, R8, R10, R11_
  - _Prompt: Role: Software Architect | Task: Create ObservabilityManager singleton coordinating all observability components | Restrictions: Thread-safe singleton, clean shutdown | Success: Manager coordinates all components_

- [x] 3.2. Implement singleton pattern with thread-safe initialization
  - File: src/cardlink/observability/manager.py
  - Use threading.Lock for thread-safe singleton access
  - Purpose: Ensure single global observability instance
  - _Leverage: threading.Lock, module-level instance_
  - _Requirements: R1_
  - _Prompt: Role: Software Architect | Task: Implement thread-safe singleton with double-checked locking | Restrictions: Must be thread-safe | Success: Concurrent access returns same instance_

- [x] 3.3. Implement `initialize()` to start all components
  - File: src/cardlink/observability/manager.py
  - Initialize metrics, tracing, health, and logging based on configuration
  - Purpose: Start all enabled observability components
  - _Leverage: ObservabilityConfig, component classes_
  - _Requirements: R1, R8, R10, R11_
  - _Prompt: Role: Software Architect | Task: Implement initialize() starting components based on config.enabled flags | Restrictions: Handle initialization failures gracefully | Success: All enabled components start_

- [x] 3.4. Implement `shutdown()` to stop all components
  - File: src/cardlink/observability/manager.py
  - Gracefully shutdown all active components, flush buffers
  - Purpose: Clean resource cleanup on application exit
  - _Leverage: Component shutdown methods_
  - _Requirements: R1_
  - _Prompt: Role: Software Architect | Task: Implement shutdown() stopping all components cleanly | Restrictions: Handle shutdown errors, log failures | Success: Clean shutdown without resource leaks_

- [x] 3.5. Add `metrics` property for MetricsCollector access
  - File: src/cardlink/observability/manager.py
  - Property returning MetricsCollector instance, raising if not initialized
  - Purpose: Provide type-safe access to metrics functionality
  - _Leverage: Python property decorator_
  - _Requirements: R1_
  - _Prompt: Role: Software Architect | Task: Add metrics property returning collector or raising RuntimeError | Restrictions: Check initialization state | Success: Property returns collector when initialized_

- [x] 3.6. Add `tracer` property for TracingProvider access
  - File: src/cardlink/observability/manager.py
  - Property returning TracingProvider instance
  - Purpose: Provide type-safe access to tracing functionality
  - _Leverage: Python property decorator_
  - _Requirements: R8_
  - _Prompt: Role: Software Architect | Task: Add tracer property returning provider or raising RuntimeError | Restrictions: Check initialization and enabled state | Success: Property returns provider when enabled_

- [x] 3.7. Add `health` property for HealthChecker access
  - File: src/cardlink/observability/manager.py
  - Property returning HealthChecker instance
  - Purpose: Provide type-safe access to health check functionality
  - _Leverage: Python property decorator_
  - _Requirements: R10_
  - _Prompt: Role: Software Architect | Task: Add health property returning checker or raising RuntimeError | Restrictions: Check initialization and enabled state | Success: Property returns checker when enabled_

- [x] 3.8. Add `logger` property for StructuredLogger access
  - File: src/cardlink/observability/manager.py
  - Property returning StructuredLogger/LoggerManager instance
  - Purpose: Provide type-safe access to structured logging
  - _Leverage: Python property decorator_
  - _Requirements: R11_
  - _Prompt: Role: Software Architect | Task: Add logger property returning manager | Restrictions: Check initialization | Success: Property returns logger manager_

- [x] 3.9. Implement `get_observability()` global accessor function
  - File: src/cardlink/observability/manager.py
  - Module-level function returning singleton ObservabilityManager
  - Purpose: Provide convenient global access to observability
  - _Leverage: Module-level singleton pattern_
  - _Requirements: R1_
  - _Prompt: Role: Software Architect | Task: Create get_observability() returning singleton instance | Restrictions: Thread-safe, lazy initialization | Success: Function returns singleton_

- [x] 3.10. Write unit tests for ObservabilityManager
  - File: tests/observability/test_manager.py
  - Test singleton behavior, initialization, shutdown, property access
  - Purpose: Ensure manager reliability
  - _Leverage: pytest, conftest.py fixtures_
  - _Requirements: R1_
  - _Prompt: Role: QA Engineer | Task: Write tests for singleton, init/shutdown, properties | Restrictions: Test thread safety, error cases | Success: Full manager coverage_

### 4. Metrics Registry Implementation

- [x] 4.1. Create `metrics/registry.py` with MetricsRegistry class
  - File: src/cardlink/observability/metrics/registry.py
  - Create MetricsRegistry class defining all Prometheus metrics
  - Purpose: Centralize metric definitions for consistency
  - _Leverage: prometheus_client Counter, Gauge, Histogram, Info_
  - _Requirements: R1, R2, R3, R4, R5, R6, R7_
  - _Prompt: Role: Metrics Engineer | Task: Create MetricsRegistry with all CardLink metrics using prometheus_client | Restrictions: Follow Prometheus naming conventions (cardlink_ prefix) | Success: All metrics defined with proper types_

- [x] 4.2. Define APDU metrics (commands_total, responses_total, duration, bytes)
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_apdu_commands_total, cardlink_apdu_responses_total, cardlink_apdu_response_time_seconds, cardlink_apdu_data_bytes
  - Purpose: Track APDU command/response patterns and performance
  - _Leverage: Counter, Histogram_
  - _Requirements: R2_
  - _Prompt: Role: Metrics Engineer | Task: Define APDU metrics with command, interface, status_word labels | Restrictions: Use appropriate bucket sizes for duration | Success: APDU operations fully instrumented_

- [x] 4.3. Define session metrics (active, total, duration)
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_active_sessions, cardlink_sessions_total, cardlink_session_duration_seconds
  - Purpose: Track session lifecycle and duration
  - _Leverage: Gauge, Counter, Histogram_
  - _Requirements: R3, R4_
  - _Prompt: Role: Metrics Engineer | Task: Define session metrics with session_type, protocol, status labels | Restrictions: Use Gauge for active count | Success: Session lifecycle tracked_

- [x] 4.4. Define BIP/connection metrics (active, bytes, duration)
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_bip_connections_active, cardlink_bip_bytes_transferred_total, cardlink_bip_connection_duration_seconds
  - Purpose: Track Bearer Independent Protocol connections
  - _Leverage: Gauge, Counter, Histogram_
  - _Requirements: R3_
  - _Prompt: Role: Metrics Engineer | Task: Define BIP metrics with bearer_type, direction labels | Restrictions: Track both sent/received bytes | Success: BIP connections fully tracked_

- [x] 4.5. Define system metrics (cpu, memory, uptime, threads)
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_system_cpu_usage_percent, cardlink_system_memory_usage_bytes, cardlink_system_process_uptime_seconds, cardlink_system_threads_active
  - Purpose: Track system resource utilization
  - _Leverage: Gauge_
  - _Requirements: R7_
  - _Prompt: Role: Metrics Engineer | Task: Define system resource metrics | Restrictions: Use appropriate units (bytes, percent, seconds) | Success: System resources monitored_

- [x] 4.6. Define database metrics (connections, query_duration, operations)
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_database_connections_active, cardlink_database_query_duration_seconds, cardlink_database_operations_total
  - Purpose: Track database performance and connection pool
  - _Leverage: Gauge, Histogram, Counter_
  - _Requirements: R7_
  - _Prompt: Role: Metrics Engineer | Task: Define database metrics with operation, table labels | Restrictions: Include error counts | Success: Database operations tracked_

- [x] 4.7. Define application info metric
  - File: src/cardlink/observability/metrics/registry.py
  - Create cardlink_application_info with version, description labels
  - Purpose: Expose build and version information
  - _Leverage: Info_
  - _Requirements: R1_
  - _Prompt: Role: Metrics Engineer | Task: Define application info metric | Restrictions: Include name, description | Success: App info exposed in metrics_

- [x] 4.8. Write unit tests for registry definitions
  - File: tests/observability/test_registry.py
  - Test metric creation, labels, and types
  - Purpose: Verify metric definitions are correct
  - _Leverage: pytest, isolated registry fixture_
  - _Requirements: R1_
  - _Prompt: Role: QA Engineer | Task: Write tests verifying all metrics exist with correct types | Restrictions: Use isolated registry | Success: All metrics verified_

### 5. Metrics Collector Implementation

- [x] 5.1. Create `metrics/collector.py` with MetricsCollector class
  - File: src/cardlink/observability/metrics/collector.py
  - Create MetricsCollector providing high-level recording methods
  - Purpose: Simplify metrics recording throughout application
  - _Leverage: MetricsRegistry, MetricsConfig_
  - _Requirements: R1, R2, R3, R4, R5, R6, R7_
  - _Prompt: Role: Metrics Engineer | Task: Create MetricsCollector with convenient recording methods | Restrictions: Thread-safe updates, handle errors gracefully | Success: Recording methods work correctly_

- [x] 5.2. Implement APDU recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_apdu_command(), record_apdu_response(), record_apdu_error(), time_apdu_command() context manager
  - Purpose: Provide convenient APDU metrics recording
  - _Leverage: MetricsRegistry, contextmanager_
  - _Requirements: R2_
  - _Prompt: Role: Metrics Engineer | Task: Implement APDU recording with timing context manager | Restrictions: Include data length tracking | Success: APDU operations easily instrumented_

- [x] 5.3. Implement session recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_session_start(), record_session_end(), record_session_error()
  - Purpose: Track session lifecycle
  - _Leverage: MetricsRegistry_
  - _Requirements: R3, R4_
  - _Prompt: Role: Metrics Engineer | Task: Implement session recording methods | Restrictions: Track active count, duration, errors | Success: Session lifecycle instrumented_

- [x] 5.4. Implement BIP connection recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_bip_connection_open(), record_bip_connection_close(), record_bip_data_transfer(), record_bip_error()
  - Purpose: Track BIP connection lifecycle and data transfer
  - _Leverage: MetricsRegistry_
  - _Requirements: R3_
  - _Prompt: Role: Metrics Engineer | Task: Implement BIP recording methods | Restrictions: Track both directions | Success: BIP connections instrumented_

- [x] 5.5. Implement database recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_database_connection_change(), time_database_query() context manager, record_database_error()
  - Purpose: Track database operations and performance
  - _Leverage: MetricsRegistry, contextmanager_
  - _Requirements: R7_
  - _Prompt: Role: Metrics Engineer | Task: Implement database recording with query timing | Restrictions: Include operation/table labels | Success: Database operations instrumented_

- [x] 5.6. Implement system metrics collection
  - File: src/cardlink/observability/metrics/collector.py
  - Create _collect_system_metrics() using psutil, background collection thread
  - Purpose: Periodically collect CPU, memory, uptime metrics
  - _Leverage: psutil, threading_
  - _Requirements: R7_
  - _Prompt: Role: Metrics Engineer | Task: Implement background system metrics collection | Restrictions: Configurable interval, graceful shutdown | Success: System metrics collected periodically_

- [ ] 5.7. Implement TLS handshake recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_tls_handshake(), set_tls_connections(), inc/dec_tls_connections()
  - Purpose: Track PSK-TLS handshake metrics
  - _Leverage: MetricsRegistry_
  - _Requirements: R3_
  - _Prompt: Role: Metrics Engineer | Task: Implement TLS handshake recording | Restrictions: Include cipher_suite, result labels | Success: TLS operations instrumented_

- [ ] 5.8. Implement device recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create set_devices_connected(), record_device_error(), record_at_command_duration(), record_adb_operation_duration()
  - Purpose: Track device connections and operations
  - _Leverage: MetricsRegistry_
  - _Requirements: R5_
  - _Prompt: Role: Metrics Engineer | Task: Implement device recording methods | Restrictions: Include device_type labels | Success: Device operations instrumented_

- [ ] 5.9. Implement test recording methods
  - File: src/cardlink/observability/metrics/collector.py
  - Create record_test_result() with suite_name, status, duration
  - Purpose: Track test execution metrics
  - _Leverage: MetricsRegistry_
  - _Requirements: R6_
  - _Prompt: Role: Metrics Engineer | Task: Implement test result recording | Restrictions: Include all outcomes (pass/fail/skip/error) | Success: Test execution instrumented_

- [ ] 5.10. Write unit tests for MetricsCollector
  - File: tests/observability/test_collector.py
  - Test all recording methods, system metrics collection, timing context managers
  - Purpose: Verify collector functionality
  - _Leverage: pytest, isolated registry fixture_
  - _Requirements: R1_
  - _Prompt: Role: QA Engineer | Task: Write comprehensive collector tests | Restrictions: Test thread safety, error handling | Success: Full collector coverage_

### 6. Metrics HTTP Server Implementation

- [x] 6.1. Create `metrics/server.py` with MetricsServer class
  - File: src/cardlink/observability/metrics/server.py
  - Create MetricsServer with start(), shutdown() methods
  - Purpose: Expose Prometheus metrics via HTTP
  - _Leverage: http.server, prometheus_client_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Create HTTP server for /metrics endpoint | Restrictions: Background thread, graceful shutdown | Success: Server starts/stops cleanly_

- [x] 6.2. Create MetricsHTTPHandler request handler
  - File: src/cardlink/observability/metrics/server.py
  - Create HTTP handler responding to GET /metrics
  - Purpose: Handle metrics endpoint requests
  - _Leverage: http.server.BaseHTTPRequestHandler_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Create request handler for metrics endpoint | Restrictions: Support configurable path | Success: Handler responds to requests_

- [x] 6.3. Implement `/metrics` endpoint with Prometheus format
  - File: src/cardlink/observability/metrics/server.py
  - Return metrics in Prometheus text format using generate_latest()
  - Purpose: Serve metrics for Prometheus scraping
  - _Leverage: prometheus_client.generate_latest(), CONTENT_TYPE_LATEST_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Implement /metrics returning Prometheus format | Restrictions: <100ms response time | Success: Prometheus can scrape endpoint_

- [x] 6.4. Add optional HTTP Basic authentication
  - File: src/cardlink/observability/metrics/server.py
  - Implement Basic auth check when auth_username/password configured
  - Purpose: Secure metrics endpoint
  - _Leverage: base64, HTTP 401 response_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Add Basic auth support | Restrictions: Only when configured, return 401 on failure | Success: Auth works when configured_

- [x] 6.5. Implement graceful `shutdown()` method
  - File: src/cardlink/observability/metrics/server.py
  - Stop HTTP server cleanly, join thread
  - Purpose: Clean resource cleanup
  - _Leverage: HTTPServer.shutdown()_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Implement clean shutdown | Restrictions: Timeout on thread join | Success: Server stops without hanging_

- [x] 6.6. Add request logging suppression
  - File: src/cardlink/observability/metrics/server.py
  - Override log_message() to use Python logging instead of stdout
  - Purpose: Prevent log spam from health check requests
  - _Leverage: logging module_
  - _Requirements: R1_
  - _Prompt: Role: Backend Engineer | Task: Suppress default request logging | Restrictions: Use debug level | Success: No stdout spam from requests_

- [ ] 6.7. Write integration tests for metrics endpoint
  - File: tests/observability/test_metrics_server.py
  - Test endpoint responses, authentication, concurrent requests
  - Purpose: Verify server functionality
  - _Leverage: pytest, requests library_
  - _Requirements: R1_
  - _Prompt: Role: QA Engineer | Task: Write server integration tests | Restrictions: Test auth, format, performance | Success: Server behavior verified_

### 7. Tracing Provider Implementation

- [x] 7.1. Create `tracing/provider.py` with TracingProvider class
  - File: src/cardlink/observability/tracing/provider.py
  - Create TracingProvider managing OpenTelemetry tracer
  - Purpose: Provide distributed tracing capability
  - _Leverage: opentelemetry-api, opentelemetry-sdk_
  - _Requirements: R8, R9_
  - _Prompt: Role: Observability Engineer | Task: Create TracingProvider with OTLP export | Restrictions: Support gRPC and HTTP protocols | Success: Traces export to OTLP endpoint_

- [x] 7.2. Implement `initialize()` with Resource and TracerProvider setup
  - File: src/cardlink/observability/tracing/provider.py
  - Set up Resource with service.name, service.version; create TracerProvider
  - Purpose: Configure OpenTelemetry with proper resource attributes
  - _Leverage: opentelemetry.sdk.resources, opentelemetry.sdk.trace_
  - _Requirements: R8_
  - _Prompt: Role: Observability Engineer | Task: Initialize TracerProvider with Resource | Restrictions: Include all resource attributes | Success: Traces include service info_

- [x] 7.3. Implement OTLP exporter configuration (gRPC and HTTP)
  - File: src/cardlink/observability/tracing/provider.py
  - Create OTLPSpanExporter based on configured protocol
  - Purpose: Support both OTLP transport options
  - _Leverage: opentelemetry-exporter-otlp-proto-grpc, opentelemetry-exporter-otlp-proto-http_
  - _Requirements: R8_
  - _Prompt: Role: Observability Engineer | Task: Configure OTLP exporter for grpc/http | Restrictions: Handle connection failures gracefully | Success: Export works with both protocols_

- [x] 7.4. Implement BatchSpanProcessor setup
  - File: src/cardlink/observability/tracing/provider.py
  - Configure BatchSpanProcessor for efficient span batching
  - Purpose: Optimize trace export performance
  - _Leverage: opentelemetry.sdk.trace.export.BatchSpanProcessor_
  - _Requirements: R8_
  - _Prompt: Role: Observability Engineer | Task: Set up BatchSpanProcessor | Restrictions: Configure batch size and interval | Success: Spans batched efficiently_

- [x] 7.5. Implement `start_span()` context manager
  - File: src/cardlink/observability/tracing/provider.py
  - Create context manager for span creation with attributes
  - Purpose: Simplify span creation in application code
  - _Leverage: tracer.start_as_current_span(), contextmanager_
  - _Requirements: R9_
  - _Prompt: Role: Observability Engineer | Task: Create start_span context manager | Restrictions: Support kind and attributes | Success: Spans easily created_

- [x] 7.6. Implement context propagation methods
  - File: src/cardlink/observability/tracing/provider.py
  - Create inject_context() and extract_context() for W3C Trace Context
  - Purpose: Enable distributed tracing across services
  - _Leverage: opentelemetry.propagate_
  - _Requirements: R9_
  - _Prompt: Role: Observability Engineer | Task: Implement context injection/extraction | Restrictions: Use W3C Trace Context format | Success: Context propagates across services_

- [x] 7.7. Implement `trace_decorator()` for function instrumentation
  - File: src/cardlink/observability/tracing/provider.py
  - Create decorator for automatic function tracing
  - Purpose: Simplify instrumentation of functions
  - _Leverage: functools.wraps, tracer_
  - _Requirements: R9_
  - _Prompt: Role: Observability Engineer | Task: Create trace decorator | Restrictions: Preserve function signature | Success: Functions easily instrumented_

- [x] 7.8. Write unit tests for TracingProvider
  - File: tests/observability/test_tracing.py
  - Test provider initialization, span creation, context propagation
  - Purpose: Verify tracing functionality
  - _Leverage: pytest, in-memory exporter_
  - _Requirements: R8, R9_
  - _Prompt: Role: QA Engineer | Task: Write tracing unit tests | Restrictions: Use in-memory exporter for testing | Success: Full tracing coverage_

### 8. Health Checker Implementation

- [x] 8.1. Create `health/checker.py` with HealthChecker class
  - File: src/cardlink/observability/health/checker.py
  - Create HealthChecker with HealthStatus enum, check registration
  - Purpose: Provide health check infrastructure
  - _Leverage: Python dataclasses, enum_
  - _Requirements: R10_
  - _Prompt: Role: Reliability Engineer | Task: Create HealthChecker with pluggable checks | Restrictions: 5 second timeout, aggregate results | Success: Health checks can be registered and run_

- [x] 8.2. Implement `register_check()` and `unregister_check()` methods
  - File: src/cardlink/observability/health/checker.py
  - Allow dynamic registration of named health checks
  - Purpose: Support pluggable health checks
  - _Leverage: Dictionary of check functions_
  - _Requirements: R10_
  - _Prompt: Role: Reliability Engineer | Task: Implement check registration | Restrictions: Thread-safe registration | Success: Checks can be added/removed_

- [x] 8.3. Implement `run_all_checks()` with aggregated status
  - File: src/cardlink/observability/health/checker.py
  - Run all registered checks, aggregate into overall health
  - Purpose: Provide comprehensive health status
  - _Leverage: concurrent.futures for parallel execution_
  - _Requirements: R10_
  - _Prompt: Role: Reliability Engineer | Task: Implement parallel check execution | Restrictions: Timeout individual checks | Success: Overall health correctly computed_

- [x] 8.4. Create pre-defined health checks
  - File: src/cardlink/observability/health/checks.py
  - Create database, disk space, memory check factory functions
  - Purpose: Provide common health checks out of box
  - _Leverage: psutil, database connection test_
  - _Requirements: R10_
  - _Prompt: Role: Reliability Engineer | Task: Create database, disk, memory checks | Restrictions: Configurable thresholds | Success: Common checks available_

- [x] 8.5. Implement health HTTP server
  - File: src/cardlink/observability/health/server.py
  - Create HTTP server with /health, /health/live, /health/ready endpoints
  - Purpose: Expose health checks via HTTP for Kubernetes
  - _Leverage: http.server, JSON responses_
  - _Requirements: R10_
  - _Prompt: Role: API Developer | Task: Create health HTTP endpoints | Restrictions: Return 200 or 503 based on status | Success: Kubernetes probes work_

- [x] 8.6. Write unit tests for health checker
  - File: tests/observability/test_health.py
  - Test check registration, execution, aggregation, timeouts
  - Purpose: Verify health check functionality
  - _Leverage: pytest, mock checks_
  - _Requirements: R10_
  - _Prompt: Role: QA Engineer | Task: Write health checker tests | Restrictions: Test failure scenarios | Success: Full health coverage_

### 9. Structured Logger Implementation

- [x] 9.1. Create `logging/structured.py` with StructuredFormatter
  - File: src/cardlink/observability/logging/structured.py
  - Create JSON formatter with timestamp, level, message, component, trace_id
  - Purpose: Provide structured JSON log output
  - _Leverage: logging.Formatter, json_
  - _Requirements: R11_
  - _Prompt: Role: Logging Engineer | Task: Create JSON log formatter | Restrictions: ISO 8601 timestamps, include trace context | Success: Logs output as JSON_

- [x] 9.2. Implement trace context extraction
  - File: src/cardlink/observability/logging/structured.py
  - Extract trace_id and span_id from OpenTelemetry context
  - Purpose: Enable log-trace correlation
  - _Leverage: opentelemetry.trace.get_current_span()_
  - _Requirements: R11_
  - _Prompt: Role: Logging Engineer | Task: Extract trace context into logs | Restrictions: Handle missing context gracefully | Success: Logs include trace IDs when available_

- [x] 9.3. Create LoggerManager class
  - File: src/cardlink/observability/logging/manager.py
  - Manage component loggers with configurable levels
  - Purpose: Provide per-component log configuration
  - _Leverage: logging.getLogger(), logging.setLevel()_
  - _Requirements: R11_
  - _Prompt: Role: Logging Engineer | Task: Create logger manager | Restrictions: Support runtime level changes | Success: Component loggers configurable_

- [x] 9.4. Write unit tests for structured logging
  - File: tests/observability/test_logging.py
  - Test JSON formatting, trace context, level configuration
  - Purpose: Verify logging functionality
  - _Leverage: pytest, StringIO capture_
  - _Requirements: R11_
  - _Prompt: Role: QA Engineer | Task: Write logging tests | Restrictions: Verify JSON structure | Success: Full logging coverage_

### 10. Dashboard Templates Implementation

- [ ] 10.1. Create `dashboards/templates.py` with DashboardTemplates class
  - File: src/cardlink/observability/dashboards/templates.py
  - Create class generating Grafana dashboard JSON
  - Purpose: Provide ready-to-use Grafana dashboards
  - _Leverage: JSON generation, Grafana schema_
  - _Requirements: R12_
  - _Prompt: Role: Visualization Engineer | Task: Create Grafana dashboard generator | Restrictions: Valid Grafana 9.0+ JSON | Success: Dashboards import into Grafana_

- [ ] 10.2. Implement OTA overview dashboard
  - File: src/cardlink/observability/dashboards/templates.py
  - Dashboard showing sessions, triggers, connection status
  - Purpose: Provide operational visibility
  - _Leverage: Prometheus queries, Grafana panels_
  - _Requirements: R12_
  - _Prompt: Role: Visualization Engineer | Task: Create OTA overview dashboard | Restrictions: Include key metrics | Success: Dashboard shows session overview_

- [ ] 10.3. Implement export_all() method
  - File: src/cardlink/observability/dashboards/templates.py
  - Export all dashboards to specified directory as JSON files
  - Purpose: Enable easy dashboard deployment
  - _Leverage: json.dump(), pathlib_
  - _Requirements: R12_
  - _Prompt: Role: Visualization Engineer | Task: Implement dashboard export | Restrictions: Create directory if needed | Success: JSON files created_

### 11. Alerting Rules Implementation

- [ ] 11.1. Create `alerting/rules.py` with AlertingRules class
  - File: src/cardlink/observability/alerting/rules.py
  - Create class generating Prometheus alerting rules YAML
  - Purpose: Provide ready-to-use alerting rules
  - _Leverage: YAML generation, Prometheus alert format_
  - _Requirements: R13_
  - _Prompt: Role: SRE Engineer | Task: Create alerting rules generator | Restrictions: Valid Prometheus YAML | Success: Rules import into Prometheus_

- [ ] 11.2. Define error and performance alerting rules
  - File: src/cardlink/observability/alerting/rules.py
  - Create rules for high error rates, latency, disconnections
  - Purpose: Alert on operational issues
  - _Leverage: Prometheus alerting expressions_
  - _Requirements: R13_
  - _Prompt: Role: SRE Engineer | Task: Define alerting rules | Restrictions: Include severity levels | Success: Alerts fire on conditions_

- [ ] 11.3. Implement export_yaml() method
  - File: src/cardlink/observability/alerting/rules.py
  - Export rules to YAML file
  - Purpose: Enable easy alerting deployment
  - _Leverage: yaml.dump()_
  - _Requirements: R13_
  - _Prompt: Role: SRE Engineer | Task: Implement YAML export | Restrictions: Valid Prometheus format | Success: YAML file created_

### 12. CLI Commands Implementation

- [ ] 12.1. Create `cardlink/cli/observe.py` with Click command group
  - File: src/cardlink/cli/observe.py
  - Create gp-observe CLI with status, export, health, config, test subcommands
  - Purpose: Provide CLI access to observability features
  - _Leverage: Click framework_
  - _Requirements: R14_
  - _Prompt: Role: CLI Developer | Task: Create observability CLI group | Restrictions: Use Click, consistent with other CLI commands | Success: CLI accessible_

- [ ] 12.2. Implement `status` command
  - File: src/cardlink/cli/observe.py
  - Display current metrics summary with optional JSON output
  - Purpose: Quick metrics overview from terminal
  - _Leverage: Click, MetricsCollector_
  - _Requirements: R14_
  - _Prompt: Role: CLI Developer | Task: Create status command | Restrictions: Human-readable default, --json option | Success: Status displays metrics_

- [ ] 12.3. Implement `health` command
  - File: src/cardlink/cli/observe.py
  - Display health status with colored output
  - Purpose: Quick health check from terminal
  - _Leverage: Click, HealthChecker, rich/colorama_
  - _Requirements: R14_
  - _Prompt: Role: CLI Developer | Task: Create health command | Restrictions: Color by status, --verbose option | Success: Health status displayed_

- [ ] 12.4. Register CLI entry point in pyproject.toml
  - File: pyproject.toml
  - Add gp-observe entry point
  - Purpose: Make CLI installable
  - _Leverage: pyproject.toml scripts_
  - _Requirements: R14_
  - _Prompt: Role: CLI Developer | Task: Register CLI entry point | Restrictions: Follow existing pattern | Success: gp-observe command available_

### 13. Component Integrations

- [ ] 13.1. Integrate observability with PSK-TLS server
  - File: src/cardlink/server/*.py
  - Add metrics for TLS handshakes, APDU exchanges; tracing spans for sessions
  - Purpose: Instrument server operations
  - _Leverage: MetricsCollector, TracingProvider_
  - _Requirements: R2, R3, R9_
  - _Prompt: Role: Integration Engineer | Task: Instrument PSK-TLS server | Restrictions: Minimal performance impact | Success: Server operations tracked_

- [ ] 13.2. Integrate observability with phone controller
  - File: src/cardlink/phone/*.py
  - Add metrics for ADB operations, device connections
  - Purpose: Instrument device operations
  - _Leverage: MetricsCollector_
  - _Requirements: R5, R9_
  - _Prompt: Role: Integration Engineer | Task: Instrument phone controller | Restrictions: Handle failures gracefully | Success: Device operations tracked_

- [ ] 13.3. Integrate observability with database layer
  - File: src/cardlink/database/*.py
  - Add metrics for queries, connection pool; health check for connectivity
  - Purpose: Instrument database operations
  - _Leverage: MetricsCollector, HealthChecker_
  - _Requirements: R7, R9, R10_
  - _Prompt: Role: Integration Engineer | Task: Instrument database layer | Restrictions: Don't modify query semantics | Success: Database operations tracked_

### 14. Documentation and Performance Testing

- [ ] 14.1. Write module docstrings for all classes
  - Files: All src/cardlink/observability/**/*.py
  - Add Google-style docstrings with examples
  - Purpose: Enable autodoc generation
  - _Leverage: Google docstring style_
  - _Requirements: R1, R8, R10, R11_
  - _Prompt: Role: Technical Writer | Task: Add comprehensive docstrings | Restrictions: Include usage examples | Success: All classes documented_

- [ ] 14.2. Create observability guide documentation
  - File: docs/observability-guide.md
  - Document setup, configuration, usage, troubleshooting
  - Purpose: Enable users to set up observability stack
  - _Leverage: Markdown, code examples_
  - _Requirements: R1, R8, R10, R11, R12, R13, R14_
  - _Prompt: Role: Technical Writer | Task: Write observability guide | Restrictions: Include all config options | Success: Users can follow guide_

- [ ] 14.3. Benchmark metrics collection overhead
  - File: tests/observability/test_performance.py
  - Measure CPU overhead of metrics collection
  - Purpose: Verify <1% CPU overhead requirement
  - _Leverage: pytest-benchmark, psutil_
  - _Requirements: R1_
  - _Prompt: Role: Performance Engineer | Task: Benchmark metrics overhead | Restrictions: Test under realistic load | Success: <1% CPU overhead verified_

- [ ] 14.4. Test metrics endpoint response time
  - File: tests/observability/test_performance.py
  - Measure /metrics endpoint latency under load
  - Purpose: Verify <100ms response requirement
  - _Leverage: pytest-benchmark, concurrent requests_
  - _Requirements: R1_
  - _Prompt: Role: Performance Engineer | Task: Benchmark endpoint latency | Restrictions: Test concurrent requests | Success: <100ms latency verified_

## Task Dependencies

```
1 (Setup) → 2 (Config) → 3 (Manager)
         → 4 (Registry) → 5 (Collector) → 6 (Server)
         → 7 (Tracing)
         → 8 (Health)
         → 9 (Logging)
         → 10 (Dashboards)
         → 11 (Alerting)

12 (CLI) ← depends on 5, 6, 8
13 (Integrations) ← depends on 3, 5, 7, 8
14 (Docs/Perf) ← finalize after implementation
```

## Progress Summary

| Section | Tasks | Completed | Pending |
|---------|-------|-----------|---------|
| 1. Setup | 7 | 5 | 2 |
| 2. Config | 7 | 6 | 1 |
| 3. Manager | 10 | 9 | 1 |
| 4. Registry | 8 | 7 | 1 |
| 5. Collector | 10 | 6 | 4 |
| 6. Server | 7 | 6 | 1 |
| 7. Tracing | 8 | 0 | 8 |
| 8. Health | 6 | 0 | 6 |
| 9. Logging | 4 | 0 | 4 |
| 10. Dashboards | 3 | 0 | 3 |
| 11. Alerting | 3 | 0 | 3 |
| 12. CLI | 4 | 0 | 4 |
| 13. Integrations | 3 | 0 | 3 |
| 14. Docs/Perf | 4 | 0 | 4 |
| **Total** | **84** | **39** | **45** |

## Notes

- OpenTelemetry tracing is optional but recommended for debugging complex issues
- Metrics collection should have minimal performance impact (<1% CPU overhead)
- Health checks should complete within 5 seconds to avoid timeout issues
- Dashboard templates are Grafana-compatible JSON exports
- Alerting rules are Prometheus-compatible YAML format
- Label cardinality should be controlled to prevent memory issues
