"""Tracing provider for OpenTelemetry distributed tracing.

This module provides a TracingProvider class that manages OpenTelemetry
tracing with OTLP export support.
"""

import functools
import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional, TypeVar

from opentelemetry import trace as otel_trace
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer

from cardlink.observability.config import TracingConfig

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class TracingProvider:
    """OpenTelemetry tracing provider for CardLink.

    This class manages the OpenTelemetry tracer provider, span export,
    and provides convenient methods for creating spans.

    Example:
        >>> from cardlink.observability.config import TracingConfig
        >>> config = TracingConfig(
        ...     enabled=True,
        ...     otlp_endpoint="localhost:4317",
        ...     otlp_protocol="grpc",
        ...     service_name="cardlink",
        ...     service_version="1.0.0"
        ... )
        >>> provider = TracingProvider(config)
        >>> provider.start()
        >>>
        >>> # Create spans
        >>> with provider.start_span("process_apdu", kind=SpanKind.INTERNAL) as span:
        ...     span.set_attribute("apdu.command", "SELECT")
        ...     # Do work
        ...
        >>> provider.shutdown()
    """

    def __init__(self, config: TracingConfig) -> None:
        """Initialize tracing provider.

        Args:
            config: Tracing configuration.
        """
        self.config = config
        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[Tracer] = None
        self._span_processor: Optional[BatchSpanProcessor] = None
        self._running = False

    def start(self) -> None:
        """Start the tracing provider.

        This initializes the TracerProvider with resource attributes,
        configures the OTLP exporter, and sets up batch span processing.

        Example:
            >>> provider = TracingProvider(config)
            >>> provider.start()
        """
        if self._running:
            logger.warning("TracingProvider already running")
            return

        logger.info(
            f"Starting tracing provider with endpoint {self.config.otlp_endpoint}"
        )

        # Create resource with service attributes
        resource = self._create_resource()

        # Create tracer provider
        self._tracer_provider = TracerProvider(resource=resource)

        # Create and add span exporter
        exporter = self._create_exporter()
        if exporter:
            self._span_processor = BatchSpanProcessor(
                exporter,
                max_queue_size=2048,
                schedule_delay_millis=5000,
                max_export_batch_size=512,
            )
            self._tracer_provider.add_span_processor(self._span_processor)

        # Set as global tracer provider
        otel_trace.set_tracer_provider(self._tracer_provider)

        # Get tracer instance
        self._tracer = self._tracer_provider.get_tracer(
            self.config.service_name,
            self.config.service_version,
        )

        self._running = True
        logger.info("Tracing provider started")

    def shutdown(self) -> None:
        """Shutdown the tracing provider gracefully.

        This flushes any pending spans and shuts down the span processor.

        Example:
            >>> provider.shutdown()
        """
        if not self._running:
            return

        logger.info("Shutting down tracing provider")

        if self._span_processor:
            try:
                self._span_processor.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down span processor: {e}")

        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down tracer provider: {e}")

        self._running = False
        logger.info("Tracing provider stopped")

    def _create_resource(self) -> Resource:
        """Create OpenTelemetry resource with service attributes.

        Returns:
            Resource with service name, version, and environment.
        """
        return Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.language": "python",
            }
        )

    def _create_exporter(self) -> Optional[SpanExporter]:
        """Create OTLP span exporter based on configuration.

        Returns:
            SpanExporter for OTLP, or None if creation fails.
        """
        if not self.config.otlp_endpoint:
            logger.warning("No OTLP endpoint configured, traces will not be exported")
            return None

        try:
            if self.config.otlp_protocol == "grpc":
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                return OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    insecure=True,  # TODO: Add TLS configuration
                )
            elif self.config.otlp_protocol == "http":
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                # HTTP endpoint typically needs /v1/traces suffix
                endpoint = self.config.otlp_endpoint
                if not endpoint.endswith("/v1/traces"):
                    endpoint = f"http://{endpoint}/v1/traces"

                return OTLPSpanExporter(endpoint=endpoint)
            else:
                logger.error(f"Unknown OTLP protocol: {self.config.otlp_protocol}")
                return None

        except ImportError as e:
            logger.error(f"Failed to import OTLP exporter: {e}")
            logger.info("Install opentelemetry-exporter-otlp for OTLP export support")
            return None
        except Exception as e:
            logger.error(f"Failed to create OTLP exporter: {e}")
            return None

    @property
    def tracer(self) -> Tracer:
        """Get the OpenTelemetry tracer.

        Returns:
            Tracer instance.

        Raises:
            RuntimeError: If provider not started.
        """
        if not self._running or not self._tracer:
            raise RuntimeError("TracingProvider not started")
        return self._tracer

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Any]:
        """Create a new span as a context manager.

        Args:
            name: Span name.
            kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER).
            attributes: Initial span attributes.

        Yields:
            The active span.

        Example:
            >>> with provider.start_span("process_command", kind=SpanKind.SERVER) as span:
            ...     span.set_attribute("command.type", "SELECT")
            ...     # Process command
        """
        if not self._running or not self._tracer:
            # Return no-op context if not running
            yield None
            return

        with self._tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes,
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def inject_context(self, carrier: Dict[str, str]) -> None:
        """Inject current trace context into a carrier (e.g., HTTP headers).

        This implements W3C Trace Context propagation for distributed tracing.

        Args:
            carrier: Dictionary to inject context into.

        Example:
            >>> headers = {}
            >>> provider.inject_context(headers)
            >>> # headers now contains traceparent, tracestate
            >>> requests.get("http://service/api", headers=headers)
        """
        inject(carrier)

    def extract_context(self, carrier: Dict[str, str]) -> Any:
        """Extract trace context from a carrier (e.g., HTTP headers).

        This extracts W3C Trace Context for continuing distributed traces.

        Args:
            carrier: Dictionary containing context headers.

        Returns:
            Extracted context.

        Example:
            >>> context = provider.extract_context(request.headers)
            >>> with provider.start_span("handle_request", context=context):
            ...     # Handle request as part of distributed trace
        """
        return extract(carrier)

    def get_current_span(self) -> Any:
        """Get the currently active span.

        Returns:
            Current span, or None if no span is active.
        """
        return otel_trace.get_current_span()

    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID as a hex string.

        Returns:
            Trace ID string, or None if no span is active.

        Example:
            >>> trace_id = provider.get_current_trace_id()
            >>> logger.info(f"Processing request", extra={"trace_id": trace_id})
        """
        span = self.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None

    def get_current_span_id(self) -> Optional[str]:
        """Get the current span ID as a hex string.

        Returns:
            Span ID string, or None if no span is active.
        """
        span = self.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
        return None

    @property
    def is_running(self) -> bool:
        """Check if provider is running.

        Returns:
            True if running, False otherwise.
        """
        return self._running


def trace(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator for automatic function tracing.

    This decorator creates a span for each function call, automatically
    recording exceptions and setting span status.

    Args:
        name: Span name (defaults to function name).
        kind: Span kind.
        attributes: Additional span attributes.

    Returns:
        Decorated function.

    Example:
        >>> @trace("process_apdu", kind=SpanKind.INTERNAL)
        ... def process_apdu(apdu: bytes) -> bytes:
        ...     # Process APDU command
        ...     return response
        >>>
        >>> @trace()  # Uses function name as span name
        ... def another_function():
        ...     pass
    """

    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current tracer
            tracer = otel_trace.get_tracer(__name__)

            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes,
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper  # type: ignore

    return decorator
