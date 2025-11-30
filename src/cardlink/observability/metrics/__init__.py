"""Metrics collection package for Prometheus.

This package provides comprehensive Prometheus metrics for CardLink,
including APDU operations, sessions, BIP connections, and system metrics.

Example:
    >>> from cardlink.observability.metrics import MetricsCollector
    >>> from cardlink.observability.config import MetricsConfig
    >>>
    >>> # Create collector
    >>> config = MetricsConfig(enabled=True, port=9090)
    >>> collector = MetricsCollector(config)
    >>> collector.start()
    >>>
    >>> # Record metrics
    >>> collector.record_apdu_command("SELECT", "physical")
    >>> collector.record_session_start("admin", "psk-tls")
    >>> collector.record_apdu_response(0x9000, 150)
"""

from cardlink.observability.metrics.collector import MetricsCollector
from cardlink.observability.metrics.registry import MetricsRegistry

__all__ = [
    "MetricsCollector",
    "MetricsRegistry",
]
