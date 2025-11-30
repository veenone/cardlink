"""Tracing module for distributed tracing with OpenTelemetry.

This module provides distributed tracing capabilities using OpenTelemetry,
with support for OTLP export to Jaeger, Zipkin, or other OTLP-compatible backends.
"""

from cardlink.observability.tracing.provider import TracingProvider, trace

__all__ = ["TracingProvider", "trace"]
