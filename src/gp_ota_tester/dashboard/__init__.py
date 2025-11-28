"""GP OTA Tester Web Dashboard.

This package provides a web-based dashboard for monitoring and
controlling GlobalPlatform OTA test sessions.

Features:
- Real-time APDU log viewing with virtual scrolling
- Session management and monitoring
- Command builder for manual APDU commands
- Alert configuration for specific APDU patterns
- Dark/light theme support

Quick Start:
    >>> from gp_ota_tester.dashboard import start_dashboard
    >>>
    >>> # Start dashboard server
    >>> await start_dashboard(host="127.0.0.1", port=8080)

Example with custom configuration:
    >>> from gp_ota_tester.dashboard import DashboardServer, DashboardConfig
    >>>
    >>> config = DashboardConfig(
    ...     host="0.0.0.0",
    ...     port=8080,
    ...     cors_origins=["http://localhost:3000"],
    ... )
    >>> server = DashboardServer(config)
    >>> await server.start()
"""

__version__ = "0.1.0"

from gp_ota_tester.dashboard.server import (
    DashboardServer,
    DashboardConfig,
    DashboardState,
    Session,
    APDUEntry,
    start_dashboard,
)

__all__ = [
    "__version__",
    "DashboardServer",
    "DashboardConfig",
    "DashboardState",
    "Session",
    "APDUEntry",
    "start_dashboard",
]
