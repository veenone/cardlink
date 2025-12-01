"""Custom exception hierarchy for network simulator integration.

This module defines all exceptions used throughout the network simulator
integration, providing precise error handling and reporting.

Exception Hierarchy:
    NetworkSimulatorError (base)
    ├── ConnectionError - Connection failures
    ├── AuthenticationError - Authentication failures
    ├── CommandError - Command execution failures
    ├── TimeoutError - Operation timeouts
    └── ConfigurationError - Configuration errors
"""

from typing import Any, Optional


class NetworkSimulatorError(Exception):
    """Base exception for all network simulator errors.

    Attributes:
        message: Human-readable error message.
        details: Additional error context and details.

    Example:
        >>> raise NetworkSimulatorError("Operation failed", {"code": 500})
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return f"{self.__class__.__name__}({self.message!r}, details={self.details!r})"


class ConnectionError(NetworkSimulatorError):
    """Exception raised when connection to simulator fails.

    This exception is raised for:
    - Connection refused
    - Connection reset
    - Network unreachable
    - SSL/TLS errors (non-authentication)
    - Connection timeouts during establishment

    Attributes:
        url: The URL that was being connected to.
        cause: The underlying cause of the connection failure.

    Example:
        >>> raise ConnectionError(
        ...     "Connection refused",
        ...     {"url": "wss://localhost:9001", "cause": "ECONNREFUSED"}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        url: Optional[str] = None,
        cause: Optional[str] = None,
    ) -> None:
        """Initialize the connection error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            url: URL that was being connected to.
            cause: Underlying cause of the failure.
        """
        details = details or {}
        if url:
            details["url"] = url
        if cause:
            details["cause"] = cause
        super().__init__(message, details)
        self.url = url
        self.cause = cause


class AuthenticationError(NetworkSimulatorError):
    """Exception raised when authentication to simulator fails.

    This exception is raised for:
    - Invalid API key
    - Expired credentials
    - Certificate verification failures
    - Permission denied

    Attributes:
        identity: The identity (API key, username, etc.) that was used.

    Example:
        >>> raise AuthenticationError(
        ...     "Invalid API key",
        ...     {"identity": "my-key", "code": 401}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        identity: Optional[str] = None,
    ) -> None:
        """Initialize the authentication error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            identity: The identity that was used for authentication.
        """
        details = details or {}
        if identity:
            # Don't include full key, just indicate it was provided
            details["identity_provided"] = bool(identity)
        super().__init__(message, details)
        self.identity = identity


class CommandError(NetworkSimulatorError):
    """Exception raised when a simulator command fails.

    This exception is raised for:
    - Invalid command parameters
    - Command execution failures
    - Resource not found errors
    - Rate limiting

    Attributes:
        method: The command method that was called.
        params: The parameters that were passed.
        error_code: JSON-RPC or application error code.

    Example:
        >>> raise CommandError(
        ...     "UE not found",
        ...     {"method": "ue.get", "imsi": "001010123456789", "code": -32003}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        method: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        error_code: Optional[int] = None,
    ) -> None:
        """Initialize the command error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            method: The command method that was called.
            params: The parameters that were passed (sensitive data may be redacted).
            error_code: JSON-RPC or application error code.
        """
        details = details or {}
        if method:
            details["method"] = method
        if params:
            # Redact potentially sensitive parameters
            safe_params = {
                k: v if k not in ("api_key", "password", "secret") else "***"
                for k, v in params.items()
            }
            details["params"] = safe_params
        if error_code is not None:
            details["error_code"] = error_code
        super().__init__(message, details)
        self.method = method
        self.params = params
        self.error_code = error_code


class TimeoutError(NetworkSimulatorError):
    """Exception raised when an operation times out.

    This exception is raised for:
    - Command response timeouts
    - Operation timeouts
    - Wait timeouts (e.g., wait_for_registration)

    Attributes:
        operation: The operation that timed out.
        timeout: The timeout value that was exceeded.

    Example:
        >>> raise TimeoutError(
        ...     "Wait for UE registration timed out",
        ...     {"operation": "wait_for_registration", "timeout": 30, "imsi": "001010123456789"}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Initialize the timeout error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            operation: The operation that timed out.
            timeout: The timeout value that was exceeded.
        """
        details = details or {}
        if operation:
            details["operation"] = operation
        if timeout is not None:
            details["timeout_seconds"] = timeout
        super().__init__(message, details)
        self.operation = operation
        self.timeout = timeout


class ConfigurationError(NetworkSimulatorError):
    """Exception raised for configuration errors.

    This exception is raised for:
    - Invalid configuration values
    - Missing required configuration
    - Incompatible configuration options

    Attributes:
        config_key: The configuration key that has an error.
        config_value: The invalid configuration value.

    Example:
        >>> raise ConfigurationError(
        ...     "Invalid URL scheme",
        ...     {"config_key": "url", "config_value": "http://localhost:9001"}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
    ) -> None:
        """Initialize the configuration error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            config_key: The configuration key that has an error.
            config_value: The invalid configuration value (sensitive values are redacted).
        """
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            # Redact potentially sensitive values
            if config_key in ("api_key", "password", "secret"):
                details["config_value"] = "***"
            else:
                details["config_value"] = config_value
        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value


class NotConnectedError(NetworkSimulatorError):
    """Exception raised when attempting operations on disconnected simulator.

    This exception is raised when:
    - Operations are attempted before calling connect()
    - Operations are attempted after disconnection

    Example:
        >>> raise NotConnectedError("Not connected to simulator")
    """

    def __init__(
        self,
        message: str = "Not connected to simulator",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the not connected error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)


class ResourceNotFoundError(CommandError):
    """Exception raised when a requested resource is not found.

    This exception is raised for:
    - UE not found
    - Session not found
    - Configuration key not found

    Attributes:
        resource_type: Type of resource (e.g., "UE", "Session").
        resource_id: Identifier of the resource.

    Example:
        >>> raise ResourceNotFoundError(
        ...     "UE not found",
        ...     resource_type="UE",
        ...     resource_id="001010123456789"
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Initialize the resource not found error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            resource_type: Type of resource (e.g., "UE", "Session").
            resource_id: Identifier of the resource.
            method: The command method that was called.
        """
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, details, method=method, error_code=-32003)
        self.resource_type = resource_type
        self.resource_id = resource_id


class RateLimitError(CommandError):
    """Exception raised when rate limited by the simulator.

    This exception is raised when:
    - Too many requests in a short period
    - Server is overloaded

    Attributes:
        retry_after: Suggested wait time before retrying (seconds).

    Example:
        >>> raise RateLimitError(
        ...     "Rate limit exceeded",
        ...     retry_after=5.0
        ... )
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        method: Optional[str] = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            retry_after: Suggested wait time before retrying (seconds).
            method: The command method that was called.
        """
        details = details or {}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, details, method=method, error_code=-32429)
        self.retry_after = retry_after


class CircuitBreakerOpenError(NetworkSimulatorError):
    """Exception raised when circuit breaker is open.

    This exception indicates the system has detected repeated failures
    and is temporarily refusing requests to allow recovery.

    Attributes:
        open_until: When the circuit breaker will attempt to close.
        failure_count: Number of failures that triggered the breaker.

    Example:
        >>> raise CircuitBreakerOpenError(
        ...     "Circuit breaker open due to repeated failures"
        ... )
    """

    def __init__(
        self,
        message: str = "Circuit breaker open - service temporarily unavailable",
        details: Optional[dict[str, Any]] = None,
        open_until: Optional[float] = None,
        failure_count: int = 0,
    ) -> None:
        """Initialize the circuit breaker error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
            open_until: Timestamp when breaker will half-open.
            failure_count: Number of failures that triggered the breaker.
        """
        details = details or {}
        if open_until is not None:
            details["open_until"] = open_until
        if failure_count:
            details["failure_count"] = failure_count
        super().__init__(message, details)
        self.open_until = open_until
        self.failure_count = failure_count


class RetryableError(NetworkSimulatorError):
    """Marker class for errors that can be retried.

    Subclass this for errors that may succeed on retry.
    The retry logic can check isinstance(error, RetryableError).
    """

    pass


class TransientConnectionError(ConnectionError, RetryableError):
    """Connection error that may succeed on retry.

    This exception is raised for:
    - Temporary network issues
    - Server temporarily unavailable
    - Connection reset (non-fatal)

    Example:
        >>> raise TransientConnectionError(
        ...     "Connection temporarily unavailable, will retry"
        ... )
    """

    pass


class PermanentConnectionError(ConnectionError):
    """Connection error that should not be retried.

    This exception is raised for:
    - Invalid URL/host
    - Certificate errors
    - Authentication failures at transport level

    Example:
        >>> raise PermanentConnectionError(
        ...     "Invalid SSL certificate"
        ... )
    """

    pass
