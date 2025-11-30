"""Exception hierarchy for UICC Provisioner.

This module defines all exceptions used throughout the provisioner
module with helpful error messages and troubleshooting hints.
"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ProvisionerError(Exception):
    """Base exception for all provisioner errors.

    All provisioner-specific exceptions inherit from this class,
    allowing code to catch all provisioner errors with a single handler.

    Attributes:
        message: Human-readable error description.
        hint: Optional troubleshooting hint.
    """

    def __init__(self, message: str, hint: Optional[str] = None):
        self.message = message
        self.hint = hint
        super().__init__(message)

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message


# =============================================================================
# Reader and Connection Errors
# =============================================================================


class ReaderNotFoundError(ProvisionerError):
    """Raised when no PC/SC reader is found.

    This typically occurs when:
    - No smart card reader is connected
    - pcscd service is not running (Linux)
    - Reader drivers are not installed
    """

    def __init__(self, reader_name: Optional[str] = None):
        if reader_name:
            message = f"Reader not found: {reader_name}"
        else:
            message = "No PC/SC readers found"
        hint = (
            "Check that:\n"
            "  - Smart card reader is connected\n"
            "  - On Linux: pcscd service is running (sudo systemctl start pcscd)\n"
            "  - Reader drivers are installed"
        )
        super().__init__(message, hint)
        self.reader_name = reader_name


class CardNotFoundError(ProvisionerError):
    """Raised when no card is present in the reader.

    This occurs when trying to connect to a reader that
    doesn't have a card inserted.
    """

    def __init__(self, reader_name: str):
        message = f"No card present in reader: {reader_name}"
        hint = "Insert a smart card into the reader and try again."
        super().__init__(message, hint)
        self.reader_name = reader_name


class NotConnectedError(ProvisionerError):
    """Raised when an operation requires a card connection.

    This occurs when trying to send APDUs or perform operations
    without first establishing a connection to the card.
    """

    def __init__(self, operation: str = "this operation"):
        message = f"Not connected to card - cannot perform {operation}"
        hint = "Call connect() before performing card operations."
        super().__init__(message, hint)
        self.operation = operation


class ConnectionError(ProvisionerError):
    """Raised when card connection fails.

    This can occur due to:
    - Protocol mismatch (T=0 vs T=1)
    - Card communication error
    - Reader hardware issues
    """

    def __init__(self, reason: str, reader_name: Optional[str] = None):
        message = f"Connection failed: {reason}"
        if reader_name:
            message = f"Connection to {reader_name} failed: {reason}"
        hint = (
            "Try:\n"
            "  - Reseating the card\n"
            "  - Using a different protocol (T=0 or T=1)\n"
            "  - Checking if the card is damaged"
        )
        super().__init__(message, hint)
        self.reason = reason
        self.reader_name = reader_name


# =============================================================================
# APDU Errors
# =============================================================================


class APDUError(ProvisionerError):
    """Raised when an APDU command fails.

    This exception includes the status word (SW1, SW2) and
    a decoded status message for easier debugging.

    Attributes:
        sw1: First status byte.
        sw2: Second status byte.
        command: The APDU command that failed (hex string).
        status_message: Human-readable status description.
    """

    def __init__(
        self,
        sw1: int,
        sw2: int,
        command: Optional[str] = None,
        status_message: Optional[str] = None,
    ):
        self.sw1 = sw1
        self.sw2 = sw2
        self.command = command
        self.status_message = status_message or f"Unknown status: {sw1:02X}{sw2:02X}"

        sw_hex = f"{sw1:02X}{sw2:02X}"
        message = f"APDU error: SW={sw_hex} ({self.status_message})"
        if command:
            message = f"APDU error for command {command[:20]}...: SW={sw_hex} ({self.status_message})"

        hint = self._get_hint_for_sw(sw1, sw2)
        super().__init__(message, hint)

    @property
    def sw(self) -> int:
        """Get status word as 16-bit integer."""
        return (self.sw1 << 8) | self.sw2

    @staticmethod
    def _get_hint_for_sw(sw1: int, sw2: int) -> Optional[str]:
        """Get troubleshooting hint for common status words."""
        if sw1 == 0x69 and sw2 == 0x82:
            return "Security status not satisfied - try authenticating first."
        elif sw1 == 0x69 and sw2 == 0x85:
            return "Conditions of use not satisfied - check card state."
        elif sw1 == 0x6A and sw2 == 0x82:
            return "File or application not found - check AID/file path."
        elif sw1 == 0x6A and sw2 == 0x86:
            return "Incorrect parameters P1-P2 - check command format."
        elif sw1 == 0x63:
            return f"Verification failed - {sw2 & 0x0F} retries remaining."
        elif sw1 == 0x6D:
            return "Instruction not supported - check card capabilities."
        elif sw1 == 0x6E:
            return "Class not supported - try a different CLA byte."
        return None


class InvalidAPDUError(ProvisionerError):
    """Raised when an APDU is malformed.

    This occurs when:
    - APDU is too short or too long
    - Lc/Le values don't match data length
    - Invalid hex string
    """

    def __init__(self, reason: str, apdu: Optional[str] = None):
        message = f"Invalid APDU: {reason}"
        if apdu:
            message = f"Invalid APDU '{apdu}': {reason}"
        hint = (
            "APDU format: CLA INS P1 P2 [Lc Data...] [Le]\n"
            "Minimum length: 4 bytes (CLA INS P1 P2)"
        )
        super().__init__(message, hint)
        self.reason = reason
        self.apdu = apdu


# =============================================================================
# Authentication and Security Errors
# =============================================================================


class AuthenticationError(ProvisionerError):
    """Raised when authentication fails.

    This can occur during:
    - PIN verification
    - ADM key verification
    - Secure channel establishment
    """

    def __init__(
        self,
        reason: str,
        retries_remaining: Optional[int] = None,
    ):
        self.reason = reason
        self.retries_remaining = retries_remaining

        message = f"Authentication failed: {reason}"
        if retries_remaining is not None:
            message += f" ({retries_remaining} retries remaining)"

        if retries_remaining is not None and retries_remaining <= 2:
            hint = f"WARNING: Only {retries_remaining} retries remaining before lockout!"
        else:
            hint = "Check credentials and try again."

        super().__init__(message, hint)


class SecurityError(ProvisionerError):
    """Raised for security-related failures.

    This includes:
    - Secure channel failures
    - Cryptogram verification failures
    - Key derivation errors
    """

    def __init__(self, reason: str, operation: Optional[str] = None):
        self.reason = reason
        self.operation = operation

        message = f"Security error: {reason}"
        if operation:
            message = f"Security error during {operation}: {reason}"

        hint = (
            "This may indicate:\n"
            "  - Incorrect keys\n"
            "  - Card cryptogram mismatch\n"
            "  - Secure channel out of sync"
        )
        super().__init__(message, hint)


class SecureChannelError(SecurityError):
    """Raised when secure channel operations fail.

    Specific to SCP02/SCP03 secure channel issues.
    """

    def __init__(self, reason: str, scp_version: Optional[str] = None):
        self.scp_version = scp_version
        operation = f"SCP{scp_version}" if scp_version else "secure channel"
        super().__init__(reason, operation)


# =============================================================================
# Profile Errors
# =============================================================================


class ProfileError(ProvisionerError):
    """Base exception for profile-related errors."""

    def __init__(self, message: str, profile_name: Optional[str] = None):
        self.profile_name = profile_name
        if profile_name:
            message = f"Profile '{profile_name}': {message}"
        super().__init__(message)


class ProfileNotFoundError(ProfileError):
    """Raised when a profile file is not found."""

    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        message = f"Profile not found: {profile_path}"
        super().__init__(message)
        self.hint = "Check the profile path and ensure the file exists."


class ProfileValidationError(ProfileError):
    """Raised when profile validation fails."""

    def __init__(self, reason: str, profile_name: Optional[str] = None):
        self.reason = reason
        message = f"Profile validation failed: {reason}"
        super().__init__(message, profile_name)


class ProfileIncompatibleError(ProfileError):
    """Raised when a profile is incompatible with the card."""

    def __init__(self, reason: str, profile_name: Optional[str] = None):
        self.reason = reason
        message = f"Profile incompatible with card: {reason}"
        super().__init__(message, profile_name)
        self.hint = "Check ICCID pattern and card type compatibility."


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(ProvisionerError):
    """Raised when configuration operations fail."""

    def __init__(self, config_type: str, reason: str):
        self.config_type = config_type
        self.reason = reason
        message = f"{config_type} configuration error: {reason}"
        super().__init__(message)


class PSKConfigError(ConfigurationError):
    """Raised when PSK configuration fails."""

    def __init__(self, reason: str):
        super().__init__("PSK", reason)
        self.hint = "Ensure secure channel is established before writing keys."


class URLConfigError(ConfigurationError):
    """Raised when URL configuration fails."""

    def __init__(self, reason: str):
        super().__init__("URL", reason)


class TriggerConfigError(ConfigurationError):
    """Raised when trigger configuration fails."""

    def __init__(self, reason: str):
        super().__init__("Trigger", reason)


class BIPConfigError(ConfigurationError):
    """Raised when BIP configuration fails."""

    def __init__(self, reason: str):
        super().__init__("BIP", reason)
        self.hint = "Check terminal profile for BIP support."


# =============================================================================
# TLV Errors
# =============================================================================


class TLVError(ProvisionerError):
    """Raised when TLV parsing or construction fails."""

    def __init__(self, reason: str, data: Optional[bytes] = None):
        self.reason = reason
        self.data = data
        message = f"TLV error: {reason}"
        if data:
            message += f" (data: {data.hex()[:40]}...)"
        super().__init__(message)


class TLVParseError(TLVError):
    """Raised when TLV parsing fails."""

    def __init__(self, reason: str, offset: Optional[int] = None, data: Optional[bytes] = None):
        self.offset = offset
        if offset is not None:
            reason = f"{reason} at offset {offset}"
        super().__init__(reason, data)


# =============================================================================
# ATR Errors
# =============================================================================


class ATRError(ProvisionerError):
    """Raised when ATR parsing or validation fails."""

    def __init__(self, reason: str, atr: Optional[bytes] = None):
        self.reason = reason
        self.atr = atr
        message = f"ATR error: {reason}"
        if atr:
            message += f" (ATR: {atr.hex()})"
        super().__init__(message)


# =============================================================================
# Decorator for consistent error handling
# =============================================================================


def handle_provisioner_operation(operation_name: str) -> Callable[[F], F]:
    """Decorator for consistent error handling in provisioner operations.

    This decorator catches common exceptions and converts them to
    appropriate ProvisionerError subclasses with helpful messages.

    Args:
        operation_name: Name of the operation for error messages.

    Example:
        @handle_provisioner_operation("select application")
        def select_app(self, aid: str) -> APDUResponse:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except ProvisionerError:
                # Re-raise provisioner errors as-is
                raise
            except ValueError as e:
                raise ConfigurationError(operation_name, str(e)) from e
            except OSError as e:
                raise ProvisionerError(
                    f"I/O error during {operation_name}: {e}",
                    "Check reader connection and permissions.",
                ) from e
            except Exception as e:
                raise ProvisionerError(
                    f"Unexpected error during {operation_name}: {e}",
                    "See logs for details.",
                ) from e

        return wrapper  # type: ignore

    return decorator
