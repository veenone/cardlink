"""SCP02 Secure Channel Protocol Implementation.

This module implements the GlobalPlatform SCP02 secure channel protocol
for authenticated and encrypted communication with smart cards.

SCP02 uses Triple-DES for session key derivation and MAC calculation,
providing mutual authentication between host and card.

Example:
    ```python
    from gp_ota_tester.provisioner import PCSCClient, SecureDomainManager, SCP02

    client = PCSCClient()
    client.connect(0)

    sd = SecureDomainManager(client.transmit)
    sd.select_isd()

    # Establish secure channel with default test keys
    scp = SCP02(client.transmit)
    scp.initialize()  # Performs INITIALIZE UPDATE + EXTERNAL AUTHENTICATE

    # Send secured commands
    response = scp.send(bytes.fromhex("80F28002024F00"))

    client.disconnect()
    ```
"""

import logging
import os
import secrets
from typing import Callable, Optional, Tuple, Union

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from gp_ota_tester.provisioner.apdu_interface import APDUInterface, SWDecoder
from gp_ota_tester.provisioner.exceptions import (
    APDUError,
    AuthenticationError,
    ProvisionerError,
    SecurityError,
)
from gp_ota_tester.provisioner.models import (
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

# SCP02 security levels
SECURITY_LEVEL_NONE = 0x00
SECURITY_LEVEL_CMAC = 0x01
SECURITY_LEVEL_CENC_CMAC = 0x03
SECURITY_LEVEL_RMAC = 0x10
SECURITY_LEVEL_RENC = 0x20

# Key derivation constants
DERIVATION_CONST_CMAC = bytes([0x01, 0x01])
DERIVATION_CONST_RMAC = bytes([0x01, 0x02])
DERIVATION_CONST_ENC = bytes([0x01, 0x82])
DERIVATION_CONST_DEK = bytes([0x01, 0x81])

# Transmit function type
TransmitFunc = Callable[[bytes], APDUResponse]


# =============================================================================
# SCP02 Implementation
# =============================================================================


class SCP02:
    """SCP02 Secure Channel Protocol implementation.

    This class implements the GlobalPlatform SCP02 secure channel protocol
    with support for:
    - INITIALIZE UPDATE command
    - Session key derivation using Triple-DES
    - Mutual authentication (card and host cryptograms)
    - EXTERNAL AUTHENTICATE command
    - C-MAC calculation for command authentication
    - MAC chaining
    - Optional C-ENC for command encryption

    Attributes:
        is_authenticated: Whether secure channel is established.
        security_level: Current security level (0x01=CMAC, 0x03=CENC+CMAC).

    Example:
        ```python
        scp = SCP02(client.transmit)

        # Use custom keys
        keys = SCPKeys(enc=my_enc, mac=my_mac, dek=my_dek)
        scp.initialize(keys=keys, security_level=0x03)  # With encryption

        # Send secured command
        response = scp.send(command)
        ```
    """

    def __init__(
        self,
        transmit_func: TransmitFunc,
        auto_get_response: bool = True,
    ):
        """Initialize SCP02 secure channel.

        Args:
            transmit_func: Function to transmit APDU and receive response.
            auto_get_response: Automatically handle GET RESPONSE (SW=61xx).
        """
        self._apdu = APDUInterface(transmit_func, auto_get_response)
        self._transmit = transmit_func

        # Session state
        self._is_authenticated = False
        self._security_level = SECURITY_LEVEL_NONE
        self._session_keys: Optional[_SCP02SessionKeys] = None
        self._mac_chaining_value = bytes(8)  # IV for MAC chaining

        # Challenge/response data
        self._host_challenge = bytes(8)
        self._card_challenge = bytes(8)
        self._sequence_counter = bytes(2)
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
            security_level: Desired security level (0x01=CMAC, 0x03=CENC+CMAC).
            host_challenge: Custom host challenge (random if not provided).

        Raises:
            AuthenticationError: If authentication fails.
            APDUError: If card returns error.
        """
        if keys is None:
            keys = SCPKeys.default_test_keys()
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

        self._is_authenticated = True
        self._security_level = security_level
        logger.info(f"SCP02 secure channel established (security level: {security_level:02X})")

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
            p2=0x00,  # Key identifier (0 = first available)
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
        - Bytes 10-11: Key information (version, SCP ID)
        - Bytes 12-13: Sequence counter
        - Bytes 14-19: Card challenge
        - Bytes 20-27: Card cryptogram

        Args:
            data: Response data.
        """
        self._key_diversification_data = data[0:10]
        key_version = data[10]
        scp_id = data[11]
        self._sequence_counter = data[12:14]
        self._card_challenge = data[14:20]

        logger.debug(
            f"INITIALIZE UPDATE: key_version={key_version:02X}, "
            f"scp_id={scp_id:02X}, seq={self._sequence_counter.hex()}"
        )

        if scp_id not in [0x02, 0x15]:  # SCP02 variants
            logger.warning(f"Unexpected SCP identifier: {scp_id:02X}")

    def _derive_session_keys(self, static_keys: SCPKeys) -> "_SCP02SessionKeys":
        """Derive session keys from static keys.

        SCP02 session key derivation uses:
        - Input: sequence counter + derivation constant
        - Triple-DES CBC encryption with zero IV

        Args:
            static_keys: Static card keys.

        Returns:
            Derived session keys.
        """
        # Session MAC key
        s_mac = self._derive_key(
            static_keys.mac,
            self._sequence_counter + DERIVATION_CONST_CMAC[:2],
        )

        # Session encryption key
        s_enc = self._derive_key(
            static_keys.enc,
            self._sequence_counter + DERIVATION_CONST_ENC[:2],
        )

        # Data encryption key (DEK) - used as-is for key encryption
        s_dek = static_keys.dek

        logger.debug("Session keys derived")
        return _SCP02SessionKeys(enc=s_enc, mac=s_mac, dek=s_dek)

    def _derive_key(self, key: bytes, derivation_data: bytes) -> bytes:
        """Derive a session key using Triple-DES.

        Args:
            key: Base key (16 or 24 bytes).
            derivation_data: Data to encrypt for derivation.

        Returns:
            Derived 16-byte key.
        """
        # Ensure key is 24 bytes (3DES requires 24 bytes)
        if len(key) == 16:
            key = key + key[:8]  # K1 + K2 + K1

        # Pad derivation data to 16 bytes
        pad_data = derivation_data.ljust(16, b'\x00')

        # Encrypt with Triple-DES CBC, zero IV
        cipher = Cipher(
            algorithms.TripleDES(key),
            modes.CBC(bytes(8)),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        derived = encryptor.update(pad_data) + encryptor.finalize()

        return derived[:16]

    def _verify_card_cryptogram(self, card_cryptogram: bytes) -> bool:
        """Verify card cryptogram for mutual authentication.

        Card cryptogram = MAC over (host_challenge || sequence_counter || card_challenge)

        Args:
            card_cryptogram: Cryptogram from card.

        Returns:
            True if cryptogram is valid.
        """
        # Build derivation data
        data = (
            self._host_challenge +
            self._sequence_counter +
            self._card_challenge
        )

        # Calculate expected cryptogram using session MAC key
        expected = self._calculate_full_mac(data, self._session_keys.enc)

        # Constant-time comparison
        return secrets.compare_digest(card_cryptogram, expected)

    def _calculate_host_cryptogram(self) -> bytes:
        """Calculate host cryptogram for mutual authentication.

        Host cryptogram = MAC over (sequence_counter || card_challenge || host_challenge)

        Returns:
            8-byte host cryptogram.
        """
        data = (
            self._sequence_counter +
            self._card_challenge +
            self._host_challenge
        )

        return self._calculate_full_mac(data, self._session_keys.enc)

    def _calculate_full_mac(self, data: bytes, key: bytes) -> bytes:
        """Calculate full (8-byte) MAC using ISO 9797-1 Method 2.

        Uses single-DES CBC for intermediate blocks, 3DES for final block.

        Args:
            data: Data to MAC.
            key: MAC key (16 bytes).

        Returns:
            8-byte MAC value.
        """
        # Pad data
        padded = self._pad_iso9797(data)

        # Split into 8-byte blocks
        blocks = [padded[i:i + 8] for i in range(0, len(padded), 8)]

        # Process all but last block with single DES
        mac = bytes(8)  # IV
        des_key = key[:8]
        for block in blocks[:-1]:
            xored = bytes(a ^ b for a, b in zip(mac, block))
            cipher = Cipher(
                algorithms.TripleDES(des_key + des_key + des_key),
                modes.ECB(),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()
            mac = encryptor.update(xored) + encryptor.finalize()

        # Process last block with full 3DES
        xored = bytes(a ^ b for a, b in zip(mac, blocks[-1]))
        tdes_key = key + key[:8] if len(key) == 16 else key
        cipher = Cipher(
            algorithms.TripleDES(tdes_key),
            modes.ECB(),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        mac = encryptor.update(xored) + encryptor.finalize()

        return mac

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
        # Build command data: host cryptogram
        data = host_cryptogram

        # Add C-MAC
        command_header = bytes([GP_CLA_SECURE, INS.EXTERNAL_AUTH, security_level, 0x00])
        command_with_length = command_header + bytes([len(data) + 8])  # +8 for MAC
        mac = self._calculate_cmac(command_with_length + data)

        # Build final command
        command = APDUCommand(
            cla=GP_CLA_SECURE,
            ins=INS.EXTERNAL_AUTH,
            p1=security_level,
            p2=0x00,
            data=data + mac,
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

    def _calculate_cmac(self, data: bytes) -> bytes:
        """Calculate C-MAC for command authentication.

        Uses MAC chaining: MAC is calculated over (chaining_value || data)

        Args:
            data: Command data (header + length + command data).

        Returns:
            8-byte C-MAC.
        """
        # Prepend MAC chaining value
        full_data = self._mac_chaining_value + data

        # Calculate MAC
        return self._calculate_full_mac(full_data, self._session_keys.mac)

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

        # Send and return response
        return self._transmit(secured_command)

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

        # Set secure CLA
        secure_cla = cla | 0x04  # Add secure messaging indicator

        # Encrypt data if required
        if self._security_level & SECURITY_LEVEL_CENC_CMAC == SECURITY_LEVEL_CENC_CMAC and data:
            data = self._encrypt_data(data)

        # Build header for MAC calculation
        new_lc = len(data) + 8  # +8 for MAC
        header = bytes([secure_cla, ins, p1, p2, new_lc])

        # Calculate C-MAC
        mac = self._calculate_cmac(header + data)

        # Update MAC chaining value
        self._mac_chaining_value = mac

        # Build secured command
        secured = bytes([secure_cla, ins, p1, p2, new_lc]) + data + mac

        if le is not None:
            secured += bytes([le])

        return secured

    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt command data using session encryption key.

        Uses Triple-DES CBC with zero IV.

        Args:
            data: Plain data.

        Returns:
            Encrypted data.
        """
        # Pad data
        padded = self._pad_iso9797(data)

        # Encrypt with 3DES CBC
        key = self._session_keys.enc
        if len(key) == 16:
            key = key + key[:8]

        cipher = Cipher(
            algorithms.TripleDES(key),
            modes.CBC(bytes(8)),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(padded) + encryptor.finalize()

    @staticmethod
    def _pad_iso9797(data: bytes) -> bytes:
        """Apply ISO 9797-1 Method 2 padding.

        Appends 0x80 followed by zeros to reach 8-byte boundary.

        Args:
            data: Data to pad.

        Returns:
            Padded data.
        """
        # Add mandatory 0x80 byte
        padded = data + b'\x80'

        # Pad to 8-byte boundary
        pad_length = (8 - (len(padded) % 8)) % 8
        return padded + (b'\x00' * pad_length)

    def close(self) -> None:
        """Close secure channel (clear session data)."""
        self._is_authenticated = False
        self._security_level = SECURITY_LEVEL_NONE
        self._session_keys = None
        self._mac_chaining_value = bytes(8)
        logger.debug("SCP02 secure channel closed")

    def wrap_key(self, key: bytes) -> bytes:
        """Wrap a key for secure transmission using DEK.

        Args:
            key: Key to wrap (must be 16 or 24 bytes).

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

        # Use DEK for key wrapping
        dek = self._session_keys.dek
        if len(dek) == 16:
            dek = dek + dek[:8]

        # Encrypt key with 3DES ECB
        cipher = Cipher(
            algorithms.TripleDES(dek),
            modes.ECB(),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return encryptor.update(key) + encryptor.finalize()


# =============================================================================
# Session Keys Container
# =============================================================================


class _SCP02SessionKeys:
    """Container for SCP02 session keys."""

    __slots__ = ("enc", "mac", "dek")

    def __init__(self, enc: bytes, mac: bytes, dek: bytes):
        self.enc = enc
        self.mac = mac
        self.dek = dek
