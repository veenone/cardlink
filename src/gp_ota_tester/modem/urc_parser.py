"""URC Parser for Modem Controller.

This module parses Unsolicited Result Codes (URCs) from modem
into structured events.
"""

import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from gp_ota_tester.modem.exceptions import URCParseError
from gp_ota_tester.modem.models import (
    NetworkType,
    RegistrationStatus,
    SIMStatus,
    URCEvent,
    URCType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Common URC Patterns
# =============================================================================

# Network registration URCs
CREG_PATTERN = re.compile(r"^\+CREG:\s*(\d)(?:,([0-9A-Fa-f]+),([0-9A-Fa-f]+))?")
CEREG_PATTERN = re.compile(r"^\+CEREG:\s*(\d)(?:,([0-9A-Fa-f]+),([0-9A-Fa-f]+)(?:,(\d+))?)?")

# SIM status URC
CPIN_PATTERN = re.compile(r"^\+CPIN:\s*(.+)")

# Signal quality URC (some modems send this unsolicited)
CSQ_PATTERN = re.compile(r"^\+CSQ:\s*(\d+),(\d+)")

# SMS URCs
CMTI_PATTERN = re.compile(r'^\+CMTI:\s*"([^"]+)",(\d+)')  # New SMS indication
CMT_PATTERN = re.compile(r'^\+CMT:\s*"([^"]+)"')  # SMS received directly

# Call URCs
RING_PATTERN = re.compile(r"^RING$")
NO_CARRIER_PATTERN = re.compile(r"^NO CARRIER$")
CLIP_PATTERN = re.compile(r'^\+CLIP:\s*"([^"]+)"')

# Quectel-specific URCs
QSTK_PATTERN = re.compile(r'^\+QSTK:\s*"?([0-9A-Fa-f]+)"?')  # STK proactive command
QIND_PATTERN = re.compile(r'^\+QIND:\s*"([^"]+)"(?:,(.+))?')  # Various indications
QUSIM_PATTERN = re.compile(r"^\+QUSIM:\s*(\d+)")  # SIM ready indication

# Other URCs
CUSD_PATTERN = re.compile(r'^\+CUSD:\s*(\d)(?:,"([^"]*)")?')  # USSD response


class URCParser:
    """Parses modem URCs into structured events.

    Provides pattern matching and parsing for common URC types,
    with support for custom pattern registration.

    Example:
        >>> parser = URCParser()
        >>>
        >>> event = parser.parse("+CREG: 1,1234,ABCD")
        >>> print(event.type)  # URCType.NETWORK_REGISTRATION
        >>> print(event.data)  # {'stat': 1, 'lac': '1234', 'ci': 'ABCD'}
    """

    def __init__(self):
        """Initialize parser with default patterns."""
        # Pattern: (regex, event_type, parser_function)
        self._patterns: List[Tuple[Pattern, URCType, Callable]] = []

        # Register default patterns
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default URC patterns."""
        # Network registration
        self.register_pattern(
            CREG_PATTERN,
            URCType.NETWORK_REGISTRATION,
            self._parse_creg,
        )
        self.register_pattern(
            CEREG_PATTERN,
            URCType.EPS_REGISTRATION,
            self._parse_cereg,
        )

        # SIM status
        self.register_pattern(
            CPIN_PATTERN,
            URCType.SIM_STATUS,
            self._parse_cpin,
        )

        # Signal
        self.register_pattern(
            CSQ_PATTERN,
            URCType.SIGNAL_CHANGE,
            self._parse_csq,
        )

        # SMS
        self.register_pattern(
            CMTI_PATTERN,
            URCType.SMS_RECEIVED,
            self._parse_cmti,
        )
        self.register_pattern(
            CMT_PATTERN,
            URCType.SMS_RECEIVED,
            self._parse_cmt,
        )

        # Call
        self.register_pattern(
            RING_PATTERN,
            URCType.RING,
            self._parse_ring,
        )
        self.register_pattern(
            CLIP_PATTERN,
            URCType.CALL_STATUS,
            self._parse_clip,
        )

        # Quectel STK
        self.register_pattern(
            QSTK_PATTERN,
            URCType.STK_EVENT,
            self._parse_qstk,
        )
        self.register_pattern(
            QIND_PATTERN,
            URCType.INDICATION,
            self._parse_qind,
        )

    def is_urc(self, line: str) -> bool:
        """Check if line is a URC.

        Args:
            line: Line to check.

        Returns:
            True if line appears to be a URC.
        """
        line = line.strip()

        # Empty lines are not URCs
        if not line:
            return False

        # Check for common URC indicators
        # URCs typically start with + or are specific keywords
        if line.startswith("+"):
            return True

        # Specific keyword URCs
        keyword_urcs = {"RING", "NO CARRIER", "BUSY", "NO ANSWER", "CONNECT"}
        if line in keyword_urcs:
            return True

        return False

    def parse(self, line: str) -> Optional[URCEvent]:
        """Parse URC line into event.

        Args:
            line: URC line to parse.

        Returns:
            URCEvent if successfully parsed, None otherwise.
        """
        line = line.strip()

        if not self.is_urc(line):
            return None

        # Try each registered pattern
        for pattern, event_type, parser in self._patterns:
            match = pattern.match(line)
            if match:
                try:
                    data = parser(match)
                    return URCEvent(
                        type=event_type,
                        timestamp=datetime.now(),
                        raw_line=line,
                        data=data,
                    )
                except Exception as e:
                    logger.warning("Error parsing URC '%s': %s", line, e)

        # Unknown URC
        return URCEvent(
            type=URCType.UNKNOWN,
            timestamp=datetime.now(),
            raw_line=line,
            data={"raw": line},
        )

    def register_pattern(
        self,
        pattern: Pattern,
        event_type: URCType,
        parser: Callable[[re.Match], Dict[str, Any]],
    ) -> None:
        """Register custom URC pattern.

        Args:
            pattern: Compiled regex pattern.
            event_type: Type of event to create.
            parser: Function to parse match into data dict.
        """
        self._patterns.append((pattern, event_type, parser))

    def register_pattern_string(
        self,
        pattern_str: str,
        event_type: URCType,
        parser: Callable[[re.Match], Dict[str, Any]],
    ) -> None:
        """Register custom URC pattern from string.

        Args:
            pattern_str: Regex pattern string.
            event_type: Type of event to create.
            parser: Function to parse match into data dict.
        """
        pattern = re.compile(pattern_str)
        self.register_pattern(pattern, event_type, parser)

    # =========================================================================
    # Default Parsers
    # =========================================================================

    def _parse_creg(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CREG URC."""
        stat = int(match.group(1))
        lac = match.group(2)
        ci = match.group(3)

        return {
            "stat": stat,
            "status": self._registration_status(stat),
            "lac": lac,
            "ci": ci,
        }

    def _parse_cereg(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CEREG URC."""
        stat = int(match.group(1))
        tac = match.group(2)
        ci = match.group(3)
        act = match.group(4)

        return {
            "stat": stat,
            "status": self._registration_status(stat),
            "tac": tac,
            "ci": ci,
            "act": int(act) if act else None,
            "network_type": self._access_technology(int(act)) if act else None,
        }

    def _parse_cpin(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CPIN URC."""
        status_str = match.group(1).strip()

        # Map to SIMStatus enum
        status_map = {
            "READY": SIMStatus.READY,
            "SIM PIN": SIMStatus.SIM_PIN,
            "SIM PUK": SIMStatus.SIM_PUK,
            "SIM PIN2": SIMStatus.SIM_PIN2,
            "SIM PUK2": SIMStatus.SIM_PUK2,
            "PH-SIM PIN": SIMStatus.PH_SIM_PIN,
            "PH-NET PIN": SIMStatus.PH_NET_PIN,
            "PH-NET PUK": SIMStatus.PH_NET_PUK,
            "NOT INSERTED": SIMStatus.NOT_INSERTED,
            "NOT READY": SIMStatus.NOT_READY,
        }

        status = status_map.get(status_str, SIMStatus.ERROR)

        return {
            "status_string": status_str,
            "status": status,
            "ready": status == SIMStatus.READY,
        }

    def _parse_csq(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CSQ URC."""
        rssi = int(match.group(1))
        ber = int(match.group(2))

        # Convert RSSI to dBm
        # 0: -113 dBm or less
        # 1: -111 dBm
        # 2-30: -109 to -53 dBm
        # 31: -51 dBm or greater
        # 99: not known or not detectable
        if rssi == 99:
            rssi_dbm = None
        elif rssi == 0:
            rssi_dbm = -113
        elif rssi == 31:
            rssi_dbm = -51
        else:
            rssi_dbm = -113 + (rssi * 2)

        return {
            "rssi": rssi,
            "rssi_dbm": rssi_dbm,
            "ber": ber,
        }

    def _parse_cmti(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CMTI URC (new SMS indication)."""
        storage = match.group(1)
        index = int(match.group(2))

        return {
            "storage": storage,
            "index": index,
            "type": "indication",
        }

    def _parse_cmt(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CMT URC (SMS received directly)."""
        sender = match.group(1)

        return {
            "sender": sender,
            "type": "direct",
        }

    def _parse_ring(self, match: re.Match) -> Dict[str, Any]:
        """Parse RING URC."""
        return {"ringing": True}

    def _parse_clip(self, match: re.Match) -> Dict[str, Any]:
        """Parse +CLIP URC (caller ID)."""
        number = match.group(1)

        return {
            "number": number,
        }

    def _parse_qstk(self, match: re.Match) -> Dict[str, Any]:
        """Parse +QSTK URC (Quectel STK proactive command)."""
        pdu = match.group(1)

        # Parse basic STK command info
        data = {
            "pdu": pdu,
            "pdu_bytes": bytes.fromhex(pdu) if pdu else b"",
        }

        # Try to extract command type from TLV
        if len(pdu) >= 4:
            try:
                pdu_bytes = bytes.fromhex(pdu)
                if pdu_bytes and len(pdu_bytes) >= 2:
                    # First byte is typically tag, second is length
                    # Proactive command structure varies
                    data["tag"] = pdu_bytes[0]
            except ValueError:
                pass

        return data

    def _parse_qind(self, match: re.Match) -> Dict[str, Any]:
        """Parse +QIND URC (Quectel indication)."""
        indication = match.group(1)
        params = match.group(2)

        data = {
            "indication": indication,
            "params": params,
        }

        # Parse specific indications
        if indication == "SMS DONE":
            data["sms_ready"] = True
        elif indication == "PB DONE":
            data["phonebook_ready"] = True
        elif indication == "csq":
            # +QIND: "csq",<rssi>,<ber>
            if params:
                parts = params.split(",")
                if len(parts) >= 2:
                    data["rssi"] = int(parts[0])
                    data["ber"] = int(parts[1])

        return data

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _registration_status(self, stat: int) -> RegistrationStatus:
        """Convert registration status code to enum."""
        try:
            return RegistrationStatus(stat)
        except ValueError:
            return RegistrationStatus.UNKNOWN

    def _access_technology(self, act: int) -> NetworkType:
        """Convert access technology code to NetworkType."""
        act_map = {
            0: NetworkType.GSM,
            1: NetworkType.GSM,  # GSM Compact
            2: NetworkType.UMTS,
            3: NetworkType.EDGE,
            4: NetworkType.HSDPA,
            5: NetworkType.HSUPA,
            6: NetworkType.HSPA,
            7: NetworkType.LTE,
            8: NetworkType.LTE_CA,  # EC-GSM-IoT
            9: NetworkType.LTE,  # E-UTRAN (NB-S1 mode)
            10: NetworkType.NR5G_NSA,
            11: NetworkType.NR5G_SA,
            12: NetworkType.NR5G_NSA,  # NG-RAN
            13: NetworkType.NR5G_SA,  # E-UTRA-NR dual connectivity
        }
        return act_map.get(act, NetworkType.UNKNOWN)


# =============================================================================
# Default Parser Instance
# =============================================================================

# Global parser instance for convenience
_default_parser: Optional[URCParser] = None


def get_parser() -> URCParser:
    """Get default URC parser instance."""
    global _default_parser
    if _default_parser is None:
        _default_parser = URCParser()
    return _default_parser


def parse_urc(line: str) -> Optional[URCEvent]:
    """Parse URC line using default parser.

    Args:
        line: URC line to parse.

    Returns:
        URCEvent if successfully parsed, None otherwise.
    """
    return get_parser().parse(line)


def is_urc(line: str) -> bool:
    """Check if line is a URC using default parser.

    Args:
        line: Line to check.

    Returns:
        True if line appears to be a URC.
    """
    return get_parser().is_urc(line)
