"""Profile Manager for device profile persistence.

This module provides the ProfileManager class for saving, loading,
and managing device profiles to/from the filesystem.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gp_ota_tester.phone.exceptions import (
    ProfileError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileSaveError,
)
from gp_ota_tester.phone.models import (
    DataConnectionState,
    DeviceProfile,
    FullProfile,
    NetworkProfile,
    NetworkType,
    SIMProfile,
    SIMStatus,
)

logger = logging.getLogger(__name__)


# Default storage directory
DEFAULT_PROFILE_DIR = Path.home() / ".cardlink" / "profiles"


class ProfileManager:
    """Manager for device profile persistence.

    This class handles saving, loading, listing, and comparing
    device profiles stored as JSON files.

    Features:
    - Save profiles to ~/.cardlink/profiles/
    - Load profiles with automatic deserialization
    - List all saved profiles
    - Compare profiles to detect changes
    - Export/import profiles in various formats

    Args:
        storage_path: Custom path for profile storage.
                     Defaults to ~/.cardlink/profiles/

    Example:
        ```python
        manager = ProfileManager()

        # Save a profile
        await manager.save_profile("my_device", full_profile)

        # Load a profile
        profile = await manager.load_profile("my_device")

        # List profiles
        profiles = manager.list_profiles()

        # Compare profiles
        diff = manager.compare(profile1, profile2)
        ```
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
    ):
        """Initialize profile manager.

        Args:
            storage_path: Custom storage directory path.
        """
        self._storage_path = storage_path or DEFAULT_PROFILE_DIR
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

    @property
    def storage_path(self) -> Path:
        """Get the storage directory path."""
        return self._storage_path

    def _profile_path(self, name: str) -> Path:
        """Get the file path for a profile name.

        Args:
            name: Profile name.

        Returns:
            Full path to the profile file.
        """
        # Sanitize name to prevent directory traversal
        safe_name = "".join(c for c in name if c.isalnum() or c in "._-")
        if not safe_name:
            safe_name = "profile"
        return self._storage_path / f"{safe_name}.json"

    async def save_profile(
        self,
        name: str,
        profile: FullProfile,
        overwrite: bool = True,
    ) -> Path:
        """Save a device profile to storage.

        Args:
            name: Profile name/identifier.
            profile: FullProfile to save.
            overwrite: Whether to overwrite existing profile.

        Returns:
            Path to the saved profile file.

        Raises:
            ProfileSaveError: If saving fails.
        """
        path = self._profile_path(name)

        if path.exists() and not overwrite:
            raise ProfileSaveError(name, "Profile already exists")

        try:
            # Convert to dict and add metadata
            data = profile.to_dict()
            data["_meta"] = {
                "name": name,
                "saved_at": datetime.now().isoformat(),
                "version": "1.0",
            }

            # Write to file (using sync I/O for simplicity, can use aiofiles if needed)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved profile '{name}' to {path}")
            return path

        except Exception as e:
            raise ProfileSaveError(name, str(e))

    async def load_profile(self, name: str) -> FullProfile:
        """Load a device profile from storage.

        Args:
            name: Profile name/identifier.

        Returns:
            Loaded FullProfile.

        Raises:
            ProfileNotFoundError: If profile doesn't exist.
            ProfileLoadError: If loading fails.
        """
        path = self._profile_path(name)

        if not path.exists():
            raise ProfileNotFoundError(name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self._dict_to_profile(data)

        except ProfileNotFoundError:
            raise
        except json.JSONDecodeError as e:
            raise ProfileLoadError(name, f"Invalid JSON: {e}")
        except Exception as e:
            raise ProfileLoadError(name, str(e))

    def _dict_to_profile(self, data: Dict[str, Any]) -> FullProfile:
        """Convert a dictionary to a FullProfile.

        Args:
            data: Dictionary data from JSON.

        Returns:
            FullProfile instance.
        """
        # Parse device profile
        device_data = data.get("device", {})
        device = DeviceProfile(
            serial=device_data.get("serial", ""),
            model=device_data.get("model", ""),
            manufacturer=device_data.get("manufacturer", ""),
            brand=device_data.get("brand", ""),
            device=device_data.get("device", ""),
            product=device_data.get("product", ""),
            android_version=device_data.get("android_version", ""),
            api_level=device_data.get("api_level", 0),
            build_number=device_data.get("build_number", ""),
            build_fingerprint=device_data.get("build_fingerprint", ""),
            kernel_version=device_data.get("kernel_version", ""),
            baseband_version=device_data.get("baseband_version", ""),
            security_patch=device_data.get("security_patch", ""),
            imei=device_data.get("imei", ""),
            imei2=device_data.get("imei2", ""),
            hardware=device_data.get("hardware", ""),
            board=device_data.get("board", ""),
            abi=device_data.get("abi", ""),
            timestamp=self._parse_timestamp(device_data.get("timestamp")),
        )

        # Parse SIM profiles
        sim_profiles = []
        for sim_data in data.get("sim_profiles", []):
            sim = SIMProfile(
                slot=sim_data.get("slot", 0),
                status=self._parse_enum(SIMStatus, sim_data.get("status")),
                iccid=sim_data.get("iccid", ""),
                imsi=sim_data.get("imsi", ""),
                msisdn=sim_data.get("msisdn", ""),
                spn=sim_data.get("spn", ""),
                mcc=sim_data.get("mcc", ""),
                mnc=sim_data.get("mnc", ""),
                operator_name=sim_data.get("operator_name", ""),
                is_embedded=sim_data.get("is_embedded", False),
                is_active=sim_data.get("is_active", False),
                timestamp=self._parse_timestamp(sim_data.get("timestamp")),
            )
            sim_profiles.append(sim)

        # Parse network profile
        network = None
        network_data = data.get("network")
        if network_data:
            network = NetworkProfile(
                operator_name=network_data.get("operator_name", ""),
                network_type=self._parse_enum(
                    NetworkType, network_data.get("network_type")
                ),
                data_state=self._parse_enum(
                    DataConnectionState, network_data.get("data_state")
                ),
                data_roaming=network_data.get("data_roaming", False),
                signal_strength_dbm=network_data.get("signal_strength_dbm", -999),
                signal_level=network_data.get("signal_level", 0),
                is_wifi_connected=network_data.get("is_wifi_connected", False),
                wifi_ssid=network_data.get("wifi_ssid", ""),
                wifi_ip=network_data.get("wifi_ip", ""),
                mobile_ip=network_data.get("mobile_ip", ""),
                apn_name=network_data.get("apn_name", ""),
                apn_type=network_data.get("apn_type", ""),
                mcc=network_data.get("mcc", ""),
                mnc=network_data.get("mnc", ""),
                cell_id=network_data.get("cell_id", ""),
                lac=network_data.get("lac", ""),
                timestamp=self._parse_timestamp(network_data.get("timestamp")),
            )

        # Create FullProfile
        return FullProfile(
            device=device,
            sim_profiles=sim_profiles,
            network=network,
            timestamp=self._parse_timestamp(data.get("timestamp")),
        )

    def _parse_timestamp(self, value: Optional[str]) -> datetime:
        """Parse an ISO timestamp string.

        Args:
            value: ISO timestamp string or None.

        Returns:
            datetime object.
        """
        if value is None:
            return datetime.now()
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now()

    def _parse_enum(self, enum_class, value: Optional[str]):
        """Parse an enum value.

        Args:
            enum_class: The enum class.
            value: String value or None.

        Returns:
            Enum member or default (UNKNOWN).
        """
        if value is None:
            return enum_class.UNKNOWN
        try:
            return enum_class(value)
        except ValueError:
            return enum_class.UNKNOWN

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all saved profiles.

        Returns:
            List of profile metadata dictionaries.
        """
        profiles = []

        for path in self._storage_path.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("_meta", {})
                device = data.get("device", {})

                profiles.append(
                    {
                        "name": meta.get("name", path.stem),
                        "file": path.name,
                        "serial": device.get("serial", ""),
                        "model": device.get("model", ""),
                        "saved_at": meta.get("saved_at", ""),
                        "path": str(path),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read profile {path}: {e}")

        return sorted(profiles, key=lambda p: p.get("name", ""))

    def delete_profile(self, name: str) -> bool:
        """Delete a saved profile.

        Args:
            name: Profile name.

        Returns:
            True if deleted, False if not found.
        """
        path = self._profile_path(name)

        if not path.exists():
            return False

        try:
            path.unlink()
            logger.info(f"Deleted profile '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile '{name}': {e}")
            return False

    def profile_exists(self, name: str) -> bool:
        """Check if a profile exists.

        Args:
            name: Profile name.

        Returns:
            True if profile exists.
        """
        return self._profile_path(name).exists()

    async def export_profile(
        self,
        name: str,
        format: str = "json",
    ) -> str:
        """Export a profile to a specific format.

        Args:
            name: Profile name.
            format: Export format ("json", "yaml", "summary").

        Returns:
            Exported string data.

        Raises:
            ProfileNotFoundError: If profile doesn't exist.
        """
        profile = await self.load_profile(name)

        if format == "json":
            return profile.to_json()

        elif format == "yaml":
            # Simple YAML-like output (no dependency on PyYAML)
            return self._to_yaml_like(profile.to_dict())

        elif format == "summary":
            return self._format_summary(profile)

        else:
            raise ProfileError(f"Unknown export format: {format}")

    def _to_yaml_like(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Convert dict to YAML-like string.

        Args:
            data: Dictionary to convert.
            indent: Current indentation level.

        Returns:
            YAML-like formatted string.
        """
        lines = []
        prefix = "  " * indent

        for key, value in data.items():
            if key.startswith("_"):
                continue

            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._to_yaml_like(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  - # item {i}")
                        lines.append(self._to_yaml_like(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")

        return "\n".join(lines)

    def _format_summary(self, profile: FullProfile) -> str:
        """Format profile as human-readable summary.

        Args:
            profile: Profile to format.

        Returns:
            Summary string.
        """
        lines = [
            "=== Device Profile Summary ===",
            "",
            f"Serial:       {profile.device.serial}",
            f"Model:        {profile.device.manufacturer} {profile.device.model}",
            f"Android:      {profile.device.android_version} (API {profile.device.api_level})",
            f"Build:        {profile.device.build_number}",
            f"IMEI:         {profile.device.imei or 'N/A'}",
            "",
        ]

        if profile.sim_profiles:
            lines.append("=== SIM Information ===")
            lines.append("")
            for sim in profile.sim_profiles:
                lines.extend(
                    [
                        f"Slot {sim.slot}:",
                        f"  Status:     {sim.status.value}",
                        f"  ICCID:      {sim.iccid or 'N/A'}",
                        f"  IMSI:       {sim.imsi or 'N/A'}",
                        f"  Operator:   {sim.operator_name or 'N/A'}",
                        "",
                    ]
                )

        if profile.network:
            lines.extend(
                [
                    "=== Network Status ===",
                    "",
                    f"Operator:     {profile.network.operator_name}",
                    f"Type:         {profile.network.network_type.value}",
                    f"Data State:   {profile.network.data_state.value}",
                    f"Signal:       {profile.network.signal_strength_dbm} dBm",
                    f"WiFi:         {'Connected' if profile.network.is_wifi_connected else 'Disconnected'}",
                    "",
                ]
            )

        lines.append(f"Captured:     {profile.timestamp.isoformat()}")

        return "\n".join(lines)

    async def import_profile(
        self,
        name: str,
        data: str,
        format: str = "json",
    ) -> FullProfile:
        """Import a profile from string data.

        Args:
            name: Name to save the profile as.
            data: Profile data string.
            format: Data format ("json").

        Returns:
            Imported FullProfile.

        Raises:
            ProfileError: If import fails.
        """
        if format != "json":
            raise ProfileError(f"Import only supports JSON format, got: {format}")

        try:
            parsed = json.loads(data)
            profile = self._dict_to_profile(parsed)
            await self.save_profile(name, profile)
            return profile
        except json.JSONDecodeError as e:
            raise ProfileError(f"Invalid JSON data: {e}")
        except Exception as e:
            raise ProfileError(f"Import failed: {e}")

    @staticmethod
    def compare(
        profile1: FullProfile,
        profile2: FullProfile,
    ) -> Dict[str, Any]:
        """Compare two profiles and identify differences.

        Args:
            profile1: First profile.
            profile2: Second profile.

        Returns:
            Dictionary of differences.
        """
        differences = {
            "device": {},
            "sim": [],
            "network": {},
        }

        # Compare device info
        d1 = profile1.device.to_dict()
        d2 = profile2.device.to_dict()

        for key in d1:
            if key == "timestamp":
                continue
            if d1.get(key) != d2.get(key):
                differences["device"][key] = {
                    "old": d1.get(key),
                    "new": d2.get(key),
                }

        # Compare SIM profiles
        for i, (sim1, sim2) in enumerate(
            zip(profile1.sim_profiles, profile2.sim_profiles)
        ):
            s1 = sim1.to_dict()
            s2 = sim2.to_dict()
            sim_diff = {}

            for key in s1:
                if key == "timestamp":
                    continue
                if s1.get(key) != s2.get(key):
                    sim_diff[key] = {
                        "old": s1.get(key),
                        "new": s2.get(key),
                    }

            if sim_diff:
                differences["sim"].append({"slot": i, "changes": sim_diff})

        # Compare network info
        if profile1.network and profile2.network:
            n1 = profile1.network.to_dict()
            n2 = profile2.network.to_dict()

            for key in n1:
                if key == "timestamp":
                    continue
                if n1.get(key) != n2.get(key):
                    differences["network"][key] = {
                        "old": n1.get(key),
                        "new": n2.get(key),
                    }

        # Remove empty sections
        return {k: v for k, v in differences.items() if v}

    def get_profile_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a profile without loading it.

        Args:
            name: Profile name.

        Returns:
            Profile metadata dictionary or None.
        """
        path = self._profile_path(name)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            meta = data.get("_meta", {})
            device = data.get("device", {})

            return {
                "name": meta.get("name", name),
                "serial": device.get("serial", ""),
                "model": device.get("model", ""),
                "manufacturer": device.get("manufacturer", ""),
                "android_version": device.get("android_version", ""),
                "saved_at": meta.get("saved_at", ""),
                "file_size": path.stat().st_size,
                "path": str(path),
            }
        except Exception:
            return None
