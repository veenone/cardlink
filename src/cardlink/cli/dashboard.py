"""Dashboard CLI commands for GP OTA Tester.

This module provides command-line interface commands for starting
and managing the web dashboard.

Example:
    $ gp-dashboard start
    $ gp-dashboard start --port 8080 --host 0.0.0.0
"""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console

console = Console()


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Web dashboard for GP OTA Tester.

    Start and manage the web-based monitoring dashboard.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Host to bind to",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Port to bind to",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Open browser automatically",
)
@click.pass_context
def start(ctx: click.Context, host: str, port: int, open_browser: bool) -> None:
    """Start the dashboard server.

    Starts the web dashboard for monitoring APDU traffic and
    managing test sessions.
    """
    try:
        from cardlink.dashboard import DashboardServer, DashboardConfig

        config = DashboardConfig(host=host, port=port)
        server = DashboardServer(config)

        url = f"http://{host}:{port}"
        console.print(f"\n[bold green]Starting GP OTA Dashboard[/bold green]")
        console.print(f"[cyan]URL:[/cyan] {url}")
        console.print("\nPress Ctrl+C to stop\n")

        if open_browser:
            import webbrowser
            webbrowser.open(url)

        try:
            asyncio.run(server.start())
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")

    except ImportError as e:
        console.print(f"[red]Error: Missing dependency - {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Dashboard host",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Dashboard port",
)
@click.pass_context
def status(ctx: click.Context, host: str, port: int) -> None:
    """Check dashboard server status.

    Checks if the dashboard server is running and displays
    basic status information.
    """
    import urllib.request
    import json

    url = f"http://{host}:{port}/api/status"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())

            console.print(f"\n[bold green]Dashboard is running[/bold green]")
            console.print(f"[cyan]URL:[/cyan] http://{host}:{port}")
            console.print(f"[cyan]Sessions:[/cyan] {data.get('sessions', 0)}")
            console.print(f"[cyan]Clients:[/cyan] {data.get('clients', 0)}")
            console.print()

    except urllib.error.URLError:
        console.print(f"\n[yellow]Dashboard is not running at http://{host}:{port}[/yellow]")
        console.print("Start with: gp-dashboard start\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Dashboard host",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Dashboard port",
)
@click.pass_context
def open_browser(ctx: click.Context, host: str, port: int) -> None:
    """Open dashboard in browser.

    Opens the default web browser to the dashboard URL.
    """
    import webbrowser

    url = f"http://{host}:{port}"

    try:
        webbrowser.open(url)
        console.print(f"[green]Opened {url}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for dashboard CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
