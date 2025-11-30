"""Unit tests for MetricsCollector.

Tests all recording methods, system metrics collection, and timing context managers.
"""

import time

import pytest
from prometheus_client import CollectorRegistry

from cardlink.observability.config import MetricsConfig
from cardlink.observability.metrics.collector import MetricsCollector
from cardlink.observability.metrics.registry import MetricsRegistry


class TestMetricsCollectorCreation:
    """Tests for MetricsCollector initialization."""

    @pytest.fixture
    def config(self):
        """Create test metrics config."""
        return MetricsConfig(
            enabled=True,
            port=29090,  # Use high port to avoid conflicts
            path="/metrics",
            collection_interval=60,  # Long interval to avoid background collection
        )

    def test_create_collector(self, config):
        """Test creating metrics collector."""
        collector = MetricsCollector(config)
        assert collector is not None
        assert collector.config == config
        assert collector.registry is not None

    def test_collector_not_running_initially(self, config):
        """Test collector is not running on creation."""
        collector = MetricsCollector(config)
        assert collector._running is False


class TestAPDURecording:
    """Tests for APDU metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29091, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_apdu_command(self, collector):
        """Test recording APDU commands."""
        collector.record_apdu_command("SELECT", "physical")
        collector.record_apdu_command("SELECT", "physical")
        collector.record_apdu_command("GET_DATA", "logical")

        assert (
            collector.registry.apdu_commands_total.labels(
                command="SELECT", interface="physical"
            )._value._value
            == 2
        )
        assert (
            collector.registry.apdu_commands_total.labels(
                command="GET_DATA", interface="logical"
            )._value._value
            == 1
        )

    def test_record_apdu_response(self, collector):
        """Test recording APDU responses."""
        collector.record_apdu_response(0x9000, 150, True)
        collector.record_apdu_response(0x6A82, 0, False)

        assert (
            collector.registry.apdu_responses_total.labels(
                status_word="0x9000", success="True"
            )._value._value
            == 1
        )
        assert (
            collector.registry.apdu_responses_total.labels(
                status_word="0x6A82", success="False"
            )._value._value
            == 1
        )

    def test_record_apdu_error(self, collector):
        """Test recording APDU errors."""
        collector.record_apdu_error("timeout", "SELECT")
        collector.record_apdu_error("timeout", "SELECT")

        assert (
            collector.registry.apdu_errors_total.labels(
                error_type="timeout", command="SELECT"
            )._value._value
            == 2
        )

    def test_time_apdu_command(self, collector):
        """Test timing APDU commands."""
        with collector.time_apdu_command("SELECT"):
            time.sleep(0.01)

        # Verify histogram was updated
        assert collector.registry.apdu_response_time_seconds.labels(
            command="SELECT"
        )._sum._value > 0


class TestSessionRecording:
    """Tests for session metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29092, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_session_start(self, collector):
        """Test recording session start."""
        collector.record_session_start("admin", "psk-tls")

        assert (
            collector.registry.active_sessions.labels(session_type="admin")._value._value
            == 1
        )
        assert (
            collector.registry.sessions_total.labels(
                session_type="admin", protocol="psk-tls"
            )._value._value
            == 1
        )

    def test_record_session_end(self, collector):
        """Test recording session end."""
        collector.record_session_start("admin", "psk-tls")
        collector.record_session_end("admin", 45.5, "completed")

        assert (
            collector.registry.active_sessions.labels(session_type="admin")._value._value
            == 0
        )

    def test_record_session_error(self, collector):
        """Test recording session errors."""
        collector.record_session_error("admin", "authentication_failed")

        assert (
            collector.registry.session_errors_total.labels(
                session_type="admin", error_type="authentication_failed"
            )._value._value
            == 1
        )


class TestBIPRecording:
    """Tests for BIP metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29093, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_bip_connection_open(self, collector):
        """Test recording BIP connection open."""
        collector.record_bip_connection_open("tcp")

        assert (
            collector.registry.bip_connections_active.labels(
                bearer_type="tcp"
            )._value._value
            == 1
        )

    def test_record_bip_connection_close(self, collector):
        """Test recording BIP connection close."""
        collector.record_bip_connection_open("tcp")
        collector.record_bip_connection_close("tcp", 120.5, "normal")

        assert (
            collector.registry.bip_connections_active.labels(
                bearer_type="tcp"
            )._value._value
            == 0
        )

    def test_record_bip_data_transfer(self, collector):
        """Test recording BIP data transfer."""
        collector.record_bip_data_transfer("sent", 1024, "tcp")

        assert (
            collector.registry.bip_bytes_transferred_total.labels(
                direction="sent", bearer_type="tcp"
            )._value._value
            == 1024
        )

    def test_record_bip_error(self, collector):
        """Test recording BIP errors."""
        collector.record_bip_error("connection_refused", "tcp")

        assert (
            collector.registry.bip_errors_total.labels(
                error_type="connection_refused", bearer_type="tcp"
            )._value._value
            == 1
        )


class TestTLSRecording:
    """Tests for TLS metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29094, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_tls_handshake(self, collector):
        """Test recording TLS handshake."""
        collector.record_tls_handshake(
            "TLS_PSK_WITH_AES_128_CBC_SHA", "success", 0.15
        )

        assert (
            collector.registry.tls_handshakes_total.labels(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA", result="success"
            )._value._value
            == 1
        )

    def test_time_tls_handshake(self, collector):
        """Test timing TLS handshake."""
        with collector.time_tls_handshake("TLS_PSK_WITH_AES_128_CBC_SHA"):
            time.sleep(0.01)

        assert (
            collector.registry.tls_handshakes_total.labels(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA", result="success"
            )._value._value
            == 1
        )

    def test_time_tls_handshake_failure(self, collector):
        """Test timing TLS handshake that fails."""
        with pytest.raises(ValueError):
            with collector.time_tls_handshake("TLS_PSK_WITH_AES_128_CBC_SHA"):
                raise ValueError("Handshake failed")

        assert (
            collector.registry.tls_handshakes_total.labels(
                cipher_suite="TLS_PSK_WITH_AES_128_CBC_SHA", result="failure"
            )._value._value
            == 1
        )

    def test_tls_connections_management(self, collector):
        """Test TLS connection counting."""
        collector.set_tls_connections(0)
        collector.inc_tls_connections()
        collector.inc_tls_connections()
        assert collector.registry.tls_connections_active._value._value == 2

        collector.dec_tls_connections()
        assert collector.registry.tls_connections_active._value._value == 1

    def test_record_tls_error(self, collector):
        """Test recording TLS errors."""
        collector.record_tls_error("handshake_timeout")

        assert (
            collector.registry.tls_errors_total.labels(
                error_type="handshake_timeout"
            )._value._value
            == 1
        )


class TestDeviceRecording:
    """Tests for device metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29095, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_set_devices_connected(self, collector):
        """Test setting connected device count."""
        collector.set_devices_connected("phone", 2)

        assert (
            collector.registry.devices_connected.labels(
                device_type="phone"
            )._value._value
            == 2
        )

    def test_inc_dec_devices_connected(self, collector):
        """Test incrementing/decrementing device count."""
        collector.set_devices_connected("modem", 0)
        collector.inc_devices_connected("modem")
        collector.inc_devices_connected("modem")

        assert (
            collector.registry.devices_connected.labels(
                device_type="modem"
            )._value._value
            == 2
        )

        collector.dec_devices_connected("modem")
        assert (
            collector.registry.devices_connected.labels(
                device_type="modem"
            )._value._value
            == 1
        )

    def test_record_device_error(self, collector):
        """Test recording device errors."""
        collector.record_device_error("phone", "connection_lost")

        assert (
            collector.registry.device_errors_total.labels(
                device_type="phone", error_type="connection_lost"
            )._value._value
            == 1
        )

    def test_record_at_command_duration(self, collector):
        """Test recording AT command duration."""
        collector.record_at_command_duration("AT+CSIM", 0.25)

        assert (
            collector.registry.at_command_duration_seconds.labels(
                command="AT+CSIM"
            )._sum._value
            == 0.25
        )

    def test_time_at_command(self, collector):
        """Test timing AT commands."""
        with collector.time_at_command("AT+CPIN"):
            time.sleep(0.01)

        assert (
            collector.registry.at_command_duration_seconds.labels(
                command="AT+CPIN"
            )._sum._value
            > 0
        )

    def test_record_adb_operation_duration(self, collector):
        """Test recording ADB operation duration."""
        collector.record_adb_operation_duration("shell", 1.5)

        assert (
            collector.registry.adb_operation_duration_seconds.labels(
                operation="shell"
            )._sum._value
            == 1.5
        )

    def test_time_adb_operation(self, collector):
        """Test timing ADB operations."""
        with collector.time_adb_operation("push"):
            time.sleep(0.01)

        assert (
            collector.registry.adb_operation_duration_seconds.labels(
                operation="push"
            )._sum._value
            > 0
        )

    def test_record_device_operation(self, collector):
        """Test recording device operations."""
        collector.record_device_operation("phone", "connect", "success")
        collector.record_device_operation("phone", "connect", "failure")

        assert (
            collector.registry.device_operations_total.labels(
                device_type="phone", operation="connect", status="success"
            )._value._value
            == 1
        )
        assert (
            collector.registry.device_operations_total.labels(
                device_type="phone", operation="connect", status="failure"
            )._value._value
            == 1
        )


class TestTestRecording:
    """Tests for test metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29096, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_test_result(self, collector):
        """Test recording test results."""
        collector.record_test_result("e2e_basic", "pass", "test_connection", 5.2)
        collector.record_test_result("e2e_basic", "fail", "test_auth", 1.0)

        assert (
            collector.registry.test_results_total.labels(
                suite_name="e2e_basic", status="pass"
            )._value._value
            == 1
        )
        assert (
            collector.registry.test_results_total.labels(
                suite_name="e2e_basic", status="fail"
            )._value._value
            == 1
        )

    def test_record_test_suite_duration(self, collector):
        """Test recording test suite duration."""
        collector.record_test_suite_duration("e2e_basic", 120.5)

        assert (
            collector.registry.test_suite_duration_seconds.labels(
                suite_name="e2e_basic"
            )._sum._value
            == 120.5
        )

    def test_time_test_suite(self, collector):
        """Test timing test suites."""
        with collector.time_test_suite("integration"):
            time.sleep(0.01)

        # Verify duration was recorded
        assert (
            collector.registry.test_suite_duration_seconds.labels(
                suite_name="integration"
            )._sum._value
            > 0
        )

        # Verify tests_running was managed correctly
        assert (
            collector.registry.tests_running.labels(
                suite_name="integration"
            )._value._value
            == 0
        )

    def test_set_tests_running(self, collector):
        """Test setting running test count."""
        collector.set_tests_running("e2e_basic", 3)

        assert (
            collector.registry.tests_running.labels(
                suite_name="e2e_basic"
            )._value._value
            == 3
        )


class TestDatabaseRecording:
    """Tests for database metric recording methods."""

    @pytest.fixture
    def collector(self):
        """Create collector with isolated registry."""
        config = MetricsConfig(enabled=True, port=29097, collection_interval=60)
        coll = MetricsCollector(config)
        coll.registry = MetricsRegistry(registry=CollectorRegistry())
        return coll

    def test_record_database_connection_change(self, collector):
        """Test recording database connection changes."""
        collector.record_database_connection_change(1)
        collector.record_database_connection_change(1)

        assert collector.registry.database_connections_active._value._value == 2

        collector.record_database_connection_change(-1)
        assert collector.registry.database_connections_active._value._value == 1

    def test_time_database_query(self, collector):
        """Test timing database queries."""
        with collector.time_database_query("select", "sessions"):
            time.sleep(0.01)

        assert (
            collector.registry.database_query_duration_seconds.labels(
                operation="select", table="sessions"
            )._sum._value
            > 0
        )
        assert (
            collector.registry.database_operations_total.labels(
                operation="select", table="sessions", status="success"
            )._value._value
            == 1
        )

    def test_time_database_query_error(self, collector):
        """Test timing database query that fails."""
        with pytest.raises(ValueError):
            with collector.time_database_query("insert", "logs"):
                raise ValueError("Insert failed")

        assert (
            collector.registry.database_operations_total.labels(
                operation="insert", table="logs", status="error"
            )._value._value
            == 1
        )

    def test_record_database_error(self, collector):
        """Test recording database errors."""
        collector.record_database_error("connection_lost", "select")

        assert (
            collector.registry.database_errors_total.labels(
                error_type="connection_lost", operation="select"
            )._value._value
            == 1
        )
