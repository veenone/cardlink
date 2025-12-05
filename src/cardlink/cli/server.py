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

from cardlink.server import (
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

# Default PID file location (cross-platform)
def _get_default_pid_file() -> Path:
    """Get default PID file location based on platform."""
    if sys.platform == "win32":
        # Windows: use TEMP directory
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        return temp_dir / "gp-ota-server.pid"
    else:
        # Unix-like: use /tmp
        return Path("/tmp/gp-ota-server.pid")


def _get_pid_file() -> Path:
    """Get the PID file path from environment or default."""
    env_path = os.environ.get("GP_OTA_SERVER_PID_FILE")
    if env_path:
        return Path(env_path)
    return _get_default_pid_file()


def _write_pid_file(pid: int) -> None:
    """Write PID to file."""
    pid_file = _get_pid_file()
    try:
        pid_file.write_text(str(pid))
        logger.debug(f"Wrote PID {pid} to {pid_file}")
    except IOError as e:
        logger.warning(f"Failed to write PID file: {e}")


def _read_pid_file() -> Optional[int]:
    """Read PID from file."""
    pid_file = _get_pid_file()
    try:
        if pid_file.exists():
            pid_str = pid_file.read_text().strip()
            return int(pid_str)
    except (IOError, ValueError) as e:
        logger.debug(f"Failed to read PID file: {e}")
    return None


def _remove_pid_file() -> None:
    """Remove PID file."""
    pid_file = _get_pid_file()
    try:
        if pid_file.exists():
            pid_file.unlink()
            logger.debug(f"Removed PID file {pid_file}")
    except IOError as e:
        logger.warning(f"Failed to remove PID file: {e}")


def _is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


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

    Available Commands:
        start     - Start the PSK-TLS server
        stop      - Stop the running server
        status    - Show server status and statistics
        validate  - Validate configuration files before starting

    Use 'gp-server COMMAND --help' for detailed help on each command.

    Configuration:
        Config files: examples/configs/server_config.yaml
        Keys files:   examples/configs/psk_keys.yaml

    Environment Variables:
        GP_OTA_SERVER_HOST     - Override default host
        GP_OTA_SERVER_PORT     - Override default port
        GP_OTA_SERVER_CONFIG   - Default config file path
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
    help="Path to YAML configuration file (see examples/configs/server_config.yaml for format)",
)
@click.option(
    "--keys", "-k",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PSK keys YAML file containing identity:key pairs (see examples/configs/psk_keys.yaml)",
)
@click.option(
    "--ciphers",
    default="production",
    type=click.Choice(["production", "legacy", "all"]),
    help="Cipher suite selection: 'production' (AES-CBC-SHA256/384), 'legacy' (AES-CBC-SHA), 'all' (both)",
)
@click.option(
    "--enable-null-ciphers",
    is_flag=True,
    help="Enable NULL cipher suites with NO ENCRYPTION - for debugging only in isolated environments!",
)
@click.option(
    "--max-connections",
    default=10,
    type=int,
    help="Maximum concurrent client connections to accept (default: 10, each uses one thread)",
)
@click.option(
    "--session-timeout",
    default=300.0,
    type=float,
    help="Session inactivity timeout in seconds - inactive sessions are automatically closed (default: 300)",
)
@click.option(
    "--handshake-timeout",
    default=30.0,
    type=float,
    help="TLS handshake timeout in seconds - handshake must complete within this time (default: 30)",
)
@click.option(
    "--dashboard",
    is_flag=True,
    help="Enable web dashboard for server monitoring (requires dashboard module installation)",
)
@click.option(
    "--foreground", "-f",
    is_flag=True,
    help="Run server in foreground with console output instead of backgrounding (useful for debugging)",
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
    handshake_timeout: float,
    dashboard: bool,
    foreground: bool,
) -> None:
    """Start the PSK-TLS Admin Server.

    The server will listen for incoming TLS-PSK connections and process
    GlobalPlatform APDU commands.

    Configuration Priority (highest to lowest):
        1. CLI options (e.g., --port, --host)
        2. Environment variables (GP_OTA_SERVER_HOST, GP_OTA_SERVER_PORT)
        3. Configuration file (--config)
        4. Built-in defaults

    Configuration File Format:
        See examples/configs/server_config.yaml for a complete example.
        The config file supports all server options including cipher suites,
        timeouts, connection limits, and key store paths.

    PSK Keys File Format:
        See examples/configs/psk_keys.yaml for key store format.
        Contains identity:key pairs in YAML format.

    Examples:

        # Start with defaults (localhost:8443)
        gp-server start

        # Start on custom port
        gp-server start --port 9443

        # Start with configuration file
        gp-server start --config examples/configs/server_config.yaml

        # Start with separate keys file
        gp-server start --config server.yaml --keys psk_keys.yaml

        # Start with verbose logging
        gp-server -v start --port 8443

        # Start with NULL ciphers for debugging (NO ENCRYPTION!)
        gp-server start --enable-null-ciphers --foreground

        # Validate config before starting
        gp-server validate --config server.yaml --keys psk_keys.yaml
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
            handshake_timeout=handshake_timeout,
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
            "+==============================================================+\n"
            "|  WARNING: NULL CIPHERS ENABLED - NO ENCRYPTION!              |\n"
            "|  Traffic will be transmitted in PLAINTEXT.                   |\n"
            "|  Use only for testing in isolated environments.              |\n"
            "+==============================================================+\n",
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
        _remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check if server is already running
    existing_pid = _read_pid_file()
    if existing_pid and _is_process_running(existing_pid):
        click.echo(
            click.style(
                f"Server is already running (PID: {existing_pid}). "
                "Use 'gp-server stop' to stop it first.",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    # Start server
    try:
        click.echo(f"Starting PSK-TLS Admin Server on {host}:{port}...")
        server.start()

        # Write PID file
        _write_pid_file(os.getpid())

        click.echo(click.style(
            f"Server started successfully on {host}:{port}",
            fg="green",
        ))
        click.echo(f"PID: {os.getpid()}")
        click.echo(f"PID file: {_get_pid_file()}")

        if foreground:
            click.echo("Press Ctrl+C to stop the server")

            # Keep running until interrupted
            try:
                while server.is_running:
                    time.sleep(1)
            finally:
                _remove_pid_file()
        else:
            click.echo(
                f"Server running in background. Use 'gp-server stop' to stop."
            )

            # Keep running in background
            try:
                while server.is_running:
                    time.sleep(1)
            finally:
                _remove_pid_file()

    except Exception as e:
        _remove_pid_file()
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
    help="Force immediate shutdown (SIGKILL instead of SIGTERM)",
)
@click.pass_context
def stop(ctx: click.Context, timeout: float, force: bool) -> None:
    """Stop the running PSK-TLS Admin Server.

    Sends a shutdown signal to the running server and waits for
    graceful shutdown.

    Examples:

        # Stop with default timeout
        gp-server stop

        # Force immediate shutdown
        gp-server stop --force

        # Stop with custom timeout
        gp-server stop --timeout 10
    """
    global _server_instance

    # First, try to use the in-process server instance
    if _server_instance is not None:
        click.echo("Stopping server (in-process)...")
        try:
            _server_instance.stop(timeout=timeout)
            _remove_pid_file()
            click.echo(click.style("Server stopped successfully", fg="green"))
        except Exception as e:
            click.echo(click.style(f"Error stopping server: {e}", fg="red"), err=True)
            sys.exit(1)
        _server_instance = None
        return

    # Otherwise, try to find and signal the server via PID file
    pid = _read_pid_file()
    if pid is None:
        click.echo(click.style("No server found (no PID file)", fg="yellow"))
        click.echo(f"PID file location: {_get_pid_file()}")
        return

    if not _is_process_running(pid):
        click.echo(
            click.style(
                f"Server not running (stale PID file, PID: {pid})",
                fg="yellow",
            )
        )
        _remove_pid_file()
        return

    click.echo(f"Stopping server (PID: {pid})...")

    # Send appropriate signal
    try:
        if force:
            click.echo("Sending SIGKILL...")
            os.kill(pid, signal.SIGKILL)
        else:
            click.echo("Sending SIGTERM...")
            os.kill(pid, signal.SIGTERM)

        # Wait for process to terminate
        waited = 0.0
        interval = 0.1
        while waited < timeout and _is_process_running(pid):
            time.sleep(interval)
            waited += interval

        if _is_process_running(pid):
            if not force:
                click.echo(
                    click.style(
                        f"Server did not stop within {timeout}s. "
                        "Use --force to send SIGKILL.",
                        fg="yellow",
                    )
                )
                sys.exit(1)
            else:
                click.echo(
                    click.style(
                        f"Server did not stop after SIGKILL (PID: {pid})",
                        fg="red",
                    ),
                    err=True,
                )
                sys.exit(1)

        _remove_pid_file()
        click.echo(click.style("Server stopped successfully", fg="green"))

    except ProcessLookupError:
        click.echo(click.style("Server already stopped", fg="yellow"))
        _remove_pid_file()
    except PermissionError:
        click.echo(
            click.style(
                f"Permission denied to stop server (PID: {pid}). Try with sudo.",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error stopping server: {e}", fg="red"), err=True)
        sys.exit(1)


# =============================================================================
# Status Command
# =============================================================================


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show server status.

    Displays information about the running server including:
    - Running state
    - PID
    - Active connections (if in-process)
    - Session count (if in-process)
    """
    global _server_instance

    # First check in-process server
    if _server_instance is not None and _server_instance.is_running:
        click.echo(click.style("Server Status:", fg="green", bold=True))
        click.echo(f"  Running: True (in-process)")
        click.echo(f"  PID: {os.getpid()}")
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
        return

    # Check via PID file
    pid = _read_pid_file()
    if pid is None:
        click.echo(click.style("Server is not running", fg="yellow"))
        click.echo(f"PID file: {_get_pid_file()} (not found)")
        return

    if not _is_process_running(pid):
        click.echo(click.style("Server is not running (stale PID file)", fg="yellow"))
        click.echo(f"PID file: {_get_pid_file()} (PID: {pid}, not running)")
        _remove_pid_file()
        return

    click.echo(click.style("Server Status:", fg="green", bold=True))
    click.echo(f"  Running: True")
    click.echo(f"  PID: {pid}")
    click.echo(f"  PID file: {_get_pid_file()}")
    click.echo("")
    click.echo("  Note: Detailed stats available only from the same process.")
    click.echo("  Use 'gp-server stop' to stop the server.")


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
    handshake_timeout: float,
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
        handshake_timeout: TLS handshake timeout from CLI.
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
    config_dict["handshake_timeout"] = handshake_timeout

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
# Validate Command
# =============================================================================


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to YAML configuration file to validate",
)
@click.option(
    "--keys", "-k",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to PSK keys YAML file to validate",
)
@click.pass_context
def validate(ctx: click.Context, config: Path, keys: Optional[Path]) -> None:
    """Validate configuration file without starting server.

    Checks configuration file syntax and validates all settings.

    Examples:

        # Validate config file
        gp-server validate --config server.yaml

        # Validate config and keys
        gp-server validate --config server.yaml --keys keys.yaml
    """
    click.echo(f"Validating configuration: {config}")

    try:
        server_config, key_store_path = load_configuration(
            config_path=config,
            host="127.0.0.1",  # Default, will be overridden by config
            port=8443,
            ciphers="production",
            enable_null_ciphers=False,
            max_connections=10,
            session_timeout=300.0,
            handshake_timeout=30.0,
            keys_path=keys,
        )
        click.echo(click.style("Configuration valid!", fg="green"))
        click.echo(f"  Host: {server_config.host}")
        click.echo(f"  Port: {server_config.port}")
        click.echo(f"  Max connections: {server_config.max_connections}")
        click.echo(f"  Session timeout: {server_config.session_timeout}s")
        click.echo(f"  Handshake timeout: {server_config.handshake_timeout}s")

        if key_store_path:
            click.echo(f"\nValidating key store: {key_store_path}")
            try:
                key_store = FileKeyStore(str(key_store_path))
                identities = key_store.get_all_identities()
                click.echo(click.style("Key store valid!", fg="green"))
                click.echo(f"  Loaded {len(identities)} PSK identities")
            except Exception as e:
                click.echo(click.style(f"Key store error: {e}", fg="red"), err=True)
                sys.exit(1)

    except ConfigurationError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"), err=True)
        sys.exit(1)


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
