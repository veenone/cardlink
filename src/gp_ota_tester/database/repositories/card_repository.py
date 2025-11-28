"""Card profile repository for GP OTA Tester.

This module provides the repository for card profile CRUD operations
with PSK key encryption support.

Example:
    >>> from gp_ota_tester.database.repositories import CardRepository
    >>> with UnitOfWork(manager) as uow:
    ...     profile = uow.cards.get("89012345678901234567")
    ...     psk_key = uow.cards.get_decrypted_psk(profile, encryption_key)
"""

import logging
import os
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from gp_ota_tester.database.exceptions import EncryptionError
from gp_ota_tester.database.models import CardProfile
from gp_ota_tester.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CardRepository(BaseRepository[CardProfile]):
    """Repository for card profile operations.

    Provides CRUD operations and card-specific queries with
    support for PSK key encryption/decryption.

    Example:
        >>> repo = CardRepository(session)
        >>> profiles = repo.find_with_psk()
        >>> repo.set_encrypted_psk(profile, psk_key, encryption_key)
    """

    def __init__(self, session: Session) -> None:
        """Initialize card repository.

        Args:
            session: SQLAlchemy session.
        """
        super().__init__(session, CardProfile)

    def find_by_imsi(self, imsi: str) -> Optional[CardProfile]:
        """Find card profile by IMSI.

        Args:
            imsi: IMSI to search for.

        Returns:
            CardProfile if found, None otherwise.
        """
        stmt = select(CardProfile).where(CardProfile.imsi == imsi)
        result = self._session.execute(stmt)
        return result.scalar_one_or_none()

    def find_by_psk_identity(self, identity: str) -> Optional[CardProfile]:
        """Find card profile by PSK identity.

        Args:
            identity: PSK identity string.

        Returns:
            CardProfile if found, None otherwise.
        """
        stmt = select(CardProfile).where(CardProfile.psk_identity == identity)
        result = self._session.execute(stmt)
        return result.scalar_one_or_none()

    def find_by_card_type(self, card_type: str) -> List[CardProfile]:
        """Find card profiles by card type.

        Args:
            card_type: Card type (UICC, USIM, eUICC, ISIM).

        Returns:
            List of matching profiles.
        """
        stmt = select(CardProfile).where(CardProfile.card_type == card_type)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_with_psk(self) -> List[CardProfile]:
        """Find all card profiles with PSK configured.

        Returns:
            List of profiles with PSK identity and key.
        """
        stmt = select(CardProfile).where(
            CardProfile.psk_identity.isnot(None),
            CardProfile.psk_key_encrypted.isnot(None),
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def find_without_psk(self) -> List[CardProfile]:
        """Find card profiles without PSK configured.

        Returns:
            List of profiles missing PSK configuration.
        """
        stmt = select(CardProfile).where(
            or_(
                CardProfile.psk_identity.is_(None),
                CardProfile.psk_key_encrypted.is_(None),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def search(self, query: str) -> List[CardProfile]:
        """Search card profiles by ICCID, IMSI, or PSK identity.

        Args:
            query: Search string.

        Returns:
            List of matching profiles.
        """
        pattern = f"%{query}%"
        stmt = select(CardProfile).where(
            or_(
                CardProfile.iccid.ilike(pattern),
                CardProfile.imsi.ilike(pattern),
                CardProfile.psk_identity.ilike(pattern),
            )
        )
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def get_psk_identities(self) -> List[str]:
        """Get all PSK identities.

        Returns:
            List of PSK identity strings.
        """
        stmt = select(CardProfile.psk_identity).where(
            CardProfile.psk_identity.isnot(None)
        )
        result = self._session.execute(stmt)
        return [row[0] for row in result.all()]

    # =========================================================================
    # PSK Encryption/Decryption
    # =========================================================================

    def set_encrypted_psk(
        self,
        profile: CardProfile,
        psk_key: bytes,
        encryption_key: bytes,
    ) -> None:
        """Set encrypted PSK key on profile.

        Args:
            profile: Card profile to update.
            psk_key: Raw PSK key bytes.
            encryption_key: Fernet encryption key.

        Raises:
            EncryptionError: If encryption fails.
        """
        try:
            from cryptography.fernet import Fernet

            fernet = Fernet(encryption_key)
            profile.psk_key_encrypted = fernet.encrypt(psk_key)
            logger.debug("PSK key encrypted for ICCID: %s", profile.short_iccid)
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt PSK key: {e}") from e

    def get_decrypted_psk(
        self,
        profile: CardProfile,
        encryption_key: bytes,
    ) -> Optional[bytes]:
        """Get decrypted PSK key from profile.

        Args:
            profile: Card profile with encrypted PSK.
            encryption_key: Fernet encryption key.

        Returns:
            Decrypted PSK key bytes, or None if not set.

        Raises:
            EncryptionError: If decryption fails.
        """
        if profile.psk_key_encrypted is None:
            return None

        try:
            from cryptography.fernet import Fernet

            fernet = Fernet(encryption_key)
            return fernet.decrypt(profile.psk_key_encrypted)
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt PSK key: {e}") from e

    def clear_psk(self, profile: CardProfile) -> None:
        """Clear PSK credentials from profile.

        Args:
            profile: Card profile to clear.
        """
        profile.psk_identity = None
        profile.psk_key_encrypted = None
        logger.debug("PSK cleared for ICCID: %s", profile.short_iccid)

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generate a new Fernet encryption key.

        Returns:
            New encryption key bytes.
        """
        from cryptography.fernet import Fernet

        return Fernet.generate_key()

    def get_stats(self) -> dict:
        """Get card profile statistics.

        Returns:
            Dictionary with profile counts.
        """
        return {
            "total": self.count(),
            "with_psk": len(self.find_with_psk()),
            "without_psk": len(self.find_without_psk()),
            "uicc": self.count_by(card_type="UICC"),
            "usim": self.count_by(card_type="USIM"),
            "euicc": self.count_by(card_type="eUICC"),
        }
