"""Metrics HTTP server for Prometheus endpoint.

This module provides an HTTP server that exposes Prometheus metrics
at the configured endpoint.
"""

import base64
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from cardlink.observability.config import MetricsConfig

logger = logging.getLogger(__name__)


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Prometheus metrics endpoint."""

    def __init__(self, config: MetricsConfig, registry: CollectorRegistry, *args, **kwargs):
        """Initialize handler with config.

        Args:
            config: Metrics configuration.
            registry: Prometheus collector registry.
        """
        self.metrics_config = config
        self.registry = registry
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests."""
        # Check if request is for metrics endpoint
        if self.path != self.metrics_config.path:
            self.send_error(404, "Not Found")
            return

        # Check authentication if configured
        if self.metrics_config.auth_username and self.metrics_config.auth_password:
            if not self._check_auth():
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="Metrics"')
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return

        # Generate and send metrics
        try:
            metrics_output = generate_latest(self.registry)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(metrics_output)))
            self.end_headers()
            self.wfile.write(metrics_output)
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            self.send_error(500, "Internal Server Error")

    def _check_auth(self) -> bool:
        """Check HTTP Basic authentication.

        Returns:
            True if authentication is valid, False otherwise.
        """
        auth_header = self.headers.get("Authorization")
        if not auth_header:
            return False

        # Parse Basic auth header
        try:
            auth_type, auth_data = auth_header.split(" ", 1)
            if auth_type.lower() != "basic":
                return False

            decoded = base64.b64decode(auth_data).decode("utf-8")
            username, password = decoded.split(":", 1)

            return (
                username == self.metrics_config.auth_username
                and password == self.metrics_config.auth_password
            )
        except Exception:
            return False

    def log_message(self, format: str, *args) -> None:
        """Override log_message to use Python logging.

        Args:
            format: Log format string.
            *args: Format arguments.
        """
        logger.debug(f"{self.address_string()} - {format % args}")


class MetricsServer:
    """HTTP server for exposing Prometheus metrics.

    This server runs in a background thread and exposes metrics at the
    configured endpoint with optional HTTP Basic authentication.

    Example:
        >>> from cardlink.observability.config import MetricsConfig
        >>> config = MetricsConfig(
        ...     enabled=True,
        ...     port=9090,
        ...     path="/metrics",
        ...     auth_username="admin",
        ...     auth_password="secret"
        ... )
        >>> server = MetricsServer(config)
        >>> server.start()
        >>> # Server is now running at http://localhost:9090/metrics
        >>> server.shutdown()
    """

    def __init__(self, config: MetricsConfig, registry: CollectorRegistry):
        """Initialize metrics server.

        Args:
            config: Metrics configuration.
            registry: Prometheus collector registry.
        """
        self.config = config
        self.registry = registry
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the HTTP server in a background thread.

        Example:
            >>> server = MetricsServer(config)
            >>> server.start()
        """
        if self._running:
            logger.warning("Metrics server already running")
            return

        # Create handler factory with config and registry
        def handler_factory(*args, **kwargs):
            return MetricsHTTPHandler(self.config, self.registry, *args, **kwargs)

        # Create HTTP server
        try:
            self._httpd = HTTPServer(("0.0.0.0", self.config.port), handler_factory)
            logger.info(
                f"Metrics server listening on port {self.config.port}, "
                f"path {self.config.path}"
            )

            # Start server in background thread
            self._running = True
            self._thread = threading.Thread(
                target=self._serve_forever, daemon=True, name="MetricsServer"
            )
            self._thread.start()

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    def shutdown(self) -> None:
        """Shutdown the HTTP server gracefully.

        Example:
            >>> server.shutdown()
        """
        if not self._running:
            return

        logger.info("Shutting down metrics server")
        self._running = False

        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()  # Close the socket to release the port

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("Metrics server stopped")

    def _serve_forever(self) -> None:
        """Background thread method to serve HTTP requests."""
        try:
            self._httpd.serve_forever()
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
        finally:
            self._running = False

    @property
    def is_running(self) -> bool:
        """Check if server is running.

        Returns:
            True if server is running, False otherwise.
        """
        return self._running

    @property
    def url(self) -> str:
        """Get the full URL of the metrics endpoint.

        Returns:
            Metrics endpoint URL.

        Example:
            >>> server = MetricsServer(config)
            >>> server.start()
            >>> print(server.url)
            http://0.0.0.0:9090/metrics
        """
        return f"http://0.0.0.0:{self.config.port}{self.config.path}"
