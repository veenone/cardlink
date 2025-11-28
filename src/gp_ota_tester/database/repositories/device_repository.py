"""Device repository for GP OTA Tester.

This module provides the repository for device CRUD operations
and device-specific queries.

Example:
    >>> from gp_ota_tester.database.repositories import DeviceRepository
    >>> with UnitOfWork(manager) as uow:
    ...     phones = uow.devices.find_phones()
    ...     active = uow.devices.find_active()
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from gp_ota_tester.database.models import Device, DeviceType
from gp_ota_tester.database.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    """Repository for device operations.

    Provides CRUD operations and device-specific queries for
    phone and modem devices.

    Example:
        >>> repo = DeviceRepository(session)
        >>> phones = repo.find_phones()
        >>> recent = repo.find_recent(hours=24)
    """

    def __init__(self, session: Session) -> None:
        """Initialize device repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, Device)

    def find_by_type(self, device_type: DeviceType) -> List[Device]:
        """Find devices by type.

        Args:
            device_type: Device type to filter by.

        Returns:
            List of devices matching the type.
        """
        stmt = select(Device).where(Device.device_type == device_type)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_phones(self) -> List[Device]:
        """Find all phone devices.

        Returns:
            List of phone devices.
        """
        return self.find_by_type(DeviceType.PHONE)

    def find_modems(self) -> List[Device]:
        """Find all modem devices.

        Returns:
            List of modem devices.
        """
        return self.find_by_type(DeviceType.MODEM)

    def find_active(self) -> List[Device]:
        """Find all active devices.

        Returns:
            List of active devices.
        """
        stmt = select(Device).where(Device.is_active == True)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_inactive(self) -> List[Device]:
        """Find all inactive devices.

        Returns:
            List of inactive devices.
        """
        stmt = select(Device).where(Device.is_active == False)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_recent(self, hours: int = 24) -> List[Device]:
        """Find devices seen within the specified hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of recently seen devices.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Device)
            .where(Device.last_seen >= cutoff)
            .order_by(Device.last_seen.desc())
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_stale(self, hours: int = 24) -> List[Device]:
        """Find devices not seen within the specified hours.

        Args:
            hours: Number of hours threshold.

        Returns:
            List of stale devices.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(Device).where(
            or_(
                Device.last_seen < cutoff,
                Device.last_seen.is_(None),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def search(self, query: str) -> List[Device]:
        """Search devices by name, ID, or model.

        Args:
            query: Search string.

        Returns:
            List of matching devices.
        """
        pattern = f"%{query}%"
        stmt = select(Device).where(
            or_(
                Device.id.ilike(pattern),
                Device.name.ilike(pattern),
                Device.model.ilike(pattern),
                Device.manufacturer.ilike(pattern),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_iccid(self, iccid: str) -> List[Device]:
        """Find devices with specific ICCID.

        Args:
            iccid: ICCID to search for.

        Returns:
            List of matching devices.
        """
        stmt = select(Device).where(Device.iccid == iccid)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_by_imei(self, imei: str) -> Optional[Device]:
        """Find device by IMEI.

        Args:
            imei: IMEI to search for.

        Returns:
            Device if found, None otherwise.
        """
        stmt = select(Device).where(Device.imei == imei)
        result = self._session.execute(stmt)
        return result.scalar_one_or_none()

    def update_last_seen(self, device_id: str) -> bool:
        """Update device last seen timestamp.

        Args:
            device_id: Device ID to update.

        Returns:
            True if device was updated.
        """
        stmt = (
            update(Device)
            .where(Device.id == device_id)
            .values(last_seen=datetime.utcnow())
        )
        result = self._session.execute(stmt)
        return result.rowcount > 0

    def activate(self, device_id: str) -> bool:
        """Activate a device.

        Args:
            device_id: Device ID to activate.

        Returns:
            True if device was activated.
        """
        stmt = (
            update(Device)
            .where(Device.id == device_id)
            .values(is_active=True)
        )
        result = self._session.execute(stmt)
        return result.rowcount > 0

    def deactivate(self, device_id: str) -> bool:
        """Deactivate a device.

        Args:
            device_id: Device ID to deactivate.

        Returns:
            True if device was deactivated.
        """
        stmt = (
            update(Device)
            .where(Device.id == device_id)
            .values(is_active=False)
        )
        result = self._session.execute(stmt)
        return result.rowcount > 0

    def get_stats(self) -> dict:
        """Get device statistics.

        Returns:
            Dictionary with device counts by type and status.
        """
        return {
            "total": self.count(),
            "phones": self.count_by(device_type=DeviceType.PHONE),
            "modems": self.count_by(device_type=DeviceType.MODEM),
            "active": self.count_by(is_active=True),
            "inactive": self.count_by(is_active=False),
            "recent_24h": len(self.find_recent(hours=24)),
        }
