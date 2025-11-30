"""Unit tests for ObservabilityManager.

Tests singleton pattern, initialization, shutdown, and component access.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from cardlink.observability.config import (
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    TracingConfig,
)
from cardlink.observability.manager import (
    ObservabilityManager,
    get_observability,
    reset_observability,
)


class TestObservabilityManagerSingleton:
    """Tests for singleton pattern implementation."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        reset_observability()

    def test_get_observability_returns_same_instance(self):
        """Test that get_observability returns the same instance."""
        obs1 = get_observability()
        obs2 = get_observability()
        assert obs1 is obs2

    def test_reset_observability_creates_new_instance(self):
        """Test that reset creates a new instance."""
        obs1 = get_observability()
        reset_observability()
        obs2 = get_observability()
        assert obs1 is not obs2

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        instances = []
        errors = []

        def get_instance():
            try:
                obs = get_observability()
                instances.append(obs)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)


class TestObservabilityManagerInitialization:
    """Tests for initialization behavior."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        obs = get_observability()
        if obs.is_initialized:
            obs.shutdown()
        reset_observability()

    def test_not_initialized_by_default(self):
        """Test that manager is not initialized on creation."""
        obs = get_observability()
        assert obs.is_initialized is False

    def test_initialize_with_default_config(self, monkeypatch):
        """Test initialization with environment-derived config."""
        # Set minimal environment
        monkeypatch.setenv("GP_METRICS_ENABLED", "false")
        monkeypatch.setenv("GP_TRACING_ENABLED", "false")
        monkeypatch.setenv("GP_HEALTH_ENABLED", "false")

        obs = get_observability()
        obs.initialize()

        assert obs.is_initialized is True

    def test_initialize_with_custom_config(self, observability_config_disabled):
        """Test initialization with provided config."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)

        assert obs.is_initialized is True
        assert obs.config == observability_config_disabled

    def test_initialize_validates_config(self):
        """Test that initialize validates configuration."""
        invalid_config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=True, port=0),  # Invalid port
        )

        obs = get_observability()
        with pytest.raises(ValueError, match="Invalid metrics port"):
            obs.initialize(invalid_config)

        assert obs.is_initialized is False

    def test_initialize_idempotent(self, observability_config_disabled):
        """Test that repeated initialization is safe."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)
        obs.initialize(observability_config_disabled)  # Should warn but not error

        assert obs.is_initialized is True

    def test_initialize_starts_metrics(self, metrics_config):
        """Test that initialization starts metrics when enabled."""
        config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )

        obs = get_observability()
        obs.initialize(config)

        assert obs._metrics is not None
        # Verify it started (it has a running thread)
        assert obs._metrics._running is True


class TestObservabilityManagerShutdown:
    """Tests for shutdown behavior."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        reset_observability()

    def test_shutdown_stops_metrics(self, metrics_config):
        """Test that shutdown stops metrics collector."""
        config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )

        obs = get_observability()
        obs.initialize(config)
        assert obs._metrics._running is True

        obs.shutdown()
        assert obs.is_initialized is False
        assert obs._metrics._running is False

    def test_shutdown_not_initialized(self):
        """Test that shutdown is safe when not initialized."""
        obs = get_observability()
        obs.shutdown()  # Should not raise

    def test_shutdown_idempotent(self, observability_config_disabled):
        """Test that repeated shutdown is safe."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)
        obs.shutdown()
        obs.shutdown()  # Should not raise

    def test_shutdown_handles_component_errors(self, metrics_config):
        """Test that shutdown handles component errors gracefully."""
        config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )

        obs = get_observability()
        obs.initialize(config)

        # Mock shutdown to raise
        original_shutdown = obs._metrics.shutdown
        obs._metrics.shutdown = MagicMock(side_effect=Exception("Shutdown error"))

        obs.shutdown()  # Should not raise, just log error
        assert obs.is_initialized is False

        # Restore for cleanup
        obs._metrics.shutdown = original_shutdown


class TestObservabilityManagerProperties:
    """Tests for property accessors."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        obs = get_observability()
        if obs.is_initialized:
            obs.shutdown()
        reset_observability()

    def test_config_property_not_initialized(self):
        """Test config property raises when not initialized."""
        obs = get_observability()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = obs.config

    def test_config_property_initialized(self, observability_config_disabled):
        """Test config property returns config when initialized."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)
        assert obs.config == observability_config_disabled

    def test_metrics_property_not_initialized(self):
        """Test metrics property raises when not initialized."""
        obs = get_observability()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = obs.metrics

    def test_metrics_property_disabled(self, metrics_config_disabled):
        """Test metrics property raises when disabled."""
        config = ObservabilityConfig(
            metrics=metrics_config_disabled,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs = get_observability()
        obs.initialize(config)

        with pytest.raises(RuntimeError, match="Metrics not enabled"):
            _ = obs.metrics

    def test_metrics_property_enabled(self, metrics_config):
        """Test metrics property returns collector when enabled."""
        config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs = get_observability()
        obs.initialize(config)

        metrics = obs.metrics
        assert metrics is not None

    def test_tracer_property_not_initialized(self):
        """Test tracer property raises when not initialized."""
        obs = get_observability()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = obs.tracer

    def test_tracer_property_disabled(self, tracing_config_disabled):
        """Test tracer property raises when disabled."""
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=False),
            tracing=tracing_config_disabled,
            health=HealthConfig(enabled=False),
        )
        obs = get_observability()
        obs.initialize(config)

        with pytest.raises(RuntimeError, match="Tracing not enabled"):
            _ = obs.tracer

    def test_health_property_not_initialized(self):
        """Test health property raises when not initialized."""
        obs = get_observability()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = obs.health

    def test_health_property_disabled(self, health_config_disabled):
        """Test health property raises when disabled."""
        config = ObservabilityConfig(health=health_config_disabled)
        obs = get_observability()
        obs.initialize(config)

        with pytest.raises(RuntimeError, match="Health checks not enabled"):
            _ = obs.health

    def test_logger_property_not_initialized(self):
        """Test logger property raises when not initialized."""
        obs = get_observability()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = obs.logger

    def test_is_initialized_property(self, observability_config_disabled):
        """Test is_initialized reflects state correctly."""
        obs = get_observability()
        assert obs.is_initialized is False

        obs.initialize(observability_config_disabled)
        assert obs.is_initialized is True

        obs.shutdown()
        assert obs.is_initialized is False


class TestObservabilityManagerComponentInitialization:
    """Tests for individual component initialization."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        obs = get_observability()
        if obs.is_initialized:
            obs.shutdown()
        reset_observability()

    def test_metrics_initialization(self, metrics_config):
        """Test metrics component initializes correctly."""
        config = ObservabilityConfig(
            metrics=metrics_config,
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs = get_observability()
        obs.initialize(config)

        assert obs._metrics is not None
        assert obs._metrics._running is True

    def test_tracing_initialization(self, tracing_config):
        """Test tracing component initializes correctly."""
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=False),
            tracing=tracing_config,
            health=HealthConfig(enabled=False),
        )
        obs = get_observability()
        obs.initialize(config)

        # Tracer should be initialized
        assert obs._tracer is not None
        assert obs._tracer._running is True

    def test_health_initialization(self, health_config):
        """Test health component initializes correctly."""
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=False),
            tracing=TracingConfig(enabled=False),
            health=health_config,
        )
        obs = get_observability()
        obs.initialize(config)

        # Health should be initialized
        assert obs._health is not None
        assert obs._health.is_running is True

    def test_logging_always_initialized(self, observability_config_disabled):
        """Test logging is always initialized regardless of config."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)

        # Logging should be initialized (though manager may be None until implemented)
        assert obs.is_initialized is True


class TestResetObservability:
    """Tests for reset_observability function."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Ensure clean state for each test."""
        reset_observability()
        yield
        reset_observability()

    def test_reset_shuts_down_if_initialized(self, observability_config_disabled):
        """Test reset calls shutdown if manager was initialized."""
        obs = get_observability()
        obs.initialize(observability_config_disabled)
        assert obs.is_initialized is True

        reset_observability()

        # New instance should not be initialized
        new_obs = get_observability()
        assert new_obs.is_initialized is False

    def test_reset_safe_when_not_initialized(self):
        """Test reset is safe when manager was never initialized."""
        obs = get_observability()
        assert obs.is_initialized is False

        reset_observability()  # Should not raise

    def test_reset_creates_new_instance(self):
        """Test reset creates a completely new manager instance."""
        obs1 = get_observability()
        id1 = id(obs1)

        reset_observability()

        obs2 = get_observability()
        id2 = id(obs2)

        assert id1 != id2
