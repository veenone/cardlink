"""Modem CLI commands for GP OTA Tester.

This module provides command-line interface commands for modem
control and monitoring.

Example:
    $ gp-modem list
    $ gp-modem info /dev/ttyUSB2
    $ gp-modem at /dev/ttyUSB2 ATI
    $ gp-modem monitor /dev/ttyUSB2
"""

import asyncio
import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Modem control and monitoring commands.

    Discover, configure, and monitor IoT cellular modems.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON",
)
@click.pass_context
def list(ctx: click.Context, json_output: bool) -> None:
    """List connected modems.

    Scans all serial ports for IoT modems and displays their
    basic information.
    """
    try:
        from cardlink.modem import ModemController

        async def _list():
            controller = ModemController()
            modems = await controller.discover_modems()
            return modems

        modems = run_async(_list())

        if json_output:
            data = [m.to_dict() for m in modems]
            click.echo(json.dumps(data, indent=2))
            return

        if not modems:
            console.print("[yellow]No modems found[/yellow]")
            return

        table = Table(title="Connected Modems")
        table.add_column("Port", style="cyan")
        table.add_column("Manufacturer", style="green")
        table.add_column("Model", style="green")
        table.add_column("IMEI", style="white")

        for modem in modems:
            # Mask IMEI (show only last 4 digits)
            imei = modem.imei
            if imei and len(imei) > 4:
                imei = "***" + imei[-4:]

            table.add_row(
                modem.port,
                modem.manufacturer,
                modem.model,
                imei,
            )

        console.print(table)
        console.print(f"\n[bold]Total: {len(modems)} modem(s)[/bold]")

    except ImportError:
        console.print("[red]Error: pyserial not installed.[/red]")
        console.print("Install with: pip install pyserial")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.option("--modem", "-m", is_flag=True, help="Show modem info only")
@click.option("--sim", "-s", is_flag=True, help="Show SIM info only")
@click.option("--network", "-n", is_flag=True, help="Show network info only")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def info(
    ctx: click.Context,
    port: str,
    modem: bool,
    sim: bool,
    network: bool,
    json_output: bool,
) -> None:
    """Show modem information.

    Display detailed information about modem, SIM, and network status.

    PORT: Serial port path (e.g., /dev/ttyUSB2 or COM3)
    """
    try:
        from cardlink.modem import ModemController

        async def _get_info():
            controller = ModemController()
            m = await controller.get_modem(port)
            profile = await m.get_profile()
            await controller.close_all_modems()
            return profile

        profile = run_async(_get_info())

        # Determine what to show
        show_all = not (modem or sim or network)

        if json_output:
            data = {}
            if show_all or modem:
                data["modem"] = profile.modem.to_dict()
            if show_all or sim:
                data["sim"] = profile.sim.to_dict()
            if show_all or network:
                data["network"] = profile.network.to_dict()
            click.echo(json.dumps(data, indent=2))
            return

        # Modem info
        if show_all or modem:
            table = Table(title="Modem Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Manufacturer", profile.modem.manufacturer)
            table.add_row("Model", profile.modem.model)
            table.add_row("Firmware", profile.modem.firmware_version)
            table.add_row("IMEI", profile.modem.imei)
            table.add_row("Vendor", profile.modem.vendor.value)

            console.print(table)
            console.print()

        # SIM info
        if show_all or sim:
            table = Table(title="SIM Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Status", profile.sim.status.value)
            table.add_row("ICCID", profile.sim.iccid or "N/A")
            table.add_row("IMSI", profile.sim.imsi or "N/A")
            table.add_row("MSISDN", profile.sim.msisdn or "N/A")
            if profile.sim.mcc:
                table.add_row("MCC/MNC", f"{profile.sim.mcc}/{profile.sim.mnc}")

            console.print(table)
            console.print()

        # Network info
        if show_all or network:
            table = Table(title="Network Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            reg_status = profile.network.registration_status
            if hasattr(reg_status, 'name'):
                table.add_row("Registration", reg_status.name)
            else:
                table.add_row("Registration", str(reg_status))

            table.add_row("Operator", profile.network.operator_name or "N/A")
            table.add_row("Network Type", profile.network.network_type.value)
            table.add_row("APN", profile.network.apn or "N/A")

            if profile.network.rssi:
                table.add_row("RSSI", f"{profile.network.rssi} dBm")
            if profile.network.rsrp:
                table.add_row("RSRP", f"{profile.network.rsrp} dBm")
            if profile.network.sinr:
                table.add_row("SINR", f"{profile.network.sinr} dB")
            if profile.network.rsrq:
                table.add_row("RSRQ", f"{profile.network.rsrq} dB")

            if profile.network.ip_address:
                table.add_row("IP Address", profile.network.ip_address)

            if profile.network.cell_id:
                table.add_row("Cell ID", profile.network.cell_id)
            if profile.network.tac:
                table.add_row("TAC", profile.network.tac)

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.argument("command")
@click.option("--timeout", "-t", type=float, default=5.0, help="Command timeout")
@click.pass_context
def at(ctx: click.Context, port: str, command: str, timeout: float) -> None:
    """Send AT command to modem.

    PORT: Serial port path (e.g., /dev/ttyUSB2)
    COMMAND: AT command to send (with or without AT prefix)
    """
    try:
        from cardlink.modem import ModemController

        async def _send_command():
            controller = ModemController()
            modem = await controller.get_modem(port)
            response = await modem.at.send_command(command, timeout=timeout, check_error=False)
            await controller.close_all_modems()
            return response

        response = run_async(_send_command())

        console.print(f"[cyan]Command:[/cyan] {response.command}")
        console.print(f"[cyan]Result:[/cyan] {response.result.value}")

        if response.data:
            console.print("[cyan]Response:[/cyan]")
            for line in response.data:
                console.print(f"  {line}")

        if response.error_code:
            console.print(f"[red]Error Code:[/red] {response.error_code}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.option("--duration", "-d", type=int, help="Monitor duration in seconds")
@click.pass_context
def monitor(ctx: click.Context, port: str, duration: Optional[int]) -> None:
    """Monitor BIP/URC events.

    Starts real-time monitoring of STK and BIP events on the modem.
    Press Ctrl+C to stop.

    PORT: Serial port path
    """
    try:
        from cardlink.modem import ModemController

        def on_bip_event(event):
            console.print(f"[bold green]BIP Event:[/bold green] {event.command.name}")
            if event.channel_id is not None:
                console.print(f"  Channel ID: {event.channel_id}")
            if event.destination_address:
                console.print(f"  Destination: {event.destination_address}")
            if event.buffer_size:
                console.print(f"  Buffer Size: {event.buffer_size}")
            console.print(f"  Raw PDU: {event.raw_pdu[:40]}...")

        async def _monitor():
            controller = ModemController()
            modem = await controller.get_modem(port)

            console.print(f"[bold]Monitoring BIP events on {port}[/bold]")
            console.print("Press Ctrl+C to stop\n")

            modem.on_bip_event(on_bip_event)
            await modem.start_bip_monitoring()

            try:
                if duration:
                    await asyncio.sleep(duration)
                else:
                    # Run forever until interrupted
                    while True:
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await modem.stop_bip_monitoring()
                await controller.close_all_modems()

            console.print("\n[bold]Monitoring stopped[/bold]")

        try:
            run_async(_monitor())
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.argument("pdu")
@click.pass_context
def trigger(ctx: click.Context, port: str, pdu: str) -> None:
    """Send SMS trigger PDU.

    Sends an SMS message in PDU mode (for OTA triggers).

    PORT: Serial port path
    PDU: Hex-encoded PDU string
    """
    try:
        from cardlink.modem import ModemController

        async def _send_trigger():
            controller = ModemController()
            modem = await controller.get_modem(port)

            console.print(f"[bold]Sending SMS PDU to {port}[/bold]")
            result = await modem.sms.send_raw_pdu(pdu)
            await controller.close_all_modems()
            return result

        result = run_async(_send_trigger())

        if result.success:
            console.print(f"[green]SMS sent successfully[/green]")
            console.print(f"Message Reference: {result.message_reference}")
        else:
            console.print(f"[red]SMS send failed[/red]")
            console.print(f"Error: {result.error}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.argument("host")
@click.option("--count", "-c", type=int, default=4, help="Number of pings")
@click.pass_context
def ping(ctx: click.Context, port: str, host: str, count: int) -> None:
    """Ping host via modem.

    Tests network connectivity by pinging a host through the modem.

    PORT: Serial port path
    HOST: Host to ping (IP or hostname)
    """
    try:
        from cardlink.modem import ModemController

        async def _ping():
            controller = ModemController()
            modem = await controller.get_modem(port)

            console.print(f"[bold]Pinging {host} from {port}[/bold]\n")
            result = await modem.network.ping(host, count=count)
            await controller.close_all_modems()
            return result

        result = run_async(_ping())

        if result.success:
            console.print(f"[green]Ping statistics for {host}:[/green]")
            console.print(f"  Packets: Sent = {result.sent}, Received = {result.received}, Lost = {result.lost}")
            console.print(f"  Round-trip times: min={result.min_time}ms, max={result.max_time}ms, avg={result.avg_time}ms")
        else:
            console.print(f"[red]Ping failed[/red]")
            if result.error:
                console.print(f"Error: {result.error}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.argument("apn")
@click.option("--username", "-u", default="", help="APN username")
@click.option("--password", "-p", default="", help="APN password")
@click.pass_context
def configure_apn(ctx: click.Context, port: str, apn: str, username: str, password: str) -> None:
    """Configure APN settings.

    PORT: Serial port path
    APN: Access Point Name
    """
    try:
        from cardlink.modem import ModemController

        async def _configure():
            controller = ModemController()
            modem = await controller.get_modem(port)
            success = await modem.configure_apn(apn, username=username, password=password)
            await controller.close_all_modems()
            return success

        success = run_async(_configure())

        if success:
            console.print(f"[green]APN configured successfully: {apn}[/green]")
        else:
            console.print("[red]Failed to configure APN[/red]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def ports(ctx: click.Context) -> None:
    """List all serial ports.

    Shows all available serial ports with their details.
    """
    try:
        from cardlink.modem import SerialClient

        ports = SerialClient.list_ports()

        if not ports:
            console.print("[yellow]No serial ports found[/yellow]")
            return

        table = Table(title="Serial Ports")
        table.add_column("Port", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("VID:PID", style="green")
        table.add_column("Manufacturer", style="white")

        for port in ports:
            vid_pid = ""
            if port.vid is not None and port.pid is not None:
                vid_pid = f"{port.vid:04x}:{port.pid:04x}"

            table.add_row(
                port.port,
                port.description[:30] if port.description else "",
                vid_pid,
                port.manufacturer[:20] if port.manufacturer else "",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.group()
def profile() -> None:
    """Modem profile management.

    Save, load, compare, and manage modem configuration profiles.
    """
    pass


@profile.command()
@click.argument("port")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing profile")
@click.pass_context
def save(ctx: click.Context, port: str, name: str, force: bool) -> None:
    """Save modem profile.

    Captures current modem configuration and saves it to a file.

    PORT: Serial port path
    NAME: Profile name
    """
    try:
        from cardlink.modem import ModemController
        from pathlib import Path

        # Profile directory
        profile_dir = Path.home() / ".cardlink" / "profiles" / "modem"
        profile_dir.mkdir(parents=True, exist_ok=True)

        profile_file = profile_dir / f"{name}.json"

        # Check if exists
        if profile_file.exists() and not force:
            console.print(f"[red]Profile '{name}' already exists. Use --force to overwrite.[/red]")
            sys.exit(1)

        async def _save_profile():
            controller = ModemController()
            modem = await controller.get_modem(port)
            profile = await modem.get_profile()
            await controller.close_all_modems()
            return profile

        profile = run_async(_save_profile())

        # Save to file
        with open(profile_file, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)

        console.print(f"[green]Profile saved:[/green] {profile_file}")
        console.print(f"  Port: {port}")
        console.print(f"  Model: {profile.modem.model}")
        console.print(f"  IMEI: {profile.modem.imei}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command()
@click.argument("name")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def load(ctx: click.Context, name: str, json_output: bool) -> None:
    """Load and display saved profile.

    NAME: Profile name
    """
    try:
        from pathlib import Path

        profile_file = Path.home() / ".cardlink" / "profiles" / "modem" / f"{name}.json"

        if not profile_file.exists():
            console.print(f"[red]Profile '{name}' not found[/red]")
            sys.exit(1)

        with open(profile_file, "r") as f:
            data = json.load(f)

        if json_output:
            click.echo(json.dumps(data, indent=2))
            return

        # Display profile
        console.print(f"[bold]Profile: {name}[/bold]\n")

        # Modem info
        if "modem" in data:
            table = Table(title="Modem Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            modem = data["modem"]
            table.add_row("Manufacturer", modem.get("manufacturer", "N/A"))
            table.add_row("Model", modem.get("model", "N/A"))
            table.add_row("Firmware", modem.get("firmware_version", "N/A"))
            table.add_row("IMEI", modem.get("imei", "N/A"))
            table.add_row("Vendor", modem.get("vendor", "N/A"))

            console.print(table)
            console.print()

        # SIM info
        if "sim" in data:
            table = Table(title="SIM Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            sim = data["sim"]
            table.add_row("Status", sim.get("status", "N/A"))
            table.add_row("ICCID", sim.get("iccid", "N/A"))
            table.add_row("IMSI", sim.get("imsi", "N/A"))
            table.add_row("MSISDN", sim.get("msisdn", "N/A"))
            if sim.get("mcc") and sim.get("mnc"):
                table.add_row("MCC/MNC", f"{sim['mcc']}/{sim['mnc']}")

            console.print(table)
            console.print()

        # Network info
        if "network" in data:
            table = Table(title="Network Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            network = data["network"]
            table.add_row("Registration", network.get("registration_status", "N/A"))
            table.add_row("Operator", network.get("operator_name", "N/A"))
            table.add_row("Network Type", network.get("network_type", "N/A"))
            table.add_row("APN", network.get("apn", "N/A"))

            if network.get("rssi"):
                table.add_row("RSSI", f"{network['rssi']} dBm")
            if network.get("rsrp"):
                table.add_row("RSRP", f"{network['rsrp']} dBm")

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List saved profiles."""
    try:
        from pathlib import Path

        profile_dir = Path.home() / ".cardlink" / "profiles" / "modem"

        if not profile_dir.exists():
            console.print("[yellow]No profiles found[/yellow]")
            return

        profile_files = sorted(profile_dir.glob("*.json"))

        if not profile_files:
            console.print("[yellow]No profiles found[/yellow]")
            return

        table = Table(title="Saved Modem Profiles")
        table.add_column("Name", style="cyan")
        table.add_column("Model", style="green")
        table.add_column("IMEI", style="white")
        table.add_column("Saved", style="white")

        for profile_file in profile_files:
            try:
                with open(profile_file, "r") as f:
                    data = json.load(f)

                name = profile_file.stem
                model = data.get("modem", {}).get("model", "N/A")
                imei = data.get("modem", {}).get("imei", "N/A")

                # Mask IMEI
                if imei and imei != "N/A" and len(imei) > 4:
                    imei = "***" + imei[-4:]

                # Get file modified time
                import datetime
                mtime = datetime.datetime.fromtimestamp(profile_file.stat().st_mtime)
                saved = mtime.strftime("%Y-%m-%d %H:%M")

                table.add_row(name, model, imei, saved)

            except Exception as e:
                console.print(f"[yellow]Warning: Could not load {profile_file.name}: {e}[/yellow]")
                continue

        console.print(table)
        console.print(f"\n[bold]Total: {len(profile_files)} profile(s)[/bold]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@profile.command()
@click.argument("name1")
@click.argument("name2")
@click.pass_context
def compare(ctx: click.Context, name1: str, name2: str) -> None:
    """Compare two profiles.

    Shows differences between two saved profiles.

    NAME1: First profile name
    NAME2: Second profile name
    """
    try:
        from pathlib import Path

        profile_dir = Path.home() / ".cardlink" / "profiles" / "modem"

        profile1_file = profile_dir / f"{name1}.json"
        profile2_file = profile_dir / f"{name2}.json"

        if not profile1_file.exists():
            console.print(f"[red]Profile '{name1}' not found[/red]")
            sys.exit(1)

        if not profile2_file.exists():
            console.print(f"[red]Profile '{name2}' not found[/red]")
            sys.exit(1)

        with open(profile1_file, "r") as f:
            data1 = json.load(f)

        with open(profile2_file, "r") as f:
            data2 = json.load(f)

        console.print(f"[bold]Comparing Profiles[/bold]")
        console.print(f"  Profile 1: {name1}")
        console.print(f"  Profile 2: {name2}\n")

        # Compare function
        def compare_dicts(d1, d2, section_name):
            differences = []
            all_keys = set(d1.keys()) | set(d2.keys())

            for key in sorted(all_keys):
                val1 = d1.get(key)
                val2 = d2.get(key)

                if val1 != val2:
                    differences.append((key, val1, val2))

            if differences:
                table = Table(title=f"{section_name} Differences")
                table.add_column("Field", style="cyan")
                table.add_column("Profile 1", style="yellow")
                table.add_column("Profile 2", style="green")

                for key, val1, val2 in differences:
                    table.add_row(
                        key,
                        str(val1) if val1 is not None else "N/A",
                        str(val2) if val2 is not None else "N/A",
                    )

                console.print(table)
                console.print()
                return True
            return False

        # Compare each section
        has_differences = False
        has_differences |= compare_dicts(data1.get("modem", {}), data2.get("modem", {}), "Modem")
        has_differences |= compare_dicts(data1.get("sim", {}), data2.get("sim", {}), "SIM")
        has_differences |= compare_dicts(data1.get("network", {}), data2.get("network", {}), "Network")

        if not has_differences:
            console.print("[green]Profiles are identical[/green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command()
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(ctx: click.Context, name: str, yes: bool) -> None:
    """Delete saved profile.

    NAME: Profile name
    """
    try:
        from pathlib import Path

        profile_file = Path.home() / ".cardlink" / "profiles" / "modem" / f"{name}.json"

        if not profile_file.exists():
            console.print(f"[red]Profile '{name}' not found[/red]")
            sys.exit(1)

        if not yes:
            confirm = click.confirm(f"Delete profile '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        profile_file.unlink()
        console.print(f"[green]Profile deleted:[/green] {name}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("port")
@click.option("--start", "-s", is_flag=True, help="Start diagnostic logging")
@click.option("--stop", "-x", is_flag=True, help="Stop diagnostic logging")
@click.option("--export", "-e", type=click.Path(), help="Export log to file")
@click.pass_context
def diag(ctx: click.Context, port: str, start: bool, stop: bool, export: Optional[str]) -> None:
    """QXDM diagnostic interface.

    Control Qualcomm diagnostic logging (requires Qualcomm-based modems).

    PORT: Serial port path
    """
    try:
        from cardlink.modem import ModemController

        async def _diag_operation():
            controller = ModemController()
            modem = await controller.get_modem(port)

            # Check if QXDM is available
            if not hasattr(modem, "qxdm") or modem.qxdm is None:
                console.print("[yellow]QXDM interface not available for this modem[/yellow]")
                await controller.close_all_modems()
                return False

            if start:
                console.print("[bold]Starting diagnostic logging...[/bold]")
                success = await modem.qxdm.start_logging()
                if success:
                    console.print("[green]Diagnostic logging started[/green]")
                else:
                    console.print("[red]Failed to start diagnostic logging[/red]")

            elif stop:
                console.print("[bold]Stopping diagnostic logging...[/bold]")
                await modem.qxdm.stop_logging()
                console.print("[green]Diagnostic logging stopped[/green]")

            elif export:
                console.print(f"[bold]Exporting diagnostic log to {export}...[/bold]")
                success = await modem.qxdm.export_log(export)
                if success:
                    console.print(f"[green]Log exported:[/green] {export}")
                else:
                    console.print("[red]Failed to export log[/red]")

            else:
                # Show status
                is_available = await modem.qxdm.is_available()
                console.print(f"QXDM Available: {'Yes' if is_available else 'No'}")

                if is_available:
                    dm_port = modem.qxdm.get_dm_port()
                    console.print(f"DM Port: {dm_port or 'Not detected'}")

            await controller.close_all_modems()
            return True

        run_async(_diag_operation())

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def main() -> None:
    """Entry point for modem CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
