"""Database event system for GP OTA Tester.

This module provides an event emitter for database operations,
allowing components to subscribe to and react to database changes.

Example:
    >>> from gp_ota_tester.database.events import DatabaseEventEmitter, DatabaseEvent
    >>> emitter = DatabaseEventEmitter()
    >>> def on_device_created(event: DatabaseEvent):
    ...     print(f"Device created: {event.entity_id}")
    >>> emitter.on("device.created", on_device_created)
    >>> emitter.emit("device.created", "Device", "RF8M33XXXXX")
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Database event types."""

    # Entity lifecycle events
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

    # Session events
    SESSION_STARTED = "session.started"
    SESSION_COMPLETED = "session.completed"
    SESSION_FAILED = "session.failed"

    # Test events
    TEST_STARTED = "test.started"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"

    # System events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MIGRATED = "migrated"


@dataclass
class DatabaseEvent:
    """Database event data.

    Represents an event that occurred in the database layer.

    Attributes:
        event_type: Type of event (e.g., "device.created").
        entity_type: Type of entity involved (e.g., "Device").
        entity_id: ID of the entity (if applicable).
        data: Additional event data.
        timestamp: When the event occurred.
    """

    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[Any] = None
    data: Optional[Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_type(self) -> str:
        """Get full event type string.

        Returns:
            Event type, optionally prefixed with entity type.
        """
        if self.entity_type:
            return f"{self.entity_type.lower()}.{self.event_type}"
        return self.event_type


# Type alias for event handlers
EventHandler = Callable[[DatabaseEvent], None]


class DatabaseEventEmitter:
    """Thread-safe event emitter for database events.

    Allows subscribing to and emitting database events.
    Supports wildcard handlers that receive all events.

    Thread Safety:
        All handler registration and emission is thread-safe.

    Example:
        >>> emitter = DatabaseEventEmitter()
        >>>
        >>> # Subscribe to specific event
        >>> def on_device_created(event):
        ...     print(f"Device created: {event.entity_id}")
        >>> emitter.on("device.created", on_device_created)
        >>>
        >>> # Subscribe to all events
        >>> def log_all(event):
        ...     logger.info(f"Event: {event.full_type}")
        >>> emitter.on("*", log_all)
        >>>
        >>> # Emit event
        >>> emitter.emit("created", "Device", "device_123")
    """

    def __init__(self) -> None:
        """Initialize event emitter."""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._lock = threading.RLock()
        self._enabled = True

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Register event handler.

        Args:
            event_type: Event type to handle, or "*" for all events.
            handler: Callable that receives DatabaseEvent.

        Example:
            >>> emitter.on("device.created", my_handler)
            >>> emitter.on("*", my_catch_all_handler)
        """
        with self._lock:
            if event_type == "*":
                if handler not in self._wildcard_handlers:
                    self._wildcard_handlers.append(handler)
                    logger.debug("Registered wildcard handler: %s", handler.__name__)
            else:
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                if handler not in self._handlers[event_type]:
                    self._handlers[event_type].append(handler)
                    logger.debug("Registered handler for %s: %s", event_type, handler.__name__)

    def off(self, event_type: str, handler: EventHandler) -> bool:
        """Remove event handler.

        Args:
            event_type: Event type, or "*" for wildcard handlers.
            handler: Handler to remove.

        Returns:
            True if handler was removed, False if not found.
        """
        with self._lock:
            if event_type == "*":
                if handler in self._wildcard_handlers:
                    self._wildcard_handlers.remove(handler)
                    logger.debug("Removed wildcard handler: %s", handler.__name__)
                    return True
            elif event_type in self._handlers:
                if handler in self._handlers[event_type]:
                    self._handlers[event_type].remove(handler)
                    logger.debug("Removed handler for %s: %s", event_type, handler.__name__)
                    return True
            return False

    def emit(
        self,
        event_type: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an event to all registered handlers.

        Args:
            event_type: Type of event (e.g., "created").
            entity_type: Type of entity (e.g., "Device").
            entity_id: ID of the entity.
            data: Additional event data.

        Example:
            >>> emitter.emit("created", "Device", "RF8M33XXXXX", {"name": "Test Phone"})
        """
        if not self._enabled:
            return

        event = DatabaseEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data or {},
        )

        full_type = event.full_type

        with self._lock:
            # Get handlers (copy to avoid modification during iteration)
            handlers = list(self._handlers.get(full_type, []))
            wildcards = list(self._wildcard_handlers)

        # Call handlers outside lock to avoid deadlocks
        for handler in handlers + wildcards:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    "Error in event handler %s for %s: %s",
                    handler.__name__,
                    full_type,
                    e,
                )

    def emit_event(self, event: DatabaseEvent) -> None:
        """Emit a pre-built event.

        Args:
            event: DatabaseEvent to emit.
        """
        self.emit(
            event.event_type,
            event.entity_type,
            event.entity_id,
            event.data,
        )

    def clear(self, event_type: Optional[str] = None) -> None:
        """Clear handlers.

        Args:
            event_type: If specified, clear only this type.
                       If None or "*", clear all handlers.
        """
        with self._lock:
            if event_type is None or event_type == "*":
                self._handlers.clear()
                self._wildcard_handlers.clear()
                logger.debug("Cleared all event handlers")
            elif event_type in self._handlers:
                del self._handlers[event_type]
                logger.debug("Cleared handlers for %s", event_type)

    def enable(self) -> None:
        """Enable event emission."""
        self._enabled = True
        logger.debug("Event emission enabled")

    def disable(self) -> None:
        """Disable event emission."""
        self._enabled = False
        logger.debug("Event emission disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if events are enabled."""
        return self._enabled

    def handler_count(self, event_type: Optional[str] = None) -> int:
        """Get count of registered handlers.

        Args:
            event_type: If specified, count for this type only.

        Returns:
            Number of handlers.
        """
        with self._lock:
            if event_type is None:
                count = sum(len(h) for h in self._handlers.values())
                return count + len(self._wildcard_handlers)
            elif event_type == "*":
                return len(self._wildcard_handlers)
            else:
                return len(self._handlers.get(event_type, []))

    def get_event_types(self) -> Set[str]:
        """Get all registered event types.

        Returns:
            Set of event type strings.
        """
        with self._lock:
            return set(self._handlers.keys())


# Global event emitter instance
_global_emitter: Optional[DatabaseEventEmitter] = None


def get_emitter() -> DatabaseEventEmitter:
    """Get the global event emitter instance.

    Creates it if it doesn't exist.

    Returns:
        Global DatabaseEventEmitter instance.
    """
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = DatabaseEventEmitter()
    return _global_emitter


def set_emitter(emitter: Optional[DatabaseEventEmitter]) -> None:
    """Set the global event emitter.

    Args:
        emitter: Emitter to use, or None to clear.
    """
    global _global_emitter
    _global_emitter = emitter
