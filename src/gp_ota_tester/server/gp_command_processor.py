"""GlobalPlatform Command Processor.

This module processes GlobalPlatform APDU commands and generates responses.
It supports command routing to specific handlers based on INS code.

Example:
    >>> from gp_ota_tester.server.gp_command_processor import GPCommandProcessor
    >>> processor = GPCommandProcessor(event_emitter)
    >>> response = processor.process_command(apdu, session)

Security Note:
    - Command data is logged in truncated form to avoid exposing sensitive data
    - Full APDU logging should only be enabled for debugging
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from gp_ota_tester.server.event_emitter import (
    EVENT_APDU_RECEIVED,
    EVENT_APDU_SENT,
    EventEmitter,
)
from gp_ota_tester.server.http_handler import APDUCommand, APDUResponse

if TYPE_CHECKING:
    from gp_ota_tester.server.models import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Constants - GlobalPlatform INS Codes
# =============================================================================

# Card Management Commands
INS_SELECT = 0xA4
INS_INSTALL = 0xE6
INS_DELETE = 0xE4
INS_GET_STATUS = 0xF2
INS_SET_STATUS = 0xF0
INS_LOAD = 0xE8

# Secure Channel Commands
INS_INITIALIZE_UPDATE = 0x50
INS_EXTERNAL_AUTHENTICATE = 0x82
INS_BEGIN_RMAC_SESSION = 0x7A
INS_END_RMAC_SESSION = 0x78

# Data Commands
INS_GET_DATA = 0xCA
INS_PUT_DATA = 0xDA
INS_STORE_DATA = 0xE2

# Status Words
SW_SUCCESS = (0x90, 0x00)
SW_MORE_DATA_PREFIX = 0x61  # 61XX - more data available
SW_WRONG_LENGTH = (0x67, 0x00)
SW_SECURITY_NOT_SATISFIED = (0x69, 0x82)
SW_CONDITIONS_NOT_SATISFIED = (0x69, 0x85)
SW_WRONG_DATA = (0x6A, 0x80)
SW_FILE_NOT_FOUND = (0x6A, 0x82)
SW_RECORD_NOT_FOUND = (0x6A, 0x83)
SW_NOT_ENOUGH_MEMORY = (0x6A, 0x84)
SW_WRONG_P1P2 = (0x6A, 0x86)
SW_REFERENCED_DATA_NOT_FOUND = (0x6A, 0x88)
SW_INS_NOT_SUPPORTED = (0x6D, 0x00)
SW_CLA_NOT_SUPPORTED = (0x6E, 0x00)
SW_UNKNOWN = (0x6F, 0x00)

# INS code to name mapping
INS_NAMES: Dict[int, str] = {
    INS_SELECT: "SELECT",
    INS_INSTALL: "INSTALL",
    INS_DELETE: "DELETE",
    INS_GET_STATUS: "GET STATUS",
    INS_SET_STATUS: "SET STATUS",
    INS_LOAD: "LOAD",
    INS_INITIALIZE_UPDATE: "INITIALIZE UPDATE",
    INS_EXTERNAL_AUTHENTICATE: "EXTERNAL AUTHENTICATE",
    INS_BEGIN_RMAC_SESSION: "BEGIN R-MAC SESSION",
    INS_END_RMAC_SESSION: "END R-MAC SESSION",
    INS_GET_DATA: "GET DATA",
    INS_PUT_DATA: "PUT DATA",
    INS_STORE_DATA: "STORE DATA",
}


# =============================================================================
# Response Handler Base Class
# =============================================================================


class ResponseHandler(ABC):
    """Abstract base class for APDU response handlers.

    Each handler implements logic for a specific INS code.

    Example:
        >>> class MyHandler(ResponseHandler):
        ...     def handle(self, apdu, session):
        ...         return APDUResponse(sw1=0x90, sw2=0x00)
    """

    @abstractmethod
    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle an APDU command.

        Args:
            apdu: Parsed APDU command.
            session: Current session context.

        Returns:
            APDUResponse with data and status word.
        """
        pass


# =============================================================================
# Built-in Handlers
# =============================================================================


class SelectHandler(ResponseHandler):
    """Handler for SELECT command (INS 0xA4).

    Simulates card application selection.
    """

    # Common AIDs
    ISD_AID = bytes.fromhex("A000000151000000")  # Issuer Security Domain
    CM_AID = bytes.fromhex("A0000001510000")  # Card Manager

    def __init__(self) -> None:
        """Initialize SELECT handler."""
        self._selected_aid: Optional[bytes] = None

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle SELECT command.

        Args:
            apdu: SELECT APDU command.
            session: Current session.

        Returns:
            APDUResponse with FCI or error status.
        """
        # P1=04: Select by DF name (AID)
        if apdu.p1 == 0x04:
            aid = apdu.data
            self._selected_aid = aid

            logger.debug(
                "SELECT by AID: %s",
                aid.hex().upper() if aid else "empty",
            )

            # Return simple FCI template
            # Tag 6F (FCI Template) containing:
            #   84 (DF Name) - the AID
            #   A5 (Proprietary data) - empty for simplicity
            fci = self._build_fci(aid)
            return APDUResponse(data=fci, sw1=0x90, sw2=0x00)

        # P1=00: Select MF, DF, or EF by file identifier
        elif apdu.p1 == 0x00:
            logger.debug("SELECT by file ID")
            return APDUResponse(sw1=0x90, sw2=0x00)

        else:
            logger.warning("SELECT with unsupported P1=%02X", apdu.p1)
            return APDUResponse(sw1=0x6A, sw2=0x86)  # Wrong P1/P2

    def _build_fci(self, aid: bytes) -> bytes:
        """Build FCI (File Control Information) template.

        Args:
            aid: Application Identifier.

        Returns:
            FCI TLV structure.
        """
        # Build inner content
        # 84 LL AID
        aid_tlv = bytes([0x84, len(aid)]) + aid if aid else b""

        # A5 00 (empty proprietary info)
        prop_tlv = bytes([0xA5, 0x00])

        inner = aid_tlv + prop_tlv

        # Wrap in 6F (FCI template)
        return bytes([0x6F, len(inner)]) + inner

    @property
    def selected_aid(self) -> Optional[bytes]:
        """Get currently selected AID."""
        return self._selected_aid


class InstallHandler(ResponseHandler):
    """Handler for INSTALL command (INS 0xE6).

    Simulates package installation on the card.
    """

    # INSTALL types (P1)
    INSTALL_FOR_LOAD = 0x02
    INSTALL_FOR_INSTALL = 0x04
    INSTALL_FOR_MAKE_SELECTABLE = 0x08
    INSTALL_FOR_INSTALL_AND_MAKE_SELECTABLE = 0x0C
    INSTALL_FOR_EXTRADITION = 0x10
    INSTALL_FOR_REGISTRY_UPDATE = 0x40
    INSTALL_FOR_PERSONALIZATION = 0x20

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle INSTALL command.

        Args:
            apdu: INSTALL APDU command.
            session: Current session.

        Returns:
            APDUResponse indicating install status.
        """
        install_type = apdu.p1

        if install_type == self.INSTALL_FOR_LOAD:
            logger.info("INSTALL for LOAD requested")
            return self._handle_for_load(apdu)

        elif install_type in (
            self.INSTALL_FOR_INSTALL,
            self.INSTALL_FOR_MAKE_SELECTABLE,
            self.INSTALL_FOR_INSTALL_AND_MAKE_SELECTABLE,
        ):
            logger.info("INSTALL for INSTALL/MAKE SELECTABLE requested")
            return self._handle_for_install(apdu)

        elif install_type == self.INSTALL_FOR_EXTRADITION:
            logger.info("INSTALL for EXTRADITION requested")
            return APDUResponse(sw1=0x90, sw2=0x00)

        else:
            logger.warning("INSTALL with unsupported P1=%02X", install_type)
            return APDUResponse(sw1=0x6A, sw2=0x86)

    def _handle_for_load(self, apdu: APDUCommand) -> APDUResponse:
        """Handle INSTALL for LOAD command."""
        # Parse INSTALL for LOAD data
        # Structure: Executable Load File AID length + AID + Security Domain AID length + AID + ...
        if len(apdu.data) < 2:
            return APDUResponse(sw1=0x6A, sw2=0x80)  # Wrong data

        logger.debug("INSTALL for LOAD data: %s...", apdu.data[:16].hex())
        return APDUResponse(sw1=0x90, sw2=0x00)

    def _handle_for_install(self, apdu: APDUCommand) -> APDUResponse:
        """Handle INSTALL for INSTALL command."""
        if len(apdu.data) < 2:
            return APDUResponse(sw1=0x6A, sw2=0x80)

        logger.debug("INSTALL for INSTALL data: %s...", apdu.data[:16].hex())
        return APDUResponse(sw1=0x90, sw2=0x00)


class DeleteHandler(ResponseHandler):
    """Handler for DELETE command (INS 0xE4).

    Simulates deletion of card content.
    """

    # DELETE types (P1)
    DELETE_CARD_CONTENT = 0x00
    DELETE_CARD_CONTENT_AND_RELATED = 0x80

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle DELETE command.

        Args:
            apdu: DELETE APDU command.
            session: Current session.

        Returns:
            APDUResponse indicating delete status.
        """
        # Parse AID from data (TLV format: 4F LL AID)
        if len(apdu.data) < 3 or apdu.data[0] != 0x4F:
            logger.warning("DELETE: Invalid data format")
            return APDUResponse(sw1=0x6A, sw2=0x80)

        aid_len = apdu.data[1]
        if len(apdu.data) < 2 + aid_len:
            return APDUResponse(sw1=0x6A, sw2=0x80)

        aid = apdu.data[2:2 + aid_len]
        logger.info("DELETE AID: %s", aid.hex().upper())

        # Simulate successful deletion
        return APDUResponse(sw1=0x90, sw2=0x00)


class GetStatusHandler(ResponseHandler):
    """Handler for GET STATUS command (INS 0xF2).

    Returns card content and application status.
    """

    # GET STATUS types (P1)
    GET_STATUS_ISD = 0x80  # Issuer Security Domain
    GET_STATUS_APPS = 0x40  # Applications and Security Domains
    GET_STATUS_EXEC_LOAD_FILES = 0x20  # Executable Load Files
    GET_STATUS_EXEC_LOAD_FILES_AND_MODULES = 0x10  # Load Files and Modules

    def __init__(self) -> None:
        """Initialize GET STATUS handler."""
        # Mock data for status responses
        self._applications: List[Dict[str, Any]] = []

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle GET STATUS command.

        Args:
            apdu: GET STATUS APDU command.
            session: Current session.

        Returns:
            APDUResponse with status data.
        """
        status_type = apdu.p1

        if status_type == self.GET_STATUS_ISD:
            logger.debug("GET STATUS: Issuer Security Domain")
            return self._get_isd_status()

        elif status_type == self.GET_STATUS_APPS:
            logger.debug("GET STATUS: Applications")
            return self._get_apps_status()

        elif status_type in (
            self.GET_STATUS_EXEC_LOAD_FILES,
            self.GET_STATUS_EXEC_LOAD_FILES_AND_MODULES,
        ):
            logger.debug("GET STATUS: Executable Load Files")
            return self._get_load_files_status()

        else:
            logger.warning("GET STATUS with unsupported P1=%02X", status_type)
            return APDUResponse(sw1=0x6A, sw2=0x86)

    def _get_isd_status(self) -> APDUResponse:
        """Get Issuer Security Domain status."""
        # Return ISD AID and life cycle state
        # E3 LL (GP Registry Entry)
        #   4F LL AID
        #   9F70 01 LC (Life Cycle State)
        #   C5 01 PP (Privileges)

        isd_aid = bytes.fromhex("A000000151000000")
        lc_state = 0x0F  # SECURED
        privileges = 0x80  # Security Domain

        entry = (
            bytes([0x4F, len(isd_aid)]) + isd_aid +
            bytes([0x9F, 0x70, 0x01, lc_state]) +
            bytes([0xC5, 0x01, privileges])
        )

        data = bytes([0xE3, len(entry)]) + entry
        return APDUResponse(data=data, sw1=0x90, sw2=0x00)

    def _get_apps_status(self) -> APDUResponse:
        """Get applications status."""
        # Return empty list or mock applications
        if not self._applications:
            return APDUResponse(sw1=0x6A, sw2=0x88)  # Referenced data not found

        # Build response with application entries
        data = b""
        for app in self._applications:
            aid = app.get("aid", b"")
            entry = bytes([0x4F, len(aid)]) + aid
            data += bytes([0xE3, len(entry)]) + entry

        return APDUResponse(data=data, sw1=0x90, sw2=0x00)

    def _get_load_files_status(self) -> APDUResponse:
        """Get executable load files status."""
        # Return empty or mock load files
        return APDUResponse(sw1=0x6A, sw2=0x88)  # Referenced data not found

    def add_mock_application(self, aid: bytes, lc_state: int = 0x07) -> None:
        """Add mock application for testing."""
        self._applications.append({"aid": aid, "lc_state": lc_state})


class InitUpdateHandler(ResponseHandler):
    """Handler for INITIALIZE UPDATE command (INS 0x50).

    Part of SCP02/SCP03 secure channel establishment.
    """

    def __init__(self) -> None:
        """Initialize handler with mock data."""
        # Mock key diversification data
        self._key_diversification = bytes.fromhex("0102030405060708090A")
        self._key_info = bytes([0x01, 0x01])  # Key version, SCP identifier
        self._sequence_counter = bytes([0x00, 0x00, 0x00])
        self._card_challenge = bytes.fromhex("0102030405060708")
        self._card_cryptogram = bytes.fromhex("AABBCCDD11223344")

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle INITIALIZE UPDATE command.

        Args:
            apdu: INIT UPDATE APDU command.
            session: Current session.

        Returns:
            APDUResponse with initialization data.
        """
        # Host challenge should be in data field (8 bytes)
        host_challenge = apdu.data[:8] if len(apdu.data) >= 8 else b"\x00" * 8

        logger.debug(
            "INITIALIZE UPDATE: host_challenge=%s",
            host_challenge.hex(),
        )

        # Build response:
        # Key Diversification Data (10 bytes) +
        # Key Information (2 bytes) +
        # Sequence Counter (3 bytes) +
        # Card Challenge (8 bytes) +
        # Card Cryptogram (8 bytes)
        response_data = (
            self._key_diversification +
            self._key_info +
            self._sequence_counter +
            self._card_challenge +
            self._card_cryptogram
        )

        return APDUResponse(data=response_data, sw1=0x90, sw2=0x00)


class ExtAuthHandler(ResponseHandler):
    """Handler for EXTERNAL AUTHENTICATE command (INS 0x82).

    Completes secure channel establishment.
    """

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle EXTERNAL AUTHENTICATE command.

        Args:
            apdu: EXT AUTH APDU command.
            session: Current session.

        Returns:
            APDUResponse indicating authentication status.
        """
        # P1 contains security level
        security_level = apdu.p1
        logger.debug(
            "EXTERNAL AUTHENTICATE: security_level=%02X",
            security_level,
        )

        # Host cryptogram should be in data (8 bytes for SCP02)
        if len(apdu.data) < 8:
            return APDUResponse(sw1=0x67, sw2=0x00)  # Wrong length

        host_cryptogram = apdu.data[:8]
        logger.debug("Host cryptogram: %s", host_cryptogram.hex())

        # In a real implementation, verify the cryptogram
        # For testing, accept any value
        return APDUResponse(sw1=0x90, sw2=0x00)


class DefaultHandler(ResponseHandler):
    """Default handler for unknown commands.

    Returns SW 6D00 (INS not supported).
    """

    def handle(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Handle unknown command.

        Args:
            apdu: Unknown APDU command.
            session: Current session.

        Returns:
            APDUResponse with 6D00 status.
        """
        logger.warning(
            "Unknown command INS=%02X, returning 6D00",
            apdu.ins,
        )
        return APDUResponse(sw1=0x6D, sw2=0x00)


# =============================================================================
# GP Command Processor
# =============================================================================


class GPCommandProcessor:
    """Processes GlobalPlatform APDU commands.

    Routes commands to registered handlers based on INS code,
    emits events for monitoring, and tracks timing.

    Example:
        >>> emitter = EventEmitter()
        >>> processor = GPCommandProcessor(emitter)
        >>>
        >>> # Register custom handler
        >>> processor.register_handler(0xCA, GetDataHandler())
        >>>
        >>> # Process command
        >>> response = processor.process_command(apdu, session)
    """

    def __init__(
        self,
        event_emitter: Optional[EventEmitter] = None,
        register_default_handlers: bool = True,
    ) -> None:
        """Initialize GP Command Processor.

        Args:
            event_emitter: Event emitter for APDU events.
            register_default_handlers: Whether to register built-in handlers.
        """
        self._event_emitter = event_emitter
        self._handlers: Dict[int, ResponseHandler] = {}
        self._default_handler = DefaultHandler()

        # Register built-in handlers
        if register_default_handlers:
            self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register built-in command handlers."""
        self._handlers[INS_SELECT] = SelectHandler()
        self._handlers[INS_INSTALL] = InstallHandler()
        self._handlers[INS_DELETE] = DeleteHandler()
        self._handlers[INS_GET_STATUS] = GetStatusHandler()
        self._handlers[INS_INITIALIZE_UPDATE] = InitUpdateHandler()
        self._handlers[INS_EXTERNAL_AUTHENTICATE] = ExtAuthHandler()

    def register_handler(
        self,
        ins_code: int,
        handler: ResponseHandler,
    ) -> None:
        """Register handler for specific INS code.

        Args:
            ins_code: Instruction byte to handle.
            handler: Handler instance.
        """
        self._handlers[ins_code] = handler
        logger.debug(
            "Registered handler for INS %02X (%s)",
            ins_code,
            INS_NAMES.get(ins_code, "UNKNOWN"),
        )

    def unregister_handler(self, ins_code: int) -> Optional[ResponseHandler]:
        """Unregister handler for INS code.

        Args:
            ins_code: Instruction byte.

        Returns:
            Previously registered handler or None.
        """
        return self._handlers.pop(ins_code, None)

    def get_handler(self, ins_code: int) -> ResponseHandler:
        """Get handler for INS code.

        Args:
            ins_code: Instruction byte.

        Returns:
            Handler for INS code or default handler.
        """
        return self._handlers.get(ins_code, self._default_handler)

    def process_command(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Process APDU command and return response.

        Routes command to appropriate handler, emits events,
        and tracks timing.

        Args:
            apdu: Parsed APDU command.
            session: Current session context.

        Returns:
            APDUResponse from handler.
        """
        start_time = time.monotonic()
        session_id = session.session_id if session else None

        # Log command receipt (truncate data for security)
        command_hex = apdu.raw.hex().upper() if apdu.raw else ""
        command_preview = command_hex[:32] + "..." if len(command_hex) > 32 else command_hex

        logger.debug(
            "APDU received: %s (INS=%02X), data_len=%d, session=%s",
            apdu.command_name,
            apdu.ins,
            len(apdu.data) if apdu.data else 0,
            session_id,
        )

        # Emit received event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_APDU_RECEIVED,
                {
                    "session_id": session_id,
                    "command_name": apdu.command_name,
                    "ins": apdu.ins,
                    "cla": apdu.cla,
                    "p1": apdu.p1,
                    "p2": apdu.p2,
                    "data_length": len(apdu.data) if apdu.data else 0,
                    "command_preview": command_preview,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        # Get handler and process
        handler = self.get_handler(apdu.ins)
        response = handler.handle(apdu, session)

        # Calculate duration
        duration_ms = (time.monotonic() - start_time) * 1000

        # Log response
        response_hex = response.to_bytes().hex().upper()
        response_preview = (
            response_hex[:32] + "..." if len(response_hex) > 32 else response_hex
        )

        logger.debug(
            "APDU response: SW=%s, data_len=%d, duration=%.2fms, session=%s",
            response.status_word,
            len(response.data) if response.data else 0,
            duration_ms,
            session_id,
        )

        # Emit sent event
        if self._event_emitter:
            self._event_emitter.emit(
                EVENT_APDU_SENT,
                {
                    "session_id": session_id,
                    "command_name": apdu.command_name,
                    "ins": apdu.ins,
                    "sw1": response.sw1,
                    "sw2": response.sw2,
                    "status_word": response.status_word,
                    "is_success": response.is_success,
                    "data_length": len(response.data) if response.data else 0,
                    "response_preview": response_preview,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return response

    def get_registered_handlers(self) -> Dict[int, str]:
        """Get map of registered INS codes to handler names.

        Returns:
            Dictionary of INS code to handler class name.
        """
        return {
            ins: type(handler).__name__
            for ins, handler in self._handlers.items()
        }


# =============================================================================
# Mock Command Processor for Testing
# =============================================================================


class MockGPCommandProcessor(GPCommandProcessor):
    """Mock command processor for testing.

    Records processed commands and allows configuring responses.

    Example:
        >>> processor = MockGPCommandProcessor()
        >>> processor.set_response(0xA4, APDUResponse(sw1=0x90, sw2=0x00))
        >>> response = processor.process_command(select_apdu, session)
        >>> assert len(processor.processed_commands) == 1
    """

    def __init__(self) -> None:
        """Initialize mock processor."""
        super().__init__(event_emitter=None, register_default_handlers=False)
        self.processed_commands: List[APDUCommand] = []
        self._configured_responses: Dict[int, APDUResponse] = {}
        self._default_response = APDUResponse(sw1=0x90, sw2=0x00)

    def set_response(self, ins_code: int, response: APDUResponse) -> None:
        """Configure response for specific INS code."""
        self._configured_responses[ins_code] = response

    def set_default_response(self, response: APDUResponse) -> None:
        """Set default response for unconfigured commands."""
        self._default_response = response

    def process_command(
        self,
        apdu: APDUCommand,
        session: Optional["Session"],
    ) -> APDUResponse:
        """Process command with mock behavior."""
        self.processed_commands.append(apdu)

        if apdu.ins in self._configured_responses:
            return self._configured_responses[apdu.ins]

        return self._default_response

    def clear(self) -> None:
        """Clear recorded commands and configured responses."""
        self.processed_commands.clear()
        self._configured_responses.clear()
