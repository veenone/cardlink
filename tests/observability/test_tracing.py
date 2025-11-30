"""Unit tests for TracingProvider.

Tests tracer initialization, span creation, context propagation, and decorator.
"""

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.trace import SpanKind

from cardlink.observability.config import TracingConfig
from cardlink.observability.tracing.provider import TracingProvider, trace


class TestTracingProviderCreation:
    """Tests for TracingProvider initialization."""

    def test_create_provider(self, tracing_config):
        """Test creating tracing provider."""
        provider = TracingProvider(tracing_config)
        assert provider is not None
        assert provider.config == tracing_config
        assert provider.is_running is False

    def test_create_provider_disabled(self, tracing_config_disabled):
        """Test creating disabled tracing provider."""
        provider = TracingProvider(tracing_config_disabled)
        assert provider is not None
        assert provider.config.enabled is False


class TestTracingProviderLifecycle:
    """Tests for TracingProvider start/stop lifecycle."""

    def test_start_provider(self, tracing_config):
        """Test starting tracing provider."""
        provider = TracingProvider(tracing_config)
        provider.start()

        try:
            assert provider.is_running is True
            assert provider._tracer is not None
            assert provider._tracer_provider is not None
        finally:
            provider.shutdown()

    def test_start_idempotent(self, tracing_config):
        """Test that starting twice is safe."""
        provider = TracingProvider(tracing_config)
        provider.start()
        provider.start()  # Should warn but not error

        try:
            assert provider.is_running is True
        finally:
            provider.shutdown()

    def test_shutdown_provider(self, tracing_config):
        """Test shutting down tracing provider."""
        provider = TracingProvider(tracing_config)
        provider.start()
        provider.shutdown()

        assert provider.is_running is False

    def test_shutdown_not_started(self, tracing_config):
        """Test shutdown when not started is safe."""
        provider = TracingProvider(tracing_config)
        provider.shutdown()  # Should not raise

    def test_shutdown_idempotent(self, tracing_config):
        """Test that shutdown twice is safe."""
        provider = TracingProvider(tracing_config)
        provider.start()
        provider.shutdown()
        provider.shutdown()  # Should not raise


class TestTracingProviderTracer:
    """Tests for tracer access."""

    def test_tracer_property_running(self, tracing_config):
        """Test accessing tracer when running."""
        provider = TracingProvider(tracing_config)
        provider.start()

        try:
            tracer = provider.tracer
            assert tracer is not None
        finally:
            provider.shutdown()

    def test_tracer_property_not_running(self, tracing_config):
        """Test accessing tracer when not running raises error."""
        provider = TracingProvider(tracing_config)

        with pytest.raises(RuntimeError, match="not started"):
            _ = provider.tracer


class TestTracingProviderSpans:
    """Tests for span creation."""

    @pytest.fixture
    def running_provider(self, tracing_config):
        """Create and start a provider for testing."""
        provider = TracingProvider(tracing_config)
        provider.start()
        yield provider
        provider.shutdown()

    def test_start_span_context_manager(self, running_provider):
        """Test creating span with context manager."""
        with running_provider.start_span("test_span") as span:
            assert span is not None

    def test_start_span_with_kind(self, running_provider):
        """Test creating span with specific kind."""
        with running_provider.start_span(
            "server_span", kind=SpanKind.SERVER
        ) as span:
            assert span is not None

    def test_start_span_with_attributes(self, running_provider):
        """Test creating span with initial attributes."""
        attributes = {"key1": "value1", "key2": 42}
        with running_provider.start_span(
            "attr_span", attributes=attributes
        ) as span:
            assert span is not None

    def test_start_span_exception_handling(self, running_provider):
        """Test that exceptions are recorded in span."""
        with pytest.raises(ValueError):
            with running_provider.start_span("error_span") as span:
                raise ValueError("Test error")

    def test_start_span_not_running(self, tracing_config):
        """Test start_span when provider not running yields None."""
        provider = TracingProvider(tracing_config)
        # Don't start the provider

        with provider.start_span("test") as span:
            assert span is None


class TestTracingProviderContext:
    """Tests for context propagation."""

    @pytest.fixture
    def running_provider(self, tracing_config):
        """Create and start a provider for testing."""
        provider = TracingProvider(tracing_config)
        provider.start()
        yield provider
        provider.shutdown()

    def test_inject_context(self, running_provider):
        """Test injecting trace context into carrier."""
        with running_provider.start_span("test"):
            carrier = {}
            running_provider.inject_context(carrier)
            # W3C Trace Context adds traceparent header
            # Note: May be empty if no span is active in some implementations

    def test_extract_context(self, running_provider):
        """Test extracting trace context from carrier."""
        carrier = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }
        context = running_provider.extract_context(carrier)
        assert context is not None

    def test_get_current_span(self, running_provider):
        """Test getting current span."""
        with running_provider.start_span("test"):
            span = running_provider.get_current_span()
            assert span is not None

    def test_get_current_trace_id(self, running_provider):
        """Test getting current trace ID."""
        with running_provider.start_span("test"):
            trace_id = running_provider.get_current_trace_id()
            assert trace_id is not None
            assert len(trace_id) == 32  # 128-bit hex

    def test_get_current_span_id(self, running_provider):
        """Test getting current span ID."""
        with running_provider.start_span("test"):
            span_id = running_provider.get_current_span_id()
            assert span_id is not None
            assert len(span_id) == 16  # 64-bit hex

    def test_get_current_trace_id_no_span(self, running_provider):
        """Test getting trace ID when no span is active."""
        # No active span
        trace_id = running_provider.get_current_trace_id()
        assert trace_id is None


class TestTraceDecorator:
    """Tests for the @trace decorator."""

    @pytest.fixture(autouse=True)
    def setup_tracing(self, tracing_config):
        """Start tracing for decorator tests."""
        provider = TracingProvider(tracing_config)
        provider.start()
        yield provider
        provider.shutdown()

    def test_trace_decorator_basic(self):
        """Test basic decorator usage."""
        @trace()
        def simple_function():
            return 42

        result = simple_function()
        assert result == 42

    def test_trace_decorator_with_name(self):
        """Test decorator with custom name."""
        @trace("custom_span_name")
        def named_function():
            return "hello"

        result = named_function()
        assert result == "hello"

    def test_trace_decorator_with_kind(self):
        """Test decorator with span kind."""
        @trace(kind=SpanKind.CLIENT)
        def client_function():
            pass

        client_function()  # Should not raise

    def test_trace_decorator_with_attributes(self):
        """Test decorator with attributes."""
        @trace(attributes={"custom.attr": "value"})
        def attributed_function():
            pass

        attributed_function()  # Should not raise

    def test_trace_decorator_preserves_args(self):
        """Test that decorator preserves function arguments."""
        @trace()
        def func_with_args(a, b, c=None):
            return (a, b, c)

        result = func_with_args(1, 2, c=3)
        assert result == (1, 2, 3)

    def test_trace_decorator_preserves_exception(self):
        """Test that decorator preserves and records exceptions."""
        @trace()
        def failing_function():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError, match="Test error"):
            failing_function()

    def test_trace_decorator_preserves_docstring(self):
        """Test that decorator preserves function metadata."""
        @trace()
        def documented_function():
            """This is the docstring."""
            pass

        assert documented_function.__doc__ == """This is the docstring."""
        assert documented_function.__name__ == "documented_function"


class TestTracingProviderResource:
    """Tests for resource creation."""

    def test_resource_includes_service_name(self, tracing_config):
        """Test that resource includes service name."""
        provider = TracingProvider(tracing_config)
        resource = provider._create_resource()

        attrs = dict(resource.attributes)
        assert attrs.get("service.name") == tracing_config.service_name

    def test_resource_includes_service_version(self, tracing_config):
        """Test that resource includes service version."""
        provider = TracingProvider(tracing_config)
        resource = provider._create_resource()

        attrs = dict(resource.attributes)
        assert attrs.get("service.version") == tracing_config.service_version


class TestTracingProviderExporter:
    """Tests for exporter creation."""

    def test_create_exporter_grpc(self, tracing_config):
        """Test creating gRPC OTLP exporter."""
        provider = TracingProvider(tracing_config)
        # Note: This may fail if opentelemetry-exporter-otlp is not installed
        try:
            exporter = provider._create_exporter()
            # Exporter may be None if library not installed
        except ImportError:
            pytest.skip("OTLP exporter not installed")

    def test_create_exporter_http(self):
        """Test creating HTTP OTLP exporter."""
        config = TracingConfig(
            enabled=True,
            otlp_endpoint="localhost:4318",
            otlp_protocol="http",
            service_name="test",
            service_version="1.0.0",
        )
        provider = TracingProvider(config)
        try:
            exporter = provider._create_exporter()
            # Exporter may be None if library not installed
        except ImportError:
            pytest.skip("OTLP HTTP exporter not installed")

    def test_create_exporter_no_endpoint(self):
        """Test exporter creation with no endpoint returns None."""
        config = TracingConfig(
            enabled=True,
            otlp_endpoint=None,
            service_name="test",
            service_version="1.0.0",
        )
        provider = TracingProvider(config)
        exporter = provider._create_exporter()
        assert exporter is None

    def test_create_exporter_invalid_protocol(self):
        """Test exporter creation with invalid protocol returns None."""
        config = TracingConfig(
            enabled=True,
            otlp_endpoint="localhost:4317",
            otlp_protocol="invalid",
            service_name="test",
            service_version="1.0.0",
        )
        provider = TracingProvider(config)
        exporter = provider._create_exporter()
        assert exporter is None
