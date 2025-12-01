"""Config Manager for network simulator integration.

This module provides centralized configuration management with
state tracking, file operations, and change notification.

Classes:
    ConfigManager: Manager for simulator configuration
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from cardlink.netsim.interface import SimulatorInterface

log = logging.getLogger(__name__)


class ConfigManager:
    """Manager for simulator configuration.

    Provides centralized configuration management with:
    - Configuration get/set operations
    - Local caching
    - File-based persistence (YAML)
    - Change event notification

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> config_manager = ConfigManager(adapter, event_emitter)
        >>> # Get current config
        >>> config = await config_manager.get()
        >>> print(config["cell"]["plmn"])
        >>> # Update config
        >>> await config_manager.set({"cell": {"plmn": "001-01"}})
        >>> # Save to file
        >>> config_manager.save_to_file("config.yaml")
    """

    def __init__(self, adapter: SimulatorInterface, event_emitter: Any) -> None:
        """Initialize Config Manager.

        Args:
            adapter: The simulator adapter for config operations.
            event_emitter: Event emitter for broadcasting config events.
        """
        self._adapter = adapter
        self._events = event_emitter

        # Cached configuration
        self._config_cache: Optional[dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 30.0  # Cache TTL in seconds

    # =========================================================================
    # Configuration Query Operations
    # =========================================================================

    async def get(self, refresh: bool = False) -> dict[str, Any]:
        """Get current simulator configuration.

        Args:
            refresh: If True, bypass cache and fetch fresh config.

        Returns:
            Configuration dictionary.
        """
        # Check cache validity
        if not refresh and self._is_cache_valid():
            return self._config_cache.copy()

        log.debug("Fetching configuration from simulator")

        config = await self._adapter.get_config()
        self._config_cache = config
        self._cache_time = datetime.utcnow()

        return config.copy()

    async def get_value(
        self,
        key: str,
        default: Any = None,
        refresh: bool = False,
    ) -> Any:
        """Get a specific configuration value.

        Args:
            key: Configuration key (dot-separated for nested, e.g., "cell.plmn").
            default: Default value if key not found.
            refresh: If True, bypass cache.

        Returns:
            Configuration value or default.
        """
        config = await self.get(refresh=refresh)

        # Handle dot-separated keys
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def get_cached(self) -> Optional[dict[str, Any]]:
        """Get cached configuration without fetching.

        Returns:
            Cached configuration or None if not cached.
        """
        return self._config_cache.copy() if self._config_cache else None

    def _is_cache_valid(self) -> bool:
        """Check if cache is valid."""
        if self._config_cache is None or self._cache_time is None:
            return False

        elapsed = (datetime.utcnow() - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl

    # =========================================================================
    # Configuration Update Operations
    # =========================================================================

    async def set(self, params: dict[str, Any]) -> bool:
        """Set configuration parameters.

        Args:
            params: Configuration parameters to set.

        Returns:
            True if configuration was applied successfully.

        Raises:
            CommandError: If configuration fails.
        """
        log.info(f"Setting configuration: {list(params.keys())}")

        # Apply configuration
        result = await self._adapter.set_config(params)

        if result:
            # Invalidate cache
            self._config_cache = None
            self._cache_time = None

            # Emit config changed event
            await self._events.emit("config_changed", {
                "params": params,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return result

    async def set_value(self, key: str, value: Any) -> bool:
        """Set a specific configuration value.

        Args:
            key: Configuration key (dot-separated for nested).
            value: Value to set.

        Returns:
            True if value was set successfully.
        """
        # Build nested dict from dot-separated key
        parts = key.split(".")
        params: dict[str, Any] = {}
        current = params

        for i, part in enumerate(parts[:-1]):
            current[part] = {}
            current = current[part]

        current[parts[-1]] = value

        return await self.set(params)

    async def reload(self) -> dict[str, Any]:
        """Reload configuration from simulator.

        Clears cache and fetches fresh configuration.

        Returns:
            Fresh configuration dictionary.
        """
        log.debug("Reloading configuration")
        self._config_cache = None
        self._cache_time = None
        return await self.get(refresh=True)

    # =========================================================================
    # File Operations
    # =========================================================================

    async def load_from_file(self, file_path: str) -> bool:
        """Load and apply configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file.

        Returns:
            True if configuration was loaded and applied successfully.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If YAML is invalid.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        log.info(f"Loading configuration from {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Apply configuration
        return await self.set(config)

    def save_to_file(
        self,
        file_path: str,
        include_defaults: bool = True,
    ) -> None:
        """Save current configuration to YAML file.

        Args:
            file_path: Path to save configuration.
            include_defaults: If True, include all values (including defaults).

        Raises:
            ValueError: If no configuration is cached.
        """
        if self._config_cache is None:
            raise ValueError("No configuration cached. Call get() first.")

        path = Path(file_path)
        log.info(f"Saving configuration to {file_path}")

        # Prepare config for saving
        config = self._config_cache.copy()

        # Add metadata
        config["_metadata"] = {
            "saved_at": datetime.utcnow().isoformat(),
            "source": "network_simulator",
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def validate_file(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Validate a configuration file.

        Args:
            file_path: Path to YAML configuration file.

        Returns:
            Tuple of (is_valid, error_message).
        """
        path = Path(file_path)

        if not path.exists():
            return False, f"File not found: {file_path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {e}"

        if not isinstance(config, dict):
            return False, "Configuration must be a dictionary"

        # Basic structure validation
        return True, None

    # =========================================================================
    # Configuration Templates
    # =========================================================================

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration template.

        Returns:
            Default configuration dictionary.
        """
        return {
            "cell": {
                "plmn": "001-01",
                "frequency": 1950,
                "bandwidth": 20,
                "tx_power": 23,
            },
            "network": {
                "apn": "internet",
                "dns1": "8.8.8.8",
                "dns2": "8.8.4.4",
            },
            "security": {
                "authentication": "EPS-AKA",
                "encryption": "EEA1",
                "integrity": "EIA1",
            },
        }

    def merge_config(
        self,
        base: dict[str, Any],
        overlay: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge two configurations.

        Args:
            base: Base configuration.
            overlay: Configuration to overlay on base.

        Returns:
            Merged configuration.
        """
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value

        return result
