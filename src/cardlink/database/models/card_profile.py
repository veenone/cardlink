"""Card profile model for GP OTA Tester.

This module defines the CardProfile model for storing UICC card
profiles with PSK credentials and configuration.

Example:
    >>> from cardlink.database.models import CardProfile
    >>> profile = CardProfile(
    ...     iccid="89012345678901234567",
    ...     psk_identity="test_card_001",
    ... )
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Index, LargeBinary, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cardlink.database.models.base import Base, TimestampMixin
from cardlink.database.models.enums import CardType

if TYPE_CHECKING:
    from cardlink.database.models.session import OTASession
    from cardlink.database.models.test_result import TestResult


class CardProfile(Base, TimestampMixin):
    """UICC card profile model.

    Stores card profile information including PSK credentials,
    server configuration, and BIP/trigger settings.

    The PSK key is stored encrypted using Fernet encryption.
    Use the encryption utilities to encrypt/decrypt keys.

    Attributes:
        iccid: Integrated Circuit Card Identifier (primary key).
        imsi: International Mobile Subscriber Identity.
        card_type: Type of card (UICC, USIM, eUICC, ISIM).
        atr: Answer To Reset (hex encoded).
        psk_identity: PSK identity string for TLS authentication.
        psk_key_encrypted: Encrypted PSK key (Fernet).
        admin_url: OTA admin server URL.
        trigger_config: SMS/CAT trigger configuration.
        bip_config: Bearer Independent Protocol configuration.
        security_domains: Security domain information.
        notes: Additional notes.

    Relationships:
        sessions: OTA sessions using this card.
        test_results: Test results for this card.

    Example:
        >>> profile = CardProfile(iccid="89012345678901234567")
        >>> profile.set_trigger_config({"type": "sms", "port": 2948})
    """

    __tablename__ = "card_profiles"

    # Primary key - ICCID
    iccid: Mapped[str] = mapped_column(
        String(22),
        primary_key=True,
        doc="Integrated Circuit Card Identifier",
    )

    # Card information
    imsi: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="International Mobile Subscriber Identity",
    )

    card_type: Mapped[str] = mapped_column(
        String(20),
        default=CardType.UICC.value,
        nullable=False,
        doc="Type of card (UICC, USIM, eUICC, ISIM)",
    )

    atr: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Answer To Reset (hex encoded)",
    )

    # PSK configuration
    psk_identity: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="PSK identity string for TLS-PSK authentication",
    )

    psk_key_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        nullable=True,
        doc="Encrypted PSK key (Fernet encryption)",
    )

    # Server configuration
    admin_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="OTA admin server URL",
    )

    # Trigger configuration (JSON)
    trigger_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="SMS/CAT trigger configuration",
    )

    # BIP configuration (JSON)
    bip_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Bearer Independent Protocol configuration",
    )

    # Security Domain info (JSON)
    security_domains: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Security domain information",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Additional notes about the card",
    )

    # Relationships
    sessions: Mapped[List["OTASession"]] = relationship(
        "OTASession",
        back_populates="card",
        lazy="dynamic",
    )

    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="card",
        lazy="dynamic",
    )

    # Table configuration
    __table_args__ = (
        Index("idx_card_type", "card_type"),
        Index("idx_card_psk_identity", "psk_identity"),
        Index("idx_card_imsi", "imsi"),
    )

    @property
    def has_psk(self) -> bool:
        """Check if PSK credentials are configured."""
        return self.psk_identity is not None and self.psk_key_encrypted is not None

    @property
    def short_iccid(self) -> str:
        """Get shortened ICCID for display (last 8 digits)."""
        if len(self.iccid) >= 8:
            return f"...{self.iccid[-8:]}"
        return self.iccid

    def set_trigger_config(
        self,
        trigger_type: str = "sms",
        **kwargs: Any,
    ) -> None:
        """Set trigger configuration.

        Args:
            trigger_type: Type of trigger ("sms" or "cat").
            **kwargs: Additional trigger parameters.
        """
        self.trigger_config = {
            "type": trigger_type,
            **kwargs,
        }

    def set_bip_config(
        self,
        channel: int = 1,
        buffer_size: int = 1500,
        **kwargs: Any,
    ) -> None:
        """Set BIP configuration.

        Args:
            channel: BIP channel number.
            buffer_size: Buffer size for BIP.
            **kwargs: Additional BIP parameters.
        """
        self.bip_config = {
            "channel": channel,
            "buffer_size": buffer_size,
            **kwargs,
        }

    def add_security_domain(
        self,
        aid: str,
        name: Optional[str] = None,
        privileges: Optional[List[str]] = None,
    ) -> None:
        """Add a security domain.

        Args:
            aid: Application Identifier (hex).
            name: Security domain name.
            privileges: List of privileges.
        """
        if self.security_domains is None:
            self.security_domains = {"domains": []}

        domain = {
            "aid": aid,
            "name": name,
            "privileges": privileges or [],
        }

        if "domains" not in self.security_domains:
            self.security_domains["domains"] = []

        self.security_domains["domains"].append(domain)

    def get_trigger_type(self) -> Optional[str]:
        """Get trigger type from configuration.

        Returns:
            Trigger type or None if not configured.
        """
        if self.trigger_config is None:
            return None
        return self.trigger_config.get("type")
