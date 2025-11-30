"""Unit tests for observability configuration module.

Tests configuration parsing, validation, defaults, and environment variable loading.
"""

import pytest

from cardlink.observability.config import (
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    TracingConfig,
)


class TestMetricsConfig:
    """Tests for MetricsConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MetricsConfig()
        assert config.enabled is True
        assert config.port == 9090
        assert config.path == "/metrics"
        assert config.auth_username is None
        assert config.auth_password is None
        assert config.collection_interval == 15

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MetricsConfig(
            enabled=False,
            port=9100,
            path="/custom-metrics",
            auth_username="user",
            auth_password="pass",
            collection_interval=30,
        )
        assert config.enabled is False
        assert config.port == 9100
        assert config.path == "/custom-metrics"
        assert config.auth_username == "user"
        assert config.auth_password == "pass"
        assert config.collection_interval == 30

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        # Clear any existing env vars
        for key in [
            "GP_METRICS_ENABLED",
            "GP_METRICS_PORT",
            "GP_METRICS_PATH",
            "GP_METRICS_AUTH_USERNAME",
            "GP_METRICS_AUTH_PASSWORD",
            "GP_METRICS_INTERVAL",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = MetricsConfig.from_env()
        assert config.enabled is True
        assert config.port == 9090
        assert config.path == "/metrics"
        assert config.auth_username is None
        assert config.auth_password is None
        assert config.collection_interval == 15

    def test_from_env_custom(self, env_metrics_config):
        """Test from_env with custom environment variables."""
        config = MetricsConfig.from_env()
        assert config.enabled is True
        assert config.port == 19092
        assert config.path == "/test-metrics"
        assert config.auth_username == "env_user"
        assert config.auth_password == "env_pass"
        assert config.collection_interval == 30

    def test_from_env_disabled(self, monkeypatch):
        """Test from_env with metrics disabled."""
        monkeypatch.setenv("GP_METRICS_ENABLED", "false")
        config = MetricsConfig.from_env()
        assert config.enabled is False


class TestTracingConfig:
    """Tests for TracingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TracingConfig()
        assert config.enabled is False
        assert config.otlp_endpoint is None
        assert config.otlp_protocol == "grpc"
        assert config.service_name == "cardlink"
        assert config.service_version == "1.0.0"
        assert config.sample_rate == 1.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TracingConfig(
            enabled=True,
            otlp_endpoint="localhost:4317",
            otlp_protocol="http",
            service_name="test-service",
            service_version="2.0.0",
            sample_rate=0.5,
        )
        assert config.enabled is True
        assert config.otlp_endpoint == "localhost:4317"
        assert config.otlp_protocol == "http"
        assert config.service_name == "test-service"
        assert config.service_version == "2.0.0"
        assert config.sample_rate == 0.5

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        for key in [
            "GP_TRACING_ENABLED",
            "GP_OTLP_ENDPOINT",
            "GP_OTLP_PROTOCOL",
            "GP_SERVICE_NAME",
            "GP_SERVICE_VERSION",
            "GP_TRACE_SAMPLE_RATE",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = TracingConfig.from_env()
        assert config.enabled is False
        assert config.otlp_endpoint is None
        assert config.otlp_protocol == "grpc"
        assert config.service_name == "cardlink"
        assert config.service_version == "1.0.0"
        assert config.sample_rate == 1.0

    def test_from_env_custom(self, env_tracing_config):
        """Test from_env with custom environment variables."""
        config = TracingConfig.from_env()
        assert config.enabled is True
        assert config.otlp_endpoint == "localhost:4318"
        assert config.otlp_protocol == "http"
        assert config.service_name == "cardlink-env-test"
        assert config.service_version == "2.0.0"
        assert config.sample_rate == 0.5


class TestHealthConfig:
    """Tests for HealthConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HealthConfig()
        assert config.enabled is True
        assert config.port == 8080
        assert config.check_timeout == 5.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HealthConfig(enabled=False, port=8081, check_timeout=10.0)
        assert config.enabled is False
        assert config.port == 8081
        assert config.check_timeout == 10.0

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        for key in ["GP_HEALTH_ENABLED", "GP_HEALTH_PORT", "GP_HEALTH_TIMEOUT"]:
            monkeypatch.delenv(key, raising=False)

        config = HealthConfig.from_env()
        assert config.enabled is True
        assert config.port == 8080
        assert config.check_timeout == 5.0

    def test_from_env_custom(self, env_health_config):
        """Test from_env with custom environment variables."""
        config = HealthConfig.from_env()
        assert config.enabled is True
        assert config.port == 18081
        assert config.check_timeout == 10.0


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.trace_correlation is True
        assert config.output_file is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            level="DEBUG",
            format="text",
            trace_correlation=False,
            output_file="/var/log/app.log",
        )
        assert config.level == "DEBUG"
        assert config.format == "text"
        assert config.trace_correlation is False
        assert config.output_file == "/var/log/app.log"

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        for key in [
            "GP_LOG_LEVEL",
            "GP_LOG_FORMAT",
            "GP_LOG_TRACE_CORRELATION",
            "GP_LOG_FILE",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = LoggingConfig.from_env()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.trace_correlation is True
        assert config.output_file is None

    def test_from_env_custom(self, env_logging_config):
        """Test from_env with custom environment variables."""
        config = LoggingConfig.from_env()
        assert config.level == "DEBUG"
        assert config.format == "text"
        assert config.trace_correlation is False
        assert config.output_file == "/tmp/test.log"

    def test_from_env_uppercase_level(self, monkeypatch):
        """Test that log level is uppercased."""
        monkeypatch.setenv("GP_LOG_LEVEL", "debug")
        config = LoggingConfig.from_env()
        assert config.level == "DEBUG"


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ObservabilityConfig()
        assert isinstance(config.metrics, MetricsConfig)
        assert isinstance(config.tracing, TracingConfig)
        assert isinstance(config.health, HealthConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_custom_components(self):
        """Test custom component configurations."""
        metrics = MetricsConfig(port=9100)
        tracing = TracingConfig(enabled=True, otlp_endpoint="localhost:4317")
        health = HealthConfig(port=8081)
        logging = LoggingConfig(level="DEBUG")

        config = ObservabilityConfig(
            metrics=metrics,
            tracing=tracing,
            health=health,
            logging=logging,
        )

        assert config.metrics.port == 9100
        assert config.tracing.enabled is True
        assert config.tracing.otlp_endpoint == "localhost:4317"
        assert config.health.port == 8081
        assert config.logging.level == "DEBUG"

    def test_from_env(self, env_all_config):
        """Test from_env creates complete config from environment."""
        config = ObservabilityConfig.from_env()

        # Verify metrics
        assert config.metrics.enabled is True
        assert config.metrics.port == 19092

        # Verify tracing
        assert config.tracing.enabled is True
        assert config.tracing.otlp_endpoint == "localhost:4318"

        # Verify health
        assert config.health.enabled is True
        assert config.health.port == 18081

        # Verify logging
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "text"


class TestObservabilityConfigValidation:
    """Tests for ObservabilityConfig.validate() method."""

    def test_valid_default_config(self):
        """Test validation passes for default config."""
        config = ObservabilityConfig()
        config.validate()  # Should not raise

    def test_valid_full_config(self):
        """Test validation passes for fully configured config."""
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=True, port=9090),
            tracing=TracingConfig(
                enabled=True, otlp_endpoint="localhost:4317", sample_rate=0.5
            ),
            health=HealthConfig(enabled=True, port=8080),
            logging=LoggingConfig(level="INFO", format="json"),
        )
        config.validate()  # Should not raise

    def test_invalid_metrics_port_low(self):
        """Test validation fails for port < 1."""
        config = ObservabilityConfig(metrics=MetricsConfig(port=0))
        with pytest.raises(ValueError, match="Invalid metrics port"):
            config.validate()

    def test_invalid_metrics_port_high(self):
        """Test validation fails for port > 65535."""
        config = ObservabilityConfig(metrics=MetricsConfig(port=70000))
        with pytest.raises(ValueError, match="Invalid metrics port"):
            config.validate()

    def test_invalid_metrics_path(self):
        """Test validation fails for path not starting with /."""
        config = ObservabilityConfig(metrics=MetricsConfig(path="metrics"))
        with pytest.raises(ValueError, match="Metrics path must start with /"):
            config.validate()

    def test_invalid_collection_interval(self):
        """Test validation fails for collection_interval < 1."""
        config = ObservabilityConfig(metrics=MetricsConfig(collection_interval=0))
        with pytest.raises(ValueError, match="Collection interval must be >= 1"):
            config.validate()

    def test_tracing_requires_endpoint(self):
        """Test validation fails when tracing enabled without endpoint."""
        config = ObservabilityConfig(
            tracing=TracingConfig(enabled=True, otlp_endpoint=None)
        )
        with pytest.raises(ValueError, match="OTLP endpoint required"):
            config.validate()

    def test_invalid_otlp_protocol(self):
        """Test validation fails for invalid OTLP protocol."""
        config = ObservabilityConfig(
            tracing=TracingConfig(
                enabled=True, otlp_endpoint="localhost:4317", otlp_protocol="invalid"
            )
        )
        with pytest.raises(ValueError, match="Invalid OTLP protocol"):
            config.validate()

    def test_invalid_sample_rate_negative(self):
        """Test validation fails for sample_rate < 0."""
        config = ObservabilityConfig(
            tracing=TracingConfig(
                enabled=True, otlp_endpoint="localhost:4317", sample_rate=-0.1
            )
        )
        with pytest.raises(ValueError, match="Sample rate must be 0.0-1.0"):
            config.validate()

    def test_invalid_sample_rate_high(self):
        """Test validation fails for sample_rate > 1."""
        config = ObservabilityConfig(
            tracing=TracingConfig(
                enabled=True, otlp_endpoint="localhost:4317", sample_rate=1.5
            )
        )
        with pytest.raises(ValueError, match="Sample rate must be 0.0-1.0"):
            config.validate()

    def test_invalid_health_port(self):
        """Test validation fails for invalid health port."""
        config = ObservabilityConfig(health=HealthConfig(port=0))
        with pytest.raises(ValueError, match="Invalid health port"):
            config.validate()

    def test_invalid_check_timeout(self):
        """Test validation fails for check_timeout <= 0."""
        config = ObservabilityConfig(health=HealthConfig(check_timeout=0))
        with pytest.raises(ValueError, match="Check timeout must be positive"):
            config.validate()

    def test_invalid_log_level(self):
        """Test validation fails for invalid log level."""
        config = ObservabilityConfig(logging=LoggingConfig(level="INVALID"))
        with pytest.raises(ValueError, match="Invalid log level"):
            config.validate()

    def test_invalid_log_format(self):
        """Test validation fails for invalid log format."""
        config = ObservabilityConfig(logging=LoggingConfig(format="xml"))
        with pytest.raises(ValueError, match="Invalid log format"):
            config.validate()

    def test_disabled_components_skip_validation(self):
        """Test that disabled components skip their validation."""
        # Invalid values but disabled - should pass
        config = ObservabilityConfig(
            metrics=MetricsConfig(enabled=False, port=0),
            tracing=TracingConfig(enabled=False, otlp_endpoint=None),
            health=HealthConfig(enabled=False, port=0),
        )
        config.validate()  # Should not raise

    def test_valid_edge_case_values(self):
        """Test validation passes for edge case valid values."""
        config = ObservabilityConfig(
            metrics=MetricsConfig(port=1, collection_interval=1),
            tracing=TracingConfig(
                enabled=True, otlp_endpoint="localhost:4317", sample_rate=0.0
            ),
            health=HealthConfig(port=65535, check_timeout=0.001),
            logging=LoggingConfig(level="CRITICAL"),
        )
        config.validate()  # Should not raise
