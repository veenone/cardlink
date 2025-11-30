"""Database model enumerations for GP OTA Tester.

This module defines enum types used across database models.

Example:
    >>> from cardlink.database.models.enums import DeviceType, SessionStatus
    >>> device_type = DeviceType.PHONE
    >>> status = SessionStatus.ACTIVE
"""

import enum


class DeviceType(enum.Enum):
    """Device type enumeration.

    Attributes:
        PHONE: Android phone device (connected via ADB).
        MODEM: USB modem device (connected via serial port).
    """

    PHONE = "phone"
    MODEM = "modem"


class SessionStatus(enum.Enum):
    """OTA session status enumeration.

    Attributes:
        PENDING: Session created but not yet started.
        ACTIVE: Session in progress, connection established.
        COMPLETED: Session finished successfully.
        FAILED: Session ended with an error.
        TIMEOUT: Session timed out waiting for connection.
    """

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TestStatus(enum.Enum):
    """Test result status enumeration.

    Attributes:
        PASSED: All assertions passed.
        FAILED: One or more assertions failed.
        SKIPPED: Test was skipped (precondition not met).
        ERROR: Test encountered an unexpected error.
    """

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class CommDirection(enum.Enum):
    """Communication log direction enumeration.

    Attributes:
        COMMAND: Command sent from server to card.
        RESPONSE: Response received from card.
    """

    COMMAND = "command"
    RESPONSE = "response"


class CardType(enum.Enum):
    """Card type enumeration.

    Attributes:
        UICC: Universal Integrated Circuit Card.
        USIM: Universal Subscriber Identity Module.
        EUICC: Embedded UICC (eSIM).
        ISIM: IP Multimedia Services Identity Module.
    """

    UICC = "UICC"
    USIM = "USIM"
    EUICC = "eUICC"
    ISIM = "ISIM"
