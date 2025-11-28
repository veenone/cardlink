"""Database models for GP OTA Tester.

This module exports all SQLAlchemy models and enumerations.

Example:
    >>> from gp_ota_tester.database.models import (
    ...     Device, DeviceType,
    ...     CardProfile,
    ...     OTASession, SessionStatus,
    ...     CommLog, CommDirection,
    ...     TestResult, TestStatus,
    ...     Setting,
    ... )
"""

from gp_ota_tester.database.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid
from gp_ota_tester.database.models.card_profile import CardProfile
from gp_ota_tester.database.models.comm_log import CommLog
from gp_ota_tester.database.models.device import Device
from gp_ota_tester.database.models.enums import (
    CardType,
    CommDirection,
    DeviceType,
    SessionStatus,
    TestStatus,
)
from gp_ota_tester.database.models.session import OTASession
from gp_ota_tester.database.models.setting import Setting, SettingKeys
from gp_ota_tester.database.models.test_result import TestResult

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
