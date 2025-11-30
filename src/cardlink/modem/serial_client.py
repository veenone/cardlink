"""Serial Client for Modem Controller.

This module provides low-level serial port communication for modem
interactions, including port discovery and async read/write operations.
"""

import asyncio
import logging
import threading
from typing import List, Optional

from cardlink.modem.exceptions import SerialPortError
from cardlink.modem.models import (
    ModemVendor,
    PortInfo,
    QUECTEL_USB_IDS,
    SIERRA_USB_IDS,
    SIMCOM_USB_IDS,
    USB_VENDOR_MAP,
)

logger = logging.getLogger(__name__)

# Default serial settings
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1.0
DEFAULT_READ_TIMEOUT = 0.1  # For non-blocking reads


class SerialClient:
    """Low-level serial port communication wrapper.

    Provides async-friendly serial port operations for modem communication.
    Uses pyserial for cross-platform serial port access.

    Example:
        >>> client = SerialClient("/dev/ttyUSB2")
        >>> await client.open()
        >>> await client.write(b"ATI\\r\\n")
        >>> response = await client.read_until(b"OK")
        >>> await client.close()
    """

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
        write_timeout: Optional[float] = None,
    ):
        """Initialize serial client.

        Args:
            port: Serial port path (e.g., /dev/ttyUSB2 or COM3)
            baudrate: Baud rate (default: 115200)
            timeout: Read timeout in seconds (default: 1.0)
            write_timeout: Write timeout in seconds (default: None)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout

        self._serial: Optional["serial.Serial"] = None
        self._lock = threading.Lock()
        self._read_buffer = bytearray()

    @property
    def is_open(self) -> bool:
        """Check if serial port is open."""
        return self._serial is not None and self._serial.is_open

    async def open(self) -> None:
        """Open serial port.

        Raises:
            SerialPortError: If port cannot be opened.
        """
        if self.is_open:
            return

        try:
            import serial

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=DEFAULT_READ_TIMEOUT,  # Short timeout for non-blocking
                write_timeout=self.write_timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )

            # Clear buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self._read_buffer.clear()

            logger.debug("Opened serial port %s at %d baud", self.port, self.baudrate)

        except ImportError:
            raise SerialPortError(
                self.port,
                "pyserial not installed. Install with: pip install pyserial",
            )
        except serial.SerialException as e:
            raise SerialPortError(self.port, str(e), cause=e)

    async def close(self) -> None:
        """Close serial port."""
        if self._serial is not None:
            try:
                self._serial.close()
                logger.debug("Closed serial port %s", self.port)
            except Exception as e:
                logger.warning("Error closing serial port %s: %s", self.port, e)
            finally:
                self._serial = None
                self._read_buffer.clear()

    async def write(self, data: bytes) -> int:
        """Write data to serial port.

        Args:
            data: Bytes to write.

        Returns:
            Number of bytes written.

        Raises:
            SerialPortError: If write fails.
        """
        if not self.is_open:
            raise SerialPortError(self.port, "Port not open")

        try:
            loop = asyncio.get_event_loop()
            # Use thread pool for blocking write
            count = await loop.run_in_executor(None, self._serial.write, data)
            logger.debug("Wrote %d bytes to %s: %r", count, self.port, data)
            return count

        except Exception as e:
            raise SerialPortError(self.port, f"Write failed: {e}", cause=e)

    async def read(self, size: int = 1024) -> bytes:
        """Read data from serial port.

        Args:
            size: Maximum bytes to read.

        Returns:
            Bytes read (may be empty if no data available).

        Raises:
            SerialPortError: If read fails.
        """
        if not self.is_open:
            raise SerialPortError(self.port, "Port not open")

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._serial.read, size)
            if data:
                logger.debug("Read %d bytes from %s: %r", len(data), self.port, data)
            return data

        except Exception as e:
            raise SerialPortError(self.port, f"Read failed: {e}", cause=e)

    async def read_line(self, timeout: Optional[float] = None) -> str:
        """Read a line from serial port.

        Args:
            timeout: Timeout in seconds (default: instance timeout).

        Returns:
            Line read (without trailing newline).

        Raises:
            SerialPortError: If read fails or times out.
        """
        if not self.is_open:
            raise SerialPortError(self.port, "Port not open")

        timeout = timeout or self.timeout
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            # Check for complete line in buffer
            newline_idx = self._read_buffer.find(b"\n")
            if newline_idx >= 0:
                line = bytes(self._read_buffer[: newline_idx + 1])
                del self._read_buffer[: newline_idx + 1]
                return line.decode("utf-8", errors="replace").rstrip("\r\n")

            # Check timeout
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise SerialPortError(self.port, f"Timeout reading line after {timeout}s")

            # Read more data
            try:
                data = await self.read(1024)
                if data:
                    self._read_buffer.extend(data)
                else:
                    # Small delay to avoid busy loop
                    await asyncio.sleep(0.01)
            except SerialPortError:
                raise

    async def read_until(
        self,
        terminator: bytes,
        timeout: Optional[float] = None,
        include_terminator: bool = True,
    ) -> bytes:
        """Read until terminator or timeout.

        Args:
            terminator: Bytes sequence to read until.
            timeout: Timeout in seconds (default: instance timeout).
            include_terminator: Whether to include terminator in result.

        Returns:
            Bytes read.

        Raises:
            SerialPortError: If read fails or times out.
        """
        if not self.is_open:
            raise SerialPortError(self.port, "Port not open")

        timeout = timeout or self.timeout
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            # Check for terminator in buffer
            term_idx = self._read_buffer.find(terminator)
            if term_idx >= 0:
                if include_terminator:
                    end_idx = term_idx + len(terminator)
                else:
                    end_idx = term_idx
                result = bytes(self._read_buffer[:end_idx])
                del self._read_buffer[: term_idx + len(terminator)]
                return result

            # Check timeout
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                # Return what we have in buffer
                buffered = bytes(self._read_buffer)
                self._read_buffer.clear()
                raise SerialPortError(
                    self.port,
                    f"Timeout after {timeout}s waiting for {terminator!r}. "
                    f"Buffer contents: {buffered!r}",
                )

            # Read more data
            try:
                data = await self.read(1024)
                if data:
                    self._read_buffer.extend(data)
                else:
                    await asyncio.sleep(0.01)
            except SerialPortError:
                raise

    async def read_available(self) -> bytes:
        """Read all available data without blocking.

        Returns:
            All available data in receive buffer.
        """
        if not self.is_open:
            raise SerialPortError(self.port, "Port not open")

        result = bytearray()

        # First, get any buffered data
        result.extend(self._read_buffer)
        self._read_buffer.clear()

        # Then read any data from serial port
        try:
            if self._serial.in_waiting > 0:
                data = await self.read(self._serial.in_waiting)
                result.extend(data)
        except Exception:
            pass

        return bytes(result)

    async def flush(self) -> None:
        """Flush write buffer."""
        if not self.is_open:
            return

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._serial.flush)
        except Exception as e:
            logger.warning("Error flushing serial port: %s", e)

    async def clear_buffers(self) -> None:
        """Clear input and output buffers."""
        if not self.is_open:
            return

        try:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self._read_buffer.clear()
        except Exception as e:
            logger.warning("Error clearing buffers: %s", e)

    @staticmethod
    def list_ports() -> List[PortInfo]:
        """List available serial ports.

        Returns:
            List of PortInfo for available ports.
        """
        try:
            from serial.tools import list_ports

            ports = []
            for port in list_ports.comports():
                # Extract USB VID:PID
                vid_pid = ""
                vid = None
                pid = None
                if port.vid is not None and port.pid is not None:
                    vid = port.vid
                    pid = port.pid
                    vid_pid = f"{port.vid:04x}:{port.pid:04x}"

                # Determine manufacturer from USB ID if not provided
                manufacturer = port.manufacturer or ""
                if not manufacturer and vid_pid in USB_VENDOR_MAP:
                    manufacturer = USB_VENDOR_MAP[vid_pid].value

                ports.append(
                    PortInfo(
                        port=port.device,
                        description=port.description or "",
                        hwid=port.hwid or "",
                        manufacturer=manufacturer,
                        product=port.product or "",
                        serial_number=port.serial_number or "",
                        vid=vid,
                        pid=pid,
                        location=port.location or "",
                    )
                )

            return ports

        except ImportError:
            logger.warning("pyserial not installed, cannot list ports")
            return []

    @staticmethod
    def list_modem_ports() -> List[PortInfo]:
        """List serial ports that appear to be modems.

        Filters ports based on known modem USB VID:PIDs.

        Returns:
            List of PortInfo for detected modem ports.
        """
        all_ports = SerialClient.list_ports()
        modem_ports = []

        for port in all_ports:
            if port.vid is not None and port.pid is not None:
                vid_pid = f"{port.vid:04x}:{port.pid:04x}"
                if vid_pid in USB_VENDOR_MAP:
                    modem_ports.append(port)

        return modem_ports

    @staticmethod
    def get_vendor_from_port(port_info: PortInfo) -> ModemVendor:
        """Determine modem vendor from port info.

        Args:
            port_info: Port information.

        Returns:
            Modem vendor enum.
        """
        if port_info.vid is not None and port_info.pid is not None:
            vid_pid = f"{port_info.vid:04x}:{port_info.pid:04x}"
            if vid_pid in USB_VENDOR_MAP:
                return USB_VENDOR_MAP[vid_pid]

        # Try to determine from manufacturer string
        manufacturer = port_info.manufacturer.lower()
        if "quectel" in manufacturer:
            return ModemVendor.QUECTEL
        elif "sierra" in manufacturer:
            return ModemVendor.SIERRA
        elif "simcom" in manufacturer:
            return ModemVendor.SIMCOM
        elif "telit" in manufacturer:
            return ModemVendor.TELIT
        elif "u-blox" in manufacturer or "ublox" in manufacturer:
            return ModemVendor.UBLOX

        return ModemVendor.UNKNOWN

    @staticmethod
    def get_model_from_usb_id(vid: int, pid: int) -> Optional[str]:
        """Get modem model from USB VID:PID.

        Args:
            vid: USB Vendor ID.
            pid: USB Product ID.

        Returns:
            Model name if known, None otherwise.
        """
        vid_pid = f"{vid:04x}:{pid:04x}"

        if vid_pid in QUECTEL_USB_IDS:
            return QUECTEL_USB_IDS[vid_pid]
        if vid_pid in SIERRA_USB_IDS:
            return SIERRA_USB_IDS[vid_pid]
        if vid_pid in SIMCOM_USB_IDS:
            return SIMCOM_USB_IDS[vid_pid]

        return None

    def __repr__(self) -> str:
        """String representation."""
        status = "open" if self.is_open else "closed"
        return f"SerialClient(port={self.port!r}, baudrate={self.baudrate}, {status})"

    async def __aenter__(self) -> "SerialClient":
        """Async context manager entry."""
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
