"""Metrics registry for Prometheus metrics definitions.

This module defines all Prometheus metrics used in CardLink for monitoring
APDU operations, sessions, BIP connections, and system health.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info


class MetricsRegistry:
    """Registry of all Prometheus metrics for CardLink.

    This class defines and maintains all metrics used throughout the application.
    Metrics are organized by component: APDU, Sessions, BIP, System, etc.

    Example:
        >>> registry = MetricsRegistry()
        >>> # Record APDU command
        >>> registry.apdu_commands_total.labels(
        ...     command="SELECT",
        ...     interface="physical"
        ... ).inc()
        >>> # Record response time
        >>> registry.apdu_response_time_seconds.labels(
        ...     command="SELECT"
        ... ).observe(0.15)
    """

    def __init__(self, registry: CollectorRegistry = None) -> None:
        """Initialize all Prometheus metrics.

        Args:
            registry: Prometheus collector registry. If None, uses the default global registry.
        """
        self.registry = registry or CollectorRegistry()
        self._create_apdu_metrics()
        self._create_session_metrics()
        self._create_bip_metrics()
        self._create_tls_metrics()
        self._create_device_metrics()
        self._create_test_metrics()
        self._create_system_metrics()
        self._create_database_metrics()
        self._create_info_metrics()

    def _create_apdu_metrics(self) -> None:
        """Create APDU-related metrics."""
        # APDU command counter
        self.apdu_commands_total = Counter(
            name="cardlink_apdu_commands_total",
            documentation="Total number of APDU commands sent",
            labelnames=["command", "interface"],
            registry=self.registry,
        )

        # APDU response counter
        self.apdu_responses_total = Counter(
            name="cardlink_apdu_responses_total",
            documentation="Total number of APDU responses received",
            labelnames=["status_word", "success"],
            registry=self.registry,
        )

        # APDU errors counter
        self.apdu_errors_total = Counter(
            name="cardlink_apdu_errors_total",
            documentation="Total number of APDU errors",
            labelnames=["error_type", "command"],
            registry=self.registry,
        )

        # APDU response time histogram
        self.apdu_response_time_seconds = Histogram(
            name="cardlink_apdu_response_time_seconds",
            documentation="APDU command response time in seconds",
            labelnames=["command"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry,
        )

        # APDU data size histogram
        self.apdu_data_bytes = Histogram(
            name="cardlink_apdu_data_bytes",
            documentation="Size of APDU data in bytes",
            labelnames=["direction"],  # sent/received
            buckets=[16, 32, 64, 128, 256, 512, 1024, 2048, 4096],
            registry=self.registry,
        )

    def _create_session_metrics(self) -> None:
        """Create session-related metrics."""
        # Active sessions gauge
        self.active_sessions = Gauge(
            name="cardlink_active_sessions",
            documentation="Number of currently active sessions",
            labelnames=["session_type"],  # admin/data/provisioning
            registry=self.registry,
        )

        # Session duration histogram
        self.session_duration_seconds = Histogram(
            name="cardlink_session_duration_seconds",
            documentation="Session duration in seconds",
            labelnames=["session_type", "status"],  # completed/failed/timeout
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry,
        )

        # Session errors counter
        self.session_errors_total = Counter(
            name="cardlink_session_errors_total",
            documentation="Total number of session errors",
            labelnames=["session_type", "error_type"],
            registry=self.registry,
        )

        # Sessions total counter
        self.sessions_total = Counter(
            name="cardlink_sessions_total",
            documentation="Total number of sessions started",
            labelnames=["session_type", "protocol"],  # psk-tls/http
            registry=self.registry,
        )

    def _create_bip_metrics(self) -> None:
        """Create BIP (Bearer Independent Protocol) metrics."""
        # BIP connections gauge
        self.bip_connections_active = Gauge(
            name="cardlink_bip_connections_active",
            documentation="Number of active BIP connections",
            labelnames=["bearer_type"],  # tcp/udp/gprs/wifi
            registry=self.registry,
        )

        # BIP data transfer counter
        self.bip_bytes_transferred_total = Counter(
            name="cardlink_bip_bytes_transferred_total",
            documentation="Total bytes transferred over BIP",
            labelnames=["direction", "bearer_type"],  # sent/received
            registry=self.registry,
        )

        # BIP connection duration histogram
        self.bip_connection_duration_seconds = Histogram(
            name="cardlink_bip_connection_duration_seconds",
            documentation="BIP connection duration in seconds",
            labelnames=["bearer_type", "status"],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry,
        )

        # BIP errors counter
        self.bip_errors_total = Counter(
            name="cardlink_bip_errors_total",
            documentation="Total number of BIP errors",
            labelnames=["error_type", "bearer_type"],
            registry=self.registry,
        )

    def _create_tls_metrics(self) -> None:
        """Create TLS/PSK handshake metrics."""
        # TLS handshake counter
        self.tls_handshakes_total = Counter(
            name="cardlink_tls_handshakes_total",
            documentation="Total number of TLS handshakes",
            labelnames=["cipher_suite", "result"],  # result: success/failure
            registry=self.registry,
        )

        # TLS handshake duration histogram
        self.tls_handshake_duration_seconds = Histogram(
            name="cardlink_tls_handshake_duration_seconds",
            documentation="TLS handshake duration in seconds",
            labelnames=["cipher_suite"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry,
        )

        # Active TLS connections gauge
        self.tls_connections_active = Gauge(
            name="cardlink_tls_connections_active",
            documentation="Number of active TLS connections",
            registry=self.registry,
        )

        # TLS errors counter
        self.tls_errors_total = Counter(
            name="cardlink_tls_errors_total",
            documentation="Total number of TLS errors",
            labelnames=["error_type"],
            registry=self.registry,
        )

    def _create_device_metrics(self) -> None:
        """Create device connection and operation metrics."""
        # Connected devices gauge
        self.devices_connected = Gauge(
            name="cardlink_devices_connected",
            documentation="Number of connected devices",
            labelnames=["device_type"],  # phone, modem, reader
            registry=self.registry,
        )

        # Device errors counter
        self.device_errors_total = Counter(
            name="cardlink_device_errors_total",
            documentation="Total number of device errors",
            labelnames=["device_type", "error_type"],
            registry=self.registry,
        )

        # AT command duration histogram
        self.at_command_duration_seconds = Histogram(
            name="cardlink_at_command_duration_seconds",
            documentation="AT command execution time in seconds",
            labelnames=["command"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry,
        )

        # ADB operation duration histogram
        self.adb_operation_duration_seconds = Histogram(
            name="cardlink_adb_operation_duration_seconds",
            documentation="ADB operation execution time in seconds",
            labelnames=["operation"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
            registry=self.registry,
        )

        # Device operations counter
        self.device_operations_total = Counter(
            name="cardlink_device_operations_total",
            documentation="Total number of device operations",
            labelnames=["device_type", "operation", "status"],
            registry=self.registry,
        )

    def _create_test_metrics(self) -> None:
        """Create test execution metrics."""
        # Test results counter
        self.test_results_total = Counter(
            name="cardlink_test_results_total",
            documentation="Total number of test results",
            labelnames=["suite_name", "status"],  # status: pass/fail/skip/error
            registry=self.registry,
        )

        # Test duration histogram
        self.test_duration_seconds = Histogram(
            name="cardlink_test_duration_seconds",
            documentation="Test execution time in seconds",
            labelnames=["suite_name", "test_name"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
            registry=self.registry,
        )

        # Test suite duration histogram
        self.test_suite_duration_seconds = Histogram(
            name="cardlink_test_suite_duration_seconds",
            documentation="Test suite execution time in seconds",
            labelnames=["suite_name"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0],
            registry=self.registry,
        )

        # Tests running gauge
        self.tests_running = Gauge(
            name="cardlink_tests_running",
            documentation="Number of tests currently running",
            labelnames=["suite_name"],
            registry=self.registry,
        )

    def _create_system_metrics(self) -> None:
        """Create system and resource metrics."""
        # CPU usage gauge
        self.system_cpu_usage_percent = Gauge(
            name="cardlink_system_cpu_usage_percent",
            documentation="System CPU usage percentage",
            registry=self.registry,
        )

        # Memory usage gauge
        self.system_memory_usage_bytes = Gauge(
            name="cardlink_system_memory_usage_bytes",
            documentation="System memory usage in bytes",
            registry=self.registry,
        )

        # Disk usage gauge
        self.system_disk_usage_bytes = Gauge(
            name="cardlink_system_disk_usage_bytes",
            documentation="System disk usage in bytes",
            labelnames=["path"],
            registry=self.registry,
        )

        # Network bytes counter
        self.system_network_bytes_total = Counter(
            name="cardlink_system_network_bytes_total",
            documentation="Total network bytes transferred",
            labelnames=["direction", "interface"],  # sent/received
            registry=self.registry,
        )

        # Process uptime gauge
        self.system_process_uptime_seconds = Gauge(
            name="cardlink_system_process_uptime_seconds",
            documentation="Process uptime in seconds",
            registry=self.registry,
        )

        # Thread count gauge
        self.system_threads_active = Gauge(
            name="cardlink_system_threads_active",
            documentation="Number of active threads",
            registry=self.registry,
        )

    def _create_database_metrics(self) -> None:
        """Create database-related metrics."""
        # Database connections gauge
        self.database_connections_active = Gauge(
            name="cardlink_database_connections_active",
            documentation="Number of active database connections",
            registry=self.registry,
        )

        # Database query duration histogram
        self.database_query_duration_seconds = Histogram(
            name="cardlink_database_query_duration_seconds",
            documentation="Database query execution time in seconds",
            labelnames=["operation", "table"],  # select/insert/update/delete
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry,
        )

        # Database operations counter
        self.database_operations_total = Counter(
            name="cardlink_database_operations_total",
            documentation="Total number of database operations",
            labelnames=["operation", "table", "status"],  # success/error
            registry=self.registry,
        )

        # Database errors counter
        self.database_errors_total = Counter(
            name="cardlink_database_errors_total",
            documentation="Total number of database errors",
            labelnames=["error_type", "operation"],
            registry=self.registry,
        )

    def _create_info_metrics(self) -> None:
        """Create informational metrics."""
        # Application info
        self.application_info = Info(
            name="cardlink_application",
            documentation="CardLink application information",
            registry=self.registry,
        )

        # Set application info
        self.application_info.info(
            {
                "name": "cardlink",
                "description": "GlobalPlatform Amendment B (SCP81) UICC Test Platform",
            }
        )

    def get_all_metrics(self) -> dict:
        """Get all registered metrics.

        Returns:
            Dictionary mapping metric names to metric objects.

        Example:
            >>> registry = MetricsRegistry()
            >>> metrics = registry.get_all_metrics()
            >>> print(metrics.keys())
        """
        return {
            # APDU metrics
            "apdu_commands_total": self.apdu_commands_total,
            "apdu_responses_total": self.apdu_responses_total,
            "apdu_errors_total": self.apdu_errors_total,
            "apdu_response_time_seconds": self.apdu_response_time_seconds,
            "apdu_data_bytes": self.apdu_data_bytes,
            # Session metrics
            "active_sessions": self.active_sessions,
            "session_duration_seconds": self.session_duration_seconds,
            "session_errors_total": self.session_errors_total,
            "sessions_total": self.sessions_total,
            # BIP metrics
            "bip_connections_active": self.bip_connections_active,
            "bip_bytes_transferred_total": self.bip_bytes_transferred_total,
            "bip_connection_duration_seconds": self.bip_connection_duration_seconds,
            "bip_errors_total": self.bip_errors_total,
            # TLS metrics
            "tls_handshakes_total": self.tls_handshakes_total,
            "tls_handshake_duration_seconds": self.tls_handshake_duration_seconds,
            "tls_connections_active": self.tls_connections_active,
            "tls_errors_total": self.tls_errors_total,
            # Device metrics
            "devices_connected": self.devices_connected,
            "device_errors_total": self.device_errors_total,
            "at_command_duration_seconds": self.at_command_duration_seconds,
            "adb_operation_duration_seconds": self.adb_operation_duration_seconds,
            "device_operations_total": self.device_operations_total,
            # Test metrics
            "test_results_total": self.test_results_total,
            "test_duration_seconds": self.test_duration_seconds,
            "test_suite_duration_seconds": self.test_suite_duration_seconds,
            "tests_running": self.tests_running,
            # System metrics
            "system_cpu_usage_percent": self.system_cpu_usage_percent,
            "system_memory_usage_bytes": self.system_memory_usage_bytes,
            "system_disk_usage_bytes": self.system_disk_usage_bytes,
            "system_network_bytes_total": self.system_network_bytes_total,
            "system_process_uptime_seconds": self.system_process_uptime_seconds,
            "system_threads_active": self.system_threads_active,
            # Database metrics
            "database_connections_active": self.database_connections_active,
            "database_query_duration_seconds": self.database_query_duration_seconds,
            "database_operations_total": self.database_operations_total,
            "database_errors_total": self.database_errors_total,
            # Info metrics
            "application_info": self.application_info,
        }
