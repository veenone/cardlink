"""Custom exceptions for Modem Controller.

This module defines the exception hierarchy for modem-related errors,
including AT command errors with CME/CMS error code lookup.
"""

from typing import Optional


class ModemControllerError(Exception):
    """Base exception for all modem controller errors."""

    pass


class ModemNotFoundError(ModemControllerError):
    """Raised when specified modem is not connected or not found."""

    def __init__(self, port: Optional[str] = None, message: Optional[str] = None):
        self.port = port
        if message:
            super().__init__(message)
        elif port:
            super().__init__(f"Modem not found on port: {port}")
        else:
            super().__init__("No modem found")


class SerialPortError(ModemControllerError):
    """Raised for serial port communication errors."""

    def __init__(self, port: str, message: str, cause: Optional[Exception] = None):
        self.port = port
        self.cause = cause
        super().__init__(f"Serial port error on {port}: {message}")


class ATCommandError(ModemControllerError):
    """Raised when an AT command execution fails."""

    def __init__(self, command: str, message: str, raw_response: Optional[str] = None):
        self.command = command
        self.raw_response = raw_response
        super().__init__(f"AT command failed '{command}': {message}")


class ATTimeoutError(ATCommandError):
    """Raised when an AT command times out waiting for response."""

    def __init__(self, command: str, timeout: float):
        self.timeout = timeout
        super().__init__(command, f"Timeout after {timeout}s waiting for response")


# CME Error codes lookup table
# Reference: 3GPP TS 27.007
CME_ERRORS = {
    0: "Phone failure",
    1: "No connection to phone",
    2: "Phone-adaptor link reserved",
    3: "Operation not allowed",
    4: "Operation not supported",
    5: "PH-SIM PIN required",
    6: "PH-FSIM PIN required",
    7: "PH-FSIM PUK required",
    10: "SIM not inserted",
    11: "SIM PIN required",
    12: "SIM PUK required",
    13: "SIM failure",
    14: "SIM busy",
    15: "SIM wrong",
    16: "Incorrect password",
    17: "SIM PIN2 required",
    18: "SIM PUK2 required",
    20: "Memory full",
    21: "Invalid index",
    22: "Not found",
    23: "Memory failure",
    24: "Text string too long",
    25: "Invalid characters in text string",
    26: "Dial string too long",
    27: "Invalid characters in dial string",
    30: "No network service",
    31: "Network timeout",
    32: "Network not allowed - emergency calls only",
    40: "Network personalization PIN required",
    41: "Network personalization PUK required",
    42: "Network subset personalization PIN required",
    43: "Network subset personalization PUK required",
    44: "Service provider personalization PIN required",
    45: "Service provider personalization PUK required",
    46: "Corporate personalization PIN required",
    47: "Corporate personalization PUK required",
    48: "Hidden key required",
    49: "EAP method not supported",
    50: "Incorrect parameters",
    100: "Unknown error",
    103: "Illegal MS",
    106: "Illegal ME",
    107: "GPRS services not allowed",
    111: "PLMN not allowed",
    112: "Location area not allowed",
    113: "Roaming not allowed in this location area",
    132: "Service option not supported",
    133: "Requested service option not subscribed",
    134: "Service option temporarily out of order",
    148: "Unspecified GPRS error",
    149: "PDP authentication failure",
    150: "Invalid mobile class",
}


class CMEError(ATCommandError):
    """+CME ERROR from modem with error code lookup."""

    def __init__(self, code: int, command: str = "", raw_response: Optional[str] = None):
        self.code = code
        self.error_message = CME_ERRORS.get(code, f"Unknown CME error")
        message = f"+CME ERROR {code}: {self.error_message}"
        super().__init__(command, message, raw_response)


# CMS Error codes lookup table
# Reference: 3GPP TS 27.005
CMS_ERRORS = {
    1: "Unassigned (unallocated) number",
    8: "Operator determined barring",
    10: "Call barred",
    21: "Short message transfer rejected",
    27: "Destination out of service",
    28: "Unidentified subscriber",
    29: "Facility rejected",
    30: "Unknown subscriber",
    38: "Network out of order",
    41: "Temporary failure",
    42: "Congestion",
    47: "Resources unavailable, unspecified",
    50: "Requested facility not subscribed",
    69: "Requested facility not implemented",
    81: "Invalid short message transfer reference value",
    95: "Invalid message, unspecified",
    96: "Invalid mandatory information",
    97: "Message type non-existent or not implemented",
    98: "Message not compatible with short message protocol state",
    99: "Information element non-existent or not implemented",
    111: "Protocol error, unspecified",
    127: "Interworking, unspecified",
    128: "Telematic interworking not supported",
    129: "Short message Type 0 not supported",
    130: "Cannot replace short message",
    143: "Unspecified TP-PID error",
    144: "Data coding scheme (alphabet) not supported",
    145: "Message class not supported",
    159: "Unspecified TP-DCS error",
    160: "Command cannot be actioned",
    161: "Command unsupported",
    175: "Unspecified TP-Command error",
    176: "TPDU not supported",
    192: "SC busy",
    193: "No SC subscription",
    194: "SC system failure",
    195: "Invalid SME address",
    196: "Destination SME barred",
    197: "SM Rejected-Duplicate SM",
    198: "TP-VPF not supported",
    199: "TP-VP not supported",
    208: "D0 SIM SMS storage full",
    209: "No SMS storage capability in SIM",
    210: "Error in MS",
    211: "Memory Capacity Exceeded",
    212: "SIM Application Toolkit Busy",
    213: "SIM data download error",
    255: "Unspecified error cause",
    300: "ME failure",
    301: "SMS service of ME reserved",
    302: "Operation not allowed",
    303: "Operation not supported",
    304: "Invalid PDU mode parameter",
    305: "Invalid text mode parameter",
    310: "SIM not inserted",
    311: "SIM PIN required",
    312: "PH-SIM PIN required",
    313: "SIM failure",
    314: "SIM busy",
    315: "SIM wrong",
    316: "SIM PUK required",
    317: "SIM PIN2 required",
    318: "SIM PUK2 required",
    320: "Memory failure",
    321: "Invalid memory index",
    322: "Memory full",
    330: "SMSC address unknown",
    331: "No network service",
    332: "Network timeout",
    340: "No +CNMA acknowledgement expected",
    500: "Unknown error",
    512: "User abort",
    513: "Unable to store",
    514: "Invalid status",
    515: "Invalid character in address string",
    516: "Invalid length",
    517: "Invalid character in PDU",
    518: "Invalid parameter",
    519: "Invalid length or character",
    520: "Invalid character in text",
    521: "Timer expired",
    522: "Operation temporary not allowed",
}


class CMSError(ATCommandError):
    """+CMS ERROR from modem with error code lookup."""

    def __init__(self, code: int, command: str = "", raw_response: Optional[str] = None):
        self.code = code
        self.error_message = CMS_ERRORS.get(code, f"Unknown CMS error")
        message = f"+CMS ERROR {code}: {self.error_message}"
        super().__init__(command, message, raw_response)


class URCParseError(ModemControllerError):
    """Raised when URC parsing fails."""

    def __init__(self, line: str, reason: str):
        self.line = line
        self.reason = reason
        super().__init__(f"Failed to parse URC '{line}': {reason}")


class BIPMonitorError(ModemControllerError):
    """Raised for BIP monitoring errors."""

    pass


class SMSTriggerError(ModemControllerError):
    """Raised for SMS trigger errors."""

    def __init__(self, message: str, pdu: Optional[str] = None):
        self.pdu = pdu
        super().__init__(message)


class NetworkError(ModemControllerError):
    """Raised for network-related errors."""

    pass


class QXDMError(ModemControllerError):
    """Raised for QXDM diagnostic errors."""

    pass
