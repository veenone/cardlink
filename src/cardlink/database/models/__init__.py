"""Database models for GP OTA Tester.

This module exports all SQLAlchemy models and enumerations.

Example:
    >>> from cardlink.database.models import (
    ...     Device, DeviceType,
    ...     CardProfile,
    ...     OTASession, SessionStatus,
    ...     CommLog, CommDirection,
    ...     TestResult, TestStatus,
    ...     Setting,
    ... )
"""

from cardlink.database.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid
from cardlink.database.models.card_profile import CardProfile
from cardlink.database.models.comm_log import CommLog
from cardlink.database.models.device import Device
from cardlink.database.models.enums import (
    CardType,
    CommDirection,
    DeviceType,
    SessionStatus,
    TestStatus,
)
from cardlink.database.models.session import OTASession
from cardlink.database.models.setting import Setting, SettingKeys
from cardlink.database.models.test_result import TestResult

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid",
    # Enums
    "DeviceType",
    "SessionStatus",
    "TestStatus",
    "CommDirection",
    "CardType",
    # Models
    "Device",
    "CardProfile",
    "OTASession",
    "CommLog",
    "TestResult",
    "Setting",
    "SettingKeys",
]
