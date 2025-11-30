"""Observability package for GP-OTA-Tester.

This package provides comprehensive observability capabilities including:
- Prometheus metrics collection and exposure
- OpenTelemetry distributed tracing
- Health check endpoints
- Structured JSON logging with trace correlation
- Grafana dashboard templates
- Prometheus alerting rules

Example:
    >>> from cardlink.observability import get_observability
    >>>
    >>> # Initialize observability
    >>> obs = get_observability()
    >>> obs.initialize()
    >>>
    >>> # Record metrics
    >>> obs.metrics.record_apdu_command("SELECT", "physical")
    >>>
    >>> # Create trace span
    >>> with obs.tracer.start_span("process_session") as span:
    ...     # Your code here
    ...     pass
    >>>
    >>> # Check health
    >>> health_status = obs.health.run_all_checks()
    >>>
    >>> # Log with context
    >>> logger = obs.logger.get_logger("my_component")
    >>> logger.info("Operation completed", session_id=123)
"""

from cardlink.observability.config import ObservabilityConfig
from cardlink.observability.manager import ObservabilityManager, get_observability

__all__ = [
    "ObservabilityConfig",
    "ObservabilityManager",
    "get_observability",
]
