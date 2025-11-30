"""Unit tests for HealthChecker.

Tests health check registration, execution, and HTTP endpoint.
"""

import time
from unittest.mock import MagicMock

import pytest

from cardlink.observability.config import HealthConfig
from cardlink.observability.health.checker import (
    AggregatedHealthResult,
    HealthCheckResult,
    HealthChecker,
    HealthStatus,
    create_database_check,
    create_disk_space_check,
    create_memory_check,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_status_values(self):
        """Test health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_create_result(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
        )
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.duration_ms == 0.0
        assert result.details == {}

    def test_create_result_with_details(self):
        """Test creating result with details."""
        result = HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connected",
            duration_ms=15.5,
            details={"connection_pool": 5},
        )
        assert result.details == {"connection_pool": 5}


class TestAggregatedHealthResult:
    """Tests for AggregatedHealthResult dataclass."""

    def test_create_aggregated(self):
        """Test creating aggregated result."""
        result = AggregatedHealthResult(status=HealthStatus.HEALTHY)
        assert result.status == HealthStatus.HEALTHY
        assert result.checks == {}
        assert result.timestamp > 0

    def test_to_dict(self):
        """Test converting to dictionary."""
        check_result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK",
            duration_ms=10.0,
        )
        result = AggregatedHealthResult(
            status=HealthStatus.HEALTHY,
            checks={"test": check_result},
        )

        d = result.to_dict()
        assert d["status"] == "healthy"
        assert "timestamp" in d
        assert "test" in d["checks"]
        assert d["checks"]["test"]["status"] == "healthy"


class TestHealthCheckerCreation:
    """Tests for HealthChecker initialization."""

    def test_create_checker(self, health_config):
        """Test creating health checker."""
        checker = HealthChecker(health_config)
        assert checker is not None
        assert checker.config == health_config
        assert checker.is_running is False

    def test_registered_checks_empty(self, health_config):
        """Test no checks registered initially."""
        checker = HealthChecker(health_config)
        assert checker.registered_checks == []


class TestHealthCheckerRegistration:
    """Tests for health check registration."""

    @pytest.fixture
    def checker(self, health_config):
        """Create health checker for testing."""
        return HealthChecker(health_config)

    def test_register_check(self, checker):
        """Test registering a health check."""

        def my_check():
            return HealthCheckResult("test", HealthStatus.HEALTHY)

        checker.register_check("test", my_check)
        assert "test" in checker.registered_checks

    def test_register_multiple_checks(self, checker):
        """Test registering multiple checks."""

        def check1():
            return HealthCheckResult("check1", HealthStatus.HEALTHY)

        def check2():
            return HealthCheckResult("check2", HealthStatus.HEALTHY)

        checker.register_check("check1", check1)
        checker.register_check("check2", check2)

        assert len(checker.registered_checks) == 2

    def test_unregister_check(self, checker):
        """Test unregistering a health check."""

        def my_check():
            return HealthCheckResult("test", HealthStatus.HEALTHY)

        checker.register_check("test", my_check)
        assert "test" in checker.registered_checks

        result = checker.unregister_check("test")
        assert result is True
        assert "test" not in checker.registered_checks

    def test_unregister_nonexistent(self, checker):
        """Test unregistering non-existent check."""
        result = checker.unregister_check("nonexistent")
        assert result is False


class TestHealthCheckerExecution:
    """Tests for health check execution."""

    @pytest.fixture
    def checker(self, health_config):
        """Create health checker for testing."""
        return HealthChecker(health_config)

    def test_run_single_check(self, checker):
        """Test running a single check."""

        def healthy_check():
            return HealthCheckResult("test", HealthStatus.HEALTHY, "OK")

        checker.register_check("test", healthy_check)
        result = checker.run_check("test")

        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY

    def test_run_check_not_found(self, checker):
        """Test running non-existent check raises error."""
        with pytest.raises(KeyError, match="not found"):
            checker.run_check("nonexistent")

    def test_run_all_checks_empty(self, checker):
        """Test running with no registered checks."""
        result = checker.run_all_checks()
        assert result.status == HealthStatus.HEALTHY
        assert result.checks == {}

    def test_run_all_checks_healthy(self, checker):
        """Test running all healthy checks."""

        def check1():
            return HealthCheckResult("check1", HealthStatus.HEALTHY)

        def check2():
            return HealthCheckResult("check2", HealthStatus.HEALTHY)

        checker.register_check("check1", check1)
        checker.register_check("check2", check2)

        result = checker.run_all_checks()
        assert result.status == HealthStatus.HEALTHY
        assert len(result.checks) == 2

    def test_run_all_checks_unhealthy(self, checker):
        """Test running with unhealthy check."""

        def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY)

        def unhealthy_check():
            return HealthCheckResult("unhealthy", HealthStatus.UNHEALTHY, "Failed")

        checker.register_check("healthy", healthy_check)
        checker.register_check("unhealthy", unhealthy_check)

        result = checker.run_all_checks()
        assert result.status == HealthStatus.UNHEALTHY

    def test_run_all_checks_degraded(self, checker):
        """Test running with degraded check."""

        def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY)

        def degraded_check():
            return HealthCheckResult("degraded", HealthStatus.DEGRADED, "Slow")

        checker.register_check("healthy", healthy_check)
        checker.register_check("degraded", degraded_check)

        result = checker.run_all_checks()
        assert result.status == HealthStatus.DEGRADED

    def test_run_check_with_exception(self, checker):
        """Test check that raises exception."""

        def failing_check():
            raise RuntimeError("Check failed")

        checker.register_check("failing", failing_check)
        result = checker.run_check("failing")

        assert result.status == HealthStatus.UNHEALTHY
        assert "Check failed" in result.message

    def test_run_check_measures_duration(self, checker):
        """Test that check duration is measured."""

        def slow_check():
            time.sleep(0.05)
            return HealthCheckResult("slow", HealthStatus.HEALTHY)

        checker.register_check("slow", slow_check)
        result = checker.run_check("slow")

        assert result.duration_ms >= 50  # At least 50ms


class TestHealthCheckerLifecycle:
    """Tests for HealthChecker start/shutdown lifecycle."""

    def test_start_checker(self, health_config):
        """Test starting health checker."""
        checker = HealthChecker(health_config)
        checker.start()

        try:
            assert checker.is_running is True
        finally:
            checker.shutdown()

    def test_start_idempotent(self, health_config):
        """Test that starting twice is safe."""
        checker = HealthChecker(health_config)
        checker.start()
        checker.start()  # Should warn but not error

        try:
            assert checker.is_running is True
        finally:
            checker.shutdown()

    def test_shutdown_checker(self, health_config):
        """Test shutting down health checker."""
        checker = HealthChecker(health_config)
        checker.start()
        checker.shutdown()

        assert checker.is_running is False

    def test_shutdown_not_started(self, health_config):
        """Test shutdown when not started is safe."""
        checker = HealthChecker(health_config)
        checker.shutdown()  # Should not raise

    def test_shutdown_idempotent(self, health_config):
        """Test that shutdown twice is safe."""
        checker = HealthChecker(health_config)
        checker.start()
        checker.shutdown()
        checker.shutdown()  # Should not raise


class TestBuiltInChecks:
    """Tests for built-in health check factories."""

    def test_database_check_healthy(self):
        """Test database check when healthy."""

        def healthy_db():
            return True

        check = create_database_check(healthy_db)
        result = check()

        assert result.status == HealthStatus.HEALTHY

    def test_database_check_unhealthy(self):
        """Test database check when unhealthy."""

        def unhealthy_db():
            return False

        check = create_database_check(unhealthy_db)
        result = check()

        assert result.status == HealthStatus.UNHEALTHY

    def test_database_check_exception(self):
        """Test database check when it raises exception."""

        def failing_db():
            raise ConnectionError("Cannot connect")

        check = create_database_check(failing_db)
        result = check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Cannot connect" in result.message

    def test_disk_space_check(self):
        """Test disk space check."""
        check = create_disk_space_check("/", min_free_percent=1.0)
        result = check()

        # Should at least complete without error
        assert result.name == "disk_space"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert "free_percent" in result.details

    def test_memory_check(self):
        """Test memory check."""
        check = create_memory_check(max_usage_percent=99.0)
        result = check()

        # Should at least complete without error
        assert result.name == "memory"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert "used_percent" in result.details


class TestHealthStatusAggregation:
    """Tests for status aggregation logic."""

    @pytest.fixture
    def checker(self, health_config):
        """Create health checker for testing."""
        return HealthChecker(health_config)

    def test_aggregate_all_healthy(self, checker):
        """Test aggregation with all healthy."""
        results = [
            HealthCheckResult("a", HealthStatus.HEALTHY),
            HealthCheckResult("b", HealthStatus.HEALTHY),
        ]
        status = checker._aggregate_status(results)
        assert status == HealthStatus.HEALTHY

    def test_aggregate_one_unhealthy(self, checker):
        """Test aggregation with one unhealthy."""
        results = [
            HealthCheckResult("a", HealthStatus.HEALTHY),
            HealthCheckResult("b", HealthStatus.UNHEALTHY),
        ]
        status = checker._aggregate_status(results)
        assert status == HealthStatus.UNHEALTHY

    def test_aggregate_one_degraded(self, checker):
        """Test aggregation with one degraded."""
        results = [
            HealthCheckResult("a", HealthStatus.HEALTHY),
            HealthCheckResult("b", HealthStatus.DEGRADED),
        ]
        status = checker._aggregate_status(results)
        assert status == HealthStatus.DEGRADED

    def test_aggregate_empty(self, checker):
        """Test aggregation with no results."""
        status = checker._aggregate_status([])
        assert status == HealthStatus.HEALTHY

    def test_aggregate_unhealthy_priority(self, checker):
        """Test that unhealthy has priority over degraded."""
        results = [
            HealthCheckResult("a", HealthStatus.DEGRADED),
            HealthCheckResult("b", HealthStatus.UNHEALTHY),
        ]
        status = checker._aggregate_status(results)
        assert status == HealthStatus.UNHEALTHY
