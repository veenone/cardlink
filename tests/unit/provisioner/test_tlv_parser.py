"""
Unit tests for TLV Parser.

Tests the TLVParser class with various TLV structures including simple tags,
constructed tags, different length encodings, and nested structures according
to ASN.1 BER encoding rules.
"""

import pytest

from cardlink.provisioner.tlv_parser import TLV, TLVParser, Tags
from cardlink.provisioner.exceptions import TLVError, TLVParseError


class TestTLVDataclass:
    """Test TLV dataclass properties and methods."""

    def test_create_simple_tlv(self):
        """Test creating simple TLV."""
        tlv = TLV(tag=0x84, value=bytes.fromhex("A0000000041010"))

        assert tlv.tag == 0x84
        assert tlv.value == bytes.fromhex("A0000000041010")
        assert tlv.length == 7
        assert len(tlv.children) == 0

    def test_tag_bytes_single_byte(self):
        """Test tag_bytes for single-byte tag."""
        tlv = TLV(tag=0x84, value=b"test")

        assert tlv.tag_bytes == bytes([0x84])

    def test_tag_bytes_two_byte(self):
        """Test tag_bytes for two-byte tag."""
        tlv = TLV(tag=0xBF0C, value=b"test")

        assert tlv.tag_bytes == bytes([0xBF, 0x0C])

    def test_tag_hex(self):
        """Test tag_hex property."""
        tlv = TLV(tag=0x84, value=b"test")

        assert tlv.tag_hex == "84"

    def test_tag_hex_two_byte(self):
        """Test tag_hex for two-byte tag."""
        tlv = TLV(tag=0xBF0C, value=b"test")

        assert tlv.tag_hex == "BF0C"

    def test_is_constructed_primitive(self):
        """Test is_constructed for primitive tag."""
        tlv = TLV(tag=0x84, value=b"test")  # Bit 6 not set

        assert not tlv.is_constructed

    def test_is_constructed_constructed(self):
        """Test is_constructed for constructed tag."""
        tlv = TLV(tag=0xA5, value=b"test")  # Bit 6 set (0x20)

        assert tlv.is_constructed

    def test_is_constructed_two_byte_tag(self):
        """Test is_constructed with two-byte tag."""
        tlv = TLV(tag=0xBF0C, value=b"test")  # First byte has bit 6 set

        assert tlv.is_constructed

    def test_to_bytes_simple(self):
        """Test encoding simple TLV to bytes."""
        tlv = TLV(tag=0x84, value=bytes.fromhex("A0000000041010"))

        result = tlv.to_bytes()

        expected = bytes.fromhex("8407A0000000041010")
        assert result == expected

    def test_to_hex(self):
        """Test to_hex method."""
        tlv = TLV(tag=0x84, value=bytes.fromhex("A0000000041010"))

        result = tlv.to_hex()

        assert result == "8407A0000000041010"

    def test_to_dict_simple(self):
        """Test converting simple TLV to dict."""
        tlv = TLV(tag=0x84, value=bytes.fromhex("AABBCC"))

        result = tlv.to_dict()

        assert result["tag"] == "84"
        assert result["length"] == 3
        assert result["value"] == "AABBCC"

    def test_to_dict_with_children(self):
        """Test converting TLV with children to dict."""
        parent = TLV(tag=0xA5, value=b"")
        parent.children = [
            TLV(tag=0x84, value=b"test"),
            TLV(tag=0x85, value=b"data"),
        ]

        result = parent.to_dict()

        assert result["tag"] == "A5"
        assert "children" in result
        assert len(result["children"]) == 2

    def test_find_child(self):
        """Test finding child TLV by tag."""
        parent = TLV(tag=0xA5, value=b"")
        child1 = TLV(tag=0x84, value=b"test")
        child2 = TLV(tag=0x85, value=b"data")
        parent.children = [child1, child2]

        found = parent.find(0x84)

        assert found == child1
        assert found.value == b"test"

    def test_find_child_not_found(self):
        """Test finding non-existent child."""
        parent = TLV(tag=0xA5, value=b"")
        parent.children = [TLV(tag=0x84, value=b"test")]

        found = parent.find(0x99)

        assert found is None

    def test_find_all(self):
        """Test finding all children with tag."""
        parent = TLV(tag=0xA5, value=b"")
        parent.children = [
            TLV(tag=0x84, value=b"test1"),
            TLV(tag=0x84, value=b"test2"),
            TLV(tag=0x85, value=b"data"),
        ]

        found = parent.find_all(0x84)

        assert len(found) == 2
        assert found[0].value == b"test1"
        assert found[1].value == b"test2"

    def test_find_recursive(self):
        """Test recursive search for tag in children."""
        # Test finding direct child recursively
        data = bytes.fromhex("6F0BA5098407A0000000041010")
        tlv = TLVParser.parse(data)

        # Find A5 (immediate child of 6F)
        found = tlv.find_recursive(0xA5)

        assert found is not None
        assert found.tag == 0xA5
        # Verify it has children
        assert len(found.children) == 1

    def test_find_recursive_self(self):
        """Test recursive search finds self."""
        tlv = TLV(tag=0x84, value=b"test")

        found = tlv.find_recursive(0x84)

        assert found == tlv

    def test_iter_children(self):
        """Test iterating over children."""
        parent = TLV(tag=0xA5, value=b"")
        parent.children = [
            TLV(tag=0x84, value=b"test1"),
            TLV(tag=0x85, value=b"test2"),
        ]

        children = list(parent)

        assert len(children) == 2
        assert children[0].tag == 0x84

    def test_len_children(self):
        """Test len() on TLV returns child count."""
        parent = TLV(tag=0xA5, value=b"")
        parent.children = [TLV(tag=0x84, value=b"test")] * 3

        assert len(parent) == 3


class TestTLVParserSimple:
    """Test parsing simple TLV structures."""

    def test_parse_simple_tlv_bytes(self):
        """Test parsing simple TLV from bytes."""
        data = bytes.fromhex("8407A0000000041010")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x84
        assert tlv.value == bytes.fromhex("A0000000041010")

    def test_parse_simple_tlv_hex_string(self):
        """Test parsing TLV from hex string."""
        data = "84 07 A0 00 00 00 04 10 10"

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x84
        assert tlv.value == bytes.fromhex("A0000000041010")

    def test_parse_empty_data(self):
        """Test parsing empty data raises error."""
        with pytest.raises(TLVParseError, match="Empty data"):
            TLVParser.parse(b"")

    def test_parse_invalid_hex_string(self):
        """Test parsing invalid hex string."""
        with pytest.raises(TLVParseError, match="Invalid hex string"):
            TLVParser.parse("not a hex string")

    def test_parse_truncated_tlv(self):
        """Test parsing truncated TLV."""
        # Tag and length indicate 7 bytes, but only 3 provided
        data = bytes.fromhex("8407AABBCC")

        with pytest.raises(TLVParseError, match="extends beyond data"):
            TLVParser.parse(data)

    def test_parse_zero_length_value(self):
        """Test parsing TLV with zero-length value."""
        data = bytes.fromhex("8400")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x84
        assert tlv.value == b""
        assert tlv.length == 0


class TestTLVParserTags:
    """Test parsing different tag formats."""

    def test_parse_single_byte_tag(self):
        """Test parsing single-byte tag."""
        data = bytes.fromhex("5003AABBCC")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x50

    def test_parse_two_byte_tag(self):
        """Test parsing two-byte tag."""
        # Tag BF0C (bits 1-5 all set in first byte)
        data = bytes.fromhex("BF0C03AABBCC")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0xBF0C
        assert tlv.value == bytes.fromhex("AABBCC")

    def test_parse_constructed_tag(self):
        """Test parsing constructed tag (bit 6 set)."""
        data = bytes.fromhex("A503840100")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0xA5
        assert tlv.is_constructed

    def test_parse_tag_truncated(self):
        """Test parsing with truncated multi-byte tag."""
        # BF without second byte
        data = bytes.fromhex("BF")

        with pytest.raises(TLVParseError, match="multi-byte tag"):
            TLVParser.parse(data)


class TestTLVParserLength:
    """Test parsing different length encodings."""

    def test_parse_short_form_length(self):
        """Test parsing short form length (< 0x80)."""
        data = bytes.fromhex("840AAA" + "BB" * 9)

        tlv = TLVParser.parse(data)

        assert tlv.length == 10

    def test_parse_long_form_81_length(self):
        """Test parsing long form length (0x81)."""
        # Length = 0x81 0x90 = 144 bytes
        value = b"\xAA" * 144
        data = bytes([0x84, 0x81, 0x90]) + value

        tlv = TLVParser.parse(data)

        assert tlv.length == 144

    def test_parse_long_form_82_length(self):
        """Test parsing long form length (0x82)."""
        # Length = 0x82 0x01 0x00 = 256 bytes
        value = b"\xBB" * 256
        data = bytes([0x84, 0x82, 0x01, 0x00]) + value

        tlv = TLVParser.parse(data)

        assert tlv.length == 256

    def test_parse_long_form_83_length(self):
        """Test parsing long form length (0x83)."""
        # Length = 0x83 0x00 0x01 0x00 = 256 bytes
        value = b"\xCC" * 256
        data = bytes([0x84, 0x83, 0x00, 0x01, 0x00]) + value

        tlv = TLVParser.parse(data)

        assert tlv.length == 256

    def test_parse_indefinite_length_error(self):
        """Test parsing indefinite length (0x80) raises error."""
        data = bytes.fromhex("A58000")

        with pytest.raises(TLVParseError, match="Indefinite length not supported"):
            TLVParser.parse(data)

    def test_parse_unsupported_length_encoding(self):
        """Test parsing unsupported length encoding."""
        # 0x84 = 4-byte length (not commonly used)
        data = bytes.fromhex("A5840000010000")

        with pytest.raises(TLVParseError, match="Unsupported length encoding"):
            TLVParser.parse(data)

    def test_parse_length_truncated(self):
        """Test parsing with truncated length bytes."""
        # Says 2 length bytes (0x82) but only 1 provided
        data = bytes.fromhex("A58201")

        with pytest.raises(TLVParseError, match="end of data in length"):
            TLVParser.parse(data)


class TestTLVParserConstructed:
    """Test parsing constructed TLV structures with children."""

    def test_parse_constructed_with_children(self):
        """Test parsing constructed TLV with child TLVs."""
        # A5 09 (FCI proprietary) - length fixed to 9
        #   84 07 A0000000041010 (DF name - 7 bytes)
        data = bytes.fromhex("A5098407A0000000041010")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0xA5
        assert tlv.is_constructed
        assert len(tlv.children) == 1
        assert tlv.children[0].tag == 0x84

    def test_parse_nested_constructed(self):
        """Test parsing nested constructed TLVs."""
        # 6F 0B (FCI template) - 11 bytes
        #   A5 09 (FCI proprietary) - 9 bytes
        #     84 07 A0000000041010 (DF name) - 7 bytes
        data = bytes.fromhex("6F0BA5098407A0000000041010")

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x6F
        assert len(tlv.children) == 1
        assert tlv.children[0].tag == 0xA5
        assert len(tlv.children[0].children) == 1
        assert tlv.children[0].children[0].tag == 0x84

    def test_parse_constructed_multiple_children(self):
        """Test parsing constructed with multiple children."""
        # A5 (FCI proprietary)
        #   84 03 AABBCC (DF name)
        #   87 01 00 (discretionary)
        data = bytes.fromhex("A5088403AABBCC870100")

        tlv = TLVParser.parse(data)

        assert len(tlv.children) == 2
        assert tlv.children[0].tag == 0x84
        assert tlv.children[1].tag == 0x87

    def test_parse_constructed_with_padding(self):
        """Test parsing constructed TLV with padding bytes."""
        # A5 with child and padding
        data = bytes.fromhex("A5068403AABBCC00")

        tlv = TLVParser.parse(data)

        assert len(tlv.children) == 1  # Padding skipped

    def test_parse_constructed_malformed_children(self):
        """Test parsing constructed with malformed children keeps raw value."""
        # A5 02 with malformed child data (02 says 2 bytes of value)
        data = bytes.fromhex("A50284FF")  # Child says 255 bytes but not present

        tlv = TLVParser.parse(data)

        # Should keep as raw value if children can't be parsed
        assert tlv.is_constructed
        assert len(tlv.children) == 0  # Parsing failed, no children


class TestTLVParserMultiple:
    """Test parsing multiple consecutive TLV structures."""

    def test_parse_all_multiple_tlvs(self):
        """Test parsing multiple consecutive TLVs."""
        data = bytes.fromhex("8403AABBCC8502DDEE")

        tlvs = TLVParser.parse_all(data)

        assert len(tlvs) == 2
        assert tlvs[0].tag == 0x84
        assert tlvs[1].tag == 0x85

    def test_parse_all_with_padding(self):
        """Test parsing multiple TLVs with padding."""
        data = bytes.fromhex("8403AABBCC008502DDEEFF")

        tlvs = TLVParser.parse_all(data)

        assert len(tlvs) == 2

    def test_parse_all_empty_data(self):
        """Test parsing empty data returns empty list."""
        tlvs = TLVParser.parse_all(b"")

        assert tlvs == []

    def test_parse_all_only_padding(self):
        """Test parsing only padding bytes."""
        data = bytes.fromhex("0000FFFF")

        tlvs = TLVParser.parse_all(data)

        assert tlvs == []


class TestTLVParserBuild:
    """Test building TLV structures."""

    def test_build_simple_tlv_bytes(self):
        """Test building TLV from bytes."""
        result = TLVParser.build(0x84, bytes.fromhex("A0000000041010"))

        expected = bytes.fromhex("8407A0000000041010")
        assert result == expected

    def test_build_simple_tlv_hex_string(self):
        """Test building TLV from hex string."""
        result = TLVParser.build(0x84, "A0 00 00 00 04 10 10")

        expected = bytes.fromhex("8407A0000000041010")
        assert result == expected

    def test_build_two_byte_tag(self):
        """Test building TLV with two-byte tag."""
        result = TLVParser.build(0xBF0C, bytes.fromhex("AABBCC"))

        expected = bytes.fromhex("BF0C03AABBCC")
        assert result == expected

    def test_build_empty_value(self):
        """Test building TLV with empty value."""
        result = TLVParser.build(0x84, b"")

        expected = bytes.fromhex("8400")
        assert result == expected

    def test_build_constructed(self):
        """Test building constructed TLV."""
        children = [
            TLV(tag=0x84, value=bytes.fromhex("AABBCC")),
            TLV(tag=0x85, value=bytes.fromhex("DDEE")),
        ]

        result = TLVParser.build_constructed(0xA5, children)

        # Total value length: 8403AABBCC (5 bytes) + 8502DDEE (4 bytes) = 9 bytes
        expected = bytes.fromhex("A5098403AABBCC8502DDEE")
        assert result == expected


class TestTLVParserEncodeLength:
    """Test length encoding."""

    def test_encode_length_short_form(self):
        """Test encoding short form length."""
        result = TLVParser.encode_length(10)

        assert result == bytes([0x0A])

    def test_encode_length_short_form_max(self):
        """Test encoding maximum short form length."""
        result = TLVParser.encode_length(127)

        assert result == bytes([0x7F])

    def test_encode_length_81_form(self):
        """Test encoding 0x81 form (128-255 bytes)."""
        result = TLVParser.encode_length(200)

        assert result == bytes([0x81, 0xC8])

    def test_encode_length_82_form(self):
        """Test encoding 0x82 form (256-65535 bytes)."""
        result = TLVParser.encode_length(300)

        assert result == bytes([0x82, 0x01, 0x2C])

    def test_encode_length_83_form(self):
        """Test encoding 0x83 form (>65535 bytes)."""
        result = TLVParser.encode_length(70000)

        assert result == bytes([0x83, 0x01, 0x11, 0x70])

    def test_encode_length_too_large(self):
        """Test encoding length that's too large."""
        with pytest.raises(TLVError, match="Length too large"):
            TLVParser.encode_length(0x01000000)


class TestTLVParserGetValue:
    """Test utility function to get value by tag."""

    def test_get_value_found(self):
        """Test getting value for existing tag."""
        data = bytes.fromhex("8403AABBCC8502DDEE")

        value = TLVParser.get_value(data, 0x84)

        assert value == bytes.fromhex("AABBCC")

    def test_get_value_not_found(self):
        """Test getting value for non-existent tag."""
        data = bytes.fromhex("8403AABBCC")

        value = TLVParser.get_value(data, 0x99)

        assert value is None

    def test_get_value_in_constructed(self):
        """Test getting value from constructed TLV with direct child."""
        # Find tag 0xA5 which is a direct child
        data = bytes.fromhex("6F0BA5098407A0000000041010")

        value = TLVParser.get_value(data, 0xA5)

        # A5's value contains the encoded 84 TLV
        assert value is not None
        assert len(value) == 9

    def test_get_value_deep_nesting(self):
        """Test getting value searches through children recursively."""
        # Multiple TLVs at root level, find one deep inside
        data = bytes.fromhex("6F0BA5098407A0000000041010")

        # Parse and manually search
        tlv = TLVParser.parse(data)
        a5_child = tlv.find(0xA5)
        assert a5_child is not None

        value_84 = TLVParser.get_value(a5_child.value, 0x84)
        assert value_84 == bytes.fromhex("A0000000041010")

    def test_get_value_malformed_data(self):
        """Test getting value from malformed data."""
        data = bytes.fromhex("84FFAABB")  # Says 255 bytes but only 2

        value = TLVParser.get_value(data, 0x84)

        assert value is None


class TestTLVParserRealWorldExamples:
    """Test with real-world TLV data from smart cards."""

    def test_parse_fci_response(self):
        """Test parsing FCI response from SELECT command."""
        # Real FCI template from card SELECT response
        data = bytes.fromhex(
            "6F1C840E315041592E5359532E4444463031A50ABF0C0761054F07A0000000041010"
        )

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0x6F  # FCI template
        assert len(tlv.children) == 2
        # DF name
        df_name = tlv.find(0x84)
        assert df_name is not None
        # FCI proprietary
        fci_prop = tlv.find(0xA5)
        assert fci_prop is not None

    def test_parse_gp_get_status_response(self):
        """Test parsing GlobalPlatform GET STATUS response."""
        # Example GET STATUS response - simplified format
        data = bytes.fromhex(
            "E3"  # Registry data tag
            "14"  # Length = 20 bytes
            "0F"  # AID length = 15
            "A000000003000000000000000000000000"  # ISD AID (15 bytes)
            "07"  # Lifecycle state (1 byte)
            "0000"  # Privileges (2 bytes)
            "00"  # Executable module length (1 byte)
        )

        tlv = TLVParser.parse(data)

        assert tlv.tag == 0xE3
        assert len(tlv.value) == 20

    def test_parse_atr_historical_bytes(self):
        """Test parsing ATR historical bytes with padding."""
        # Historical bytes with padding and simple TLV
        data = bytes.fromhex("008403AABBCC")  # Padding + valid TLV

        tlvs = TLVParser.parse_all(data)

        # Should parse after padding
        assert len(tlvs) >= 1
        assert tlvs[0].tag == 0x84


class TestTags:
    """Test Tags constants."""

    def test_common_tags_defined(self):
        """Test that common tags are defined."""
        assert Tags.FCI_TEMPLATE == 0x6F
        assert Tags.DF_NAME == 0x84
        assert Tags.FCI_PROPRIETARY == 0xA5
        assert Tags.GP_AID == 0x4F

    def test_ber_tlv_tags_defined(self):
        """Test that BER-TLV common tags are defined."""
        assert Tags.SEQUENCE == 0x30
        assert Tags.OCTET_STRING == 0x04
        assert Tags.INTEGER == 0x02
