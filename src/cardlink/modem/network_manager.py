"""Network Manager for Modem Controller.

This module manages modem network configuration including
APN settings, PDP context, and data connection.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from cardlink.modem.at_interface import ATInterface
from cardlink.modem.exceptions import ATCommandError, NetworkError
from cardlink.modem.models import (
    AuthType,
    NetworkType,
    PingResult,
    RegistrationStatus,
)

logger = logging.getLogger(__name__)

# Response patterns
CREG_PATTERN = re.compile(r"\+CREG:\s*(\d+),(\d+)")
CEREG_PATTERN = re.compile(r"\+CEREG:\s*(\d+),(\d+)")
CGACT_PATTERN = re.compile(r"\+CGACT:\s*(\d+),(\d+)")
CGPADDR_PATTERN = re.compile(r'\+CGPADDR:\s*(\d+),"?([^"]+)"?')
QPING_PATTERN = re.compile(r'\+QPING:\s*(\d+)(?:,"([^"]+)",(\d+),(\d+),(\d+))?')

# Default timeouts
REGISTRATION_TIMEOUT = 60.0
PDP_ACTIVATION_TIMEOUT = 30.0
PING_TIMEOUT = 30.0


@dataclass
class RegistrationInfo:
    """Network registration information."""

    cs_status: RegistrationStatus
    eps_status: RegistrationStatus
    is_registered: bool


@dataclass
class PDPContext:
    """PDP context information."""

    cid: int
    pdp_type: str
    apn: str
    active: bool
    ip_address: Optional[str] = None


class NetworkManager:
    """Manages modem network configuration.

    Provides methods for APN configuration, PDP context management,
    and network connectivity testing.

    Example:
        >>> manager = NetworkManager(at_interface)
        >>>
        >>> # Configure APN
        >>> await manager.configure_apn("internet", username="user", password="pass")
        >>>
        >>> # Activate PDP context
        >>> await manager.activate_pdp(1)
        >>>
        >>> # Get IP address
        >>> ip = await manager.get_ip_address(1)
        >>> print(f"IP: {ip}")
        >>>
        >>> # Ping test
        >>> result = await manager.ping("8.8.8.8")
        >>> print(f"Success: {result.success}, Avg: {result.avg_time}ms")
    """

    def __init__(self, at_interface: ATInterface):
        """Initialize network manager.

        Args:
            at_interface: AT interface for communication.
        """
        self.at = at_interface

    # =========================================================================
    # Registration Check
    # =========================================================================

    async def check_registration(self) -> RegistrationInfo:
        """Check network registration status.

        Returns:
            RegistrationInfo with CS and EPS registration status.
        """
        cs_status = RegistrationStatus.UNKNOWN
        eps_status = RegistrationStatus.UNKNOWN

        # Check CS registration
        try:
            response = await self.at.send_command("AT+CREG?", check_error=False)
            if response.success:
                match = CREG_PATTERN.search(response.raw_response)
                if match:
                    stat = int(match.group(2))
                    try:
                        cs_status = RegistrationStatus(stat)
                    except ValueError:
                        pass
        except ATCommandError:
            pass

        # Check EPS registration
        try:
            response = await self.at.send_command("AT+CEREG?", check_error=False)
            if response.success:
                match = CEREG_PATTERN.search(response.raw_response)
                if match:
                    stat = int(match.group(2))
                    try:
                        eps_status = RegistrationStatus(stat)
                    except ValueError:
                        pass
        except ATCommandError:
            pass

        # Determine if registered
        registered_states = {
            RegistrationStatus.REGISTERED_HOME,
            RegistrationStatus.REGISTERED_ROAMING,
        }
        is_registered = cs_status in registered_states or eps_status in registered_states

        return RegistrationInfo(
            cs_status=cs_status,
            eps_status=eps_status,
            is_registered=is_registered,
        )

    async def wait_for_registration(
        self,
        timeout: float = REGISTRATION_TIMEOUT,
        poll_interval: float = 2.0,
    ) -> bool:
        """Wait for network registration.

        Args:
            timeout: Maximum wait time in seconds.
            poll_interval: Polling interval in seconds.

        Returns:
            True if registered within timeout.
        """
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            info = await self.check_registration()
            if info.is_registered:
                logger.info("Network registered: CS=%s, EPS=%s",
                           info.cs_status.name, info.eps_status.name)
                return True

            await asyncio.sleep(poll_interval)

        logger.warning("Registration timeout after %ds", timeout)
        return False

    # =========================================================================
    # APN Configuration
    # =========================================================================

    async def configure_apn(
        self,
        apn: str,
        cid: int = 1,
        pdp_type: str = "IP",
        username: str = "",
        password: str = "",
        auth_type: AuthType = AuthType.NONE,
    ) -> bool:
        """Configure APN settings.

        Args:
            apn: Access Point Name.
            cid: PDP context ID (default: 1).
            pdp_type: PDP type (IP, IPV6, IPV4V6).
            username: Authentication username.
            password: Authentication password.
            auth_type: Authentication type.

        Returns:
            True if configuration successful.

        Raises:
            NetworkError: If configuration fails.
        """
        try:
            # Set PDP context definition
            cmd = f'AT+CGDCONT={cid},"{pdp_type}","{apn}"'
            response = await self.at.send_command(cmd)
            if not response.success:
                raise NetworkError(f"Failed to set PDP context: {response.raw_response}")

            # Set authentication if provided
            if username or password:
                auth_value = auth_type.value
                cmd = f'AT+CGAUTH={cid},{auth_value},"{password}","{username}"'
                response = await self.at.send_command(cmd, check_error=False)
                # Authentication command may fail on some modems if not supported
                if not response.success:
                    logger.warning("CGAUTH command not supported, trying QICSGP")

                    # Try Quectel-specific command
                    cmd = f'AT+QICSGP={cid},{auth_value},"{apn}","{username}","{password}"'
                    await self.at.send_command(cmd, check_error=False)

            logger.info("APN configured: %s (cid=%d)", apn, cid)
            return True

        except ATCommandError as e:
            raise NetworkError(f"Failed to configure APN: {e}")

    async def get_apn(self, cid: int = 1) -> Optional[str]:
        """Get configured APN for PDP context.

        Args:
            cid: PDP context ID.

        Returns:
            APN string if configured, None otherwise.
        """
        try:
            response = await self.at.send_command("AT+CGDCONT?", check_error=False)
            if response.success:
                pattern = rf'\+CGDCONT:\s*{cid},"[^"]*","([^"]*)"'
                match = re.search(pattern, response.raw_response)
                if match:
                    return match.group(1)
        except ATCommandError:
            pass
        return None

    # =========================================================================
    # PDP Context Management
    # =========================================================================

    async def activate_pdp(self, cid: int = 1) -> bool:
        """Activate PDP context.

        Args:
            cid: PDP context ID.

        Returns:
            True if activation successful.

        Raises:
            NetworkError: If activation fails.
        """
        try:
            cmd = f"AT+CGACT=1,{cid}"
            response = await self.at.send_command(cmd, timeout=PDP_ACTIVATION_TIMEOUT)

            if response.success:
                logger.info("PDP context %d activated", cid)
                return True

            raise NetworkError(f"PDP activation failed: {response.raw_response}")

        except ATCommandError as e:
            raise NetworkError(f"Failed to activate PDP: {e}")

    async def deactivate_pdp(self, cid: int = 1) -> bool:
        """Deactivate PDP context.

        Args:
            cid: PDP context ID.

        Returns:
            True if deactivation successful.
        """
        try:
            cmd = f"AT+CGACT=0,{cid}"
            response = await self.at.send_command(cmd, timeout=PDP_ACTIVATION_TIMEOUT)
            if response.success:
                logger.info("PDP context %d deactivated", cid)
                return True
        except ATCommandError:
            pass
        return False

    async def is_pdp_active(self, cid: int = 1) -> bool:
        """Check if PDP context is active.

        Args:
            cid: PDP context ID.

        Returns:
            True if context is active.
        """
        try:
            response = await self.at.send_command("AT+CGACT?", check_error=False)
            if response.success:
                pattern = rf"\+CGACT:\s*{cid},(\d+)"
                match = re.search(pattern, response.raw_response)
                if match:
                    return match.group(1) == "1"
        except ATCommandError:
            pass
        return False

    async def get_pdp_contexts(self) -> List[PDPContext]:
        """Get all configured PDP contexts.

        Returns:
            List of PDPContext objects.
        """
        contexts = []

        try:
            # Get context definitions
            response = await self.at.send_command("AT+CGDCONT?", check_error=False)
            if response.success:
                pattern = r'\+CGDCONT:\s*(\d+),"([^"]*)","([^"]*)"'
                for match in re.finditer(pattern, response.raw_response):
                    contexts.append(PDPContext(
                        cid=int(match.group(1)),
                        pdp_type=match.group(2),
                        apn=match.group(3),
                        active=False,
                    ))

            # Get activation status
            response = await self.at.send_command("AT+CGACT?", check_error=False)
            if response.success:
                for match in CGACT_PATTERN.finditer(response.raw_response):
                    cid = int(match.group(1))
                    active = match.group(2) == "1"
                    for ctx in contexts:
                        if ctx.cid == cid:
                            ctx.active = active
                            break

            # Get IP addresses
            for ctx in contexts:
                if ctx.active:
                    ctx.ip_address = await self.get_ip_address(ctx.cid)

        except ATCommandError:
            pass

        return contexts

    # =========================================================================
    # IP Address
    # =========================================================================

    async def get_ip_address(self, cid: int = 1) -> Optional[str]:
        """Get assigned IP address for PDP context.

        Args:
            cid: PDP context ID.

        Returns:
            IP address string if assigned, None otherwise.
        """
        try:
            cmd = f"AT+CGPADDR={cid}"
            response = await self.at.send_command(cmd, check_error=False)
            if response.success:
                match = CGPADDR_PATTERN.search(response.raw_response)
                if match:
                    ip = match.group(2).strip()
                    if ip and ip != "0.0.0.0":
                        return ip
        except ATCommandError:
            pass
        return None

    # =========================================================================
    # Ping / Connectivity Test
    # =========================================================================

    async def ping(
        self,
        host: str,
        count: int = 4,
        timeout: float = 10.0,
        cid: int = 1,
    ) -> PingResult:
        """Ping host via modem.

        Uses AT+QPING for Quectel modems.

        Args:
            host: Host to ping (IP or hostname).
            count: Number of ping packets.
            timeout: Timeout per packet in seconds.
            cid: PDP context ID to use.

        Returns:
            PingResult with statistics.
        """
        result = PingResult(host=host)

        try:
            # Quectel QPING format: AT+QPING=<contextID>,"<host>"[,<timeout>][,<pingnum>]
            timeout_ms = int(timeout * 1000)
            cmd = f'AT+QPING={cid},"{host}",{timeout_ms},{count}'

            response = await self.at.send_command(
                cmd,
                timeout=PING_TIMEOUT + (timeout * count),
                check_error=False,
            )

            result.raw_response = response.raw_response

            if not response.success:
                result.error = "Ping command failed"
                return result

            # Parse QPING responses
            # +QPING: <result>[,"<ipaddress>",<bytes>,<time>,<ttl>]
            # Final: +QPING: 0,<sent>,<rcvd>,<lost>,<min>,<max>,<avg>
            times = []

            for match in QPING_PATTERN.finditer(response.raw_response):
                result_code = int(match.group(1))

                if match.group(2):  # Individual ping response
                    if result_code == 0:
                        time_ms = int(match.group(4))
                        times.append(time_ms)
                elif len(match.groups()) >= 5:  # Could be summary
                    # Parse summary line differently
                    pass

            # Parse final summary
            # Look for final +QPING line with statistics
            summary_pattern = r"\+QPING:\s*0,(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)"
            summary_match = re.search(summary_pattern, response.raw_response)

            if summary_match:
                result.sent = int(summary_match.group(1))
                result.received = int(summary_match.group(2))
                result.lost = int(summary_match.group(3))
                result.min_time = float(summary_match.group(4))
                result.max_time = float(summary_match.group(5))
                result.avg_time = float(summary_match.group(6))
                result.success = result.received > 0
            elif times:
                # Fallback to calculated stats
                result.sent = count
                result.received = len(times)
                result.lost = count - len(times)
                if times:
                    result.min_time = float(min(times))
                    result.max_time = float(max(times))
                    result.avg_time = sum(times) / len(times)
                result.success = len(times) > 0

            logger.info(
                "Ping %s: %d/%d received, avg=%.1fms",
                host,
                result.received,
                result.sent,
                result.avg_time or 0,
            )

        except ATCommandError as e:
            result.error = str(e)
            logger.warning("Ping failed: %s", e)

        return result

    # =========================================================================
    # Operator Selection
    # =========================================================================

    async def get_operator(self) -> Optional[str]:
        """Get current network operator name.

        Returns:
            Operator name if registered, None otherwise.
        """
        try:
            response = await self.at.send_command("AT+COPS?", check_error=False)
            if response.success:
                # +COPS: <mode>[,<format>,<oper>[,<AcT>]]
                match = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', response.raw_response)
                if match:
                    return match.group(1)
        except ATCommandError:
            pass
        return None

    async def set_operator_auto(self) -> bool:
        """Set automatic operator selection.

        Returns:
            True if successful.
        """
        try:
            response = await self.at.send_command("AT+COPS=0", timeout=30.0)
            return response.success
        except ATCommandError:
            return False

    async def scan_operators(self) -> List[str]:
        """Scan for available network operators.

        This operation can take a long time (up to 3 minutes).

        Returns:
            List of operator names.
        """
        operators = []

        try:
            response = await self.at.send_command("AT+COPS=?", timeout=180.0, check_error=False)
            if response.success:
                # Parse operator list
                # +COPS: (status,"long","short","numeric",<AcT>),...
                pattern = r'\(\d+,"([^"]+)","[^"]*","\d+"(?:,\d+)?\)'
                for match in re.finditer(pattern, response.raw_response):
                    operators.append(match.group(1))
        except ATCommandError:
            pass

        return operators
