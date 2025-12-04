"""PC/SC Client for smart card communication.

This module provides a high-level interface to PC/SC readers and smart cards
using the pyscard library.

Example:
    ```python
    from cardlink.provisioner import PCSCClient

    # List available readers
    client = PCSCClient()
    readers = client.list_readers()
    print(f"Found {len(readers)} readers")

    # Connect to card
    client.connect(readers[0].name)
    print(f"Connected to: {client.card_info.atr_hex}")

    # Send APDU
    response = client.transmit(bytes.fromhex("00A4040007A0000000041010"))
    print(f"Response: {response.data.hex()} SW={response.sw:04X}")

    # Disconnect
    client.disconnect()
    ```
"""

import logging
import threading
from typing import Callable, List, Optional, Union

from cardlink.provisioner.atr_parser import ATRParser, parse_atr
from cardlink.provisioner.exceptions import (
    APDUError,
    CardNotFoundError,
    NotConnectedError,
    ProvisionerError,
    ReaderNotFoundError,
)
from cardlink.provisioner.models import (
    APDUResponse,
    CardInfo,
    Protocol,
    ReaderInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Card Observer Callback Type
# =============================================================================

CardEventCallback = Callable[["CardInfo", bool], None]  # card_info, is_insertion


# =============================================================================
# PC/SC Client
# =============================================================================


class PCSCClient:
    """High-level PC/SC client for smart card communication.

    This class provides a thread-safe interface to PC/SC readers and cards.
    It handles reader enumeration, card connection with protocol negotiation,
    APDU transmission with automatic GET RESPONSE handling, and card monitoring.

    Attributes:
        is_connected: Whether a card is currently connected.
        card_info: Information about the connected card (if any).
        reader_info: Information about the current reader (if any).

    Example:
        ```python
        client = PCSCClient()
        readers = client.list_readers()

        if readers:
            client.connect(readers[0].name)
            response = client.transmit(b"\\x00\\xA4\\x04\\x00\\x00")
            client.disconnect()
        ```
    """

    def __init__(self):
        """Initialize PC/SC client."""
        self._connection = None
        self._reader = None
        self._card_info: Optional[CardInfo] = None
        self._reader_info: Optional[ReaderInfo] = None
        self._lock = threading.Lock()
        self._monitor = None
        self._observer = None
        self._card_callbacks: List[CardEventCallback] = []
        self._atr_parser = ATRParser()

    @property
    def is_connected(self) -> bool:
        """Check if connected to a card."""
        return self._connection is not None

    @property
    def card_info(self) -> Optional[CardInfo]:
        """Get information about connected card."""
        return self._card_info

    @property
    def reader_info(self) -> Optional[ReaderInfo]:
        """Get information about current reader."""
        return self._reader_info

    def list_readers(self) -> List[ReaderInfo]:
        """List available PC/SC readers.

        Returns:
            List of ReaderInfo objects for each available reader.

        Raises:
            ProvisionerError: If PC/SC service is not available.
        """
        try:
            from smartcard.System import readers
            from smartcard.Exceptions import NoReadersException
        except ImportError as e:
            raise ProvisionerError(
                "pyscard not installed. Install with: pip install pyscard"
            ) from e

        try:
            reader_list = readers()
        except NoReadersException:
            return []
        except Exception as e:
            raise ProvisionerError(f"Failed to list readers: {e}") from e

        result = []
        for i, reader in enumerate(reader_list):
            name = str(reader)
            reader_info = ReaderInfo(
                name=name,
                index=i,
                has_card=self._reader_has_card(reader),
            )
            result.append(reader_info)

        logger.debug(f"Found {len(result)} PC/SC readers")
        return result

    def _reader_has_card(self, reader) -> bool:
        """Check if reader has a card inserted.

        Args:
            reader: pyscard reader object.

        Returns:
            True if card is present.
        """
        try:
            from smartcard.CardConnection import CardConnection

            connection = reader.createConnection()
            connection.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
            connection.disconnect()
            return True
        except Exception:
            return False

    def get_reader(self, name_or_index: Union[str, int]) -> ReaderInfo:
        """Get reader by name or index.

        Args:
            name_or_index: Reader name (string) or index (int).

        Returns:
            ReaderInfo for the specified reader.

        Raises:
            ReaderNotFoundError: If reader not found.
        """
        readers = self.list_readers()

        if isinstance(name_or_index, int):
            if 0 <= name_or_index < len(readers):
                return readers[name_or_index]
            raise ReaderNotFoundError(f"Reader index {name_or_index} out of range")

        # Search by name (partial match)
        name_lower = name_or_index.lower()
        for reader in readers:
            if name_lower in reader.name.lower():
                return reader

        raise ReaderNotFoundError(name_or_index)

    def connect(
        self,
        reader: Union[str, int, ReaderInfo],
        protocol: Optional[Protocol] = None,
    ) -> CardInfo:
        """Connect to a card in the specified reader.

        Args:
            reader: Reader name, index, or ReaderInfo object.
            protocol: Preferred protocol (T=0 or T=1). If None, auto-negotiate.

        Returns:
            CardInfo with ATR and detected card type.

        Raises:
            ReaderNotFoundError: If reader not found.
            CardNotFoundError: If no card in reader.
            ProvisionerError: If connection fails.
        """
        try:
            from smartcard.System import readers as get_readers
            from smartcard.CardConnection import CardConnection
            from smartcard.Exceptions import NoCardException, CardConnectionException
        except ImportError as e:
            raise ProvisionerError(
                "pyscard not installed. Install with: pip install pyscard"
            ) from e

        with self._lock:
            # Disconnect if already connected
            if self._connection:
                self._do_disconnect()

            # Resolve reader
            if isinstance(reader, ReaderInfo):
                reader_info = reader
            else:
                reader_info = self.get_reader(reader)

            # Get pyscard reader object
            try:
                reader_list = get_readers()
                pyscard_reader = None
                for r in reader_list:
                    if str(r) == reader_info.name:
                        pyscard_reader = r
                        break

                if pyscard_reader is None:
                    raise ReaderNotFoundError(reader_info.name)

            except Exception as e:
                raise ReaderNotFoundError(
                    reader_info.name, f"Error accessing reader: {e}"
                )

            # Create connection
            try:
                connection = pyscard_reader.createConnection()
            except Exception as e:
                raise ProvisionerError(f"Failed to create connection: {e}") from e

            # Determine protocol flags
            if protocol == Protocol.T0:
                proto_flag = CardConnection.T0_protocol
            elif protocol == Protocol.T1:
                proto_flag = CardConnection.T1_protocol
            else:
                # Auto-negotiate: try T=1 first, then T=0
                proto_flag = CardConnection.T0_protocol | CardConnection.T1_protocol

            # Connect
            try:
                connection.connect(proto_flag)
            except NoCardException:
                raise CardNotFoundError(reader_info.name)
            except CardConnectionException as e:
                raise ProvisionerError(f"Card connection failed: {e}") from e
            except Exception as e:
                raise ProvisionerError(f"Connection error: {e}") from e

            # Store connection
            self._connection = connection
            self._reader = pyscard_reader
            self._reader_info = reader_info

            # Get ATR and parse it
            atr_bytes = bytes(connection.getATR())
            atr_info = self._atr_parser.parse(atr_bytes)

            # Determine actual protocol
            actual_protocol = Protocol.T0
            if hasattr(connection, "getProtocol"):
                conn_proto = connection.getProtocol()
                if conn_proto == CardConnection.T1_protocol:
                    actual_protocol = Protocol.T1

            # Create card info
            self._card_info = CardInfo(
                atr=atr_bytes,
                atr_info=atr_info,
                protocol=actual_protocol,
                reader_name=reader_info.name,
            )

            logger.info(
                f"Connected to card in {reader_info.name} "
                f"(ATR: {self._card_info.atr_hex}, Protocol: {actual_protocol.name})"
            )

            return self._card_info

    def disconnect(self) -> None:
        """Disconnect from the current card.

        Safe to call even if not connected.
        """
        with self._lock:
            self._do_disconnect()

    def _do_disconnect(self) -> None:
        """Internal disconnect (must hold lock)."""
        if self._connection:
            try:
                self._connection.disconnect()
            except Exception as e:
                logger.debug(f"Error during disconnect: {e}")

            self._connection = None
            self._reader = None
            self._card_info = None
            logger.debug("Disconnected from card")

    def reconnect(
        self,
        protocol: Optional[Protocol] = None,
    ) -> CardInfo:
        """Reconnect to the card.

        Useful after a card reset or to change protocol.

        Args:
            protocol: Preferred protocol for reconnection.

        Returns:
            New CardInfo after reconnection.

        Raises:
            NotConnectedError: If no reader was previously connected.
        """
        with self._lock:
            if self._reader_info is None:
                raise NotConnectedError("reconnect")

            reader_info = self._reader_info
            self._do_disconnect()

        return self.connect(reader_info, protocol)

    def transmit(
        self,
        apdu: Union[bytes, str, list],
        auto_get_response: bool = True,
    ) -> APDUResponse:
        """Transmit APDU to the card.

        Args:
            apdu: APDU command as bytes, hex string, or list of ints.
            auto_get_response: Automatically handle GET RESPONSE (SW=61xx).

        Returns:
            APDUResponse with response data and status word.

        Raises:
            NotConnectedError: If not connected to a card.
            APDUError: If transmission fails.
        """
        # Convert to list of ints (required by pyscard)
        if isinstance(apdu, str):
            apdu = bytes.fromhex(apdu.replace(" ", ""))

        if isinstance(apdu, bytes):
            apdu_list = list(apdu)
        else:
            apdu_list = list(apdu)

        with self._lock:
            if not self._connection:
                raise NotConnectedError("transmit")

            try:
                response, sw1, sw2 = self._connection.transmit(apdu_list)
            except Exception as e:
                raise APDUError(str(e), bytes(apdu_list).hex()) from e

            # Convert response to bytes
            data = bytes(response)

            logger.debug(
                f"APDU: {bytes(apdu_list).hex().upper()} -> "
                f"{data.hex().upper()} SW={sw1:02X}{sw2:02X}"
            )

            # Handle GET RESPONSE for T=0
            if auto_get_response and sw1 == 0x61:
                get_response_apdu = [0x00, 0xC0, 0x00, 0x00, sw2]
                try:
                    response2, sw1, sw2 = self._connection.transmit(get_response_apdu)
                    data = bytes(response2)
                    logger.debug(
                        f"GET RESPONSE: {data.hex().upper()} SW={sw1:02X}{sw2:02X}"
                    )
                except Exception as e:
                    raise APDUError(f"GET RESPONSE failed: {e}") from e

            return APDUResponse(data=data, sw1=sw1, sw2=sw2)

    def transmit_raw(
        self,
        apdu: Union[bytes, str],
    ) -> APDUResponse:
        """Transmit APDU without automatic GET RESPONSE handling.

        Args:
            apdu: APDU command as bytes or hex string.

        Returns:
            APDUResponse with response data and status word.
        """
        return self.transmit(apdu, auto_get_response=False)

    def reset_card(self) -> CardInfo:
        """Perform warm reset of the card.

        Returns:
            CardInfo after reset.

        Raises:
            NotConnectedError: If not connected.
            ProvisionerError: If reset fails.
        """
        try:
            from smartcard.CardConnection import CardConnection
        except ImportError as e:
            raise ProvisionerError(
                "pyscard not installed. Install with: pip install pyscard"
            ) from e

        with self._lock:
            if not self._connection:
                raise NotConnectedError("reset_card")

            try:
                # Reconnect performs a reset
                self._connection.reconnect(
                    disposition=CardConnection.RESET_CARD,
                )

                # Update ATR info
                atr_bytes = bytes(self._connection.getATR())
                atr_info = self._atr_parser.parse(atr_bytes)

                self._card_info = CardInfo(
                    atr=atr_bytes,
                    atr_info=atr_info,
                    protocol=self._card_info.protocol if self._card_info else Protocol.T0,
                    reader_name=self._reader_info.name if self._reader_info else "",
                )

                logger.info(f"Card reset, new ATR: {self._card_info.atr_hex}")
                return self._card_info

            except Exception as e:
                raise ProvisionerError(f"Card reset failed: {e}") from e

    # =========================================================================
    # Card Monitoring
    # =========================================================================

    def start_monitoring(self) -> None:
        """Start monitoring for card insertion/removal events.

        Card events will be delivered to registered callbacks.

        Raises:
            ProvisionerError: If monitoring fails to start.
        """
        try:
            from smartcard.CardMonitoring import CardMonitor, CardObserver
        except ImportError as e:
            raise ProvisionerError(
                "pyscard not installed. Install with: pip install pyscard"
            ) from e

        if self._monitor is not None:
            logger.debug("Card monitoring already active")
            return

        class InternalObserver(CardObserver):
            def __init__(inner_self, client: "PCSCClient"):
                inner_self.client = client

            def update(inner_self, observable, actions):
                added_cards, removed_cards = actions
                for card in added_cards:
                    inner_self.client._on_card_inserted(card)
                for card in removed_cards:
                    inner_self.client._on_card_removed(card)

        try:
            self._observer = InternalObserver(self)
            self._monitor = CardMonitor()
            self._monitor.addObserver(self._observer)
            logger.info("Card monitoring started")
        except Exception as e:
            self._monitor = None
            self._observer = None
            raise ProvisionerError(f"Failed to start card monitoring: {e}") from e

    def stop_monitoring(self) -> None:
        """Stop monitoring for card events."""
        if self._monitor is not None:
            try:
                self._monitor.deleteObserver(self._observer)
            except Exception as e:
                logger.debug(f"Error stopping monitor: {e}")

            self._monitor = None
            self._observer = None
            logger.info("Card monitoring stopped")

    def on_card_event(self, callback: CardEventCallback) -> None:
        """Register callback for card insertion/removal events.

        Args:
            callback: Function called with (CardInfo, is_insertion) arguments.
        """
        self._card_callbacks.append(callback)

    def remove_card_callback(self, callback: CardEventCallback) -> None:
        """Remove a previously registered callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._card_callbacks:
            self._card_callbacks.remove(callback)

    def _on_card_inserted(self, card) -> None:
        """Handle card insertion event.

        Args:
            card: pyscard card object.
        """
        try:
            atr_bytes = bytes(card.atr)
            atr_info = self._atr_parser.parse(atr_bytes)

            card_info = CardInfo(
                atr=atr_bytes,
                atr_info=atr_info,
                protocol=Protocol.T0,  # Unknown until connected
                reader_name=str(card.reader),
            )

            logger.info(f"Card inserted in {card.reader}: {card_info.atr_hex}")

            for callback in self._card_callbacks:
                try:
                    callback(card_info, True)
                except Exception as e:
                    logger.error(f"Error in card callback: {e}")

        except Exception as e:
            logger.error(f"Error processing card insertion: {e}")

    def _on_card_removed(self, card) -> None:
        """Handle card removal event.

        Args:
            card: pyscard card object.
        """
        try:
            # Create minimal CardInfo for removed card
            atr_bytes = bytes(card.atr) if card.atr else b""

            card_info = CardInfo(
                atr=atr_bytes,
                atr_info=None,
                protocol=Protocol.T0,
                reader_name=str(card.reader),
            )

            logger.info(f"Card removed from {card.reader}")

            # If this was our connected card, mark as disconnected
            if self._reader_info and self._reader_info.name == str(card.reader):
                with self._lock:
                    self._connection = None
                    self._card_info = None

            for callback in self._card_callbacks:
                try:
                    callback(card_info, False)
                except Exception as e:
                    logger.error(f"Error in card callback: {e}")

        except Exception as e:
            logger.error(f"Error processing card removal: {e}")

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self) -> "PCSCClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensure cleanup."""
        self.stop_monitoring()
        self.disconnect()

    def __del__(self):
        """Destructor - ensure cleanup."""
        try:
            self.stop_monitoring()
            self.disconnect()
        except Exception:
            pass


# =============================================================================
# Convenience Functions
# =============================================================================


def list_readers() -> List[ReaderInfo]:
    """List available PC/SC readers.

    Returns:
        List of ReaderInfo objects.
    """
    client = PCSCClient()
    return client.list_readers()


def connect_card(
    reader: Union[str, int, None] = None,
    protocol: Optional[Protocol] = None,
) -> PCSCClient:
    """Create client and connect to card.

    Args:
        reader: Reader name, index, or None for first available.
        protocol: Preferred protocol (T=0 or T=1).

    Returns:
        Connected PCSCClient instance.

    Raises:
        ReaderNotFoundError: If no readers available.
        CardNotFoundError: If no card in reader.
    """
    client = PCSCClient()
    readers = client.list_readers()

    if not readers:
        raise ReaderNotFoundError("No PC/SC readers available")

    if reader is None:
        # Find first reader with a card
        for r in readers:
            if r.has_card:
                reader = r
                break
        else:
            reader = readers[0]

    client.connect(reader, protocol)
    return client
