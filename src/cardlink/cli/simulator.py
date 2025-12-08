"""CLI for Mobile Simulator.

This module provides command-line interface for controlling the
mobile simulator for testing PSK-TLS server connectivity.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

console = Console()

# Configure logging
def setup_logging(verbose: bool = False) -> None:
    """Set up logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Mobile Simulator for GP OTA Tester.

    Simulates a mobile phone with UICC connecting to the PSK-TLS Admin Server.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.command()
@click.option(
    "-s", "--server",
    default="127.0.0.1:8443",
    help="Server address (host:port)",
)
@click.option(
    "--psk-identity",
    default="test_card",
    help="PSK identity for TLS authentication",
)
@click.option(
    "--psk-key",
    default="00000000000000000000000000000000",
    help="PSK key in hex (16 or 32 bytes)",
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML configuration file",
)
@click.option(
    "--mode",
    type=click.Choice(["normal", "error", "timeout"]),
    default="normal",
    help="Simulation behavior mode",
)
@click.option(
    "--error-rate",
    type=float,
    default=0.0,
    help="Error injection rate (0.0 to 1.0)",
)
@click.option(
    "--timeout-probability",
    type=float,
    default=0.0,
    help="Timeout simulation probability (0.0 to 1.0)",
)
@click.option(
    "--enable-null-ciphers",
    is_flag=True,
    help="Enable NULL cipher suites with NO ENCRYPTION - for debugging only in isolated environments!",
)
@click.option(
    "-n", "--count",
    type=int,
    default=1,
    help="Number of sessions to run",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Run sessions in parallel (with --count)",
)
@click.option(
    "--loop",
    is_flag=True,
    help="Run continuously in loop mode",
)
@click.option(
    "--interval",
    type=float,
    default=5.0,
    help="Interval between sessions in loop mode (seconds)",
)
@click.option(
    "--persistent",
    is_flag=True,
    help="Keep session open and poll for new commands from server",
)
@click.option(
    "--poll-interval",
    type=int,
    default=1000,
    help="Poll interval in persistent mode (milliseconds)",
)
@click.option(
    "--session-timeout",
    type=float,
    default=0.0,
    help="Session timeout in persistent mode (seconds, 0=no timeout)",
)
@click.pass_context
def run(
    ctx: click.Context,
    server: str,
    psk_identity: str,
    psk_key: str,
    config: Optional[Path],
    mode: str,
    error_rate: float,
    timeout_probability: float,
    enable_null_ciphers: bool,
    count: int,
    parallel: bool,
    loop: bool,
    interval: float,
    persistent: bool,
    poll_interval: int,
    session_timeout: float,
) -> None:
    """Run mobile simulator session(s).

    Connects to the PSK-TLS server and runs APDU exchange sessions.
    """
    try:
        from cardlink.simulator import (
            BehaviorConfig,
            BehaviorMode,
            ConnectionMode,
            MobileSimulator,
            SimulatorConfig,
        )
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        console.print("Install with: pip install gp-ota-tester[simulator]")
        sys.exit(1)

    # Build configuration
    if config:
        with open(config) as f:
            config_data = yaml.safe_load(f)
        sim_config = SimulatorConfig.from_dict(config_data)
    else:
        # Parse server address
        if ":" in server:
            host, port_str = server.rsplit(":", 1)
            port = int(port_str)
        else:
            host = server
            port = 8443

        # Parse PSK key
        try:
            psk_key_bytes = bytes.fromhex(psk_key)
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid PSK key hex: {psk_key}")
            sys.exit(1)

        # Build behavior config
        behavior = BehaviorConfig(
            mode=BehaviorMode(mode),
            error_rate=error_rate,
            timeout_probability=timeout_probability,
            connection_mode=ConnectionMode.PERSISTENT if persistent else ConnectionMode.SINGLE,
            poll_interval_ms=poll_interval,
            session_timeout_seconds=session_timeout,
        )

        sim_config = SimulatorConfig(
            server_host=host,
            server_port=port,
            psk_identity=psk_identity,
            psk_key=psk_key_bytes,
            enable_null_ciphers=enable_null_ciphers,
            behavior=behavior,
        )

    # Validate config
    try:
        sim_config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold]Mobile Simulator[/bold]")
    console.print(f"Server: {sim_config.server_address}")
    console.print(f"PSK Identity: {sim_config.psk_identity}")
    console.print(f"Mode: {sim_config.behavior.mode.value}")
    if sim_config.behavior.connection_mode == ConnectionMode.PERSISTENT:
        console.print(f"[cyan]Persistent mode:[/cyan] poll every {sim_config.behavior.poll_interval_ms}ms")
        if sim_config.behavior.session_timeout_seconds > 0:
            console.print(f"  Session timeout: {sim_config.behavior.session_timeout_seconds}s")
        else:
            console.print(f"  Session timeout: none (Ctrl+C to stop)")

    # Warn about NULL ciphers
    if sim_config.enable_null_ciphers:
        console.print()
        console.print("[red bold]WARNING: NULL ciphers enabled - traffic will be UNENCRYPTED![/red bold]")
        console.print("[red]Only use in isolated test environments![/red]")

    console.print()

    # Run sessions
    async def run_sessions():
        simulator = MobileSimulator(sim_config)
        session_count = 0
        success_count = 0

        try:
            while True:
                if parallel and count > 1:
                    # Run multiple sessions in parallel
                    tasks = []
                    for i in range(count):
                        sim = MobileSimulator(sim_config)
                        tasks.append(sim.run_complete_session())

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        session_count += 1
                        if isinstance(result, Exception):
                            console.print(f"[red]Session {i+1} failed:[/red] {result}")
                        elif result.success:
                            success_count += 1
                            console.print(
                                f"[green]Session {i+1}:[/green] "
                                f"{result.apdu_count} APDUs, "
                                f"{result.duration_seconds:.2f}s, "
                                f"SW={result.final_sw}"
                            )
                        else:
                            console.print(
                                f"[yellow]Session {i+1}:[/yellow] "
                                f"Failed - {result.error}"
                            )
                else:
                    # Run sessions sequentially
                    for i in range(count):
                        session_count += 1
                        console.print(f"[bold]Session {session_count}[/bold]")

                        result = await simulator.run_complete_session()

                        if result.success:
                            success_count += 1
                            console.print(
                                f"  [green]Success:[/green] "
                                f"{result.apdu_count} APDUs, "
                                f"{result.duration_seconds:.2f}s, "
                                f"SW={result.final_sw}"
                            )
                        else:
                            console.print(
                                f"  [red]Failed:[/red] {result.error}"
                            )

                        # Show APDU exchanges if verbose
                        if ctx.obj.get("verbose") and result.exchanges:
                            for ex in result.exchanges:
                                console.print(
                                    f"    {ex.description}: "
                                    f"[dim]{ex.command[:20]}...[/dim] -> "
                                    f"SW={ex.sw}"
                                )

                if not loop:
                    break

                console.print(f"\n[dim]Waiting {interval}s before next session...[/dim]")
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")

        # Print summary
        console.print()
        console.print("[bold]Summary[/bold]")
        console.print(f"  Sessions: {session_count}")
        console.print(f"  Successful: {success_count}")
        console.print(f"  Failed: {session_count - success_count}")

        stats = simulator.get_statistics()
        console.print(f"  Total APDUs sent: {stats.total_apdus_sent}")
        console.print(f"  Total APDUs received: {stats.total_apdus_received}")
        if stats.avg_apdu_response_time_ms > 0:
            console.print(f"  Avg APDU time: {stats.avg_apdu_response_time_ms:.1f}ms")

    asyncio.run(run_sessions())


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("simulator.yaml"),
    help="Output file path",
)
def config_generate(output: Path) -> None:
    """Generate sample configuration file."""
    sample_config = """\
# Mobile Simulator Configuration
# ================================

# Server connection settings
server:
  host: "127.0.0.1"
  port: 8443
  connect_timeout: 30.0
  read_timeout: 30.0
  retry_count: 3
  retry_backoff:
    - 1.0
    - 2.0
    - 4.0

# PSK-TLS credentials
psk:
  identity: "test_card_001"
  key: "0102030405060708090A0B0C0D0E0F10"

# Virtual UICC configuration
uicc:
  iccid: "8901234567890123456"
  imsi: "310150123456789"
  msisdn: "+14155551234"

  # GlobalPlatform settings
  gp:
    version: "2.2.1"
    scp_version: "03"
    isd_aid: "A000000151000000"

  # Pre-installed applets
  applets:
    - aid: "A0000001510001"
      name: "TestApplet"
      state: "SELECTABLE"
      privileges: "00"

# Simulation behavior
behavior:
  mode: "normal"  # normal, error, timeout
  response_delay_ms: 20

  # Error injection settings (when mode=error)
  error:
    rate: 0.0
    codes:
      - "6A82"
      - "6985"
      - "6D00"

  # Timeout simulation settings (when mode=timeout)
  timeout:
    probability: 0.0
    delay_range:
      min: 1000
      max: 5000

  # Connection behavior
  connection:
    mode: "single"  # single, per_command, batch, reconnect, persistent
    batch_size: 5
    reconnect_after: 3
    poll_interval_ms: 1000  # Poll interval for persistent mode
    session_timeout_seconds: 0  # Session timeout (0 = no timeout)
"""

    with open(output, "w") as f:
        f.write(sample_config)

    console.print(f"[green]Generated configuration file:[/green] {output}")


@cli.command()
@click.option(
    "-s", "--server",
    default="127.0.0.1:8443",
    help="Server address to test (host:port)",
)
@click.option(
    "--psk-identity",
    default="test_card",
    help="PSK identity for TLS authentication",
)
@click.option(
    "--psk-key",
    default="00000000000000000000000000000000",
    help="PSK key in hex (16 or 32 bytes)",
)
def test_connection(server: str, psk_identity: str, psk_key: str) -> None:
    """Test connection to PSK-TLS server.

    Attempts to establish a TLS-PSK connection without running a full session.
    """
    try:
        from cardlink.simulator import PSKTLSClient
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        console.print("Install with: pip install gp-ota-tester[simulator]")
        sys.exit(1)

    # Parse server address
    if ":" in server:
        host, port_str = server.rsplit(":", 1)
        port = int(port_str)
    else:
        host = server
        port = 8443

    # Parse PSK key
    try:
        psk_key_bytes = bytes.fromhex(psk_key)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid PSK key hex: {psk_key}")
        sys.exit(1)

    console.print(f"Testing connection to {host}:{port}...")
    console.print(f"PSK Identity: {psk_identity}")

    async def test():
        client = PSKTLSClient(
            host=host,
            port=port,
            psk_identity=psk_identity,
            psk_key=psk_key_bytes,
            timeout=10.0,
        )

        try:
            info = await client.connect()
            console.print()
            console.print("[green]Connection successful![/green]")
            console.print(f"  Cipher: {info.cipher_suite}")
            console.print(f"  Protocol: {info.protocol_version}")
            console.print(f"  Handshake: {info.handshake_duration_ms:.1f}ms")
            await client.close()

        except Exception as e:
            console.print()
            console.print(f"[red]Connection failed:[/red] {e}")
            sys.exit(1)

    asyncio.run(test())


@cli.command()
def status() -> None:
    """Show simulator status and statistics."""
    console.print("[bold]Mobile Simulator Status[/bold]")
    console.print()
    console.print("  Status: [green]Ready[/green]")
    console.print()
    console.print("Use 'gp-simulator run' to start a simulation session.")
    console.print("Use 'gp-simulator test-connection' to test server connectivity.")


@cli.command()
@click.option(
    "-d", "--dashboard",
    default="http://127.0.0.1:8080",
    help="Dashboard URL (e.g., http://localhost:8080)",
)
@click.option(
    "--session-id",
    help="Session ID to close (if not specified, lists available sessions)",
)
@click.option(
    "--all",
    "close_all",
    is_flag=True,
    help="Close all sessions",
)
def close_session(dashboard: str, session_id: Optional[str], close_all: bool) -> None:
    """Close a session in the dashboard.

    If no session ID is specified, lists all available sessions.
    Use --all to close all sessions.
    """
    import urllib.request
    import urllib.error

    api_base = dashboard.rstrip("/") + "/api"

    def api_request(method: str, path: str) -> dict:
        """Make API request."""
        url = f"{api_base}{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                import json
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"error": "not_found"}
            raise

    try:
        # Get list of sessions
        sessions = api_request("GET", "/sessions")

        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return

        if not session_id and not close_all:
            # List sessions
            console.print("[bold]Available Sessions[/bold]")
            console.print()
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim")
            table.add_column("Name/Identity")
            table.add_column("Status")
            table.add_column("APDUs")

            for s in sessions:
                psk_id = s.get("metadata", {}).get("psk_identity", s.get("name", ""))
                display_name = psk_id[:20] + "..." if len(psk_id) > 20 else psk_id
                table.add_row(
                    s["id"][:12] + "...",
                    display_name,
                    s.get("status", "unknown"),
                    str(s.get("apduCount", 0)),
                )
            console.print(table)
            console.print()
            console.print("Use --session-id <ID> to close a specific session.")
            console.print("Use --all to close all sessions.")
            return

        if close_all:
            # Close all sessions
            count = 0
            for s in sessions:
                try:
                    api_request("DELETE", f"/sessions/{s['id']}")
                    count += 1
                    console.print(f"[green]Closed:[/green] {s['id'][:12]}...")
                except Exception as e:
                    console.print(f"[red]Failed:[/red] {s['id'][:12]}... - {e}")
            console.print(f"\n[bold]Closed {count} session(s)[/bold]")
        else:
            # Close specific session
            # Find session by partial ID match
            matching = [s for s in sessions if s["id"].startswith(session_id)]
            if not matching:
                console.print(f"[red]Error:[/red] Session not found: {session_id}")
                sys.exit(1)
            if len(matching) > 1:
                console.print(f"[red]Error:[/red] Multiple sessions match: {session_id}")
                for s in matching:
                    console.print(f"  - {s['id']}")
                sys.exit(1)

            s = matching[0]
            api_request("DELETE", f"/sessions/{s['id']}")
            console.print(f"[green]Session closed:[/green] {s['id']}")

    except urllib.error.URLError as e:
        console.print(f"[red]Error:[/red] Cannot connect to dashboard at {dashboard}")
        console.print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
