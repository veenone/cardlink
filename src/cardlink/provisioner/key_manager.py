"""Key management utilities for UICC Provisioner.

This module provides cryptographic key management operations including
secure random key generation, HKDF-based key derivation, constant-time
comparisons, and secure memory erasure.
"""

import hashlib
import hmac
import secrets
from typing import Optional

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


class KeyManager:
    """Cryptographic key management utilities.

    This class provides methods for:
    - Generating cryptographically secure random keys
    - Deriving keys using HKDF (HMAC-based Extract-and-Expand Key Derivation Function)
    - Constant-time key comparison to prevent timing attacks
    - Secure memory erasure for sensitive key material

    Example:
        >>> # Generate a 16-byte random key
        >>> key = KeyManager.generate_random_key(16)
        >>> print(f"Key: {key.hex()}")

        >>> # Derive a key from a master key
        >>> master_key = KeyManager.generate_random_key(32)
        >>> derived = KeyManager.derive_key(
        ...     master_key,
        ...     info=b"encryption",
        ...     length=16
        ... )

        >>> # Constant-time comparison
        >>> if KeyManager.secure_compare(key1, key2):
        ...     print("Keys match")
    """

    @staticmethod
    def generate_random_key(size: int) -> bytes:
        """Generate a cryptographically secure random key.

        Uses the `secrets` module which provides cryptographically
        strong random numbers suitable for managing data such as
        passwords, account authentication, security tokens, and
        related secrets.

        Args:
            size: Key size in bytes.

        Returns:
            Random key bytes of specified size.

        Raises:
            ValueError: If size is less than 1.

        Example:
            >>> key = KeyManager.generate_random_key(16)
            >>> len(key)
            16
            >>> key_128 = KeyManager.generate_random_key(16)  # 128-bit
            >>> key_256 = KeyManager.generate_random_key(32)  # 256-bit
        """
        if size < 1:
            raise ValueError("Key size must be at least 1 byte")

        return secrets.token_bytes(size)

    @staticmethod
    def derive_key(
        master_key: bytes,
        salt: Optional[bytes] = None,
        info: Optional[bytes] = None,
        length: int = 32,
        algorithm: str = "sha256"
    ) -> bytes:
        """Derive a key using HKDF (HMAC-based KDF).

        HKDF is a simple key derivation function (KDF) based on the
        HMAC message authentication code. It is defined in RFC 5869.

        The HKDF function performs two operations:
        1. Extract: Derives a pseudorandom key from input key material
        2. Expand: Expands the pseudorandom key to the desired length

        Args:
            master_key: Input key material.
            salt: Optional salt value (random value).
                  If None, a string of zeros equal to hash length is used.
            info: Optional context and application specific information.
                  This allows deriving different keys from the same master key.
            length: Desired length of derived key in bytes.
            algorithm: Hash algorithm to use ("sha256" or "sha384").

        Returns:
            Derived key bytes of specified length.

        Raises:
            ValueError: If algorithm is not supported or length is invalid.

        Example:
            >>> master = KeyManager.generate_random_key(32)
            >>> # Derive different keys for different purposes
            >>> enc_key = KeyManager.derive_key(
            ...     master, info=b"encryption", length=16
            ... )
            >>> mac_key = KeyManager.derive_key(
            ...     master, info=b"mac", length=16
            ... )
        """
        # Select hash algorithm
        if algorithm == "sha256":
            hash_algorithm = hashes.SHA256()
        elif algorithm == "sha384":
            hash_algorithm = hashes.SHA384()
        elif algorithm == "sha512":
            hash_algorithm = hashes.SHA512()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        # Create HKDF instance
        hkdf = HKDF(
            algorithm=hash_algorithm,
            length=length,
            salt=salt,
            info=info,
            backend=default_backend()
        )

        # Derive key
        return hkdf.derive(master_key)

    @staticmethod
    def secure_compare(a: bytes, b: bytes) -> bool:
        """Compare two byte strings in constant time.

        This function compares two byte strings in constant time to
        prevent timing attacks. Regular comparison operations (==)
        can leak information about the values being compared through
        timing variations.

        Args:
            a: First byte string.
            b: Second byte string.

        Returns:
            True if byte strings are equal, False otherwise.

        Note:
            This uses hmac.compare_digest which is designed to prevent
            timing analysis by avoiding short-circuit evaluation.

        Example:
            >>> key1 = b"secret_key_123"
            >>> key2 = b"secret_key_123"
            >>> key3 = b"different_key"
            >>> KeyManager.secure_compare(key1, key2)
            True
            >>> KeyManager.secure_compare(key1, key3)
            False
        """
        return hmac.compare_digest(a, b)

    @staticmethod
    def secure_erase(data: bytearray) -> None:
        """Securely erase sensitive data from memory.

        Overwrites the memory containing sensitive data with zeros
        to prevent it from lingering in memory after use.

        Note:
            This is a best-effort operation. Python's memory management
            may have made copies of the data that cannot be directly
            overwritten. For maximum security, use memory-secure types
            or libraries designed for handling secrets.

        Args:
            data: Bytearray to erase (must be mutable).

        Example:
            >>> secret = bytearray(b"my_secret_key")
            >>> # Use the secret
            >>> process_secret(secret)
            >>> # Erase it when done
            >>> KeyManager.secure_erase(secret)
            >>> secret
            bytearray(b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00')
        """
        if not isinstance(data, bytearray):
            raise TypeError("Data must be a bytearray for in-place modification")

        # Overwrite with zeros
        for i in range(len(data)):
            data[i] = 0

    @staticmethod
    def constant_time_compare_digest(a: bytes, b: bytes, digest_length: int = 8) -> bool:
        """Compare first N bytes of two digests in constant time.

        Useful for comparing truncated MACs or cryptogram values.

        Args:
            a: First byte string.
            b: Second byte string.
            digest_length: Number of bytes to compare.

        Returns:
            True if first digest_length bytes match, False otherwise.

        Example:
            >>> mac1 = bytes.fromhex("AABBCCDD11223344")
            >>> mac2 = bytes.fromhex("AABBCCDD99887766")
            >>> KeyManager.constant_time_compare_digest(mac1, mac2, 4)
            True
            >>> KeyManager.constant_time_compare_digest(mac1, mac2, 8)
            False
        """
        if len(a) < digest_length or len(b) < digest_length:
            return False

        return hmac.compare_digest(a[:digest_length], b[:digest_length])
