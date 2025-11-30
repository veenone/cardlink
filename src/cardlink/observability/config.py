"""Observability configuration module.

This module provides comprehensive configuration for all observability components.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricsConfig:
    """Configuration for Prometheus metrics."""

    enabled: bool = True
    port: int = 9090
    path: str = "/metrics"
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    collection_interval: int = 15  # seconds

    @classmethod
    def from_env(cls) -> "MetricsConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("GP_METRICS_ENABLED", "true").lower() == "true",
            port=int(os.getenv("GP_METRICS_PORT", "9090")),
            path=os.getenv("GP_METRICS_PATH", "/metrics"),
            auth_username=os.getenv("GP_METRICS_AUTH_USERNAME"),
            auth_password=os.getenv("GP_METRICS_AUTH_PASSWORD"),
            collection_interval=int(os.getenv("GP_METRICS_INTERVAL", "15")),
        )


@dataclass
class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    enabled: bool = False
    otlp_endpoint: Optional[str] = None
    otlp_protocol: str = "grpc"  # or "http"
    service_name: str = "cardlink"
    service_version: str = "1.0.0"
    sample_rate: float = 1.0  # 1.0 = 100% sampling

    @classmethod
    def from_env(cls) -> "TracingConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("GP_TRACING_ENABLED", "false").lower() == "true",
            otlp_endpoint=os.getenv("GP_OTLP_ENDPOINT"),
            otlp_protocol=os.getenv("GP_OTLP_PROTOCOL", "grpc"),
            service_name=os.getenv("GP_SERVICE_NAME", "cardlink"),
            service_version=os.getenv("GP_SERVICE_VERSION", "1.0.0"),
            sample_rate=float(os.getenv("GP_TRACE_SAMPLE_RATE", "1.0")),
        )


@dataclass
class HealthConfig:
    """Configuration for health checks."""

    enabled: bool = True
    port: int = 8080
    check_timeout: float = 5.0  # seconds

    @classmethod
    def from_env(cls) -> "HealthConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("GP_HEALTH_ENABLED", "true").lower() == "true",
            port=int(os.getenv("GP_HEALTH_PORT", "8080")),
            check_timeout=float(os.getenv("GP_HEALTH_TIMEOUT", "5.0")),
        )


@dataclass
class LoggingConfig:
    """Configuration for structured logging."""

    level: str = "INFO"
    format: str = "json"  # or "text"
    trace_correlation: bool = True
    output_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables."""
        return cls(
            level=os.getenv("GP_LOG_LEVEL", "INFO").upper(),
            format=os.getenv("GP_LOG_FORMAT", "json").lower(),
            trace_correlation=os.getenv("GP_LOG_TRACE_CORRELATION", "true").lower()
            == "true",
            output_file=os.getenv("GP_LOG_FILE"),
        )


@dataclass
class ObservabilityConfig:
    """Comprehensive observability configuration.

    This dataclass provides configuration for all observability components:
    metrics, tracing, health checks, and logging.

    Example:
        >>> # Create from environment variables
        >>> config = ObservabilityConfig.from_env()
        >>>
        >>> # Create programmatically
        >>> config = ObservabilityConfig(
        ...     metrics=MetricsConfig(enabled=True, port=9090),
        ...     tracing=TracingConfig(enabled=True, otlp_endpoint="localhost:4317"),
        ...     health=HealthConfig(enabled=True, port=8080),
        ...     logging=LoggingConfig(level="INFO", format="json"),
        ... )
        >>>
        >>> # Check if features are enabled
        >>> if config.metrics.enabled:
        ...     print(f"Metrics endpoint: http://localhost:{config.metrics.port}{config.metrics.path}")
    """

    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create complete configuration from environment variables.

        Reads configuration from environment variables with GP_ prefix.

        Environment Variables:
            Metrics:
                GP_METRICS_ENABLED: Enable metrics (default: true)
                GP_METRICS_PORT: Metrics HTTP port (default: 9090)
                GP_METRICS_PATH: Metrics endpoint path (default: /metrics)
                GP_METRICS_AUTH_USERNAME: HTTP Basic auth username (optional)
                GP_METRICS_AUTH_PASSWORD: HTTP Basic auth password (optional)
                GP_METRICS_INTERVAL: System metrics collection interval in seconds (default: 15)

            Tracing:
                GP_TRACING_ENABLED: Enable tracing (default: false)
                GP_OTLP_ENDPOINT: OTLP collector endpoint (e.g., localhost:4317)
                GP_OTLP_PROTOCOL: OTLP protocol - grpc or http (default: grpc)
                GP_SERVICE_NAME: Service name for traces (default: cardlink)
                GP_SERVICE_VERSION: Service version (default: 1.0.0)
                GP_TRACE_SAMPLE_RATE: Trace sampling rate 0.0-1.0 (default: 1.0)

            Health:
                GP_HEALTH_ENABLED: Enable health checks (default: true)
                GP_HEALTH_PORT: Health check HTTP port (default: 8080)
                GP_HEALTH_TIMEOUT: Health check timeout in seconds (default: 5.0)

            Logging:
                GP_LOG_LEVEL: Log level - DEBUG, INFO, WARNING, ERROR (default: INFO)
                GP_LOG_FORMAT: Log format - json or text (default: json)
                GP_LOG_TRACE_CORRELATION: Include trace IDs in logs (default: true)
                GP_LOG_FILE: Log file path (optional, defaults to stdout)

        Returns:
            Complete ObservabilityConfig with all sub-configurations.

        Example:
            >>> # Set environment variables
            >>> os.environ["GP_METRICS_PORT"] = "9100"
            >>> os.environ["GP_TRACING_ENABLED"] = "true"
            >>> os.environ["GP_OTLP_ENDPOINT"] = "localhost:4317"
            >>>
            >>> # Create config
            >>> config = ObservabilityConfig.from_env()
            >>> assert config.metrics.port == 9100
            >>> assert config.tracing.enabled is True
        """
        return cls(
            metrics=MetricsConfig.from_env(),
            tracing=TracingConfig.from_env(),
            health=HealthConfig.from_env(),
            logging=LoggingConfig.from_env(),
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid.

        Example:
            >>> config = ObservabilityConfig()
            >>> config.metrics.port = -1
            >>> config.validate()  # Raises ValueError
        """
        # Validate metrics
        if self.metrics.enabled:
            if not (1 <= self.metrics.port <= 65535):
                raise ValueError(f"Invalid metrics port: {self.metrics.port}")
            if not self.metrics.path.startswith("/"):
                raise ValueError(f"Metrics path must start with /: {self.metrics.path}")
            if self.metrics.collection_interval < 1:
                raise ValueError(
                    f"Collection interval must be >= 1: {self.metrics.collection_interval}"
                )

        # Validate tracing
        if self.tracing.enabled:
            if not self.tracing.otlp_endpoint:
                raise ValueError("OTLP endpoint required when tracing is enabled")
            if self.tracing.otlp_protocol not in ("grpc", "http"):
                raise ValueError(
                    f"Invalid OTLP protocol: {self.tracing.otlp_protocol}"
                )
            if not (0.0 <= self.tracing.sample_rate <= 1.0):
                raise ValueError(
                    f"Sample rate must be 0.0-1.0: {self.tracing.sample_rate}"
                )

        # Validate health
        if self.health.enabled:
            if not (1 <= self.health.port <= 65535):
                raise ValueError(f"Invalid health port: {self.health.port}")
            if self.health.check_timeout <= 0:
                raise ValueError(
                    f"Check timeout must be positive: {self.health.check_timeout}"
                )

        # Validate logging
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.logging.level not in valid_levels:
            raise ValueError(
                f"Invalid log level: {self.logging.level}. Must be one of {valid_levels}"
            )
        if self.logging.format not in ("json", "text"):
            raise ValueError(
                f"Invalid log format: {self.logging.format}. Must be 'json' or 'text'"
            )
