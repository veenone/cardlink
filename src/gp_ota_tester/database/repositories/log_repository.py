"""Communication log repository for GP OTA Tester.

This module provides the repository for APDU communication log
operations.

Example:
    >>> from gp_ota_tester.database.repositories import LogRepository
    >>> with UnitOfWork(manager) as uow:
    ...     logs = uow.logs.find_by_session(session_id)
    ...     commands = uow.logs.find_commands(session_id)
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from gp_ota_tester.database.models import CommLog, CommDirection
from gp_ota_tester.database.repositories.base import BaseRepository


class LogRepository(BaseRepository[CommLog]):
    """Repository for communication log operations.

    Provides CRUD operations and log-specific queries.

    Example:
        >>> repo = LogRepository(session)
        >>> logs = repo.find_by_session(session_id)
        >>> repo.log_command(session_id, "00A4040007...")
    """

    def __init__(self, session: Session) -> None:
        """Initialize log repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, CommLog)

    def find_by_session(self, session_id: str) -> List[CommLog]:
        """Find all logs for a session.

        Args:
            session_id: Session UUID.

        Returns:
            List of logs ordered by timestamp.
        """
        stmt = (
            select(CommLog)
            .where(CommLog.session_id == session_id)
            .order_by(CommLog.timestamp)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_commands(self, session_id: str) -> List[CommLog]:
        """Find command logs for a session.

        Args:
            session_id: Session UUID.

        Returns:
            List of command logs.
        """
        stmt = (
            select(CommLog)
            .where(
                and_(
                    CommLog.session_id == session_id,
                    CommLog.direction == CommDirection.COMMAND.value,
                )
            )
            .order_by(CommLog.timestamp)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_responses(self, session_id: str) -> List[CommLog]:
        """Find response logs for a session.

        Args:
            session_id: Session UUID.

        Returns:
            List of response logs.
        """
        stmt = (
            select(CommLog)
            .where(
                and_(
                    CommLog.session_id == session_id,
                    CommLog.direction == CommDirection.RESPONSE.value,
                )
            )
            .order_by(CommLog.timestamp)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_errors(self, session_id: str) -> List[CommLog]:
        """Find error responses for a session.

        Args:
            session_id: Session UUID.

        Returns:
            List of error response logs (non-9000/61XX status).
        """
        stmt = (
            select(CommLog)
            .where(
                and_(
                    CommLog.session_id == session_id,
                    CommLog.direction == CommDirection.RESPONSE.value,
                    CommLog.status_word.isnot(None),
                    ~CommLog.status_word.like("90%"),
                    ~CommLog.status_word.like("61%"),
                )
            )
            .order_by(CommLog.timestamp)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_status_word(
        self,
        status_word: str,
        session_id: Optional[str] = None,
    ) -> List[CommLog]:
        """Find logs by status word.

        Args:
            status_word: Status word to search for (e.g., "6A82").
            session_id: Optional session ID to filter by.

        Returns:
            List of matching logs.
        """
        conditions = [CommLog.status_word == status_word.upper()]
        if session_id:
            conditions.append(CommLog.session_id == session_id)

        stmt = (
            select(CommLog)
            .where(and_(*conditions))
            .order_by(CommLog.timestamp.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_recent(
        self,
        hours: int = 24,
        limit: Optional[int] = None,
    ) -> List[CommLog]:
        """Find recent logs.

        Args:
            hours: Hours to look back.
            limit: Maximum logs to return.

        Returns:
            List of recent logs.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(CommLog)
            .where(CommLog.timestamp >= cutoff)
            .order_by(CommLog.timestamp.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def log_command(
        self,
        session_id: str,
        raw_data: str,
        decoded_data: Optional[str] = None,
    ) -> CommLog:
        """Log a command.

        Args:
            session_id: Session UUID.
            raw_data: Raw APDU data (hex).
            decoded_data: Optional decoded representation.

        Returns:
            Created log entry.
        """
        log = CommLog.create_command(session_id, raw_data, decoded_data)
        return self.create(log)

    def log_response(
        self,
        session_id: str,
        raw_data: str,
        latency_ms: Optional[float] = None,
        decoded_data: Optional[str] = None,
    ) -> CommLog:
        """Log a response.

        Args:
            session_id: Session UUID.
            raw_data: Raw APDU data (hex).
            latency_ms: Response latency.
            decoded_data: Optional decoded representation.

        Returns:
            Created log entry.
        """
        log = CommLog.create_response(session_id, raw_data, latency_ms, decoded_data)
        return self.create(log)

    def get_session_summary(self, session_id: str) -> dict:
        """Get summary statistics for a session.

        Args:
            session_id: Session UUID.

        Returns:
            Dictionary with log statistics.
        """
        logs = self.find_by_session(session_id)
        commands = [l for l in logs if l.is_command]
        responses = [l for l in logs if l.is_response]

        # Calculate latency stats
        latencies = [r.latency_ms for r in responses if r.latency_ms]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Count success/errors
        success_count = sum(1 for r in responses if r.is_success)
        error_count = len(responses) - success_count

        return {
            "total_logs": len(logs),
            "command_count": len(commands),
            "response_count": len(responses),
            "success_count": success_count,
            "error_count": error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
        }

    def delete_for_session(self, session_id: str) -> int:
        """Delete all logs for a session.

        Args:
            session_id: Session UUID.

        Returns:
            Number of deleted logs.
        """
        return self.delete_by(session_id=session_id)

    def get_stats(self, hours: Optional[int] = None) -> dict:
        """Get overall log statistics.

        Args:
            hours: If specified, only count logs from last N hours.

        Returns:
            Dictionary with statistics.
        """
        base_query = select(func.count()).select_from(CommLog)

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            base_query = base_query.where(CommLog.timestamp >= cutoff)

        total = self._session.execute(base_query).scalar() or 0

        return {
            "total": total,
            "commands": self.count_by(direction=CommDirection.COMMAND.value),
            "responses": self.count_by(direction=CommDirection.RESPONSE.value),
        }
