"""Repository classes for GP OTA Tester database.

This module exports all repository classes and pagination types.

Example:
    >>> from gp_ota_tester.database.repositories import (
    ...     DeviceRepository,
    ...     CardRepository,
    ...     SessionRepository,
    ...     LogRepository,
    ...     TestRepository,
    ...     SettingRepository,
    ...     Page,
    ... )
"""

from gp_ota_tester.database.repositories.base import BaseRepository, Page
from gp_ota_tester.database.repositories.card_repository import CardRepository
from gp_ota_tester.database.repositories.device_repository import DeviceRepository
from gp_ota_tester.database.repositories.log_repository import LogRepository
from gp_ota_tester.database.repositories.session_repository import SessionRepository
from gp_ota_tester.database.repositories.setting_repository import SettingRepository
from gp_ota_tester.database.repositories.test_repository import TestRepository

__all__ = [
    # Base
    "BaseRepository",
    "Page",
    # Repositories
    "DeviceRepository",
    "CardRepository",
    "SessionRepository",
    "LogRepository",
    "TestRepository",
    "SettingRepository",
]
