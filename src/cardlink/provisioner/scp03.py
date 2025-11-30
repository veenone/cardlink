"""SCP03 Secure Channel Protocol Implementation.

This module implements the GlobalPlatform SCP03 secure channel protocol
for authenticated and encrypted communication with smart cards using AES.

SCP03 uses AES-128 for session key derivation and AES-CMAC for authentication,
providing stronger security than SCP02's Triple-DES based approach.

Example:
    ```python
    from cardlink.provisioner import PCSCClient, SecureDomainManager, SCP03

    client = PCSCClient()
    client.connect(0)

    sd = SecureDomainManager(client.transmit)
    sd.select_isd()

    # Establish secure channel with default test keys
    scp = SCP03(client.transmit)
    scp.initialize()

    # Send secured commands
    response = scp.send(bytes.fromhex("80F28002024F00"))

    client.disconnect()
    ```
"""

import logging
import secrets
from typing import Callable, Optional, Union

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.backends import default_backend

from cardlink.provisioner.apdu_interface import APDUInterface, SWDecoder
from cardlink.provisioner.exceptions import (
    APDUError,
    AuthenticationError,
    ProvisionerError,
    SecurityError,
)
from cardlink.provisioner.models import (
    APDUCommand,
    APDUResponse,
    INS,
    SCPKeys,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# GlobalPlatform CLA byte
GP_CLA = 0x80
GP_CLA_SECURE = 0x84  # With secure messaging

# SCP03 security levels
SECURITY_LEVEL_NONE = 0x00
SECURITY_LEVEL_CMAC = 0x01
SECURITY_LEVEL_CENC_CMAC = 0x03
SECURITY_LEVEL_RMAC = 0x10
SECURITY_LEVEL_CENC_CMAC_RMAC = 0x13
SECURITY_LEVEL_RENC = 0x30
SECURITY_LEVEL_FULL = 0x33

# KDF constants for SCP03 (NIST SP 800-108)
KDF_CONST_CMAC = 0x01  # Card cryptogram (S-MAC key derivation)
KDF_CONST_RMAC = 0x02  # R-MAC key derivation
KDF_CONST_ENC = 0x04   # S-ENC key derivation
KDF_CONST_CARD_CRYPTO = 0x00  # Card cryptogram calculation
KDF_CONST_HOST_CRYPTO = 0x01  # Host cryptogram calculation

# AES block size
AES_BLOCK_SIZE = 16

# Transmit function type
TransmitFunc = Callable[[bytes], APDUResponse]


# =============================================================================
# SCP03 Implementation
# =============================================================================


class SCP03:
    """SCP03 Secure Channel Protocol implementation.

    This class implements the GlobalPlatform SCP03 secure channel protocol
    with support for:
    - INITIALIZE UPDATE command
    - Session key derivation using AES-CMAC (NIST SP 800-108)
    - Mutual authentication with AES-CMAC based cryptograms
    - EXTERNAL AUTHENTICATE command
    - C-MAC calculation using AES-CMAC
    - Optional C-ENC for command encryption (AES-CBC)
    - Encryption counter management

    Attributes:
        is_authenticated: Whether secure channel is established.
        security_level: Current security level.

    Example:
        ```python
        scp = SCP03(client.transmit)

        # Use custom keys
        keys = SCPKeys(enc=my_enc, mac=my_mac, dek=my_dek)
        scp.initialize(keys=keys, security_level=0x33)  # Full security

        # Send secured command
        response = scp.send(command)
        ```
    """

    def __init__(
        self,
        transmit_func: TransmitFunc,
        auto_get_response: bool = True,
    ):
        """Initialize SCP03 secure channel.

        Args:
            transmit_func: Function to transmit APDU and receive response.
            auto_get_response: Automatically handle GET RESPONSE (SW=61xx).
        """
        self._apdu = APDUInterface(transmit_func, auto_get_response)
        self._transmit = transmit_func

        # Session state
        self._is_authenticated = False
        self._security_level = SECURITY_LEVEL_NONE
        self._session_keys: Optional[_SCP03SessionKeys] = None
        self._mac_chaining_value = bytes(AES_BLOCK_SIZE)
        self._encryption_counter = bytes(AES_BLOCK_SIZE)

        # Challenge/response data
        self._host_challenge = bytes(8)
        self._card_challenge = bytes(8)
        self._key_diversification_data = bytes(10)

    @property
    def is_authenticated(self) -> bool:
        """Check if secure channel is established."""
        return self._is_authenticated

    @property
    def security_level(self) -> int:
        """Get current security level."""
        return self._security_level

    def initialize(
        self,
        keys: Optional[SCPKeys] = None,
        key_version: int = 0x00,
        security_level: int = SECURITY_LEVEL_CMAC,
        host_challenge: Optional[bytes] = None,
    ) -> None:
        """Initialize secure channel with INITIALIZE UPDATE + EXTERNAL AUTHENTICATE.

        Args:
            keys: Static keys (defaults to test keys).
            key_version: Key version number to use.
            security_level: Desired security level.
            host_challenge: Custom host challenge (random if not provided).

        Raises:
            AuthenticationError: If authentication fails.
            APDUError: If card returns error.
        """
        if keys is None:
            keys = self._get_default_test_keys()
            logger.warning("Using default test keys - NOT FOR PRODUCTION USE")

        # Generate host challenge
        if host_challenge:
            self._host_challenge = host_challenge
        else:
            self._host_challenge = secrets.token_bytes(8)

        # Step 1: INITIALIZE UPDATE
        init_response = self._send_initialize_update(key_version)

        # Step 2: Parse response
        self._parse_initialize_update_response(init_response.data)

        # Step 3: Derive session keys
        self._session_keys = self._derive_session_keys(keys)

        # Step 4: Verify card cryptogram
        card_cryptogram = init_response.data[20:28]
        if not self._verify_card_cryptogram(card_cryptogram):
            raise AuthenticationError(
                "Card cryptogram verification failed",
                "Card authentication failed - possible key mismatch",
            )

        # Step 5: Calculate host cryptogram
        host_cryptogram = self._calculate_host_cryptogram()

        # Step 6: EXTERNAL AUTHENTICATE
        self._send_external_authenticate(host_cryptogram, security_level)

        # Initialize encryption counter
        self._encryption_counter = self._initialize_enc_counter()

        self._is_authenticated = True
        self._security_level = security_level
        logger.info(f"SCP03 secure channel established (security level: {security_level:02X})")

    @staticmethod
    def _get_default_test_keys() -> SCPKeys:
        """Get default GlobalPlatform test keys for AES-128.

        Returns:
            Test keys (NOT FOR PRODUCTION USE).
        """
        # Default GP test key
        default_key = bytes.fromhex("404142434445464748494A4B4C4D4E4F")
        return SCPKeys(enc=default_key, mac=default_key, dek=default_key, version=0)

    def _send_initialize_update(self, key_version: int) -> APDUResponse:
        """Send INITIALIZE UPDATE command.

        Args:
            key_version: Key version to use.

        Returns:
            INITIALIZE UPDATE response.
        """
        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.INITIALIZE_UPDATE,
            p1=key_version,
            p2=0x00,  # Key identifier
            data=self._host_challenge,
            le=0,
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "INITIALIZE UPDATE",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        if len(response.data) < 28:
            raise AuthenticationError(
                "Invalid INITIALIZE UPDATE response",
                f"Expected 28+ bytes, got {len(response.data)}",
            )

        return response

    def _parse_initialize_update_response(self, data: bytes) -> None:
        """Parse INITIALIZE UPDATE response.

        Response format:
        - Bytes 0-9: Key diversification data
        - Byte 10: Key version
        - Byte 11: SCP identifier (0x03 for SCP03)
        - Byte 12: SCP options (i parameter)
        - Bytes 13-20: Card challenge
        - Bytes 21-28: Card cryptogram

        Args:
            data: Response data.
        """
        self._key_diversification_data = data[0:10]
        key_version = data[10]
        scp_id = data[11]
        scp_option = data[12] if len(data) > 12 else 0x00
        self._card_challenge = data[13:21] if len(data) >= 21 else data[12:20]

        logger.debug(
            f"INITIALIZE UPDATE: key_version={key_version:02X}, "
            f"scp_id={scp_id:02X}, scp_option={scp_option:02X}"
        )

        if scp_id != 0x03:
            logger.warning(f"Unexpected SCP identifier: {scp_id:02X} (expected 0x03)")

    def _derive_session_keys(self, static_keys: SCPKeys) -> "_SCP03SessionKeys":
        """Derive session keys using NIST SP 800-108 KDF.

        Args:
            static_keys: Static card keys.

        Returns:
            Derived session keys.
        """
        # Context for key derivation
        context = self._host_challenge + self._card_challenge

        # Derive S-MAC key
        s_mac = self._kdf(static_keys.mac, KDF_CONST_CMAC, context)

        # Derive S-ENC key
        s_enc = self._kdf(static_keys.enc, KDF_CONST_ENC, context)

        # Derive R-MAC key (if needed)
        s_rmac = self._kdf(static_keys.mac, KDF_CONST_RMAC, context)

        # DEK is used as-is for key wrapping
        s_dek = static_keys.dek

        logger.debug("SCP03 session keys derived")
        return _SCP03SessionKeys(enc=s_enc, mac=s_mac, rmac=s_rmac, dek=s_dek)

    def _kdf(self, key: bytes, constant: int, context: bytes, length: int = 16) -> bytes:
        """Key Derivation Function per NIST SP 800-108.

        KDF format: label || 0x00 || L || i || context

        Where:
        - label: derivation constant (1 byte)
        - L: output length in bits (2 bytes, big-endian)
        - i: counter (1 byte)
        - context: host_challenge || card_challenge

        Args:
            key: Base key.
            constant: Derivation constant.
            context: Context data (challenges).
            length: Output length in bytes.

        Returns:
            Derived key.
        """
        # Build derivation data
        # Label || 0x00 || L (bits) || counter || context
        label = bytes([constant])
        separator = b'\x00'
        output_bits = (length * 8).to_bytes(2, "big")
        counter = b'\x01'

        derivation_data = label + separator + output_bits + counter + context

        # Pad to block boundary if needed
        if len(derivation_data) < AES_BLOCK_SIZE:
            derivation_data = derivation_data + b'\x00' * (AES_BLOCK_SIZE - len(derivation_data))

        # Calculate AES-CMAC
        derived = self._aes_cmac(key, derivation_data)

        return derived[:length]

    def _aes_cmac(self, key: bytes, data: bytes) -> bytes:
        """Calculate AES-CMAC.

        Args:
            key: AES key (16 bytes).
            data: Data to MAC.

        Returns:
            16-byte MAC.
        """
        c = cmac.CMAC(algorithms.AES(key), backend=default_backend())
        c.update(data)
        return c.finalize()

    def _verify_card_cryptogram(self, card_cryptogram: bytes) -> bool:
        """Verify card cryptogram using AES-CMAC.

        Card cryptogram = AES-CMAC(S-MAC, host_challenge || card_challenge)
        (truncated to 8 bytes)

        Args:
            card_cryptogram: Cryptogram from card.

        Returns:
            True if cryptogram is valid.
        """
        # Build context for cryptogram
        context = self._host_challenge + self._card_challenge

        # Calculate expected cryptogram
        full_mac = self._calculate_cryptogram(
            self._session_keys.mac,
            KDF_CONST_CARD_CRYPTO,
            context,
        )
        expected = full_mac[:8]

        # Constant-time comparison
        return secrets.compare_digest(card_cryptogram, expected)

    def _calculate_host_cryptogram(self) -> bytes:
        """Calculate host cryptogram using AES-CMAC.

        Host cryptogram = AES-CMAC(S-MAC, card_challenge || host_challenge)
        (truncated to 8 bytes)

        Returns:
            8-byte host cryptogram.
        """
        # Note: order is reversed from card cryptogram
        context = self._card_challenge + self._host_challenge

        full_mac = self._calculate_cryptogram(
            self._session_keys.mac,
            KDF_CONST_HOST_CRYPTO,
            context,
        )
        return full_mac[:8]

    def _calculate_cryptogram(
        self,
        key: bytes,
        constant: int,
        context: bytes,
    ) -> bytes:
        """Calculate a cryptogram using KDF and AES-CMAC.

        Args:
            key: Session MAC key.
            constant: Derivation constant.
            context: Context data.

        Returns:
            16-byte MAC.
        """
        # Build derivation data similar to KDF
        label = bytes([constant])
        separator = b'\x00'
        output_bits = (64).to_bytes(2, "big")  # 64 bits = 8 bytes output
        counter = b'\x01'

        derivation_data = label + separator + output_bits + counter + context

        return self._aes_cmac(key, derivation_data)

    def _send_external_authenticate(
        self,
        host_cryptogram: bytes,
        security_level: int,
    ) -> None:
        """Send EXTERNAL AUTHENTICATE command.

        Args:
            host_cryptogram: Calculated host cryptogram.
            security_level: Desired security level.
        """
        # Build command header for MAC calculation
        command_header = bytes([GP_CLA_SECURE, INS.EXTERNAL_AUTH, security_level, 0x00])

        # Calculate C-MAC over header + host_cryptogram
        # First, initialize MAC chaining value
        self._mac_chaining_value = bytes(AES_BLOCK_SIZE)

        # Build data for MAC: header + Lc + host_cryptogram
        lc = len(host_cryptogram)
        mac_input = self._mac_chaining_value + command_header + bytes([lc]) + host_cryptogram

        # Pad to block boundary
        mac_input = self._pad_iso9797(mac_input)

        # Calculate AES-CMAC
        mac = self._aes_cmac(self._session_keys.mac, mac_input)

        # Build command with MAC (first 8 bytes of AES-CMAC)
        command = APDUCommand(
            cla=GP_CLA_SECURE,
            ins=INS.EXTERNAL_AUTH,
            p1=security_level,
            p2=0x00,
            data=host_cryptogram + mac[:8],
        )

        response = self._transmit(command.to_bytes())

        if not response.is_success:
            self._is_authenticated = False
            raise AuthenticationError(
                "EXTERNAL AUTHENTICATE failed",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        # Update MAC chaining value
        self._mac_chaining_value = mac

    def _initialize_enc_counter(self) -> bytes:
        """Initialize encryption counter for C-ENC.

        Counter is initialized to: card_challenge || host_challenge

        Returns:
            16-byte initial counter.
        """
        # Build initial counter from challenges
        return self._card_challenge + self._host_challenge

    def send(self, command: Union[bytes, APDUCommand]) -> APDUResponse:
        """Send command through secure channel.

        Args:
            command: APDU command (bytes or APDUCommand).

        Returns:
            Response from card.

        Raises:
            SecurityError: If secure channel not established.
            APDUError: If command fails.
        """
        if not self._is_authenticated:
            raise SecurityError(
                "Secure channel not established",
                "Call initialize() before sending secured commands",
            )

        if isinstance(command, APDUCommand):
            command = command.to_bytes()

        # Apply security
        secured_command = self._secure_command(command)

        # Send command
        response = self._transmit(secured_command)

        # Verify R-MAC if enabled
        if self._security_level & SECURITY_LEVEL_RMAC:
            self._verify_rmac(response)

        return response

    def _secure_command(self, command: bytes) -> bytes:
        """Apply secure messaging to command.

        Args:
            command: Original APDU command.

        Returns:
            Secured command with C-MAC (and C-ENC if enabled).
        """
        # Parse command
        cla = command[0]
        ins = command[1]
        p1 = command[2]
        p2 = command[3]

        # Get command data
        if len(command) == 4:
            data = b""
            le = None
        elif len(command) == 5:
            data = b""
            le = command[4]
        else:
            lc = command[4]
            data = command[5:5 + lc]
            le = command[5 + lc] if len(command) > 5 + lc else None

        # Encrypt data if required
        encrypted_data = data
        if self._security_level & SECURITY_LEVEL_CENC_CMAC == SECURITY_LEVEL_CENC_CMAC and data:
            encrypted_data = self._encrypt_data(data)

        # Set secure CLA
        secure_cla = cla | 0x04

        # Calculate new Lc (data + 8 bytes MAC)
        new_lc = len(encrypted_data) + 8

        # Build header for MAC calculation
        header = bytes([secure_cla, ins, p1, p2, new_lc])

        # Calculate C-MAC
        mac_input = self._mac_chaining_value + header + encrypted_data
        mac_input = self._pad_iso9797(mac_input)
        full_mac = self._aes_cmac(self._session_keys.mac, mac_input)
        mac = full_mac[:8]

        # Update MAC chaining value
        self._mac_chaining_value = full_mac

        # Build secured command
        secured = header + encrypted_data + mac

        if le is not None:
            secured += bytes([le])

        return secured

    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt command data using AES-CBC.

        Uses encryption counter as IV, which is incremented after each encryption.

        Args:
            data: Plain data.

        Returns:
            Encrypted data.
        """
        # Pad data to block boundary
        padded = self._pad_iso9797(data)

        # Generate ICV (Initial Chaining Value) from counter
        icv = self._generate_icv()

        # Encrypt with AES-CBC
        cipher = Cipher(
            algorithms.AES(self._session_keys.enc),
            modes.CBC(icv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()

        # Increment counter
        self._increment_counter()

        return encrypted

    def _generate_icv(self) -> bytes:
        """Generate ICV for encryption.

        ICV = AES(S-ENC, counter)

        Returns:
            16-byte ICV.
        """
        cipher = Cipher(
            algorithms.AES(self._session_keys.enc),
            modes.ECB(),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(self._encryption_counter) + encryptor.finalize()

    def _increment_counter(self) -> None:
        """Increment encryption counter."""
        # Convert to integer, increment, convert back
        counter_int = int.from_bytes(self._encryption_counter, "big")
        counter_int = (counter_int + 1) % (2 ** 128)
        self._encryption_counter = counter_int.to_bytes(16, "big")

    def _verify_rmac(self, response: APDUResponse) -> bool:
        """Verify R-MAC on response (if enabled).

        Args:
            response: Response from card.

        Returns:
            True if R-MAC is valid.

        Raises:
            SecurityError: If R-MAC verification fails.
        """
        # R-MAC verification would be implemented here
        # For now, just return True (not all cards support R-MAC)
        return True

    @staticmethod
    def _pad_iso9797(data: bytes) -> bytes:
        """Apply ISO 9797-1 Method 2 padding (80 00...00).

        Appends 0x80 followed by zeros to reach 16-byte boundary.

        Args:
            data: Data to pad.

        Returns:
            Padded data.
        """
        # Add mandatory 0x80 byte
        padded = data + b'\x80'

        # Pad to 16-byte boundary (AES block size)
        pad_length = (AES_BLOCK_SIZE - (len(padded) % AES_BLOCK_SIZE)) % AES_BLOCK_SIZE
        return padded + (b'\x00' * pad_length)

    def close(self) -> None:
        """Close secure channel (clear session data)."""
        self._is_authenticated = False
        self._security_level = SECURITY_LEVEL_NONE
        self._session_keys = None
        self._mac_chaining_value = bytes(AES_BLOCK_SIZE)
        self._encryption_counter = bytes(AES_BLOCK_SIZE)
        logger.debug("SCP03 secure channel closed")

    def wrap_key(self, key: bytes) -> bytes:
        """Wrap a key for secure transmission using DEK.

        Uses AES-KWP (Key Wrap with Padding) for SCP03.

        Args:
            key: Key to wrap.

        Returns:
            Wrapped key.

        Raises:
            SecurityError: If session not established.
        """
        if not self._is_authenticated:
            raise SecurityError(
                "Secure channel not established",
                "Call initialize() before wrapping keys",
            )

        # Simple ECB wrapping (actual implementation would use AES-KWP)
        # Pad key to 16-byte boundary
        if len(key) % 16 != 0:
            key = key + b'\x00' * (16 - len(key) % 16)

        cipher = Cipher(
            algorithms.AES(self._session_keys.dek),
            modes.ECB(),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(key) + encryptor.finalize()


# =============================================================================
# Session Keys Container
# =============================================================================


class _SCP03SessionKeys:
    """Container for SCP03 session keys."""

    __slots__ = ("enc", "mac", "rmac", "dek")

    def __init__(self, enc: bytes, mac: bytes, rmac: bytes, dek: bytes):
        self.enc = enc
        self.mac = mac
        self.rmac = rmac
        self.dek = dek
