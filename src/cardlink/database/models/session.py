"""OTA Session model for GP OTA Tester.

This module defines the OTASession model for recording OTA
communication sessions between the server and UICC cards.

Example:
    >>> from cardlink.database.models import OTASession, SessionStatus
    >>> session = OTASession(
    ...     device_id="RF8M33XXXXX",
    ...     card_iccid="89012345678901234567",
    ...     status=SessionStatus.PENDING,
    ... )
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cardlink.database.models.base import Base, TimestampMixin, generate_uuid
from cardlink.database.models.enums import SessionStatus

if TYPE_CHECKING:
    from cardlink.database.models.card_profile import CardProfile
    from cardlink.database.models.comm_log import CommLog
    from cardlink.database.models.device import Device


class OTASession(Base, TimestampMixin):
    """OTA session record model.

    Records information about OTA communication sessions including
    timing, TLS parameters, and status.

    Attributes:
        id: Unique session identifier (UUID).
        device_id: Associated device identifier.
        card_iccid: Associated card ICCID.
        session_type: Type of session (triggered, polled).
        status: Current session status.
        started_at: When session started.
        ended_at: When session ended.
        duration_ms: Session duration in milliseconds.
        tls_cipher_suite: TLS cipher suite used.
        tls_psk_identity: PSK identity used for TLS.
        error_code: Error code if session failed.
        error_message: Error message if session failed.

    Relationships:
        device: Associated device.
        card: Associated card profile.
        comm_logs: Communication logs for this session.

    Example:
        >>> session = OTASession(device_id="RF8M33XXXXX")
        >>> session.start()
        >>> # ... perform OTA operations ...
        >>> session.complete()
    """

    __tablename__ = "ota_sessions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique session identifier (UUID)",
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

    # Session info
    session_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Type of session (triggered, polled)",
    )

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus),
        default=SessionStatus.PENDING,
        nullable=False,
        doc="Current session status",
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="When session started (connection established)",
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="When session ended",
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Session duration in milliseconds",
    )

    # TLS info
    tls_cipher_suite: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="TLS cipher suite used for connection",
    )

    tls_psk_identity: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="PSK identity used for TLS authentication",
    )

    # Error info
    error_code: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        doc="Error code if session failed",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if session failed",
    )

    # Relationships
    device: Mapped[Optional["Device"]] = relationship(
        "Device",
        back_populates="sessions",
    )

    card: Mapped[Optional["CardProfile"]] = relationship(
        "CardProfile",
        back_populates="sessions",
    )

    comm_logs: Mapped[List["CommLog"]] = relationship(
        "CommLog",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CommLog.timestamp",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_session_device", "device_id"),
        Index("idx_session_card", "card_iccid"),
        Index("idx_session_status", "status"),
        Index("idx_session_created", "created_at"),
        Index("idx_session_started", "started_at"),
    )

    @property
    def is_pending(self) -> bool:
        """Check if session is pending."""
        return self.status == SessionStatus.PENDING

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if session completed successfully."""
        return self.status == SessionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if session failed."""
        return self.status == SessionStatus.FAILED

    @property
    def is_timeout(self) -> bool:
        """Check if session timed out."""
        return self.status == SessionStatus.TIMEOUT

    @property
    def is_finished(self) -> bool:
        """Check if session is finished (completed, failed, or timeout)."""
        return self.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.TIMEOUT,
        )

    def start(self) -> None:
        """Mark session as started.

        Sets started_at timestamp and status to ACTIVE.
        """
        self.started_at = datetime.utcnow()
        self.status = SessionStatus.ACTIVE

    def complete(self) -> None:
        """Mark session as completed successfully.

        Sets ended_at timestamp, calculates duration, and
        sets status to COMPLETED.
        """
        self.ended_at = datetime.utcnow()
        self.status = SessionStatus.COMPLETED
        self._calculate_duration()

    def fail(self, error_code: str, error_message: str) -> None:
        """Mark session as failed.

        Args:
            error_code: Error code.
            error_message: Error message.
        """
        self.ended_at = datetime.utcnow()
        self.status = SessionStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self._calculate_duration()

    def timeout(self) -> None:
        """Mark session as timed out."""
        self.ended_at = datetime.utcnow()
        self.status = SessionStatus.TIMEOUT
        self.error_code = "TIMEOUT"
        self.error_message = "Session timed out waiting for connection"
        self._calculate_duration()

    def _calculate_duration(self) -> None:
        """Calculate duration in milliseconds."""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def set_tls_info(
        self,
        cipher_suite: str,
        psk_identity: Optional[str] = None,
    ) -> None:
        """Set TLS connection information.

        Args:
            cipher_suite: TLS cipher suite.
            psk_identity: PSK identity used.
        """
        self.tls_cipher_suite = cipher_suite
        if psk_identity:
            self.tls_psk_identity = psk_identity
