"""Phone CLI commands for GP OTA Tester.

This module provides command-line interface commands for Android
phone control via ADB.

Example:
    $ gp-phone list
    $ gp-phone info <serial>
    $ gp-phone at <serial> AT+CPIN?
    $ gp-phone monitor <serial>
    $ gp-phone profile save <serial> <name>
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
@click.option(
    "--adb-path",
    type=str,
    default=None,
    help="Custom path to ADB executable",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, adb_path: Optional[str]) -> None:
    """Android phone control and monitoring via ADB.

    Discover, configure, and monitor Android devices for OTA testing.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["adb_path"] = adb_path

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
    """List connected Android devices.

    Scans for all Android devices connected via ADB and displays
    their basic information.
    """
    try:
        from cardlink.phone import PhoneController

        async def _list():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            devices = await controller.discover_devices()
            return devices

        devices = run_async(_list())

        if json_output:
            data = [d.to_dict() for d in devices]
            click.echo(json.dumps(data, indent=2))
            return

        if not devices:
            console.print("[yellow]No Android devices found[/yellow]")
            console.print("Make sure USB debugging is enabled and device is authorized.")
            return

        table = Table(title="Connected Android Devices")
        table.add_column("Serial", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Model", style="white")
        table.add_column("Product", style="white")

        for device in devices:
            state_style = "green" if device.state.value == "device" else "yellow"
            table.add_row(
                device.serial,
                f"[{state_style}]{device.state.value}[/{state_style}]",
                device.model or "N/A",
                device.product or "N/A",
            )

        console.print(table)
        console.print(f"\n[bold]Total: {len(devices)} device(s)[/bold]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("serial")
@click.option("--device", "-d", is_flag=True, help="Show device info only")
@click.option("--sim", "-s", is_flag=True, help="Show SIM info only")
@click.option("--network", "-n", is_flag=True, help="Show network info only")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all information")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def info(
    ctx: click.Context,
    serial: str,
    device: bool,
    sim: bool,
    network: bool,
    show_all: bool,
    json_output: bool,
) -> None:
    """Show device information.

    Display detailed information about device, SIM, and network status.

    SERIAL: Device serial number (from 'list' command)
    """
    try:
        from cardlink.phone import PhoneController

        async def _get_info():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)
            profile = await phone.info.get_full_profile()
            return profile

        profile = run_async(_get_info())

        # Determine what to show
        if not (device or sim or network):
            show_all = True

        if json_output:
            data = {}
            if show_all or device:
                data["device"] = profile.device.to_dict()
            if show_all or sim:
                data["sim_profiles"] = [s.to_dict() for s in profile.sim_profiles]
            if show_all or network:
                data["network"] = profile.network.to_dict() if profile.network else None
            click.echo(json.dumps(data, indent=2))
            return

        # Device info
        if show_all or device:
            table = Table(title="Device Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Serial", profile.device.serial)
            table.add_row("Manufacturer", profile.device.manufacturer)
            table.add_row("Model", profile.device.model)
            table.add_row("Brand", profile.device.brand)
            table.add_row("Android Version", profile.device.android_version)
            table.add_row("API Level", str(profile.device.api_level))
            table.add_row("Build Number", profile.device.build_number)
            table.add_row("Security Patch", profile.device.security_patch)
            if profile.device.imei:
                # Mask IMEI for security
                imei = profile.device.imei
                masked = imei[:4] + "****" + imei[-4:] if len(imei) > 8 else imei
                table.add_row("IMEI", masked)
            table.add_row("Baseband", profile.device.baseband_version or "N/A")

            console.print(table)
            console.print()

        # SIM info
        if show_all or sim:
            if profile.sim_profiles:
                for sim_profile in profile.sim_profiles:
                    table = Table(title=f"SIM Slot {sim_profile.slot}")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")

                    table.add_row("Status", sim_profile.status.value)
                    table.add_row("ICCID", sim_profile.iccid or "N/A")
                    table.add_row("IMSI", sim_profile.imsi or "N/A")
                    table.add_row("MSISDN", sim_profile.msisdn or "N/A")
                    table.add_row("Operator", sim_profile.operator_name or "N/A")
                    if sim_profile.mcc:
                        table.add_row("MCC/MNC", f"{sim_profile.mcc}/{sim_profile.mnc}")
                    table.add_row("eSIM", "Yes" if sim_profile.is_embedded else "No")
                    table.add_row("Active", "Yes" if sim_profile.is_active else "No")

                    console.print(table)
                    console.print()
            else:
                console.print("[yellow]No SIM information available[/yellow]\n")

        # Network info
        if show_all or network:
            if profile.network:
                table = Table(title="Network Information")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Operator", profile.network.operator_name or "N/A")
                table.add_row("Network Type", profile.network.network_type.value)
                table.add_row("Data State", profile.network.data_state.value)
                table.add_row("Roaming", "Yes" if profile.network.data_roaming else "No")
                if profile.network.signal_strength_dbm != -999:
                    table.add_row("Signal", f"{profile.network.signal_strength_dbm} dBm")
                table.add_row(
                    "WiFi",
                    f"Connected ({profile.network.wifi_ssid})"
                    if profile.network.is_wifi_connected
                    else "Disconnected",
                )
                if profile.network.mobile_ip:
                    table.add_row("Mobile IP", profile.network.mobile_ip)
                if profile.network.apn_name:
                    table.add_row("APN", profile.network.apn_name)

                console.print(table)
            else:
                console.print("[yellow]No network information available[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("serial")
@click.argument("command")
@click.option("--timeout", "-t", type=float, default=5.0, help="Command timeout")
@click.pass_context
def at(ctx: click.Context, serial: str, command: str, timeout: float) -> None:
    """Send AT command to device modem.

    SERIAL: Device serial number
    COMMAND: AT command to send (with or without AT prefix)

    Note: AT commands may require root access on the device.
    """
    try:
        from cardlink.phone import PhoneController

        async def _send_command():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)
            response = await phone.at.send_command(command, timeout=timeout)
            return response

        response = run_async(_send_command())

        console.print(f"[cyan]Command:[/cyan] {command}")
        console.print(f"[cyan]Result:[/cyan] {response.result.value}")

        if response.response_lines:
            console.print("[cyan]Response:[/cyan]")
            for line in response.response_lines:
                console.print(f"  {line}")

        if response.error_code:
            console.print(f"[red]Error Code:[/red] {response.error_code}")
        if response.error_message:
            console.print(f"[red]Error:[/red] {response.error_message}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("serial")
@click.option("--duration", "-d", type=int, help="Monitor duration in seconds")
@click.pass_context
def monitor(ctx: click.Context, serial: str, duration: Optional[int]) -> None:
    """Monitor BIP events in real-time.

    Starts real-time monitoring of BIP (Bearer Independent Protocol)
    events via logcat. Press Ctrl+C to stop.

    SERIAL: Device serial number
    """
    try:
        from cardlink.phone import PhoneController

        def on_bip_event(event):
            console.print(f"[bold green]BIP Event:[/bold green] {event.event_type.value}")
            if event.channel_id is not None:
                console.print(f"  Channel ID: {event.channel_id}")
            if event.address:
                console.print(f"  Address: {event.address}:{event.port}")
            if event.bearer_type:
                console.print(f"  Bearer: {event.bearer_type}")
            if event.data_length:
                console.print(f"  Data Length: {event.data_length}")
            if event.status:
                console.print(f"  Status: {event.status}")
            console.print(f"  Time: {event.timestamp.isoformat()}")
            console.print()

        async def _monitor():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)

            console.print(f"[bold]Monitoring BIP events on {serial}[/bold]")
            console.print("Press Ctrl+C to stop\n")

            phone.bip.on_bip_event(on_bip_event)
            await phone.bip.start()

            try:
                if duration:
                    await asyncio.sleep(duration)
                else:
                    while True:
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await phone.bip.stop()

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
@click.argument("serial")
@click.option("--template", "-t", type=str, help="Trigger template name")
@click.option("--pdu", "-p", type=str, help="Raw PDU hex string")
@click.pass_context
def trigger(ctx: click.Context, serial: str, template: Optional[str], pdu: Optional[str]) -> None:
    """Send SMS-PP trigger.

    Send an SMS-PP trigger message to initiate OTA session.

    SERIAL: Device serial number

    Either --template or --pdu must be specified.
    """
    if not template and not pdu:
        console.print("[red]Error: Either --template or --pdu must be specified[/red]")
        sys.exit(1)

    try:
        from cardlink.phone import PhoneController

        async def _send_trigger():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)

            if pdu:
                console.print(f"[bold]Sending raw PDU to {serial}[/bold]")
                result = await phone.sms.send_raw_pdu(pdu)
            else:
                console.print(f"[bold]Sending trigger '{template}' to {serial}[/bold]")
                result = await phone.sms.send_trigger(template, {})

            return result

        result = run_async(_send_trigger())

        if result.success:
            console.print("[green]Trigger sent successfully[/green]")
            console.print(f"Method: {result.method_used}")
        else:
            console.print("[red]Trigger send failed[/red]")
            if result.error_message:
                console.print(f"Error: {result.error_message}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


# =============================================================================
# Profile Subgroup
# =============================================================================


@cli.group()
def profile():
    """Device profile management commands.

    Save, load, and compare device profiles.
    """
    pass


@profile.command("save")
@click.argument("serial")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing profile")
@click.pass_context
def profile_save(ctx: click.Context, serial: str, name: str, force: bool) -> None:
    """Save device profile.

    Captures current device state and saves it to a profile.

    SERIAL: Device serial number
    NAME: Profile name to save as
    """
    try:
        from cardlink.phone import PhoneController, ProfileManager

        async def _save():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)
            profile = await phone.info.get_full_profile()

            manager = ProfileManager()
            path = await manager.save_profile(name, profile, overwrite=force)
            return path

        path = run_async(_save())
        console.print(f"[green]Profile saved:[/green] {path}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command("load")
@click.argument("name")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def profile_load(ctx: click.Context, name: str, json_output: bool) -> None:
    """Load and display a saved profile.

    NAME: Profile name to load
    """
    try:
        from cardlink.phone import ProfileManager

        async def _load():
            manager = ProfileManager()
            profile = await manager.load_profile(name)
            return profile

        profile = run_async(_load())

        if json_output:
            click.echo(profile.to_json())
            return

        # Display summary
        from cardlink.phone.profile_manager import ProfileManager as PM

        manager = PM()
        summary = manager._format_summary(profile)
        console.print(summary)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def profile_list(ctx: click.Context, json_output: bool) -> None:
    """List all saved profiles."""
    try:
        from cardlink.phone import ProfileManager

        manager = ProfileManager()
        profiles = manager.list_profiles()

        if json_output:
            click.echo(json.dumps(profiles, indent=2))
            return

        if not profiles:
            console.print("[yellow]No saved profiles[/yellow]")
            return

        table = Table(title="Saved Profiles")
        table.add_column("Name", style="cyan")
        table.add_column("Serial", style="green")
        table.add_column("Model", style="white")
        table.add_column("Saved At", style="white")

        for p in profiles:
            table.add_row(
                p.get("name", ""),
                p.get("serial", ""),
                p.get("model", ""),
                p.get("saved_at", "")[:19],  # Truncate timestamp
            )

        console.print(table)
        console.print(f"\n[bold]Total: {len(profiles)} profile(s)[/bold]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@profile.command("compare")
@click.argument("name1")
@click.argument("name2")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def profile_compare(ctx: click.Context, name1: str, name2: str, json_output: bool) -> None:
    """Compare two saved profiles.

    NAME1: First profile name
    NAME2: Second profile name
    """
    try:
        from cardlink.phone import ProfileManager

        async def _compare():
            manager = ProfileManager()
            profile1 = await manager.load_profile(name1)
            profile2 = await manager.load_profile(name2)
            diff = manager.compare(profile1, profile2)
            return diff

        diff = run_async(_compare())

        if json_output:
            click.echo(json.dumps(diff, indent=2))
            return

        if not diff:
            console.print("[green]Profiles are identical[/green]")
            return

        console.print(f"[bold]Differences between '{name1}' and '{name2}':[/bold]\n")

        if "device" in diff:
            table = Table(title="Device Changes")
            table.add_column("Property", style="cyan")
            table.add_column(f"{name1}", style="yellow")
            table.add_column(f"{name2}", style="green")

            for key, values in diff["device"].items():
                table.add_row(key, str(values["old"]), str(values["new"]))

            console.print(table)
            console.print()

        if "network" in diff:
            table = Table(title="Network Changes")
            table.add_column("Property", style="cyan")
            table.add_column(f"{name1}", style="yellow")
            table.add_column(f"{name2}", style="green")

            for key, values in diff["network"].items():
                table.add_row(key, str(values["old"]), str(values["new"]))

            console.print(table)
            console.print()

        if "sim" in diff:
            for sim_diff in diff["sim"]:
                slot = sim_diff.get("slot", "?")
                table = Table(title=f"SIM Slot {slot} Changes")
                table.add_column("Property", style="cyan")
                table.add_column(f"{name1}", style="yellow")
                table.add_column(f"{name2}", style="green")

                for key, values in sim_diff.get("changes", {}).items():
                    table.add_row(key, str(values["old"]), str(values["new"]))

                console.print(table)
                console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@profile.command("delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def profile_delete(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a saved profile.

    NAME: Profile name to delete
    """
    try:
        from cardlink.phone import ProfileManager

        manager = ProfileManager()

        if not manager.profile_exists(name):
            console.print(f"[yellow]Profile '{name}' not found[/yellow]")
            return

        if not force:
            if not click.confirm(f"Delete profile '{name}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        if manager.delete_profile(name):
            console.print(f"[green]Profile '{name}' deleted[/green]")
        else:
            console.print(f"[red]Failed to delete profile '{name}'[/red]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


# =============================================================================
# Network Subgroup
# =============================================================================


@cli.group()
def network():
    """Network configuration commands.

    Control WiFi, mobile data, and APN settings.
    """
    pass


@network.command("wifi")
@click.argument("serial")
@click.argument("action", type=click.Choice(["enable", "disable", "status"]))
@click.pass_context
def network_wifi(ctx: click.Context, serial: str, action: str) -> None:
    """Control WiFi.

    SERIAL: Device serial number
    ACTION: enable, disable, or status
    """
    try:
        from cardlink.phone import PhoneController

        async def _wifi():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)

            if action == "enable":
                success = await phone.network.enable_wifi()
                return "enabled" if success else "failed"
            elif action == "disable":
                success = await phone.network.disable_wifi()
                return "disabled" if success else "failed"
            else:
                status = await phone.network.get_wifi_status()
                return status

        result = run_async(_wifi())

        if action == "status":
            console.print(f"WiFi: {result}")
        else:
            if "failed" in result:
                console.print(f"[red]WiFi {action} failed[/red]")
            else:
                console.print(f"[green]WiFi {result}[/green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@network.command("data")
@click.argument("serial")
@click.argument("action", type=click.Choice(["enable", "disable"]))
@click.pass_context
def network_data(ctx: click.Context, serial: str, action: str) -> None:
    """Control mobile data.

    SERIAL: Device serial number
    ACTION: enable or disable
    """
    try:
        from cardlink.phone import PhoneController

        async def _data():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)

            if action == "enable":
                return await phone.network.enable_mobile_data()
            else:
                return await phone.network.disable_mobile_data()

        success = run_async(_data())

        if success:
            console.print(f"[green]Mobile data {action}d[/green]")
        else:
            console.print(f"[red]Failed to {action} mobile data[/red]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@network.command("test")
@click.argument("serial")
@click.option("--url", "-u", default="https://www.google.com", help="URL to test")
@click.pass_context
def network_test(ctx: click.Context, serial: str, url: str) -> None:
    """Test network connectivity.

    SERIAL: Device serial number
    """
    try:
        from cardlink.phone import PhoneController

        async def _test():
            controller = PhoneController(adb_path=ctx.obj.get("adb_path"))
            phone = await controller.get_device(serial)
            return await phone.network.test_connectivity(url)

        result = run_async(_test())

        if result:
            console.print(f"[green]Connectivity OK:[/green] {url}")
        else:
            console.print(f"[red]Connectivity failed:[/red] {url}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for phone CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
