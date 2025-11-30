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
    count: int,
    parallel: bool,
    loop: bool,
    interval: float,
) -> None:
    """Run mobile simulator session(s).

    Connects to the PSK-TLS server and runs APDU exchange sessions.
    """
    try:
        from cardlink.simulator import (
            BehaviorConfig,
            BehaviorMode,
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
        )

        sim_config = SimulatorConfig(
            server_host=host,
            server_port=port,
            psk_identity=psk_identity,
            psk_key=psk_key_bytes,
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
    mode: "single"  # single, per_command, batch, reconnect
    batch_size: 5
    reconnect_after: 3
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


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
