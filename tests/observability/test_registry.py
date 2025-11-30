"""Unit tests for MetricsRegistry.

Tests metric definitions, labels, and registry isolation.
"""

import pytest
from prometheus_client import CollectorRegistry

from cardlink.observability.metrics.registry import MetricsRegistry


class TestMetricsRegistryCreation:
    """Tests for MetricsRegistry initialization."""

    def test_create_with_default_registry(self):
        """Test creating registry with default Prometheus registry."""
        registry = MetricsRegistry()
        assert registry is not None
        assert registry.registry is not None

    def test_create_with_custom_registry(self, isolated_registry):
        """Test creating registry with custom Prometheus registry."""
        registry = MetricsRegistry(registry=isolated_registry)
        assert registry.registry is isolated_registry

    def test_all_metrics_created(self, metrics_registry):
        """Test that all expected metrics are created."""
        metrics = metrics_registry.get_all_metrics()

        # APDU metrics
        assert "apdu_commands_total" in metrics
        assert "apdu_responses_total" in metrics
        assert "apdu_errors_total" in metrics
        assert "apdu_response_time_seconds" in metrics
        assert "apdu_data_bytes" in metrics

        # Session metrics
        assert "active_sessions" in metrics
        assert "session_duration_seconds" in metrics
        assert "session_errors_total" in metrics
        assert "sessions_total" in metrics

        # BIP metrics
        assert "bip_connections_active" in metrics
        assert "bip_bytes_transferred_total" in metrics
        assert "bip_connection_duration_seconds" in metrics
        assert "bip_errors_total" in metrics

        # TLS metrics
        assert "tls_handshakes_total" in metrics
        assert "tls_handshake_duration_seconds" in metrics
        assert "tls_connections_active" in metrics
        assert "tls_errors_total" in metrics

        # Device metrics
        assert "devices_connected" in metrics
        assert "device_errors_total" in metrics
        assert "at_command_duration_seconds" in metrics
        assert "adb_operation_duration_seconds" in metrics
        assert "device_operations_total" in metrics

        # Test metrics
        assert "test_results_total" in metrics
        assert "test_duration_seconds" in metrics
        assert "test_suite_duration_seconds" in metrics
        assert "tests_running" in metrics

        # System metrics
        assert "system_cpu_usage_percent" in metrics
        assert "system_memory_usage_bytes" in metrics
        assert "system_disk_usage_bytes" in metrics
        assert "system_network_bytes_total" in metrics
        assert "system_process_uptime_seconds" in metrics
        assert "system_threads_active" in metrics

        # Database metrics
        assert "database_connections_active" in metrics
        assert "database_query_duration_seconds" in metrics
        assert "database_operations_total" in metrics
        assert "database_errors_total" in metrics

        # Info metrics
        assert "application_info" in metrics

    def test_metrics_count(self, metrics_registry):
        """Test the total number of metrics."""
        metrics = metrics_registry.get_all_metrics()
        # 5 APDU + 4 Session + 4 BIP + 4 TLS + 5 Device + 4 Test + 6 System + 4 Database + 1 Info = 37
        assert len(metrics) == 37


class TestAPDUMetrics:
    """Tests for APDU-related metrics."""

    def test_apdu_commands_total_counter(self, metrics_registry):
        """Test APDU commands counter."""
        counter = metrics_registry.apdu_commands_total
        # prometheus_client stores base name without _total suffix
        assert "cardlink_apdu_commands" in counter._name

        # Test incrementing with labels
        counter.labels(command="SELECT", interface="physical").inc()
        assert counter.labels(command="SELECT", interface="physical")._value._value == 1

        counter.labels(command="SELECT", interface="physical").inc(5)
        assert counter.labels(command="SELECT", interface="physical")._value._value == 6

    def test_apdu_commands_labels(self, metrics_registry):
        """Test APDU commands counter labels."""
        counter = metrics_registry.apdu_commands_total

        # Different labels create different series
        counter.labels(command="SELECT", interface="physical").inc()
        counter.labels(command="GET_DATA", interface="logical").inc()

        assert counter.labels(command="SELECT", interface="physical")._value._value == 1
        assert counter.labels(command="GET_DATA", interface="logical")._value._value == 1

    def test_apdu_responses_total_counter(self, metrics_registry):
        """Test APDU responses counter."""
        counter = metrics_registry.apdu_responses_total

        counter.labels(status_word="0x9000", success="True").inc()
        counter.labels(status_word="0x6A82", success="False").inc()

        assert counter.labels(status_word="0x9000", success="True")._value._value == 1
        assert counter.labels(status_word="0x6A82", success="False")._value._value == 1

    def test_apdu_errors_total_counter(self, metrics_registry):
        """Test APDU errors counter."""
        counter = metrics_registry.apdu_errors_total

        counter.labels(error_type="timeout", command="SELECT").inc()
        counter.labels(error_type="connection_lost", command="GET_DATA").inc(3)

        assert counter.labels(error_type="timeout", command="SELECT")._value._value == 1
        assert counter.labels(error_type="connection_lost", command="GET_DATA")._value._value == 3

    def test_apdu_response_time_histogram(self, metrics_registry):
        """Test APDU response time histogram."""
        histogram = metrics_registry.apdu_response_time_seconds

        # Observe some values
        histogram.labels(command="SELECT").observe(0.05)
        histogram.labels(command="SELECT").observe(0.15)
        histogram.labels(command="GET_DATA").observe(0.01)

        # Sum should be total of observed values
        assert histogram.labels(command="SELECT")._sum._value == pytest.approx(0.20)
        assert histogram.labels(command="GET_DATA")._sum._value == pytest.approx(0.01)

    def test_apdu_data_bytes_histogram(self, metrics_registry):
        """Test APDU data bytes histogram."""
        histogram = metrics_registry.apdu_data_bytes

        histogram.labels(direction="sent").observe(128)
        histogram.labels(direction="received").observe(256)

        assert histogram.labels(direction="sent")._sum._value == 128
        assert histogram.labels(direction="received")._sum._value == 256


class TestSessionMetrics:
    """Tests for session-related metrics."""

    def test_active_sessions_gauge(self, metrics_registry):
        """Test active sessions gauge."""
        gauge = metrics_registry.active_sessions

        # Increment and decrement
        gauge.labels(session_type="admin").inc()
        assert gauge.labels(session_type="admin")._value._value == 1

        gauge.labels(session_type="admin").dec()
        assert gauge.labels(session_type="admin")._value._value == 0

    def test_session_duration_histogram(self, metrics_registry):
        """Test session duration histogram."""
        histogram = metrics_registry.session_duration_seconds

        histogram.labels(session_type="admin", status="completed").observe(45.5)
        histogram.labels(session_type="data", status="timeout").observe(300.0)

        assert histogram.labels(session_type="admin", status="completed")._sum._value == 45.5
        assert histogram.labels(session_type="data", status="timeout")._sum._value == 300.0

    def test_session_errors_counter(self, metrics_registry):
        """Test session errors counter."""
        counter = metrics_registry.session_errors_total

        counter.labels(session_type="admin", error_type="auth_failed").inc()
        assert counter.labels(session_type="admin", error_type="auth_failed")._value._value == 1

    def test_sessions_total_counter(self, metrics_registry):
        """Test sessions total counter."""
        counter = metrics_registry.sessions_total

        counter.labels(session_type="admin", protocol="psk-tls").inc()
        counter.labels(session_type="data", protocol="http").inc(5)

        assert counter.labels(session_type="admin", protocol="psk-tls")._value._value == 1
        assert counter.labels(session_type="data", protocol="http")._value._value == 5


class TestBIPMetrics:
    """Tests for BIP-related metrics."""

    def test_bip_connections_active_gauge(self, metrics_registry):
        """Test BIP connections gauge."""
        gauge = metrics_registry.bip_connections_active

        gauge.labels(bearer_type="tcp").inc()
        gauge.labels(bearer_type="tcp").inc()
        gauge.labels(bearer_type="udp").inc()

        assert gauge.labels(bearer_type="tcp")._value._value == 2
        assert gauge.labels(bearer_type="udp")._value._value == 1

    def test_bip_bytes_transferred_counter(self, metrics_registry):
        """Test BIP bytes transferred counter."""
        counter = metrics_registry.bip_bytes_transferred_total

        counter.labels(direction="sent", bearer_type="tcp").inc(1024)
        counter.labels(direction="received", bearer_type="tcp").inc(2048)

        assert counter.labels(direction="sent", bearer_type="tcp")._value._value == 1024
        assert counter.labels(direction="received", bearer_type="tcp")._value._value == 2048

    def test_bip_connection_duration_histogram(self, metrics_registry):
        """Test BIP connection duration histogram."""
        histogram = metrics_registry.bip_connection_duration_seconds

        histogram.labels(bearer_type="tcp", status="normal").observe(120.5)
        histogram.labels(bearer_type="tcp", status="error").observe(5.0)

        assert histogram.labels(bearer_type="tcp", status="normal")._sum._value == 120.5
        assert histogram.labels(bearer_type="tcp", status="error")._sum._value == 5.0

    def test_bip_errors_counter(self, metrics_registry):
        """Test BIP errors counter."""
        counter = metrics_registry.bip_errors_total

        counter.labels(error_type="connection_refused", bearer_type="tcp").inc()
        counter.labels(error_type="timeout", bearer_type="tcp").inc(3)

        assert counter.labels(error_type="connection_refused", bearer_type="tcp")._value._value == 1
        assert counter.labels(error_type="timeout", bearer_type="tcp")._value._value == 3


class TestSystemMetrics:
    """Tests for system-related metrics."""

    def test_cpu_usage_gauge(self, metrics_registry):
        """Test CPU usage gauge."""
        gauge = metrics_registry.system_cpu_usage_percent
        gauge.set(45.5)
        assert gauge._value._value == 45.5

    def test_memory_usage_gauge(self, metrics_registry):
        """Test memory usage gauge."""
        gauge = metrics_registry.system_memory_usage_bytes
        gauge.set(1024 * 1024 * 512)  # 512 MB
        assert gauge._value._value == 1024 * 1024 * 512

    def test_disk_usage_gauge(self, metrics_registry):
        """Test disk usage gauge with path label."""
        gauge = metrics_registry.system_disk_usage_bytes
        gauge.labels(path="/").set(1024 * 1024 * 1024 * 100)  # 100 GB
        assert gauge.labels(path="/")._value._value == 1024 * 1024 * 1024 * 100

    def test_network_bytes_counter(self, metrics_registry):
        """Test network bytes counter."""
        counter = metrics_registry.system_network_bytes_total

        counter.labels(direction="sent", interface="eth0").inc(1000000)
        counter.labels(direction="received", interface="eth0").inc(5000000)

        assert counter.labels(direction="sent", interface="eth0")._value._value == 1000000
        assert counter.labels(direction="received", interface="eth0")._value._value == 5000000

    def test_process_uptime_gauge(self, metrics_registry):
        """Test process uptime gauge."""
        gauge = metrics_registry.system_process_uptime_seconds
        gauge.set(3600)  # 1 hour
        assert gauge._value._value == 3600

    def test_threads_active_gauge(self, metrics_registry):
        """Test active threads gauge."""
        gauge = metrics_registry.system_threads_active
        gauge.set(10)
        assert gauge._value._value == 10


class TestDatabaseMetrics:
    """Tests for database-related metrics."""

    def test_database_connections_gauge(self, metrics_registry):
        """Test database connections gauge."""
        gauge = metrics_registry.database_connections_active
        gauge.set(5)
        assert gauge._value._value == 5

        gauge.inc()
        assert gauge._value._value == 6

        gauge.dec(2)
        assert gauge._value._value == 4

    def test_database_query_duration_histogram(self, metrics_registry):
        """Test database query duration histogram."""
        histogram = metrics_registry.database_query_duration_seconds

        histogram.labels(operation="select", table="sessions").observe(0.05)
        histogram.labels(operation="insert", table="logs").observe(0.1)

        assert histogram.labels(operation="select", table="sessions")._sum._value == 0.05
        assert histogram.labels(operation="insert", table="logs")._sum._value == 0.1

    def test_database_operations_counter(self, metrics_registry):
        """Test database operations counter."""
        counter = metrics_registry.database_operations_total

        counter.labels(operation="select", table="sessions", status="success").inc()
        counter.labels(operation="insert", table="logs", status="success").inc(10)
        counter.labels(operation="update", table="devices", status="error").inc()

        assert counter.labels(operation="select", table="sessions", status="success")._value._value == 1
        assert counter.labels(operation="insert", table="logs", status="success")._value._value == 10
        assert counter.labels(operation="update", table="devices", status="error")._value._value == 1

    def test_database_errors_counter(self, metrics_registry):
        """Test database errors counter."""
        counter = metrics_registry.database_errors_total

        counter.labels(error_type="connection_lost", operation="select").inc()
        counter.labels(error_type="query_timeout", operation="insert").inc(2)

        assert counter.labels(error_type="connection_lost", operation="select")._value._value == 1
        assert counter.labels(error_type="query_timeout", operation="insert")._value._value == 2


class TestInfoMetrics:
    """Tests for informational metrics."""

    def test_application_info(self, metrics_registry):
        """Test application info metric."""
        info = metrics_registry.application_info

        # Info metric should exist and be the correct type
        assert info is not None
        assert "cardlink_application" in info._name


class TestMetricsRegistryIsolation:
    """Tests for registry isolation between instances."""

    def test_separate_registries_are_independent(self):
        """Test that separate registries don't share state."""
        reg1 = CollectorRegistry()
        reg2 = CollectorRegistry()

        registry1 = MetricsRegistry(registry=reg1)
        registry2 = MetricsRegistry(registry=reg2)

        # Increment in one registry
        registry1.apdu_commands_total.labels(command="SELECT", interface="physical").inc()

        # Should not affect other registry
        assert registry1.apdu_commands_total.labels(command="SELECT", interface="physical")._value._value == 1
        # registry2 starts fresh
        assert registry2.apdu_commands_total.labels(command="SELECT", interface="physical")._value._value == 0

    def test_fixture_isolation(self, metrics_registry):
        """Test that fixture provides isolated registry."""
        # Increment a counter
        metrics_registry.apdu_commands_total.labels(command="TEST", interface="test").inc(100)
        assert metrics_registry.apdu_commands_total.labels(command="TEST", interface="test")._value._value == 100

    def test_fixture_isolation_subsequent(self, metrics_registry):
        """Test that each test gets fresh registry."""
        # This should be fresh from fixture
        metrics_registry.apdu_commands_total.labels(command="TEST", interface="test").inc()
        assert metrics_registry.apdu_commands_total.labels(command="TEST", interface="test")._value._value == 1
