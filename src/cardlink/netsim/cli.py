"""CLI for Network Simulator Integration.

This module provides command-line interface for controlling and
monitoring network simulators like Amarisoft Callbox.
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


def setup_logging(verbose: bool = False) -> None:
    """Set up logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# Store the connected manager instance
_manager_instance = None


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option(
    "--url",
    envvar="NETSIM_URL",
    help="Simulator WebSocket URL (wss://host:port)",
)
@click.option(
    "--type",
    "simulator_type",
    type=click.Choice(["amarisoft", "generic"]),
    default="amarisoft",
    help="Simulator type",
)
@click.option(
    "--api-key",
    envvar="NETSIM_API_KEY",
    help="API key for authentication",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    url: Optional[str],
    simulator_type: str,
    api_key: Optional[str],
) -> None:
    """Network Simulator CLI for GP OTA Tester.

    Control and monitor network simulators like Amarisoft Callbox.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["url"] = url
    ctx.obj["simulator_type"] = simulator_type
    ctx.obj["api_key"] = api_key
    setup_logging(verbose)


# =============================================================================
# Connection Commands
# =============================================================================


@cli.command()
@click.option(
    "--url",
    required=True,
    help="Simulator WebSocket URL (wss://host:port)",
)
@click.option(
    "--type",
    "simulator_type",
    type=click.Choice(["amarisoft", "generic"]),
    default="amarisoft",
    help="Simulator type",
)
@click.option(
    "--api-key",
    help="API key for authentication",
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML configuration file",
)
@click.pass_context
def connect(
    ctx: click.Context,
    url: str,
    simulator_type: str,
    api_key: Optional[str],
    config: Optional[Path],
) -> None:
    """Connect to a network simulator.

    Establishes connection and authenticates if API key provided.
    """
    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    # Load config from file if provided
    if config:
        with open(config) as f:
            config_data = yaml.safe_load(f)
        url = config_data.get("url", url)
        api_key = config_data.get("api_key", api_key)
        simulator_type = config_data.get("type", simulator_type)

    console.print(f"[bold]Connecting to Network Simulator[/bold]")
    console.print(f"URL: {url}")
    console.print(f"Type: {simulator_type}")
    console.print()

    # Build config
    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def do_connect():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            console.print("[green]Connected successfully![/green]")

            # Get status
            status = await manager.get_status()
            console.print(f"  Simulator: [cyan]{status.simulator_type.value}[/cyan]")
            console.print(f"  Connected: [green]{status.connected}[/green]")

            if status.authenticated:
                console.print(f"  Authenticated: [green]Yes[/green]")
            else:
                console.print(f"  Authenticated: [yellow]No[/yellow]")

        except Exception as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(do_connect())


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show simulator connection status."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[yellow]No simulator URL configured[/yellow]")
        console.print("Use --url option or set NETSIM_URL environment variable")
        return

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def get_status():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            status = await manager.get_status()

            console.print("[bold]Simulator Status[/bold]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("URL", url)
            table.add_row("Type", status.simulator_type.value)
            table.add_row("Connected", "[green]Yes[/green]" if status.connected else "[red]No[/red]")
            table.add_row("Authenticated", "[green]Yes[/green]" if status.authenticated else "[yellow]No[/yellow]")

            if hasattr(status, "cell_status"):
                table.add_row("Cell Status", status.cell_status.value if status.cell_status else "Unknown")

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(get_status())


# =============================================================================
# UE Commands
# =============================================================================


@cli.group()
def ue() -> None:
    """UE (User Equipment) management commands."""
    pass


@ue.command("list")
@click.pass_context
def ue_list(ctx: click.Context) -> None:
    """List connected UEs."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def list_ues():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            ues = await manager.ue.list_ues()

            if not ues:
                console.print("[yellow]No UEs connected[/yellow]")
                return

            table = Table(title="Connected UEs")
            table.add_column("IMSI", style="cyan")
            table.add_column("Status")
            table.add_column("Cell ID")
            table.add_column("IP Address")

            for ue in ues:
                status_color = "green" if ue.status.value == "registered" else "yellow"
                table.add_row(
                    ue.imsi,
                    f"[{status_color}]{ue.status.value}[/{status_color}]",
                    str(ue.cell_id) if ue.cell_id else "-",
                    ue.ip_address or "-",
                )

            console.print(table)
            console.print(f"\nTotal: {len(ues)} UE(s)")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(list_ues())


@ue.command("show")
@click.argument("imsi")
@click.pass_context
def ue_show(ctx: click.Context, imsi: str) -> None:
    """Show details for a specific UE by IMSI."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def show_ue():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            ue = await manager.ue.get_ue(imsi)

            if not ue:
                console.print(f"[yellow]UE not found:[/yellow] {imsi}")
                return

            console.print(f"[bold]UE Details: {imsi}[/bold]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("IMSI", ue.imsi)
            status_color = "green" if ue.status.value == "registered" else "yellow"
            table.add_row("Status", f"[{status_color}]{ue.status.value}[/{status_color}]")
            table.add_row("Cell ID", str(ue.cell_id) if ue.cell_id else "-")
            table.add_row("IP Address", ue.ip_address or "-")
            if hasattr(ue, "registered_at") and ue.registered_at:
                table.add_row("Registered At", ue.registered_at.isoformat())

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(show_ue())


@ue.command("wait")
@click.argument("imsi")
@click.option("-t", "--timeout", default=30.0, help="Timeout in seconds")
@click.pass_context
def ue_wait(ctx: click.Context, imsi: str, timeout: float) -> None:
    """Wait for a UE to register."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print(f"Waiting for UE registration: {imsi} (timeout: {timeout}s)...")

    async def wait_for_ue():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            ue = await manager.ue.wait_for_registration(imsi, timeout=timeout)

            if ue:
                console.print(f"[green]UE registered![/green]")
                console.print(f"  IMSI: {ue.imsi}")
                console.print(f"  Status: {ue.status.value}")
                console.print(f"  IP: {ue.ip_address or 'N/A'}")
            else:
                console.print(f"[red]Timeout:[/red] UE did not register within {timeout}s")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(wait_for_ue())


@ue.command("detach")
@click.argument("imsi")
@click.option("--cause", default="reattach_required", help="Detach cause")
@click.pass_context
def ue_detach(ctx: click.Context, imsi: str, cause: str) -> None:
    """Detach a UE from the network."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def detach_ue():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            success = await manager.ue.detach_ue(imsi)

            if success:
                console.print(f"[green]UE detached successfully[/green]")
            else:
                console.print(f"[red]Failed to detach UE[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(detach_ue())


# =============================================================================
# Session Commands
# =============================================================================


@cli.group()
def session() -> None:
    """Data session management commands."""
    pass


@session.command("list")
@click.option("--imsi", help="Filter by IMSI")
@click.pass_context
def session_list(ctx: click.Context, imsi: Optional[str]) -> None:
    """List active data sessions."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def list_sessions():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            sessions = await manager.sessions.list_sessions(imsi=imsi)

            if not sessions:
                console.print("[yellow]No active sessions[/yellow]")
                return

            table = Table(title="Active Data Sessions")
            table.add_column("Session ID", style="cyan")
            table.add_column("IMSI")
            table.add_column("APN")
            table.add_column("IP Address")
            table.add_column("QoS")

            for sess in sessions:
                table.add_row(
                    sess.session_id,
                    sess.imsi,
                    sess.apn or "-",
                    sess.ip_address or "-",
                    f"QCI {sess.qci}" if hasattr(sess, "qci") and sess.qci else "-",
                )

            console.print(table)
            console.print(f"\nTotal: {len(sessions)} session(s)")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(list_sessions())


@session.command("show")
@click.argument("session_id")
@click.pass_context
def session_show(ctx: click.Context, session_id: str) -> None:
    """Show details for a specific session."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def show_session():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            sess = await manager.sessions.get_session(session_id)

            if not sess:
                console.print(f"[yellow]Session not found:[/yellow] {session_id}")
                return

            console.print(f"[bold]Session Details: {session_id}[/bold]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("Session ID", sess.session_id)
            table.add_row("IMSI", sess.imsi)
            table.add_row("APN", sess.apn or "-")
            table.add_row("IP Address", sess.ip_address or "-")
            if hasattr(sess, "qci"):
                table.add_row("QCI", str(sess.qci) if sess.qci else "-")
            if hasattr(sess, "established_at") and sess.established_at:
                table.add_row("Established At", sess.established_at.isoformat())

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(show_session())


@session.command("release")
@click.argument("session_id")
@click.pass_context
def session_release(ctx: click.Context, session_id: str) -> None:
    """Release a data session."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def release_session():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            success = await manager.sessions.release_session(session_id)

            if success:
                console.print(f"[green]Session released successfully[/green]")
            else:
                console.print(f"[red]Failed to release session[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(release_session())


# =============================================================================
# SMS Commands
# =============================================================================


@cli.group()
def sms() -> None:
    """SMS injection and management commands."""
    pass


@sms.command("send")
@click.argument("imsi")
@click.argument("pdu")
@click.pass_context
def sms_send(ctx: click.Context, imsi: str, pdu: str) -> None:
    """Send SMS-PP PDU to a UE.

    PDU should be hex-encoded SMS data.
    """
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    # Validate PDU hex
    try:
        pdu_bytes = bytes.fromhex(pdu)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid hex PDU: {pdu}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print(f"Sending SMS to {imsi}...")
    console.print(f"PDU ({len(pdu_bytes)} bytes): {pdu[:40]}{'...' if len(pdu) > 40 else ''}")

    async def send_sms():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            message_id = await manager.sms.send_mt_sms(imsi, pdu_bytes)

            console.print(f"[green]SMS sent successfully![/green]")
            console.print(f"  Message ID: {message_id}")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(send_sms())


@sms.command("trigger")
@click.argument("imsi")
@click.option("--tar", default="000001", help="TAR value in hex (3 bytes)")
@click.pass_context
def sms_trigger(ctx: click.Context, imsi: str, tar: str) -> None:
    """Send OTA trigger SMS to a UE.

    Sends a formatted OTA trigger to initiate admin session.
    """
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    # Validate TAR hex
    try:
        tar_bytes = bytes.fromhex(tar)
        if len(tar_bytes) != 3:
            raise ValueError("TAR must be exactly 3 bytes")
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid TAR: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print(f"Sending OTA trigger to {imsi}...")
    console.print(f"TAR: {tar}")

    async def send_trigger():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            message_id = await manager.sms.send_ota_trigger(imsi, tar_bytes)

            console.print(f"[green]Trigger sent successfully![/green]")
            console.print(f"  Message ID: {message_id}")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(send_trigger())


@sms.command("history")
@click.option("--limit", default=20, help="Maximum entries to show")
@click.pass_context
def sms_history(ctx: click.Context, limit: int) -> None:
    """Show SMS history."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def show_history():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            history = manager.sms.get_message_history(limit=limit)

            if not history:
                console.print("[yellow]No SMS history[/yellow]")
                return

            table = Table(title="SMS History")
            table.add_column("ID", style="cyan")
            table.add_column("IMSI")
            table.add_column("Direction")
            table.add_column("Status")
            table.add_column("Time")

            for msg in history:
                table.add_row(
                    msg.message_id[:8],
                    msg.imsi,
                    msg.direction,
                    msg.status,
                    msg.timestamp.strftime("%H:%M:%S") if msg.timestamp else "-",
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(show_history())


# =============================================================================
# Cell Commands
# =============================================================================


@cli.group()
def cell() -> None:
    """Cell (eNB/gNB) management commands."""
    pass


@cell.command("start")
@click.pass_context
def cell_start(ctx: click.Context) -> None:
    """Start the cell."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print("Starting cell...")

    async def start_cell():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            success = await manager.cell.start()

            if success:
                console.print("[green]Cell started successfully![/green]")
                status = await manager.cell.get_status()
                console.print(f"  Status: {status.status.value}")
            else:
                console.print("[red]Failed to start cell[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(start_cell())


@cell.command("stop")
@click.pass_context
def cell_stop(ctx: click.Context) -> None:
    """Stop the cell."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print("Stopping cell...")

    async def stop_cell():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            success = await manager.cell.stop()

            if success:
                console.print("[green]Cell stopped successfully![/green]")
            else:
                console.print("[red]Failed to stop cell[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(stop_cell())


@cell.command("status")
@click.pass_context
def cell_status(ctx: click.Context) -> None:
    """Show cell status."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def get_status():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            status = await manager.cell.get_status()

            console.print("[bold]Cell Status[/bold]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            status_color = "green" if status.status.value == "active" else "yellow"
            table.add_row("Status", f"[{status_color}]{status.status.value}[/{status_color}]")
            table.add_row("Cell ID", str(status.cell_id) if status.cell_id else "-")
            if hasattr(status, "plmn"):
                table.add_row("PLMN", status.plmn or "-")
            if hasattr(status, "frequency"):
                table.add_row("Frequency", f"{status.frequency} MHz" if status.frequency else "-")
            if hasattr(status, "bandwidth"):
                table.add_row("Bandwidth", f"{status.bandwidth} MHz" if status.bandwidth else "-")

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(get_status())


@cell.command("config")
@click.option("--plmn", help="PLMN code (e.g., 001-01)")
@click.option("--frequency", type=int, help="Frequency in MHz")
@click.option("--bandwidth", type=int, help="Bandwidth in MHz")
@click.option("--power", type=int, help="Transmit power in dBm")
@click.pass_context
def cell_config(
    ctx: click.Context,
    plmn: Optional[str],
    frequency: Optional[int],
    bandwidth: Optional[int],
    power: Optional[int],
) -> None:
    """Configure cell parameters."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    # Build config params
    params = {}
    if plmn:
        params["plmn"] = plmn
    if frequency:
        params["frequency"] = frequency
    if bandwidth:
        params["bandwidth"] = bandwidth
    if power:
        params["tx_power"] = power

    if not params:
        console.print("[yellow]No configuration parameters specified[/yellow]")
        console.print("Use --plmn, --frequency, --bandwidth, or --power")
        return

    try:
        from cardlink.netsim import SimulatorConfig, SimulatorManager, SimulatorType
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    console.print("Configuring cell...")
    for key, value in params.items():
        console.print(f"  {key}: {value}")

    async def configure_cell():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()
            success = await manager.cell.configure(params)

            if success:
                console.print("[green]Cell configured successfully![/green]")
            else:
                console.print("[red]Failed to configure cell[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(configure_cell())


# =============================================================================
# Scenario Commands
# =============================================================================


@cli.command()
@click.argument("scenario_file", type=click.Path(exists=True, path_type=Path))
@click.option("--var", "-V", multiple=True, help="Variable in name=value format")
@click.pass_context
def run_scenario(ctx: click.Context, scenario_file: Path, var: tuple) -> None:
    """Run a test scenario from YAML file."""
    url = ctx.obj.get("url")
    if not url:
        console.print("[red]Error:[/red] No simulator URL configured")
        sys.exit(1)

    try:
        from cardlink.netsim import (
            Scenario,
            ScenarioRunner,
            SimulatorConfig,
            SimulatorManager,
            SimulatorType,
        )
    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        sys.exit(1)

    # Parse variables
    variables = {}
    for v in var:
        if "=" in v:
            key, value = v.split("=", 1)
            variables[key.strip()] = value.strip()
        else:
            console.print(f"[yellow]Warning:[/yellow] Invalid variable format: {v}")

    # Load scenario
    try:
        scenario = Scenario.from_file(str(scenario_file))
    except Exception as e:
        console.print(f"[red]Error loading scenario:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold]Running Scenario: {scenario.name}[/bold]")
    if scenario.description:
        console.print(f"{scenario.description}")
    console.print(f"Steps: {len(scenario.steps)}")
    console.print()

    simulator_type = ctx.obj.get("simulator_type", "amarisoft")
    api_key = ctx.obj.get("api_key")

    sim_type = SimulatorType.AMARISOFT if simulator_type == "amarisoft" else SimulatorType.GENERIC
    sim_config = SimulatorConfig(
        url=url,
        simulator_type=sim_type,
        api_key=api_key,
    )

    async def execute_scenario():
        manager = SimulatorManager(sim_config)
        try:
            await manager.connect()

            runner = ScenarioRunner(manager)
            result = await runner.run(scenario, variables=variables)

            # Display results
            console.print()
            if result.passed:
                console.print(f"[green bold]PASSED[/green bold] in {result.duration_ms:.1f}ms")
            else:
                console.print(f"[red bold]FAILED[/red bold] in {result.duration_ms:.1f}ms")

            # Step summary
            console.print()
            table = Table(title="Step Results")
            table.add_column("Step", style="cyan")
            table.add_column("Status")
            table.add_column("Duration")
            table.add_column("Error")

            for step_result in result.step_results:
                status_map = {
                    "passed": "[green]PASSED[/green]",
                    "failed": "[red]FAILED[/red]",
                    "skipped": "[yellow]SKIPPED[/yellow]",
                }
                status_text = status_map.get(step_result.status.value, step_result.status.value)

                table.add_row(
                    step_result.step_name,
                    status_text,
                    f"{step_result.duration_ms:.1f}ms",
                    step_result.error[:40] if step_result.error else "-",
                )

            console.print(table)

            console.print()
            console.print(f"Passed: {result.passed_count}")
            console.print(f"Failed: {result.failed_count}")
            console.print(f"Skipped: {result.skipped_count}")

            if not result.passed:
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        finally:
            await manager.disconnect()

    asyncio.run(execute_scenario())


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
