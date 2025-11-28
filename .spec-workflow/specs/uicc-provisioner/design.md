# Design Document: UICC Provisioner

## Introduction

This document describes the technical design for the UICC Provisioner component of CardLink. The provisioner enables PC/SC-based smart card access to configure UICC cards for SCP81 OTA testing, including PSK keys, admin URLs, triggers, and BIP settings.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                       │
│                         (cardlink-provision)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                          Provisioner Core                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ProfileManager│  │ APDULogger │  │EventEmitter │  │ KeyManager  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│                         Card Operations Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  PSKConfig  │  │  URLConfig  │  │TriggerConfig│  │  BIPConfig  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│                       Security Domain Layer                                  │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                    SecureDomainManager                          │        │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │        │
│  │  │  SCP02    │  │  SCP03    │  │  PINAuth  │  │  ADMAuth  │    │        │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │        │
│  └─────────────────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│                           APDU Layer                                         │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                      APDUInterface                               │        │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │        │
│  │  │ TLVParser │  │SWDecoder  │  │APDUBuilder│  │ Scripting │    │        │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │        │
│  └─────────────────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│                          PC/SC Layer                                         │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                       PCSCClient                                 │        │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │        │
│  │  │ReaderMgr  │  │ CardConn  │  │ATRParser  │  │ProtocolMgr│    │        │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │        │
│  └─────────────────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│                        pyscard Library                                       │
│                    (smartcard.System, etc.)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility |
|-----------|----------------|
| **PCSCClient** | PC/SC reader management, card connection, low-level transmit |
| **APDUInterface** | APDU construction, transmission, response parsing |
| **SecureDomainManager** | Security Domain selection, secure channel establishment |
| **SCP02/SCP03** | Secure channel protocol implementations |
| **PSKConfig** | PSK identity and key provisioning |
| **URLConfig** | Admin server URL configuration |
| **TriggerConfig** | OTA trigger mechanism configuration |
| **BIPConfig** | BIP/CAT settings configuration |
| **ProfileManager** | Card profile save/load/apply operations |
| **KeyManager** | Cryptographic key handling and secure storage |
| **EventEmitter** | Event publication for external integration |

## Component Design

### 1. PCSCClient

Manages PC/SC reader discovery and card communication.

```python
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.CardMonitoring import CardMonitor, CardObserver
from typing import Optional, List, Callable
from dataclasses import dataclass
import threading

@dataclass
class ReaderInfo:
    name: str
    index: int
    has_card: bool
    atr: Optional[bytes] = None

@dataclass
class CardInfo:
    atr: bytes
    protocol: int  # T=0 or T=1
    reader_name: str
    historical_bytes: bytes

class PCSCClient:
    """PC/SC reader and card management."""

    def __init__(self, event_emitter: Optional['EventEmitter'] = None):
        self._context = None
        self._connection: Optional[CardConnection] = None
        self._current_reader: Optional[str] = None
        self._event_emitter = event_emitter
        self._card_monitor: Optional[CardMonitor] = None
        self._lock = threading.Lock()

    def list_readers(self) -> List[ReaderInfo]:
        """List all available PC/SC readers."""
        reader_list = readers()
        result = []
        for idx, reader in enumerate(reader_list):
            info = ReaderInfo(
                name=str(reader),
                index=idx,
                has_card=self._check_card_present(reader)
            )
            if info.has_card:
                info.atr = self._get_atr(reader)
            result.append(info)
        return result

    def connect(self, reader_name: str, protocol: int = None) -> CardInfo:
        """Connect to card in specified reader."""
        reader_list = readers()
        target_reader = None
        for reader in reader_list:
            if str(reader) == reader_name or reader_name in str(reader):
                target_reader = reader
                break

        if not target_reader:
            raise ReaderNotFoundError(f"Reader not found: {reader_name}")

        connection = target_reader.createConnection()
        if protocol:
            connection.connect(protocol)
        else:
            connection.connect()

        self._connection = connection
        self._current_reader = str(target_reader)

        atr = bytes(connection.getATR())
        card_info = CardInfo(
            atr=atr,
            protocol=connection.getProtocol(),
            reader_name=self._current_reader,
            historical_bytes=self._extract_historical_bytes(atr)
        )

        if self._event_emitter:
            self._event_emitter.emit('card_connected', card_info)

        return card_info

    def disconnect(self) -> None:
        """Disconnect from current card."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None
            if self._event_emitter:
                self._event_emitter.emit('card_disconnected', {
                    'reader': self._current_reader
                })

    def transmit(self, apdu: bytes) -> tuple[bytes, int, int]:
        """Transmit APDU and return (data, SW1, SW2)."""
        if not self._connection:
            raise NotConnectedError("No card connection")

        with self._lock:
            response, sw1, sw2 = self._connection.transmit(list(apdu))

            # Handle GET RESPONSE for T=0
            if sw1 == 0x61:
                get_response = [0x00, 0xC0, 0x00, 0x00, sw2]
                response, sw1, sw2 = self._connection.transmit(get_response)

            return bytes(response), sw1, sw2

    def start_monitoring(self,
                         on_insert: Callable[[str, bytes], None],
                         on_remove: Callable[[str], None]) -> None:
        """Start monitoring for card insertion/removal."""
        class Observer(CardObserver):
            def __init__(self, insert_cb, remove_cb):
                self._insert_cb = insert_cb
                self._remove_cb = remove_cb

            def update(self, observable, actions):
                added, removed = actions
                for card in added:
                    self._insert_cb(str(card.reader), bytes(card.atr))
                for card in removed:
                    self._remove_cb(str(card.reader))

        self._card_monitor = CardMonitor()
        self._card_monitor.addObserver(Observer(on_insert, on_remove))

    def stop_monitoring(self) -> None:
        """Stop card monitoring."""
        if self._card_monitor:
            self._card_monitor.deleteObservers()
            self._card_monitor = None

    def _check_card_present(self, reader) -> bool:
        """Check if card is present in reader."""
        try:
            conn = reader.createConnection()
            conn.connect()
            conn.disconnect()
            return True
        except:
            return False

    def _get_atr(self, reader) -> Optional[bytes]:
        """Get ATR from card in reader."""
        try:
            conn = reader.createConnection()
            conn.connect()
            atr = bytes(conn.getATR())
            conn.disconnect()
            return atr
        except:
            return None

    def _extract_historical_bytes(self, atr: bytes) -> bytes:
        """Extract historical bytes from ATR."""
        if len(atr) < 2:
            return b''
        # T0 byte contains number of historical bytes in lower nibble
        t0 = atr[1]
        num_historical = t0 & 0x0F
        # Historical bytes are at the end before TCK (if present)
        return atr[-(num_historical + 1):-1] if num_historical > 0 else b''


class ATRParser:
    """Parse and interpret ATR (Answer To Reset)."""

    @staticmethod
    def parse(atr: bytes) -> dict:
        """Parse ATR into structured data."""
        result = {
            'raw': atr.hex().upper(),
            'ts': atr[0] if len(atr) > 0 else None,
            't0': atr[1] if len(atr) > 1 else None,
            'protocols': [],
            'historical_bytes': b'',
            'card_type': 'Unknown'
        }

        if result['ts'] == 0x3B:
            result['convention'] = 'Direct'
        elif result['ts'] == 0x3F:
            result['convention'] = 'Inverse'

        # Determine supported protocols
        if result['t0']:
            t0 = result['t0']
            if t0 & 0x80:  # TA1 present
                result['protocols'].append('T=0')
            # Further protocol detection from TD bytes...

        # Identify card type from historical bytes
        result['card_type'] = ATRParser._identify_card_type(atr)

        return result

    @staticmethod
    def _identify_card_type(atr: bytes) -> str:
        """Identify card type from ATR patterns."""
        atr_hex = atr.hex().upper()

        # Common UICC/SIM patterns
        if '80318065' in atr_hex:
            return 'UICC (3GPP)'
        if '8031A065' in atr_hex:
            return 'USIM'
        if 'A000000087' in atr_hex:
            return 'eUICC'

        return 'Smart Card'
```

### 2. APDUInterface

Handles APDU construction, transmission, and response parsing.

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import IntEnum

class INS(IntEnum):
    """Common instruction bytes."""
    SELECT = 0xA4
    READ_BINARY = 0xB0
    UPDATE_BINARY = 0xD6
    READ_RECORD = 0xB2
    UPDATE_RECORD = 0xDC
    GET_RESPONSE = 0xC0
    VERIFY = 0x20
    GET_STATUS = 0xF2
    INSTALL = 0xE6
    DELETE = 0xE4
    PUT_KEY = 0xD8
    SET_STATUS = 0xF0
    INITIALIZE_UPDATE = 0x50
    EXTERNAL_AUTHENTICATE = 0x82

@dataclass
class APDUCommand:
    """APDU command structure."""
    cla: int
    ins: int
    p1: int
    p2: int
    data: bytes = b''
    le: Optional[int] = None

    def to_bytes(self) -> bytes:
        """Convert to byte array for transmission."""
        cmd = bytes([self.cla, self.ins, self.p1, self.p2])

        if self.data:
            cmd += bytes([len(self.data)]) + self.data

        if self.le is not None:
            cmd += bytes([self.le])

        return cmd

@dataclass
class APDUResponse:
    """APDU response structure."""
    data: bytes
    sw1: int
    sw2: int

    @property
    def sw(self) -> int:
        """Combined status word."""
        return (self.sw1 << 8) | self.sw2

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.sw1 == 0x90 and self.sw2 == 0x00

    @property
    def status_message(self) -> str:
        """Human-readable status message."""
        return SWDecoder.decode(self.sw1, self.sw2)


class SWDecoder:
    """Decode status words to human-readable messages."""

    STATUS_WORDS = {
        0x9000: "Success",
        0x6283: "Selected file invalidated",
        0x6300: "Verification failed",
        0x63C0: "Verification failed, 0 retries left",
        0x63C1: "Verification failed, 1 retry left",
        0x63C2: "Verification failed, 2 retries left",
        0x63C3: "Verification failed, 3 retries left",
        0x6581: "Memory failure",
        0x6700: "Wrong length",
        0x6882: "Secure messaging not supported",
        0x6982: "Security status not satisfied",
        0x6983: "Authentication method blocked",
        0x6984: "Referenced data invalidated",
        0x6985: "Conditions of use not satisfied",
        0x6986: "Command not allowed",
        0x6A80: "Incorrect parameters in data field",
        0x6A81: "Function not supported",
        0x6A82: "File or application not found",
        0x6A83: "Record not found",
        0x6A84: "Not enough memory space",
        0x6A86: "Incorrect P1-P2",
        0x6A88: "Referenced data not found",
        0x6B00: "Wrong parameters P1-P2",
        0x6D00: "Instruction not supported",
        0x6E00: "Class not supported",
        0x6F00: "No precise diagnosis",
    }

    @classmethod
    def decode(cls, sw1: int, sw2: int) -> str:
        """Decode SW1 SW2 to message."""
        sw = (sw1 << 8) | sw2

        if sw in cls.STATUS_WORDS:
            return cls.STATUS_WORDS[sw]

        # Handle ranges
        if sw1 == 0x61:
            return f"Response available: {sw2} bytes"
        if sw1 == 0x6C:
            return f"Wrong Le field, expected {sw2}"
        if sw1 == 0x63 and (sw2 & 0xF0) == 0xC0:
            return f"Verification failed, {sw2 & 0x0F} retries left"

        return f"Unknown status: {sw1:02X}{sw2:02X}"


class APDUInterface:
    """High-level APDU interface."""

    def __init__(self, pcsc_client: PCSCClient,
                 logger: Optional['APDULogger'] = None,
                 event_emitter: Optional['EventEmitter'] = None):
        self._client = pcsc_client
        self._logger = logger
        self._event_emitter = event_emitter

    def send(self, command: APDUCommand) -> APDUResponse:
        """Send APDU command and get response."""
        cmd_bytes = command.to_bytes()

        if self._logger:
            self._logger.log_command(cmd_bytes)

        data, sw1, sw2 = self._client.transmit(cmd_bytes)

        response = APDUResponse(data=data, sw1=sw1, sw2=sw2)

        if self._logger:
            self._logger.log_response(response)

        if self._event_emitter:
            self._event_emitter.emit('apdu_exchange', {
                'command': cmd_bytes.hex().upper(),
                'response': data.hex().upper(),
                'sw': f"{sw1:02X}{sw2:02X}"
            })

        return response

    def send_raw(self, apdu_hex: str) -> APDUResponse:
        """Send raw APDU from hex string."""
        apdu_bytes = bytes.fromhex(apdu_hex.replace(' ', ''))
        data, sw1, sw2 = self._client.transmit(apdu_bytes)
        return APDUResponse(data=data, sw1=sw1, sw2=sw2)

    def select_by_aid(self, aid: bytes) -> APDUResponse:
        """SELECT application by AID."""
        cmd = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x04,  # Select by name
            p2=0x00,  # First or only occurrence
            data=aid,
            le=0x00
        )
        return self.send(cmd)

    def select_by_path(self, path: List[int]) -> APDUResponse:
        """SELECT file by path."""
        data = b''.join(fid.to_bytes(2, 'big') for fid in path)
        cmd = APDUCommand(
            cla=0x00,
            ins=INS.SELECT,
            p1=0x08,  # Select by path from MF
            p2=0x04,  # Return FCP template
            data=data
        )
        return self.send(cmd)

    def read_binary(self, offset: int = 0, length: int = 0) -> APDUResponse:
        """READ BINARY from current file."""
        cmd = APDUCommand(
            cla=0x00,
            ins=INS.READ_BINARY,
            p1=(offset >> 8) & 0x7F,
            p2=offset & 0xFF,
            le=length if length else 0x00
        )
        return self.send(cmd)

    def update_binary(self, offset: int, data: bytes) -> APDUResponse:
        """UPDATE BINARY in current file."""
        cmd = APDUCommand(
            cla=0x00,
            ins=INS.UPDATE_BINARY,
            p1=(offset >> 8) & 0x7F,
            p2=offset & 0xFF,
            data=data
        )
        return self.send(cmd)

    def verify_pin(self, pin: bytes, pin_ref: int = 0x01) -> APDUResponse:
        """VERIFY PIN."""
        cmd = APDUCommand(
            cla=0x00,
            ins=INS.VERIFY,
            p1=0x00,
            p2=pin_ref,
            data=pin
        )
        return self.send(cmd)

    def get_status(self, p1: int, p2: int, aid_filter: bytes = b'') -> APDUResponse:
        """GET STATUS for Security Domain."""
        cmd = APDUCommand(
            cla=0x80,
            ins=INS.GET_STATUS,
            p1=p1,
            p2=p2,
            data=bytes([0x4F, len(aid_filter)]) + aid_filter if aid_filter else bytes([0x4F, 0x00]),
            le=0x00
        )
        return self.send(cmd)


class TLVParser:
    """Parse and build TLV (Tag-Length-Value) structures."""

    @staticmethod
    def parse(data: bytes) -> Dict[int, bytes]:
        """Parse TLV data into dictionary."""
        result = {}
        offset = 0

        while offset < len(data):
            # Parse tag (1 or 2 bytes)
            tag = data[offset]
            offset += 1
            if (tag & 0x1F) == 0x1F:  # Two-byte tag
                tag = (tag << 8) | data[offset]
                offset += 1

            # Parse length (1 or more bytes)
            length = data[offset]
            offset += 1
            if length == 0x81:
                length = data[offset]
                offset += 1
            elif length == 0x82:
                length = (data[offset] << 8) | data[offset + 1]
                offset += 2

            # Extract value
            value = data[offset:offset + length]
            offset += length

            result[tag] = value

        return result

    @staticmethod
    def build(tag: int, value: bytes) -> bytes:
        """Build TLV from tag and value."""
        result = b''

        # Encode tag
        if tag > 0xFF:
            result += bytes([(tag >> 8) & 0xFF, tag & 0xFF])
        else:
            result += bytes([tag])

        # Encode length
        length = len(value)
        if length < 0x80:
            result += bytes([length])
        elif length < 0x100:
            result += bytes([0x81, length])
        else:
            result += bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])

        # Append value
        result += value

        return result
```

### 3. SecureDomainManager

Manages Security Domain operations and secure channel establishment.

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import IntEnum
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class LifeCycleState(IntEnum):
    """Security Domain life cycle states."""
    OP_READY = 0x01
    INITIALIZED = 0x07
    SECURED = 0x0F
    CARD_LOCKED = 0x7F
    TERMINATED = 0xFF

@dataclass
class SecurityDomainInfo:
    """Information about a Security Domain."""
    aid: bytes
    life_cycle_state: LifeCycleState
    privileges: int
    associated_sd: Optional[bytes] = None

class SecureDomainManager:
    """Manages Security Domain operations."""

    ISD_AID = bytes.fromhex('A000000151000000')

    def __init__(self, apdu_interface: APDUInterface):
        self._apdu = apdu_interface
        self._secure_channel: Optional['SecureChannel'] = None
        self._current_sd: Optional[bytes] = None

    def select_isd(self) -> APDUResponse:
        """Select Issuer Security Domain."""
        response = self._apdu.select_by_aid(self.ISD_AID)
        if response.is_success:
            self._current_sd = self.ISD_AID
        return response

    def select_sd(self, aid: bytes) -> APDUResponse:
        """Select a Security Domain by AID."""
        response = self._apdu.select_by_aid(aid)
        if response.is_success:
            self._current_sd = aid
        return response

    def get_status_isd(self) -> List[SecurityDomainInfo]:
        """Get status of ISD and associated SDs."""
        response = self._apdu.get_status(0x80, 0x00)
        return self._parse_get_status_response(response.data)

    def get_status_apps(self) -> List[dict]:
        """Get status of applications."""
        response = self._apdu.get_status(0x40, 0x00)
        return self._parse_get_status_response(response.data)

    def authenticate_scp02(self, keys: 'SCPKeys') -> bool:
        """Establish SCP02 secure channel."""
        scp02 = SCP02(self._apdu, keys)
        if scp02.initialize():
            self._secure_channel = scp02
            return True
        return False

    def authenticate_scp03(self, keys: 'SCPKeys') -> bool:
        """Establish SCP03 secure channel."""
        scp03 = SCP03(self._apdu, keys)
        if scp03.initialize():
            self._secure_channel = scp03
            return True
        return False

    def send_secured(self, command: APDUCommand) -> APDUResponse:
        """Send command through secure channel."""
        if not self._secure_channel:
            raise SecurityError("No secure channel established")
        return self._secure_channel.send(command)

    def install_for_install(self, load_aid: bytes, module_aid: bytes,
                           instance_aid: bytes, privileges: int,
                           parameters: bytes = b'') -> APDUResponse:
        """INSTALL [for install] command."""
        data = (
            bytes([len(load_aid)]) + load_aid +
            bytes([len(module_aid)]) + module_aid +
            bytes([len(instance_aid)]) + instance_aid +
            bytes([0x01, privileges]) +
            bytes([len(parameters)]) + parameters +
            bytes([0x00])  # Token length
        )
        cmd = APDUCommand(
            cla=0x80,
            ins=INS.INSTALL,
            p1=0x04,  # For install
            p2=0x00,
            data=data
        )
        return self.send_secured(cmd) if self._secure_channel else self._apdu.send(cmd)

    def delete(self, aid: bytes, cascade: bool = False) -> APDUResponse:
        """DELETE command."""
        data = TLVParser.build(0x4F, aid)
        cmd = APDUCommand(
            cla=0x80,
            ins=INS.DELETE,
            p1=0x00,
            p2=0x80 if cascade else 0x00,
            data=data
        )
        return self.send_secured(cmd) if self._secure_channel else self._apdu.send(cmd)

    def put_key(self, key_version: int, key_index: int,
                key_type: int, key_data: bytes) -> APDUResponse:
        """PUT KEY command."""
        # Build key data block
        key_block = bytes([key_version, key_type, len(key_data)]) + key_data

        cmd = APDUCommand(
            cla=0x80,
            ins=INS.PUT_KEY,
            p1=key_version,
            p2=key_index,
            data=key_block
        )
        return self.send_secured(cmd)

    def _parse_get_status_response(self, data: bytes) -> List[SecurityDomainInfo]:
        """Parse GET STATUS response."""
        result = []
        offset = 0

        while offset < len(data):
            entry_len = data[offset]
            offset += 1

            entry_data = data[offset:offset + entry_len]
            offset += entry_len

            # Parse TLV in entry
            tlv = TLVParser.parse(entry_data)

            if 0x4F in tlv:
                info = SecurityDomainInfo(
                    aid=tlv[0x4F],
                    life_cycle_state=LifeCycleState(tlv.get(0x9F70, b'\x00')[0] if 0x9F70 in tlv else 0),
                    privileges=tlv.get(0xC5, b'\x00')[0] if 0xC5 in tlv else 0
                )
                result.append(info)

        return result


@dataclass
class SCPKeys:
    """Secure Channel Protocol keys."""
    enc: bytes  # Encryption key
    mac: bytes  # MAC key
    dek: bytes  # Data encryption key (for PUT KEY)
    key_version: int = 0x01

    @classmethod
    def default_test_keys(cls) -> 'SCPKeys':
        """Return default test keys (GlobalPlatform test keys)."""
        default_key = bytes.fromhex('404142434445464748494A4B4C4D4E4F')
        return cls(enc=default_key, mac=default_key, dek=default_key)


class SCP02:
    """SCP02 secure channel implementation."""

    def __init__(self, apdu_interface: APDUInterface, keys: SCPKeys):
        self._apdu = apdu_interface
        self._keys = keys
        self._session_keys: Optional[dict] = None
        self._mac_chain: bytes = bytes(8)

    def initialize(self) -> bool:
        """Initialize SCP02 secure channel."""
        # INITIALIZE UPDATE
        host_challenge = os.urandom(8)
        cmd = APDUCommand(
            cla=0x80,
            ins=INS.INITIALIZE_UPDATE,
            p1=self._keys.key_version,
            p2=0x00,
            data=host_challenge,
            le=0x00
        )
        response = self._apdu.send(cmd)

        if not response.is_success:
            return False

        # Parse response
        if len(response.data) < 28:
            return False

        key_diversification = response.data[0:10]
        key_version = response.data[10]
        scp_id = response.data[11]
        sequence_counter = response.data[12:14]
        card_challenge = response.data[14:20]
        card_cryptogram = response.data[20:28]

        # Derive session keys
        self._session_keys = self._derive_session_keys(sequence_counter)

        # Verify card cryptogram
        if not self._verify_card_cryptogram(host_challenge, sequence_counter,
                                           card_challenge, card_cryptogram):
            return False

        # Calculate host cryptogram
        host_cryptogram = self._calculate_host_cryptogram(
            host_challenge, sequence_counter, card_challenge
        )

        # EXTERNAL AUTHENTICATE
        cmd = APDUCommand(
            cla=0x84,
            ins=INS.EXTERNAL_AUTHENTICATE,
            p1=0x01,  # C-MAC
            p2=0x00,
            data=host_cryptogram
        )
        # Add C-MAC
        cmd_with_mac = self._add_cmac(cmd)
        response = self._apdu.send(cmd_with_mac)

        return response.is_success

    def send(self, command: APDUCommand) -> APDUResponse:
        """Send command with secure channel protection."""
        secured_cmd = self._add_cmac(command)
        return self._apdu.send(secured_cmd)

    def _derive_session_keys(self, sequence_counter: bytes) -> dict:
        """Derive session keys from static keys."""
        # Simplified key derivation (actual implementation uses full derivation)
        derivation_data = bytes([0x01, 0x82]) + sequence_counter + bytes(12)

        cipher = Cipher(algorithms.TripleDES(self._keys.enc + self._keys.enc[:8]),
                       modes.CBC(bytes(8)), backend=default_backend())
        encryptor = cipher.encryptor()
        s_enc = encryptor.update(derivation_data) + encryptor.finalize()

        derivation_data = bytes([0x01, 0x01]) + sequence_counter + bytes(12)
        cipher = Cipher(algorithms.TripleDES(self._keys.mac + self._keys.mac[:8]),
                       modes.CBC(bytes(8)), backend=default_backend())
        encryptor = cipher.encryptor()
        s_mac = encryptor.update(derivation_data) + encryptor.finalize()

        return {'enc': s_enc[:16], 'mac': s_mac[:16]}

    def _verify_card_cryptogram(self, host_challenge: bytes, sequence_counter: bytes,
                                card_challenge: bytes, card_cryptogram: bytes) -> bool:
        """Verify card cryptogram."""
        # Calculate expected cryptogram
        data = host_challenge + sequence_counter + card_challenge
        data = data + bytes(24 - len(data))  # Pad to 24 bytes

        cipher = Cipher(algorithms.TripleDES(self._session_keys['enc'] + self._session_keys['enc'][:8]),
                       modes.CBC(bytes(8)), backend=default_backend())
        encryptor = cipher.encryptor()
        result = encryptor.update(data) + encryptor.finalize()

        return result[-8:] == card_cryptogram

    def _calculate_host_cryptogram(self, host_challenge: bytes,
                                   sequence_counter: bytes,
                                   card_challenge: bytes) -> bytes:
        """Calculate host cryptogram."""
        data = sequence_counter + card_challenge + host_challenge
        data = data + bytes(24 - len(data))

        cipher = Cipher(algorithms.TripleDES(self._session_keys['enc'] + self._session_keys['enc'][:8]),
                       modes.CBC(bytes(8)), backend=default_backend())
        encryptor = cipher.encryptor()
        result = encryptor.update(data) + encryptor.finalize()

        return result[-8:]

    def _add_cmac(self, command: APDUCommand) -> APDUCommand:
        """Add C-MAC to command."""
        # Build data for MAC calculation
        cmd_bytes = command.to_bytes()

        # Modify CLA to indicate secure messaging
        new_cla = command.cla | 0x04

        # Calculate MAC
        mac_input = self._mac_chain + bytes([new_cla]) + cmd_bytes[1:]
        mac_input = self._pad_iso9797(mac_input)

        cipher = Cipher(algorithms.TripleDES(self._session_keys['mac'] + self._session_keys['mac'][:8]),
                       modes.CBC(bytes(8)), backend=default_backend())
        encryptor = cipher.encryptor()
        result = encryptor.update(mac_input) + encryptor.finalize()

        c_mac = result[-8:]
        self._mac_chain = c_mac

        # Return new command with MAC appended
        return APDUCommand(
            cla=new_cla,
            ins=command.ins,
            p1=command.p1,
            p2=command.p2,
            data=command.data + c_mac,
            le=command.le
        )

    def _pad_iso9797(self, data: bytes) -> bytes:
        """ISO 9797-1 Method 2 padding."""
        padded = data + bytes([0x80])
        while len(padded) % 8 != 0:
            padded += bytes([0x00])
        return padded


class SCP03:
    """SCP03 secure channel implementation (AES-based)."""

    def __init__(self, apdu_interface: APDUInterface, keys: SCPKeys):
        self._apdu = apdu_interface
        self._keys = keys
        self._session_keys: Optional[dict] = None
        self._counter: int = 0

    def initialize(self) -> bool:
        """Initialize SCP03 secure channel."""
        # Similar to SCP02 but with AES and different key derivation
        host_challenge = os.urandom(8)
        cmd = APDUCommand(
            cla=0x80,
            ins=INS.INITIALIZE_UPDATE,
            p1=self._keys.key_version,
            p2=0x00,
            data=host_challenge,
            le=0x00
        )
        response = self._apdu.send(cmd)

        if not response.is_success or len(response.data) < 32:
            return False

        # Parse response and derive keys (SCP03 specific)
        # ... implementation details ...

        return True

    def send(self, command: APDUCommand) -> APDUResponse:
        """Send command with SCP03 protection."""
        # Add AES-CMAC
        # ... implementation details ...
        return self._apdu.send(command)
```

### 4. PSKConfig

Handles PSK key provisioning on the UICC.

```python
from dataclasses import dataclass
from typing import Optional
import os
import secrets

@dataclass
class PSKConfiguration:
    """PSK configuration data."""
    identity: bytes
    key: bytes
    key_size: int

    @classmethod
    def generate(cls, identity: str, key_size: int = 32) -> 'PSKConfiguration':
        """Generate new PSK with random key."""
        if key_size not in (16, 32, 64):
            raise ValueError("Key size must be 16, 32, or 64 bytes")

        return cls(
            identity=identity.encode('utf-8'),
            key=secrets.token_bytes(key_size),
            key_size=key_size
        )

    @classmethod
    def from_hex(cls, identity: str, key_hex: str) -> 'PSKConfiguration':
        """Create PSK from hex key string."""
        key = bytes.fromhex(key_hex.replace(' ', ''))
        return cls(
            identity=identity.encode('utf-8'),
            key=key,
            key_size=len(key)
        )


class PSKConfig:
    """Configure PSK on UICC card."""

    # File IDs for PSK storage (vendor-specific, example values)
    EF_PSK_ID = 0x6F01
    EF_PSK_KEY = 0x6F02

    def __init__(self, apdu_interface: APDUInterface,
                 sd_manager: SecureDomainManager):
        self._apdu = apdu_interface
        self._sd = sd_manager

    def configure(self, psk: PSKConfiguration) -> bool:
        """Configure PSK identity and key on card."""
        # Store PSK identity
        if not self._write_psk_identity(psk.identity):
            return False

        # Store PSK key
        if not self._write_psk_key(psk.key):
            return False

        return True

    def read_configuration(self) -> Optional[PSKConfiguration]:
        """Read current PSK configuration from card."""
        identity = self._read_psk_identity()
        if identity is None:
            return None

        # Note: Key should not be readable for security
        # We can only verify it exists
        key_exists = self._verify_psk_key_exists()

        if not key_exists:
            return None

        return PSKConfiguration(
            identity=identity,
            key=b'',  # Key is write-only
            key_size=0
        )

    def verify(self, psk: PSKConfiguration) -> bool:
        """Verify PSK configuration matches."""
        current = self.read_configuration()
        if current is None:
            return False

        return current.identity == psk.identity

    def _write_psk_identity(self, identity: bytes) -> bool:
        """Write PSK identity to card."""
        # Select PSK identity file
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_ID])
        if not response.is_success:
            # Try to create file if it doesn't exist
            if not self._create_psk_file(self.EF_PSK_ID, len(identity)):
                return False
            response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_ID])

        # Write identity
        response = self._apdu.update_binary(0, identity)
        return response.is_success

    def _write_psk_key(self, key: bytes) -> bool:
        """Write PSK key to card."""
        # Select PSK key file
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_KEY])
        if not response.is_success:
            if not self._create_psk_file(self.EF_PSK_KEY, len(key)):
                return False
            response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_KEY])

        # Write key (may require secure channel)
        response = self._apdu.update_binary(0, key)
        return response.is_success

    def _read_psk_identity(self) -> Optional[bytes]:
        """Read PSK identity from card."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_ID])
        if not response.is_success:
            return None

        response = self._apdu.read_binary(0, 0)
        if not response.is_success:
            return None

        # Strip padding
        return response.data.rstrip(b'\xFF').rstrip(b'\x00')

    def _verify_psk_key_exists(self) -> bool:
        """Verify PSK key file exists and has content."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_PSK_KEY])
        return response.is_success

    def _create_psk_file(self, fid: int, size: int) -> bool:
        """Create PSK file on card."""
        # CREATE FILE command (may require secure channel)
        # Implementation depends on card profile
        return False


class KeyManager:
    """Secure key handling utilities."""

    @staticmethod
    def generate_random_key(size: int) -> bytes:
        """Generate cryptographically secure random key."""
        return secrets.token_bytes(size)

    @staticmethod
    def derive_key(master_key: bytes, label: bytes, context: bytes,
                   output_size: int) -> bytes:
        """Derive key using HKDF."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=output_size,
            salt=None,
            info=label + context,
            backend=default_backend()
        )
        return hkdf.derive(master_key)

    @staticmethod
    def secure_compare(a: bytes, b: bytes) -> bool:
        """Constant-time comparison to prevent timing attacks."""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0

    @staticmethod
    def secure_erase(data: bytearray) -> None:
        """Securely erase sensitive data from memory."""
        for i in range(len(data)):
            data[i] = 0
```

### 5. URLConfig

Configures admin server URL on the UICC.

```python
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

@dataclass
class URLConfiguration:
    """Admin server URL configuration."""
    url: str
    scheme: str
    host: str
    port: int
    path: str

    @classmethod
    def from_url(cls, url: str) -> 'URLConfiguration':
        """Parse URL into configuration."""
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("URL must use http or https scheme")

        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == 'https' else 80

        return cls(
            url=url,
            scheme=parsed.scheme,
            host=parsed.hostname,
            port=port,
            path=parsed.path or '/'
        )

    def to_tlv(self) -> bytes:
        """Encode URL as TLV for card storage."""
        url_bytes = self.url.encode('utf-8')
        return TLVParser.build(0x5A, url_bytes)  # Example tag


class URLConfig:
    """Configure admin server URL on UICC."""

    EF_ADMIN_URL = 0x6F03
    MAX_URL_LENGTH = 255

    def __init__(self, apdu_interface: APDUInterface):
        self._apdu = apdu_interface

    def configure(self, config: URLConfiguration) -> bool:
        """Store admin URL on card."""
        if len(config.url) > self.MAX_URL_LENGTH:
            raise ValueError(f"URL exceeds maximum length of {self.MAX_URL_LENGTH}")

        # Select URL file
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_ADMIN_URL])
        if not response.is_success:
            return False

        # Encode and write
        url_data = config.to_tlv()
        response = self._apdu.update_binary(0, url_data)

        return response.is_success

    def read_configuration(self) -> Optional[URLConfiguration]:
        """Read current URL configuration."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_ADMIN_URL])
        if not response.is_success:
            return None

        response = self._apdu.read_binary(0, 0)
        if not response.is_success:
            return None

        # Parse TLV
        tlv = TLVParser.parse(response.data)
        if 0x5A not in tlv:
            return None

        url_str = tlv[0x5A].decode('utf-8').rstrip('\x00')
        return URLConfiguration.from_url(url_str)

    def validate(self, url: str) -> bool:
        """Validate URL format."""
        try:
            config = URLConfiguration.from_url(url)
            return len(url) <= self.MAX_URL_LENGTH
        except:
            return False
```

### 6. TriggerConfig

Configures OTA trigger mechanisms on the UICC.

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import IntEnum

class TriggerType(IntEnum):
    """OTA trigger types."""
    SMS_PP = 0x01
    POLLING = 0x02
    BIP_PUSH = 0x03

@dataclass
class SMSTriggerConfig:
    """SMS-PP trigger configuration."""
    tar: bytes  # Toolkit Application Reference (3 bytes)
    originating_address: Optional[str] = None
    kic: Optional[bytes] = None  # Ciphering key
    kid: Optional[bytes] = None  # Signing key
    counter: int = 0
    security_level: int = 0x00

@dataclass
class PollTriggerConfig:
    """Polling trigger configuration."""
    interval_seconds: int
    enabled: bool = True

@dataclass
class TriggerConfiguration:
    """Complete trigger configuration."""
    trigger_type: TriggerType
    sms_config: Optional[SMSTriggerConfig] = None
    poll_config: Optional[PollTriggerConfig] = None


class TriggerConfig:
    """Configure OTA triggers on UICC."""

    EF_TRIGGER_CONFIG = 0x6F04

    def __init__(self, apdu_interface: APDUInterface):
        self._apdu = apdu_interface

    def configure_sms_trigger(self, config: SMSTriggerConfig) -> bool:
        """Configure SMS-PP trigger."""
        # Build trigger data TLV
        data = b''
        data += TLVParser.build(0x80, config.tar)  # TAR
        data += TLVParser.build(0x81, bytes([config.security_level]))

        if config.kic:
            data += TLVParser.build(0x82, config.kic)
        if config.kid:
            data += TLVParser.build(0x83, config.kid)
        if config.originating_address:
            data += TLVParser.build(0x84, config.originating_address.encode())

        data += TLVParser.build(0x85, config.counter.to_bytes(5, 'big'))

        # Write to card
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_TRIGGER_CONFIG])
        if not response.is_success:
            return False

        trigger_tlv = TLVParser.build(0xA0, data)  # SMS trigger wrapper
        response = self._apdu.update_binary(0, trigger_tlv)

        return response.is_success

    def configure_poll_trigger(self, config: PollTriggerConfig) -> bool:
        """Configure polling trigger."""
        data = bytes([0x01 if config.enabled else 0x00])
        data += config.interval_seconds.to_bytes(4, 'big')

        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_TRIGGER_CONFIG])
        if not response.is_success:
            return False

        trigger_tlv = TLVParser.build(0xA1, data)  # Poll trigger wrapper
        response = self._apdu.update_binary(0, trigger_tlv)

        return response.is_success

    def read_configuration(self) -> List[TriggerConfiguration]:
        """Read all trigger configurations."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_TRIGGER_CONFIG])
        if not response.is_success:
            return []

        response = self._apdu.read_binary(0, 0)
        if not response.is_success:
            return []

        return self._parse_trigger_config(response.data)

    def disable_trigger(self, trigger_type: TriggerType) -> bool:
        """Disable a specific trigger."""
        # Read current config, remove specified trigger, rewrite
        configs = self.read_configuration()
        configs = [c for c in configs if c.trigger_type != trigger_type]
        return self._write_all_triggers(configs)

    def _parse_trigger_config(self, data: bytes) -> List[TriggerConfiguration]:
        """Parse trigger configuration data."""
        configs = []
        tlv = TLVParser.parse(data)

        if 0xA0 in tlv:
            # SMS trigger
            sms_tlv = TLVParser.parse(tlv[0xA0])
            sms_config = SMSTriggerConfig(
                tar=sms_tlv.get(0x80, b'\x00\x00\x00'),
                security_level=sms_tlv.get(0x81, b'\x00')[0] if 0x81 in sms_tlv else 0,
                kic=sms_tlv.get(0x82),
                kid=sms_tlv.get(0x83)
            )
            configs.append(TriggerConfiguration(
                trigger_type=TriggerType.SMS_PP,
                sms_config=sms_config
            ))

        if 0xA1 in tlv:
            # Poll trigger
            poll_data = tlv[0xA1]
            poll_config = PollTriggerConfig(
                enabled=poll_data[0] == 0x01,
                interval_seconds=int.from_bytes(poll_data[1:5], 'big')
            )
            configs.append(TriggerConfiguration(
                trigger_type=TriggerType.POLLING,
                poll_config=poll_config
            ))

        return configs

    def _write_all_triggers(self, configs: List[TriggerConfiguration]) -> bool:
        """Write all trigger configurations."""
        # Implementation to rewrite all triggers
        return True
```

### 7. BIPConfig

Configures BIP (Bearer Independent Protocol) settings.

```python
from dataclasses import dataclass
from typing import Optional
from enum import IntEnum

class BearerType(IntEnum):
    """Bearer types for BIP."""
    CSD = 0x01
    GPRS = 0x02
    DEFAULT = 0x03
    PACKET_SERVICE = 0x09
    EUTRAN = 0x0B

@dataclass
class BIPConfiguration:
    """BIP configuration parameters."""
    bearer_type: BearerType
    apn: Optional[str] = None
    buffer_size: int = 1400
    connection_timeout: int = 60

    def to_tlv(self) -> bytes:
        """Encode BIP config as TLV."""
        data = b''
        data += TLVParser.build(0x80, bytes([self.bearer_type]))

        if self.apn:
            # Encode APN as label format
            apn_encoded = self._encode_apn(self.apn)
            data += TLVParser.build(0x81, apn_encoded)

        data += TLVParser.build(0x82, self.buffer_size.to_bytes(2, 'big'))
        data += TLVParser.build(0x83, self.connection_timeout.to_bytes(2, 'big'))

        return data

    def _encode_apn(self, apn: str) -> bytes:
        """Encode APN in DNS label format."""
        result = b''
        for label in apn.split('.'):
            result += bytes([len(label)]) + label.encode('ascii')
        return result


class BIPConfig:
    """Configure BIP settings on UICC."""

    EF_BIP_CONFIG = 0x6F05

    def __init__(self, apdu_interface: APDUInterface):
        self._apdu = apdu_interface

    def configure(self, config: BIPConfiguration) -> bool:
        """Store BIP configuration on card."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_BIP_CONFIG])
        if not response.is_success:
            return False

        data = config.to_tlv()
        response = self._apdu.update_binary(0, data)

        return response.is_success

    def read_configuration(self) -> Optional[BIPConfiguration]:
        """Read current BIP configuration."""
        response = self._apdu.select_by_path([0x3F00, 0x7FFF, self.EF_BIP_CONFIG])
        if not response.is_success:
            return None

        response = self._apdu.read_binary(0, 0)
        if not response.is_success:
            return None

        return self._parse_bip_config(response.data)

    def check_terminal_support(self) -> dict:
        """Check terminal profile for BIP support."""
        # Read terminal profile
        response = self._apdu.select_by_path([0x3F00, 0x7F10, 0x6F52])  # EF_TST
        if not response.is_success:
            return {'bip_supported': False}

        response = self._apdu.read_binary(0, 0)
        if not response.is_success:
            return {'bip_supported': False}

        # Parse terminal profile for BIP capabilities
        profile = response.data
        return {
            'bip_supported': len(profile) > 17 and (profile[17] & 0x01),
            'open_channel': len(profile) > 17 and (profile[17] & 0x01),
            'close_channel': len(profile) > 17 and (profile[17] & 0x02),
            'receive_data': len(profile) > 17 and (profile[17] & 0x04),
            'send_data': len(profile) > 17 and (profile[17] & 0x08)
        }

    def _parse_bip_config(self, data: bytes) -> Optional[BIPConfiguration]:
        """Parse BIP configuration from TLV data."""
        if not data or data == b'\xFF' * len(data):
            return None

        tlv = TLVParser.parse(data)

        bearer = BearerType(tlv[0x80][0]) if 0x80 in tlv else BearerType.DEFAULT

        apn = None
        if 0x81 in tlv:
            apn = self._decode_apn(tlv[0x81])

        buffer_size = int.from_bytes(tlv.get(0x82, b'\x05\x78'), 'big')
        timeout = int.from_bytes(tlv.get(0x83, b'\x00\x3C'), 'big')

        return BIPConfiguration(
            bearer_type=bearer,
            apn=apn,
            buffer_size=buffer_size,
            connection_timeout=timeout
        )

    def _decode_apn(self, data: bytes) -> str:
        """Decode APN from DNS label format."""
        labels = []
        offset = 0
        while offset < len(data):
            length = data[offset]
            if length == 0:
                break
            offset += 1
            labels.append(data[offset:offset + length].decode('ascii'))
            offset += length
        return '.'.join(labels)
```

### 8. ProfileManager

Manages card configuration profiles.

```python
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import json
from pathlib import Path
from datetime import datetime

@dataclass
class CardProfile:
    """Complete card configuration profile."""
    name: str
    created_at: str
    card_info: Dict[str, Any]
    psk_identity: Optional[str] = None
    psk_key: Optional[str] = None  # Hex encoded, optional export
    admin_url: Optional[str] = None
    triggers: List[Dict[str, Any]] = None
    bip_config: Optional[Dict[str, Any]] = None
    security_domains: List[Dict[str, Any]] = None

    def to_json(self, include_keys: bool = False) -> str:
        """Export profile to JSON."""
        data = asdict(self)
        if not include_keys:
            data.pop('psk_key', None)
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'CardProfile':
        """Load profile from JSON."""
        data = json.loads(json_str)
        return cls(**data)


class ProfileManager:
    """Manages card configuration profiles."""

    def __init__(self,
                 pcsc_client: PCSCClient,
                 apdu_interface: APDUInterface,
                 sd_manager: SecureDomainManager,
                 psk_config: PSKConfig,
                 url_config: URLConfig,
                 trigger_config: TriggerConfig,
                 bip_config: BIPConfig):
        self._pcsc = pcsc_client
        self._apdu = apdu_interface
        self._sd = sd_manager
        self._psk = psk_config
        self._url = url_config
        self._trigger = trigger_config
        self._bip = bip_config

    def save_profile(self, name: str, include_keys: bool = False) -> CardProfile:
        """Save current card configuration as profile."""
        # Get card info
        card_info = self._get_card_info()

        # Get PSK config
        psk = self._psk.read_configuration()
        psk_identity = psk.identity.decode() if psk else None

        # Get URL config
        url = self._url.read_configuration()
        admin_url = url.url if url else None

        # Get triggers
        triggers = [asdict(t) for t in self._trigger.read_configuration()]

        # Get BIP config
        bip = self._bip.read_configuration()
        bip_dict = asdict(bip) if bip else None

        # Get Security Domains
        sds = self._sd.get_status_isd()
        sd_list = [{'aid': sd.aid.hex(), 'state': sd.life_cycle_state.name}
                   for sd in sds]

        profile = CardProfile(
            name=name,
            created_at=datetime.utcnow().isoformat(),
            card_info=card_info,
            psk_identity=psk_identity,
            admin_url=admin_url,
            triggers=triggers,
            bip_config=bip_dict,
            security_domains=sd_list
        )

        return profile

    def load_profile(self, profile: CardProfile) -> Dict[str, Any]:
        """Load profile and return diff with current card."""
        current = self.save_profile("current")

        diff = {
            'psk_identity': {
                'current': current.psk_identity,
                'profile': profile.psk_identity,
                'changed': current.psk_identity != profile.psk_identity
            },
            'admin_url': {
                'current': current.admin_url,
                'profile': profile.admin_url,
                'changed': current.admin_url != profile.admin_url
            },
            'triggers': {
                'current': current.triggers,
                'profile': profile.triggers,
                'changed': current.triggers != profile.triggers
            },
            'bip_config': {
                'current': current.bip_config,
                'profile': profile.bip_config,
                'changed': current.bip_config != profile.bip_config
            }
        }

        return diff

    def apply_profile(self, profile: CardProfile,
                      psk_key: Optional[bytes] = None) -> Dict[str, bool]:
        """Apply profile to card."""
        results = {}

        # Apply PSK
        if profile.psk_identity:
            if psk_key or profile.psk_key:
                key = psk_key or bytes.fromhex(profile.psk_key)
                psk = PSKConfiguration(
                    identity=profile.psk_identity.encode(),
                    key=key,
                    key_size=len(key)
                )
                results['psk'] = self._psk.configure(psk)
            else:
                results['psk'] = False

        # Apply URL
        if profile.admin_url:
            url = URLConfiguration.from_url(profile.admin_url)
            results['url'] = self._url.configure(url)

        # Apply triggers
        if profile.triggers:
            results['triggers'] = self._apply_triggers(profile.triggers)

        # Apply BIP config
        if profile.bip_config:
            bip = BIPConfiguration(**profile.bip_config)
            results['bip'] = self._bip.configure(bip)

        return results

    def compare_profiles(self, profile1: CardProfile,
                        profile2: CardProfile) -> Dict[str, Any]:
        """Compare two profiles and highlight differences."""
        diff = {}

        fields = ['psk_identity', 'admin_url', 'triggers', 'bip_config']
        for field in fields:
            val1 = getattr(profile1, field)
            val2 = getattr(profile2, field)
            if val1 != val2:
                diff[field] = {
                    'profile1': val1,
                    'profile2': val2
                }

        return diff

    def export_profile(self, profile: CardProfile, path: Path,
                      include_keys: bool = False) -> None:
        """Export profile to file."""
        json_str = profile.to_json(include_keys=include_keys)
        path.write_text(json_str)

    def import_profile(self, path: Path) -> CardProfile:
        """Import profile from file."""
        json_str = path.read_text()
        return CardProfile.from_json(json_str)

    def _get_card_info(self) -> Dict[str, Any]:
        """Get basic card information."""
        # Read ICCID
        response = self._apdu.select_by_path([0x3F00, 0x2FE2])
        iccid = None
        if response.is_success:
            resp = self._apdu.read_binary(0, 10)
            if resp.is_success:
                iccid = self._decode_iccid(resp.data)

        return {
            'iccid': iccid,
            'atr': self._pcsc._connection.getATR() if self._pcsc._connection else None
        }

    def _decode_iccid(self, data: bytes) -> str:
        """Decode ICCID from BCD format."""
        result = ''
        for byte in data:
            result += f'{byte & 0x0F:X}'
            if (byte >> 4) != 0x0F:
                result += f'{byte >> 4:X}'
        return result

    def _apply_triggers(self, triggers: List[Dict]) -> bool:
        """Apply trigger configurations."""
        success = True
        for trigger in triggers:
            if trigger['trigger_type'] == TriggerType.SMS_PP.value:
                config = SMSTriggerConfig(**trigger['sms_config'])
                success = success and self._trigger.configure_sms_trigger(config)
            elif trigger['trigger_type'] == TriggerType.POLLING.value:
                config = PollTriggerConfig(**trigger['poll_config'])
                success = success and self._trigger.configure_poll_trigger(config)
        return success
```

### 9. EventEmitter

Event publication for external integration.

```python
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

@dataclass
class ProvisionerEvent:
    """Event data structure."""
    event_type: str
    timestamp: str
    data: Dict[str, Any]

class EventEmitter:
    """Event emitter for provisioner events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()

    def on(self, event_type: str, handler: Callable[[ProvisionerEvent], None]) -> None:
        """Register event handler."""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable = None) -> None:
        """Remove event handler."""
        with self._lock:
            if event_type in self._handlers:
                if handler:
                    self._handlers[event_type].remove(handler)
                else:
                    del self._handlers[event_type]

    def emit(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Emit event to all registered handlers."""
        event = ProvisionerEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data or {}
        )

        # Queue event for async processing
        self._event_queue.put(event)

        # Also call handlers directly
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            handlers += self._handlers.get('*', [])  # Wildcard handlers

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Log error but don't propagate
                pass

    def get_pending_events(self) -> List[ProvisionerEvent]:
        """Get all pending events from queue."""
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events
```

### 10. APDULogger

Comprehensive APDU logging.

```python
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path

@dataclass
class APDULogEntry:
    """Single APDU exchange log entry."""
    timestamp: str
    direction: str  # 'command' or 'response'
    data: str  # Hex string
    decoded: Optional[str] = None
    sw: Optional[str] = None
    sw_message: Optional[str] = None

class APDULogger:
    """Logs all APDU exchanges."""

    def __init__(self, max_entries: int = 10000):
        self._entries: List[APDULogEntry] = []
        self._max_entries = max_entries
        self._enabled = True

    def log_command(self, apdu: bytes) -> None:
        """Log outgoing APDU command."""
        if not self._enabled:
            return

        entry = APDULogEntry(
            timestamp=datetime.utcnow().isoformat(),
            direction='command',
            data=apdu.hex().upper(),
            decoded=self._decode_command(apdu)
        )
        self._add_entry(entry)

    def log_response(self, response: APDUResponse) -> None:
        """Log incoming APDU response."""
        if not self._enabled:
            return

        entry = APDULogEntry(
            timestamp=datetime.utcnow().isoformat(),
            direction='response',
            data=response.data.hex().upper() if response.data else '',
            sw=f'{response.sw1:02X}{response.sw2:02X}',
            sw_message=response.status_message
        )
        self._add_entry(entry)

    def get_entries(self, count: Optional[int] = None) -> List[APDULogEntry]:
        """Get log entries."""
        if count:
            return self._entries[-count:]
        return self._entries.copy()

    def clear(self) -> None:
        """Clear all log entries."""
        self._entries.clear()

    def export(self, path: Path, format: str = 'json') -> None:
        """Export logs to file."""
        if format == 'json':
            data = [asdict(e) for e in self._entries]
            path.write_text(json.dumps(data, indent=2))
        elif format == 'csv':
            import csv
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'direction', 'data', 'decoded', 'sw', 'sw_message'])
                for e in self._entries:
                    writer.writerow([e.timestamp, e.direction, e.data,
                                   e.decoded, e.sw, e.sw_message])

    def enable(self) -> None:
        """Enable logging."""
        self._enabled = True

    def disable(self) -> None:
        """Disable logging."""
        self._enabled = False

    def _add_entry(self, entry: APDULogEntry) -> None:
        """Add entry with overflow handling."""
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def _decode_command(self, apdu: bytes) -> str:
        """Decode APDU command to human-readable form."""
        if len(apdu) < 4:
            return "Invalid APDU"

        cla, ins, p1, p2 = apdu[0], apdu[1], apdu[2], apdu[3]

        ins_names = {
            0xA4: 'SELECT',
            0xB0: 'READ BINARY',
            0xD6: 'UPDATE BINARY',
            0xB2: 'READ RECORD',
            0xDC: 'UPDATE RECORD',
            0x20: 'VERIFY',
            0xF2: 'GET STATUS',
            0xE6: 'INSTALL',
            0xE4: 'DELETE',
            0xD8: 'PUT KEY',
            0x50: 'INITIALIZE UPDATE',
            0x82: 'EXTERNAL AUTHENTICATE'
        }

        ins_name = ins_names.get(ins, f'INS={ins:02X}')
        return f'{ins_name} P1={p1:02X} P2={p2:02X}'
```

## CLI Design

### Command Structure

```
cardlink-provision
├── list                    # List readers and cards
├── info <reader>           # Show card information
│   ├── --atr              # ATR only
│   ├── --iccid            # ICCID only
│   ├── --sd               # Security Domains
│   └── --all              # All information (default)
├── psk <reader>           # PSK configuration
│   ├── --identity <id>    # Set PSK identity
│   ├── --key <hex>        # Set PSK key (hex)
│   ├── --generate <size>  # Generate random key
│   └── --export           # Export current PSK
├── url <reader> <url>     # Set admin URL
│   └── --read             # Read current URL
├── trigger <reader>       # Trigger configuration
│   ├── --sms              # Configure SMS-PP trigger
│   ├── --poll <interval>  # Configure polling trigger
│   ├── --tar <hex>        # Set TAR
│   ├── --disable <type>   # Disable trigger
│   └── --list             # List configured triggers
├── bip <reader>           # BIP configuration
│   ├── --bearer <type>    # Set bearer type
│   ├── --apn <apn>        # Set APN
│   └── --read             # Read current config
├── apdu <reader> <hex>    # Send raw APDU
│   └── --script <file>    # Run APDU script
├── auth <reader>          # Authentication
│   ├── --pin <pin>        # PIN authentication
│   ├── --adm <key>        # ADM key authentication
│   ├── --scp02            # SCP02 secure channel
│   └── --scp03            # SCP03 secure channel
└── profile                # Profile management
    ├── save <name>        # Save current config
    ├── load <file>        # Load and show diff
    ├── apply <file>       # Apply profile to card
    ├── compare <f1> <f2>  # Compare two profiles
    └── export <name>      # Export to file
        └── --with-keys    # Include PSK keys
```

### CLI Implementation

```python
import click
from typing import Optional

@click.group()
@click.version_option()
def cli():
    """CardLink UICC Provisioner - Configure UICC cards for SCP81 testing."""
    pass

@cli.command()
def list():
    """List all connected PC/SC readers and cards."""
    client = PCSCClient()
    readers = client.list_readers()

    if not readers:
        click.echo("No PC/SC readers found.")
        click.echo("\nTroubleshooting:")
        click.echo("  - Ensure pcscd service is running (Linux)")
        click.echo("  - Check USB connection to card reader")
        click.echo("  - Verify reader drivers are installed")
        return

    click.echo(f"Found {len(readers)} reader(s):\n")
    for reader in readers:
        status = "Card present" if reader.has_card else "No card"
        click.echo(f"  [{reader.index}] {reader.name}")
        click.echo(f"      Status: {status}")
        if reader.atr:
            click.echo(f"      ATR: {reader.atr.hex().upper()}")
        click.echo()

@cli.command()
@click.argument('reader')
@click.option('--atr', is_flag=True, help='Show ATR only')
@click.option('--iccid', is_flag=True, help='Show ICCID only')
@click.option('--sd', is_flag=True, help='Show Security Domains')
@click.option('--all', 'show_all', is_flag=True, default=True, help='Show all info')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def info(reader: str, atr: bool, iccid: bool, sd: bool, show_all: bool, as_json: bool):
    """Show card information."""
    client = PCSCClient()

    try:
        card_info = client.connect(reader)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return

    apdu = APDUInterface(client)
    sd_mgr = SecureDomainManager(apdu)

    info_data = {}

    if atr or show_all:
        info_data['atr'] = {
            'raw': card_info.atr.hex().upper(),
            'analysis': ATRParser.parse(card_info.atr)
        }

    if iccid or show_all:
        # Read ICCID
        response = apdu.select_by_path([0x3F00, 0x2FE2])
        if response.is_success:
            resp = apdu.read_binary(0, 10)
            if resp.is_success:
                info_data['iccid'] = decode_iccid(resp.data)

    if sd or show_all:
        sd_mgr.select_isd()
        sds = sd_mgr.get_status_isd()
        info_data['security_domains'] = [
            {'aid': s.aid.hex().upper(), 'state': s.life_cycle_state.name}
            for s in sds
        ]

    if as_json:
        click.echo(json.dumps(info_data, indent=2))
    else:
        for key, value in info_data.items():
            click.echo(f"\n{key.upper()}:")
            if isinstance(value, dict):
                for k, v in value.items():
                    click.echo(f"  {k}: {v}")
            elif isinstance(value, list):
                for item in value:
                    click.echo(f"  - {item}")
            else:
                click.echo(f"  {value}")

    client.disconnect()

@cli.command()
@click.argument('reader')
@click.option('--identity', help='PSK identity string')
@click.option('--key', help='PSK key (hex)')
@click.option('--generate', type=int, help='Generate random key of size')
@click.option('--export', 'do_export', is_flag=True, help='Export current PSK')
def psk(reader: str, identity: Optional[str], key: Optional[str],
        generate: Optional[int], do_export: bool):
    """Configure PSK on card."""
    client = PCSCClient()
    client.connect(reader)
    apdu = APDUInterface(client)
    sd_mgr = SecureDomainManager(apdu)
    psk_cfg = PSKConfig(apdu, sd_mgr)

    if do_export:
        current = psk_cfg.read_configuration()
        if current:
            click.echo(f"PSK Identity: {current.identity.decode()}")
            click.echo("PSK Key: [write-only, not readable]")
        else:
            click.echo("No PSK configured")
        return

    if identity:
        if generate:
            psk_config = PSKConfiguration.generate(identity, generate)
            click.echo(f"Generated {generate}-byte key: {psk_config.key.hex().upper()}")
        elif key:
            psk_config = PSKConfiguration.from_hex(identity, key)
        else:
            click.echo("Error: --key or --generate required", err=True)
            return

        if psk_cfg.configure(psk_config):
            click.echo("PSK configured successfully")
        else:
            click.echo("Failed to configure PSK", err=True)

    client.disconnect()

@cli.command()
@click.argument('reader')
@click.argument('url', required=False)
@click.option('--read', 'do_read', is_flag=True, help='Read current URL')
def url(reader: str, url: Optional[str], do_read: bool):
    """Configure admin server URL."""
    client = PCSCClient()
    client.connect(reader)
    apdu = APDUInterface(client)
    url_cfg = URLConfig(apdu)

    if do_read:
        current = url_cfg.read_configuration()
        if current:
            click.echo(f"Admin URL: {current.url}")
        else:
            click.echo("No URL configured")
        return

    if url:
        if not url_cfg.validate(url):
            click.echo(f"Error: Invalid URL format", err=True)
            return

        config = URLConfiguration.from_url(url)
        if url_cfg.configure(config):
            click.echo(f"URL configured: {url}")
        else:
            click.echo("Failed to configure URL", err=True)

    client.disconnect()

@cli.command()
@click.argument('reader')
@click.argument('apdu_hex')
@click.option('--script', type=click.Path(exists=True), help='Run APDU script')
def apdu(reader: str, apdu_hex: str, script: Optional[str]):
    """Send raw APDU command."""
    client = PCSCClient()
    client.connect(reader)
    apdu_if = APDUInterface(client)

    if script:
        # Run script file
        with open(script) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    response = apdu_if.send_raw(line)
                    click.echo(f">> {line}")
                    click.echo(f"<< {response.data.hex().upper()} {response.sw:04X}")
    else:
        response = apdu_if.send_raw(apdu_hex)
        click.echo(f"Response: {response.data.hex().upper()}")
        click.echo(f"Status: {response.sw:04X} ({response.status_message})")

    client.disconnect()

@cli.group()
def profile():
    """Profile management commands."""
    pass

@profile.command()
@click.argument('reader')
@click.argument('name')
@click.option('--with-keys', is_flag=True, help='Include PSK keys')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def save(reader: str, name: str, with_keys: bool, output: Optional[str]):
    """Save current card configuration as profile."""
    # Implementation
    pass

@profile.command()
@click.argument('file', type=click.Path(exists=True))
def load(file: str):
    """Load profile and show diff with current card."""
    # Implementation
    pass

@profile.command()
@click.argument('reader')
@click.argument('file', type=click.Path(exists=True))
@click.option('--key', help='PSK key if not in profile')
def apply(reader: str, file: str, key: Optional[str]):
    """Apply profile to card."""
    # Implementation
    pass

if __name__ == '__main__':
    cli()
```

## Error Handling

### Error Types

```python
class ProvisionerError(Exception):
    """Base exception for provisioner errors."""
    pass

class ReaderNotFoundError(ProvisionerError):
    """PC/SC reader not found."""
    pass

class CardNotFoundError(ProvisionerError):
    """No card in reader."""
    pass

class NotConnectedError(ProvisionerError):
    """Not connected to card."""
    pass

class APDUError(ProvisionerError):
    """APDU command failed."""
    def __init__(self, sw1: int, sw2: int, message: str = None):
        self.sw1 = sw1
        self.sw2 = sw2
        super().__init__(message or SWDecoder.decode(sw1, sw2))

class AuthenticationError(ProvisionerError):
    """Authentication failed."""
    pass

class SecurityError(ProvisionerError):
    """Security operation failed."""
    pass

class ProfileError(ProvisionerError):
    """Profile operation failed."""
    pass
```

### Error Handling Strategy

```python
def handle_provisioner_operation(func):
    """Decorator for error handling in provisioner operations."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ReaderNotFoundError as e:
            click.echo(f"Reader error: {e}", err=True)
            click.echo("\nTroubleshooting:")
            click.echo("  - Check reader connection")
            click.echo("  - Run 'cardlink-provision list' to see available readers")
            return None
        except CardNotFoundError as e:
            click.echo(f"Card error: {e}", err=True)
            click.echo("  - Ensure card is properly inserted")
            return None
        except APDUError as e:
            click.echo(f"Card returned error: {e.sw1:02X}{e.sw2:02X} - {e}", err=True)
            return None
        except AuthenticationError as e:
            click.echo(f"Authentication failed: {e}", err=True)
            return None
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            return None
    return wrapper
```

## Testing Strategy

### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch

class TestPCSCClient:
    def test_list_readers_empty(self):
        with patch('smartcard.System.readers', return_value=[]):
            client = PCSCClient()
            assert client.list_readers() == []

    def test_atr_parser(self):
        atr = bytes.fromhex('3B9F96801FC78031A073BE21136743200718000000')
        result = ATRParser.parse(atr)
        assert result['convention'] == 'Direct'
        assert 'UICC' in result['card_type'] or 'USIM' in result['card_type']

class TestAPDUInterface:
    def test_select_by_aid(self):
        mock_client = Mock()
        mock_client.transmit.return_value = (b'\x6F\x10', 0x90, 0x00)

        apdu = APDUInterface(mock_client)
        response = apdu.select_by_aid(bytes.fromhex('A000000151000000'))

        assert response.is_success
        mock_client.transmit.assert_called_once()

class TestTLVParser:
    def test_parse_simple(self):
        data = bytes.fromhex('4F07A0000001510000')
        result = TLVParser.parse(data)
        assert 0x4F in result
        assert result[0x4F] == bytes.fromhex('A0000001510000')

    def test_build_simple(self):
        result = TLVParser.build(0x4F, bytes.fromhex('A0000001510000'))
        assert result == bytes.fromhex('4F07A0000001510000')
```

### Integration Tests

```python
@pytest.mark.integration
class TestProvisionerIntegration:
    @pytest.fixture
    def provisioner(self):
        """Setup provisioner with real reader."""
        client = PCSCClient()
        readers = client.list_readers()
        if not readers or not any(r.has_card for r in readers):
            pytest.skip("No card reader with card available")

        reader = next(r for r in readers if r.has_card)
        client.connect(reader.name)

        yield client

        client.disconnect()

    def test_read_iccid(self, provisioner):
        apdu = APDUInterface(provisioner)
        response = apdu.select_by_path([0x3F00, 0x2FE2])
        assert response.is_success

        response = apdu.read_binary(0, 10)
        assert response.is_success
        assert len(response.data) == 10
```

## Dependencies

### Required Packages

```
pyscard>=2.0.0          # PC/SC interface
cryptography>=3.4.0     # Cryptographic operations
click>=8.0.0            # CLI framework
```

### System Requirements

- **Linux**: pcscd service, libpcsclite-dev
- **macOS**: Native PC/SC support (no additional dependencies)
- **Windows**: WinSCard (built-in)
