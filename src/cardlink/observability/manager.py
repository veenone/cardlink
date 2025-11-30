"""Observability manager for centralized observability control.

This module provides a singleton manager that coordinates all observability
components: metrics, tracing, health checks, and logging.
"""

import logging
import threading
from typing import Optional

from cardlink.observability.config import ObservabilityConfig

# Singleton instance
_observability_manager: Optional["ObservabilityManager"] = None
_lock = threading.Lock()

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Singleton manager for all observability components.

    This manager provides centralized control over metrics collection,
    distributed tracing, health checks, and structured logging.

    Example:
        >>> # Get singleton instance
        >>> obs = get_observability()
        >>>
        >>> # Initialize with default config
        >>> obs.initialize()
        >>>
        >>> # Initialize with custom config
        >>> config = ObservabilityConfig.from_env()
        >>> obs.initialize(config)
        >>>
        >>> # Access components
        >>> obs.metrics.record_apdu_command("SELECT", "physical")
        >>> with obs.tracer.start_span("process_session") as span:
        ...     # Your code here
        ...     pass
        >>> health_status = obs.health.run_all_checks()
        >>> logger = obs.logger.get_logger("my_component")
    """

    def __init__(self) -> None:
        """Initialize observability manager (private constructor)."""
        self._config: Optional[ObservabilityConfig] = None
        self._initialized = False
        self._metrics = None
        self._tracer = None
        self._health = None
        self._logger_manager = None

    def initialize(self, config: Optional[ObservabilityConfig] = None) -> None:
        """Initialize all observability components.

        Args:
            config: Observability configuration. If None, loads from environment.

        Raises:
            ValueError: If configuration is invalid.
            RuntimeError: If already initialized.

        Example:
            >>> obs = get_observability()
            >>> obs.initialize()  # Use environment config
            >>>
            >>> # Or with custom config
            >>> config = ObservabilityConfig(
            ...     metrics=MetricsConfig(enabled=True, port=9090),
            ...     tracing=TracingConfig(enabled=False),
            ... )
            >>> obs.initialize(config)
        """
        if self._initialized:
            logger.warning("ObservabilityManager already initialized")
            return

        # Load and validate config
        self._config = config or ObservabilityConfig.from_env()
        self._config.validate()

        logger.info("Initializing observability components")

        # Initialize components based on config
        if self._config.metrics.enabled:
            self._initialize_metrics()

        if self._config.tracing.enabled:
            self._initialize_tracing()

        if self._config.health.enabled:
            self._initialize_health()

        # Always initialize logging
        self._initialize_logging()

        self._initialized = True
        logger.info("Observability initialization complete")

    def shutdown(self) -> None:
        """Shutdown all observability components gracefully.

        Example:
            >>> obs = get_observability()
            >>> obs.shutdown()
        """
        if not self._initialized:
            return

        logger.info("Shutting down observability components")

        # Shutdown metrics
        if self._metrics:
            try:
                if hasattr(self._metrics, "shutdown"):
                    self._metrics.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down metrics: {e}")

        # Shutdown tracing
        if self._tracer:
            try:
                if hasattr(self._tracer, "shutdown"):
                    self._tracer.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down tracing: {e}")

        # Shutdown health
        if self._health:
            try:
                if hasattr(self._health, "shutdown"):
                    self._health.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down health: {e}")

        # Shutdown logging (do last so we can log errors above)
        if self._logger_manager:
            try:
                if hasattr(self._logger_manager, "shutdown"):
                    self._logger_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down logging: {e}")

        self._initialized = False
        logger.info("Observability shutdown complete")

    def _initialize_metrics(self) -> None:
        """Initialize metrics collection."""
        logger.info(f"Initializing metrics on port {self._config.metrics.port}")
        from cardlink.observability.metrics.collector import MetricsCollector

        self._metrics = MetricsCollector(self._config.metrics)
        self._metrics.start()

    def _initialize_tracing(self) -> None:
        """Initialize distributed tracing."""
        logger.info(
            f"Initializing tracing with endpoint {self._config.tracing.otlp_endpoint}"
        )
        from cardlink.observability.tracing.provider import TracingProvider

        self._tracer = TracingProvider(self._config.tracing)
        self._tracer.start()

    def _initialize_health(self) -> None:
        """Initialize health checks."""
        logger.info(f"Initializing health checks on port {self._config.health.port}")
        from cardlink.observability.health.checker import HealthChecker

        self._health = HealthChecker(self._config.health)
        self._health.start()

    def _initialize_logging(self) -> None:
        """Initialize structured logging."""
        logger.info(
            f"Initializing logging with level {self._config.logging.level}, "
            f"format {self._config.logging.format}"
        )
        from cardlink.observability.logging.manager import LoggerManager

        self._logger_manager = LoggerManager(self._config.logging)
        self._logger_manager.configure()

    @property
    def config(self) -> ObservabilityConfig:
        """Get current configuration.

        Returns:
            Current observability configuration.

        Raises:
            RuntimeError: If not initialized.
        """
        if not self._initialized or not self._config:
            raise RuntimeError("ObservabilityManager not initialized")
        return self._config

    @property
    def metrics(self):
        """Get metrics collector.

        Returns:
            Metrics collector instance.

        Raises:
            RuntimeError: If not initialized or metrics disabled.
        """
        if not self._initialized:
            raise RuntimeError("ObservabilityManager not initialized")
        if not self._config.metrics.enabled:
            raise RuntimeError("Metrics not enabled")
        return self._metrics

    @property
    def tracer(self):
        """Get tracing provider.

        Returns:
            Tracing provider instance.

        Raises:
            RuntimeError: If not initialized or tracing disabled.
        """
        if not self._initialized:
            raise RuntimeError("ObservabilityManager not initialized")
        if not self._config.tracing.enabled:
            raise RuntimeError("Tracing not enabled")
        return self._tracer

    @property
    def health(self):
        """Get health checker.

        Returns:
            Health checker instance.

        Raises:
            RuntimeError: If not initialized or health checks disabled.
        """
        if not self._initialized:
            raise RuntimeError("ObservabilityManager not initialized")
        if not self._config.health.enabled:
            raise RuntimeError("Health checks not enabled")
        return self._health

    @property
    def logger(self):
        """Get logger manager.

        Returns:
            Logger manager instance.

        Raises:
            RuntimeError: If not initialized.
        """
        if not self._initialized:
            raise RuntimeError("ObservabilityManager not initialized")
        return self._logger_manager

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized.

        Returns:
            True if initialized, False otherwise.
        """
        return self._initialized


def get_observability() -> ObservabilityManager:
    """Get the singleton ObservabilityManager instance.

    This function implements thread-safe singleton pattern for accessing
    the global observability manager.

    Returns:
        Singleton ObservabilityManager instance.

    Example:
        >>> # Get instance
        >>> obs = get_observability()
        >>>
        >>> # Initialize if needed
        >>> if not obs.is_initialized:
        ...     obs.initialize()
        >>>
        >>> # Use observability features
        >>> obs.metrics.record_apdu_command("SELECT", "physical")
    """
    global _observability_manager

    if _observability_manager is None:
        with _lock:
            if _observability_manager is None:
                _observability_manager = ObservabilityManager()

    return _observability_manager


def reset_observability() -> None:
    """Reset the singleton instance (mainly for testing).

    Warning:
        This should only be used in tests. In production code,
        use the shutdown() method instead.

    Example:
        >>> # In tests
        >>> obs = get_observability()
        >>> obs.initialize()
        >>> # ... test code ...
        >>> obs.shutdown()
        >>> reset_observability()  # Clean up for next test
    """
    global _observability_manager

    with _lock:
        if _observability_manager is not None:
            if _observability_manager.is_initialized:
                _observability_manager.shutdown()
        _observability_manager = None
