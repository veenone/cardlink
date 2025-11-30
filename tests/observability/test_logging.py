"""Unit tests for structured logging.

Tests JSON formatting, trace context, and logger manager functionality.
"""

import json
import logging
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from cardlink.observability.config import LoggingConfig
from cardlink.observability.logging.manager import LoggerManager, get_logger
from cardlink.observability.logging.structured import (
    StructuredFormatter,
    TextFormatter,
)


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter for testing."""
        return StructuredFormatter(include_trace_context=False)

    @pytest.fixture
    def log_record(self):
        """Create a basic log record."""
        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_format_basic_message(self, formatter, log_record):
        """Test formatting a basic log message."""
        output = formatter.format(log_record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "cardlink.test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_timestamp_format(self, formatter, log_record):
        """Test timestamp is ISO 8601 format."""
        output = formatter.format(log_record)
        data = json.loads(output)

        # Should be ISO 8601 with microseconds and Z suffix
        timestamp = data["timestamp"]
        assert "T" in timestamp
        assert timestamp.endswith("+00:00")

    def test_format_with_args(self, formatter):
        """Test formatting message with arguments."""
        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Value is %s",
            args=("hello",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Value is hello"

    def test_format_with_extra_fields(self, formatter, log_record):
        """Test formatting with extra fields from record."""
        log_record.user_id = 123
        log_record.session_id = "sess_001"

        output = formatter.format(log_record)
        data = json.loads(output)

        assert data["user_id"] == 123
        assert data["session_id"] == "sess_001"

    def test_format_with_exception(self, formatter):
        """Test formatting with exception info."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]
        assert data["exception"]["traceback"] is not None

    def test_static_extra_fields(self):
        """Test adding static extra fields."""
        formatter = StructuredFormatter(
            include_trace_context=False,
            extra_fields={"service": "cardlink", "version": "1.0.0"},
        )

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["service"] == "cardlink"
        assert data["version"] == "1.0.0"

    def test_source_location(self):
        """Test including source location."""
        formatter = StructuredFormatter(
            include_trace_context=False,
            include_source_location=True,
        )

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "source" in data
        assert data["source"]["file"] == "test.py"
        assert data["source"]["line"] == 42

    def test_trace_context_disabled(self):
        """Test trace context is not included when disabled."""
        formatter = StructuredFormatter(include_trace_context=False)

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "trace_id" not in data
        assert "span_id" not in data

    def test_trace_context_with_mock(self):
        """Test trace context is included when available."""
        formatter = StructuredFormatter(include_trace_context=True)

        # Mock OpenTelemetry trace context
        mock_ctx = MagicMock()
        mock_ctx.trace_id = 0x12345678901234567890123456789012
        mock_ctx.span_id = 0x1234567890123456

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = mock_ctx

        with patch(
            "cardlink.observability.logging.structured.trace.get_current_span",
            return_value=mock_span,
        ):
            record = logging.LogRecord(
                name="cardlink.test",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert "trace_id" in data
            assert "span_id" in data

    def test_json_serialization_fallback(self, formatter):
        """Test fallback for non-serializable objects."""

        class CustomObject:
            pass

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.custom = CustomObject()

        # Should not raise, should serialize to string
        output = formatter.format(record)
        data = json.loads(output)

        assert "custom" in data
        assert "CustomObject" in data["custom"]


class TestTextFormatter:
    """Tests for TextFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter for testing."""
        return TextFormatter(include_trace_context=False)

    def test_format_basic_message(self, formatter):
        """Test formatting a basic text log message."""
        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "[cardlink.test]" in output
        assert "Test message" in output
        assert "T" in output  # ISO timestamp
        assert "Z" in output

    def test_format_with_source_location(self):
        """Test text format with source location."""
        formatter = TextFormatter(
            include_trace_context=False,
            include_source_location=True,
        )

        record = logging.LogRecord(
            name="cardlink.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "[test.py:42]" in output


class TestLoggerManager:
    """Tests for LoggerManager."""

    @pytest.fixture
    def config(self):
        """Create test logging config."""
        return LoggingConfig(
            level="INFO",
            format="json",
            trace_correlation=False,
        )

    @pytest.fixture
    def text_config(self):
        """Create text format config."""
        return LoggingConfig(
            level="DEBUG",
            format="text",
            trace_correlation=False,
        )

    @pytest.fixture
    def manager(self, config):
        """Create logger manager for testing."""
        mgr = LoggerManager(config)
        yield mgr
        # Cleanup
        if mgr.is_configured:
            mgr.shutdown()

    def test_create_manager(self, config):
        """Test creating logger manager."""
        manager = LoggerManager(config)
        assert manager is not None
        assert manager.config == config
        assert manager.is_configured is False

    def test_configure_manager(self, manager):
        """Test configuring the manager."""
        manager.configure()
        assert manager.is_configured is True

    def test_configure_idempotent(self, manager):
        """Test that configure is idempotent."""
        manager.configure()
        manager.configure()  # Should not raise
        assert manager.is_configured is True

    def test_get_logger(self, manager):
        """Test getting a logger."""
        manager.configure()
        logger = manager.get_logger("test_component")

        assert logger is not None
        assert logger.name == "cardlink.test_component"

    def test_get_logger_with_prefix(self, manager):
        """Test getting logger with existing prefix."""
        manager.configure()
        logger = manager.get_logger("cardlink.test")

        assert logger.name == "cardlink.test"

    def test_get_logger_caching(self, manager):
        """Test that loggers are cached."""
        manager.configure()
        logger1 = manager.get_logger("test")
        logger2 = manager.get_logger("test")

        assert logger1 is logger2

    def test_set_level(self, manager):
        """Test setting log level for component."""
        manager.configure()
        manager.set_level("test", "DEBUG")

        level = manager.get_level("test")
        assert level == "DEBUG"

    def test_set_global_level(self, manager):
        """Test setting global log level."""
        manager.configure()
        manager.get_logger("comp1")
        manager.get_logger("comp2")

        manager.set_global_level("WARNING")

        assert manager.get_level("comp1") == "WARNING"
        assert manager.get_level("comp2") == "WARNING"

    def test_registered_loggers(self, manager):
        """Test listing registered loggers."""
        manager.configure()
        manager.get_logger("comp1")
        manager.get_logger("comp2")

        loggers = manager.registered_loggers

        assert "cardlink.comp1" in loggers
        assert "cardlink.comp2" in loggers

    def test_add_extra_field(self, manager):
        """Test adding static extra field."""
        manager.configure()
        manager.add_extra_field("environment", "test")

        # Verify field was added to formatter
        assert manager._formatter.extra_fields["environment"] == "test"

    def test_remove_extra_field(self, manager):
        """Test removing static extra field."""
        manager.configure()
        manager.add_extra_field("environment", "test")
        manager.remove_extra_field("environment")

        assert "environment" not in manager._formatter.extra_fields

    def test_text_format_manager(self, text_config):
        """Test manager with text format."""
        manager = LoggerManager(text_config)
        manager.configure()

        try:
            assert isinstance(manager._formatter, TextFormatter)
        finally:
            manager.shutdown()

    def test_shutdown_manager(self, manager):
        """Test shutting down the manager."""
        manager.configure()
        manager.shutdown()

        assert manager.is_configured is False
        assert len(manager.registered_loggers) == 0

    def test_shutdown_not_configured(self, config):
        """Test shutdown when not configured."""
        manager = LoggerManager(config)
        manager.shutdown()  # Should not raise


class TestLoggerManagerIntegration:
    """Integration tests for logger manager."""

    @pytest.fixture
    def capture_stream(self):
        """Create a StringIO to capture log output."""
        return StringIO()

    def test_json_log_output(self, capture_stream):
        """Test actual JSON log output."""
        config = LoggingConfig(level="INFO", format="json", trace_correlation=False)
        manager = LoggerManager(config)

        # Replace handler with our capture stream
        handler = logging.StreamHandler(capture_stream)
        formatter = StructuredFormatter(include_trace_context=False)
        handler.setFormatter(formatter)

        logger = logging.getLogger("cardlink.integration_test")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            logger.info("Integration test message", extra={"test_key": "test_value"})

            output = capture_stream.getvalue()
            data = json.loads(output.strip())

            assert data["message"] == "Integration test message"
            assert data["level"] == "INFO"
            assert data["test_key"] == "test_value"

        finally:
            logger.removeHandler(handler)

    def test_text_log_output(self, capture_stream):
        """Test actual text log output."""
        handler = logging.StreamHandler(capture_stream)
        formatter = TextFormatter(include_trace_context=False)
        handler.setFormatter(formatter)

        logger = logging.getLogger("cardlink.text_test")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            logger.warning("Warning message")

            output = capture_stream.getvalue()

            assert "WARNING" in output
            assert "Warning message" in output
            assert "[cardlink.text_test]" in output

        finally:
            logger.removeHandler(handler)


class TestGetLoggerFunction:
    """Tests for the get_logger convenience function."""

    def test_get_logger_simple_name(self):
        """Test getting logger with simple name."""
        logger = get_logger("my_component")
        assert logger.name == "cardlink.my_component"

    def test_get_logger_with_prefix(self):
        """Test getting logger with cardlink prefix."""
        logger = get_logger("cardlink.existing")
        assert logger.name == "cardlink.existing"

    def test_get_logger_consistency(self):
        """Test that same logger is returned for same name."""
        logger1 = get_logger("consistent")
        logger2 = get_logger("consistent")
        assert logger1 is logger2
