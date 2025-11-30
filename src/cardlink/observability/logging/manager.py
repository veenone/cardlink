"""Logger manager for structured logging.

This module provides a LoggerManager class that manages component loggers
with configurable levels and structured output.
"""

import logging
import sys
from typing import Dict, Optional

from cardlink.observability.config import LoggingConfig
from cardlink.observability.logging.structured import StructuredFormatter, TextFormatter


class LoggerManager:
    """Manager for component loggers with structured output.

    This class manages logging configuration for the application,
    providing structured JSON or text output with trace context.

    Example:
        >>> from cardlink.observability.config import LoggingConfig
        >>> config = LoggingConfig(level="DEBUG", format="json")
        >>> manager = LoggerManager(config)
        >>> manager.configure()
        >>>
        >>> logger = manager.get_logger("my_component")
        >>> logger.info("Hello", extra={"user_id": 123})
    """

    def __init__(self, config: LoggingConfig) -> None:
        """Initialize the logger manager.

        Args:
            config: Logging configuration.
        """
        self.config = config
        self._loggers: Dict[str, logging.Logger] = {}
        self._handler: Optional[logging.Handler] = None
        self._formatter: Optional[logging.Formatter] = None
        self._configured = False
        self._root_logger_name = "cardlink"

    def configure(self) -> None:
        """Configure the root logger and handlers.

        This sets up the formatter, handler, and log level based on config.
        Should be called once during application initialization.
        """
        if self._configured:
            return

        # Create formatter based on config
        if self.config.format == "json":
            self._formatter = StructuredFormatter(
                include_trace_context=self.config.trace_correlation,
            )
        else:
            self._formatter = TextFormatter(
                include_trace_context=self.config.trace_correlation,
            )

        # Create handler
        if self.config.output_file:
            self._handler = logging.FileHandler(self.config.output_file)
        else:
            self._handler = logging.StreamHandler(sys.stderr)

        self._handler.setFormatter(self._formatter)

        # Configure root application logger
        root_logger = logging.getLogger(self._root_logger_name)
        root_logger.setLevel(self._parse_level(self.config.level))
        root_logger.addHandler(self._handler)

        # Prevent propagation to Python's root logger
        root_logger.propagate = False

        self._configured = True

    def shutdown(self) -> None:
        """Shutdown the logger manager.

        Removes handlers and cleans up resources.
        """
        if not self._configured:
            return

        root_logger = logging.getLogger(self._root_logger_name)
        if self._handler:
            root_logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None

        self._loggers.clear()
        self._configured = False

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for a component.

        Args:
            name: Component name. Will be prefixed with 'cardlink.' if not already.

        Returns:
            Logger instance for the component.

        Example:
            >>> logger = manager.get_logger("server")
            >>> logger.info("Server started", extra={"port": 8443})
        """
        # Ensure consistent naming
        if not name.startswith(self._root_logger_name):
            full_name = f"{self._root_logger_name}.{name}"
        else:
            full_name = name

        if full_name not in self._loggers:
            self._loggers[full_name] = logging.getLogger(full_name)

        return self._loggers[full_name]

    def set_level(self, name: str, level: str) -> None:
        """Set log level for a specific component.

        Args:
            name: Component name (e.g., "server", "database").
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        Example:
            >>> manager.set_level("database", "DEBUG")
        """
        logger = self.get_logger(name)
        logger.setLevel(self._parse_level(level))

    def set_global_level(self, level: str) -> None:
        """Set log level for all loggers.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        Example:
            >>> manager.set_global_level("DEBUG")
        """
        root_logger = logging.getLogger(self._root_logger_name)
        root_logger.setLevel(self._parse_level(level))

        # Also update all child loggers
        for logger in self._loggers.values():
            logger.setLevel(self._parse_level(level))

    def get_level(self, name: str) -> str:
        """Get the current log level for a component.

        Args:
            name: Component name.

        Returns:
            Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        logger = self.get_logger(name)
        return logging.getLevelName(logger.getEffectiveLevel())

    def add_extra_field(self, key: str, value: str) -> None:
        """Add a static field to all log entries.

        Args:
            key: Field name.
            value: Field value.

        Note:
            Only works with StructuredFormatter.
        """
        if isinstance(self._formatter, StructuredFormatter):
            self._formatter.extra_fields[key] = value

    def remove_extra_field(self, key: str) -> None:
        """Remove a static field from log entries.

        Args:
            key: Field name to remove.
        """
        if isinstance(self._formatter, StructuredFormatter):
            self._formatter.extra_fields.pop(key, None)

    @property
    def is_configured(self) -> bool:
        """Check if the logger manager has been configured."""
        return self._configured

    @property
    def registered_loggers(self) -> list:
        """Get list of registered logger names."""
        return list(self._loggers.keys())

    def _parse_level(self, level: str) -> int:
        """Parse log level string to integer.

        Args:
            level: Log level name.

        Returns:
            Log level integer value.
        """
        return getattr(logging, level.upper(), logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger.

    This provides a simple way to get loggers without accessing
    the ObservabilityManager directly.

    Args:
        name: Component name.

    Returns:
        Logger instance.

    Example:
        >>> from cardlink.observability.logging import get_logger
        >>> logger = get_logger("my_module")
        >>> logger.info("Hello world")
    """
    if not name.startswith("cardlink"):
        name = f"cardlink.{name}"
    return logging.getLogger(name)
