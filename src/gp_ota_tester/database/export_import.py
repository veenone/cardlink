"""Data export and import functionality for GP OTA Tester.

This module provides utilities for exporting database data to
YAML/JSON and importing it back.

Example:
    >>> from gp_ota_tester.database.export_import import DataExporter, DataImporter
    >>> exporter = DataExporter(manager)
    >>> yaml_data = exporter.export_all(format="yaml")
    >>>
    >>> importer = DataImporter(manager)
    >>> result = importer.import_data(yaml_data, format="yaml")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from gp_ota_tester.database.manager import DatabaseManager
from gp_ota_tester.database.models import (
    CardProfile,
    Device,
    DeviceType,
    OTASession,
    Setting,
    TestResult,
)
from gp_ota_tester.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Export format options."""

    JSON = "json"
    YAML = "yaml"


class ConflictMode(str, Enum):
    """Import conflict resolution modes."""

    SKIP = "skip"  # Skip existing records
    OVERWRITE = "overwrite"  # Overwrite existing records
    MERGE = "merge"  # Merge fields (preserve existing, add new)


@dataclass
class ImportResult:
    """Result of an import operation.

    Attributes:
        created: Number of records created.
        updated: Number of records updated.
        skipped: Number of records skipped.
        errors: List of error messages.
    """

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total records processed."""
        return self.created + self.updated + self.skipped

    @property
    def has_errors(self) -> bool:
        """Check if there were errors."""
        return len(self.errors) > 0

    def merge(self, other: "ImportResult") -> None:
        """Merge another result into this one."""
        self.created += other.created
        self.updated += other.updated
        self.skipped += other.skipped
        self.errors.extend(other.errors)


class DataExporter:
    """Exports database data to YAML or JSON format.

    Supports selective export of specific tables and
    handles sensitive data (PSK keys) appropriately.

    Example:
        >>> exporter = DataExporter(manager)
        >>> data = exporter.export_all(format="yaml")
        >>> exporter.export_to_file("backup.yaml", format="yaml")
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize exporter.

        Args:
            db_manager: Database manager instance.
        """
        self._db_manager = db_manager

    def export_all(
        self,
        format: str = "yaml",
        include_psk: bool = False,
    ) -> str:
        """Export all data.

        Args:
            format: Output format ("yaml" or "json").
            include_psk: Whether to include encrypted PSK keys.

        Returns:
            Exported data as string.
        """
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "devices": self._export_devices(),
            "cards": self._export_cards(include_psk=include_psk),
            "settings": self._export_settings(),
        }

        return self._serialize(data, format)

    def export_selective(
        self,
        tables: List[str],
        format: str = "yaml",
        include_psk: bool = False,
    ) -> str:
        """Export selected tables.

        Args:
            tables: List of table names to export.
            format: Output format.
            include_psk: Whether to include PSK keys.

        Returns:
            Exported data as string.
        """
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        if "devices" in tables:
            data["devices"] = self._export_devices()
        if "cards" in tables or "card_profiles" in tables:
            data["cards"] = self._export_cards(include_psk=include_psk)
        if "settings" in tables:
            data["settings"] = self._export_settings()
        if "sessions" in tables or "ota_sessions" in tables:
            data["sessions"] = self._export_sessions()
        if "test_results" in tables:
            data["test_results"] = self._export_test_results()

        return self._serialize(data, format)

    def export_to_file(
        self,
        path: str,
        format: str = "yaml",
        include_psk: bool = False,
    ) -> int:
        """Export all data to file.

        Args:
            path: Output file path.
            format: Output format.
            include_psk: Whether to include PSK keys.

        Returns:
            Number of bytes written.
        """
        data = self.export_all(format=format, include_psk=include_psk)
        with open(path, "w") as f:
            f.write(data)
        return len(data)

    def _export_devices(self) -> List[Dict[str, Any]]:
        """Export all devices."""
        with UnitOfWork(self._db_manager) as uow:
            devices = uow.devices.get_all()
            return [self._device_to_dict(d) for d in devices]

    def _export_cards(self, include_psk: bool = False) -> List[Dict[str, Any]]:
        """Export all card profiles."""
        with UnitOfWork(self._db_manager) as uow:
            cards = uow.cards.get_all()
            return [self._card_to_dict(c, include_psk) for c in cards]

    def _export_settings(self) -> List[Dict[str, Any]]:
        """Export all settings."""
        with UnitOfWork(self._db_manager) as uow:
            settings = uow.settings.get_all()
            return [self._setting_to_dict(s) for s in settings]

    def _export_sessions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Export sessions (limited for size)."""
        with UnitOfWork(self._db_manager) as uow:
            sessions = uow.sessions.find_recent(hours=24 * 30, limit=limit)
            return [self._session_to_dict(s) for s in sessions]

    def _export_test_results(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Export test results (limited for size)."""
        with UnitOfWork(self._db_manager) as uow:
            results = uow.tests.find_recent(hours=24 * 30, limit=limit)
            return [self._test_result_to_dict(r) for r in results]

    def _device_to_dict(self, device: Device) -> Dict[str, Any]:
        """Convert device to dictionary."""
        return {
            "id": device.id,
            "name": device.name,
            "device_type": device.device_type.value,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "firmware_version": device.firmware_version,
            "imei": device.imei,
            "imsi": device.imsi,
            "iccid": device.iccid,
            "connection_settings": device.connection_settings,
            "is_active": device.is_active,
            "notes": device.notes,
        }

    def _card_to_dict(
        self,
        card: CardProfile,
        include_psk: bool = False,
    ) -> Dict[str, Any]:
        """Convert card profile to dictionary."""
        data = {
            "iccid": card.iccid,
            "imsi": card.imsi,
            "card_type": card.card_type,
            "atr": card.atr,
            "psk_identity": card.psk_identity,
            "admin_url": card.admin_url,
            "trigger_config": card.trigger_config,
            "bip_config": card.bip_config,
            "security_domains": card.security_domains,
            "notes": card.notes,
        }

        if include_psk and card.psk_key_encrypted:
            # Include encrypted key (base64 encoded)
            import base64

            data["psk_key_encrypted_b64"] = base64.b64encode(
                card.psk_key_encrypted
            ).decode("ascii")

        return data

    def _setting_to_dict(self, setting: Setting) -> Dict[str, Any]:
        """Convert setting to dictionary."""
        return {
            "key": setting.key,
            "value": setting.value,
            "category": setting.category,
            "description": setting.description,
        }

    def _session_to_dict(self, session: OTASession) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": session.id,
            "device_id": session.device_id,
            "card_iccid": session.card_iccid,
            "session_type": session.session_type,
            "status": session.status.value,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_ms": session.duration_ms,
            "tls_cipher_suite": session.tls_cipher_suite,
            "tls_psk_identity": session.tls_psk_identity,
            "error_code": session.error_code,
            "error_message": session.error_message,
        }

    def _test_result_to_dict(self, result: TestResult) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            "id": result.id,
            "run_id": result.run_id,
            "suite_name": result.suite_name,
            "test_name": result.test_name,
            "device_id": result.device_id,
            "card_iccid": result.card_iccid,
            "status": result.status.value,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "ended_at": result.ended_at.isoformat() if result.ended_at else None,
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
            "assertions": result.assertions,
        }

    def _serialize(self, data: Dict[str, Any], format: str) -> str:
        """Serialize data to string."""
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "yaml":
            try:
                import yaml

                return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
            except ImportError:
                logger.warning("PyYAML not installed, falling back to JSON")
                return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unknown format: {format}")


class DataImporter:
    """Imports database data from YAML or JSON format.

    Supports various conflict resolution modes for existing records.

    Example:
        >>> importer = DataImporter(manager)
        >>> result = importer.import_data(yaml_string, format="yaml")
        >>> print(f"Created: {result.created}, Updated: {result.updated}")
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize importer.

        Args:
            db_manager: Database manager instance.
        """
        self._db_manager = db_manager

    def import_data(
        self,
        data_str: str,
        format: str = "yaml",
        conflict_mode: str = "skip",
    ) -> ImportResult:
        """Import data from string.

        Args:
            data_str: Data string to import.
            format: Data format ("yaml" or "json").
            conflict_mode: How to handle conflicts ("skip", "overwrite", "merge").

        Returns:
            ImportResult with counts.
        """
        data = self._deserialize(data_str, format)
        mode = ConflictMode(conflict_mode)
        result = ImportResult()

        # Import in order of dependencies
        if "devices" in data:
            device_result = self._import_devices(data["devices"], mode)
            result.merge(device_result)

        if "cards" in data:
            card_result = self._import_cards(data["cards"], mode)
            result.merge(card_result)

        if "settings" in data:
            settings_result = self._import_settings(data["settings"])
            result.merge(settings_result)

        logger.info(
            "Import completed: %d created, %d updated, %d skipped",
            result.created,
            result.updated,
            result.skipped,
        )

        return result

    def import_from_file(
        self,
        path: str,
        format: Optional[str] = None,
        conflict_mode: str = "skip",
    ) -> ImportResult:
        """Import data from file.

        Args:
            path: File path.
            format: Data format (auto-detected from extension if None).
            conflict_mode: Conflict resolution mode.

        Returns:
            ImportResult with counts.
        """
        with open(path, "r") as f:
            data_str = f.read()

        if format is None:
            if path.endswith(".yaml") or path.endswith(".yml"):
                format = "yaml"
            else:
                format = "json"

        return self.import_data(data_str, format, conflict_mode)

    def _deserialize(self, data_str: str, format: str) -> Dict[str, Any]:
        """Deserialize data from string."""
        if format == "json":
            return json.loads(data_str)
        elif format == "yaml":
            try:
                import yaml

                return yaml.safe_load(data_str)
            except ImportError:
                raise ImportError("PyYAML required for YAML import")
        else:
            raise ValueError(f"Unknown format: {format}")

    def _import_devices(
        self,
        devices: List[Dict[str, Any]],
        mode: ConflictMode,
    ) -> ImportResult:
        """Import devices."""
        result = ImportResult()

        with UnitOfWork(self._db_manager) as uow:
            for device_data in devices:
                try:
                    device_id = device_data.get("id")
                    if not device_id:
                        result.errors.append("Device missing 'id' field")
                        continue

                    existing = uow.devices.get(device_id)

                    if existing:
                        if mode == ConflictMode.SKIP:
                            result.skipped += 1
                        elif mode == ConflictMode.OVERWRITE:
                            self._update_device(existing, device_data)
                            result.updated += 1
                        elif mode == ConflictMode.MERGE:
                            self._merge_device(existing, device_data)
                            result.updated += 1
                    else:
                        device = self._create_device(device_data)
                        uow.devices.add(device)
                        result.created += 1

                except Exception as e:
                    result.errors.append(f"Device {device_data.get('id')}: {e}")

            uow.commit()

        return result

    def _import_cards(
        self,
        cards: List[Dict[str, Any]],
        mode: ConflictMode,
    ) -> ImportResult:
        """Import card profiles."""
        result = ImportResult()

        with UnitOfWork(self._db_manager) as uow:
            for card_data in cards:
                try:
                    iccid = card_data.get("iccid")
                    if not iccid:
                        result.errors.append("Card missing 'iccid' field")
                        continue

                    existing = uow.cards.get(iccid)

                    if existing:
                        if mode == ConflictMode.SKIP:
                            result.skipped += 1
                        elif mode == ConflictMode.OVERWRITE:
                            self._update_card(existing, card_data)
                            result.updated += 1
                        elif mode == ConflictMode.MERGE:
                            self._merge_card(existing, card_data)
                            result.updated += 1
                    else:
                        card = self._create_card(card_data)
                        uow.cards.add(card)
                        result.created += 1

                except Exception as e:
                    result.errors.append(f"Card {card_data.get('iccid')}: {e}")

            uow.commit()

        return result

    def _import_settings(
        self,
        settings: List[Dict[str, Any]],
    ) -> ImportResult:
        """Import settings (always overwrites)."""
        result = ImportResult()

        with UnitOfWork(self._db_manager) as uow:
            for setting_data in settings:
                try:
                    key = setting_data.get("key")
                    if not key:
                        result.errors.append("Setting missing 'key' field")
                        continue

                    existing = uow.settings.get(key)

                    if existing:
                        existing.value = setting_data.get("value")
                        existing.category = setting_data.get("category", "general")
                        existing.description = setting_data.get("description")
                        result.updated += 1
                    else:
                        setting = Setting(
                            key=key,
                            value=setting_data.get("value"),
                            category=setting_data.get("category", "general"),
                            description=setting_data.get("description"),
                        )
                        uow.settings.add(setting)
                        result.created += 1

                except Exception as e:
                    result.errors.append(f"Setting {setting_data.get('key')}: {e}")

            uow.commit()

        return result

    def _create_device(self, data: Dict[str, Any]) -> Device:
        """Create device from dictionary."""
        return Device(
            id=data["id"],
            name=data.get("name"),
            device_type=DeviceType(data.get("device_type", "phone")),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            firmware_version=data.get("firmware_version"),
            imei=data.get("imei"),
            imsi=data.get("imsi"),
            iccid=data.get("iccid"),
            connection_settings=data.get("connection_settings"),
            is_active=data.get("is_active", True),
            notes=data.get("notes"),
        )

    def _update_device(self, device: Device, data: Dict[str, Any]) -> None:
        """Update device from dictionary (overwrite all fields)."""
        device.name = data.get("name")
        device.device_type = DeviceType(data.get("device_type", device.device_type.value))
        device.manufacturer = data.get("manufacturer")
        device.model = data.get("model")
        device.firmware_version = data.get("firmware_version")
        device.imei = data.get("imei")
        device.imsi = data.get("imsi")
        device.iccid = data.get("iccid")
        device.connection_settings = data.get("connection_settings")
        device.is_active = data.get("is_active", True)
        device.notes = data.get("notes")

    def _merge_device(self, device: Device, data: Dict[str, Any]) -> None:
        """Merge device data (only update non-None fields)."""
        if data.get("name") is not None:
            device.name = data["name"]
        if data.get("device_type") is not None:
            device.device_type = DeviceType(data["device_type"])
        if data.get("manufacturer") is not None:
            device.manufacturer = data["manufacturer"]
        if data.get("model") is not None:
            device.model = data["model"]
        if data.get("firmware_version") is not None:
            device.firmware_version = data["firmware_version"]
        if data.get("imei") is not None:
            device.imei = data["imei"]
        if data.get("imsi") is not None:
            device.imsi = data["imsi"]
        if data.get("iccid") is not None:
            device.iccid = data["iccid"]
        if data.get("connection_settings") is not None:
            device.connection_settings = data["connection_settings"]
        if data.get("is_active") is not None:
            device.is_active = data["is_active"]
        if data.get("notes") is not None:
            device.notes = data["notes"]

    def _create_card(self, data: Dict[str, Any]) -> CardProfile:
        """Create card profile from dictionary."""
        card = CardProfile(
            iccid=data["iccid"],
            imsi=data.get("imsi"),
            card_type=data.get("card_type", "UICC"),
            atr=data.get("atr"),
            psk_identity=data.get("psk_identity"),
            admin_url=data.get("admin_url"),
            trigger_config=data.get("trigger_config"),
            bip_config=data.get("bip_config"),
            security_domains=data.get("security_domains"),
            notes=data.get("notes"),
        )

        # Handle encrypted PSK key if present
        if data.get("psk_key_encrypted_b64"):
            import base64

            card.psk_key_encrypted = base64.b64decode(data["psk_key_encrypted_b64"])

        return card

    def _update_card(self, card: CardProfile, data: Dict[str, Any]) -> None:
        """Update card from dictionary."""
        card.imsi = data.get("imsi")
        card.card_type = data.get("card_type", "UICC")
        card.atr = data.get("atr")
        card.psk_identity = data.get("psk_identity")
        card.admin_url = data.get("admin_url")
        card.trigger_config = data.get("trigger_config")
        card.bip_config = data.get("bip_config")
        card.security_domains = data.get("security_domains")
        card.notes = data.get("notes")

        if data.get("psk_key_encrypted_b64"):
            import base64

            card.psk_key_encrypted = base64.b64decode(data["psk_key_encrypted_b64"])

    def _merge_card(self, card: CardProfile, data: Dict[str, Any]) -> None:
        """Merge card data (only update non-None fields)."""
        if data.get("imsi") is not None:
            card.imsi = data["imsi"]
        if data.get("card_type") is not None:
            card.card_type = data["card_type"]
        if data.get("atr") is not None:
            card.atr = data["atr"]
        if data.get("psk_identity") is not None:
            card.psk_identity = data["psk_identity"]
        if data.get("admin_url") is not None:
            card.admin_url = data["admin_url"]
        if data.get("trigger_config") is not None:
            card.trigger_config = data["trigger_config"]
        if data.get("bip_config") is not None:
            card.bip_config = data["bip_config"]
        if data.get("security_domains") is not None:
            card.security_domains = data["security_domains"]
        if data.get("notes") is not None:
            card.notes = data["notes"]

        if data.get("psk_key_encrypted_b64"):
            import base64

            card.psk_key_encrypted = base64.b64decode(data["psk_key_encrypted_b64"])
