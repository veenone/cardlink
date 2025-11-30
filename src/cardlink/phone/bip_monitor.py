"""BIP Monitor for tracking Bearer Independent Protocol events.

This module provides the BIPMonitor class for monitoring BIP events
from Android logcat in real-time.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, List, Optional

from cardlink.phone.adb_client import ADBClient
from cardlink.phone.exceptions import BIPMonitorError, LogcatError
from cardlink.phone.logcat_parser import LogcatParser
from cardlink.phone.models import BIPEvent, LogcatEntry

logger = logging.getLogger(__name__)


# Callback type for BIP events
BIPEventCallback = Callable[[BIPEvent], None]


class BIPMonitor:
    """Monitor for BIP (Bearer Independent Protocol) events.

    This class monitors Android logcat for BIP events from STK/CAT
    and provides real-time event streaming and callbacks.

    Features:
    - Real-time BIP event detection from logcat
    - Event callbacks for integration
    - Async iterator for event streaming
    - Session correlation for tracking OTA flows

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.

    Example:
        ```python
        client = ADBClient()
        monitor = BIPMonitor(client, "device123")

        # Register callback
        monitor.on_bip_event(lambda e: print(f"BIP: {e.event_type}"))

        # Start monitoring
        await monitor.start()

        # Or use async context manager
        async with monitor.start_monitoring() as events:
            async for event in events:
                print(f"Event: {event.event_type}")
        ```
    """

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
    ):
        """Initialize BIP monitor.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
        """
        self._client = adb_client
        self._serial = serial
        self._parser = LogcatParser()

        # Monitoring state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue[BIPEvent] = asyncio.Queue()

        # Callbacks
        self._callbacks: List[BIPEventCallback] = []

        # Event tracking
        self._events: List[BIPEvent] = []
        self._session_id: Optional[str] = None

    @property
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running

    @property
    def events(self) -> List[BIPEvent]:
        """Get list of captured BIP events."""
        return self._events.copy()

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID for event correlation."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: Optional[str]) -> None:
        """Set session ID for event correlation."""
        self._session_id = value

    def on_bip_event(self, callback: BIPEventCallback) -> None:
        """Register callback for BIP events.

        Args:
            callback: Function called with BIPEvent when detected.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: BIPEventCallback) -> bool:
        """Remove a registered callback.

        Args:
            callback: Callback to remove.

        Returns:
            True if callback was found and removed.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            return True
        return False

    def clear_callbacks(self) -> None:
        """Remove all registered callbacks."""
        self._callbacks.clear()

    def clear_events(self) -> None:
        """Clear captured events list."""
        self._events.clear()

    async def start(self) -> None:
        """Start BIP monitoring.

        This starts a background task that monitors logcat for BIP events.
        Events are emitted via callbacks and can be retrieved via the
        events property.
        """
        if self._running:
            logger.warning("BIP monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"BIP monitor started for device {self._serial}")

    async def stop(self) -> None:
        """Stop BIP monitoring."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info(f"BIP monitor stopped for device {self._serial}")

    @asynccontextmanager
    async def start_monitoring(self) -> AsyncIterator[AsyncIterator[BIPEvent]]:
        """Context manager for BIP monitoring with async iterator.

        Yields an async iterator that produces BIP events.

        Example:
            ```python
            async with monitor.start_monitoring() as events:
                async for event in events:
                    print(event)
            ```
        """
        await self.start()
        try:
            yield self._event_iterator()
        finally:
            await self.stop()

    async def _event_iterator(self) -> AsyncIterator[BIPEvent]:
        """Async iterator that yields BIP events."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0,
                )
                yield event
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        filter_specs = self._parser.get_filter_specs()

        try:
            async for line in self._client.start_logcat(
                self._serial,
                filters=filter_specs,
                clear=True,
            ):
                if not self._running:
                    break

                try:
                    await self._process_line(line)
                except Exception as e:
                    logger.debug(f"Error processing log line: {e}")
                    continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"BIP monitor error: {e}")
            raise BIPMonitorError(str(e), self._serial)

    async def _process_line(self, line: str) -> None:
        """Process a single logcat line.

        Args:
            line: Raw logcat line.
        """
        # Parse the line
        entry = self._parser.parse_line(line)
        if entry is None:
            return

        # Check if it's a BIP event
        if not self._parser.is_bip_event(entry):
            return

        # Extract BIP event details
        bip_event = self._parser.extract_bip_event(entry)
        if bip_event is None:
            return

        # Add session ID if set
        if self._session_id:
            bip_event.session_id = self._session_id

        # Store event
        self._events.append(bip_event)

        # Queue for async iterator
        try:
            self._event_queue.put_nowait(bip_event)
        except asyncio.QueueFull:
            # Remove oldest if queue is full
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(bip_event)
            except asyncio.QueueEmpty:
                pass

        # Emit callbacks
        self._emit_event(bip_event)

        logger.debug(f"BIP event detected: {bip_event.event_type.value}")

    def _emit_event(self, event: BIPEvent) -> None:
        """Emit BIP event to all callbacks."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"BIP callback error: {e}")

    async def wait_for_event(
        self,
        timeout: float = 30.0,
        event_type: Optional[str] = None,
    ) -> Optional[BIPEvent]:
        """Wait for a specific BIP event.

        Args:
            timeout: Maximum time to wait in seconds.
            event_type: Specific event type to wait for, or None for any.

        Returns:
            BIPEvent if found, None if timeout.
        """
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=min(1.0, timeout),
                )

                if event_type is None or event.event_type.value == event_type:
                    return event

            except asyncio.TimeoutError:
                continue

        return None

    async def __aenter__(self) -> "BIPMonitor":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


class LogcatMonitor:
    """General-purpose logcat monitor.

    This class provides raw logcat monitoring with filtering support.
    Use BIPMonitor for BIP-specific monitoring.

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.
        tags: List of tags to monitor (None for all).
        buffer: Log buffer to monitor.

    Example:
        ```python
        monitor = LogcatMonitor(client, "device123", tags=["Telephony"])
        async with monitor.start_monitoring() as entries:
            async for entry in entries:
                print(f"[{entry.level}] {entry.tag}: {entry.message}")
        ```
    """

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
        tags: Optional[List[str]] = None,
        buffer: str = "main",
    ):
        """Initialize logcat monitor.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
            tags: Tags to filter, or None for all.
            buffer: Log buffer (main, system, radio, events, crash).
        """
        self._client = adb_client
        self._serial = serial
        self._tags = tags
        self._buffer = buffer
        self._parser = LogcatParser()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._entry_queue: asyncio.Queue[LogcatEntry] = asyncio.Queue(maxsize=1000)

        self._callbacks: List[Callable[[LogcatEntry], None]] = []

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    def on_entry(self, callback: Callable[[LogcatEntry], None]) -> None:
        """Register callback for log entries."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start logcat monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop logcat monitoring."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @asynccontextmanager
    async def start_monitoring(self) -> AsyncIterator[AsyncIterator[LogcatEntry]]:
        """Context manager for logcat monitoring."""
        await self.start()
        try:
            yield self._entry_iterator()
        finally:
            await self.stop()

    async def _entry_iterator(self) -> AsyncIterator[LogcatEntry]:
        """Async iterator for log entries."""
        while self._running:
            try:
                entry = await asyncio.wait_for(
                    self._entry_queue.get(),
                    timeout=1.0,
                )
                yield entry
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        filters = None
        if self._tags:
            filters = ["*:S"] + [f"{tag}:V" for tag in self._tags]

        try:
            async for line in self._client.start_logcat(
                self._serial,
                filters=filters,
                buffer=self._buffer,
                clear=True,
            ):
                if not self._running:
                    break

                entry = self._parser.parse_line(line)
                if entry is None:
                    continue

                # Filter by tags if specified
                if self._tags and entry.tag not in self._tags:
                    if not any(t in entry.tag for t in self._tags):
                        continue

                # Queue entry
                try:
                    self._entry_queue.put_nowait(entry)
                except asyncio.QueueFull:
                    try:
                        self._entry_queue.get_nowait()
                        self._entry_queue.put_nowait(entry)
                    except asyncio.QueueEmpty:
                        pass

                # Emit callbacks
                for callback in self._callbacks:
                    try:
                        callback(entry)
                    except Exception as e:
                        logger.error(f"Logcat callback error: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Logcat monitor error: {e}")
            raise LogcatError(str(e), self._serial)

    async def __aenter__(self) -> "LogcatMonitor":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
