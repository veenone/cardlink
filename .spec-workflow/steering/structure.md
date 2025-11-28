# Project Structure

## Directory Organization

```
cardlink/
├── src/
│   └── cardlink/
│       ├── __init__.py
│       ├── cli/                      # CLI Layer
│       │   ├── __init__.py
│       │   ├── server.py             # cardlink-server CLI
│       │   ├── phone.py              # cardlink-phone CLI
│       │   ├── modem.py              # cardlink-modem CLI (IoT modems)
│       │   ├── provision.py          # cardlink-provision CLI
│       │   └── test.py               # cardlink-test CLI
│       ├── dashboard/                # Frontend Layer
│       │   ├── __init__.py
│       │   ├── server.py             # Dashboard web server
│       │   ├── websocket.py          # WebSocket handlers
│       │   ├── routes/               # HTTP route handlers
│       │   │   ├── __init__.py
│       │   │   ├── sessions.py       # OTA session management
│       │   │   ├── commands.py       # Manual RAM commands
│       │   │   └── logs.py           # Communication logs
│       │   ├── static/               # Frontend assets
│       │   │   ├── css/
│       │   │   ├── js/
│       │   │   └── index.html
│       │   └── templates/            # HTML templates (if using Jinja2)
│       ├── server/                   # Service Layer - Admin Server
│       │   ├── __init__.py
│       │   ├── admin_server.py       # PSK-TLS HTTPS server
│       │   ├── tls_handler.py        # TLS/PSK connection handling
│       │   ├── tls_monitor.py        # TLS handshake monitoring
│       │   └── session_manager.py    # Session state management
│       ├── phone/                    # Service Layer - Phone Controller
│       │   ├── __init__.py
│       │   ├── adb_controller.py     # ADB device control
│       │   ├── at_interface.py       # AT command interface
│       │   ├── network_manager.py    # WiFi/network control
│       │   ├── bip_monitor.py        # BIP event monitoring
│       │   ├── sms_trigger.py        # SMS-PP trigger
│       │   └── logcat_parser.py      # Android log parsing
│       ├── modem/                    # Service Layer - IoT Modem Controller
│       │   ├── __init__.py
│       │   ├── serial_controller.py  # Serial/USB communication
│       │   ├── at_interface.py       # AT command interface for modems
│       │   ├── quectel.py            # Quectel-specific handlers
│       │   ├── qxdm_interface.py     # QXDM diagnostic integration
│       │   └── bip_monitor.py        # BIP event monitoring for modems
│       ├── provision/                # Service Layer - UICC Provisioner
│       │   ├── __init__.py
│       │   ├── card_manager.py       # PC/SC card access
│       │   ├── key_injector.py       # PSK key provisioning
│       │   ├── url_config.py         # Admin URL setup
│       │   └── bip_config.py         # BIP settings
│       ├── network_sim/              # Service Layer - Network Simulator
│       │   ├── __init__.py
│       │   ├── amarisoft.py          # Amarisoft integration
│       │   ├── websocket_client.py   # WebSocket client for simulator
│       │   └── tcp_client.py         # TCP/IP fallback client
│       ├── observability/            # Observability Layer - Metrics & Monitoring
│       │   ├── __init__.py
│       │   ├── metrics.py            # Prometheus metrics definitions
│       │   ├── collectors.py         # Custom metric collectors
│       │   ├── exporter.py           # Metrics HTTP endpoint (/metrics)
│       │   ├── otlp.py               # OpenTelemetry/Grafana Alloy export
│       │   └── dashboards/           # Pre-built Grafana dashboard templates
│       │       ├── overview.json     # OTA session overview dashboard
│       │       ├── apdu_analysis.json # APDU command analysis dashboard
│       │       └── errors.json       # Error rate monitoring dashboard
│       ├── database/                 # Data Layer
│       │   ├── __init__.py
│       │   ├── engine.py             # Database engine setup (SQLite/MySQL/PostgreSQL)
│       │   ├── models.py             # SQLAlchemy ORM models
│       │   ├── migrations/           # Alembic migrations
│       │   │   └── versions/
│       │   ├── repositories/         # Data access layer
│       │   │   ├── __init__.py
│       │   │   ├── session_repo.py   # Session data repository
│       │   │   ├── device_repo.py    # Device configuration repository
│       │   │   ├── card_repo.py      # UICC card profiles repository
│       │   │   ├── log_repo.py       # Communication logs repository
│       │   │   └── test_repo.py      # Test results repository
│       │   └── schemas.py            # Pydantic schemas for validation
│       ├── protocol/                 # Protocol Layer
│       │   ├── __init__.py
│       │   ├── apdu.py               # C-APDU, R-APDU classes
│       │   ├── tlv.py                # BER-TLV encoding/decoding
│       │   ├── gp_commands.py        # GP card command builders
│       │   ├── http_protocol.py      # HTTP Admin protocol
│       │   ├── sms_pdu.py            # SMS-PP PDU encoding
│       │   └── bip_commands.py       # BIP proactive commands
│       ├── testing/                  # Test Framework
│       │   ├── __init__.py
│       │   ├── runner.py             # Test case runner
│       │   ├── assertions.py         # Test assertions
│       │   ├── phone_fixtures.py     # Phone test fixtures
│       │   ├── modem_fixtures.py     # IoT modem test fixtures
│       │   └── e2e_orchestrator.py   # End-to-end coordinator
│       └── utils/                    # Shared Utilities
│           ├── __init__.py
│           ├── logging.py            # Logging configuration
│           ├── network.py            # Network utilities
│           ├── adb_utils.py          # ADB helpers
│           └── serial_utils.py       # Serial port helpers
├── tests/
│   ├── unit/                         # Unit tests
│   │   ├── test_apdu.py
│   │   ├── test_tlv.py
│   │   ├── test_gp_commands.py
│   │   ├── test_database.py
│   │   ├── test_metrics.py
│   │   └── ...
│   ├── integration/                  # Integration tests
│   │   ├── test_server.py
│   │   ├── test_phone.py
│   │   ├── test_modem.py
│   │   ├── test_repositories.py
│   │   └── ...
│   └── e2e/                          # End-to-end tests
│       ├── test_basic_connectivity.py
│       └── test_compliance.py
├── examples/
│   ├── test_suites/                  # Example test configurations
│   │   ├── smoke.yaml
│   │   ├── compliance.yaml
│   │   └── e2e_basic.yaml
│   └── configs/                      # Example configurations
│       ├── uicc_template.yaml
│       ├── phone_setup.yaml
│       └── modem_setup.yaml
├── data/                             # Default data directory
│   └── cardlink.db                   # SQLite database (default)
├── docker/                           # Docker deployment files
│   ├── Dockerfile                    # Main application Dockerfile
│   ├── Dockerfile.dev                # Development Dockerfile
│   └── .dockerignore                 # Docker ignore patterns
├── monitoring/                       # Monitoring configuration
│   ├── prometheus.yml                # Prometheus scrape config
│   ├── alloy-config.river            # Grafana Alloy configuration
│   └── grafana/
│       └── provisioning/
│           ├── dashboards/           # Auto-provisioned dashboards
│           └── datasources/          # Auto-provisioned datasources
├── config/                           # Configuration templates
│   ├── cardlink.yaml.example         # Example server configuration
│   └── .env.example                  # Example environment variables
├── docs/
│   ├── setup_guide.md                # Hardware setup guide
│   ├── uicc_provisioning.md          # Card provisioning guide
│   ├── modem_guide.md                # IoT modem guide
│   ├── dashboard_guide.md            # Dashboard usage guide
│   ├── database_guide.md             # Database configuration guide
│   ├── monitoring_guide.md           # Prometheus/Grafana setup guide
│   ├── docker_guide.md               # Docker deployment guide
│   └── troubleshooting.md            # Common issues
├── docker-compose.yml                # Docker Compose orchestration
├── pyproject.toml                    # Project configuration
├── README.md                         # Project overview
├── CHANGELOG.md                      # Version history
└── CLAUDE.md                         # AI assistant context
```

## Naming Conventions

### Files
- **Modules**: `snake_case.py` (e.g., `admin_server.py`, `adb_controller.py`)
- **Test files**: `test_<module>.py` (e.g., `test_apdu.py`, `test_server.py`)
- **Configuration**: `snake_case.yaml` (e.g., `uicc_template.yaml`)

### Code
- **Classes**: `PascalCase` (e.g., `AdminServer`, `ADBController`, `APDUCommand`)
- **Functions/Methods**: `snake_case` (e.g., `send_command`, `get_device_info`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PORT`, `MAX_TIMEOUT`)
- **Variables**: `snake_case` (e.g., `session_id`, `psk_key`)
- **Private members**: `_leading_underscore` (e.g., `_connection`, `_parse_response`)

## Import Patterns

### Import Order
1. Standard library imports
2. Third-party library imports
3. Local application imports (absolute)
4. Relative imports within same package

### Example
```python
# Standard library
import logging
import threading
from dataclasses import dataclass
from typing import Optional, List

# Third-party
import click
from sslpsk3 import SSLContext
from sqlalchemy.orm import Session

# Local absolute imports
from cardlink.protocol.apdu import APDUCommand, APDUResponse
from cardlink.database.repositories import SessionRepository
from cardlink.utils.logging import get_logger

# Relative imports (within same module)
from .session_manager import SessionManager
```

### Module/Package Organization
- Use absolute imports from `cardlink` package root
- Use relative imports within the same sub-package
- Each sub-package has `__init__.py` exposing public API

## Code Structure Patterns

### Module Organization
```python
"""Module docstring describing purpose."""

# 1. Imports (as described above)

# 2. Constants and configuration
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# 3. Type definitions / Enums
class DeviceState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

# 4. Data classes
@dataclass
class DeviceInfo:
    serial: str
    model: str

# 5. Main classes / functions
class Controller:
    """Main implementation."""
    pass

# 6. Helper functions (private)
def _parse_response(data: bytes) -> dict:
    """Internal helper."""
    pass
```

### Class Organization
```python
class AdminServer:
    """Class docstring."""

    # Class constants
    DEFAULT_PORT = 8443

    def __init__(self, ...):
        """Constructor with parameter docs."""
        pass

    # Public methods (alphabetically or by workflow)
    def start(self):
        pass

    def stop(self):
        pass

    # Private methods
    def _handle_connection(self):
        pass
```

### Function Organization
```python
def process_apdu(command: APDUCommand, timeout: int = 30) -> APDUResponse:
    """
    Process an APDU command.

    Args:
        command: The APDU command to send
        timeout: Response timeout in seconds

    Returns:
        APDUResponse with status and data

    Raises:
        TimeoutError: If no response within timeout
        ProtocolError: If invalid response received
    """
    # 1. Input validation
    if not command:
        raise ValueError("Command cannot be None")

    # 2. Core logic
    response = _send_and_receive(command, timeout)

    # 3. Return result
    return response
```

## Code Organization Principles

1. **Single Responsibility**: Each module handles one concern (e.g., `tls_handler.py` only handles TLS, not HTTP parsing)
2. **Modularity**: Components can be used independently (e.g., phone controller without server)
3. **Testability**: Classes accept dependencies via constructor for easy mocking
4. **Consistency**: Follow patterns established in existing code

## Module Boundaries

### Layer Dependencies
```
CLI Layer → Service Layer → Protocol Layer
              ↓      ↓           ↓
         Dashboard   Data    Observability
           Layer    Layer       Layer
                                  ↓
                         External Monitoring
                    (Prometheus / Grafana Alloy)
```

- **Protocol Layer**: No dependencies on other layers. Pure data structures and encoding.
- **Data Layer**: No dependencies on other layers. Provides database access via repositories.
- **Observability Layer**: No dependencies on other layers. Provides metrics export and monitoring integration.
- **Service Layer**: Depends on Protocol, Data, and Observability layers. Contains business logic.
- **CLI Layer**: Depends on Service Layer. Thin wrapper for command-line interface.
- **Dashboard Layer**: Depends on Service Layer. Provides web UI, can be disabled.

### Cross-Module Communication
- **Server ↔ Dashboard**: WebSocket for real-time updates, shared session state
- **Server ↔ Phone/Modem**: Through testing orchestrator, not direct coupling
- **Network Sim → Server**: Event callbacks, webhook-style integration
- **Observability → External**: Prometheus scraping `/metrics` endpoint, OTLP export to Grafana Alloy

### Public API Exposure
Each package `__init__.py` exports only public classes/functions:

```python
# cardlink/server/__init__.py
from .admin_server import AdminServer
from .session_manager import Session, SessionManager

__all__ = ['AdminServer', 'Session', 'SessionManager']
```

## Code Size Guidelines

- **File size**: Maximum 500 lines (split into multiple modules if larger)
- **Function size**: Maximum 50 lines (extract helpers if larger)
- **Class size**: Maximum 300 lines (consider splitting responsibilities)
- **Nesting depth**: Maximum 4 levels (refactor complex conditionals)

## Dashboard Structure

```
src/cardlink/dashboard/
├── server.py              # Flask/aiohttp app setup
├── websocket.py           # WebSocket handlers for real-time updates
├── routes/
│   ├── sessions.py        # /api/sessions - OTA session management
│   ├── commands.py        # /api/commands - Manual RAM commands
│   ├── logs.py            # /api/logs - Communication logs
│   └── tls.py             # /api/tls - TLS handshake info
└── static/
    ├── index.html         # Single-page dashboard
    ├── css/
    │   └── styles.css     # Dashboard styles
    └── js/
        ├── app.js         # Main application
        ├── websocket.js   # WebSocket client
        ├── sessions.js    # Session management UI
        ├── commands.js    # Command builder UI
        └── logs.js        # Log viewer UI
```

### Separation of Concerns
- Dashboard is self-contained in its own package
- Own entry point: `cardlink-server start --dashboard` enables web UI
- Minimal dependencies on core server (only session/command interfaces)
- Can be completely disabled without affecting CLI/server functionality

## Database Layer

### Database Structure
```
src/cardlink/database/
├── __init__.py
├── engine.py              # Database engine configuration
├── models.py              # SQLAlchemy ORM models
├── migrations/            # Alembic database migrations
│   ├── env.py
│   ├── alembic.ini
│   └── versions/          # Migration scripts
├── repositories/          # Repository pattern for data access
│   ├── __init__.py
│   ├── base_repo.py       # Base repository class
│   ├── session_repo.py    # OTA session data
│   ├── device_repo.py     # Phone/modem configurations
│   ├── card_repo.py       # UICC card profiles
│   ├── log_repo.py        # Communication logs
│   └── test_repo.py       # Test results and history
└── schemas.py             # Pydantic schemas for validation
```

### Database Support
- **SQLite3** (default): Local file-based, no setup required
- **MySQL**: For production deployments with multiple users
- **PostgreSQL**: For enterprise deployments with advanced features

### Database Configuration
```python
# Database connection via environment variable or config
DATABASE_URL = "sqlite:///data/cardlink.db"      # Default SQLite
DATABASE_URL = "mysql://user:pass@host/cardlink" # MySQL
DATABASE_URL = "postgresql://user:pass@host/cardlink" # PostgreSQL
```

### Data Models
| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Device` | Phone/modem configurations | serial, type, name, connection_params |
| `Card` | UICC card profiles | iccid, psk_identity, psk_key, admin_url |
| `Session` | OTA session records | id, device_id, card_id, status, timestamps |
| `CommandLog` | APDU command/response logs | session_id, direction, apdu_hex, timestamp |
| `TestResult` | Test execution results | test_id, session_id, status, duration, errors |
| `ServerConfig` | Server settings | key, value, description |

### Repository Pattern
```python
class SessionRepository:
    """Data access for OTA sessions."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, device_id: int, card_id: int) -> SessionModel:
        """Create a new session record."""
        pass

    def get_by_id(self, session_id: int) -> Optional[SessionModel]:
        """Retrieve session by ID."""
        pass

    def get_active(self) -> List[SessionModel]:
        """Get all active sessions."""
        pass

    def add_command_log(self, session_id: int, apdu: bytes, response: bytes):
        """Log APDU exchange."""
        pass
```

## Observability Layer

### Observability Structure
```
src/cardlink/observability/
├── __init__.py
├── metrics.py            # Prometheus metric definitions
├── collectors.py         # Custom metric collectors
├── exporter.py           # HTTP /metrics endpoint
├── otlp.py               # OpenTelemetry/Grafana Alloy export
└── dashboards/           # Pre-built Grafana dashboards
    ├── overview.json     # OTA session overview
    ├── apdu_analysis.json # APDU command analysis
    └── errors.json       # Error rate monitoring
```

### Metrics Architecture
```python
# cardlink/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# APDU Metrics
apdu_commands_total = Counter(
    'cardlink_apdu_commands_total',
    'Total APDU commands sent',
    ['command_type', 'device_id', 'card_iccid']
)

apdu_responses_total = Counter(
    'cardlink_apdu_responses_total',
    'Total APDU responses received',
    ['status_word', 'device_id', 'card_iccid']
)

apdu_duration_seconds = Histogram(
    'cardlink_apdu_duration_seconds',
    'APDU command/response latency',
    ['command_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Session Metrics
sessions_active = Gauge(
    'cardlink_sessions_active',
    'Currently active OTA sessions'
)

sessions_total = Counter(
    'cardlink_sessions_total',
    'Total OTA sessions',
    ['status']  # success, failed, timeout
)

# TLS Metrics
tls_handshakes_total = Counter(
    'cardlink_tls_handshakes_total',
    'TLS handshake count',
    ['result', 'cipher_suite']
)

# Device Metrics
device_connections = Gauge(
    'cardlink_device_connections',
    'Connected devices',
    ['device_type']  # phone, modem
)
```

### Integration Patterns

#### Prometheus Scraping
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cardlink'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

#### Grafana Alloy Configuration
```river
// alloy config
prometheus.scrape "cardlink" {
  targets = [{"__address__" = "localhost:9090"}]
  forward_to = [prometheus.remote_write.default.receiver]
}

// Or via OTLP
otelcol.receiver.otlp "default" {
  grpc { endpoint = "0.0.0.0:4317" }
  http { endpoint = "0.0.0.0:4318" }
  output {
    metrics = [otelcol.exporter.prometheus.default.input]
  }
}
```

### Collector Pattern
```python
# cardlink/observability/collectors.py
class APDUMetricsCollector:
    """Collect metrics from APDU exchanges."""

    def record_command(self, command: APDUCommand, device_id: str, iccid: str):
        """Record outgoing APDU command."""
        apdu_commands_total.labels(
            command_type=command.ins_name,
            device_id=device_id,
            card_iccid=iccid
        ).inc()

    def record_response(self, response: APDUResponse, device_id: str, iccid: str, duration: float):
        """Record APDU response with timing."""
        apdu_responses_total.labels(
            status_word=response.sw_hex,
            device_id=device_id,
            card_iccid=iccid
        ).inc()
        apdu_duration_seconds.labels(
            command_type=response.command_type
        ).observe(duration)
```

### Pre-built Grafana Dashboards
| Dashboard | Purpose | Panels |
|-----------|---------|--------|
| `overview.json` | OTA session monitoring | Active sessions, success rate, throughput |
| `apdu_analysis.json` | Command analysis | Command distribution, latency percentiles, error breakdown |
| `errors.json` | Error monitoring | Error rates, failed sessions, timeout tracking |

## Docker Deployment Structure

### Docker Files Organization
```
cardlink/
├── docker/
│   ├── Dockerfile              # Production multi-stage build
│   ├── Dockerfile.dev          # Development with hot reload
│   └── .dockerignore           # Exclude unnecessary files
├── docker-compose.yml          # Main orchestration file
├── monitoring/
│   ├── prometheus.yml          # Prometheus configuration
│   ├── alloy-config.river      # Grafana Alloy configuration
│   └── grafana/
│       └── provisioning/
│           ├── dashboards/
│           │   ├── dashboard.yml
│           │   └── cardlink/
│           │       ├── overview.json
│           │       ├── apdu_analysis.json
│           │       └── errors.json
│           └── datasources/
│               └── datasource.yml
└── config/
    ├── cardlink.yaml.example   # Server configuration template
    └── .env.example            # Environment variables template
```

### Dockerfile Structure
```dockerfile
# docker/Dockerfile
# Multi-stage build for smaller production image

# Stage 1: Build
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Stage 2: Production
FROM python:3.11-slim AS production
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    libpcsclite1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create non-root user
RUN useradd -m -u 1000 cardlink
USER cardlink

# Create directories
RUN mkdir -p /home/cardlink/data /home/cardlink/config

# Environment
ENV DATABASE_URL=sqlite:////home/cardlink/data/cardlink.db
ENV CARDLINK_LOG_LEVEL=INFO

# Ports
EXPOSE 8443 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Entry point
ENTRYPOINT ["cardlink-server"]
CMD ["start", "--dashboard", "--metrics"]
```

### Docker Compose Profiles
| Profile | Services | Use Case |
|---------|----------|----------|
| (default) | cardlink-server | Server-only deployment |
| `production` | + postgres | Production with PostgreSQL |
| `monitoring` | + prometheus, grafana, alloy | Full observability stack |

### Volume Strategy
| Volume | Purpose | Mount Point |
|--------|---------|-------------|
| `cardlink-data` | Database and logs | `/home/cardlink/data` |
| `postgres-data` | PostgreSQL data | `/var/lib/postgresql/data` |
| `prometheus-data` | Metrics storage | `/prometheus` |
| `grafana-data` | Grafana config | `/var/lib/grafana` |

### Network Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    cardlink-network                      │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │   cardlink   │    │   postgres   │                   │
│  │   server     │───▶│   (optional) │                   │
│  │  :8443/:8080 │    │    :5432     │                   │
│  │    /:9090    │    └──────────────┘                   │
│  └──────┬───────┘                                       │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  prometheus  │───▶│   grafana    │                   │
│  │   :9091      │    │    :3000     │                   │
│  └──────────────┘    └──────────────┘                   │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │    alloy     │                                       │
│  │ :4317/:4318  │                                       │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

### Configuration Files

#### config/cardlink.yaml.example
```yaml
# CardLink Server Configuration
server:
  host: 0.0.0.0
  port: 8443
  dashboard_port: 8080

database:
  url: ${DATABASE_URL:-sqlite:///data/cardlink.db}
  pool_size: 5

monitoring:
  enabled: true
  port: 9090
  otlp:
    enabled: false
    endpoint: ""

logging:
  level: ${CARDLINK_LOG_LEVEL:-INFO}
  format: json
```

#### config/.env.example
```bash
# Database
DATABASE_URL=sqlite:///data/cardlink.db
# DATABASE_URL=postgresql://cardlink:password@postgres:5432/cardlink

# Server
CARDLINK_LOG_LEVEL=INFO
SERVER_PORT=8443
DASHBOARD_PORT=8080
METRICS_PORT=9090

# Monitoring
METRICS_ENABLED=true
OTLP_ENDPOINT=

# Production PostgreSQL
DB_PASSWORD=changeme

# Grafana
GRAFANA_PASSWORD=admin
```

### Deployment Patterns

#### Development (Hot Reload)
```yaml
# docker-compose.override.yml
services:
  cardlink-server:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    volumes:
      - ./src:/app/src:ro
    environment:
      - CARDLINK_LOG_LEVEL=DEBUG
```

#### Production (External Database)
```yaml
# docker-compose.prod.yml
services:
  cardlink-server:
    environment:
      - DATABASE_URL=postgresql://cardlink:${DB_PASSWORD}@postgres:5432/cardlink
    depends_on:
      postgres:
        condition: service_healthy
```

## Documentation Standards

- All public classes and functions must have docstrings (Google style)
- Complex algorithms should include inline comments
- Each package should have a README explaining its purpose
- Type hints required for all public APIs

### Docstring Example
```python
def send_apdu(self, command: APDUCommand, timeout: int = 30) -> APDUResponse:
    """
    Send an APDU command to the UICC.

    Args:
        command: The APDU command to transmit.
        timeout: Maximum time to wait for response in seconds.

    Returns:
        APDUResponse containing status word and response data.

    Raises:
        ConnectionError: If not connected to device.
        TimeoutError: If response not received within timeout.

    Example:
        >>> cmd = APDUCommand(cla=0x00, ins=0xA4, p1=0x04, p2=0x00)
        >>> response = controller.send_apdu(cmd)
        >>> print(response.sw)
        '9000'
    """
```
