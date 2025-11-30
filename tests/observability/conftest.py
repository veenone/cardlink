"""Pytest fixtures for observability testing.

This module provides reusable fixtures for testing metrics, tracing,
health checks, and logging components with proper isolation.
"""

import os
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from cardlink.observability.config import (
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    TracingConfig,
)
from cardlink.observability.manager import get_observability, reset_observability
from cardlink.observability.metrics.collector import MetricsCollector
from cardlink.observability.metrics.registry import MetricsRegistry


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def metrics_config() -> MetricsConfig:
    """Create a test metrics configuration.

    Returns:
        MetricsConfig with test-appropriate defaults.
    """
    return MetricsConfig(
        enabled=True,
        port=19090,  # Use non-standard port to avoid conflicts
        path="/metrics",
        auth_username=None,
        auth_password=None,
        collection_interval=1,
    )


@pytest.fixture
def metrics_config_with_auth() -> MetricsConfig:
    """Create a metrics configuration with authentication enabled.

    Returns:
        MetricsConfig with Basic auth configured.
    """
    return MetricsConfig(
        enabled=True,
        port=19091,
        path="/metrics",
        auth_username="test_user",
        auth_password="test_pass",
        collection_interval=1,
    )


@pytest.fixture
def metrics_config_disabled() -> MetricsConfig:
    """Create a disabled metrics configuration.

    Returns:
        MetricsConfig with enabled=False.
    """
    return MetricsConfig(enabled=False)


@pytest.fixture
def tracing_config() -> TracingConfig:
    """Create a test tracing configuration.

    Returns:
        TracingConfig with test-appropriate defaults.
    """
    return TracingConfig(
        enabled=True,
        otlp_endpoint="localhost:4317",
        otlp_protocol="grpc",
        service_name="cardlink-test",
        service_version="1.0.0-test",
        sample_rate=1.0,
    )


@pytest.fixture
def tracing_config_disabled() -> TracingConfig:
    """Create a disabled tracing configuration.

    Returns:
        TracingConfig with enabled=False.
    """
    return TracingConfig(enabled=False)


@pytest.fixture
def health_config() -> HealthConfig:
    """Create a test health check configuration.

    Returns:
        HealthConfig with test-appropriate defaults.
    """
    return HealthConfig(
        enabled=True,
        port=18080,  # Non-standard port for tests
        check_timeout=2.0,
    )


@pytest.fixture
def health_config_disabled() -> HealthConfig:
    """Create a disabled health configuration.

    Returns:
        HealthConfig with enabled=False.
    """
    return HealthConfig(enabled=False)


@pytest.fixture
def logging_config() -> LoggingConfig:
    """Create a test logging configuration.

    Returns:
        LoggingConfig with test-appropriate defaults.
    """
    return LoggingConfig(
        level="DEBUG",
        format="json",
        trace_correlation=True,
        output_file=None,
    )


@pytest.fixture
def observability_config(
    metrics_config: MetricsConfig,
    tracing_config_disabled: TracingConfig,
    health_config_disabled: HealthConfig,
    logging_config: LoggingConfig,
) -> ObservabilityConfig:
    """Create a test observability configuration with metrics enabled.

    This fixture creates a minimal configuration suitable for unit tests
    where only metrics are enabled.

    Returns:
        ObservabilityConfig with metrics enabled, others disabled.
    """
    return ObservabilityConfig(
        metrics=metrics_config,
        tracing=tracing_config_disabled,
        health=health_config_disabled,
        logging=logging_config,
    )


@pytest.fixture
def observability_config_full(
    metrics_config: MetricsConfig,
    tracing_config: TracingConfig,
    health_config: HealthConfig,
    logging_config: LoggingConfig,
) -> ObservabilityConfig:
    """Create a fully-enabled observability configuration.

    Returns:
        ObservabilityConfig with all components enabled.
    """
    return ObservabilityConfig(
        metrics=metrics_config,
        tracing=tracing_config,
        health=health_config,
        logging=logging_config,
    )


@pytest.fixture
def observability_config_disabled() -> ObservabilityConfig:
    """Create an all-disabled observability configuration.

    Returns:
        ObservabilityConfig with all components disabled.
    """
    return ObservabilityConfig(
        metrics=MetricsConfig(enabled=False),
        tracing=TracingConfig(enabled=False),
        health=HealthConfig(enabled=False),
        logging=LoggingConfig(level="WARNING"),
    )


# =============================================================================
# Prometheus Registry Fixtures
# =============================================================================


@pytest.fixture
def isolated_registry() -> CollectorRegistry:
    """Create an isolated Prometheus CollectorRegistry.

    This fixture provides a fresh registry that doesn't share state
    with other tests, preventing metric collision errors.

    Returns:
        Fresh CollectorRegistry instance.
    """
    return CollectorRegistry()


@pytest.fixture
def metrics_registry(isolated_registry: CollectorRegistry) -> MetricsRegistry:
    """Create a MetricsRegistry with isolated Prometheus registry.

    This prevents metric name conflicts between tests.

    Returns:
        MetricsRegistry with isolated collector registry.
    """
    return MetricsRegistry(registry=isolated_registry)


# =============================================================================
# Component Fixtures
# =============================================================================


@pytest.fixture
def metrics_collector(metrics_config: MetricsConfig) -> Generator[MetricsCollector, None, None]:
    """Create a MetricsCollector for testing.

    This fixture provides a collector that is NOT started, allowing
    unit tests without HTTP server overhead.

    Yields:
        MetricsCollector instance (not started).
    """
    collector = MetricsCollector(metrics_config)
    yield collector
    # Cleanup: ensure collector is stopped if it was started
    if collector._running:
        collector.shutdown()


@pytest.fixture
def running_metrics_collector(
    metrics_config: MetricsConfig,
) -> Generator[MetricsCollector, None, None]:
    """Create and start a MetricsCollector for integration testing.

    Warning:
        This starts an HTTP server. Use sparingly and ensure proper cleanup.

    Yields:
        Started MetricsCollector instance.
    """
    collector = MetricsCollector(metrics_config)
    collector.start()
    yield collector
    collector.shutdown()


# =============================================================================
# Manager Fixtures
# =============================================================================


@pytest.fixture
def clean_observability() -> Generator[None, None, None]:
    """Ensure clean observability manager state for each test.

    This fixture resets the singleton before and after each test,
    ensuring complete isolation.

    Yields:
        None (side effect: cleans up observability manager).
    """
    # Reset before test
    reset_observability()
    yield
    # Reset after test
    obs = get_observability()
    if obs.is_initialized:
        obs.shutdown()
    reset_observability()


@pytest.fixture
def initialized_observability(
    clean_observability: None, observability_config: ObservabilityConfig
) -> Generator[None, None, None]:
    """Provide an initialized observability manager.

    This fixture initializes the global observability manager with
    metrics enabled for testing.

    Yields:
        None (side effect: initializes observability manager).
    """
    obs = get_observability()
    obs.initialize(observability_config)
    yield
    # Cleanup handled by clean_observability


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_tracer() -> MagicMock:
    """Create a mock tracer for testing tracing integration.

    Returns:
        MagicMock configured as a tracer with span context support.
    """
    tracer = MagicMock()

    # Configure span mock
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    span.set_attribute = MagicMock()
    span.set_status = MagicMock()
    span.record_exception = MagicMock()

    tracer.start_span = MagicMock(return_value=span)
    tracer.start_as_current_span = MagicMock(return_value=span)

    return tracer


@pytest.fixture
def mock_health_checker() -> MagicMock:
    """Create a mock health checker for testing.

    Returns:
        MagicMock configured as a health checker.
    """
    checker = MagicMock()
    checker.is_healthy = MagicMock(return_value=True)
    checker.run_check = MagicMock(return_value={"status": "healthy", "details": {}})
    checker.run_all_checks = MagicMock(
        return_value={
            "status": "healthy",
            "checks": {"database": "healthy", "server": "healthy"},
        }
    )
    return checker


@pytest.fixture
def mock_logger_manager() -> MagicMock:
    """Create a mock logger manager for testing.

    Returns:
        MagicMock configured as a logger manager.
    """
    manager = MagicMock()
    manager.get_logger = MagicMock(return_value=MagicMock())
    manager.configure = MagicMock()
    return manager


# =============================================================================
# Environment Variable Fixtures
# =============================================================================


@pytest.fixture
def env_metrics_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for metrics configuration.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    monkeypatch.setenv("GP_METRICS_ENABLED", "true")
    monkeypatch.setenv("GP_METRICS_PORT", "19092")
    monkeypatch.setenv("GP_METRICS_PATH", "/test-metrics")
    monkeypatch.setenv("GP_METRICS_AUTH_USERNAME", "env_user")
    monkeypatch.setenv("GP_METRICS_AUTH_PASSWORD", "env_pass")
    monkeypatch.setenv("GP_METRICS_INTERVAL", "30")


@pytest.fixture
def env_tracing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for tracing configuration.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    monkeypatch.setenv("GP_TRACING_ENABLED", "true")
    monkeypatch.setenv("GP_OTLP_ENDPOINT", "localhost:4318")
    monkeypatch.setenv("GP_OTLP_PROTOCOL", "http")
    monkeypatch.setenv("GP_SERVICE_NAME", "cardlink-env-test")
    monkeypatch.setenv("GP_SERVICE_VERSION", "2.0.0")
    monkeypatch.setenv("GP_TRACE_SAMPLE_RATE", "0.5")


@pytest.fixture
def env_health_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for health configuration.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    monkeypatch.setenv("GP_HEALTH_ENABLED", "true")
    monkeypatch.setenv("GP_HEALTH_PORT", "18081")
    monkeypatch.setenv("GP_HEALTH_TIMEOUT", "10.0")


@pytest.fixture
def env_logging_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for logging configuration.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    monkeypatch.setenv("GP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GP_LOG_FORMAT", "text")
    monkeypatch.setenv("GP_LOG_TRACE_CORRELATION", "false")
    monkeypatch.setenv("GP_LOG_FILE", "/tmp/test.log")


@pytest.fixture
def env_all_config(
    env_metrics_config: None,
    env_tracing_config: None,
    env_health_config: None,
    env_logging_config: None,
) -> None:
    """Set all observability environment variables.

    Args:
        env_metrics_config: Metrics env fixture.
        env_tracing_config: Tracing env fixture.
        env_health_config: Health env fixture.
        env_logging_config: Logging env fixture.
    """
    pass  # Composition fixture - just combines dependencies


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def free_port() -> int:
    """Get a free port for testing.

    Returns:
        Available TCP port number.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port
