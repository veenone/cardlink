"""AT Command Interface for Android devices.

This module provides the ATInterface class for sending AT commands
to the modem on Android devices through various transport methods.
"""

import logging
import re
import time
from typing import Optional

from gp_ota_tester.phone.adb_client import ADBClient
from gp_ota_tester.phone.exceptions import (
    ATCommandError,
    ATTimeoutError,
    ATUnavailableError,
    RootRequiredError,
)
from gp_ota_tester.phone.models import ATMethod, ATResponse, ATResult

logger = logging.getLogger(__name__)


class ATInterface:
    """Interface for sending AT commands to Android device modems.

    This class supports multiple methods for sending AT commands:
    - SERVICE_CALL: Via Android service call (most compatible)
    - DIALER_CODE: Via dialer special codes (limited commands)
    - DEVICE_NODE: Direct to modem device node (requires root)
    - RIL_REQUEST: Via RIL daemon

    The interface auto-detects the best available method.

    Args:
        adb_client: ADBClient instance.
        serial: Device serial number.
        default_timeout: Default command timeout in seconds.

    Example:
        ```python
        client = ADBClient()
        at = ATInterface(client, "device123")

        # Check availability
        if await at.is_available():
            # Send AT command
            response = await at.send_command("AT+CPIN?")
            if response.is_ok:
                print(response.data)

            # Use helper methods
            status = await at.get_sim_status()
            print(f"SIM Status: {status}")
        ```
    """

    # Common modem device nodes on Android
    DEVICE_NODES = [
        "/dev/smd0",
        "/dev/smd7",
        "/dev/smd11",
        "/dev/ttyACM0",
        "/dev/ttyUSB0",
        "/dev/ttyGS0",
        "/dev/umts_atc0",
        "/dev/umts_router0",
    ]

    def __init__(
        self,
        adb_client: ADBClient,
        serial: str,
        default_timeout: float = 5.0,
    ):
        """Initialize AT interface.

        Args:
            adb_client: ADBClient instance.
            serial: Device serial number.
            default_timeout: Default command timeout.
        """
        self._client = adb_client
        self._serial = serial
        self._default_timeout = default_timeout

        # Cached method detection
        self._detected_method: Optional[ATMethod] = None
        self._device_node: Optional[str] = None
        self._requires_root: Optional[bool] = None

    async def is_available(self) -> bool:
        """Check if AT interface is available on the device.

        Returns:
            True if any AT method is available.
        """
        method = await self._detect_method()
        return method != ATMethod.UNAVAILABLE

    async def requires_root(self) -> bool:
        """Check if the available AT method requires root.

        Returns:
            True if root is required.
        """
        if self._requires_root is not None:
            return self._requires_root

        method = await self._detect_method()

        # Only device node method typically requires root
        self._requires_root = method == ATMethod.DEVICE_NODE
        return self._requires_root

    async def get_method(self) -> ATMethod:
        """Get the detected AT command method.

        Returns:
            The ATMethod that will be used for commands.
        """
        return await self._detect_method()

    async def _detect_method(self) -> ATMethod:
        """Detect the best available AT method.

        Returns:
            Detected ATMethod.
        """
        if self._detected_method is not None:
            return self._detected_method

        # Try service call method first (most compatible)
        if await self._test_service_call():
            self._detected_method = ATMethod.SERVICE_CALL
            logger.info(f"AT interface: using SERVICE_CALL method")
            return self._detected_method

        # Try device node method (requires root)
        node = await self._find_device_node()
        if node:
            self._device_node = node
            self._detected_method = ATMethod.DEVICE_NODE
            logger.info(f"AT interface: using DEVICE_NODE method ({node})")
            return self._detected_method

        # No method available
        self._detected_method = ATMethod.UNAVAILABLE
        logger.warning("AT interface: no method available")
        return self._detected_method

    async def _test_service_call(self) -> bool:
        """Test if service call method works."""
        try:
            # Try to call phone service
            output = await self._client.shell(
                "service call phone 1",
                self._serial,
                check_error=False,
            )
            # If we get a parcel result, the service is available
            return "Parcel" in output or "Result" in output
        except Exception:
            return False

    async def _find_device_node(self) -> Optional[str]:
        """Find a working modem device node."""
        # Check if we have root
        is_root = await self._client.is_root(self._serial)
        if not is_root:
            # Try to get root
            if not await self._client.root(self._serial):
                return None

        for node in self.DEVICE_NODES:
            try:
                # Check if node exists and is readable
                output = await self._client.shell(
                    f"test -c {node} && echo 'exists'",
                    self._serial,
                    check_error=False,
                )
                if "exists" in output:
                    # Try to send a test command
                    test_result = await self._send_via_device_node(node, "AT", timeout=2.0)
                    if test_result.is_ok or "OK" in test_result.raw_response:
                        return node
            except Exception:
                continue

        return None

    async def send_command(
        self,
        command: str,
        timeout: Optional[float] = None,
    ) -> ATResponse:
        """Send an AT command and get the response.

        Args:
            command: AT command to send (with or without "AT" prefix).
            timeout: Command timeout in seconds.

        Returns:
            ATResponse with result and data.

        Raises:
            ATUnavailableError: If no AT method is available.
            ATTimeoutError: If command times out.
            ATCommandError: If command fails.
        """
        method = await self._detect_method()

        if method == ATMethod.UNAVAILABLE:
            raise ATUnavailableError(self._serial, "No AT method available")

        timeout = timeout or self._default_timeout

        # Ensure command has AT prefix
        if not command.upper().startswith("AT"):
            command = "AT" + command

        start_time = time.time()

        try:
            if method == ATMethod.SERVICE_CALL:
                response = await self._send_via_service_call(command, timeout)
            elif method == ATMethod.DEVICE_NODE:
                if self._device_node is None:
                    raise ATUnavailableError(self._serial, "Device node not found")
                response = await self._send_via_device_node(
                    self._device_node,
                    command,
                    timeout,
                )
            else:
                raise ATUnavailableError(self._serial, f"Unsupported method: {method}")

            response.duration_ms = (time.time() - start_time) * 1000
            return response

        except ATTimeoutError:
            raise
        except ATCommandError:
            raise
        except Exception as e:
            raise ATCommandError(command, str(e))

    async def _send_via_service_call(
        self,
        command: str,
        timeout: float,
    ) -> ATResponse:
        """Send AT command via Android service call.

        This uses the phone service's invokeOemRilRequestRaw method.
        """
        # Encode command as hex string for service call
        hex_command = command.encode().hex()

        # Build service call
        # Method 115 is invokeOemRilRequestStrings on some Android versions
        # This varies by Android version and OEM
        shell_cmd = (
            f"service call phone 115 i32 1 i32 {len(command)} "
            f"s16 '{command}'"
        )

        try:
            output = await self._client.shell(
                shell_cmd,
                self._serial,
                timeout=timeout,
                check_error=False,
            )

            return self._parse_service_call_response(output, command)

        except Exception as e:
            # Try alternative method numbers
            for method_num in [114, 116, 141, 142]:
                try:
                    shell_cmd = f"service call phone {method_num} s16 '{command}'"
                    output = await self._client.shell(
                        shell_cmd,
                        self._serial,
                        timeout=timeout,
                        check_error=False,
                    )
                    if "error" not in output.lower():
                        return self._parse_service_call_response(output, command)
                except Exception:
                    continue

            return ATResponse(
                result=ATResult.ERROR,
                raw_response=str(e),
                error_message=str(e),
            )

    def _parse_service_call_response(
        self,
        output: str,
        command: str,
    ) -> ATResponse:
        """Parse response from service call."""
        response = ATResponse(
            result=ATResult.ERROR,
            raw_response=output,
        )

        # Check for success patterns
        if "OK" in output.upper():
            response.result = ATResult.OK

        # Extract response data from parcel
        # Format: Result: Parcel(00000000 00000004 'data' ...)
        data_pattern = re.compile(r"'([^']*)'")
        matches = data_pattern.findall(output)
        if matches:
            response.response_lines = [m.strip() for m in matches if m.strip()]

        # Check for CME/CMS errors
        cme_match = re.search(r"\+CME ERROR:\s*(\d+)", output, re.IGNORECASE)
        if cme_match:
            response.result = ATResult.CME_ERROR
            response.error_code = int(cme_match.group(1))

        cms_match = re.search(r"\+CMS ERROR:\s*(\d+)", output, re.IGNORECASE)
        if cms_match:
            response.result = ATResult.CMS_ERROR
            response.error_code = int(cms_match.group(1))

        if "ERROR" in output.upper() and response.result == ATResult.ERROR:
            response.error_message = "Command returned ERROR"

        return response

    async def _send_via_device_node(
        self,
        node: str,
        command: str,
        timeout: float,
    ) -> ATResponse:
        """Send AT command via device node.

        This requires root access.
        """
        # Ensure command ends with CR
        if not command.endswith("\r"):
            command = command + "\r"

        # Use echo and cat with timeout
        shell_cmd = (
            f"echo -e '{command}' > {node} && "
            f"timeout {timeout} cat {node}"
        )

        try:
            output = await self._client.shell(
                shell_cmd,
                self._serial,
                timeout=timeout + 1,
                check_error=False,
            )

            return self._parse_at_response(output, command)

        except Exception as e:
            return ATResponse(
                result=ATResult.ERROR,
                raw_response=str(e),
                error_message=str(e),
            )

    def _parse_at_response(self, output: str, command: str) -> ATResponse:
        """Parse standard AT response format."""
        response = ATResponse(
            result=ATResult.NO_RESPONSE,
            raw_response=output,
        )

        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]

        # Filter out echo of command
        data_lines = []
        for line in lines:
            if line.upper().startswith(command.strip().upper()):
                continue
            data_lines.append(line)

        response.response_lines = data_lines

        # Check result
        for line in reversed(data_lines):
            line_upper = line.upper()
            if line_upper == "OK":
                response.result = ATResult.OK
                response.response_lines.remove(line)
                break
            elif line_upper == "ERROR":
                response.result = ATResult.ERROR
                response.response_lines.remove(line)
                break
            elif "+CME ERROR:" in line_upper:
                response.result = ATResult.CME_ERROR
                match = re.search(r"\+CME ERROR:\s*(\d+)", line, re.IGNORECASE)
                if match:
                    response.error_code = int(match.group(1))
                response.response_lines.remove(line)
                break
            elif "+CMS ERROR:" in line_upper:
                response.result = ATResult.CMS_ERROR
                match = re.search(r"\+CMS ERROR:\s*(\d+)", line, re.IGNORECASE)
                if match:
                    response.error_code = int(match.group(1))
                response.response_lines.remove(line)
                break

        return response

    # =========================================================================
    # Helper methods for common AT commands
    # =========================================================================

    async def get_sim_status(self) -> str:
        """Get SIM status via AT+CPIN?.

        Returns:
            SIM status string (e.g., "READY", "SIM PIN").
        """
        response = await self.send_command("AT+CPIN?")
        if response.is_ok and response.response_lines:
            # Parse "+CPIN: READY" format
            for line in response.response_lines:
                if "+CPIN:" in line.upper():
                    parts = line.split(":")
                    if len(parts) > 1:
                        return parts[1].strip()
        return "UNKNOWN"

    async def get_imsi(self) -> str:
        """Get IMSI via AT+CIMI.

        Returns:
            IMSI string or empty if unavailable.
        """
        response = await self.send_command("AT+CIMI")
        if response.is_ok and response.response_lines:
            # IMSI is returned as plain number
            for line in response.response_lines:
                if line.isdigit() and len(line) >= 15:
                    return line
        return ""

    async def get_iccid(self) -> str:
        """Get ICCID via AT+CCID or AT+ICCID.

        Returns:
            ICCID string or empty if unavailable.
        """
        # Try AT+CCID first
        response = await self.send_command("AT+CCID")
        if response.is_ok and response.response_lines:
            for line in response.response_lines:
                # ICCID format: +CCID: "8901..."
                match = re.search(r'["\']?([89]\d{17,21})["\']?', line)
                if match:
                    return match.group(1)

        # Try AT+ICCID as fallback
        response = await self.send_command("AT+ICCID")
        if response.is_ok and response.response_lines:
            for line in response.response_lines:
                match = re.search(r'["\']?([89]\d{17,21})["\']?', line)
                if match:
                    return match.group(1)

        return ""

    async def send_csim(
        self,
        length: int,
        command: str,
    ) -> ATResponse:
        """Send CSIM command for generic SIM access.

        Args:
            length: Length of command in bytes.
            command: Hex-encoded command APDU.

        Returns:
            ATResponse with CSIM result.

        Example:
            ```python
            # SELECT MF
            response = await at.send_csim(7, "00A40000023F00")
            ```
        """
        at_cmd = f'AT+CSIM={length},"{command}"'
        return await self.send_command(at_cmd)

    async def get_signal_quality(self) -> tuple:
        """Get signal quality via AT+CSQ.

        Returns:
            Tuple of (rssi, ber) or (99, 99) if unavailable.
        """
        response = await self.send_command("AT+CSQ")
        if response.is_ok and response.response_lines:
            for line in response.response_lines:
                match = re.search(r"\+CSQ:\s*(\d+),\s*(\d+)", line)
                if match:
                    return int(match.group(1)), int(match.group(2))
        return 99, 99

    async def get_operator(self) -> str:
        """Get current operator via AT+COPS?.

        Returns:
            Operator name or empty string.
        """
        response = await self.send_command("AT+COPS?")
        if response.is_ok and response.response_lines:
            for line in response.response_lines:
                # Format: +COPS: 0,0,"Operator Name",7
                match = re.search(r'\+COPS:.*"([^"]+)"', line)
                if match:
                    return match.group(1)
        return ""

    async def get_network_registration(self) -> tuple:
        """Get network registration status via AT+CREG?.

        Returns:
            Tuple of (n, stat) where stat is registration status.
        """
        response = await self.send_command("AT+CREG?")
        if response.is_ok and response.response_lines:
            for line in response.response_lines:
                match = re.search(r"\+CREG:\s*(\d+),\s*(\d+)", line)
                if match:
                    return int(match.group(1)), int(match.group(2))
        return 0, 0

    async def check_pin_required(self) -> bool:
        """Check if SIM PIN is required.

        Returns:
            True if PIN entry is required.
        """
        status = await self.get_sim_status()
        return "PIN" in status.upper() and "READY" not in status.upper()

    async def verify_pin(self, pin: str) -> bool:
        """Verify SIM PIN.

        Args:
            pin: PIN code to verify.

        Returns:
            True if PIN was accepted.

        Warning:
            Be careful with PIN attempts - too many failures will lock the SIM.
        """
        response = await self.send_command(f'AT+CPIN="{pin}"')
        return response.is_ok
