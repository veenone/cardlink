# Design Document: Observability

## Introduction

This document describes the technical design for the Observability component of CardLink. The observability layer provides comprehensive monitoring through Prometheus metrics, OpenTelemetry tracing, structured logging, and health check endpoints.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CardLink Application                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ PSK-TLS     │ │ Phone       │ │ Modem       │ │ Test        │           │
│  │ Server      │ │ Controller  │ │ Controller  │ │ Runner      │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         │               │               │               │                   │
│         └───────────────┴───────────────┴───────────────┘                   │
│                                   │                                          │
│                                   ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Observability Layer                               │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │  │
│  │  │MetricsCollector│ │TracingProvider│ │HealthChecker│ │StructuredLogger│ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘     │  │
│  │         │               │               │               │             │  │
│  │  ┌──────┴───────────────┴───────────────┴───────────────┴──────┐     │  │
│  │  │                    ObservabilityManager                      │     │  │
│  │  └──────────────────────────────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
         ┌─────────────────┐ ┌───────────┐ ┌─────────────────┐
         │ /metrics        │ │ /health   │ │ OTLP Exporter   │
         │ (Prometheus)    │ │ endpoints │ │ (gRPC/HTTP)     │
         └────────┬────────┘ └─────┬─────┘ └────────┬────────┘
                  │                │                │
                  ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        External Monitoring Systems                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Prometheus  │ │ Grafana     │ │ Grafana     │ │ Jaeger/     │           │
│  │             │ │             │ │ Alloy       │ │ Zipkin      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility |
|-----------|----------------|
| **ObservabilityManager** | Central coordinator for all observability features |
| **MetricsCollector** | Collects and exposes Prometheus metrics |
| **MetricsRegistry** | Manages metric definitions and instances |
| **MetricsExporter** | HTTP endpoint for Prometheus scraping |
| **TracingProvider** | OpenTelemetry tracer configuration |
| **SpanManager** | Creates and manages trace spans |
| **OTLPExporter** | Exports traces/metrics via OTLP |
| **HealthChecker** | Performs health checks on components |
| **HealthEndpoint** | HTTP endpoints for health status |
| **StructuredLogger** | JSON logging with trace correlation |

## Component Design

### 1. ObservabilityManager

Central manager for all observability features.

```python
from typing import Optional, Dict, Any
from dataclasses import dataclass
import threading

@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_path: str = '/metrics'
    metrics_auth_enabled: bool = False
    metrics_username: Optional[str] = None
    metrics_password: Optional[str] = None

    # Tracing
    tracing_enabled: bool = False
    otlp_endpoint: Optional[str] = None
    otlp_protocol: str = 'grpc'  # grpc or http
    service_name: str = 'cardlink'
    service_version: str = '1.0.0'

    # Health
    health_port: int = 8081
    health_enabled: bool = True

    # Logging
    log_level: str = 'INFO'
    log_format: str = 'json'
    log_trace_correlation: bool = True


class ObservabilityManager:
    """Central manager for observability features."""

    _instance: Optional['ObservabilityManager'] = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[ObservabilityConfig] = None):
        """Singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: Optional[ObservabilityConfig] = None):
        if self._initialized:
            return

        self.config = config or ObservabilityConfig()
        self._metrics_collector: Optional[MetricsCollector] = None
        self._tracing_provider: Optional[TracingProvider] = None
        self._health_checker: Optional[HealthChecker] = None
        self._logger: Optional[StructuredLogger] = None
        self._initialized = True

    def initialize(self) -> None:
        """Initialize all observability components."""
        # Initialize metrics
        if self.config.metrics_enabled:
            self._metrics_collector = MetricsCollector()
            self._metrics_collector.start_server(
                port=self.config.metrics_port,
                path=self.config.metrics_path
            )

        # Initialize tracing
        if self.config.tracing_enabled:
            self._tracing_provider = TracingProvider(
                service_name=self.config.service_name,
                service_version=self.config.service_version,
                otlp_endpoint=self.config.otlp_endpoint,
                otlp_protocol=self.config.otlp_protocol
            )
            self._tracing_provider.initialize()

        # Initialize health checker
        if self.config.health_enabled:
            self._health_checker = HealthChecker()
            self._health_checker.start_server(port=self.config.health_port)

        # Initialize structured logger
        self._logger = StructuredLogger(
            level=self.config.log_level,
            format=self.config.log_format,
            trace_correlation=self.config.log_trace_correlation
        )

    def shutdown(self) -> None:
        """Shutdown all observability components."""
        if self._metrics_collector:
            self._metrics_collector.stop_server()
        if self._tracing_provider:
            self._tracing_provider.shutdown()
        if self._health_checker:
            self._health_checker.stop_server()

    @property
    def metrics(self) -> 'MetricsCollector':
        """Get metrics collector."""
        if not self._metrics_collector:
            raise RuntimeError("Metrics not initialized")
        return self._metrics_collector

    @property
    def tracer(self) -> 'TracingProvider':
        """Get tracing provider."""
        if not self._tracing_provider:
            raise RuntimeError("Tracing not initialized")
        return self._tracing_provider

    @property
    def health(self) -> 'HealthChecker':
        """Get health checker."""
        if not self._health_checker:
            raise RuntimeError("Health checker not initialized")
        return self._health_checker

    @property
    def logger(self) -> 'StructuredLogger':
        """Get structured logger."""
        return self._logger


# Global accessor
def get_observability() -> ObservabilityManager:
    """Get the global observability manager."""
    return ObservabilityManager()
```

### 2. MetricsCollector

Collects and manages Prometheus metrics.

```python
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    start_http_server
)
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import threading

class MetricType(Enum):
    COUNTER = 'counter'
    HISTOGRAM = 'histogram'
    GAUGE = 'gauge'
    INFO = 'info'


@dataclass
class MetricDefinition:
    """Metric definition."""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str]
    buckets: Optional[List[float]] = None  # For histograms


class MetricsRegistry:
    """Registry for metric definitions."""

    # APDU Metrics
    APDU_COMMANDS_TOTAL = MetricDefinition(
        name='cardlink_apdu_commands_total',
        description='Total APDU commands sent',
        metric_type=MetricType.COUNTER,
        labels=['command_type', 'device_type']
    )

    APDU_RESPONSES_TOTAL = MetricDefinition(
        name='cardlink_apdu_responses_total',
        description='Total APDU responses received',
        metric_type=MetricType.COUNTER,
        labels=['status_word', 'status_category']
    )

    APDU_DURATION_SECONDS = MetricDefinition(
        name='cardlink_apdu_duration_seconds',
        description='APDU command/response duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['command_type'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
    )

    APDU_BYTES_TOTAL = MetricDefinition(
        name='cardlink_apdu_bytes_total',
        description='Total APDU bytes transferred',
        metric_type=MetricType.COUNTER,
        labels=['direction']  # sent, received
    )

    # TLS Metrics
    TLS_HANDSHAKES_TOTAL = MetricDefinition(
        name='cardlink_tls_handshakes_total',
        description='Total TLS handshakes',
        metric_type=MetricType.COUNTER,
        labels=['result', 'cipher_suite']
    )

    TLS_HANDSHAKE_DURATION_SECONDS = MetricDefinition(
        name='cardlink_tls_handshake_duration_seconds',
        description='TLS handshake duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['result'],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )

    TLS_CONNECTIONS_ACTIVE = MetricDefinition(
        name='cardlink_tls_connections_active',
        description='Currently active TLS connections',
        metric_type=MetricType.GAUGE,
        labels=[]
    )

    # Session Metrics
    SESSIONS_ACTIVE = MetricDefinition(
        name='cardlink_sessions_active',
        description='Currently active OTA sessions',
        metric_type=MetricType.GAUGE,
        labels=['device_type']
    )

    SESSIONS_TOTAL = MetricDefinition(
        name='cardlink_sessions_total',
        description='Total OTA sessions',
        metric_type=MetricType.COUNTER,
        labels=['status', 'session_type', 'device_type']
    )

    SESSION_DURATION_SECONDS = MetricDefinition(
        name='cardlink_session_duration_seconds',
        description='OTA session duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['status'],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
    )

    TRIGGERS_SENT_TOTAL = MetricDefinition(
        name='cardlink_triggers_sent_total',
        description='Total OTA triggers sent',
        metric_type=MetricType.COUNTER,
        labels=['trigger_type']  # sms, poll
    )

    # Device Metrics
    DEVICES_CONNECTED = MetricDefinition(
        name='cardlink_devices_connected',
        description='Currently connected devices',
        metric_type=MetricType.GAUGE,
        labels=['device_type']
    )

    DEVICE_ERRORS_TOTAL = MetricDefinition(
        name='cardlink_device_errors_total',
        description='Total device errors',
        metric_type=MetricType.COUNTER,
        labels=['device_type', 'error_type']
    )

    AT_COMMAND_DURATION_SECONDS = MetricDefinition(
        name='cardlink_at_command_duration_seconds',
        description='AT command duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['command'],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )

    ADB_OPERATION_DURATION_SECONDS = MetricDefinition(
        name='cardlink_adb_operation_duration_seconds',
        description='ADB operation duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['operation'],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )

    # Test Metrics
    TESTS_TOTAL = MetricDefinition(
        name='cardlink_tests_total',
        description='Total tests executed',
        metric_type=MetricType.COUNTER,
        labels=['suite_name', 'status']
    )

    TEST_DURATION_SECONDS = MetricDefinition(
        name='cardlink_test_duration_seconds',
        description='Test duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['suite_name'],
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
    )

    # System Metrics
    PROCESS_CPU_SECONDS = MetricDefinition(
        name='cardlink_process_cpu_seconds_total',
        description='Total CPU time used',
        metric_type=MetricType.COUNTER,
        labels=[]
    )

    PROCESS_MEMORY_BYTES = MetricDefinition(
        name='cardlink_process_memory_bytes',
        description='Process memory usage',
        metric_type=MetricType.GAUGE,
        labels=['type']  # rss, vms
    )

    DB_CONNECTIONS_ACTIVE = MetricDefinition(
        name='cardlink_db_connections_active',
        description='Active database connections',
        metric_type=MetricType.GAUGE,
        labels=[]
    )

    DB_QUERY_DURATION_SECONDS = MetricDefinition(
        name='cardlink_db_query_duration_seconds',
        description='Database query duration',
        metric_type=MetricType.HISTOGRAM,
        labels=['query_type'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
    )

    UPTIME_SECONDS = MetricDefinition(
        name='cardlink_uptime_seconds',
        description='Application uptime',
        metric_type=MetricType.GAUGE,
        labels=[]
    )

    BUILD_INFO = MetricDefinition(
        name='cardlink_build_info',
        description='Build information',
        metric_type=MetricType.INFO,
        labels=['version', 'python_version', 'platform']
    )


class MetricsCollector:
    """Collects and exposes Prometheus metrics."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self._registry = registry or CollectorRegistry()
        self._metrics: Dict[str, Any] = {}
        self._server_thread: Optional[threading.Thread] = None
        self._server_port: Optional[int] = None
        self._lock = threading.Lock()

        # Register all metrics
        self._register_metrics()

    def _register_metrics(self) -> None:
        """Register all metric definitions."""
        definitions = [
            attr for attr in dir(MetricsRegistry)
            if isinstance(getattr(MetricsRegistry, attr), MetricDefinition)
        ]

        for def_name in definitions:
            definition = getattr(MetricsRegistry, def_name)
            self._create_metric(definition)

    def _create_metric(self, definition: MetricDefinition) -> None:
        """Create metric from definition."""
        if definition.metric_type == MetricType.COUNTER:
            metric = Counter(
                definition.name,
                definition.description,
                definition.labels,
                registry=self._registry
            )
        elif definition.metric_type == MetricType.HISTOGRAM:
            metric = Histogram(
                definition.name,
                definition.description,
                definition.labels,
                buckets=definition.buckets or Histogram.DEFAULT_BUCKETS,
                registry=self._registry
            )
        elif definition.metric_type == MetricType.GAUGE:
            metric = Gauge(
                definition.name,
                definition.description,
                definition.labels,
                registry=self._registry
            )
        elif definition.metric_type == MetricType.INFO:
            metric = Info(
                definition.name,
                definition.description,
                registry=self._registry
            )
        else:
            raise ValueError(f"Unknown metric type: {definition.metric_type}")

        self._metrics[definition.name] = metric

    def get_metric(self, name: str) -> Any:
        """Get metric by name."""
        return self._metrics.get(name)

    # APDU Metrics
    def record_apdu_command(self, command_type: str, device_type: str) -> None:
        """Record APDU command sent."""
        self._metrics['cardlink_apdu_commands_total'].labels(
            command_type=command_type,
            device_type=device_type
        ).inc()

    def record_apdu_response(self, status_word: str, status_category: str) -> None:
        """Record APDU response received."""
        self._metrics['cardlink_apdu_responses_total'].labels(
            status_word=status_word,
            status_category=status_category
        ).inc()

    def record_apdu_duration(self, command_type: str, duration: float) -> None:
        """Record APDU command duration."""
        self._metrics['cardlink_apdu_duration_seconds'].labels(
            command_type=command_type
        ).observe(duration)

    def record_apdu_bytes(self, direction: str, byte_count: int) -> None:
        """Record APDU bytes transferred."""
        self._metrics['cardlink_apdu_bytes_total'].labels(
            direction=direction
        ).inc(byte_count)

    # TLS Metrics
    def record_tls_handshake(self, result: str, cipher_suite: str,
                            duration: float) -> None:
        """Record TLS handshake."""
        self._metrics['cardlink_tls_handshakes_total'].labels(
            result=result,
            cipher_suite=cipher_suite
        ).inc()
        self._metrics['cardlink_tls_handshake_duration_seconds'].labels(
            result=result
        ).observe(duration)

    def set_tls_connections(self, count: int) -> None:
        """Set active TLS connection count."""
        self._metrics['cardlink_tls_connections_active'].set(count)

    def inc_tls_connections(self) -> None:
        """Increment TLS connections."""
        self._metrics['cardlink_tls_connections_active'].inc()

    def dec_tls_connections(self) -> None:
        """Decrement TLS connections."""
        self._metrics['cardlink_tls_connections_active'].dec()

    # Session Metrics
    def set_active_sessions(self, count: int, device_type: str) -> None:
        """Set active session count."""
        self._metrics['cardlink_sessions_active'].labels(
            device_type=device_type
        ).set(count)

    def record_session_complete(self, status: str, session_type: str,
                                device_type: str, duration: float) -> None:
        """Record session completion."""
        self._metrics['cardlink_sessions_total'].labels(
            status=status,
            session_type=session_type,
            device_type=device_type
        ).inc()
        self._metrics['cardlink_session_duration_seconds'].labels(
            status=status
        ).observe(duration)

    def record_trigger_sent(self, trigger_type: str) -> None:
        """Record trigger sent."""
        self._metrics['cardlink_triggers_sent_total'].labels(
            trigger_type=trigger_type
        ).inc()

    # Device Metrics
    def set_devices_connected(self, count: int, device_type: str) -> None:
        """Set connected device count."""
        self._metrics['cardlink_devices_connected'].labels(
            device_type=device_type
        ).set(count)

    def record_device_error(self, device_type: str, error_type: str) -> None:
        """Record device error."""
        self._metrics['cardlink_device_errors_total'].labels(
            device_type=device_type,
            error_type=error_type
        ).inc()

    def record_at_command_duration(self, command: str, duration: float) -> None:
        """Record AT command duration."""
        self._metrics['cardlink_at_command_duration_seconds'].labels(
            command=command
        ).observe(duration)

    def record_adb_operation_duration(self, operation: str,
                                      duration: float) -> None:
        """Record ADB operation duration."""
        self._metrics['cardlink_adb_operation_duration_seconds'].labels(
            operation=operation
        ).observe(duration)

    # Test Metrics
    def record_test_result(self, suite_name: str, status: str,
                          duration: float) -> None:
        """Record test result."""
        self._metrics['cardlink_tests_total'].labels(
            suite_name=suite_name,
            status=status
        ).inc()
        self._metrics['cardlink_test_duration_seconds'].labels(
            suite_name=suite_name
        ).observe(duration)

    # System Metrics
    def update_system_metrics(self) -> None:
        """Update system resource metrics."""
        import psutil
        import time

        process = psutil.Process()

        # CPU
        cpu_times = process.cpu_times()
        # Note: This should be set, not inc, for total CPU time
        # Using a custom approach for CPU counter

        # Memory
        memory_info = process.memory_info()
        self._metrics['cardlink_process_memory_bytes'].labels(
            type='rss'
        ).set(memory_info.rss)
        self._metrics['cardlink_process_memory_bytes'].labels(
            type='vms'
        ).set(memory_info.vms)

    def set_build_info(self, version: str, python_version: str,
                      platform: str) -> None:
        """Set build information."""
        self._metrics['cardlink_build_info'].info({
            'version': version,
            'python_version': python_version,
            'platform': platform
        })

    def start_server(self, port: int = 9090, path: str = '/metrics') -> None:
        """Start metrics HTTP server."""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        registry = self._registry

        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == path or self.path == path + '/':
                    output = generate_latest(registry)
                    self.send_response(200)
                    self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                    self.end_headers()
                    self.wfile.write(output)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logging

        def serve():
            server = HTTPServer(('', port), MetricsHandler)
            server.serve_forever()

        self._server_port = port
        self._server_thread = threading.Thread(target=serve, daemon=True)
        self._server_thread.start()

    def stop_server(self) -> None:
        """Stop metrics server."""
        # Note: Simple implementation - thread is daemon so will stop with app
        pass

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(self._registry).decode('utf-8')
```

### 3. TracingProvider

OpenTelemetry tracing integration.

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps
import threading

class TracingProvider:
    """OpenTelemetry tracing provider."""

    def __init__(self,
                 service_name: str = 'cardlink',
                 service_version: str = '1.0.0',
                 otlp_endpoint: Optional[str] = None,
                 otlp_protocol: str = 'grpc'):
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint
        self.otlp_protocol = otlp_protocol
        self._provider: Optional[TracerProvider] = None
        self._tracer: Optional[trace.Tracer] = None
        self._propagator = TraceContextTextMapPropagator()

    def initialize(self) -> None:
        """Initialize tracing provider."""
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version
        })

        self._provider = TracerProvider(resource=resource)

        if self.otlp_endpoint:
            if self.otlp_protocol == 'grpc':
                exporter = GrpcExporter(endpoint=self.otlp_endpoint)
            else:
                exporter = HttpExporter(endpoint=self.otlp_endpoint)

            processor = BatchSpanProcessor(exporter)
            self._provider.add_span_processor(processor)

        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(self.service_name, self.service_version)

    def shutdown(self) -> None:
        """Shutdown tracing provider."""
        if self._provider:
            self._provider.shutdown()

    def get_tracer(self) -> trace.Tracer:
        """Get tracer instance."""
        if not self._tracer:
            raise RuntimeError("Tracing not initialized")
        return self._tracer

    @contextmanager
    def start_span(self, name: str, kind: SpanKind = SpanKind.INTERNAL,
                   attributes: Optional[Dict[str, Any]] = None):
        """Start a new span."""
        with self._tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {}
        ) as span:
            yield span

    def current_span(self) -> Optional[Span]:
        """Get current span."""
        return trace.get_current_span()

    def inject_context(self, carrier: Dict[str, str]) -> None:
        """Inject trace context into carrier."""
        self._propagator.inject(carrier)

    def extract_context(self, carrier: Dict[str, str]):
        """Extract trace context from carrier."""
        return self._propagator.extract(carrier)

    def trace_decorator(self, name: Optional[str] = None,
                       kind: SpanKind = SpanKind.INTERNAL):
        """Decorator to trace a function."""
        def decorator(func: Callable):
            span_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.start_span(span_name, kind=kind) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise

            return wrapper
        return decorator


class SpanManager:
    """Manages trace spans for CardLink operations."""

    def __init__(self, tracing_provider: TracingProvider):
        self._provider = tracing_provider

    @contextmanager
    def apdu_span(self, command_type: str, device_id: str):
        """Create span for APDU operation."""
        attributes = {
            'apdu.command_type': command_type,
            'device.id': device_id
        }
        with self._provider.start_span(
            f'apdu.{command_type}',
            kind=SpanKind.CLIENT,
            attributes=attributes
        ) as span:
            yield span

    @contextmanager
    def tls_handshake_span(self, client_address: str):
        """Create span for TLS handshake."""
        attributes = {
            'tls.client_address': client_address
        }
        with self._provider.start_span(
            'tls.handshake',
            kind=SpanKind.SERVER,
            attributes=attributes
        ) as span:
            yield span

    @contextmanager
    def session_span(self, session_id: str, session_type: str):
        """Create span for OTA session."""
        attributes = {
            'session.id': session_id,
            'session.type': session_type
        }
        with self._provider.start_span(
            'ota.session',
            kind=SpanKind.INTERNAL,
            attributes=attributes
        ) as span:
            yield span

    @contextmanager
    def db_span(self, operation: str, table: str):
        """Create span for database operation."""
        attributes = {
            'db.operation': operation,
            'db.table': table
        }
        with self._provider.start_span(
            f'db.{operation}',
            kind=SpanKind.CLIENT,
            attributes=attributes
        ) as span:
            yield span

    @contextmanager
    def test_span(self, suite_name: str, test_name: str):
        """Create span for test execution."""
        attributes = {
            'test.suite': suite_name,
            'test.name': test_name
        }
        with self._provider.start_span(
            f'test.{test_name}',
            kind=SpanKind.INTERNAL,
            attributes=attributes
        ) as span:
            yield span

    def add_apdu_response(self, span: Span, status_word: str,
                         duration_ms: float) -> None:
        """Add APDU response attributes to span."""
        span.set_attribute('apdu.status_word', status_word)
        span.set_attribute('apdu.duration_ms', duration_ms)

        if not status_word.startswith('90'):
            span.set_status(Status(StatusCode.ERROR, f"APDU error: {status_word}"))
```

### 4. HealthChecker

Health check implementation.

```python
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import time

class HealthStatus(Enum):
    HEALTHY = 'healthy'
    UNHEALTHY = 'unhealthy'
    DEGRADED = 'degraded'


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class OverallHealth:
    """Overall health status."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: str


class HealthChecker:
    """Performs health checks on components."""

    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._server_thread: Optional[threading.Thread] = None
        self._server: Optional[HTTPServer] = None

    def register_check(self, name: str,
                      check_fn: Callable[[], HealthCheckResult]) -> None:
        """Register a health check."""
        self._checks[name] = check_fn

    def unregister_check(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)

    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message='Check not found'
            )

        start_time = time.time()
        try:
            result = self._checks[name]()
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )

    def run_all_checks(self) -> OverallHealth:
        """Run all health checks."""
        results = []
        overall_status = HealthStatus.HEALTHY

        for name in self._checks:
            result = self.run_check(name)
            results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return OverallHealth(
            status=overall_status,
            checks=results,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        )

    def check_liveness(self) -> HealthCheckResult:
        """Basic liveness check."""
        return HealthCheckResult(
            name='liveness',
            status=HealthStatus.HEALTHY,
            message='Application is running'
        )

    def check_readiness(self) -> OverallHealth:
        """Readiness check (all components)."""
        return self.run_all_checks()

    def start_server(self, port: int = 8081) -> None:
        """Start health check HTTP server."""
        checker = self

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health' or self.path == '/health/':
                    self._handle_health()
                elif self.path == '/health/live':
                    self._handle_live()
                elif self.path == '/health/ready':
                    self._handle_ready()
                else:
                    self.send_response(404)
                    self.end_headers()

            def _handle_health(self):
                health = checker.run_all_checks()
                status_code = 200 if health.status == HealthStatus.HEALTHY else 503
                self._send_json(status_code, self._health_to_dict(health))

            def _handle_live(self):
                result = checker.check_liveness()
                status_code = 200 if result.status == HealthStatus.HEALTHY else 503
                self._send_json(status_code, asdict(result))

            def _handle_ready(self):
                health = checker.check_readiness()
                status_code = 200 if health.status == HealthStatus.HEALTHY else 503
                self._send_json(status_code, self._health_to_dict(health))

            def _send_json(self, status_code: int, data: dict):
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def _health_to_dict(self, health: OverallHealth) -> dict:
                return {
                    'status': health.status.value,
                    'timestamp': health.timestamp,
                    'checks': [asdict(c) for c in health.checks]
                }

            def log_message(self, format, *args):
                pass

        def serve():
            self._server = HTTPServer(('', port), HealthHandler)
            self._server.serve_forever()

        self._server_thread = threading.Thread(target=serve, daemon=True)
        self._server_thread.start()

    def stop_server(self) -> None:
        """Stop health check server."""
        if self._server:
            self._server.shutdown()


# Pre-defined health checks
def create_database_check(db_manager) -> Callable[[], HealthCheckResult]:
    """Create database health check."""
    def check() -> HealthCheckResult:
        try:
            health = db_manager.health_check()
            if health['status'] == 'healthy':
                return HealthCheckResult(
                    name='database',
                    status=HealthStatus.HEALTHY,
                    message='Database connection OK',
                    details=health
                )
            else:
                return HealthCheckResult(
                    name='database',
                    status=HealthStatus.UNHEALTHY,
                    message=health.get('error', 'Unknown error'),
                    details=health
                )
        except Exception as e:
            return HealthCheckResult(
                name='database',
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_metrics_check(metrics_port: int) -> Callable[[], HealthCheckResult]:
    """Create metrics endpoint health check."""
    def check() -> HealthCheckResult:
        import urllib.request
        try:
            url = f'http://localhost:{metrics_port}/metrics'
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return HealthCheckResult(
                        name='metrics',
                        status=HealthStatus.HEALTHY,
                        message='Metrics endpoint responding'
                    )
        except Exception as e:
            return HealthCheckResult(
                name='metrics',
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check
```

### 5. StructuredLogger

Structured logging with trace correlation.

```python
import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from opentelemetry import trace

class StructuredFormatter(logging.Formatter):
    """JSON formatter with trace correlation."""

    def __init__(self, include_trace: bool = True):
        super().__init__()
        self.include_trace = include_trace

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add trace context if available
        if self.include_trace:
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                log_data['trace_id'] = format(ctx.trace_id, '032x')
                log_data['span_id'] = format(ctx.span_id, '016x')

        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with trace correlation."""

    def __init__(self,
                 level: str = 'INFO',
                 format: str = 'json',
                 trace_correlation: bool = True):
        self.level = getattr(logging, level.upper())
        self.format = format
        self.trace_correlation = trace_correlation
        self._loggers: Dict[str, logging.Logger] = {}

        # Configure root logger
        self._configure_root()

    def _configure_root(self) -> None:
        """Configure root logger."""
        root = logging.getLogger()
        root.setLevel(self.level)

        # Remove existing handlers
        for handler in root.handlers[:]:
            root.removeHandler(handler)

        # Add structured handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.level)

        if self.format == 'json':
            handler.setFormatter(StructuredFormatter(
                include_trace=self.trace_correlation
            ))
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))

        root.addHandler(handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Get logger for component."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]

    def set_level(self, name: str, level: str) -> None:
        """Set log level for component."""
        logger = self.get_logger(name)
        logger.setLevel(getattr(logging, level.upper()))


class ComponentLogger:
    """Logger for a specific component with context."""

    def __init__(self, name: str, structured_logger: StructuredLogger):
        self._logger = structured_logger.get_logger(name)
        self._context: Dict[str, Any] = {}

    def with_context(self, **kwargs) -> 'ComponentLogger':
        """Create logger with additional context."""
        new_logger = ComponentLogger.__new__(ComponentLogger)
        new_logger._logger = self._logger
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(self, level: int, message: str, **kwargs) -> None:
        """Internal log method."""
        extra = {'extra_fields': {**self._context, **kwargs}}
        self._logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        self._logger.exception(message, extra={'extra_fields': {**self._context, **kwargs}})
```

### 6. Grafana Dashboard Templates

Dashboard JSON templates.

```python
from typing import Dict, Any
import json

class DashboardTemplates:
    """Grafana dashboard templates."""

    @staticmethod
    def ota_overview() -> Dict[str, Any]:
        """OTA Overview dashboard."""
        return {
            "title": "CardLink - OTA Overview",
            "uid": "cardlink-ota-overview",
            "panels": [
                {
                    "title": "Active Sessions",
                    "type": "gauge",
                    "targets": [{
                        "expr": "sum(cardlink_sessions_active)"
                    }],
                    "gridPos": {"x": 0, "y": 0, "w": 6, "h": 6}
                },
                {
                    "title": "Session Success Rate",
                    "type": "gauge",
                    "targets": [{
                        "expr": "sum(rate(cardlink_sessions_total{status='completed'}[5m])) / sum(rate(cardlink_sessions_total[5m])) * 100"
                    }],
                    "gridPos": {"x": 6, "y": 0, "w": 6, "h": 6}
                },
                {
                    "title": "Sessions Over Time",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "sum by (status) (rate(cardlink_sessions_total[5m]))",
                        "legendFormat": "{{status}}"
                    }],
                    "gridPos": {"x": 0, "y": 6, "w": 12, "h": 8}
                },
                {
                    "title": "Session Duration (p95)",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "histogram_quantile(0.95, sum(rate(cardlink_session_duration_seconds_bucket[5m])) by (le))"
                    }],
                    "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
                },
                {
                    "title": "Triggers Sent",
                    "type": "stat",
                    "targets": [{
                        "expr": "sum(increase(cardlink_triggers_sent_total[1h]))"
                    }],
                    "gridPos": {"x": 12, "y": 8, "w": 6, "h": 6}
                }
            ]
        }

    @staticmethod
    def apdu_analysis() -> Dict[str, Any]:
        """APDU Analysis dashboard."""
        return {
            "title": "CardLink - APDU Analysis",
            "uid": "cardlink-apdu-analysis",
            "panels": [
                {
                    "title": "Command Distribution",
                    "type": "piechart",
                    "targets": [{
                        "expr": "sum by (command_type) (increase(cardlink_apdu_commands_total[1h]))",
                        "legendFormat": "{{command_type}}"
                    }],
                    "gridPos": {"x": 0, "y": 0, "w": 8, "h": 8}
                },
                {
                    "title": "Response Status",
                    "type": "piechart",
                    "targets": [{
                        "expr": "sum by (status_category) (increase(cardlink_apdu_responses_total[1h]))",
                        "legendFormat": "{{status_category}}"
                    }],
                    "gridPos": {"x": 8, "y": 0, "w": 8, "h": 8}
                },
                {
                    "title": "APDU Latency Percentiles",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, sum(rate(cardlink_apdu_duration_seconds_bucket[5m])) by (le))",
                            "legendFormat": "p50"
                        },
                        {
                            "expr": "histogram_quantile(0.95, sum(rate(cardlink_apdu_duration_seconds_bucket[5m])) by (le))",
                            "legendFormat": "p95"
                        },
                        {
                            "expr": "histogram_quantile(0.99, sum(rate(cardlink_apdu_duration_seconds_bucket[5m])) by (le))",
                            "legendFormat": "p99"
                        }
                    ],
                    "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
                },
                {
                    "title": "Error Rate",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "sum(rate(cardlink_apdu_responses_total{status_category='error'}[5m])) / sum(rate(cardlink_apdu_responses_total[5m])) * 100"
                    }],
                    "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8}
                }
            ]
        }

    @staticmethod
    def device_status() -> Dict[str, Any]:
        """Device Status dashboard."""
        return {
            "title": "CardLink - Device Status",
            "uid": "cardlink-device-status",
            "panels": [
                {
                    "title": "Connected Devices",
                    "type": "stat",
                    "targets": [{
                        "expr": "sum(cardlink_devices_connected)"
                    }],
                    "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4}
                },
                {
                    "title": "Phones Connected",
                    "type": "stat",
                    "targets": [{
                        "expr": "cardlink_devices_connected{device_type='phone'}"
                    }],
                    "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4}
                },
                {
                    "title": "Modems Connected",
                    "type": "stat",
                    "targets": [{
                        "expr": "cardlink_devices_connected{device_type='modem'}"
                    }],
                    "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4}
                },
                {
                    "title": "Device Errors",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "sum by (device_type, error_type) (rate(cardlink_device_errors_total[5m]))",
                        "legendFormat": "{{device_type}} - {{error_type}}"
                    }],
                    "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8}
                },
                {
                    "title": "AT Command Latency",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "histogram_quantile(0.95, sum(rate(cardlink_at_command_duration_seconds_bucket[5m])) by (le, command))",
                        "legendFormat": "{{command}}"
                    }],
                    "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8}
                }
            ]
        }

    @staticmethod
    def test_results() -> Dict[str, Any]:
        """Test Results dashboard."""
        return {
            "title": "CardLink - Test Results",
            "uid": "cardlink-test-results",
            "panels": [
                {
                    "title": "Test Pass Rate",
                    "type": "gauge",
                    "targets": [{
                        "expr": "sum(rate(cardlink_tests_total{status='passed'}[1h])) / sum(rate(cardlink_tests_total[1h])) * 100"
                    }],
                    "gridPos": {"x": 0, "y": 0, "w": 8, "h": 6}
                },
                {
                    "title": "Tests by Status",
                    "type": "piechart",
                    "targets": [{
                        "expr": "sum by (status) (increase(cardlink_tests_total[1h]))",
                        "legendFormat": "{{status}}"
                    }],
                    "gridPos": {"x": 8, "y": 0, "w": 8, "h": 6}
                },
                {
                    "title": "Test Duration Trend",
                    "type": "timeseries",
                    "targets": [{
                        "expr": "histogram_quantile(0.95, sum(rate(cardlink_test_duration_seconds_bucket[5m])) by (le, suite_name))",
                        "legendFormat": "{{suite_name}}"
                    }],
                    "gridPos": {"x": 0, "y": 6, "w": 24, "h": 8}
                }
            ]
        }

    @staticmethod
    def export_all(output_dir: str) -> None:
        """Export all dashboards to files."""
        import os

        os.makedirs(output_dir, exist_ok=True)

        dashboards = {
            'ota-overview.json': DashboardTemplates.ota_overview(),
            'apdu-analysis.json': DashboardTemplates.apdu_analysis(),
            'device-status.json': DashboardTemplates.device_status(),
            'test-results.json': DashboardTemplates.test_results()
        }

        for filename, dashboard in dashboards.items():
            path = os.path.join(output_dir, filename)
            with open(path, 'w') as f:
                json.dump(dashboard, f, indent=2)
```

### 7. Alerting Rules

Prometheus alerting rules.

```python
from typing import Dict, Any, List
import yaml

class AlertingRules:
    """Prometheus alerting rule definitions."""

    @staticmethod
    def get_rules() -> Dict[str, Any]:
        """Get all alerting rules."""
        return {
            'groups': [
                {
                    'name': 'cardlink.errors',
                    'rules': [
                        {
                            'alert': 'HighAPDUErrorRate',
                            'expr': 'sum(rate(cardlink_apdu_responses_total{status_category="error"}[5m])) / sum(rate(cardlink_apdu_responses_total[5m])) > 0.05',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'High APDU error rate',
                                'description': 'APDU error rate is above 5% for the last 5 minutes'
                            }
                        },
                        {
                            'alert': 'SessionTimeoutSpike',
                            'expr': 'sum(rate(cardlink_sessions_total{status="timeout"}[5m])) > 0.1',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'Session timeout spike',
                                'description': 'Session timeout rate has increased significantly'
                            }
                        },
                        {
                            'alert': 'TLSHandshakeFailures',
                            'expr': 'sum(rate(cardlink_tls_handshakes_total{result="failed"}[5m])) > 0',
                            'for': '2m',
                            'labels': {'severity': 'critical'},
                            'annotations': {
                                'summary': 'TLS handshake failures detected',
                                'description': 'TLS handshakes are failing'
                            }
                        },
                        {
                            'alert': 'DeviceDisconnected',
                            'expr': 'cardlink_devices_connected == 0',
                            'for': '1m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'No devices connected',
                                'description': 'No test devices are currently connected'
                            }
                        },
                        {
                            'alert': 'DatabaseConnectionFailure',
                            'expr': 'cardlink_db_connections_active == 0',
                            'for': '1m',
                            'labels': {'severity': 'critical'},
                            'annotations': {
                                'summary': 'Database connection failure',
                                'description': 'Unable to connect to database'
                            }
                        }
                    ]
                },
                {
                    'name': 'cardlink.performance',
                    'rules': [
                        {
                            'alert': 'HighAPDULatency',
                            'expr': 'histogram_quantile(0.95, sum(rate(cardlink_apdu_duration_seconds_bucket[5m])) by (le)) > 1',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'High APDU latency',
                                'description': 'P95 APDU latency is above 1 second'
                            }
                        },
                        {
                            'alert': 'LongSessionDuration',
                            'expr': 'histogram_quantile(0.95, sum(rate(cardlink_session_duration_seconds_bucket[5m])) by (le)) > 60',
                            'for': '10m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'Long session duration',
                                'description': 'P95 session duration exceeds 60 seconds'
                            }
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def export_yaml(output_path: str) -> None:
        """Export rules as YAML file."""
        rules = AlertingRules.get_rules()
        with open(output_path, 'w') as f:
            yaml.dump(rules, f, default_flow_style=False)
```

## CLI Design

### Command Structure

```
cardlink-metrics
├── status                  # Show metrics summary
│   └── --json             # JSON output
├── export                  # Export all metrics
│   ├── --format <fmt>     # prometheus or json
│   └── --output <file>    # Output file
├── health                  # Show health status
│   └── --verbose          # Include all check details
├── config                  # View/update config
│   ├── show               # Show current config
│   └── set <key> <value>  # Update config
├── test                    # Test connectivity
│   └── --otlp             # Test OTLP endpoint
└── dashboards             # Dashboard management
    └── export <dir>       # Export Grafana dashboards
```

## Dependencies

### Required Packages

```
prometheus-client>=0.17.0      # Prometheus metrics
opentelemetry-api>=1.20.0      # OpenTelemetry API
opentelemetry-sdk>=1.20.0      # OpenTelemetry SDK
opentelemetry-exporter-otlp>=1.20.0  # OTLP exporter
psutil>=5.9.0                  # System metrics
pyyaml>=6.0                    # YAML export
```

### Optional Packages

```
opentelemetry-exporter-jaeger  # Jaeger export
opentelemetry-exporter-zipkin  # Zipkin export
```
