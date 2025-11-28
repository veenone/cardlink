"""Communication log model for GP OTA Tester.

This module defines the CommLog model for recording APDU commands
and responses during OTA sessions.

Example:
    >>> from gp_ota_tester.database.models import CommLog, CommDirection
    >>> log = CommLog(
    ...     session_id="550e8400-e29b-41d4-a716-446655440000",
    ...     direction=CommDirection.COMMAND,
    ...     raw_data="00A4040007A0000000041010",
    ... )
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from gp_ota_tester.database.models.base import Base
from gp_ota_tester.database.models.enums import CommDirection

if TYPE_CHECKING:
    from gp_ota_tester.database.models.session import OTASession


# Common status word messages
STATUS_WORDS = {
    "9000": "Success",
    "6100": "More data available",
    "6283": "Selected file invalidated",
    "6300": "Verification failed",
    "6400": "Execution error",
    "6581": "Memory failure",
    "6700": "Wrong length",
    "6881": "Logical channel not supported",
    "6882": "Secure messaging not supported",
    "6883": "Last command expected",
    "6884": "Command chaining not supported",
    "6982": "Security status not satisfied",
    "6983": "Authentication blocked",
    "6984": "Reference data invalidated",
    "6985": "Conditions of use not satisfied",
    "6986": "Command not allowed",
    "6A80": "Incorrect parameters in data field",
    "6A81": "Function not supported",
    "6A82": "File not found",
    "6A83": "Record not found",
    "6A84": "Not enough memory",
    "6A86": "Incorrect P1P2",
    "6A87": "LC inconsistent with P1P2",
    "6A88": "Referenced data not found",
    "6B00": "Wrong P1P2",
    "6D00": "INS not supported",
    "6E00": "CLA not supported",
    "6F00": "Unknown error",
}


class CommLog(Base):
    """Communication log entry model.

    Records individual APDU commands and responses during OTA sessions.
    Each entry captures the raw data, timing, and decoded information.

    Attributes:
        id: Auto-incrementing primary key.
        session_id: Associated session UUID.
        timestamp: When the command/response occurred.
        latency_ms: Response latency in milliseconds.
        direction: Command or response.
        raw_data: Raw APDU data (hex encoded).
        decoded_data: Human-readable decoded data.
        status_word: Response status word (SW1SW2).
        status_message: Human-readable status message.

    Relationships:
        session: Associated OTA session.

    Example:
        >>> log = CommLog(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     direction=CommDirection.COMMAND,
        ...     raw_data="00A4040007A0000000041010",
        ... )
        >>> log.decode_status_word("9000")
        'Success'
    """

    __tablename__ = "comm_logs"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key",
    )

    # Foreign key
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ota_sessions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated session UUID",
    )

    # Timing
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        doc="When the command/response occurred",
    )

    latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Response latency in milliseconds",
    )

    # Data
    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Direction: command or response",
    )

    raw_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw APDU data (hex encoded)",
    )

    decoded_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable decoded data",
    )

    # Response info
    status_word: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        doc="Response status word (SW1SW2 hex)",
    )

    status_message: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Human-readable status message",
    )

    # Relationships
    session: Mapped["OTASession"] = relationship(
        "OTASession",
        back_populates="comm_logs",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_log_session", "session_id"),
        Index("idx_log_timestamp", "timestamp"),
        Index("idx_log_direction", "direction"),
        Index("idx_log_status_word", "status_word"),
    )

    @property
    def is_command(self) -> bool:
        """Check if this is a command."""
        return self.direction == CommDirection.COMMAND.value

    @property
    def is_response(self) -> bool:
        """Check if this is a response."""
        return self.direction == CommDirection.RESPONSE.value

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (SW 9000 or 61XX)."""
        if not self.status_word:
            return False
        return self.status_word == "9000" or self.status_word.startswith("61")

    @property
    def raw_bytes(self) -> bytes:
        """Get raw data as bytes.

        Returns:
            Raw data decoded from hex.
        """
        return bytes.fromhex(self.raw_data)

    @property
    def data_length(self) -> int:
        """Get length of raw data in bytes."""
        return len(self.raw_data) // 2

    @classmethod
    def decode_status_word(cls, sw: str) -> str:
        """Decode status word to human-readable message.

        Args:
            sw: Status word (4 hex characters).

        Returns:
            Human-readable status message.
        """
        sw_upper = sw.upper()

        # Check exact match
        if sw_upper in STATUS_WORDS:
            return STATUS_WORDS[sw_upper]

        # Check prefix matches (61XX, 6CXX, etc.)
        sw_prefix = sw_upper[:2] + "00"
        if sw_prefix in STATUS_WORDS:
            return STATUS_WORDS[sw_prefix]

        # Unknown status word
        return f"Unknown status word: {sw_upper}"

    @classmethod
    def create_command(
        cls,
        session_id: str,
        raw_data: str,
        decoded_data: Optional[str] = None,
    ) -> "CommLog":
        """Create a command log entry.

        Args:
            session_id: Session UUID.
            raw_data: Raw APDU command (hex).
            decoded_data: Optional decoded representation.

        Returns:
            New CommLog instance.
        """
        return cls(
            session_id=session_id,
            direction=CommDirection.COMMAND.value,
            raw_data=raw_data.upper().replace(" ", ""),
            decoded_data=decoded_data,
        )

    @classmethod
    def create_response(
        cls,
        session_id: str,
        raw_data: str,
        latency_ms: Optional[float] = None,
        decoded_data: Optional[str] = None,
    ) -> "CommLog":
        """Create a response log entry.

        Args:
            session_id: Session UUID.
            raw_data: Raw APDU response (hex).
            latency_ms: Response latency.
            decoded_data: Optional decoded representation.

        Returns:
            New CommLog instance with status word decoded.
        """
        clean_data = raw_data.upper().replace(" ", "")
        status_word = clean_data[-4:] if len(clean_data) >= 4 else None
        status_message = cls.decode_status_word(status_word) if status_word else None

        return cls(
            session_id=session_id,
            direction=CommDirection.RESPONSE.value,
            raw_data=clean_data,
            latency_ms=latency_ms,
            decoded_data=decoded_data,
            status_word=status_word,
            status_message=status_message,
        )
