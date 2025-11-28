"""Logcat parser for extracting structured events from Android logs.

This module provides the LogcatParser class for parsing Android logcat
output and extracting BIP events and other relevant information.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from gp_ota_tester.phone.models import BIPEvent, BIPEventType, LogcatEntry

logger = logging.getLogger(__name__)


class LogcatParser:
    """Parser for Android logcat output.

    This class parses logcat lines into structured events and identifies
    BIP (Bearer Independent Protocol) events from STK/CAT logs.

    Supported log formats:
    - threadtime: "MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message"
    - brief: "LEVEL/TAG(PID): message"
    - time: "MM-DD HH:MM:SS.mmm LEVEL/TAG(PID): message"

    BIP event patterns detected:
    - OPEN CHANNEL commands
    - CLOSE CHANNEL commands
    - SEND DATA commands
    - RECEIVE DATA commands
    - Channel status events

    Example:
        ```python
        parser = LogcatParser()

        # Parse a log line
        entry = parser.parse_line("01-15 12:34:56.789 1234 5678 D CAT: Open Channel")
        if entry:
            print(f"[{entry.level}] {entry.tag}: {entry.message}")

        # Check for BIP events
        if parser.is_bip_event(entry):
            bip = parser.extract_bip_event(entry)
            print(f"BIP Event: {bip.event_type}")
        ```
    """

    # Regex patterns for different logcat formats
    THREADTIME_PATTERN = re.compile(
        r"^(?P<month>\d{2})-(?P<day>\d{2})\s+"
        r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<msec>\d{3})\s+"
        r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
        r"(?P<level>[VDIWEF])\s+"
        r"(?P<tag>[^:]+):\s*"
        r"(?P<message>.*)"
    )

    BRIEF_PATTERN = re.compile(
        r"^(?P<level>[VDIWEF])/(?P<tag>[^\(]+)\(\s*(?P<pid>\d+)\):\s*(?P<message>.*)"
    )

    TIME_PATTERN = re.compile(
        r"^(?P<month>\d{2})-(?P<day>\d{2})\s+"
        r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<msec>\d{3})\s+"
        r"(?P<level>[VDIWEF])/(?P<tag>[^\(]+)\(\s*(?P<pid>\d+)\):\s*"
        r"(?P<message>.*)"
    )

    # Tags relevant to BIP/STK/CAT
    BIP_TAGS = {
        "CAT",
        "StkApp",
        "CatService",
        "STK",
        "RILJ",
        "RIL",
        "Telephony",
        "IccSmsInterfaceManager",
        "SIMRecords",
        "UiccCard",
        "UiccController",
        "GsmDataConnectionTracker",
        "CatCmdMessage",
        "BipProxy",
        "BipService",
        "OpenChannelParams",
        "SendDataParams",
        "ChannelManager",
    }

    # BIP event patterns
    BIP_PATTERNS = {
        BIPEventType.OPEN_CHANNEL: [
            re.compile(r"open.?channel", re.IGNORECASE),
            re.compile(r"cmdType.*OPEN_CHANNEL", re.IGNORECASE),
            re.compile(r"proactive.*OPEN", re.IGNORECASE),
            re.compile(r"BIP.*open", re.IGNORECASE),
        ],
        BIPEventType.CLOSE_CHANNEL: [
            re.compile(r"close.?channel", re.IGNORECASE),
            re.compile(r"cmdType.*CLOSE_CHANNEL", re.IGNORECASE),
            re.compile(r"proactive.*CLOSE", re.IGNORECASE),
            re.compile(r"BIP.*close", re.IGNORECASE),
        ],
        BIPEventType.SEND_DATA: [
            re.compile(r"send.?data", re.IGNORECASE),
            re.compile(r"cmdType.*SEND_DATA", re.IGNORECASE),
            re.compile(r"proactive.*SEND.*DATA", re.IGNORECASE),
            re.compile(r"BIP.*send", re.IGNORECASE),
        ],
        BIPEventType.RECEIVE_DATA: [
            re.compile(r"receive.?data", re.IGNORECASE),
            re.compile(r"cmdType.*RECEIVE_DATA", re.IGNORECASE),
            re.compile(r"proactive.*RECEIVE.*DATA", re.IGNORECASE),
            re.compile(r"BIP.*receive", re.IGNORECASE),
        ],
        BIPEventType.GET_CHANNEL_STATUS: [
            re.compile(r"get.?channel.?status", re.IGNORECASE),
            re.compile(r"cmdType.*GET_CHANNEL_STATUS", re.IGNORECASE),
            re.compile(r"channel.?status", re.IGNORECASE),
        ],
        BIPEventType.DATA_AVAILABLE: [
            re.compile(r"data.?available", re.IGNORECASE),
            re.compile(r"EVENT_DATA_AVAILABLE", re.IGNORECASE),
        ],
        BIPEventType.CHANNEL_STATUS: [
            re.compile(r"channel.?status.*event", re.IGNORECASE),
            re.compile(r"EVENT_CHANNEL_STATUS", re.IGNORECASE),
        ],
    }

    # Patterns for extracting BIP parameters
    ADDRESS_PATTERN = re.compile(
        r"(?:address|host|server|destination)[:\s=]*[\"']?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\S+\.\S+)[\"']?",
        re.IGNORECASE,
    )
    PORT_PATTERN = re.compile(
        r"(?:port)[:\s=]*(\d{1,5})",
        re.IGNORECASE,
    )
    CHANNEL_ID_PATTERN = re.compile(
        r"(?:channel.?id|cid)[:\s=]*(\d+)",
        re.IGNORECASE,
    )
    DATA_LENGTH_PATTERN = re.compile(
        r"(?:length|size|bytes)[:\s=]*(\d+)",
        re.IGNORECASE,
    )
    BEARER_PATTERN = re.compile(
        r"(?:bearer|type)[:\s=]*[\"']?(\w+)[\"']?",
        re.IGNORECASE,
    )

    def __init__(self):
        """Initialize logcat parser."""
        self._current_year = datetime.now().year

    def parse_line(self, line: str) -> Optional[LogcatEntry]:
        """Parse a logcat line into a structured entry.

        Args:
            line: Raw logcat line.

        Returns:
            LogcatEntry if successfully parsed, None otherwise.
        """
        if not line or not line.strip():
            return None

        line = line.strip()

        # Try threadtime format first (most common)
        match = self.THREADTIME_PATTERN.match(line)
        if match:
            return self._create_entry_from_match(match, line)

        # Try time format
        match = self.TIME_PATTERN.match(line)
        if match:
            return self._create_entry_from_match(match, line)

        # Try brief format
        match = self.BRIEF_PATTERN.match(line)
        if match:
            return self._create_entry_from_brief_match(match, line)

        return None

    def _create_entry_from_match(
        self,
        match: re.Match,
        raw_line: str,
    ) -> LogcatEntry:
        """Create LogcatEntry from regex match with timestamp."""
        groups = match.groupdict()

        # Build timestamp
        try:
            timestamp = datetime(
                year=self._current_year,
                month=int(groups["month"]),
                day=int(groups["day"]),
                hour=int(groups["hour"]),
                minute=int(groups["minute"]),
                second=int(groups["second"]),
                microsecond=int(groups["msec"]) * 1000,
            )
        except (ValueError, KeyError):
            timestamp = datetime.now()

        return LogcatEntry(
            timestamp=timestamp,
            pid=int(groups.get("pid", 0)),
            tid=int(groups.get("tid", 0)),
            level=groups.get("level", "I"),
            tag=groups.get("tag", "").strip(),
            message=groups.get("message", ""),
            raw_line=raw_line,
        )

    def _create_entry_from_brief_match(
        self,
        match: re.Match,
        raw_line: str,
    ) -> LogcatEntry:
        """Create LogcatEntry from brief format match."""
        groups = match.groupdict()

        return LogcatEntry(
            timestamp=datetime.now(),
            pid=int(groups.get("pid", 0)),
            tid=0,
            level=groups.get("level", "I"),
            tag=groups.get("tag", "").strip(),
            message=groups.get("message", ""),
            raw_line=raw_line,
        )

    def is_bip_event(self, entry: Optional[LogcatEntry]) -> bool:
        """Check if a log entry is a BIP-related event.

        Args:
            entry: Parsed logcat entry.

        Returns:
            True if the entry is BIP-related.
        """
        if entry is None:
            return False

        # Check if tag is relevant
        if entry.tag not in self.BIP_TAGS:
            # Also check partial matches
            tag_relevant = any(
                bip_tag.lower() in entry.tag.lower()
                for bip_tag in self.BIP_TAGS
            )
            if not tag_relevant:
                return False

        # Check if message matches any BIP pattern
        for patterns in self.BIP_PATTERNS.values():
            for pattern in patterns:
                if pattern.search(entry.message):
                    return True

        return False

    def extract_bip_event(self, entry: LogcatEntry) -> Optional[BIPEvent]:
        """Extract BIP event details from a log entry.

        Args:
            entry: Parsed logcat entry.

        Returns:
            BIPEvent if extraction successful, None otherwise.
        """
        if not self.is_bip_event(entry):
            return None

        # Determine event type
        event_type = BIPEventType.UNKNOWN
        for etype, patterns in self.BIP_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(entry.message):
                    event_type = etype
                    break
            if event_type != BIPEventType.UNKNOWN:
                break

        # Extract parameters from message
        bip_event = BIPEvent(
            event_type=event_type,
            timestamp=entry.timestamp,
            raw_log=entry.raw_line,
        )

        message = entry.message + " " + entry.raw_line

        # Extract address
        addr_match = self.ADDRESS_PATTERN.search(message)
        if addr_match:
            bip_event.address = addr_match.group(1)

        # Extract port
        port_match = self.PORT_PATTERN.search(message)
        if port_match:
            try:
                bip_event.port = int(port_match.group(1))
            except ValueError:
                pass

        # Extract channel ID
        cid_match = self.CHANNEL_ID_PATTERN.search(message)
        if cid_match:
            try:
                bip_event.channel_id = int(cid_match.group(1))
            except ValueError:
                pass

        # Extract data length
        len_match = self.DATA_LENGTH_PATTERN.search(message)
        if len_match:
            try:
                bip_event.data_length = int(len_match.group(1))
            except ValueError:
                pass

        # Extract bearer type
        bearer_match = self.BEARER_PATTERN.search(message)
        if bearer_match:
            bip_event.bearer_type = bearer_match.group(1)

        return bip_event

    def is_relevant_tag(self, tag: str) -> bool:
        """Check if a tag is relevant for BIP/STK monitoring.

        Args:
            tag: Log tag name.

        Returns:
            True if tag is relevant.
        """
        if tag in self.BIP_TAGS:
            return True
        return any(
            bip_tag.lower() in tag.lower()
            for bip_tag in self.BIP_TAGS
        )

    def get_filter_specs(self) -> list:
        """Get logcat filter specs for BIP-related tags.

        Returns:
            List of filter specs for logcat command.
        """
        filters = ["*:S"]  # Silence all by default
        for tag in self.BIP_TAGS:
            filters.append(f"{tag}:V")  # Verbose for BIP tags
        return filters
