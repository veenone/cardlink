"""Tests for metrics collection."""

import pytest
from prometheus_client import CollectorRegistry

from cardlink.observability.config import (
    HealthConfig,
    MetricsConfig,
    ObservabilityConfig,
    TracingConfig,
)
from cardlink.observability.manager import get_observability, reset_observability
from cardlink.observability.metrics.collector import MetricsCollector
from cardlink.observability.metrics.registry import MetricsRegistry


class TestMetricsRegistry:
    """Tests for MetricsRegistry."""

    @pytest.fixture
    def isolated_prometheus_registry(self):
        """Create isolated Prometheus registry for each test."""
        return CollectorRegistry()

    def test_registry_creation(self, isolated_prometheus_registry):
        """Test creating metrics registry."""
        registry = MetricsRegistry(registry=isolated_prometheus_registry)
        assert registry is not None

    def test_all_metrics_exist(self, isolated_prometheus_registry):
        """Test that all expected metrics are registered."""
        registry = MetricsRegistry(registry=isolated_prometheus_registry)
        metrics = registry.get_all_metrics()

        # Check APDU metrics
        assert "apdu_commands_total" in metrics
        assert "apdu_responses_total" in metrics
        assert "apdu_errors_total" in metrics
        assert "apdu_response_time_seconds" in metrics
        assert "apdu_data_bytes" in metrics

        # Check session metrics
        assert "active_sessions" in metrics
        assert "session_duration_seconds" in metrics
        assert "sessions_total" in metrics

        # Check BIP metrics
        assert "bip_connections_active" in metrics
        assert "bip_bytes_transferred_total" in metrics

        # Check system metrics
        assert "system_cpu_usage_percent" in metrics
        assert "system_memory_usage_bytes" in metrics

        # Check database metrics
        assert "database_connections_active" in metrics
        assert "database_query_duration_seconds" in metrics


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.fixture
    def config(self):
        """Create test metrics config."""
        return MetricsConfig(
            enabled=True,
            port=19090,  # Use different port for tests
            path="/metrics",
            collection_interval=1,
        )

    @pytest.fixture
    def collector(self, config):
        """Create test metrics collector."""
        return MetricsCollector(config)

    def test_collector_creation(self, collector):
        """Test creating metrics collector."""
        assert collector is not None
        assert collector.registry is not None

    def test_record_apdu_command(self, collector):
        """Test recording APDU commands."""
        # Record some commands
        collector.record_apdu_command("SELECT", "physical")
        collector.record_apdu_command("GET_DATA", "logical")

        # Verify metrics were recorded
        metrics = collector.registry.apdu_commands_total
        assert metrics.labels(command="SELECT", interface="physical")._value._value == 1
        assert metrics.labels(command="GET_DATA", interface="logical")._value._value == 1

    def test_record_apdu_response(self, collector):
        """Test recording APDU responses."""
        collector.record_apdu_response(0x9000, 150, True)
        collector.record_apdu_response(0x6A82, 0, False)

        # Verify metrics
        metrics = collector.registry.apdu_responses_total
        assert metrics.labels(status_word="0x9000", success="True")._value._value == 1
        assert metrics.labels(status_word="0x6A82", success="False")._value._value == 1

    def test_time_apdu_command(self, collector):
        """Test timing APDU commands."""
        import time

        with collector.time_apdu_command("SELECT"):
            time.sleep(0.01)  # Simulate command execution

        # Verify histogram was updated
        metrics = collector.registry.apdu_response_time_seconds
        assert metrics.labels(command="SELECT")._sum._value > 0

    def test_session_tracking(self, collector):
        """Test session lifecycle tracking."""
        # Start session
        collector.record_session_start("admin", "psk-tls")
        assert (
            collector.registry.active_sessions.labels(session_type="admin")._value._value
            == 1
        )

        # End session
        collector.record_session_end("admin", 45.5, "completed")
        assert (
            collector.registry.active_sessions.labels(session_type="admin")._value._value
            == 0
        )

    def test_bip_connection_tracking(self, collector):
        """Test BIP connection tracking."""
        # Open connection
        collector.record_bip_connection_open("tcp")
        assert (
            collector.registry.bip_connections_active.labels(bearer_type="tcp")
            ._value._value
            == 1
        )

        # Transfer data
        collector.record_bip_data_transfer("sent", 1024, "tcp")
        assert (
            collector.registry.bip_bytes_transferred_total.labels(
                direction="sent", bearer_type="tcp"
            )._value._value
            == 1024
        )

        # Close connection
        collector.record_bip_connection_close("tcp", 120.5, "normal")
        assert (
            collector.registry.bip_connections_active.labels(bearer_type="tcp")
            ._value._value
            == 0
        )

    def test_database_metrics(self, collector):
        """Test database metrics."""
        # Test connection tracking
        collector.record_database_connection_change(1)
        assert collector.registry.database_connections_active._value._value == 1

        collector.record_database_connection_change(-1)
        assert collector.registry.database_connections_active._value._value == 0

        # Test query timing
        with collector.time_database_query("select", "sessions"):
            pass  # Simulate query

        # Verify metrics
        assert (
            collector.registry.database_operations_total.labels(
                operation="select", table="sessions", status="success"
            )._value._value
            == 1
        )


class TestObservabilityManager:
    """Tests for ObservabilityManager."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up observability manager after each test."""
        yield
        obs = get_observability()
        if obs.is_initialized:
            obs.shutdown()
        reset_observability()

    def test_get_singleton(self):
        """Test getting singleton instance."""
        obs1 = get_observability()
        obs2 = get_observability()
        assert obs1 is obs2

    def test_initialization(self):
        """Test initialization."""
        obs = get_observability()
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=True, port=19090),
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs.initialize(config)

        assert obs.is_initialized
        assert obs.config == config

    def test_metrics_property(self):
        """Test accessing metrics property."""
        obs = get_observability()
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=True, port=19091),
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs.initialize(config)

        # Should not raise error
        metrics = obs.metrics
        assert metrics is not None

    def test_metrics_disabled_error(self):
        """Test error when accessing disabled metrics."""
        obs = get_observability()
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=False),
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs.initialize(config)

        with pytest.raises(RuntimeError, match="Metrics not enabled"):
            _ = obs.metrics

    def test_shutdown(self):
        """Test shutdown."""
        obs = get_observability()
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=True, port=19092),
            tracing=TracingConfig(enabled=False),
            health=HealthConfig(enabled=False),
        )
        obs.initialize(config)
        obs.shutdown()

        assert not obs.is_initialized
