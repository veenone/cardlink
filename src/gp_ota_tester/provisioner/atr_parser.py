"""ATR (Answer-To-Reset) Parser for smart cards.

This module provides parsing and analysis of ATR bytes according to
ISO 7816-3 specification.
"""

import logging
from typing import List, Optional, Tuple, Union

from gp_ota_tester.provisioner.exceptions import ATRError
from gp_ota_tester.provisioner.models import ATRInfo, CardType, Convention, Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# Known ATR Patterns for Card Type Detection
# =============================================================================

# Format: (pattern_bytes, mask_bytes, card_type, description)
KNOWN_ATR_PATTERNS: List[Tuple[bytes, bytes, CardType, str]] = [
    # UICC/USIM patterns
    (
        bytes.fromhex("3B9F96801FC78031E073FE211B"),
        bytes.fromhex("FFFFFFFFFFFF00FFFFFFFFFFFFFF"),
        CardType.USIM,
        "Generic USIM",
    ),
    (
        bytes.fromhex("3B9E96801FC78031E073FE211B"),
        bytes.fromhex("FFFFFFFFFFFF00FFFFFFFFFFFFFF"),
        CardType.USIM,
        "Generic USIM variant",
    ),
    (
        bytes.fromhex("3B9F95801F"),
        bytes.fromhex("FFFFFFFFFF"),
        CardType.UICC,
        "Generic UICC T=1",
    ),
    (
        bytes.fromhex("3B9F94801FC7"),
        bytes.fromhex("FFFFFFFFFFFF"),
        CardType.UICC,
        "Generic UICC",
    ),
    # eUICC patterns
    (
        bytes.fromhex("3B9F96801FC78031A073"),
        bytes.fromhex("FFFFFFFFFFFF00FFFFFFFF"),
        CardType.EUICC,
        "eUICC",
    ),
    # JavaCard patterns
    (
        bytes.fromhex("3B8980014A434F5033"),
        bytes.fromhex("FFFFFFFFFFFFFFFFFFFFFFFF"),
        CardType.JAVACARD,
        "JCOP3 JavaCard",
    ),
    (
        bytes.fromhex("3BFE9100FF918171"),
        bytes.fromhex("FFFFFFFF00FFFFFFFF"),
        CardType.JAVACARD,
        "JavaCard",
    ),
    # Legacy SIM patterns
    (
        bytes.fromhex("3B3F94"),
        bytes.fromhex("FFFFFF"),
        CardType.SIM,
        "Legacy GSM SIM",
    ),
    (
        bytes.fromhex("3B9F94"),
        bytes.fromhex("FFFFFF"),
        CardType.UICC,
        "UICC/USIM",
    ),
]


class ATRParser:
    """Parser for Answer-To-Reset (ATR) bytes.

    This class parses ATR bytes according to ISO 7816-3 and extracts:
    - Convention (direct/inverse)
    - Supported protocols (T=0, T=1)
    - Historical bytes
    - Card type detection

    Example:
        ```python
        parser = ATRParser()
        atr_info = parser.parse(bytes.fromhex("3B9F96801FC78031E073FE211B6357"))
        print(f"Card type: {atr_info.card_type}")
        print(f"Protocols: {atr_info.protocols}")
        ```
    """

    def parse(self, atr: Union[bytes, str]) -> ATRInfo:
        """Parse ATR bytes.

        Args:
            atr: ATR as bytes or hex string.

        Returns:
            Parsed ATRInfo structure.

        Raises:
            ATRError: If ATR is invalid.
        """
        if isinstance(atr, str):
            try:
                atr = bytes.fromhex(atr.replace(" ", ""))
            except ValueError as e:
                raise ATRError(f"Invalid hex string: {e}")

        if len(atr) < 2:
            raise ATRError("ATR too short (minimum 2 bytes)", atr)

        info = ATRInfo(raw=atr)

        try:
            offset = self._parse_ts(atr, info)
            offset = self._parse_t0(atr, offset, info)
            offset = self._parse_interface_bytes(atr, offset, info)
            offset = self._parse_historical_bytes(atr, offset, info)
            self._parse_tck(atr, offset, info)
            self._identify_card_type(info)
        except IndexError as e:
            raise ATRError(f"ATR parsing failed: {e}", atr)

        return info

    def _parse_ts(self, atr: bytes, info: ATRInfo) -> int:
        """Parse TS (initial character).

        Returns:
            Next offset.
        """
        ts = atr[0]
        info.ts = ts

        if ts == 0x3B:
            info.convention = Convention.DIRECT
        elif ts == 0x3F:
            info.convention = Convention.INVERSE
        else:
            raise ATRError(f"Invalid TS byte: {ts:02X} (expected 3B or 3F)", atr)

        return 1

    def _parse_t0(self, atr: bytes, offset: int, info: ATRInfo) -> int:
        """Parse T0 (format byte).

        Returns:
            Next offset.
        """
        t0 = atr[offset]
        info.t0 = t0
        return offset + 1

    def _parse_interface_bytes(self, atr: bytes, offset: int, info: ATRInfo) -> int:
        """Parse interface bytes (TA, TB, TC, TD).

        Returns:
            Offset after interface bytes.
        """
        # T0 indicates which interface bytes are present for first set
        y = (info.t0 >> 4) & 0x0F
        i = 1  # Interface byte set number

        while True:
            # Parse TAi if present
            if y & 0x01:
                if offset >= len(atr):
                    raise ATRError(f"ATR truncated at TA{i}", atr)
                info.ta.append(atr[offset])
                offset += 1

            # Parse TBi if present
            if y & 0x02:
                if offset >= len(atr):
                    raise ATRError(f"ATR truncated at TB{i}", atr)
                info.tb.append(atr[offset])
                offset += 1

            # Parse TCi if present
            if y & 0x04:
                if offset >= len(atr):
                    raise ATRError(f"ATR truncated at TC{i}", atr)
                info.tc.append(atr[offset])
                offset += 1

            # Parse TDi if present
            if y & 0x08:
                if offset >= len(atr):
                    raise ATRError(f"ATR truncated at TD{i}", atr)
                td = atr[offset]
                info.td.append(td)

                # Extract protocol from lower nibble
                protocol = td & 0x0F
                if protocol not in info.protocols:
                    info.protocols.append(protocol)

                offset += 1
                i += 1
                y = (td >> 4) & 0x0F

                # Continue if more interface bytes indicated
                if y == 0:
                    break
            else:
                break

        # If no protocol indicated, default to T=0
        if not info.protocols:
            info.protocols.append(0)

        return offset

    def _parse_historical_bytes(self, atr: bytes, offset: int, info: ATRInfo) -> int:
        """Parse historical bytes.

        Returns:
            Offset after historical bytes.
        """
        # Number of historical bytes from T0 lower nibble
        k = info.t0 & 0x0F

        if k > 0:
            if offset + k > len(atr):
                # May be truncated, take what we have
                k = len(atr) - offset

            info.historical_bytes = atr[offset : offset + k]
            offset += k

        return offset

    def _parse_tck(self, atr: bytes, offset: int, info: ATRInfo) -> None:
        """Parse TCK (check byte) if present.

        TCK is present if any protocol other than T=0 is indicated.
        """
        if offset < len(atr):
            info.tck = atr[offset]

            # Verify TCK (XOR of bytes from T0 to TCK should be 0)
            if any(p != 0 for p in info.protocols):
                xor = 0
                for b in atr[1 : offset + 1]:
                    xor ^= b
                if xor != 0:
                    logger.warning(f"ATR TCK verification failed (XOR={xor:02X})")

    def _identify_card_type(self, info: ATRInfo) -> None:
        """Identify card type from ATR patterns."""
        atr = info.raw

        # Try known patterns
        for pattern, mask, card_type, description in KNOWN_ATR_PATTERNS:
            if self._match_pattern(atr, pattern, mask):
                info.card_type = card_type
                logger.debug(f"Identified card type: {description}")
                return

        # Fallback detection based on ATR characteristics
        if info.historical_bytes:
            hist = info.historical_bytes.hex().upper()

            # Check for UICC/USIM indicators in historical bytes
            if "80" in hist[:4]:  # Compact-TLV indicator
                info.card_type = CardType.UICC
                return

            # Check for "USIM" string
            if b"USIM" in info.historical_bytes:
                info.card_type = CardType.USIM
                return

            # Check for "SIM" string
            if b"SIM" in info.historical_bytes:
                info.card_type = CardType.UICC
                return

        # Default to unknown
        info.card_type = CardType.UNKNOWN

    def _match_pattern(self, atr: bytes, pattern: bytes, mask: bytes) -> bool:
        """Check if ATR matches a pattern with mask.

        Args:
            atr: ATR bytes.
            pattern: Expected pattern.
            mask: Mask (FF = must match, 00 = any value).

        Returns:
            True if pattern matches.
        """
        if len(atr) < len(pattern):
            return False

        for i, (p, m) in enumerate(zip(pattern, mask)):
            if (atr[i] & m) != (p & m):
                return False

        return True

    def get_protocol(self, info: ATRInfo) -> Protocol:
        """Get preferred protocol from ATR.

        Args:
            info: Parsed ATR info.

        Returns:
            Preferred protocol (T=1 if supported, else T=0).
        """
        if 1 in info.protocols:
            return Protocol.T1
        return Protocol.T0

    @staticmethod
    def format_atr(atr: Union[bytes, str]) -> str:
        """Format ATR for display.

        Args:
            atr: ATR bytes or hex string.

        Returns:
            Formatted ATR string with spaces.
        """
        if isinstance(atr, bytes):
            hex_str = atr.hex().upper()
        else:
            hex_str = atr.upper().replace(" ", "")

        # Add space every 2 characters
        return " ".join(hex_str[i : i + 2] for i in range(0, len(hex_str), 2))

    @staticmethod
    def get_card_type_name(card_type: CardType) -> str:
        """Get human-readable card type name.

        Args:
            card_type: Card type enum.

        Returns:
            Human-readable name.
        """
        names = {
            CardType.UNKNOWN: "Unknown",
            CardType.UICC: "UICC",
            CardType.USIM: "USIM (3G/4G)",
            CardType.ISIM: "ISIM (IMS)",
            CardType.EUICC: "eUICC (eSIM)",
            CardType.SIM: "SIM (2G GSM)",
            CardType.JAVACARD: "JavaCard",
        }
        return names.get(card_type, "Unknown")


def parse_atr(atr: Union[bytes, str]) -> ATRInfo:
    """Convenience function to parse ATR.

    Args:
        atr: ATR bytes or hex string.

    Returns:
        Parsed ATRInfo.
    """
    parser = ATRParser()
    return parser.parse(atr)
