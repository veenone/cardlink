"""PSK-TLS Admin Server for SCP81 OTA Testing.

This module provides a PSK-TLS server implementation for GlobalPlatform
SCP81 Over-The-Air (OTA) UICC administration testing.

Example:
    >>> from gp_ota_tester.server import AdminServer, ServerConfig, FileKeyStore
    >>> config = ServerConfig(port=8443)
    >>> key_store = FileKeyStore("keys.yaml")
    >>> server = AdminServer(config, key_store)
    >>> server.start()
"""

from gp_ota_tester.server.config import CipherConfig, ServerConfig
from gp_ota_tester.server.event_emitter import (
    EVENT_APDU_RECEIVED,
    EVENT_APDU_SENT,
    EVENT_CONNECTION_INTERRUPTED,
    EVENT_HANDSHAKE_COMPLETED,
    EVENT_HANDSHAKE_FAILED,
    EVENT_HIGH_ERROR_RATE,
    EVENT_PSK_MISMATCH,
    EVENT_SERVER_STARTED,
    EVENT_SERVER_STOPPED,
    EVENT_SESSION_ENDED,
    EVENT_SESSION_STARTED,
    EventEmitter,
    MockEventEmitter,
)
from gp_ota_tester.server.key_store import (
    DatabaseKeyStore,
    FileKeyStore,
    KeyStore,
    MemoryKeyStore,
)
from gp_ota_tester.server.models import (
    APDUExchange,
    CloseReason,
    HandshakeProgress,
    HandshakeState,
    Session,
    SessionState,
    TLSAlert,
    TLSSessionInfo,
)
from gp_ota_tester.server.http_handler import (
    CONTENT_TYPE_GP_ADMIN,
    AdminRequest,
    APDUCommand,
    APDUResponse,
    HTTPHandler,
    HTTPRequest,
    HTTPResponse,
    HTTPStatus,
    MockHTTPHandler,
)
from gp_ota_tester.server.gp_command_processor import (
    GPCommandProcessor,
    MockGPCommandProcessor,
    ResponseHandler,
    SelectHandler,
    InstallHandler,
    DeleteHandler,
    GetStatusHandler,
    InitUpdateHandler,
    ExtAuthHandler,
    INS_SELECT,
    INS_INSTALL,
    INS_DELETE,
    INS_GET_STATUS,
    INS_INITIALIZE_UPDATE,
    INS_EXTERNAL_AUTHENTICATE,
)
from gp_ota_tester.server.admin_server import (
    AdminServer,
    MockAdminServer,
    AdminServerError,
    ServerStartError,
    ServerNotRunningError,
)
from gp_ota_tester.server.session_manager import (
    SessionManager,
    SessionManagerError,
    InvalidStateTransition,
    SessionNotFound,
)
from gp_ota_tester.server.error_handler import (
    ErrorHandler,
    MismatchTracker,
)
from gp_ota_tester.server.tls_handler import (
    TLSHandler,
    MockTLSHandler,
    TLSHandlerError,
    HandshakeError,
    HAS_PSK_SUPPORT,
)

__all__ = [
    # Configuration
    "ServerConfig",
    "CipherConfig",
    # Key Stores
    "KeyStore",
    "FileKeyStore",
    "MemoryKeyStore",
    "DatabaseKeyStore",
    # Event Emitter
    "EventEmitter",
    "MockEventEmitter",
    # Event Type Constants
    "EVENT_SERVER_STARTED",
    "EVENT_SERVER_STOPPED",
    "EVENT_SESSION_STARTED",
    "EVENT_SESSION_ENDED",
    "EVENT_HANDSHAKE_COMPLETED",
    "EVENT_HANDSHAKE_FAILED",
    "EVENT_APDU_RECEIVED",
    "EVENT_APDU_SENT",
    "EVENT_PSK_MISMATCH",
    "EVENT_CONNECTION_INTERRUPTED",
    "EVENT_HIGH_ERROR_RATE",
    # Models
    "TLSSessionInfo",
    "Session",
    "APDUExchange",
    "HandshakeProgress",
    # Enums
    "SessionState",
    "CloseReason",
    "HandshakeState",
    "TLSAlert",
    # HTTP Handler
    "HTTPHandler",
    "MockHTTPHandler",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPStatus",
    "AdminRequest",
    "APDUCommand",
    "APDUResponse",
    "CONTENT_TYPE_GP_ADMIN",
    # GP Command Processor
    "GPCommandProcessor",
    "MockGPCommandProcessor",
    "ResponseHandler",
    "SelectHandler",
    "InstallHandler",
    "DeleteHandler",
    "GetStatusHandler",
    "InitUpdateHandler",
    "ExtAuthHandler",
    # INS Code Constants
    "INS_SELECT",
    "INS_INSTALL",
    "INS_DELETE",
    "INS_GET_STATUS",
    "INS_INITIALIZE_UPDATE",
    "INS_EXTERNAL_AUTHENTICATE",
    # Admin Server
    "AdminServer",
    "MockAdminServer",
    "AdminServerError",
    "ServerStartError",
    "ServerNotRunningError",
    # Session Manager
    "SessionManager",
    "SessionManagerError",
    "InvalidStateTransition",
    "SessionNotFound",
    # Error Handler
    "ErrorHandler",
    "MismatchTracker",
    # TLS Handler
    "TLSHandler",
    "MockTLSHandler",
    "TLSHandlerError",
    "HandshakeError",
    "HAS_PSK_SUPPORT",
]
