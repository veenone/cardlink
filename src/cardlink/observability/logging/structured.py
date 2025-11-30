"""Structured JSON log formatter with trace context.

This module provides a JSON formatter for structured logging with
OpenTelemetry trace context correlation.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Try to import OpenTelemetry for trace context
try:
    from opentelemetry import trace
    from opentelemetry.trace import INVALID_SPAN_ID, INVALID_TRACE_ID

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    INVALID_TRACE_ID = 0
    INVALID_SPAN_ID = 0


class StructuredFormatter(logging.Formatter):
    """JSON log formatter with structured output and trace context.

    Produces log entries in JSON format with:
    - ISO 8601 timestamps
    - Log level
    - Logger name (component)
    - Message
    - Trace context (trace_id, span_id) when available
    - Extra fields
    - Exception info

    Example output:
        {
            "timestamp": "2024-01-15T10:30:45.123456Z",
            "level": "INFO",
            "logger": "cardlink.server",
            "message": "Session started",
            "trace_id": "abc123...",
            "span_id": "def456...",
            "session_id": "sess_001"
        }
    """

    # Standard fields that are always included
    STANDARD_FIELDS = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "exc_info",
        "exc_text",
        "thread",
        "threadName",
        "taskName",
        "message",
    }

    def __init__(
        self,
        include_trace_context: bool = True,
        include_source_location: bool = False,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the structured formatter.

        Args:
            include_trace_context: Include trace_id and span_id from OpenTelemetry.
            include_source_location: Include file, function, and line number.
            extra_fields: Static fields to include in every log entry.
        """
        super().__init__()
        self.include_trace_context = include_trace_context
        self.include_source_location = include_source_location
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON-encoded log entry.
        """
        log_entry = self._build_log_entry(record)
        return json.dumps(log_entry, default=self._json_serializer)

    def _build_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Build the log entry dictionary.

        Args:
            record: The log record.

        Returns:
            Dictionary with log entry fields.
        """
        # Build base entry with standard fields
        entry: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace context if available and enabled
        if self.include_trace_context:
            trace_context = self._get_trace_context()
            if trace_context:
                entry.update(trace_context)

        # Add source location if enabled
        if self.include_source_location:
            entry["source"] = {
                "file": record.filename,
                "function": record.funcName,
                "line": record.lineno,
            }

        # Add exception info if present
        if record.exc_info:
            entry["exception"] = self._format_exception(record)

        # Add static extra fields
        entry.update(self.extra_fields)

        # Add dynamic extra fields from the record
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_FIELDS and not key.startswith("_"):
                entry[key] = value

        return entry

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """Format timestamp in ISO 8601 format with timezone.

        Args:
            record: The log record.

        Returns:
            ISO 8601 formatted timestamp.
        """
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat(timespec="microseconds")

    def _get_trace_context(self) -> Optional[Dict[str, str]]:
        """Extract trace context from OpenTelemetry.

        Returns:
            Dictionary with trace_id and span_id, or None if not available.
        """
        if not OTEL_AVAILABLE:
            return None

        try:
            span = trace.get_current_span()
            ctx = span.get_span_context()

            if ctx.trace_id == INVALID_TRACE_ID or ctx.span_id == INVALID_SPAN_ID:
                return None

            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
        except Exception:
            return None

    def _format_exception(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format exception information.

        Args:
            record: The log record with exception info.

        Returns:
            Dictionary with exception details.
        """
        exc_type, exc_value, exc_tb = record.exc_info
        return {
            "type": exc_type.__name__ if exc_type else None,
            "message": str(exc_value) if exc_value else None,
            "traceback": traceback.format_exception(exc_type, exc_value, exc_tb)
            if exc_tb
            else None,
        }

    def _json_serializer(self, obj: Any) -> str:
        """Serialize objects that aren't JSON-serializable.

        Args:
            obj: Object to serialize.

        Returns:
            String representation of the object.
        """
        try:
            return str(obj)
        except Exception:
            return f"<unserializable: {type(obj).__name__}>"


class TextFormatter(logging.Formatter):
    """Human-readable text formatter with optional trace context.

    Produces log entries in traditional text format:
        2024-01-15T10:30:45.123Z INFO [cardlink.server] [trace_id=abc123] Session started
    """

    def __init__(
        self,
        include_trace_context: bool = True,
        include_source_location: bool = False,
    ) -> None:
        """Initialize the text formatter.

        Args:
            include_trace_context: Include trace_id in the output.
            include_source_location: Include file:line in the output.
        """
        super().__init__()
        self.include_trace_context = include_trace_context
        self.include_source_location = include_source_location

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as text.

        Args:
            record: The log record to format.

        Returns:
            Formatted text log entry.
        """
        # Timestamp
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Build parts
        parts = [timestamp, record.levelname.ljust(8), f"[{record.name}]"]

        # Add trace context
        if self.include_trace_context and OTEL_AVAILABLE:
            try:
                span = trace.get_current_span()
                ctx = span.get_span_context()
                if ctx.trace_id != INVALID_TRACE_ID:
                    trace_id = format(ctx.trace_id, "032x")[:16]  # Truncate for readability
                    parts.append(f"[trace={trace_id}]")
            except Exception:
                pass

        # Add source location
        if self.include_source_location:
            parts.append(f"[{record.filename}:{record.lineno}]")

        # Add message
        parts.append(record.getMessage())

        result = " ".join(parts)

        # Add exception info
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)

        return result
