"""PSK Key Store implementations.

This module provides abstract and concrete implementations for PSK key storage,
including file-based (YAML) and database-backed key stores.

Security Note:
    PSK keys are sensitive cryptographic material. This module ensures that
    key values are NEVER logged in plaintext. Only PSK identities may be logged.

Example:
    >>> from gp_ota_tester.server.key_store import FileKeyStore
    >>> key_store = FileKeyStore("keys.yaml")
    >>> key = key_store.get_key("card_001")
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class KeyStore(ABC):
    """Abstract base class for PSK key storage.

    Implementations must provide methods to retrieve PSK keys by identity
    and check for identity existence.

    Security:
        Implementations MUST NOT log key values. Only identities may be logged.

    Example:
        >>> class MyKeyStore(KeyStore):
        ...     def get_key(self, identity: str) -> Optional[bytes]:
        ...         # Implementation here
        ...         pass
        ...     def identity_exists(self, identity: str) -> bool:
        ...         # Implementation here
        ...         pass
    """

    @abstractmethod
    def get_key(self, identity: str) -> Optional[bytes]:
        """Retrieve PSK key for the given identity.

        Args:
            identity: The PSK identity string.

        Returns:
            The PSK key as bytes, or None if identity is not found.

        Security:
            The returned key value MUST NOT be logged.
        """
        pass

    @abstractmethod
    def identity_exists(self, identity: str) -> bool:
        """Check if a PSK identity exists in the store.

        Args:
            identity: The PSK identity string to check.

        Returns:
            True if the identity exists, False otherwise.
        """
        pass

    def get_all_identities(self) -> list[str]:
        """Get list of all PSK identities in the store.

        Returns:
            List of identity strings. Default implementation returns empty list.
        """
        return []


class FileKeyStore(KeyStore):
    """File-based PSK key store using YAML format.

    Loads PSK keys from a YAML file with the following format:

    ```yaml
    keys:
      card_001: "0123456789ABCDEF0123456789ABCDEF"
      card_002: "FEDCBA9876543210FEDCBA9876543210"
    ```

    Keys are expected to be hex-encoded strings.

    Attributes:
        path: Path to the YAML key file.

    Example:
        >>> key_store = FileKeyStore("/path/to/keys.yaml")
        >>> key = key_store.get_key("card_001")
        >>> if key:
        ...     print(f"Found key for card_001 ({len(key)} bytes)")
    """

    def __init__(self, path: str) -> None:
        """Initialize FileKeyStore.

        Args:
            path: Path to the YAML key file.

        Raises:
            FileNotFoundError: If the key file does not exist.
            ValueError: If the key file is malformed.
        """
        self.path = Path(path)
        self._keys: Dict[str, bytes] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from YAML file.

        Raises:
            FileNotFoundError: If the key file does not exist.
            ValueError: If the key file is malformed or contains invalid keys.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Key store file not found: {self.path}")

        try:
            with open(self.path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in key store file: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Key store file must contain a YAML dictionary")

        keys_section = data.get("keys", data)
        if not isinstance(keys_section, dict):
            raise ValueError("Key store must have a 'keys' section with key-value pairs")

        for identity, key_hex in keys_section.items():
            if not isinstance(identity, str):
                raise ValueError(f"Key identity must be a string, got: {type(identity)}")

            if not isinstance(key_hex, str):
                raise ValueError(f"Key value for '{identity}' must be a hex string")

            try:
                key_bytes = bytes.fromhex(key_hex)
            except ValueError as e:
                raise ValueError(f"Invalid hex key for identity '{identity}': {e}") from e

            if len(key_bytes) < 16:
                logger.warning(
                    "PSK key for identity '%s' is less than 16 bytes (128 bits)", identity
                )

            self._keys[identity] = key_bytes

        # Log loaded identities (NEVER log key values)
        logger.info(
            "Loaded %d PSK identities from %s: %s",
            len(self._keys),
            self.path,
            list(self._keys.keys()),
        )

    def get_key(self, identity: str) -> Optional[bytes]:
        """Retrieve PSK key for the given identity.

        Args:
            identity: The PSK identity string.

        Returns:
            The PSK key as bytes, or None if identity is not found.
        """
        key = self._keys.get(identity)
        if key is None:
            logger.debug("PSK identity not found: %s", identity)
        else:
            # Log that we found the key, but NEVER log the key value
            logger.debug("PSK identity found: %s", identity)
        return key

    def identity_exists(self, identity: str) -> bool:
        """Check if a PSK identity exists in the store.

        Args:
            identity: The PSK identity string to check.

        Returns:
            True if the identity exists, False otherwise.
        """
        return identity in self._keys

    def get_all_identities(self) -> list[str]:
        """Get list of all PSK identities in the store.

        Returns:
            List of identity strings.
        """
        return list(self._keys.keys())

    def reload(self) -> None:
        """Reload keys from the file.

        Useful for picking up changes without restarting the server.
        """
        self._keys.clear()
        self._load_keys()
        logger.info("Reloaded key store from %s", self.path)


class MemoryKeyStore(KeyStore):
    """In-memory PSK key store for testing.

    Stores keys in memory without persistence. Useful for unit tests
    and development scenarios.

    Example:
        >>> key_store = MemoryKeyStore()
        >>> key_store.add_key("test_card", bytes.fromhex("0123456789ABCDEF"))
        >>> key = key_store.get_key("test_card")
    """

    def __init__(self) -> None:
        """Initialize empty in-memory key store."""
        self._keys: Dict[str, bytes] = {}

    def add_key(self, identity: str, key: bytes) -> None:
        """Add a PSK key to the store.

        Args:
            identity: The PSK identity string.
            key: The PSK key as bytes.
        """
        self._keys[identity] = key
        logger.debug("Added PSK identity to memory store: %s", identity)

    def remove_key(self, identity: str) -> bool:
        """Remove a PSK key from the store.

        Args:
            identity: The PSK identity string.

        Returns:
            True if the key was removed, False if it didn't exist.
        """
        if identity in self._keys:
            del self._keys[identity]
            logger.debug("Removed PSK identity from memory store: %s", identity)
            return True
        return False

    def get_key(self, identity: str) -> Optional[bytes]:
        """Retrieve PSK key for the given identity.

        Args:
            identity: The PSK identity string.

        Returns:
            The PSK key as bytes, or None if identity is not found.
        """
        return self._keys.get(identity)

    def identity_exists(self, identity: str) -> bool:
        """Check if a PSK identity exists in the store.

        Args:
            identity: The PSK identity string to check.

        Returns:
            True if the identity exists, False otherwise.
        """
        return identity in self._keys

    def get_all_identities(self) -> list[str]:
        """Get list of all PSK identities in the store.

        Returns:
            List of identity strings.
        """
        return list(self._keys.keys())

    def clear(self) -> None:
        """Remove all keys from the store."""
        self._keys.clear()
        logger.debug("Cleared all keys from memory store")


class DatabaseKeyStore(KeyStore):
    """Database-backed PSK key store.

    Retrieves PSK keys from the CardProfile table via the CardRepository.
    This integrates with the database layer for persistent key storage.

    Note:
        This class requires the database layer to be available.
        Import errors are handled gracefully for environments without database support.

    Attributes:
        card_repository: CardRepository instance for database access.

    Example:
        >>> from gp_ota_tester.database import CardRepository
        >>> repo = CardRepository(session)
        >>> key_store = DatabaseKeyStore(repo)
        >>> key = key_store.get_key("card_001")
    """

    def __init__(self, card_repository: "CardRepository") -> None:  # type: ignore[name-defined]
        """Initialize DatabaseKeyStore.

        Args:
            card_repository: CardRepository instance for database access.
        """
        self._repository = card_repository
        logger.info("Initialized database-backed key store")

    def get_key(self, identity: str) -> Optional[bytes]:
        """Retrieve PSK key for the given identity from database.

        Args:
            identity: The PSK identity string.

        Returns:
            The PSK key as bytes, or None if identity is not found.
        """
        try:
            # Query card profile by PSK identity
            key = self._repository.get_psk_key_by_identity(identity)
            if key is None:
                logger.debug("PSK identity not found in database: %s", identity)
            else:
                logger.debug("PSK identity found in database: %s", identity)
            return key
        except Exception as e:
            logger.error("Database error retrieving PSK for '%s': %s", identity, e)
            return None

    def identity_exists(self, identity: str) -> bool:
        """Check if a PSK identity exists in the database.

        Args:
            identity: The PSK identity string to check.

        Returns:
            True if the identity exists, False otherwise.
        """
        try:
            return self._repository.psk_identity_exists(identity)
        except Exception as e:
            logger.error("Database error checking identity '%s': %s", identity, e)
            return False

    def get_all_identities(self) -> list[str]:
        """Get list of all PSK identities in the database.

        Returns:
            List of identity strings.
        """
        try:
            return self._repository.get_all_psk_identities()
        except Exception as e:
            logger.error("Database error listing identities: %s", e)
            return []
