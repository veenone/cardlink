"""Device model for GP OTA Tester.

This module defines the Device model for storing phone and modem
device configurations.

Example:
    >>> from gp_ota_tester.database.models import Device, DeviceType
    >>> device = Device(
    ...     id="RF8M33XXXXX",
    ...     name="Test Phone 1",
    ...     device_type=DeviceType.PHONE,
    ...     manufacturer="Samsung",
    ...     model="Galaxy S21",
    ... )
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gp_ota_tester.database.models.base import Base, TimestampMixin
from gp_ota_tester.database.models.enums import DeviceType

if TYPE_CHECKING:
    from gp_ota_tester.database.models.session import OTASession
    from gp_ota_tester.database.models.test_result import TestResult


class Device(Base, TimestampMixin):
    """Device configuration model for phones and modems.

    Stores device information including identifiers, connection settings,
    and activity status. Devices are identified by their ADB serial (phones)
    or serial port path (modems).

    Attributes:
        id: Device identifier (ADB serial or serial port path).
        name: User-friendly device alias.
        device_type: Type of device (phone or modem).
        manufacturer: Device manufacturer.
        model: Device model name.
        firmware_version: Device firmware/OS version.
        imei: International Mobile Equipment Identity.
        imsi: International Mobile Subscriber Identity.
        iccid: Integrated Circuit Card Identifier.
        connection_settings: JSON object with connection parameters.
        last_seen: Last time device was detected/connected.
        is_active: Whether device is active for testing.
        notes: Additional notes about the device.

    Relationships:
        sessions: OTA sessions conducted with this device.
        test_results: Test results from this device.

    Example:
        >>> device = Device(
        ...     id="RF8M33XXXXX",
        ...     name="Test Phone 1",
        ...     device_type=DeviceType.PHONE,
        ... )
        >>> device.is_phone
        True
    """

    __tablename__ = "devices"

    # Primary key - ADB serial or serial port path
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        doc="Device identifier (ADB serial or serial port)",
    )

    # User-friendly name
    name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="User-friendly device alias",
    )

    # Device type
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType),
        nullable=False,
        doc="Type of device (phone or modem)",
    )

    # Device information
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="Device manufacturer (e.g., Samsung, Qualcomm)",
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="Device model name",
    )

    firmware_version: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="Device firmware/OS version",
    )

    # Identifiers
    imei: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="International Mobile Equipment Identity",
    )

    imsi: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="International Mobile Subscriber Identity",
    )

    iccid: Mapped[Optional[str]] = mapped_column(
        String(22),
        nullable=True,
        doc="Integrated Circuit Card Identifier",
    )

    # Connection settings (JSON for flexibility)
    connection_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Connection parameters (port, baud rate, etc.)",
    )

    # Status
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Last time device was detected/connected",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether device is active for testing",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Additional notes about the device",
    )

    # Relationships
    sessions: Mapped[List["OTASession"]] = relationship(
        "OTASession",
        back_populates="device",
        lazy="dynamic",
    )

    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="device",
        lazy="dynamic",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_device_type", "device_type"),
        Index("idx_device_iccid", "iccid"),
        Index("idx_device_last_seen", "last_seen"),
        Index("idx_device_active", "is_active"),
    )

    @property
    def is_phone(self) -> bool:
        """Check if device is a phone."""
        return self.device_type == DeviceType.PHONE

    @property
    def is_modem(self) -> bool:
        """Check if device is a modem."""
        return self.device_type == DeviceType.MODEM

    @property
    def display_name(self) -> str:
        """Get display name for device.

        Returns:
            User-friendly name or ID if name not set.
        """
        return self.name or self.id

    def update_last_seen(self) -> None:
        """Update last_seen to current time."""
        self.last_seen = datetime.utcnow()

    def set_connection_setting(self, key: str, value: Any) -> None:
        """Set a connection setting.

        Args:
            key: Setting key.
            value: Setting value.
        """
        if self.connection_settings is None:
            self.connection_settings = {}
        self.connection_settings[key] = value

    def get_connection_setting(self, key: str, default: Any = None) -> Any:
        """Get a connection setting.

        Args:
            key: Setting key.
            default: Default value if not found.

        Returns:
            Setting value or default.
        """
        if self.connection_settings is None:
            return default
        return self.connection_settings.get(key, default)
