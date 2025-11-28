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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import ModemController

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
        from gp_ota_tester.modem import SerialClient

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


def main() -> None:
    """Entry point for modem CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
