"""Event Manager for network simulator integration.

This module provides centralized event management with history tracking,
correlation support, and export capabilities.

Classes:
    EventManager: Manager for event tracking and correlation
"""

import asyncio
import csv
import json
import logging
import uuid
from datetime import datetime
from io import StringIO
from typing import Any, Callable, Coroutine, Optional

from cardlink.netsim.types import NetworkEvent, NetworkEventType

log = logging.getLogger(__name__)

# Type for event listeners
EventListener = Callable[[NetworkEvent], Coroutine[Any, Any, None]]


class EventManager:
    """Manager for event tracking, correlation, and analysis.

    Provides centralized event management with:
    - Event subscription and emission
    - Event history with filtering
    - Correlation tracking for related events
    - Export to JSON and CSV formats

    Attributes:
        max_history_size: Maximum number of events to keep in history.

    Example:
        >>> event_manager = EventManager()
        >>> # Subscribe to events
        >>> unsubscribe = event_manager.subscribe(my_callback)
        >>> # Start correlation
        >>> correlation_id = await event_manager.start_correlation("test_session")
        >>> # Events during correlation are tracked
        >>> await event_manager.emit(event)
        >>> # Get correlated events
        >>> events = event_manager.get_correlated_events(correlation_id)
    """

    # Default maximum history size
    DEFAULT_MAX_HISTORY = 10000

    def __init__(
        self,
        max_history_size: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        """Initialize Event Manager.

        Args:
            max_history_size: Maximum events to keep in history.
        """
        self._max_history = max_history_size

        # Event storage
        self._event_history: list[NetworkEvent] = []
        self._event_counter = 0

        # Subscribers
        self._listeners: list[EventListener] = []
        self._type_listeners: dict[NetworkEventType, list[EventListener]] = {}

        # Correlation tracking
        self._active_correlations: dict[str, datetime] = {}
        self._correlation_events: dict[str, list[NetworkEvent]] = {}

        # Thread safety
        self._lock = asyncio.Lock()

    # =========================================================================
    # Event Subscription
    # =========================================================================

    def subscribe(
        self,
        callback: EventListener,
        event_type: Optional[NetworkEventType] = None,
    ) -> Callable[[], None]:
        """Subscribe to events.

        Args:
            callback: Async callback to invoke on events.
            event_type: Optional event type to filter (None = all events).

        Returns:
            Unsubscribe function to remove the subscription.

        Example:
            >>> async def handler(event):
            ...     print(f"Event: {event.event_type}")
            >>> unsubscribe = event_manager.subscribe(handler)
            >>> # Later...
            >>> unsubscribe()
        """
        if event_type is not None:
            # Type-specific listener
            if event_type not in self._type_listeners:
                self._type_listeners[event_type] = []
            self._type_listeners[event_type].append(callback)

            def unsubscribe() -> None:
                if event_type in self._type_listeners:
                    try:
                        self._type_listeners[event_type].remove(callback)
                    except ValueError:
                        pass

            return unsubscribe
        else:
            # Global listener
            self._listeners.append(callback)

            def unsubscribe() -> None:
                try:
                    self._listeners.remove(callback)
                except ValueError:
                    pass

            return unsubscribe

    def unsubscribe_all(self) -> None:
        """Remove all event subscriptions."""
        self._listeners.clear()
        self._type_listeners.clear()

    # =========================================================================
    # Event Emission
    # =========================================================================

    async def emit(self, event: NetworkEvent) -> None:
        """Emit an event to all subscribers.

        Stores the event in history and notifies all matching subscribers.

        Args:
            event: The event to emit.
        """
        async with self._lock:
            # Store in history
            self._event_history.append(event)
            self._event_counter += 1

            # Trim history if needed
            if len(self._event_history) > self._max_history:
                excess = len(self._event_history) - self._max_history
                self._event_history = self._event_history[excess:]

            # Add to correlation if active
            if event.correlation_id and event.correlation_id in self._active_correlations:
                self._correlation_events[event.correlation_id].append(event)

        # Notify global listeners
        for callback in self._listeners:
            try:
                await callback(event)
            except Exception as e:
                log.error(f"Error in event listener: {e}")

        # Notify type-specific listeners
        if event.event_type in self._type_listeners:
            for callback in self._type_listeners[event.event_type]:
                try:
                    await callback(event)
                except Exception as e:
                    log.error(f"Error in event listener for {event.event_type}: {e}")

    async def emit_raw(
        self,
        event_type: NetworkEventType,
        data: dict[str, Any],
        imsi: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> NetworkEvent:
        """Create and emit an event.

        Convenience method to create and emit an event in one call.

        Args:
            event_type: Type of event.
            data: Event data.
            imsi: Associated IMSI (optional).
            session_id: Associated session ID (optional).
            correlation_id: Correlation ID (optional, uses active if not specified).

        Returns:
            The created event.
        """
        event = NetworkEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source="event_manager",
            data=data,
            imsi=imsi,
            session_id=session_id,
            correlation_id=correlation_id,
        )

        await self.emit(event)
        return event

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"evt_{self._event_counter:08d}_{uuid.uuid4().hex[:8]}"

    # =========================================================================
    # Event History Operations
    # =========================================================================

    def get_event_history(
        self,
        limit: int = 100,
        event_type: Optional[NetworkEventType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[NetworkEvent]:
        """Get events from history.

        Args:
            limit: Maximum number of events to return.
            event_type: Filter by event type (optional).
            since: Filter events after this time (optional).
            until: Filter events before this time (optional).

        Returns:
            List of events matching the criteria.
        """
        events = self._event_history.copy()

        # Apply filters
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]

        if since is not None:
            events = [e for e in events if e.timestamp >= since]

        if until is not None:
            events = [e for e in events if e.timestamp <= until]

        # Return last N events
        return events[-limit:] if len(events) > limit else events

    def find_events(
        self,
        imsi: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[list[NetworkEventType]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        data_filter: Optional[dict[str, Any]] = None,
        limit: int = 100,
    ) -> list[NetworkEvent]:
        """Find events matching criteria.

        Args:
            imsi: Filter by IMSI (optional).
            session_id: Filter by session ID (optional).
            event_types: Filter by event types (optional).
            since: Filter events after this time (optional).
            until: Filter events before this time (optional).
            data_filter: Filter by event data fields (optional).
            limit: Maximum number of events to return.

        Returns:
            List of events matching all criteria.
        """
        events = self._event_history.copy()

        if imsi is not None:
            events = [e for e in events if e.imsi == imsi]

        if session_id is not None:
            events = [e for e in events if e.session_id == session_id]

        if event_types is not None:
            events = [e for e in events if e.event_type in event_types]

        if since is not None:
            events = [e for e in events if e.timestamp >= since]

        if until is not None:
            events = [e for e in events if e.timestamp <= until]

        if data_filter is not None:
            filtered = []
            for event in events:
                match = all(
                    event.data.get(k) == v for k, v in data_filter.items()
                )
                if match:
                    filtered.append(event)
            events = filtered

        return events[-limit:] if len(events) > limit else events

    def get_event_by_id(self, event_id: str) -> Optional[NetworkEvent]:
        """Get a specific event by ID.

        Args:
            event_id: The event ID to find.

        Returns:
            The event if found, None otherwise.
        """
        for event in reversed(self._event_history):
            if event.event_id == event_id:
                return event
        return None

    def clear_history(self) -> int:
        """Clear all event history.

        Returns:
            Number of events cleared.
        """
        count = len(self._event_history)
        self._event_history.clear()
        log.info(f"Cleared {count} events from history")
        return count

    @property
    def event_count(self) -> int:
        """Get the total number of events in history."""
        return len(self._event_history)

    # =========================================================================
    # Event Correlation
    # =========================================================================

    async def start_correlation(self, name: Optional[str] = None) -> str:
        """Start a new event correlation session.

        Events emitted while a correlation is active will be tagged
        with the correlation ID if not already set.

        Args:
            name: Optional name for the correlation.

        Returns:
            The correlation ID.
        """
        correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
        if name:
            correlation_id = f"corr_{name}_{uuid.uuid4().hex[:8]}"

        async with self._lock:
            self._active_correlations[correlation_id] = datetime.utcnow()
            self._correlation_events[correlation_id] = []

        log.debug(f"Started correlation: {correlation_id}")
        return correlation_id

    async def end_correlation(self, correlation_id: str) -> list[NetworkEvent]:
        """End a correlation session.

        Args:
            correlation_id: The correlation ID to end.

        Returns:
            List of events captured during the correlation.
        """
        async with self._lock:
            if correlation_id in self._active_correlations:
                del self._active_correlations[correlation_id]

            events = self._correlation_events.pop(correlation_id, [])

        log.debug(f"Ended correlation {correlation_id}: {len(events)} events")
        return events

    def get_correlated_events(self, correlation_id: str) -> list[NetworkEvent]:
        """Get events for a correlation.

        Args:
            correlation_id: The correlation ID.

        Returns:
            List of correlated events.
        """
        # Check active correlations
        if correlation_id in self._correlation_events:
            return self._correlation_events[correlation_id].copy()

        # Search history
        return [
            e for e in self._event_history
            if e.correlation_id == correlation_id
        ]

    def get_active_correlations(self) -> list[str]:
        """Get list of active correlation IDs.

        Returns:
            List of active correlation IDs.
        """
        return list(self._active_correlations.keys())

    def is_correlation_active(self, correlation_id: str) -> bool:
        """Check if a correlation is active.

        Args:
            correlation_id: The correlation ID to check.

        Returns:
            True if the correlation is active.
        """
        return correlation_id in self._active_correlations

    # =========================================================================
    # Event Export
    # =========================================================================

    def export_events(
        self,
        format: str = "json",
        file_path: Optional[str] = None,
        events: Optional[list[NetworkEvent]] = None,
        **filter_kwargs,
    ) -> str:
        """Export events to file or string.

        Args:
            format: Export format ("json" or "csv").
            file_path: Path to write file (optional, returns string if not set).
            events: Events to export (optional, uses history with filters if not set).
            **filter_kwargs: Passed to find_events() if events not provided.

        Returns:
            Exported data as string (if file_path not provided).

        Raises:
            ValueError: If format is not supported.
        """
        if events is None:
            events = self.find_events(**filter_kwargs)

        if format.lower() == "json":
            output = self._export_json(events)
        elif format.lower() == "csv":
            output = self._export_csv(events)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(output)
            log.info(f"Exported {len(events)} events to {file_path}")

        return output

    def _export_json(self, events: list[NetworkEvent]) -> str:
        """Export events to JSON format."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "event_count": len(events),
            "events": [e.to_dict() for e in events],
        }
        return json.dumps(data, indent=2, default=str)

    def _export_csv(self, events: list[NetworkEvent]) -> str:
        """Export events to CSV format."""
        output = StringIO()
        fieldnames = [
            "event_id",
            "event_type",
            "timestamp",
            "source",
            "imsi",
            "session_id",
            "correlation_id",
            "data",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for event in events:
            writer.writerow({
                "event_id": event.event_id,
                "event_type": event.event_type.name,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "imsi": event.imsi or "",
                "session_id": event.session_id or "",
                "correlation_id": event.correlation_id or "",
                "data": json.dumps(event.data),
            })

        return output.getvalue()

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get event statistics.

        Returns:
            Dictionary with event statistics.
        """
        type_counts: dict[str, int] = {}
        for event in self._event_history:
            type_name = event.event_type.name
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_events": len(self._event_history),
            "total_emitted": self._event_counter,
            "events_by_type": type_counts,
            "active_correlations": len(self._active_correlations),
            "subscriber_count": len(self._listeners),
            "type_subscribers": {
                t.name: len(listeners)
                for t, listeners in self._type_listeners.items()
            },
            "max_history_size": self._max_history,
        }
