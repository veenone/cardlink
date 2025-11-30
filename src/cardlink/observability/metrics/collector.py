"""Metrics collector for recording application metrics.

This module provides high-level methods for recording metrics throughout
the CardLink application, wrapping the Prometheus metrics registry.
"""

import logging
import threading
import time
from contextlib import contextmanager
from typing import Optional

import psutil

from cardlink.observability.config import MetricsConfig
from cardlink.observability.metrics.registry import MetricsRegistry
from cardlink.observability.metrics.server import MetricsServer

logger = logging.getLogger(__name__)


class MetricsCollector:
    """High-level metrics collector for CardLink.

    This class provides convenient methods for recording metrics throughout
    the application lifecycle. It wraps the Prometheus metrics registry and
    handles metric collection and exposure.

    Example:
        >>> from cardlink.observability.config import MetricsConfig
        >>> config = MetricsConfig(enabled=True, port=9090)
        >>> collector = MetricsCollector(config)
        >>> collector.start()
        >>>
        >>> # Record APDU command
        >>> collector.record_apdu_command("SELECT", "physical")
        >>>
        >>> # Record APDU response with timing
        >>> with collector.time_apdu_command("SELECT"):
        ...     # Execute APDU command
        ...     pass
        >>> collector.record_apdu_response(0x9000, 150)
        >>>
        >>> # Stop collector
        >>> collector.shutdown()
    """

    def __init__(self, config: MetricsConfig):
        """Initialize metrics collector.

        Args:
            config: Metrics configuration.
        """
        self.config = config
        self.registry = MetricsRegistry()
        self._server: Optional[MetricsServer] = None
        self._system_metrics_thread: Optional[threading.Thread] = None
        self._running = False
        self._process = psutil.Process()
        self._start_time = time.time()

    def start(self) -> None:
        """Start metrics collection and HTTP server.

        Example:
            >>> collector = MetricsCollector(config)
            >>> collector.start()
        """
        if self._running:
            logger.warning("MetricsCollector already running")
            return

        logger.info(f"Starting metrics server on port {self.config.port}")

        # Start HTTP server
        self._server = MetricsServer(self.config, self.registry.registry)
        self._server.start()

        # Start system metrics collection
        self._running = True
        self._system_metrics_thread = threading.Thread(
            target=self._collect_system_metrics_loop, daemon=True, name="SystemMetrics"
        )
        self._system_metrics_thread.start()

        logger.info("Metrics collector started")

    def shutdown(self) -> None:
        """Stop metrics collection and HTTP server.

        Example:
            >>> collector.shutdown()
        """
        if not self._running:
            return

        logger.info("Stopping metrics collector")

        self._running = False

        # Stop system metrics collection
        if self._system_metrics_thread:
            self._system_metrics_thread.join(timeout=5)

        # Stop HTTP server
        if self._server:
            self._server.shutdown()

        logger.info("Metrics collector stopped")

    # ========================================================================
    # APDU Metrics
    # ========================================================================

    def record_apdu_command(self, command: str, interface: str = "physical") -> None:
        """Record an APDU command.

        Args:
            command: APDU command name (e.g., "SELECT", "GET_DATA").
            interface: Interface type ("physical", "logical", "at").

        Example:
            >>> collector.record_apdu_command("SELECT", "physical")
        """
        self.registry.apdu_commands_total.labels(
            command=command, interface=interface
        ).inc()

    def record_apdu_response(
        self, status_word: int, data_length: int = 0, success: bool = True
    ) -> None:
        """Record an APDU response.

        Args:
            status_word: Response status word (e.g., 0x9000).
            data_length: Length of response data in bytes.
            success: Whether the response indicates success.

        Example:
            >>> collector.record_apdu_response(0x9000, 150, True)
            >>> collector.record_apdu_response(0x6A82, 0, False)
        """
        sw_hex = f"0x{status_word:04X}"
        self.registry.apdu_responses_total.labels(
            status_word=sw_hex, success=str(success)
        ).inc()

        if data_length > 0:
            self.registry.apdu_data_bytes.labels(direction="received").observe(
                data_length
            )

    def record_apdu_error(self, error_type: str, command: str = "unknown") -> None:
        """Record an APDU error.

        Args:
            error_type: Error type (e.g., "timeout", "connection_lost").
            command: APDU command that failed.

        Example:
            >>> collector.record_apdu_error("timeout", "SELECT")
        """
        self.registry.apdu_errors_total.labels(
            error_type=error_type, command=command
        ).inc()

    @contextmanager
    def time_apdu_command(self, command: str):
        """Context manager for timing APDU commands.

        Args:
            command: APDU command name.

        Yields:
            None

        Example:
            >>> with collector.time_apdu_command("SELECT"):
            ...     # Execute APDU command
            ...     time.sleep(0.1)
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.registry.apdu_response_time_seconds.labels(command=command).observe(
                duration
            )

    # ========================================================================
    # Session Metrics
    # ========================================================================

    def record_session_start(
        self, session_type: str = "admin", protocol: str = "psk-tls"
    ) -> None:
        """Record session start.

        Args:
            session_type: Session type ("admin", "data", "provisioning").
            protocol: Protocol used ("psk-tls", "http").

        Example:
            >>> collector.record_session_start("admin", "psk-tls")
        """
        self.registry.active_sessions.labels(session_type=session_type).inc()
        self.registry.sessions_total.labels(
            session_type=session_type, protocol=protocol
        ).inc()

    def record_session_end(
        self,
        session_type: str,
        duration_seconds: float,
        status: str = "completed",
    ) -> None:
        """Record session end.

        Args:
            session_type: Session type ("admin", "data", "provisioning").
            duration_seconds: Session duration in seconds.
            status: Session end status ("completed", "failed", "timeout").

        Example:
            >>> collector.record_session_end("admin", 45.5, "completed")
        """
        self.registry.active_sessions.labels(session_type=session_type).dec()
        self.registry.session_duration_seconds.labels(
            session_type=session_type, status=status
        ).observe(duration_seconds)

    def record_session_error(self, session_type: str, error_type: str) -> None:
        """Record session error.

        Args:
            session_type: Session type.
            error_type: Error type (e.g., "authentication_failed").

        Example:
            >>> collector.record_session_error("admin", "authentication_failed")
        """
        self.registry.session_errors_total.labels(
            session_type=session_type, error_type=error_type
        ).inc()

    # ========================================================================
    # BIP Metrics
    # ========================================================================

    def record_bip_connection_open(self, bearer_type: str = "tcp") -> None:
        """Record BIP connection opened.

        Args:
            bearer_type: Bearer type ("tcp", "udp", "gprs", "wifi").

        Example:
            >>> collector.record_bip_connection_open("tcp")
        """
        self.registry.bip_connections_active.labels(bearer_type=bearer_type).inc()

    def record_bip_connection_close(
        self, bearer_type: str, duration_seconds: float, status: str = "normal"
    ) -> None:
        """Record BIP connection closed.

        Args:
            bearer_type: Bearer type.
            duration_seconds: Connection duration in seconds.
            status: Close status ("normal", "error", "timeout").

        Example:
            >>> collector.record_bip_connection_close("tcp", 120.5, "normal")
        """
        self.registry.bip_connections_active.labels(bearer_type=bearer_type).dec()
        self.registry.bip_connection_duration_seconds.labels(
            bearer_type=bearer_type, status=status
        ).observe(duration_seconds)

    def record_bip_data_transfer(
        self, direction: str, bytes_transferred: int, bearer_type: str = "tcp"
    ) -> None:
        """Record BIP data transfer.

        Args:
            direction: Transfer direction ("sent", "received").
            bytes_transferred: Number of bytes transferred.
            bearer_type: Bearer type.

        Example:
            >>> collector.record_bip_data_transfer("sent", 1024, "tcp")
        """
        self.registry.bip_bytes_transferred_total.labels(
            direction=direction, bearer_type=bearer_type
        ).inc(bytes_transferred)

    def record_bip_error(self, error_type: str, bearer_type: str = "tcp") -> None:
        """Record BIP error.

        Args:
            error_type: Error type (e.g., "connection_refused").
            bearer_type: Bearer type.

        Example:
            >>> collector.record_bip_error("connection_refused", "tcp")
        """
        self.registry.bip_errors_total.labels(
            error_type=error_type, bearer_type=bearer_type
        ).inc()

    # ========================================================================
    # Database Metrics
    # ========================================================================

    def record_database_connection_change(self, delta: int) -> None:
        """Record database connection count change.

        Args:
            delta: Change in connection count (+1 for new, -1 for closed).

        Example:
            >>> collector.record_database_connection_change(1)  # Connection opened
            >>> collector.record_database_connection_change(-1)  # Connection closed
        """
        if delta > 0:
            self.registry.database_connections_active.inc(delta)
        else:
            self.registry.database_connections_active.dec(-delta)

    @contextmanager
    def time_database_query(self, operation: str, table: str):
        """Context manager for timing database queries.

        Args:
            operation: Query operation ("select", "insert", "update", "delete").
            table: Table name.

        Yields:
            None

        Example:
            >>> with collector.time_database_query("select", "sessions"):
            ...     # Execute query
            ...     pass
        """
        start_time = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            self.registry.database_query_duration_seconds.labels(
                operation=operation, table=table
            ).observe(duration)
            self.registry.database_operations_total.labels(
                operation=operation, table=table, status=status
            ).inc()

    def record_database_error(self, error_type: str, operation: str) -> None:
        """Record database error.

        Args:
            error_type: Error type (e.g., "connection_lost", "query_timeout").
            operation: Database operation that failed.

        Example:
            >>> collector.record_database_error("connection_lost", "select")
        """
        self.registry.database_errors_total.labels(
            error_type=error_type, operation=operation
        ).inc()

    # ========================================================================
    # System Metrics Collection
    # ========================================================================

    def _collect_system_metrics_loop(self) -> None:
        """Background loop for collecting system metrics."""
        while self._running:
            try:
                self._collect_system_metrics()
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")

            # Sleep for collection interval
            time.sleep(self.config.collection_interval)

    def _collect_system_metrics(self) -> None:
        """Collect current system metrics."""
        # CPU usage
        cpu_percent = self._process.cpu_percent()
        self.registry.system_cpu_usage_percent.set(cpu_percent)

        # Memory usage
        memory_info = self._process.memory_info()
        self.registry.system_memory_usage_bytes.set(memory_info.rss)

        # Process uptime
        uptime = time.time() - self._start_time
        self.registry.system_process_uptime_seconds.set(uptime)

        # Thread count
        thread_count = self._process.num_threads()
        self.registry.system_threads_active.set(thread_count)

    # ========================================================================
    # TLS Metrics
    # ========================================================================

    def record_tls_handshake(
        self, cipher_suite: str, result: str = "success", duration_seconds: float = 0
    ) -> None:
        """Record TLS handshake completion.

        Args:
            cipher_suite: Cipher suite used (e.g., "TLS_PSK_WITH_AES_128_CBC_SHA").
            result: Handshake result ("success", "failure").
            duration_seconds: Handshake duration.

        Example:
            >>> collector.record_tls_handshake("TLS_PSK_WITH_AES_128_CBC_SHA", "success", 0.15)
        """
        self.registry.tls_handshakes_total.labels(
            cipher_suite=cipher_suite, result=result
        ).inc()

        if duration_seconds > 0:
            self.registry.tls_handshake_duration_seconds.labels(
                cipher_suite=cipher_suite
            ).observe(duration_seconds)

    @contextmanager
    def time_tls_handshake(self, cipher_suite: str):
        """Context manager for timing TLS handshakes.

        Args:
            cipher_suite: Cipher suite being negotiated.

        Yields:
            None

        Example:
            >>> with collector.time_tls_handshake("TLS_PSK_WITH_AES_128_CBC_SHA"):
            ...     # Perform handshake
            ...     pass
        """
        start_time = time.time()
        result = "success"
        try:
            yield
        except Exception:
            result = "failure"
            raise
        finally:
            duration = time.time() - start_time
            self.record_tls_handshake(cipher_suite, result, duration)

    def set_tls_connections(self, count: int) -> None:
        """Set the number of active TLS connections.

        Args:
            count: Number of active connections.

        Example:
            >>> collector.set_tls_connections(5)
        """
        self.registry.tls_connections_active.set(count)

    def inc_tls_connections(self) -> None:
        """Increment active TLS connections count.

        Example:
            >>> collector.inc_tls_connections()
        """
        self.registry.tls_connections_active.inc()

    def dec_tls_connections(self) -> None:
        """Decrement active TLS connections count.

        Example:
            >>> collector.dec_tls_connections()
        """
        self.registry.tls_connections_active.dec()

    def record_tls_error(self, error_type: str) -> None:
        """Record TLS error.

        Args:
            error_type: Error type (e.g., "handshake_timeout", "invalid_psk").

        Example:
            >>> collector.record_tls_error("handshake_timeout")
        """
        self.registry.tls_errors_total.labels(error_type=error_type).inc()

    # ========================================================================
    # Device Metrics
    # ========================================================================

    def set_devices_connected(self, device_type: str, count: int) -> None:
        """Set number of connected devices of a type.

        Args:
            device_type: Device type ("phone", "modem", "reader").
            count: Number of connected devices.

        Example:
            >>> collector.set_devices_connected("phone", 2)
        """
        self.registry.devices_connected.labels(device_type=device_type).set(count)

    def inc_devices_connected(self, device_type: str) -> None:
        """Increment connected device count.

        Args:
            device_type: Device type.

        Example:
            >>> collector.inc_devices_connected("phone")
        """
        self.registry.devices_connected.labels(device_type=device_type).inc()

    def dec_devices_connected(self, device_type: str) -> None:
        """Decrement connected device count.

        Args:
            device_type: Device type.

        Example:
            >>> collector.dec_devices_connected("phone")
        """
        self.registry.devices_connected.labels(device_type=device_type).dec()

    def record_device_error(self, device_type: str, error_type: str) -> None:
        """Record device error.

        Args:
            device_type: Device type ("phone", "modem", "reader").
            error_type: Error type (e.g., "connection_lost", "timeout").

        Example:
            >>> collector.record_device_error("phone", "connection_lost")
        """
        self.registry.device_errors_total.labels(
            device_type=device_type, error_type=error_type
        ).inc()

    def record_at_command_duration(self, command: str, duration_seconds: float) -> None:
        """Record AT command execution time.

        Args:
            command: AT command (e.g., "AT+CSIM", "AT+CPIN").
            duration_seconds: Execution time.

        Example:
            >>> collector.record_at_command_duration("AT+CSIM", 0.25)
        """
        self.registry.at_command_duration_seconds.labels(command=command).observe(
            duration_seconds
        )

    @contextmanager
    def time_at_command(self, command: str):
        """Context manager for timing AT commands.

        Args:
            command: AT command being executed.

        Yields:
            None

        Example:
            >>> with collector.time_at_command("AT+CSIM"):
            ...     # Execute AT command
            ...     pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_at_command_duration(command, duration)

    def record_adb_operation_duration(
        self, operation: str, duration_seconds: float
    ) -> None:
        """Record ADB operation execution time.

        Args:
            operation: ADB operation (e.g., "shell", "push", "pull").
            duration_seconds: Execution time.

        Example:
            >>> collector.record_adb_operation_duration("shell", 1.5)
        """
        self.registry.adb_operation_duration_seconds.labels(operation=operation).observe(
            duration_seconds
        )

    @contextmanager
    def time_adb_operation(self, operation: str):
        """Context manager for timing ADB operations.

        Args:
            operation: ADB operation being executed.

        Yields:
            None

        Example:
            >>> with collector.time_adb_operation("shell"):
            ...     # Execute ADB operation
            ...     pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_adb_operation_duration(operation, duration)

    def record_device_operation(
        self, device_type: str, operation: str, status: str = "success"
    ) -> None:
        """Record device operation.

        Args:
            device_type: Device type.
            operation: Operation name.
            status: Result status ("success", "failure").

        Example:
            >>> collector.record_device_operation("phone", "connect", "success")
        """
        self.registry.device_operations_total.labels(
            device_type=device_type, operation=operation, status=status
        ).inc()

    # ========================================================================
    # Test Metrics
    # ========================================================================

    def record_test_result(
        self,
        suite_name: str,
        status: str,
        test_name: str = "",
        duration_seconds: float = 0,
    ) -> None:
        """Record test result.

        Args:
            suite_name: Test suite name.
            status: Test status ("pass", "fail", "skip", "error").
            test_name: Individual test name (optional).
            duration_seconds: Test duration.

        Example:
            >>> collector.record_test_result("e2e_basic", "pass", "test_connection", 5.2)
        """
        self.registry.test_results_total.labels(
            suite_name=suite_name, status=status
        ).inc()

        if duration_seconds > 0 and test_name:
            self.registry.test_duration_seconds.labels(
                suite_name=suite_name, test_name=test_name
            ).observe(duration_seconds)

    def record_test_suite_duration(
        self, suite_name: str, duration_seconds: float
    ) -> None:
        """Record test suite total duration.

        Args:
            suite_name: Test suite name.
            duration_seconds: Suite execution time.

        Example:
            >>> collector.record_test_suite_duration("e2e_basic", 120.5)
        """
        self.registry.test_suite_duration_seconds.labels(suite_name=suite_name).observe(
            duration_seconds
        )

    @contextmanager
    def time_test_suite(self, suite_name: str):
        """Context manager for timing test suites.

        Args:
            suite_name: Test suite name.

        Yields:
            None

        Example:
            >>> with collector.time_test_suite("e2e_basic"):
            ...     # Run test suite
            ...     pass
        """
        self.registry.tests_running.labels(suite_name=suite_name).inc()
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_test_suite_duration(suite_name, duration)
            self.registry.tests_running.labels(suite_name=suite_name).dec()

    def set_tests_running(self, suite_name: str, count: int) -> None:
        """Set number of tests currently running in a suite.

        Args:
            suite_name: Test suite name.
            count: Number of running tests.

        Example:
            >>> collector.set_tests_running("e2e_basic", 3)
        """
        self.registry.tests_running.labels(suite_name=suite_name).set(count)
