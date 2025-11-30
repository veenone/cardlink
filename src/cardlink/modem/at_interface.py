"""AT Interface for Modem Controller.

This module provides the AT command interface for sending commands
to the modem and parsing responses, including URC handling.
"""

import asyncio
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from cardlink.modem.exceptions import (
    ATCommandError,
    ATTimeoutError,
    CMEError,
    CMSError,
    SerialPortError,
)
from cardlink.modem.models import ATResponse, ATResult
from cardlink.modem.serial_client import SerialClient

logger = logging.getLogger(__name__)

# AT command terminators
AT_COMMAND_TERMINATOR = b"\r\n"
AT_RESPONSE_TERMINATORS = [b"\r\nOK\r\n", b"\r\nERROR\r\n", b"+CME ERROR:", b"+CMS ERROR:"]

# Response parsing patterns
RESPONSE_OK = re.compile(r"^OK$", re.MULTILINE)
RESPONSE_ERROR = re.compile(r"^ERROR$", re.MULTILINE)
RESPONSE_CME_ERROR = re.compile(r"^\+CME ERROR:\s*(\d+)", re.MULTILINE)
RESPONSE_CMS_ERROR = re.compile(r"^\+CMS ERROR:\s*(\d+)", re.MULTILINE)

# URC indicator patterns (lines starting with + that are not command responses)
URC_INDICATOR = re.compile(r"^\+[A-Z]+:")

# Default timeouts
DEFAULT_COMMAND_TIMEOUT = 5.0
LONG_COMMAND_TIMEOUT = 30.0  # For network operations
VERY_LONG_TIMEOUT = 180.0  # For operations like network scan

# Commands that need longer timeouts
LONG_TIMEOUT_COMMANDS = {
    "AT+COPS": LONG_COMMAND_TIMEOUT,
    "AT+COPS?": LONG_COMMAND_TIMEOUT,
    "AT+CGATT": LONG_COMMAND_TIMEOUT,
    "AT+CGACT": LONG_COMMAND_TIMEOUT,
    "AT+QSCAN": VERY_LONG_TIMEOUT,
    "AT+QPING": LONG_COMMAND_TIMEOUT,
    "AT+CMGS": 60.0,  # SMS sending
}


class ATInterface:
    """AT command interface for modem communication.

    Provides command sending, response parsing, and URC handling.

    Example:
        >>> client = SerialClient("/dev/ttyUSB2")
        >>> await client.open()
        >>> at = ATInterface(client)
        >>> await at.start_urc_monitoring()
        >>>
        >>> response = await at.send_command("ATI")
        >>> print(response.data)
        >>>
        >>> await at.stop_urc_monitoring()
    """

    def __init__(
        self,
        serial_client: SerialClient,
        echo_enabled: bool = True,
    ):
        """Initialize AT interface.

        Args:
            serial_client: Serial client for communication.
            echo_enabled: Whether modem echoes commands (default: True).
        """
        self.serial = serial_client
        self.echo_enabled = echo_enabled

        # URC handling
        self._urc_handlers: Dict[str, List[Tuple[Pattern, Callable]]] = {}
        self._urc_monitoring = False
        self._urc_task: Optional[asyncio.Task] = None
        self._urc_queue: asyncio.Queue = asyncio.Queue()

        # Command serialization
        self._command_lock = asyncio.Lock()

    async def send_command(
        self,
        command: str,
        timeout: Optional[float] = None,
        expect_response: bool = True,
        check_error: bool = True,
    ) -> ATResponse:
        """Send AT command and return response.

        Args:
            command: AT command to send (with or without AT prefix).
            timeout: Command timeout in seconds (auto-detected if None).
            expect_response: Whether to wait for response.
            check_error: Whether to raise exception on error response.

        Returns:
            ATResponse with parsed result.

        Raises:
            ATCommandError: If command fails and check_error is True.
            ATTimeoutError: If command times out.
            CMEError: If +CME ERROR response.
            CMSError: If +CMS ERROR response.
        """
        # Ensure command starts with AT
        if not command.upper().startswith("AT"):
            command = "AT" + command

        # Determine timeout
        if timeout is None:
            timeout = self._get_command_timeout(command)

        async with self._command_lock:
            return await self._send_command_locked(
                command, timeout, expect_response, check_error
            )

    async def _send_command_locked(
        self,
        command: str,
        timeout: float,
        expect_response: bool,
        check_error: bool,
    ) -> ATResponse:
        """Send command (with lock already held)."""
        logger.debug("Sending AT command: %s (timeout=%s)", command, timeout)

        try:
            # Clear any pending data
            await self.serial.read_available()

            # Send command
            cmd_bytes = command.encode("utf-8") + AT_COMMAND_TERMINATOR
            await self.serial.write(cmd_bytes)

            if not expect_response:
                return ATResponse(
                    command=command,
                    raw_response="",
                    result=ATResult.OK,
                    data=[],
                )

            # Read response
            raw_response = await self._read_response(timeout)

            # Parse response
            response = self._parse_response(command, raw_response)

            # Check for errors
            if check_error:
                self._check_response_error(response)

            return response

        except SerialPortError as e:
            raise ATCommandError(command, str(e))

    async def _read_response(self, timeout: float) -> str:
        """Read AT command response."""
        response_data = bytearray()
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise ATTimeoutError("", timeout)

            try:
                # Read available data
                chunk = await asyncio.wait_for(
                    self.serial.read(1024),
                    timeout=min(remaining, 0.5),
                )
                if chunk:
                    response_data.extend(chunk)

                    # Check for response terminators
                    text = response_data.decode("utf-8", errors="replace")
                    if self._is_response_complete(text):
                        return text

            except asyncio.TimeoutError:
                # Continue reading if time remains
                continue
            except SerialPortError:
                raise

        # Should not reach here
        return response_data.decode("utf-8", errors="replace")

    def _is_response_complete(self, response: str) -> bool:
        """Check if response is complete (ends with OK, ERROR, etc.)."""
        # Check for standard terminators
        if RESPONSE_OK.search(response):
            return True
        if RESPONSE_ERROR.search(response):
            return True
        if RESPONSE_CME_ERROR.search(response):
            # CME ERROR may have description after code
            if "\r\n" in response.split("+CME ERROR:")[-1]:
                return True
        if RESPONSE_CMS_ERROR.search(response):
            if "\r\n" in response.split("+CMS ERROR:")[-1]:
                return True

        return False

    def _parse_response(self, command: str, raw_response: str) -> ATResponse:
        """Parse AT command response."""
        lines = raw_response.strip().split("\r\n")
        lines = [line.strip() for line in lines if line.strip()]

        # Remove echo if present
        if self.echo_enabled and lines and lines[0].upper() == command.upper():
            lines = lines[1:]

        # Filter out URCs (put them in queue for processing)
        data_lines = []
        for line in lines:
            if self._is_urc(line):
                # Queue URC for processing
                asyncio.create_task(self._queue_urc(line))
            elif line not in ("OK", "ERROR") and not line.startswith("+CME ERROR:") and not line.startswith("+CMS ERROR:"):
                data_lines.append(line)

        # Determine result
        result = ATResult.OK
        error_code = None
        error_message = None

        if RESPONSE_ERROR.search(raw_response):
            result = ATResult.ERROR
            error_message = "ERROR"

        cme_match = RESPONSE_CME_ERROR.search(raw_response)
        if cme_match:
            result = ATResult.CME_ERROR
            error_code = int(cme_match.group(1))

        cms_match = RESPONSE_CMS_ERROR.search(raw_response)
        if cms_match:
            result = ATResult.CMS_ERROR
            error_code = int(cms_match.group(1))

        return ATResponse(
            command=command,
            raw_response=raw_response,
            result=result,
            data=data_lines,
            error_code=error_code,
            error_message=error_message,
        )

    def _check_response_error(self, response: ATResponse) -> None:
        """Raise exception if response indicates error."""
        if response.result == ATResult.CME_ERROR:
            raise CMEError(
                response.error_code or 100,
                response.command,
                response.raw_response,
            )

        if response.result == ATResult.CMS_ERROR:
            raise CMSError(
                response.error_code or 500,
                response.command,
                response.raw_response,
            )

        if response.result == ATResult.ERROR:
            raise ATCommandError(
                response.command,
                "Command returned ERROR",
                response.raw_response,
            )

    def _is_urc(self, line: str) -> bool:
        """Check if line is an unsolicited result code."""
        # URCs start with + followed by uppercase letters and :
        # But we need to filter out expected response prefixes
        if not URC_INDICATOR.match(line):
            return False

        # List of prefixes that are command responses, not URCs
        response_prefixes = [
            "+CGMI:",
            "+CGMM:",
            "+CGMR:",
            "+CGSN:",
            "+CSQ:",
            "+CREG:",
            "+CEREG:",
            "+COPS:",
            "+CPIN:",
            "+CCID:",
            "+QCCID:",
            "+CIMI:",
            "+CNUM:",
            "+CGDCONT:",
            "+CGACT:",
            "+CGPADDR:",
            "+CMGS:",
            "+CMGF:",
            "+QCSQ:",
            "+QENG:",
            "+QCFG:",
        ]

        # If this looks like a response we're expecting, it's not a URC
        # URCs are typically unsolicited (network events, incoming calls, etc.)
        # Context-dependent: during command, prefix is response; otherwise, URC

        # For now, treat as non-URC if it matches known response patterns
        # Real URC detection should be done in the monitoring task
        return False

    def _get_command_timeout(self, command: str) -> float:
        """Get appropriate timeout for command."""
        cmd_upper = command.upper()

        for prefix, timeout in LONG_TIMEOUT_COMMANDS.items():
            if cmd_upper.startswith(prefix):
                return timeout

        return DEFAULT_COMMAND_TIMEOUT

    async def send_raw(self, data: bytes) -> None:
        """Send raw bytes without processing.

        Used for PDU mode operations where we send hex-encoded data
        followed by Ctrl+Z.

        Args:
            data: Raw bytes to send.
        """
        async with self._command_lock:
            await self.serial.write(data)
            logger.debug("Sent raw data: %r", data)

    async def read_until_prompt(
        self,
        prompt: bytes = b">",
        timeout: float = 5.0,
    ) -> bool:
        """Wait for prompt character (e.g., > for SMS PDU entry).

        Args:
            prompt: Prompt character to wait for.
            timeout: Timeout in seconds.

        Returns:
            True if prompt received, False otherwise.
        """
        try:
            await self.serial.read_until(prompt, timeout=timeout)
            return True
        except SerialPortError:
            return False

    # =========================================================================
    # URC Monitoring
    # =========================================================================

    async def start_urc_monitoring(self) -> None:
        """Start background URC monitoring."""
        if self._urc_monitoring:
            return

        self._urc_monitoring = True
        self._urc_task = asyncio.create_task(self._urc_monitor_loop())
        logger.debug("Started URC monitoring")

    async def stop_urc_monitoring(self) -> None:
        """Stop background URC monitoring."""
        self._urc_monitoring = False

        if self._urc_task:
            self._urc_task.cancel()
            try:
                await self._urc_task
            except asyncio.CancelledError:
                pass
            self._urc_task = None

        logger.debug("Stopped URC monitoring")

    async def _urc_monitor_loop(self) -> None:
        """Background task for monitoring URCs."""
        while self._urc_monitoring:
            try:
                # Process any queued URCs
                while not self._urc_queue.empty():
                    try:
                        line = self._urc_queue.get_nowait()
                        await self._process_urc(line)
                    except asyncio.QueueEmpty:
                        break

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in URC monitor: %s", e)
                await asyncio.sleep(1.0)

    async def _queue_urc(self, line: str) -> None:
        """Queue a URC line for processing."""
        await self._urc_queue.put(line)

    async def _process_urc(self, line: str) -> None:
        """Process a URC line by calling registered handlers."""
        for pattern, callback in self._get_all_handlers():
            match = pattern.search(line)
            if match:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(line, match)
                    else:
                        callback(line, match)
                except Exception as e:
                    logger.error("Error in URC handler for %r: %s", line, e)

    def _get_all_handlers(self) -> List[Tuple[Pattern, Callable]]:
        """Get all registered URC handlers."""
        handlers = []
        for handler_list in self._urc_handlers.values():
            handlers.extend(handler_list)
        return handlers

    def register_urc_handler(
        self,
        pattern: str,
        callback: Callable[[str, re.Match], Any],
        name: Optional[str] = None,
    ) -> None:
        """Register handler for specific URC pattern.

        Args:
            pattern: Regex pattern to match URC.
            callback: Callback function (line, match) -> None.
            name: Optional name for handler group.
        """
        compiled = re.compile(pattern)
        group = name or "default"

        if group not in self._urc_handlers:
            self._urc_handlers[group] = []

        self._urc_handlers[group].append((compiled, callback))
        logger.debug("Registered URC handler: %s -> %s", pattern, callback.__name__)

    def unregister_urc_handlers(self, name: str) -> None:
        """Unregister all handlers in a group.

        Args:
            name: Handler group name.
        """
        if name in self._urc_handlers:
            del self._urc_handlers[name]
            logger.debug("Unregistered URC handlers: %s", name)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def check_alive(self) -> bool:
        """Check if modem is responding.

        Returns:
            True if modem responds to AT command.
        """
        try:
            response = await self.send_command("AT", timeout=2.0, check_error=False)
            return response.success
        except (ATCommandError, ATTimeoutError):
            return False

    async def disable_echo(self) -> bool:
        """Disable command echo (ATE0).

        Returns:
            True if successful.
        """
        try:
            response = await self.send_command("ATE0", check_error=False)
            if response.success:
                self.echo_enabled = False
                return True
        except (ATCommandError, ATTimeoutError):
            pass
        return False

    async def enable_echo(self) -> bool:
        """Enable command echo (ATE1).

        Returns:
            True if successful.
        """
        try:
            response = await self.send_command("ATE1", check_error=False)
            if response.success:
                self.echo_enabled = True
                return True
        except (ATCommandError, ATTimeoutError):
            pass
        return False

    async def set_verbose_errors(self, verbose: bool = True) -> bool:
        """Set verbose error reporting (AT+CMEE).

        Args:
            verbose: True for verbose, False for numeric codes.

        Returns:
            True if successful.
        """
        mode = 2 if verbose else 1
        try:
            response = await self.send_command(f"AT+CMEE={mode}", check_error=False)
            return response.success
        except (ATCommandError, ATTimeoutError):
            return False

    def __repr__(self) -> str:
        """String representation."""
        return f"ATInterface(serial={self.serial!r})"
