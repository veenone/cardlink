"""CLI commands for GP OTA Tester.

This module provides command-line interface commands for managing
the PSK-TLS Admin Server, modem control, and phone control.

Example:
    $ gp-ota-server start --port 8443
    $ gp-ota-server stop
    $ gp-modem list
    $ gp-phone list
"""

from cardlink.cli.server import cli, start, stop
from cardlink.cli.modem import cli as modem_cli
from cardlink.cli.phone import cli as phone_cli

__all__ = [
    "cli",
    "start",
    "stop",
    "modem_cli",
    "phone_cli",
]
