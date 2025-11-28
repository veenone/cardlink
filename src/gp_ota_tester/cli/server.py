"""CLI commands for PSK-TLS Admin Server.

This module provides Click-based CLI commands for starting, stopping,
and managing the PSK-TLS Admin Server.

Example:
    $ gp-ota-server start --port 8443 --config server.yaml
    $ gp-ota-server stop
    $ gp-ota-server status

Environment Variables:
    GP_OTA_SERVER_HOST: Override server host
    GP_OTA_SERVER_PORT: Override server port
    GP_OTA_SERVER_CONFIG: Default configuration file path
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

from gp_ota_tester.server import (
    AdminServer,
    CipherConfig,
    EventEmitter,
    FileKeyStore,
    MemoryKeyStore,
    ServerConfig,
    HAS_PSK_SUPPORT,
)

logger = logging.getLogger(__name__)

# Global server instance for signal handling
_server_instance: Optional[AdminServer] = None


# =============================================================================
# CLI Group
# =============================================================================


@click.group()
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool) -> None:
    """GP OTA Server - PSK-TLS Admin Server for SCP81 testing.

    A GlobalPlatform SCP81 compliant PSK-TLS server for Over-The-Air
    UICC administration testing.
    """
    # Configure logging
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug


# =============================================================================
# Start Command
# =============================================================================


@cli.command()
@click.option(
    "--host",
    default="127.0.0.1",
    envvar="GP_OTA_SERVER_HOST",
    help="Host to bind to (default: 127.0.0.1)",
)
@click.option(
    "--port", "-p",
    default=8443,
    type=int,
    envvar="GP_OTA_SERVER_PORT",
    help="Port to listen on (default: 8443)",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    envvar="GP_OTA_SERVER_CONFIG",
    help="Path to YAML configuration file",
)
@click.option(
    "--keys", "-k",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PSK keys YAML file",
)
@click.option(
    "--ciphers",
    default="production",
    type=click.Choice(["production", "legacy", "all"]),
    help="Cipher suite selection (default: production)",
)
@click.option(
    "--enable-null-ciphers",
    is_flag=True,
    help="Enable NULL cipher suites (NO ENCRYPTION - testing only!)",
)
@click.option(
    "--max-connections",
    default=10,
    type=int,
    help="Maximum concurrent connections (default: 10)",
)
@click.option(
    "--session-timeout",
    default=300.0,
    type=float,
    help="Session timeout in seconds (default: 300)",
)
@click.option(
    "--dashboard",
    is_flag=True,
    help="Enable web dashboard (requires dashboard module)",
)
@click.option(
    "--foreground", "-f",
    is_flag=True,
    help="Run in foreground (don't daemonize)",
)
@click.pass_context
def start(
    ctx: click.Context,
    host: str,
    port: int,
    config: Optional[Path],
    keys: Optional[Path],
    ciphers: str,
    enable_null_ciphers: bool,
    max_connections: int,
    session_timeout: float,
    dashboard: bool,
    foreground: bool,
) -> None:
    """Start the PSK-TLS Admin Server.

    The server will listen for incoming TLS-PSK connections and process
    GlobalPlatform APDU commands.

    Examples:

        # Start with defaults
        gp-ota-server start

        # Start on custom port
        gp-ota-server start --port 9443

        # Start with configuration file
        gp-ota-server start --config server.yaml

        # Start with verbose logging
        gp-ota-server -v start --port 8443
    """
    global _server_instance

    # Check PSK support
    if not HAS_PSK_SUPPORT:
        click.echo(
            click.style(
                "ERROR: sslpsk3 library not installed. "
                "Install with: pip install sslpsk3",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    # Load configuration
    try:
        server_config, key_store_path = load_configuration(
            config_path=config,
            host=host,
            port=port,
            ciphers=ciphers,
            enable_null_ciphers=enable_null_ciphers,
            max_connections=max_connections,
            session_timeout=session_timeout,
            keys_path=keys,
        )
    except ConfigurationError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"), err=True)
        sys.exit(1)

    # Show NULL cipher warning
    if enable_null_ciphers or (
        server_config.cipher_config and
        server_config.cipher_config.enable_null_ciphers
    ):
        click.echo(click.style(
            "\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  WARNING: NULL CIPHERS ENABLED - NO ENCRYPTION!              ║\n"
            "║  Traffic will be transmitted in PLAINTEXT.                   ║\n"
            "║  Use only for testing in isolated environments.              ║\n"
            "╚══════════════════════════════════════════════════════════════╝\n",
            fg="yellow",
        ))

    # Create key store
    if key_store_path and key_store_path.exists():
        click.echo(f"Loading PSK keys from: {key_store_path}")
        key_store = FileKeyStore(str(key_store_path))
    else:
        click.echo(
            click.style(
                "Warning: No keys file specified, using empty key store",
                fg="yellow",
            )
        )
        key_store = MemoryKeyStore()

    # Create event emitter
    event_emitter = EventEmitter()

    # Create server
    try:
        server = AdminServer(
            config=server_config,
            key_store=key_store,
            event_emitter=event_emitter,
        )
        _server_instance = server
    except Exception as e:
        click.echo(click.style(f"Failed to create server: {e}", fg="red"), err=True)
        sys.exit(1)

    # Setup signal handlers
    def signal_handler(signum: int, frame: Any) -> None:
        click.echo("\nReceived shutdown signal, stopping server...")
        if _server_instance:
            _server_instance.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    try:
        click.echo(f"Starting PSK-TLS Admin Server on {host}:{port}...")
        server.start()

        click.echo(click.style(
            f"Server started successfully on {host}:{port}",
            fg="green",
        ))

        if foreground:
            click.echo("Press Ctrl+C to stop the server")

            # Keep running until interrupted
            while server.is_running:
                time.sleep(1)
        else:
            click.echo(
                f"Server running in background. Use 'gp-ota-server stop' to stop."
            )

    except Exception as e:
        click.echo(click.style(f"Failed to start server: {e}", fg="red"), err=True)
        sys.exit(1)


# =============================================================================
# Stop Command
# =============================================================================


@cli.command()
@click.option(
    "--timeout",
    default=5.0,
    type=float,
    help="Shutdown timeout in seconds (default: 5.0)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force immediate shutdown without waiting",
)
@click.pass_context
def stop(ctx: click.Context, timeout: float, force: bool) -> None:
    """Stop the running PSK-TLS Admin Server.

    Sends a shutdown signal to the running server and waits for
    graceful shutdown.

    Examples:

        # Stop with default timeout
        gp-ota-server stop

        # Force immediate shutdown
        gp-ota-server stop --force

        # Stop with custom timeout
        gp-ota-server stop --timeout 10
    """
    global _server_instance

    if _server_instance is None:
        click.echo(
            click.style("No server instance found to stop", fg="yellow")
        )
        # Try to find PID file or other mechanism
        click.echo("Note: Server may be running in a different process")
        return

    click.echo("Stopping server...")

    if force:
        timeout = 0.1

    try:
        _server_instance.stop(timeout=timeout)
        click.echo(click.style("Server stopped successfully", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error stopping server: {e}", fg="red"), err=True)
        sys.exit(1)

    _server_instance = None


# =============================================================================
# Status Command
# =============================================================================


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show server status.

    Displays information about the running server including:
    - Running state
    - Active connections
    - Session count
    """
    global _server_instance

    if _server_instance is None:
        click.echo(click.style("Server is not running", fg="yellow"))
        return

    if not _server_instance.is_running:
        click.echo(click.style("Server is stopped", fg="yellow"))
        return

    click.echo(click.style("Server Status:", fg="green", bold=True))
    click.echo(f"  Running: {_server_instance.is_running}")
    click.echo(f"  Host: {_server_instance.config.host}")
    click.echo(f"  Port: {_server_instance.config.port}")
    click.echo(f"  Active Connections: {_server_instance.get_connection_count()}")
    click.echo(f"  Active Sessions: {_server_instance.get_session_count()}")

    # Show sessions
    sessions = _server_instance.get_active_sessions()
    if sessions:
        click.echo("\n  Active Sessions:")
        for session in sessions:
            click.echo(
                f"    - {session.session_id[:8]}... "
                f"({session.client_address}, state={session.state.value})"
            )


# =============================================================================
# Configuration Loading
# =============================================================================


class ConfigurationError(Exception):
    """Configuration loading error."""

    pass


def load_configuration(
    config_path: Optional[Path],
    host: str,
    port: int,
    ciphers: str,
    enable_null_ciphers: bool,
    max_connections: int,
    session_timeout: float,
    keys_path: Optional[Path],
) -> tuple[ServerConfig, Optional[Path]]:
    """Load and merge configuration from file and CLI options.

    Args:
        config_path: Path to YAML configuration file.
        host: Host from CLI.
        port: Port from CLI.
        ciphers: Cipher selection from CLI.
        enable_null_ciphers: NULL cipher flag from CLI.
        max_connections: Max connections from CLI.
        session_timeout: Session timeout from CLI.
        keys_path: Keys file path from CLI.

    Returns:
        Tuple of (ServerConfig, keys_path).

    Raises:
        ConfigurationError: If configuration is invalid.
    """
    config_dict: Dict[str, Any] = {}

    # Load from file if provided
    if config_path:
        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except IOError as e:
            raise ConfigurationError(f"Failed to read config file: {e}")

    # Apply environment variable overrides
    env_host = os.environ.get("GP_OTA_SERVER_HOST")
    env_port = os.environ.get("GP_OTA_SERVER_PORT")

    if env_host:
        config_dict["host"] = env_host
    if env_port:
        try:
            config_dict["port"] = int(env_port)
        except ValueError:
            raise ConfigurationError(
                f"Invalid GP_OTA_SERVER_PORT: {env_port}"
            )

    # CLI options override everything
    config_dict["host"] = host
    config_dict["port"] = port
    config_dict["max_connections"] = max_connections
    config_dict["session_timeout"] = session_timeout

    # Create cipher config
    cipher_config = CipherConfig(
        enable_legacy=(ciphers in ("legacy", "all")),
        enable_null_ciphers=enable_null_ciphers,
    )
    config_dict["cipher_config"] = cipher_config

    # Get keys path from config or CLI
    final_keys_path = keys_path
    if not final_keys_path and "keys_file" in config_dict:
        final_keys_path = Path(config_dict["keys_file"])

    # Create ServerConfig
    try:
        server_config = ServerConfig(
            host=config_dict.get("host", "127.0.0.1"),
            port=config_dict.get("port", 8443),
            max_connections=config_dict.get("max_connections", 10),
            session_timeout=config_dict.get("session_timeout", 300.0),
            cipher_config=config_dict.get("cipher_config"),
            backlog=config_dict.get("backlog", 5),
            handshake_timeout=config_dict.get("handshake_timeout", 30.0),
        )
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}")

    # Validate
    try:
        server_config.validate()
    except ValueError as e:
        raise ConfigurationError(str(e))

    return server_config, final_keys_path


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
