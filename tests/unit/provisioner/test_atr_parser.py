"""
Unit tests for ATR Parser.

Tests the ATRParser class with real-world ATR samples from various
UICC/SIM card vendors to verify parsing according to ISO 7816-3.
"""

import pytest

from cardlink.provisioner.atr_parser import ATRParser, parse_atr
from cardlink.provisioner.models import ATRInfo, CardType, Convention, Protocol
from cardlink.provisioner.exceptions import ATRError


class TestATRParserBasic:
    """Test basic ATR parsing functionality."""

    def test_parse_direct_convention(self):
        """Test parsing ATR with direct convention (TS=0x3B)."""
        parser = ATRParser()
        # Generic USIM ATR
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)

        assert info.ts == 0x3B
        assert info.convention == Convention.DIRECT
        assert info.raw == atr

    def test_parse_inverse_convention(self):
        """Test parsing ATR with inverse convention (TS=0x3F)."""
        parser = ATRParser()
        # Hypothetical inverse convention ATR
        atr = bytes.fromhex("3F9F96801FC78031E073FE211B6357")

        info = parser.parse(atr)

        assert info.ts == 0x3F
        assert info.convention == Convention.INVERSE

    def test_parse_from_hex_string(self):
        """Test parsing ATR from hex string."""
        parser = ATRParser()
        atr_hex = "3B 9F 96 80 1F C7 80 31 E0 73 FE 21 1B 63 57"

        info = parser.parse(atr_hex)

        assert info.ts == 0x3B
        assert info.convention == Convention.DIRECT

    def test_parse_invalid_ts_byte(self):
        """Test parsing fails with invalid TS byte."""
        parser = ATRParser()
        # Invalid TS byte (not 3B or 3F)
        atr = bytes.fromhex("FF9F96801FC78031E073FE211B")

        with pytest.raises(ATRError, match="Invalid TS byte"):
            parser.parse(atr)

    def test_parse_too_short(self):
        """Test parsing fails with ATR too short."""
        parser = ATRParser()
        atr = bytes([0x3B])  # Only TS byte

        with pytest.raises(ATRError, match="ATR too short"):
            parser.parse(atr)

    def test_parse_invalid_hex_string(self):
        """Test parsing fails with invalid hex string."""
        parser = ATRParser()

        with pytest.raises(ATRError, match="Invalid hex string"):
            parser.parse("not a hex string")


class TestATRParserT0Parsing:
    """Test T0 (format byte) parsing."""

    def test_parse_t0_basic(self):
        """Test parsing T0 byte."""
        parser = ATRParser()
        # T0 = 0x9F means Y1=9 (TA1, TB1, TD1 present), K=15 historical bytes
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)

        assert info.t0 == 0x9F
        # K = lower nibble of T0 = 15 historical bytes
        assert len(info.historical_bytes) > 0


class TestATRParserProtocolDetection:
    """Test protocol detection from TD bytes."""

    def test_detect_t0_protocol(self):
        """Test detection of T=0 protocol."""
        parser = ATRParser()
        # ATR with T=0 only
        atr = bytes.fromhex("3B3F94000077C1641300058307")

        info = parser.parse(atr)

        assert Protocol.T0 in info.protocols

    def test_detect_t1_protocol(self):
        """Test detection of T=1 protocol."""
        parser = ATRParser()
        # Generic USIM with T=1
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)

        # Most modern UICC cards support T=1
        assert Protocol.T1 in info.protocols


class TestATRParserCardTypeDetection:
    """Test card type detection from ATR patterns."""

    def test_detect_usim_gemalto(self):
        """Test detection of Gemalto USIM card."""
        parser = ATRParser()
        # Gemalto USIM pattern
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)

        # Should detect as USIM or UICC
        assert info.card_type in [CardType.USIM, CardType.UICC]

    def test_detect_uicc_generic(self):
        """Test detection of generic UICC card."""
        parser = ATRParser()
        # Generic UICC T=1
        atr = bytes.fromhex("3B9F95801FC78031E073BE211367A5C38F078090")

        info = parser.parse(atr)

        assert info.card_type in [CardType.UICC, CardType.USIM]

    def test_detect_euicc(self):
        """Test detection of eUICC card."""
        parser = ATRParser()
        # eUICC pattern (A0 instead of E0 in byte 9)
        atr = bytes.fromhex("3B9F96801FC78031A073BE211367A5C38F078090")

        info = parser.parse(atr)

        # Should detect as eUICC or UICC
        assert info.card_type in [CardType.EUICC, CardType.UICC]

    def test_detect_javacard(self):
        """Test detection of JavaCard."""
        parser = ATRParser()
        # JCOP3 JavaCard pattern
        atr = bytes.fromhex("3B8980014A434F5033314A32")

        info = parser.parse(atr)

        assert info.card_type == CardType.JAVACARD

    def test_detect_legacy_sim(self):
        """Test detection of legacy GSM SIM."""
        parser = ATRParser()
        # Legacy SIM pattern
        atr = bytes.fromhex("3B3F94000077C1641300058307")

        info = parser.parse(atr)

        assert info.card_type in [CardType.SIM, CardType.UICC]

    def test_unknown_card_type(self):
        """Test detection falls back to UNKNOWN for unrecognized ATR."""
        parser = ATRParser()
        # Completely custom ATR that doesn't match patterns
        atr = bytes.fromhex("3B0000000000")

        info = parser.parse(atr)

        assert info.card_type == CardType.UNKNOWN


class TestATRParserHistoricalBytes:
    """Test historical bytes extraction."""

    def test_extract_historical_bytes(self):
        """Test extraction of historical bytes."""
        parser = ATRParser()
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)

        # Should have historical bytes
        assert info.historical_bytes is not None
        assert len(info.historical_bytes) > 0

    def test_no_historical_bytes(self):
        """Test ATR with no historical bytes (K=0)."""
        parser = ATRParser()
        # T0 = 0x90 means Y1=9 (TA1, TB1, TD1 present), K=0 historical bytes
        atr = bytes.fromhex("3B9096801F")

        info = parser.parse(atr)

        # Historical bytes should be empty
        assert len(info.historical_bytes) == 0


class TestATRParserHelperFunctions:
    """Test helper and utility functions."""

    def test_parse_atr_function(self):
        """Test module-level parse_atr() function."""
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parse_atr(atr)

        assert isinstance(info, ATRInfo)
        assert info.ts == 0x3B

    def test_format_atr(self):
        """Test ATR formatting utility."""
        parser = ATRParser()
        atr_bytes = bytes.fromhex("3B9F96801FC78031")

        formatted = parser.format_atr(atr_bytes)

        assert isinstance(formatted, str)
        assert "3B" in formatted
        assert "9F" in formatted

    def test_get_card_type_name(self):
        """Test card type name retrieval."""
        parser = ATRParser()

        name = parser.get_card_type_name(CardType.USIM)

        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_protocol(self):
        """Test protocol extraction."""
        parser = ATRParser()
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F80")

        info = parser.parse(atr)
        protocol = parser.get_protocol(info)

        assert isinstance(protocol, Protocol)
        assert protocol in [Protocol.T0, Protocol.T1]


class TestATRParserRealWorldSamples:
    """Test with real-world ATR samples from major vendors."""

    def test_gemalto_usim(self):
        """Test Gemalto USIM ATR."""
        parser = ATRParser()
        # Gemalto IDPrime.NET card
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F8090")

        info = parser.parse(atr)

        assert info.convention == Convention.DIRECT
        assert Protocol.T1 in info.protocols
        assert info.card_type in [CardType.USIM, CardType.UICC]

    def test_gnd_usim(self):
        """Test G&D (Giesecke & Devrient) USIM ATR."""
        parser = ATRParser()
        # G&D USIM
        atr = bytes.fromhex("3B9E96801FC78031E073FE211B667D0002009000")

        info = parser.parse(atr)

        assert info.convention == Convention.DIRECT
        assert info.card_type in [CardType.USIM, CardType.UICC]

    def test_idemia_usim(self):
        """Test IDEMIA (formerly Oberthur) USIM ATR."""
        parser = ATRParser()
        # IDEMIA USIM
        atr = bytes.fromhex("3B9F95801FC78031E073FE211367A5C38F078090")

        info = parser.parse(atr)

        assert info.convention == Convention.DIRECT
        assert info.card_type in [CardType.USIM, CardType.UICC]

    def test_nxp_jcop3(self):
        """Test NXP JCOP3 JavaCard ATR."""
        parser = ATRParser()
        # JCOP3 EMV
        atr = bytes.fromhex("3B8980014A434F5033314A3243")

        info = parser.parse(atr)

        assert info.convention == Convention.DIRECT
        assert info.card_type == CardType.JAVACARD

    def test_euicc_profile(self):
        """Test eUICC/eSIM ATR."""
        parser = ATRParser()
        # eUICC with embedded profile
        atr = bytes.fromhex("3B9F96801FC78031A073BE211367A5C38F078090")

        info = parser.parse(atr)

        assert info.convention == Convention.DIRECT
        assert info.card_type in [CardType.EUICC, CardType.UICC]


class TestATRParserEdgeCases:
    """Test edge cases and error conditions."""

    def test_minimal_valid_atr(self):
        """Test minimal valid ATR (TS + T0 only)."""
        parser = ATRParser()
        # Minimal: TS=3B, T0=00 (no interface bytes, no historical bytes)
        atr = bytes.fromhex("3B00")

        info = parser.parse(atr)

        assert info.ts == 0x3B
        assert info.t0 == 0x00

    def test_maximum_historical_bytes(self):
        """Test ATR with maximum historical bytes (K=15)."""
        parser = ATRParser()
        # T0 = 0x0F means K=15 historical bytes
        atr = bytes.fromhex("3B0F") + bytes(15)  # 15 historical bytes

        info = parser.parse(atr)

        assert len(info.historical_bytes) == 15

    def test_truncated_atr(self):
        """Test parsing fails with truncated ATR."""
        parser = ATRParser()
        # ATR indicates historical bytes but they're missing
        atr = bytes.fromhex("3B0F")  # Says 15 historical bytes but none provided

        with pytest.raises(ATRError):
            parser.parse(atr)

    def test_atr_with_checksum(self):
        """Test ATR with TCK checksum byte."""
        parser = ATRParser()
        # ATR with T=1 protocol requires TCK
        atr = bytes.fromhex("3B9F96801FC78031E073FE211B6357A4891F8090")

        info = parser.parse(atr)

        # Should parse successfully with checksum
        assert info.tck is not None
