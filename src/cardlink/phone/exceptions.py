"""Custom exceptions for Phone Controller.

This module defines the exception hierarchy for phone controller errors,
including ADB, AT command, and device-related errors.
"""

from typing import Optional


class PhoneControllerError(Exception):
    """Base exception for all phone controller errors."""

    pass


class ADBNotFoundError(PhoneControllerError):
    """Raised when ADB executable is not found or not in PATH."""

    def __init__(self, message: Optional[str] = None):
        if message:
            super().__init__(message)
        else:
            super().__init__(
                "ADB not found. Please install Android SDK Platform Tools "
                "and ensure 'adb' is in your PATH. "
                "Download from: https://developer.android.com/studio/releases/platform-tools"
            )


class DeviceNotFoundError(PhoneControllerError):
    """Raised when specified device is not connected or not found."""

    def __init__(self, serial: Optional[str] = None, message: Optional[str] = None):
        self.serial = serial
        if message:
            super().__init__(message)
        elif serial:
            super().__init__(f"Device not found: {serial}")
        else:
            super().__init__("No device found. Is USB debugging enabled and authorized?")


class DeviceUnauthorizedError(PhoneControllerError):
    """Raised when device USB debugging is not authorized."""

    def __init__(self, serial: str):
        self.serial = serial
        super().__init__(
            f"Device {serial} is unauthorized. "
            "Please check the device and authorize USB debugging."
        )


class DeviceOfflineError(PhoneControllerError):
    """Raised when device is offline."""

    def __init__(self, serial: str):
        self.serial = serial
        super().__init__(
            f"Device {serial} is offline. "
            "Try disconnecting and reconnecting the USB cable."
        )


class ADBCommandError(PhoneControllerError):
    """Raised when an ADB command fails."""

    def __init__(
        self,
        command: str,
        message: str,
        returncode: int = -1,
        stdout: str = "",
        stderr: str = "",
    ):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"ADB command failed '{command}': {message}")


class ADBTimeoutError(ADBCommandError):
    """Raised when an ADB command times out."""

    def __init__(self, command: str, timeout: float):
        self.timeout = timeout
        super().__init__(command, f"Timeout after {timeout}s waiting for response")


class ATCommandError(PhoneControllerError):
    """Raised when an AT command execution fails."""

    def __init__(
        self,
        command: str,
        message: str,
        error_code: Optional[int] = None,
        raw_response: Optional[str] = None,
    ):
        self.command = command
        self.error_code = error_code
        self.raw_response = raw_response
        super().__init__(f"AT command failed '{command}': {message}")


class ATTimeoutError(ATCommandError):
    """Raised when an AT command times out."""

    def __init__(self, command: str, timeout: float):
        self.timeout = timeout
        super().__init__(command, f"Timeout after {timeout}s waiting for response")


class ATUnavailableError(ATCommandError):
    """Raised when AT interface is not available on the device."""

    def __init__(self, serial: str, reason: str = ""):
        self.serial = serial
        message = f"AT interface unavailable on device {serial}"
        if reason:
            message += f": {reason}"
        super().__init__("", message)


class RootRequiredError(PhoneControllerError):
    """Raised when an operation requires root access."""

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            f"Operation '{operation}' requires root access. "
            "Please root the device or use an alternative method."
        )


class TimeoutError(PhoneControllerError):
    """Raised when an operation times out."""

    def __init__(self, operation: str, timeout: float):
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation '{operation}' timed out after {timeout}s")


class LogcatError(PhoneControllerError):
    """Raised for logcat monitoring errors."""

    def __init__(self, message: str, serial: Optional[str] = None):
        self.serial = serial
        if serial:
            super().__init__(f"Logcat error on device {serial}: {message}")
        else:
            super().__init__(f"Logcat error: {message}")


class BIPMonitorError(PhoneControllerError):
    """Raised for BIP monitoring errors."""

    def __init__(self, message: str, serial: Optional[str] = None):
        self.serial = serial
        if serial:
            super().__init__(f"BIP monitor error on device {serial}: {message}")
        else:
            super().__init__(f"BIP monitor error: {message}")


class SMSTriggerError(PhoneControllerError):
    """Raised for SMS-PP trigger errors."""

    def __init__(self, message: str, pdu: Optional[str] = None):
        self.pdu = pdu
        super().__init__(message)


class NetworkConfigError(PhoneControllerError):
    """Raised for network configuration errors."""

    def __init__(self, message: str, operation: Optional[str] = None):
        self.operation = operation
        if operation:
            super().__init__(f"Network config error during '{operation}': {message}")
        else:
            super().__init__(f"Network config error: {message}")


class ProfileError(PhoneControllerError):
    """Base exception for profile-related errors."""

    pass


class ProfileNotFoundError(ProfileError):
    """Raised when a saved profile is not found."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Profile not found: {name}")


class ProfileSaveError(ProfileError):
    """Raised when saving a profile fails."""

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason
        super().__init__(f"Failed to save profile '{name}': {reason}")


class ProfileLoadError(ProfileError):
    """Raised when loading a profile fails."""

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason
        super().__init__(f"Failed to load profile '{name}': {reason}")
