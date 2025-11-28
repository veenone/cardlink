"""Simulator configuration dataclasses.

This module defines configuration dataclasses for the Mobile Simulator,
including connection settings, PSK credentials, UICC profile, and behavior options.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .models import BehaviorMode, ConnectionMode, VirtualApplet


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class UICCProfile:
    """Virtual UICC profile configuration.

    Attributes:
        iccid: Integrated Circuit Card Identifier.
        imsi: International Mobile Subscriber Identity.
        msisdn: Mobile Station International Subscriber Directory Number.
        aid_isd: Issuer Security Domain AID (hex string).
        gp_version: GlobalPlatform card specification version.
        scp_version: Secure Channel Protocol version.
        applets: List of pre-installed virtual applets.

    Example:
        >>> profile = UICCProfile(
        ...     iccid="8901234567890123456",
        ...     imsi="310150123456789"
        ... )
    """

    iccid: str = "8901234567890123456"
    imsi: str = "310150123456789"
    msisdn: str = "+14155551234"
    aid_isd: str = "A000000151000000"
    gp_version: str = "2.2.1"
    scp_version: str = "03"
    applets: List[VirtualApplet] = field(default_factory=list)


@dataclass
class BehaviorConfig:
    """Simulation behavior configuration.

    Attributes:
        mode: Simulation behavior mode (normal, error, timeout).
        response_delay_ms: Normal response delay in milliseconds.
        error_rate: Probability of injecting errors (0.0 to 1.0).
        error_codes: List of error SW codes to inject.
        timeout_probability: Probability of simulating timeout (0.0 to 1.0).
        timeout_delay_min_ms: Minimum timeout delay in milliseconds.
        timeout_delay_max_ms: Maximum timeout delay in milliseconds.
        connection_mode: Connection behavior pattern.
        batch_size: Number of commands per connection in batch mode.
        reconnect_after: Number of commands before reconnecting.

    Example:
        >>> config = BehaviorConfig(mode=BehaviorMode.ERROR, error_rate=0.1)
    """

    mode: BehaviorMode = BehaviorMode.NORMAL
    response_delay_ms: int = 20
    error_rate: float = 0.0
    error_codes: List[str] = field(default_factory=lambda: ["6A82", "6985", "6D00"])
    timeout_probability: float = 0.0
    timeout_delay_min_ms: int = 1000
    timeout_delay_max_ms: int = 5000
    connection_mode: ConnectionMode = ConnectionMode.SINGLE
    batch_size: int = 5
    reconnect_after: int = 3

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid.
        """
        if self.response_delay_ms < 0:
            raise ValueError(f"Invalid response_delay_ms: {self.response_delay_ms}")

        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError(f"error_rate must be between 0.0 and 1.0: {self.error_rate}")

        if not 0.0 <= self.timeout_probability <= 1.0:
            raise ValueError(
                f"timeout_probability must be between 0.0 and 1.0: {self.timeout_probability}"
            )

        if self.timeout_delay_min_ms > self.timeout_delay_max_ms:
            raise ValueError(
                f"timeout_delay_min_ms ({self.timeout_delay_min_ms}) must be <= "
                f"timeout_delay_max_ms ({self.timeout_delay_max_ms})"
            )

        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1: {self.batch_size}")

        if self.reconnect_after < 1:
            raise ValueError(f"reconnect_after must be >= 1: {self.reconnect_after}")


@dataclass
class SimulatorConfig:
    """Mobile simulator configuration.

    Attributes:
        server_host: PSK-TLS server hostname or IP.
        server_port: PSK-TLS server port.
        psk_identity: PSK identity for TLS authentication.
        psk_key: PSK key bytes (16 or 32 bytes).
        connect_timeout: Connection timeout in seconds.
        read_timeout: Read timeout in seconds.
        retry_count: Number of connection retry attempts.
        retry_backoff: Backoff delays between retries in seconds.
        uicc_profile: Virtual UICC profile configuration.
        behavior: Simulation behavior configuration.

    Example:
        >>> config = SimulatorConfig(
        ...     server_host="192.168.1.100",
        ...     server_port=8443,
        ...     psk_identity="test_card_001",
        ...     psk_key=bytes.fromhex("0102030405060708090A0B0C0D0E0F10")
        ... )
    """

    # Server connection
    server_host: str = "127.0.0.1"
    server_port: int = 8443
    connect_timeout: float = 30.0
    read_timeout: float = 30.0
    retry_count: int = 3
    retry_backoff: List[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])

    # PSK credentials
    psk_identity: str = "test_card"
    psk_key: bytes = field(default_factory=lambda: b"\x00" * 16)

    # UICC profile
    uicc_profile: UICCProfile = field(default_factory=UICCProfile)

    # Behavior settings
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)

    @property
    def server_address(self) -> str:
        """Get server address as host:port string."""
        return f"{self.server_host}:{self.server_port}"

    @property
    def psk_key_hex(self) -> str:
        """Get PSK key as hex string."""
        return self.psk_key.hex().upper()

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.server_host:
            raise ValueError("server_host cannot be empty")

        if self.server_port < 1 or self.server_port > 65535:
            raise ValueError(f"Invalid server_port: {self.server_port}")

        if self.connect_timeout <= 0:
            raise ValueError(f"Invalid connect_timeout: {self.connect_timeout}")

        if self.read_timeout <= 0:
            raise ValueError(f"Invalid read_timeout: {self.read_timeout}")

        if self.retry_count < 0:
            raise ValueError(f"Invalid retry_count: {self.retry_count}")

        if not self.psk_identity:
            raise ValueError("psk_identity cannot be empty")

        if len(self.psk_key) not in (16, 32):
            raise ValueError(f"psk_key must be 16 or 32 bytes, got {len(self.psk_key)}")

        # Validate nested configs
        self.behavior.validate()

    @classmethod
    def from_dict(cls, data: dict) -> "SimulatorConfig":
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary (from YAML file).

        Returns:
            SimulatorConfig instance.

        Example:
            >>> data = {"server_host": "192.168.1.100", "psk_identity": "card_001"}
            >>> config = SimulatorConfig.from_dict(data)
        """
        # Extract nested configurations
        uicc_data = data.pop("uicc", {})
        behavior_data = data.pop("behavior", {})
        server_data = data.pop("server", {})
        psk_data = data.pop("psk", {})

        # Merge server and psk data into main config
        if server_data:
            data["server_host"] = server_data.get("host", data.get("server_host"))
            data["server_port"] = server_data.get("port", data.get("server_port"))
            data["connect_timeout"] = server_data.get(
                "connect_timeout", data.get("connect_timeout")
            )
            data["read_timeout"] = server_data.get("read_timeout", data.get("read_timeout"))
            data["retry_count"] = server_data.get("retry_count", data.get("retry_count"))
            data["retry_backoff"] = server_data.get("retry_backoff", data.get("retry_backoff"))

        if psk_data:
            data["psk_identity"] = psk_data.get("identity", data.get("psk_identity"))
            key_hex = psk_data.get("key", "")
            if key_hex:
                data["psk_key"] = bytes.fromhex(key_hex)

        # Build applets list
        applets = []
        applet_data = uicc_data.pop("applets", [])
        for applet in applet_data:
            applets.append(VirtualApplet(**applet))

        # Build UICC profile
        gp_data = uicc_data.pop("gp", {})
        if gp_data:
            uicc_data["gp_version"] = gp_data.get("version", "2.2.1")
            uicc_data["scp_version"] = gp_data.get("scp_version", "03")
            uicc_data["aid_isd"] = gp_data.get("isd_aid", "A000000151000000")
        uicc_profile = UICCProfile(applets=applets, **uicc_data) if uicc_data else UICCProfile()

        # Build behavior config
        mode_str = behavior_data.pop("mode", "normal")
        behavior_data["mode"] = BehaviorMode(mode_str)
        connection_mode_str = behavior_data.pop("connection_mode", None)
        if connection_mode_str:
            connection_data = behavior_data.pop("connection", {})
            behavior_data["connection_mode"] = ConnectionMode(
                connection_data.get("mode", connection_mode_str)
            )
            behavior_data["batch_size"] = connection_data.get(
                "batch_size", behavior_data.get("batch_size", 5)
            )
            behavior_data["reconnect_after"] = connection_data.get(
                "reconnect_after", behavior_data.get("reconnect_after", 3)
            )
        else:
            connection_data = behavior_data.pop("connection", {})
            if connection_data:
                behavior_data["connection_mode"] = ConnectionMode(
                    connection_data.get("mode", "single")
                )
                behavior_data["batch_size"] = connection_data.get("batch_size", 5)
                behavior_data["reconnect_after"] = connection_data.get("reconnect_after", 3)

        # Handle error and timeout sub-configs
        error_data = behavior_data.pop("error", {})
        if error_data:
            behavior_data["error_rate"] = error_data.get("rate", 0.0)
            behavior_data["error_codes"] = error_data.get("codes", ["6A82", "6985", "6D00"])

        timeout_data = behavior_data.pop("timeout", {})
        if timeout_data:
            behavior_data["timeout_probability"] = timeout_data.get("probability", 0.0)
            delay_range = timeout_data.get("delay_range", {})
            behavior_data["timeout_delay_min_ms"] = delay_range.get("min", 1000)
            behavior_data["timeout_delay_max_ms"] = delay_range.get("max", 5000)

        behavior_config = BehaviorConfig(**behavior_data) if behavior_data else BehaviorConfig()

        # Build main config (filter out None values)
        filtered_data = {k: v for k, v in data.items() if v is not None}
        return cls(uicc_profile=uicc_profile, behavior=behavior_config, **filtered_data)
