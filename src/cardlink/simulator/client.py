"""Mobile Simulator main client.

This module provides the MobileSimulator class that orchestrates
PSK-TLS connections, HTTP Admin protocol exchanges, and virtual UICC
processing for simulating mobile device behavior.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional

from .behavior import BehaviorController
from .config import SimulatorConfig
from .http_client import HTTPAdminClient, HTTPAdminError, HTTPStatusError
from .models import (
    APDUExchange,
    ConnectionState,
    SessionResult,
    SimulatorStats,
    TLSConnectionInfo,
)
from .psk_tls_client import (
    ConnectionError,
    HandshakeError,
    PSKTLSClient,
    PSKTLSClientError,
    TimeoutError,
)
from .virtual_uicc import ParsedAPDU, VirtualUICC

logger = logging.getLogger(__name__)


class SimulatorError(Exception):
    """Base exception for simulator errors."""

    pass


class MobileSimulator:
    """Simulates mobile phone with UICC connecting to admin server.

    Orchestrates PSK-TLS connection, HTTP Admin protocol, and virtual
    UICC processing to simulate a mobile device initiating SCP81
    communication with the admin server.

    Attributes:
        config: Simulator configuration.
        state: Current connection state.

    Example:
        >>> config = SimulatorConfig(
        ...     server_host="127.0.0.1",
        ...     server_port=8443,
        ...     psk_identity="test_card",
        ...     psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10")
        ... )
        >>> simulator = MobileSimulator(config)
        >>> await simulator.connect()
        >>> result = await simulator.run_session()
        >>> await simulator.disconnect()
    """

    def __init__(self, config: SimulatorConfig):
        """Initialize simulator with configuration.

        Args:
            config: Simulator configuration.
        """
        config.validate()
        self.config = config

        # State
        self._state = ConnectionState.IDLE
        self._session_id: Optional[str] = None

        # Components
        self._tls_client: Optional[PSKTLSClient] = None
        self._http_client: Optional[HTTPAdminClient] = None
        self._virtual_uicc: VirtualUICC = VirtualUICC(config.uicc_profile)
        self._behavior: BehaviorController = BehaviorController(config.behavior)

        # Statistics
        self._stats = SimulatorStats()

        # Current session tracking
        self._exchanges: List[APDUExchange] = []
        self._connection_info: Optional[TLSConnectionInfo] = None

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self._session_id

    @property
    def connection_info(self) -> Optional[TLSConnectionInfo]:
        """Get TLS connection information."""
        return self._connection_info

    @property
    def statistics(self) -> SimulatorStats:
        """Get simulator statistics."""
        return self._stats

    def _set_state(self, new_state: ConnectionState) -> None:
        """Set connection state with logging.

        Args:
            new_state: New connection state.
        """
        old_state = self._state
        self._state = new_state
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    async def connect(self) -> bool:
        """Establish PSK-TLS connection to server.

        Implements retry logic with exponential backoff.

        Returns:
            True if connection successful, False otherwise.

        Raises:
            SimulatorError: If already connected.
        """
        if self._state != ConnectionState.IDLE:
            raise SimulatorError(f"Cannot connect from state: {self._state.value}")

        self._set_state(ConnectionState.CONNECTING)
        self._stats.connections_attempted += 1

        last_error: Optional[Exception] = None
        retry_delays = self.config.retry_backoff.copy()

        for attempt in range(self.config.retry_count + 1):
            try:
                # Create TLS client
                self._tls_client = PSKTLSClient(
                    host=self.config.server_host,
                    port=self.config.server_port,
                    psk_identity=self.config.psk_identity,
                    psk_key=self.config.psk_key,
                    timeout=self.config.connect_timeout,
                )

                # Connect
                connection_start = time.monotonic()
                self._connection_info = await self._tls_client.connect()
                connection_time_ms = (time.monotonic() - connection_start) * 1000

                # Create HTTP client
                self._http_client = HTTPAdminClient(self._tls_client)

                # Update stats
                self._stats.connections_succeeded += 1
                self._stats.record_connection_time(connection_time_ms)

                # Generate session ID
                self._session_id = str(uuid.uuid4())

                self._set_state(ConnectionState.CONNECTED)
                logger.info(
                    f"Connected to {self.config.server_address} "
                    f"(session: {self._session_id[:8]}...)"
                )
                return True

            except HandshakeError as e:
                # PSK mismatch - don't retry
                logger.error(f"Handshake failed (not retrying): {e}")
                self._stats.connections_failed += 1
                self._stats.record_error("handshake_failed")
                self._set_state(ConnectionState.ERROR)
                return False

            except (ConnectionError, TimeoutError) as e:
                last_error = e
                self._stats.record_error(type(e).__name__)
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

                # Retry if attempts remaining
                if attempt < self.config.retry_count and retry_delays:
                    delay = retry_delays.pop(0) if retry_delays else 1.0
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected connection error: {e}")
                self._stats.record_error("unexpected")
                break

        # All retries exhausted
        self._stats.connections_failed += 1
        self._set_state(ConnectionState.ERROR)
        logger.error(f"Connection failed after {self.config.retry_count + 1} attempts")
        return False

    async def run_session(self) -> SessionResult:
        """Run complete admin session.

        Exchanges APDUs with the server until session completion (204)
        or an error occurs.

        Returns:
            SessionResult with session outcome.

        Raises:
            SimulatorError: If not in CONNECTED state.
        """
        if self._state != ConnectionState.CONNECTED:
            raise SimulatorError(f"Cannot run session from state: {self._state.value}")

        self._set_state(ConnectionState.EXCHANGING)
        self._exchanges = []
        session_start = time.monotonic()

        try:
            # Send initial request
            c_apdu = await self._http_client.initial_request()

            # Exchange APDUs until session complete
            while c_apdu:
                # Process C-APDU through virtual UICC
                exchange_start = time.monotonic()

                # Check for behavior modifications
                error_sw = await self._behavior.maybe_inject_behavior()
                if error_sw:
                    r_apdu = bytes.fromhex(error_sw)
                else:
                    r_apdu = self._virtual_uicc.process_apdu(c_apdu)

                exchange_time_ms = (time.monotonic() - exchange_start) * 1000

                # Record exchange
                try:
                    parsed = ParsedAPDU.parse(c_apdu)
                    ins = parsed.ins
                    description = parsed.ins_name
                except Exception:
                    ins = 0
                    description = ""

                sw = r_apdu[-2:].hex().upper() if len(r_apdu) >= 2 else ""
                exchange = APDUExchange(
                    command=c_apdu.hex().upper(),
                    response=r_apdu.hex().upper(),
                    sw=sw,
                    timestamp=datetime.utcnow(),
                    duration_ms=exchange_time_ms,
                    ins=ins,
                    description=description,
                )
                self._exchanges.append(exchange)
                self._stats.total_apdus_received += 1
                self._stats.record_apdu_time(exchange_time_ms)

                if not exchange.is_success:
                    self._stats.record_error_sw(sw)

                logger.debug(
                    f"APDU exchange: {description} -> SW={sw} ({exchange_time_ms:.1f}ms)"
                )

                # Send R-APDU and get next C-APDU
                self._stats.total_apdus_sent += 1
                c_apdu = await self._http_client.send_response(r_apdu)

            # Session complete
            session_duration = time.monotonic() - session_start
            self._stats.sessions_completed += 1
            self._stats.record_session_duration(session_duration * 1000)

            final_sw = self._exchanges[-1].sw if self._exchanges else ""
            result = SessionResult(
                success=True,
                session_id=self._session_id or "",
                duration_seconds=session_duration,
                apdu_count=len(self._exchanges),
                final_sw=final_sw,
                exchanges=self._exchanges.copy(),
                tls_info=self._connection_info,
            )

            logger.info(
                f"Session complete: {len(self._exchanges)} APDUs, "
                f"{session_duration:.2f}s, final SW={final_sw}"
            )

            self._set_state(ConnectionState.CONNECTED)
            return result

        except HTTPStatusError as e:
            self._stats.sessions_failed += 1
            session_duration = time.monotonic() - session_start

            result = SessionResult(
                success=False,
                session_id=self._session_id or "",
                duration_seconds=session_duration,
                apdu_count=len(self._exchanges),
                exchanges=self._exchanges.copy(),
                error=f"HTTP {e.status_code}: {e.reason}",
                tls_info=self._connection_info,
            )

            logger.error(f"Session failed: HTTP {e.status_code}")
            self._set_state(ConnectionState.ERROR)
            return result

        except HTTPAdminError as e:
            self._stats.sessions_failed += 1
            session_duration = time.monotonic() - session_start

            result = SessionResult(
                success=False,
                session_id=self._session_id or "",
                duration_seconds=session_duration,
                apdu_count=len(self._exchanges),
                exchanges=self._exchanges.copy(),
                error=str(e),
                tls_info=self._connection_info,
            )

            logger.error(f"Session failed: {e}")
            self._set_state(ConnectionState.ERROR)
            return result

        except PSKTLSClientError as e:
            self._stats.sessions_failed += 1
            if isinstance(e, TimeoutError):
                self._stats.timeout_count += 1
                self._set_state(ConnectionState.TIMEOUT)
            else:
                self._set_state(ConnectionState.ERROR)

            session_duration = time.monotonic() - session_start
            result = SessionResult(
                success=False,
                session_id=self._session_id or "",
                duration_seconds=session_duration,
                apdu_count=len(self._exchanges),
                exchanges=self._exchanges.copy(),
                error=str(e),
                tls_info=self._connection_info,
            )

            logger.error(f"Session failed: {e}")
            return result

        except Exception as e:
            self._stats.sessions_failed += 1
            session_duration = time.monotonic() - session_start

            result = SessionResult(
                success=False,
                session_id=self._session_id or "",
                duration_seconds=session_duration,
                apdu_count=len(self._exchanges),
                exchanges=self._exchanges.copy(),
                error=f"Unexpected error: {e}",
                tls_info=self._connection_info,
            )

            logger.error(f"Session failed: {e}")
            self._set_state(ConnectionState.ERROR)
            return result

    async def disconnect(self) -> None:
        """Close connection gracefully."""
        if self._state == ConnectionState.IDLE:
            return

        self._set_state(ConnectionState.CLOSING)
        logger.info("Disconnecting...")

        if self._tls_client:
            await self._tls_client.close()
            self._tls_client = None

        self._http_client = None
        self._connection_info = None
        self._session_id = None

        self._set_state(ConnectionState.IDLE)
        logger.info("Disconnected")

    def reset(self) -> None:
        """Reset simulator state.

        Resets virtual UICC state and behavior controller stats.
        Does not affect connection state.
        """
        self._virtual_uicc.reset()
        self._behavior.reset_stats()
        self._exchanges = []
        logger.debug("Simulator state reset")

    def get_statistics(self) -> SimulatorStats:
        """Get copy of simulator statistics.

        Returns:
            SimulatorStats with current statistics.
        """
        return SimulatorStats(
            connections_attempted=self._stats.connections_attempted,
            connections_succeeded=self._stats.connections_succeeded,
            connections_failed=self._stats.connections_failed,
            connection_errors=self._stats.connection_errors.copy(),
            sessions_completed=self._stats.sessions_completed,
            sessions_failed=self._stats.sessions_failed,
            total_apdus_sent=self._stats.total_apdus_sent,
            total_apdus_received=self._stats.total_apdus_received,
            avg_connection_time_ms=self._stats.avg_connection_time_ms,
            avg_session_duration_ms=self._stats.avg_session_duration_ms,
            avg_apdu_response_time_ms=self._stats.avg_apdu_response_time_ms,
            error_responses=self._stats.error_responses.copy(),
            timeout_count=self._stats.timeout_count,
        )

    async def run_complete_session(self) -> SessionResult:
        """Connect, run session, and disconnect.

        Convenience method that performs complete session lifecycle.

        Returns:
            SessionResult with session outcome.

        Example:
            >>> result = await simulator.run_complete_session()
            >>> print(f"Success: {result.success}, APDUs: {result.apdu_count}")
        """
        try:
            if not await self.connect():
                return SessionResult(
                    success=False,
                    session_id=self._session_id or str(uuid.uuid4()),
                    error="Connection failed",
                )

            result = await self.run_session()
            return result

        finally:
            await self.disconnect()

    async def __aenter__(self) -> "MobileSimulator":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
