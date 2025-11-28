"""Test result repository for GP OTA Tester.

This module provides the repository for test result CRUD operations
and test-specific queries.

Example:
    >>> from gp_ota_tester.database.repositories import TestRepository
    >>> with UnitOfWork(manager) as uow:
    ...     results = uow.tests.find_by_run(run_id)
    ...     passed = uow.tests.find_passed()
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from gp_ota_tester.database.models import TestResult, TestStatus
from gp_ota_tester.database.repositories.base import BaseRepository


class TestRepository(BaseRepository[TestResult]):
    """Repository for test result operations.

    Provides CRUD operations and test-specific queries.

    Example:
        >>> repo = TestRepository(session)
        >>> results = repo.find_by_run(run_id)
        >>> stats = repo.get_run_stats(run_id)
    """

    def __init__(self, session: Session) -> None:
        """Initialize test repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, TestResult)

    def find_by_run(self, run_id: str) -> List[TestResult]:
        """Find all results for a test run.

        Args:
            run_id: Test run UUID.

        Returns:
            List of test results for the run.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.run_id == run_id)
            .order_by(TestResult.started_at)
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_status(self, status: TestStatus) -> List[TestResult]:
        """Find results by status.

        Args:
            status: Test status to filter by.

        Returns:
            List of matching results.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.status == status)
            .order_by(TestResult.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_passed(self) -> List[TestResult]:
        """Find passed tests.

        Returns:
            List of passed test results.
        """
        return self.find_by_status(TestStatus.PASSED)

    def find_failed(self) -> List[TestResult]:
        """Find failed tests.

        Returns:
            List of failed test results.
        """
        return self.find_by_status(TestStatus.FAILED)

    def find_by_suite(self, suite_name: str) -> List[TestResult]:
        """Find results for a test suite.

        Args:
            suite_name: Test suite name.

        Returns:
            List of results for the suite.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.suite_name == suite_name)
            .order_by(TestResult.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_device(self, device_id: str) -> List[TestResult]:
        """Find results for a device.

        Args:
            device_id: Device ID.

        Returns:
            List of results for the device.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.device_id == device_id)
            .order_by(TestResult.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_card(self, iccid: str) -> List[TestResult]:
        """Find results for a card.

        Args:
            iccid: Card ICCID.

        Returns:
            List of results for the card.
        """
        stmt = (
            select(TestResult)
            .where(TestResult.card_iccid == iccid)
            .order_by(TestResult.created_at.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_recent(
        self,
        hours: int = 24,
        limit: Optional[int] = None,
    ) -> List[TestResult]:
        """Find recent test results.

        Args:
            hours: Hours to look back.
            limit: Maximum results to return.

        Returns:
            List of recent results.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(TestResult)
            .where(TestResult.created_at >= cutoff)
            .order_by(TestResult.created_at.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_run_ids(self, limit: int = 100) -> List[str]:
        """Get distinct run IDs ordered by most recent.

        Args:
            limit: Maximum run IDs to return.

        Returns:
            List of run ID strings.
        """
        stmt = (
            select(TestResult.run_id)
            .distinct()
            .order_by(TestResult.created_at.desc())
            .limit(limit)
        )
        result = self._session.execute(stmt)
        return [row[0] for row in result.all()]

    def get_suite_names(self) -> List[str]:
        """Get all distinct suite names.

        Returns:
            List of suite names.
        """
        stmt = select(TestResult.suite_name).distinct()
        result = self._session.execute(stmt)
        return [row[0] for row in result.all()]

    def get_run_stats(self, run_id: str) -> Dict[str, int]:
        """Get statistics for a test run.

        Args:
            run_id: Test run UUID.

        Returns:
            Dictionary with test counts by status.
        """
        results = self.find_by_run(run_id)

        stats = {
            "total": len(results),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0,
            "duration_ms": 0,
        }

        for result in results:
            stats[result.status.value] += 1
            if result.duration_ms:
                stats["duration_ms"] += result.duration_ms

        return stats

    def get_suite_stats(self, suite_name: str) -> Dict[str, int]:
        """Get statistics for a test suite.

        Args:
            suite_name: Test suite name.

        Returns:
            Dictionary with test counts by status.
        """
        results = self.find_by_suite(suite_name)

        stats = {
            "total": len(results),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0,
        }

        for result in results:
            stats[result.status.value] += 1

        return stats

    def get_overall_stats(
        self,
        hours: Optional[int] = None,
    ) -> Dict[str, any]:
        """Get overall test statistics.

        Args:
            hours: If specified, only count tests from last N hours.

        Returns:
            Dictionary with statistics.
        """
        base_conditions = []
        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            base_conditions.append(TestResult.created_at >= cutoff)

        # Count by status
        stats = {"total": 0}
        for status in TestStatus:
            conditions = base_conditions + [TestResult.status == status]
            count_query = (
                select(func.count())
                .select_from(TestResult)
                .where(and_(*conditions) if conditions else True)
            )
            count = self._session.execute(count_query).scalar() or 0
            stats[status.value] = count
            stats["total"] += count

        # Calculate pass rate
        if stats["total"] > 0:
            stats["pass_rate"] = round(
                (stats["passed"] / stats["total"]) * 100, 2
            )
        else:
            stats["pass_rate"] = 0.0

        return stats

    def delete_by_run(self, run_id: str) -> int:
        """Delete all results for a test run.

        Args:
            run_id: Test run UUID.

        Returns:
            Number of deleted results.
        """
        return self.delete_by(run_id=run_id)

    def cleanup_old(self, days: int = 30) -> int:
        """Delete test results older than N days.

        Args:
            days: Days threshold.

        Returns:
            Number of deleted results.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        results = self.find_by(lambda r: r.created_at < cutoff)

        count = 0
        for result in results:
            self.delete(result)
            count += 1

        return count
