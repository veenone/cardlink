"""Event emission system for the PSK-TLS Admin Server.

This module provides a thread-safe event emitter for distributing server events
to subscribers, enabling real-time monitoring, metrics collection, and dashboard updates.

Event Types:
    - server_started: Server has started listening
    - server_stopped: Server has stopped
    - session_started: New client session established
    - session_ended: Client session closed
    - handshake_completed: TLS handshake completed successfully
    - handshake_failed: TLS handshake failed
    - apdu_received: APDU command received from client
    - apdu_sent: APDU response sent to client
    - psk_mismatch: PSK authentication failed
    - connection_interrupted: Connection unexpectedly interrupted
    - high_error_rate: Error rate threshold exceeded

Example:
    >>> from cardlink.server.event_emitter import EventEmitter
    >>> emitter = EventEmitter()
    >>> def on_session(data):
    ...     print(f"Session started: {data['session_id']}")
    >>> emitter.subscribe("session_started", on_session)
    >>> emitter.emit("session_started", {"session_id": "abc123"})
"""

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Event Type Constants
# =============================================================================

# Server lifecycle events
EVENT_SERVER_STARTED = "server_started"
EVENT_SERVER_STOPPED = "server_stopped"

# Session lifecycle events
EVENT_SESSION_STARTED = "session_started"
EVENT_SESSION_ENDED = "session_ended"

# TLS handshake events
EVENT_HANDSHAKE_COMPLETED = "handshake_completed"
EVENT_HANDSHAKE_FAILED = "handshake_failed"

# APDU exchange events
EVENT_APDU_RECEIVED = "apdu_received"
EVENT_APDU_SENT = "apdu_sent"

# Error events
EVENT_PSK_MISMATCH = "psk_mismatch"
EVENT_CONNECTION_INTERRUPTED = "connection_interrupted"
EVENT_HIGH_ERROR_RATE = "high_error_rate"

# Wildcard for subscribing to all events
EVENT_WILDCARD = "*"

# All event types
ALL_EVENT_TYPES: Set[str] = {
    EVENT_SERVER_STARTED,
    EVENT_SERVER_STOPPED,
    EVENT_SESSION_STARTED,
    EVENT_SESSION_ENDED,
    EVENT_HANDSHAKE_COMPLETED,
    EVENT_HANDSHAKE_FAILED,
    EVENT_APDU_RECEIVED,
    EVENT_APDU_SENT,
    EVENT_PSK_MISMATCH,
    EVENT_CONNECTION_INTERRUPTED,
    EVENT_HIGH_ERROR_RATE,
}


# =============================================================================
# Event Data Classes
# =============================================================================


@dataclass
class Event:
    """Base event data structure.

    Attributes:
        event_type: Type of the event.
        timestamp: When the event occurred.
        data: Event-specific data payload.
    """

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """Event subscription record.

    Attributes:
        subscription_id: Unique subscription identifier.
        event_type: Event type to subscribe to (or "*" for all).
        callback: Function to call when event occurs.
    """

    subscription_id: str
    event_type: str
    callback: Callable[[Dict[str, Any]], None]


# =============================================================================
# Event Emitter
# =============================================================================


class EventEmitter:
    """Thread-safe event emitter for server events.

    Provides pub/sub functionality for distributing server events to
    registered subscribers. Supports wildcard subscriptions for receiving
    all events.

    Thread Safety:
        All methods are thread-safe and can be called from any thread.
        Events are processed in a dedicated background thread.

    Example:
        >>> emitter = EventEmitter()
        >>> emitter.start()
        >>>
        >>> # Subscribe to specific event
        >>> sub_id = emitter.subscribe("session_started", lambda d: print(d))
        >>>
        >>> # Subscribe to all events
        >>> emitter.subscribe("*", lambda d: log_event(d))
        >>>
        >>> # Emit event
        >>> emitter.emit("session_started", {"session_id": "123"})
        >>>
        >>> # Unsubscribe
        >>> emitter.unsubscribe(sub_id)
        >>>
        >>> emitter.stop()
    """

    def __init__(self, queue_size: int = 1000) -> None:
        """Initialize EventEmitter.

        Args:
            queue_size: Maximum number of events in the queue.
        """
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._subscriptions_lock = threading.Lock()
        self._event_queue: Queue[Optional[Event]] = Queue(maxsize=queue_size)
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the event processing thread.

        Events will not be delivered until start() is called.
        """
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_events,
            name="EventEmitter-Worker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.debug("EventEmitter started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the event processing thread.

        Args:
            timeout: Maximum time to wait for thread to finish.
        """
        if not self._running:
            return

        self._running = False
        # Send sentinel to unblock the worker
        self._event_queue.put(None)

        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            self._worker_thread = None

        logger.debug("EventEmitter stopped")

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to, or "*" for all events.
            callback: Function to call when event occurs. Receives event data dict.

        Returns:
            Subscription ID that can be used to unsubscribe.

        Example:
            >>> def handler(data):
            ...     print(f"Received: {data}")
            >>> sub_id = emitter.subscribe("session_started", handler)
        """
        subscription_id = str(uuid.uuid4())
        subscription = Subscription(
            subscription_id=subscription_id,
            event_type=event_type,
            callback=callback,
        )

        with self._subscriptions_lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(subscription)

        logger.debug(
            "Added subscription %s for event type '%s'",
            subscription_id,
            event_type,
        )
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: Subscription ID returned from subscribe().

        Returns:
            True if subscription was found and removed, False otherwise.
        """
        with self._subscriptions_lock:
            for event_type, subscriptions in self._subscriptions.items():
                for sub in subscriptions:
                    if sub.subscription_id == subscription_id:
                        subscriptions.remove(sub)
                        logger.debug(
                            "Removed subscription %s for event type '%s'",
                            subscription_id,
                            event_type,
                        )
                        return True
        return False

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit an event to all subscribers.

        Args:
            event_type: Type of event to emit.
            data: Event data payload.

        Note:
            Events are queued and processed asynchronously. If the queue is full,
            the oldest events may be dropped.
        """
        event = Event(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data or {},
        )

        try:
            self._event_queue.put_nowait(event)
        except Exception:
            logger.warning("Event queue full, dropping event: %s", event_type)

    def emit_sync(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit an event synchronously (blocking).

        Delivers the event to all subscribers immediately in the calling thread.
        Use with caution as slow subscribers will block the caller.

        Args:
            event_type: Type of event to emit.
            data: Event data payload.
        """
        event = Event(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data or {},
        )
        self._deliver_event(event)

    def _process_events(self) -> None:
        """Background thread that processes queued events."""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.1)
                if event is None:
                    # Sentinel received, exit
                    break
                self._deliver_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.exception("Error processing event: %s", e)

    def _deliver_event(self, event: Event) -> None:
        """Deliver event to all matching subscribers.

        Args:
            event: The event to deliver.
        """
        # Add metadata to event data
        event_data = {
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            **event.data,
        }

        with self._subscriptions_lock:
            # Get subscribers for this specific event type
            subscribers = list(self._subscriptions.get(event.event_type, []))
            # Also get wildcard subscribers
            subscribers.extend(self._subscriptions.get(EVENT_WILDCARD, []))

        for subscription in subscribers:
            try:
                subscription.callback(event_data)
            except Exception as e:
                logger.exception(
                    "Error in event subscriber %s for '%s': %s",
                    subscription.subscription_id,
                    event.event_type,
                    e,
                )

    def get_subscriber_count(self, event_type: Optional[str] = None) -> int:
        """Get number of subscribers.

        Args:
            event_type: Specific event type, or None for total count.

        Returns:
            Number of subscribers.
        """
        with self._subscriptions_lock:
            if event_type:
                return len(self._subscriptions.get(event_type, []))
            return sum(len(subs) for subs in self._subscriptions.values())

    def clear_subscriptions(self) -> None:
        """Remove all subscriptions."""
        with self._subscriptions_lock:
            self._subscriptions.clear()
        logger.debug("Cleared all subscriptions")


# =============================================================================
# Mock Event Emitter for Testing
# =============================================================================


class MockEventEmitter(EventEmitter):
    """Mock event emitter for testing.

    Records all emitted events for later inspection. Does not require
    start()/stop() calls.

    Example:
        >>> emitter = MockEventEmitter()
        >>> emitter.emit("session_started", {"session_id": "123"})
        >>> assert len(emitter.events) == 1
        >>> assert emitter.events[0].event_type == "session_started"
    """

    def __init__(self) -> None:
        """Initialize MockEventEmitter."""
        super().__init__()
        self.events: List[Event] = []
        self._running = True  # Always "running" for testing

    def start(self) -> None:
        """No-op for mock."""
        pass

    def stop(self, timeout: float = 5.0) -> None:
        """No-op for mock."""
        pass

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Record event and deliver synchronously.

        Args:
            event_type: Type of event to emit.
            data: Event data payload.
        """
        event = Event(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data or {},
        )
        self.events.append(event)
        self._deliver_event(event)

    def clear_events(self) -> None:
        """Clear recorded events."""
        self.events.clear()

    def get_events_by_type(self, event_type: str) -> List[Event]:
        """Get all events of a specific type.

        Args:
            event_type: Event type to filter by.

        Returns:
            List of matching events.
        """
        return [e for e in self.events if e.event_type == event_type]

    def assert_event_emitted(self, event_type: str, count: int = 1) -> None:
        """Assert that an event was emitted a specific number of times.

        Args:
            event_type: Event type to check.
            count: Expected number of emissions.

        Raises:
            AssertionError: If count doesn't match.
        """
        actual = len(self.get_events_by_type(event_type))
        assert actual == count, f"Expected {count} '{event_type}' events, got {actual}"
