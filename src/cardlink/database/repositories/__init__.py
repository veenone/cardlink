"""Repository classes for GP OTA Tester database.

This module exports all repository classes and pagination types.

Example:
    >>> from cardlink.database.repositories import (
    ...     DeviceRepository,
    ...     CardRepository,
    ...     SessionRepository,
    ...     LogRepository,
    ...     TestRepository,
    ...     SettingRepository,
    ...     ScriptRepository,
    ...     TemplateRepository,
    ...     Page,
    ... )
"""

from cardlink.database.repositories.base import BaseRepository, Page
from cardlink.database.repositories.card_repository import CardRepository
from cardlink.database.repositories.device_repository import DeviceRepository
from cardlink.database.repositories.log_repository import LogRepository
from cardlink.database.repositories.script_repository import ScriptRepository
from cardlink.database.repositories.session_repository import SessionRepository
from cardlink.database.repositories.setting_repository import SettingRepository
from cardlink.database.repositories.template_repository import TemplateRepository
from cardlink.database.repositories.test_repository import TestRepository

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
    "ScriptRepository",
    "TemplateRepository",
]
