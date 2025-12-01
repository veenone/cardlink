"""Session Manager for network simulator integration.

This module provides centralized data session (PDN/PDU context) management
with tracking, caching, and event handling.

Classes:
    SessionManager: Manager for data session monitoring and control
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from cardlink.netsim.constants import (
    EVENT_DATA_SESSION_ACTIVATED,
    EVENT_DATA_SESSION_DEACTIVATED,
    EVENT_PDN_CONNECTED,
    EVENT_PDN_DISCONNECTED,
)
from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.types import DataSession, NetworkEvent, NetworkEventType

log = logging.getLogger(__name__)


class SessionManager:
    """Manager for data session tracking and control.

    Provides centralized session management with:
    - Session cache for efficient queries
    - Event handling for activation/deactivation
    - Lookup by session ID or IMSI
    - Automatic cache synchronization

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> session_manager = SessionManager(adapter, event_emitter)
        >>> sessions = await session_manager.list_sessions()
        >>> for session in sessions:
        ...     print(f"Session {session.session_id}: {session.ip_address}")
    """

    def __init__(self, adapter: SimulatorInterface, event_emitter: Any) -> None:
        """Initialize Session Manager.

        Args:
            adapter: The simulator adapter for session operations.
            event_emitter: Event emitter for broadcasting session events.
        """
        self._adapter = adapter
        self._events = event_emitter

        # Session cache: session_id -> DataSession
        self._session_cache: dict[str, DataSession] = {}

        # Subscribe to adapter events
        asyncio.create_task(self._subscribe_events())

    async def _subscribe_events(self) -> None:
        """Subscribe to session events from adapter."""
        try:
            await self._adapter.subscribe_events(self._handle_event)
        except Exception as e:
            log.error(f"Failed to subscribe to session events: {e}")

    async def _handle_event(self, event: NetworkEvent) -> None:
        """Handle incoming session events.

        Args:
            event: The network event.
        """
        if event.event_type == NetworkEventType.PDN_CONNECT:
            await self._handle_connect(event)
        elif event.event_type == NetworkEventType.PDN_DISCONNECT:
            await self._handle_disconnect(event)

    async def _handle_connect(self, event: NetworkEvent) -> None:
        """Handle PDN/session connect event.

        Args:
            event: The connect event.
        """
        session_id = event.session_id or event.data.get("session_id")
        if not session_id:
            log.warning("Received connect event without session_id")
            return

        imsi = event.imsi or event.data.get("imsi", "")
        log.info(f"Session activated: {session_id} (IMSI: {imsi})")

        # Create DataSession from event data
        from cardlink.netsim.types import QoSParameters

        qos_data = event.data.get("qos", {})
        session = DataSession(
            session_id=session_id,
            imsi=imsi,
            apn=event.data.get("apn", ""),
            ip_address=event.data.get("ip_address"),
            ipv6_address=event.data.get("ipv6_address"),
            qos=QoSParameters(
                qci=qos_data.get("qci"),
                arp=qos_data.get("arp"),
            ),
            pdn_type=event.data.get("pdn_type", "IPv4"),
            created_at=datetime.utcnow(),
            metadata=event.data,
        )

        # Update cache
        self._session_cache[session_id] = session

        # Emit events
        await self._events.emit(EVENT_PDN_CONNECTED, {
            "session_id": session_id,
            "session": session.to_dict(),
        })
        await self._events.emit(EVENT_DATA_SESSION_ACTIVATED, {
            "session_id": session_id,
            "session": session.to_dict(),
        })

    async def _handle_disconnect(self, event: NetworkEvent) -> None:
        """Handle PDN/session disconnect event.

        Args:
            event: The disconnect event.
        """
        session_id = event.session_id or event.data.get("session_id")
        if not session_id:
            log.warning("Received disconnect event without session_id")
            return

        log.info(f"Session deactivated: {session_id}")

        # Remove from cache
        session = self._session_cache.pop(session_id, None)

        # Emit events
        await self._events.emit(EVENT_PDN_DISCONNECTED, {
            "session_id": session_id,
            "session": session.to_dict() if session else None,
        })
        await self._events.emit(EVENT_DATA_SESSION_DEACTIVATED, {
            "session_id": session_id,
            "session": session.to_dict() if session else None,
        })

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def list_sessions(self) -> list[DataSession]:
        """List all active data sessions.

        Queries the adapter and updates the local cache.

        Returns:
            List of DataSession for all active sessions.
        """
        sessions = await self._adapter.list_sessions()

        # Update cache
        self._session_cache.clear()
        for session in sessions:
            self._session_cache[session.session_id] = session

        return sessions

    async def get_session(self, session_id: str) -> Optional[DataSession]:
        """Get information about a specific session.

        Checks cache first, then queries adapter if not found.

        Args:
            session_id: The unique session identifier.

        Returns:
            DataSession if found, None otherwise.
        """
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        # Query adapter (refresh cache)
        sessions = await self._adapter.list_sessions()
        self._session_cache.clear()
        for session in sessions:
            self._session_cache[session.session_id] = session

        return self._session_cache.get(session_id)

    def get_sessions_by_imsi(self, imsi: str) -> list[DataSession]:
        """Get all sessions for a specific IMSI.

        Filters cached sessions by IMSI.

        Args:
            imsi: The IMSI to filter by.

        Returns:
            List of DataSession for the specified IMSI.
        """
        return [
            session for session in self._session_cache.values()
            if session.imsi == imsi
        ]

    def get_cached_sessions(self) -> list[DataSession]:
        """Get all cached session information.

        Returns cached sessions without querying the adapter.

        Returns:
            List of cached DataSession objects.
        """
        return list(self._session_cache.values())

    # =========================================================================
    # Control Operations
    # =========================================================================

    async def release_session(self, session_id: str) -> bool:
        """Release (terminate) a data session.

        Args:
            session_id: The session identifier to release.

        Returns:
            True if release was successful.
        """
        result = await self._adapter.release_session(session_id)

        if result:
            # Remove from cache
            session = self._session_cache.pop(session_id, None)

            # Emit events
            await self._events.emit(EVENT_PDN_DISCONNECTED, {
                "session_id": session_id,
                "session": session.to_dict() if session else None,
                "forced": True,
            })
            await self._events.emit(EVENT_DATA_SESSION_DEACTIVATED, {
                "session_id": session_id,
                "forced": True,
            })

        return result

    async def release_sessions_by_imsi(self, imsi: str) -> int:
        """Release all sessions for a specific IMSI.

        Args:
            imsi: The IMSI whose sessions to release.

        Returns:
            Number of sessions released.
        """
        sessions = self.get_sessions_by_imsi(imsi)
        released = 0

        for session in sessions:
            try:
                if await self.release_session(session.session_id):
                    released += 1
            except Exception as e:
                log.warning(f"Failed to release session {session.session_id}: {e}")

        return released

    # =========================================================================
    # Cache Management
    # =========================================================================

    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()
        log.debug("Session cache cleared")

    @property
    def cached_count(self) -> int:
        """Get number of cached sessions."""
        return len(self._session_cache)
