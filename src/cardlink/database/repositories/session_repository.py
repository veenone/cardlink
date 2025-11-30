"""OTA Session repository for GP OTA Tester.

This module provides the repository for OTA session CRUD operations
and session-specific queries.

Example:
    >>> from cardlink.database.repositories import SessionRepository
    >>> with UnitOfWork(manager) as uow:
    ...     active = uow.sessions.find_active()
    ...     recent = uow.sessions.find_recent(hours=24)
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from cardlink.database.models import OTASession, SessionStatus
from cardlink.database.repositories.base import BaseRepository


class SessionRepository(BaseRepository[OTASession]):
    """Repository for OTA session operations.

    Provides CRUD operations and session-specific queries.

    Example:
        >>> repo = SessionRepository(session)
        >>> active = repo.find_active()
        >>> failed = repo.find_by_status(SessionStatus.FAILED)
    """

    def __init__(self, session: Session) -> None:
        """Initialize session repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, OTASession)

    def find_by_status(self, status: SessionStatus) -> List[OTASession]:
        """Find sessions by status.

        Args:
            status: Session status to filter by.

        Returns:
            List of sessions with given status.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.status == status)
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_pending(self) -> List[OTASession]:
        """Find pending sessions.

        Returns:
            List of pending sessions.
        """
        return self.find_by_status(SessionStatus.PENDING)

    def find_active(self) -> List[OTASession]:
        """Find active sessions.

        Returns:
            List of active sessions.
        """
        return self.find_by_status(SessionStatus.ACTIVE)

    def find_completed(self) -> List[OTASession]:
        """Find completed sessions.

        Returns:
            List of completed sessions.
        """
        return self.find_by_status(SessionStatus.COMPLETED)

    def find_failed(self) -> List[OTASession]:
        """Find failed sessions.

        Returns:
            List of failed sessions.
        """
        return self.find_by_status(SessionStatus.FAILED)

    def find_by_device(self, device_id: str) -> List[OTASession]:
        """Find sessions for a device.

        Args:
            device_id: Device ID to filter by.

        Returns:
            List of sessions for the device.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.device_id == device_id)
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_card(self, iccid: str) -> List[OTASession]:
        """Find sessions for a card.

        Args:
            iccid: Card ICCID to filter by.

        Returns:
            List of sessions for the card.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.card_iccid == iccid)
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_recent(
        self,
        hours: int = 24,
        limit: Optional[int] = None,
    ) -> List[OTASession]:
        """Find sessions from the last N hours.

        Args:
            hours: Number of hours to look back.
            limit: Maximum number of sessions to return.

        Returns:
            List of recent sessions.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(OTASession)
            .where(OTASession.created_at >= cutoff)
            .order_by(OTASession.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_psk_identity(self, identity: str) -> List[OTASession]:
        """Find sessions by PSK identity.

        Args:
            identity: PSK identity used in session.

        Returns:
            List of sessions with the PSK identity.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.tls_psk_identity == identity)
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[OTASession]:
        """Find sessions within date range.

        Args:
            start_date: Start of date range.
            end_date: End of date range (defaults to now).

        Returns:
            List of sessions in the date range.
        """
        if end_date is None:
            end_date = datetime.utcnow()

        stmt = (
            select(OTASession)
            .where(
                and_(
                    OTASession.created_at >= start_date,
                    OTASession.created_at <= end_date,
                )
            )
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_with_errors(self) -> List[OTASession]:
        """Find sessions with errors.

        Returns:
            List of sessions that have error messages.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.error_message.isnot(None))
            .order_by(OTASession.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_with_logs(self, session_id: str) -> Optional[OTASession]:
        """Get session with communication logs eagerly loaded.

        Args:
            session_id: Session ID.

        Returns:
            Session with logs loaded, or None.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.id == session_id)
            .options(joinedload(OTASession.comm_logs))
        )
        result = self._session.execute(stmt)
        return result.scalar_one_or_none()

    def get_latest_for_device(self, device_id: str) -> Optional[OTASession]:
        """Get the most recent session for a device.

        Args:
            device_id: Device ID.

        Returns:
            Most recent session or None.
        """
        stmt = (
            select(OTASession)
            .where(OTASession.device_id == device_id)
            .order_by(OTASession.created_at.desc())
            .limit(1)
        )
        result = self._session.execute(stmt)
        return result.scalar_one_or_none()

    def cleanup_stale(self, hours: int = 24) -> int:
        """Mark stale pending sessions as timed out.

        Args:
            hours: Hours after which pending sessions are stale.

        Returns:
            Number of sessions updated.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(OTASession)
            .where(
                and_(
                    OTASession.status == SessionStatus.PENDING,
                    OTASession.created_at < cutoff,
                )
            )
        )
        result = self._session.execute(stmt)
        sessions = list(result.scalars().all())

        for session in sessions:
            session.timeout()

        return len(sessions)

    def get_stats(
        self,
        hours: Optional[int] = None,
    ) -> dict:
        """Get session statistics.

        Args:
            hours: If specified, only count sessions from last N hours.

        Returns:
            Dictionary with session statistics.
        """
        # Base query
        base_query = select(func.count()).select_from(OTASession)

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            base_query = base_query.where(OTASession.created_at >= cutoff)

        # Count by status
        stats = {
            "total": self._session.execute(base_query).scalar() or 0,
        }

        for status in SessionStatus:
            count_query = base_query.where(OTASession.status == status)
            if hours:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                count_query = count_query.where(OTASession.created_at >= cutoff)
            stats[status.value] = self._session.execute(
                select(func.count())
                .select_from(OTASession)
                .where(OTASession.status == status)
            ).scalar() or 0

        # Average duration for completed sessions
        avg_query = (
            select(func.avg(OTASession.duration_ms))
            .where(OTASession.status == SessionStatus.COMPLETED)
        )
        if hours:
            avg_query = avg_query.where(OTASession.created_at >= cutoff)
        avg_duration = self._session.execute(avg_query).scalar()
        stats["avg_duration_ms"] = round(avg_duration) if avg_duration else 0

        return stats
