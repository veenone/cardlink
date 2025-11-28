"""TLV (Tag-Length-Value) Parser for smart card data structures.

This module provides parsing and construction of TLV data structures
following ASN.1 BER encoding rules as used in smart card applications.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from gp_ota_tester.provisioner.exceptions import TLVError, TLVParseError

logger = logging.getLogger(__name__)


@dataclass
class TLV:
    """A single TLV (Tag-Length-Value) structure.

    Attributes:
        tag: Tag bytes (1 or 2 bytes).
        value: Value bytes.
        children: Nested TLV structures (for constructed tags).
    """

    tag: int
    value: bytes = b""
    children: List["TLV"] = field(default_factory=list)

    @property
    def tag_bytes(self) -> bytes:
        """Get tag as bytes."""
        if self.tag > 0xFF:
            return bytes([(self.tag >> 8) & 0xFF, self.tag & 0xFF])
        return bytes([self.tag])

    @property
    def tag_hex(self) -> str:
        """Get tag as hex string."""
        return self.tag_bytes.hex().upper()

    @property
    def length(self) -> int:
        """Get value length."""
        return len(self.value)

    @property
    def is_constructed(self) -> bool:
        """Check if this is a constructed TLV (bit 6 of first tag byte)."""
        first_byte = self.tag if self.tag <= 0xFF else (self.tag >> 8) & 0xFF
        return bool(first_byte & 0x20)

    def to_bytes(self) -> bytes:
        """Encode TLV to bytes.

        Returns:
            Encoded TLV bytes.
        """
        # Tag
        result = self.tag_bytes

        # Length
        result += TLVParser.encode_length(self.length)

        # Value
        result += self.value

        return result

    def to_hex(self) -> str:
        """Get TLV as hex string."""
        return self.to_bytes().hex().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            "tag": self.tag_hex,
            "length": self.length,
        }

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        else:
            result["value"] = self.value.hex().upper()

        return result

    def find(self, tag: int) -> Optional["TLV"]:
        """Find first child TLV with given tag.

        Args:
            tag: Tag to search for.

        Returns:
            TLV if found, None otherwise.
        """
        for child in self.children:
            if child.tag == tag:
                return child
        return None

    def find_all(self, tag: int) -> List["TLV"]:
        """Find all child TLVs with given tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of matching TLVs.
        """
        return [child for child in self.children if child.tag == tag]

    def find_recursive(self, tag: int) -> Optional["TLV"]:
        """Find first TLV with given tag recursively.

        Args:
            tag: Tag to search for.

        Returns:
            TLV if found, None otherwise.
        """
        if self.tag == tag:
            return self

        for child in self.children:
            result = child.find_recursive(tag)
            if result:
                return result

        return None

    def __iter__(self) -> Iterator["TLV"]:
        """Iterate over children."""
        return iter(self.children)

    def __len__(self) -> int:
        """Get number of children."""
        return len(self.children)


class TLVParser:
    """Parser for TLV (Tag-Length-Value) structures.

    This class provides methods for parsing and constructing TLV
    data structures following ASN.1 BER encoding rules.

    Example:
        ```python
        parser = TLVParser()

        # Parse TLV data
        tlv = parser.parse(bytes.fromhex("6F10840E315041592E5359532E4444463031"))

        # Build TLV data
        data = parser.build(0x84, bytes.fromhex("A0000000041010"))
        ```
    """

    @staticmethod
    def parse(data: Union[bytes, str]) -> TLV:
        """Parse TLV data.

        Args:
            data: TLV data as bytes or hex string.

        Returns:
            Parsed TLV structure.

        Raises:
            TLVParseError: If parsing fails.
        """
        if isinstance(data, str):
            try:
                data = bytes.fromhex(data.replace(" ", ""))
            except ValueError as e:
                raise TLVParseError(f"Invalid hex string: {e}")

        if not data:
            raise TLVParseError("Empty data")

        tlv, consumed = TLVParser._parse_tlv(data, 0)
        return tlv

    @staticmethod
    def parse_all(data: Union[bytes, str]) -> List[TLV]:
        """Parse multiple consecutive TLV structures.

        Args:
            data: TLV data as bytes or hex string.

        Returns:
            List of parsed TLV structures.

        Raises:
            TLVParseError: If parsing fails.
        """
        if isinstance(data, str):
            try:
                data = bytes.fromhex(data.replace(" ", ""))
            except ValueError as e:
                raise TLVParseError(f"Invalid hex string: {e}")

        if not data:
            return []

        tlvs = []
        offset = 0

        while offset < len(data):
            # Skip padding bytes
            if data[offset] == 0x00 or data[offset] == 0xFF:
                offset += 1
                continue

            tlv, consumed = TLVParser._parse_tlv(data, offset)
            tlvs.append(tlv)
            offset += consumed

        return tlvs

    @staticmethod
    def _parse_tlv(data: bytes, offset: int) -> Tuple[TLV, int]:
        """Parse a single TLV at the given offset.

        Args:
            data: Full data buffer.
            offset: Starting offset.

        Returns:
            Tuple of (parsed TLV, bytes consumed).

        Raises:
            TLVParseError: If parsing fails.
        """
        start_offset = offset

        if offset >= len(data):
            raise TLVParseError("Unexpected end of data", offset, data)

        # Parse tag
        tag, offset = TLVParser._parse_tag(data, offset)

        # Parse length
        length, offset = TLVParser._parse_length(data, offset)

        # Check bounds
        if offset + length > len(data):
            raise TLVParseError(
                f"Value extends beyond data (need {length} bytes, have {len(data) - offset})",
                offset,
                data,
            )

        # Extract value
        value = data[offset : offset + length]
        offset += length

        # Create TLV
        tlv = TLV(tag=tag, value=value)

        # Parse children for constructed TLVs
        if tlv.is_constructed and value:
            try:
                child_offset = 0
                while child_offset < len(value):
                    # Skip padding
                    if value[child_offset] == 0x00 or value[child_offset] == 0xFF:
                        child_offset += 1
                        continue

                    child, consumed = TLVParser._parse_tlv(value, child_offset)
                    tlv.children.append(child)
                    child_offset += consumed
            except TLVParseError:
                # If children parsing fails, keep as raw value
                tlv.children = []

        return tlv, offset - start_offset

    @staticmethod
    def _parse_tag(data: bytes, offset: int) -> Tuple[int, int]:
        """Parse tag bytes.

        Args:
            data: Data buffer.
            offset: Starting offset.

        Returns:
            Tuple of (tag value, new offset).
        """
        if offset >= len(data):
            raise TLVParseError("Unexpected end of data while parsing tag", offset, data)

        first_byte = data[offset]
        offset += 1

        # Check for multi-byte tag (bits 1-5 all set)
        if (first_byte & 0x1F) == 0x1F:
            if offset >= len(data):
                raise TLVParseError("Unexpected end of data in multi-byte tag", offset, data)

            second_byte = data[offset]
            offset += 1

            # Could have more bytes if bit 8 is set, but most cards use 2-byte max
            tag = (first_byte << 8) | second_byte
        else:
            tag = first_byte

        return tag, offset

    @staticmethod
    def _parse_length(data: bytes, offset: int) -> Tuple[int, int]:
        """Parse length bytes.

        Args:
            data: Data buffer.
            offset: Starting offset.

        Returns:
            Tuple of (length value, new offset).
        """
        if offset >= len(data):
            raise TLVParseError("Unexpected end of data while parsing length", offset, data)

        first_byte = data[offset]
        offset += 1

        if first_byte < 0x80:
            # Short form: single byte length
            return first_byte, offset

        if first_byte == 0x80:
            # Indefinite length (not supported for parsing)
            raise TLVParseError("Indefinite length not supported", offset - 1, data)

        if first_byte == 0x81:
            # Long form: 1 length byte
            if offset >= len(data):
                raise TLVParseError("Unexpected end of data in length", offset, data)
            return data[offset], offset + 1

        if first_byte == 0x82:
            # Long form: 2 length bytes
            if offset + 1 >= len(data):
                raise TLVParseError("Unexpected end of data in length", offset, data)
            length = (data[offset] << 8) | data[offset + 1]
            return length, offset + 2

        if first_byte == 0x83:
            # Long form: 3 length bytes
            if offset + 2 >= len(data):
                raise TLVParseError("Unexpected end of data in length", offset, data)
            length = (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
            return length, offset + 3

        raise TLVParseError(f"Unsupported length encoding: {first_byte:02X}", offset - 1, data)

    @staticmethod
    def encode_length(length: int) -> bytes:
        """Encode length in BER format.

        Args:
            length: Length value.

        Returns:
            Encoded length bytes.
        """
        if length < 0x80:
            return bytes([length])
        elif length <= 0xFF:
            return bytes([0x81, length])
        elif length <= 0xFFFF:
            return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
        elif length <= 0xFFFFFF:
            return bytes(
                [0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF]
            )
        else:
            raise TLVError(f"Length too large: {length}")

    @staticmethod
    def build(tag: int, value: Union[bytes, str]) -> bytes:
        """Build TLV from tag and value.

        Args:
            tag: Tag value (1 or 2 bytes).
            value: Value as bytes or hex string.

        Returns:
            Encoded TLV bytes.
        """
        if isinstance(value, str):
            value = bytes.fromhex(value.replace(" ", ""))

        tlv = TLV(tag=tag, value=value)
        return tlv.to_bytes()

    @staticmethod
    def build_constructed(tag: int, children: List[TLV]) -> bytes:
        """Build constructed TLV from children.

        Args:
            tag: Tag value.
            children: Child TLV structures.

        Returns:
            Encoded TLV bytes.
        """
        # Encode all children
        value = b"".join(child.to_bytes() for child in children)
        return TLVParser.build(tag, value)

    @staticmethod
    def get_value(data: Union[bytes, str], tag: int) -> Optional[bytes]:
        """Get value for a specific tag from TLV data.

        Args:
            data: TLV data.
            tag: Tag to find.

        Returns:
            Value bytes if found, None otherwise.
        """
        try:
            tlvs = TLVParser.parse_all(data)
            for tlv in tlvs:
                if tlv.tag == tag:
                    return tlv.value
                # Search in children recursively
                found = tlv.find_recursive(tag)
                if found:
                    return found.value
            return None
        except TLVParseError:
            return None


# =============================================================================
# Common TLV Tags
# =============================================================================


class Tags:
    """Common TLV tags used in smart card applications."""

    # ISO 7816-4 / EMV
    FCI_TEMPLATE = 0x6F
    FCI_PROPRIETARY = 0xA5
    DF_NAME = 0x84
    FCI_ISSUER_DISCRETIONARY = 0xBF0C

    # GlobalPlatform
    GP_REGISTRY = 0xE3
    GP_AID = 0x4F
    GP_LIFECYCLE = 0xC5
    GP_PRIVILEGES = 0xC6
    GP_EXECUTABLE_AID = 0xC4
    GP_ASSOCIATED_SD = 0xCC

    # UICC/SIM specific
    ICCID = 0x2FE2  # File ID, not a TLV tag
    IMSI = 0x6F07  # File ID

    # BER-TLV common
    SEQUENCE = 0x30
    SET = 0x31
    OCTET_STRING = 0x04
    UTF8_STRING = 0x0C
    PRINTABLE_STRING = 0x13
    IA5_STRING = 0x16
    INTEGER = 0x02
    BOOLEAN = 0x01
    BIT_STRING = 0x03
    OBJECT_IDENTIFIER = 0x06
    NULL = 0x05
    CONTEXT_0 = 0xA0
    CONTEXT_1 = 0xA1
    CONTEXT_2 = 0xA2
    CONTEXT_3 = 0xA3
