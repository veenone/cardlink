"""Health checker for application health monitoring.

This module provides a HealthChecker class for registering and running
health checks with an HTTP endpoint for Kubernetes probes.
"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional

from cardlink.observability.config import HealthConfig

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedHealthResult:
    """Aggregated result of all health checks."""

    status: HealthStatus
    checks: Dict[str, HealthCheckResult] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "details": check.details,
                }
                for name, check in self.checks.items()
            },
        }


# Type alias for health check functions
HealthCheckFunction = Callable[[], HealthCheckResult]


class HealthChecker:
    """Health checker with pluggable checks and HTTP endpoint.

    This class manages health checks for various application components
    and exposes them via an HTTP endpoint for Kubernetes probes.

    Example:
        >>> from cardlink.observability.config import HealthConfig
        >>> config = HealthConfig(enabled=True, port=8080)
        >>> checker = HealthChecker(config)
        >>>
        >>> # Register checks
        >>> def database_check() -> HealthCheckResult:
        ...     # Check database connection
        ...     return HealthCheckResult("database", HealthStatus.HEALTHY)
        >>>
        >>> checker.register_check("database", database_check)
        >>> checker.start()
        >>>
        >>> # Run checks
        >>> result = checker.run_all_checks()
        >>> print(result.status)
        >>>
        >>> checker.shutdown()
    """

    def __init__(self, config: HealthConfig) -> None:
        """Initialize health checker.

        Args:
            config: Health check configuration.
        """
        self.config = config
        self._checks: Dict[str, HealthCheckFunction] = {}
        self._lock = threading.Lock()
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="HealthCheck")

    def start(self) -> None:
        """Start the health check HTTP server.

        Example:
            >>> checker.start()
        """
        if self._running:
            logger.warning("HealthChecker already running")
            return

        logger.info(f"Starting health check server on port {self.config.port}")

        # Create handler factory
        checker = self

        class HealthHTTPHandler(BaseHTTPRequestHandler):
            """HTTP handler for health endpoint."""

            def do_GET(self) -> None:
                """Handle GET requests."""
                if self.path == "/health" or self.path == "/healthz":
                    self._handle_health()
                elif self.path == "/ready" or self.path == "/readyz":
                    self._handle_ready()
                elif self.path == "/live" or self.path == "/livez":
                    self._handle_live()
                else:
                    self.send_error(404, "Not Found")

            def _handle_health(self) -> None:
                """Handle full health check request."""
                result = checker.run_all_checks()
                self._send_health_response(result)

            def _handle_ready(self) -> None:
                """Handle readiness probe (all checks must pass)."""
                result = checker.run_all_checks()
                self._send_health_response(result)

            def _handle_live(self) -> None:
                """Handle liveness probe (basic check)."""
                result = AggregatedHealthResult(status=HealthStatus.HEALTHY)
                self._send_health_response(result)

            def _send_health_response(self, result: AggregatedHealthResult) -> None:
                """Send health check response."""
                if result.status == HealthStatus.HEALTHY:
                    status_code = 200
                elif result.status == HealthStatus.DEGRADED:
                    status_code = 200  # Degraded but still serving
                else:
                    status_code = 503

                response_body = json.dumps(result.to_dict()).encode("utf-8")

                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)

            def log_message(self, format: str, *args) -> None:
                """Suppress default logging."""
                logger.debug(f"{self.address_string()} - {format % args}")

        try:
            self._httpd = HTTPServer(("0.0.0.0", self.config.port), HealthHTTPHandler)

            self._running = True
            self._thread = threading.Thread(
                target=self._serve_forever, daemon=True, name="HealthServer"
            )
            self._thread.start()

            logger.info("Health check server started")

        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
            raise

    def shutdown(self) -> None:
        """Shutdown the health check server.

        Example:
            >>> checker.shutdown()
        """
        if not self._running:
            return

        logger.info("Shutting down health check server")
        self._running = False

        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()

        if self._thread:
            self._thread.join(timeout=5)

        self._executor.shutdown(wait=False)

        logger.info("Health check server stopped")

    def _serve_forever(self) -> None:
        """Background thread for HTTP server."""
        try:
            self._httpd.serve_forever()
        except Exception as e:
            logger.error(f"Health server error: {e}")
        finally:
            self._running = False

    def register_check(self, name: str, check: HealthCheckFunction) -> None:
        """Register a health check function.

        Args:
            name: Unique name for the check.
            check: Function that returns HealthCheckResult.

        Example:
            >>> def my_check() -> HealthCheckResult:
            ...     return HealthCheckResult("my_check", HealthStatus.HEALTHY)
            >>> checker.register_check("my_check", my_check)
        """
        with self._lock:
            if name in self._checks:
                logger.warning(f"Overwriting existing health check: {name}")
            self._checks[name] = check
            logger.debug(f"Registered health check: {name}")

    def unregister_check(self, name: str) -> bool:
        """Unregister a health check.

        Args:
            name: Name of the check to remove.

        Returns:
            True if check was removed, False if not found.

        Example:
            >>> checker.unregister_check("my_check")
        """
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                logger.debug(f"Unregistered health check: {name}")
                return True
            return False

    def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check by name.

        Args:
            name: Name of the check to run.

        Returns:
            Health check result.

        Raises:
            KeyError: If check not found.

        Example:
            >>> result = checker.run_check("database")
            >>> print(result.status)
        """
        with self._lock:
            if name not in self._checks:
                raise KeyError(f"Health check not found: {name}")
            check = self._checks[name]

        return self._execute_check(name, check)

    def run_all_checks(self) -> AggregatedHealthResult:
        """Run all registered health checks.

        Returns:
            Aggregated health result with all check results.

        Example:
            >>> result = checker.run_all_checks()
            >>> if result.status == HealthStatus.HEALTHY:
            ...     print("All systems operational")
        """
        with self._lock:
            checks_to_run = dict(self._checks)

        if not checks_to_run:
            return AggregatedHealthResult(status=HealthStatus.HEALTHY)

        # Run checks concurrently
        results: Dict[str, HealthCheckResult] = {}
        futures = {}

        for name, check in checks_to_run.items():
            future = self._executor.submit(self._execute_check, name, check)
            futures[name] = future

        # Collect results
        for name, future in futures.items():
            try:
                result = future.result(timeout=self.config.check_timeout)
                results[name] = result
            except FutureTimeoutError:
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Health check timed out",
                    duration_ms=self.config.check_timeout * 1000,
                )
            except Exception as e:
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check error: {str(e)}",
                )

        # Aggregate status
        overall_status = self._aggregate_status(list(results.values()))

        return AggregatedHealthResult(
            status=overall_status,
            checks=results,
        )

    def _execute_check(self, name: str, check: HealthCheckFunction) -> HealthCheckResult:
        """Execute a single health check with timing.

        Args:
            name: Check name.
            check: Check function.

        Returns:
            Health check result with duration.
        """
        start_time = time.time()
        try:
            result = check()
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=duration_ms,
            )

    def _aggregate_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Aggregate multiple check results into overall status.

        Args:
            results: List of check results.

        Returns:
            Overall health status.
        """
        if not results:
            return HealthStatus.HEALTHY

        statuses = [r.status for r in results]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    @property
    def is_running(self) -> bool:
        """Check if health server is running."""
        return self._running

    @property
    def registered_checks(self) -> List[str]:
        """Get list of registered check names."""
        with self._lock:
            return list(self._checks.keys())


# Built-in health checks
def create_database_check(check_func: Callable[[], bool]) -> HealthCheckFunction:
    """Create a database health check.

    Args:
        check_func: Function that returns True if database is healthy.

    Returns:
        Health check function.

    Example:
        >>> def db_ping() -> bool:
        ...     # Ping database
        ...     return True
        >>> check = create_database_check(db_ping)
        >>> checker.register_check("database", check)
    """

    def check() -> HealthCheckResult:
        try:
            is_healthy = check_func()
            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message="Database connection OK" if is_healthy else "Database unavailable",
            )
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {e}",
            )

    return check


def create_disk_space_check(
    path: str = "/", min_free_percent: float = 10.0
) -> HealthCheckFunction:
    """Create a disk space health check.

    Args:
        path: Path to check disk space for.
        min_free_percent: Minimum free space percentage for healthy status.

    Returns:
        Health check function.
    """

    def check() -> HealthCheckResult:
        try:
            import shutil

            total, used, free = shutil.disk_usage(path)
            free_percent = (free / total) * 100

            if free_percent >= min_free_percent:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_percent:.1f}% free"
            elif free_percent >= min_free_percent / 2:
                status = HealthStatus.DEGRADED
                message = f"Disk space low: {free_percent:.1f}% free"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space critical: {free_percent:.1f}% free"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "path": path,
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "free_percent": free_percent,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check error: {e}",
            )

    return check


def create_memory_check(max_usage_percent: float = 90.0) -> HealthCheckFunction:
    """Create a memory usage health check.

    Args:
        max_usage_percent: Maximum memory usage percentage for healthy status.

    Returns:
        Health check function.
    """

    def check() -> HealthCheckResult:
        try:
            import psutil

            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            if usage_percent <= max_usage_percent:
                status = HealthStatus.HEALTHY
                message = f"Memory OK: {usage_percent:.1f}% used"
            elif usage_percent <= max_usage_percent + 5:
                status = HealthStatus.DEGRADED
                message = f"Memory high: {usage_percent:.1f}% used"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory critical: {usage_percent:.1f}% used"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                details={
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_percent": usage_percent,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check error: {e}",
            )

    return check
