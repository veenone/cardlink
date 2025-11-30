"""Test result model for GP OTA Tester.

This module defines the TestResult model for recording test
execution results with assertions and metadata.

Example:
    >>> from cardlink.database.models import TestResult, TestStatus
    >>> result = TestResult(
    ...     run_id="550e8400-e29b-41d4-a716-446655440000",
    ...     suite_name="OTA Installation",
    ...     test_name="test_install_applet",
    ...     status=TestStatus.PASSED,
    ... )
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cardlink.database.models.base import Base, TimestampMixin, generate_uuid
from cardlink.database.models.enums import TestStatus

if TYPE_CHECKING:
    from cardlink.database.models.card_profile import CardProfile
    from cardlink.database.models.device import Device


class TestResult(Base, TimestampMixin):
    """Test execution result model.

    Records test execution results including timing, status,
    assertions, and metadata. Results are grouped by run_id.

    Attributes:
        id: Unique result identifier (UUID).
        run_id: Groups results from same test run (UUID).
        suite_name: Test suite name.
        test_name: Test case name.
        device_id: Associated device identifier.
        card_iccid: Associated card ICCID.
        started_at: When test started.
        ended_at: When test ended.
        duration_ms: Test duration in milliseconds.
        status: Test result status.
        error_message: Error message if failed/error.
        assertions: Array of assertion results.
        metadata: Additional test metadata.

    Relationships:
        device: Associated device.
        card: Associated card profile.

    Example:
        >>> result = TestResult.create(
        ...     run_id="...",
        ...     suite_name="OTA Tests",
        ...     test_name="test_select_isd",
        ... )
        >>> result.add_assertion("Status word is 9000", True)
        >>> result.pass_test()
    """

    __tablename__ = "test_results"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique result identifier (UUID)",
    )

    # Test run grouping
    run_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="Groups results from same test run",
    )

    # Test identification
    suite_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Test suite name",
    )

    test_name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        doc="Test case name",
    )

    # Foreign keys
    device_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        doc="Associated device identifier",
    )

    card_iccid: Mapped[Optional[str]] = mapped_column(
        String(22),
        ForeignKey("card_profiles.iccid", ondelete="SET NULL"),
        nullable=True,
        doc="Associated card ICCID",
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="When test started",
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="When test ended",
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Test duration in milliseconds",
    )

    # Result
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus),
        nullable=False,
        default=TestStatus.PASSED,
        doc="Test result status",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if failed/error",
    )

    # Details (JSON)
    assertions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        doc="Array of assertion results",
    )

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        doc="Additional test metadata",
    )

    # Relationships
    device: Mapped[Optional["Device"]] = relationship(
        "Device",
        back_populates="test_results",
    )

    card: Mapped[Optional["CardProfile"]] = relationship(
        "CardProfile",
        back_populates="test_results",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_test_run", "run_id"),
        Index("idx_test_suite", "suite_name"),
        Index("idx_test_status", "status"),
        Index("idx_test_created", "created_at"),
        Index("idx_test_device", "device_id"),
        Index("idx_test_card", "card_iccid"),
    )

    @property
    def is_passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASSED

    @property
    def is_failed(self) -> bool:
        """Check if test failed."""
        return self.status == TestStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        """Check if test was skipped."""
        return self.status == TestStatus.SKIPPED

    @property
    def is_error(self) -> bool:
        """Check if test had an error."""
        return self.status == TestStatus.ERROR

    @property
    def full_name(self) -> str:
        """Get full test name (suite::test)."""
        return f"{self.suite_name}::{self.test_name}"

    @property
    def assertion_count(self) -> int:
        """Get number of assertions."""
        return len(self.assertions) if self.assertions else 0

    @property
    def failed_assertion_count(self) -> int:
        """Get number of failed assertions."""
        if not self.assertions:
            return 0
        return sum(1 for a in self.assertions if not a.get("passed", True))

    def add_assertion(
        self,
        name: str,
        passed: bool,
        message: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
    ) -> None:
        """Add an assertion result.

        Args:
            name: Assertion name/description.
            passed: Whether assertion passed.
            message: Optional assertion message.
            expected: Expected value.
            actual: Actual value.
        """
        if self.assertions is None:
            self.assertions = []

        assertion = {
            "name": name,
            "passed": passed,
        }

        if message:
            assertion["message"] = message
        if expected is not None:
            assertion["expected"] = str(expected)
        if actual is not None:
            assertion["actual"] = str(actual)

        self.assertions.append(assertion)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        if self.metadata_ is None:
            self.metadata_ = {}
        self.metadata_[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key.
            default: Default value if not found.

        Returns:
            Metadata value or default.
        """
        if self.metadata_ is None:
            return default
        return self.metadata_.get(key, default)

    def _finish(self, status: TestStatus, error_message: Optional[str] = None) -> None:
        """Finish test with given status.

        Args:
            status: Final test status.
            error_message: Optional error message.
        """
        self.ended_at = datetime.utcnow()
        self.status = status
        if error_message:
            self.error_message = error_message
        self._calculate_duration()

    def pass_test(self) -> None:
        """Mark test as passed."""
        self._finish(TestStatus.PASSED)

    def fail_test(self, message: Optional[str] = None) -> None:
        """Mark test as failed.

        Args:
            message: Failure message.
        """
        self._finish(TestStatus.FAILED, message)

    def skip_test(self, reason: Optional[str] = None) -> None:
        """Mark test as skipped.

        Args:
            reason: Skip reason.
        """
        self._finish(TestStatus.SKIPPED, reason)

    def error_test(self, message: str) -> None:
        """Mark test as errored.

        Args:
            message: Error message.
        """
        self._finish(TestStatus.ERROR, message)

    def _calculate_duration(self) -> None:
        """Calculate duration in milliseconds."""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    @classmethod
    def create(
        cls,
        run_id: str,
        suite_name: str,
        test_name: str,
        device_id: Optional[str] = None,
        card_iccid: Optional[str] = None,
    ) -> "TestResult":
        """Create a new test result.

        Args:
            run_id: Test run UUID.
            suite_name: Test suite name.
            test_name: Test case name.
            device_id: Optional device ID.
            card_iccid: Optional card ICCID.

        Returns:
            New TestResult instance.
        """
        return cls(
            run_id=run_id,
            suite_name=suite_name,
            test_name=test_name,
            device_id=device_id,
            card_iccid=card_iccid,
            started_at=datetime.utcnow(),
            assertions=[],
            metadata_={},
        )
