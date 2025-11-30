"""QXDM Diagnostic Interface for Modem Controller.

This module provides optional QXDM diagnostic integration for
Qualcomm-based modems. QXDM functionality requires a separate
DM (Diagnostic Monitor) port on the modem.

Note: Full QXDM functionality requires Qualcomm QXDM software
and appropriate licenses. This module provides basic DM port
detection and logging infrastructure.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from cardlink.modem.exceptions import QXDMError
from cardlink.modem.models import PortInfo, QUECTEL_PORT_FUNCTIONS
from cardlink.modem.serial_client import SerialClient

logger = logging.getLogger(__name__)

# Common diagnostic log codes for OTA/BIP debugging
# Reference: Qualcomm DM documentation
LOG_CODES = {
    # SIM/UICC logs
    0x1098: "UIM_CMD",
    0x1099: "UIM_RSP",
    0x108F: "USIM_ACCESS",
    # SMS logs
    0x5230: "SMS_RECEIVED",
    0x5231: "SMS_SENT",
    0x12FC: "SMS_MO",
    0x12FD: "SMS_MT",
    # Data/Bearer logs
    0x4D05: "DS_BEARER_CONTEXT",
    0x4D14: "DS_PDN_EVENT",
    # LTE logs
    0xB0C0: "LTE_RRC_OTA_MSG",
    0xB0EC: "LTE_NAS_EMM_OTA",
    0xB0ED: "LTE_NAS_ESM_OTA",
    # CAT/STK logs
    0x1510: "CAT_EVENT",
    0x1511: "CAT_PROACTIVE_CMD",
    0x1512: "CAT_TERMINAL_RSP",
    # BIP-related
    0x1513: "CAT_ENVELOPE_CMD",
    0x1514: "CAT_ENVELOPE_RSP",
}


@dataclass
class DMLogEntry:
    """Diagnostic Monitor log entry."""

    timestamp: datetime
    log_code: int
    log_name: str
    data: bytes
    parsed: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QXDMConfig:
    """QXDM interface configuration."""

    dm_port: str = ""
    baudrate: int = 115200
    log_codes: Set[int] = field(default_factory=set)
    output_file: Optional[str] = None


class QXDMInterface:
    """QXDM diagnostic interface for Qualcomm modems.

    Provides basic DM port detection and log capture functionality.

    Note: This is a simplified interface. Full QXDM functionality
    requires Qualcomm's QXDM Professional software.

    Example:
        >>> qxdm = QXDMInterface()
        >>>
        >>> # Find DM port
        >>> dm_port = qxdm.find_dm_port("/dev/ttyUSB2")
        >>> if dm_port:
        ...     await qxdm.connect(dm_port)
        ...
        ...     # Start logging
        ...     await qxdm.start_logging([0x1098, 0x1099])
        ...
        ...     # ... capture logs ...
        ...
        ...     await qxdm.stop_logging()
        ...     await qxdm.disconnect()
    """

    def __init__(self, config: Optional[QXDMConfig] = None):
        """Initialize QXDM interface.

        Args:
            config: Optional configuration.
        """
        self.config = config or QXDMConfig()
        self._serial: Optional[SerialClient] = None
        self._connected = False
        self._logging = False
        self._log_task: Optional[asyncio.Task] = None
        self._log_entries: List[DMLogEntry] = []
        self._log_callbacks: List[Callable[[DMLogEntry], Any]] = []

    @property
    def is_connected(self) -> bool:
        """Check if connected to DM port."""
        return self._connected

    @property
    def is_logging(self) -> bool:
        """Check if logging is active."""
        return self._logging

    def is_available(self) -> bool:
        """Check if QXDM interface is available.

        Returns:
            True if DM port is detected and accessible.
        """
        if self.config.dm_port:
            ports = SerialClient.list_ports()
            return any(p.port == self.config.dm_port for p in ports)
        return False

    # =========================================================================
    # Port Detection
    # =========================================================================

    @staticmethod
    def find_dm_port(at_port: str) -> Optional[str]:
        """Find DM port associated with AT port.

        For Quectel modems, DM port is typically interface 0 when
        AT port is interface 2.

        Args:
            at_port: AT command port path.

        Returns:
            DM port path if found, None otherwise.
        """
        ports = SerialClient.list_ports()

        # Find the AT port info
        at_port_info = None
        for port in ports:
            if port.port == at_port:
                at_port_info = port
                break

        if not at_port_info or not at_port_info.location:
            return None

        # Extract USB location base
        # Location format varies but typically: X-Y:Z.I where I is interface
        location_base = at_port_info.location.rsplit(".", 1)[0] if "." in at_port_info.location else at_port_info.location

        # Find DM port (interface 0 for Quectel)
        for port in ports:
            if port.location and port.location.startswith(location_base):
                # Check if this is interface 0
                if ".0" in port.location or port.location.endswith(":1.0"):
                    # Verify it's the same device (same VID:PID)
                    if port.vid == at_port_info.vid and port.pid == at_port_info.pid:
                        logger.debug("Found DM port %s for AT port %s", port.port, at_port)
                        return port.port

        return None

    @staticmethod
    def get_port_function(port_info: PortInfo) -> Optional[str]:
        """Get function of a modem port (AT, DM, NMEA, etc.).

        Args:
            port_info: Port information.

        Returns:
            Port function name if determinable.
        """
        # Try to determine from location (interface number)
        if port_info.location:
            # Extract interface number from location
            match = re.search(r"\.(\d+)$", port_info.location)
            if match:
                interface = int(match.group(1))
                return QUECTEL_PORT_FUNCTIONS.get(interface)

        # Try to determine from description
        desc = port_info.description.lower()
        if "at" in desc or "modem" in desc:
            return "AT"
        elif "dm" in desc or "diag" in desc:
            return "DM"
        elif "nmea" in desc or "gps" in desc:
            return "NMEA"

        return None

    # =========================================================================
    # Connection
    # =========================================================================

    async def connect(self, dm_port: Optional[str] = None) -> None:
        """Connect to DM port.

        Args:
            dm_port: DM port path (uses config if not specified).

        Raises:
            QXDMError: If connection fails.
        """
        if self._connected:
            return

        port = dm_port or self.config.dm_port
        if not port:
            raise QXDMError("No DM port specified")

        try:
            self._serial = SerialClient(port, baudrate=self.config.baudrate)
            await self._serial.open()
            self._connected = True
            logger.info("Connected to DM port: %s", port)

        except Exception as e:
            raise QXDMError(f"Failed to connect to DM port: {e}")

    async def disconnect(self) -> None:
        """Disconnect from DM port."""
        if self._logging:
            await self.stop_logging()

        if self._serial:
            await self._serial.close()
            self._serial = None

        self._connected = False
        logger.info("Disconnected from DM port")

    # =========================================================================
    # Logging
    # =========================================================================

    async def start_logging(self, log_codes: Optional[List[int]] = None) -> None:
        """Start diagnostic logging.

        Args:
            log_codes: Log codes to capture. If None, uses config.

        Raises:
            QXDMError: If logging cannot be started.
        """
        if not self._connected:
            raise QXDMError("Not connected to DM port")

        if self._logging:
            return

        codes = set(log_codes) if log_codes else self.config.log_codes
        if not codes:
            # Default to common OTA/STK logs
            codes = {0x1510, 0x1511, 0x1512, 0x1513, 0x1514, 0x1098, 0x1099}

        self.config.log_codes = codes
        self._logging = True
        self._log_entries.clear()

        # Start log reading task
        self._log_task = asyncio.create_task(self._log_reader_loop())

        logger.info("Started logging with %d log codes", len(codes))

    async def stop_logging(self) -> None:
        """Stop diagnostic logging."""
        if not self._logging:
            return

        self._logging = False

        if self._log_task:
            self._log_task.cancel()
            try:
                await self._log_task
            except asyncio.CancelledError:
                pass
            self._log_task = None

        logger.info("Stopped logging, captured %d entries", len(self._log_entries))

    async def _log_reader_loop(self) -> None:
        """Background task to read DM logs.

        Note: This is a simplified implementation. Real DM protocol
        parsing is complex and requires Qualcomm documentation.
        """
        while self._logging and self._serial and self._serial.is_open:
            try:
                # Read available data
                data = await self._serial.read(4096)
                if data:
                    # Parse DM messages
                    entries = self._parse_dm_data(data)
                    for entry in entries:
                        self._log_entries.append(entry)
                        await self._emit_log(entry)

                await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error reading DM data: %s", e)
                await asyncio.sleep(0.1)

    def _parse_dm_data(self, data: bytes) -> List[DMLogEntry]:
        """Parse DM data into log entries.

        Note: This is a simplified parser. Real DM protocol
        has specific framing and CRC requirements.

        Args:
            data: Raw DM data.

        Returns:
            List of parsed log entries.
        """
        entries = []

        # Look for log messages
        # DM log format: 0x10 <log_code_low> <log_code_high> <length_low> <length_high> <data...>
        idx = 0
        while idx < len(data) - 5:
            if data[idx] == 0x10:  # Log message indicator
                log_code = data[idx + 1] | (data[idx + 2] << 8)
                length = data[idx + 3] | (data[idx + 4] << 8)

                if idx + 5 + length <= len(data):
                    log_data = data[idx + 5 : idx + 5 + length]

                    # Check if this is a code we're interested in
                    if log_code in self.config.log_codes:
                        entry = DMLogEntry(
                            timestamp=datetime.now(),
                            log_code=log_code,
                            log_name=LOG_CODES.get(log_code, f"0x{log_code:04X}"),
                            data=log_data,
                        )
                        entries.append(entry)

                    idx += 5 + length
                    continue

            idx += 1

        return entries

    async def _emit_log(self, entry: DMLogEntry) -> None:
        """Emit log entry to registered callbacks."""
        for callback in self._log_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception as e:
                logger.error("Error in log callback: %s", e)

    def on_log(self, callback: Callable[[DMLogEntry], Any]) -> None:
        """Register log entry callback.

        Args:
            callback: Function to call for each log entry.
        """
        self._log_callbacks.append(callback)

    # =========================================================================
    # Export
    # =========================================================================

    async def export_log(
        self,
        filepath: str,
        format: str = "txt",
    ) -> None:
        """Export captured logs to file.

        Args:
            filepath: Output file path.
            format: Export format (txt, csv, or raw).
        """
        path = Path(filepath)

        if format == "txt":
            await self._export_txt(path)
        elif format == "csv":
            await self._export_csv(path)
        elif format == "raw":
            await self._export_raw(path)
        else:
            raise QXDMError(f"Unknown export format: {format}")

        logger.info("Exported %d log entries to %s", len(self._log_entries), filepath)

    async def _export_txt(self, path: Path) -> None:
        """Export as text file."""
        with open(path, "w") as f:
            f.write("QXDM Log Export\n")
            f.write(f"Entries: {len(self._log_entries)}\n")
            f.write("-" * 60 + "\n\n")

            for entry in self._log_entries:
                f.write(f"[{entry.timestamp.isoformat()}] ")
                f.write(f"{entry.log_name} (0x{entry.log_code:04X})\n")
                f.write(f"  Data: {entry.data.hex()}\n\n")

    async def _export_csv(self, path: Path) -> None:
        """Export as CSV file."""
        import csv

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Log Code", "Log Name", "Data (hex)"])

            for entry in self._log_entries:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    f"0x{entry.log_code:04X}",
                    entry.log_name,
                    entry.data.hex(),
                ])

    async def _export_raw(self, path: Path) -> None:
        """Export as raw binary file."""
        with open(path, "wb") as f:
            for entry in self._log_entries:
                # Write simple framed format
                f.write(entry.log_code.to_bytes(2, "little"))
                f.write(len(entry.data).to_bytes(2, "little"))
                f.write(entry.data)

    def get_log_entries(self) -> List[DMLogEntry]:
        """Get captured log entries.

        Returns:
            List of DMLogEntry objects.
        """
        return self._log_entries.copy()

    def clear_logs(self) -> None:
        """Clear captured log entries."""
        self._log_entries.clear()


# =============================================================================
# Utility Functions
# =============================================================================


def get_log_code_name(code: int) -> str:
    """Get name for a log code.

    Args:
        code: Log code.

    Returns:
        Log name or hex string if unknown.
    """
    return LOG_CODES.get(code, f"0x{code:04X}")


def list_known_log_codes() -> Dict[int, str]:
    """Get dictionary of known log codes.

    Returns:
        Dictionary mapping code to name.
    """
    return LOG_CODES.copy()
