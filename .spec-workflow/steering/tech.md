# Technology Stack

## Project Type
**CardLink** - A CLI tool with integrated web dashboard for GlobalPlatform SCP81 UICC OTA testing. The platform provides server simulation, device control (mobile phones and IoT modems), smart card provisioning, network simulator integration, database-backed configuration management, and automated test execution capabilities.

## Core Technologies

### Primary Language(s)
- **Language**: Python 3.9+
- **Runtime**: CPython
- **Language-specific tools**: pip, venv, setuptools

### Key Dependencies/Libraries

| Library | Purpose | Version |
|---------|---------|---------|
| **sslpsk3** | PSK-TLS support for secure UICC communication | Latest |
| **pyscard** | PC/SC smart card interface for UICC provisioning | Latest |
| **click** | CLI framework for command-line interface | Latest |
| **pytest** | Testing framework for unit/integration/E2E tests | Latest |
| **pyyaml** | YAML configuration parsing | Latest |
| **aiohttp** or **Flask** | Web server for dashboard backend | Latest |
| **websockets** | Real-time communication for dashboard | Latest |
| **SQLAlchemy** | ORM for database operations | 2.0+ |
| **alembic** | Database migration management | Latest |
| **pydantic** | Data validation and schemas | 2.0+ |
| **prometheus-client** | Metrics export for Prometheus/Grafana | Latest |
| **opentelemetry-api** | Distributed tracing and observability | Latest |

### Application Architecture
The application follows a modular, layered architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                   │
│  (cardlink-server, cardlink-phone, cardlink-modem,                      │
│   cardlink-provision, cardlink-test)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                           Frontend Layer                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Web Dashboard                               │    │
│  │  - OTA Activity Management (sessions, scripts, triggers)         │    │
│  │  - TLS Handshake Monitor (PSK negotiation, cipher info)          │    │
│  │  - Real-time APDU Communication Log                              │    │
│  │  - Manual RAM Command Interface                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                           Service Layer                                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐               │
│  │AdminServer│ │DeviceCtrl │ │UICCProvisi│ │NetworkSim │               │
│  │(PSK-TLS)  │ │(Phone/IoT)│ │           │ │Integration│               │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘               │
├─────────────────────────────────────────────────────────────────────────┤
│                         Observability Layer                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Metrics & Monitoring (Prometheus / Grafana Alloy)               │    │
│  │  - APDU command/response metrics    - Session statistics         │    │
│  │  - TLS handshake metrics            - Error rates & latencies    │    │
│  │  - Device connection status         - Test execution metrics     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                            Data Layer                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Database (SQLite/MySQL/PostgreSQL)                              │    │
│  │  - Device configurations    - Test results                       │    │
│  │  - UICC card profiles       - Communication logs                 │    │
│  │  - Session records          - Server settings                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                           Protocol Layer                                 │
│  (APDU, TLV, GP Commands, SMS PDU, BIP Commands, AT Commands)           │
└─────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    External Monitoring (Optional)                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │
│  │  Prometheus   │  │ Grafana Alloy │  │    Grafana    │               │
│  │  (Scraping)   │  │  (Collection) │  │ (Dashboards)  │               │
│  └───────────────┘  └───────────────┘  └───────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

- **CLI Layer**: User-facing commands using Click framework (`cardlink-*` commands)
- **Frontend Layer**: Web-based dashboard for OTA activity management, TLS handshake monitoring, and manual RAM command execution
- **Service Layer**: Core business logic for server, device control (phones + IoT modems), provisioning, and network simulator integration
- **Observability Layer**: Metrics export and monitoring integration with Prometheus/Grafana Alloy for communication analysis
- **Data Layer**: Database-backed storage using SQLAlchemy ORM with repository pattern for configurations, sessions, logs, and test results
- **Protocol Layer**: Low-level protocol implementations (APDU, TLV, GP commands, AT commands)

### Data Storage
- **Primary storage**: Relational database (SQLite3 default, MySQL/PostgreSQL optional)
- **Database Features**:
  - Device configurations (phones, modems)
  - UICC card profiles (PSK keys, admin URLs)
  - OTA session records and history
  - Communication logs (APDU exchanges)
  - Test results and execution history
  - Server configuration settings
- **Caching**: In-memory session state for active connections
- **Data formats**:
  - Database tables for persistent configuration and logs
  - YAML for test suite definitions and templates
  - JSON for API responses and exports
  - Binary for APDU/TLV data

### Database Configuration
```python
# Default: SQLite (no setup required)
DATABASE_URL = "sqlite:///data/cardlink.db"

# MySQL (for multi-user production)
DATABASE_URL = "mysql://user:pass@host:3306/cardlink"

# PostgreSQL (for enterprise deployments)
DATABASE_URL = "postgresql://user:pass@host:5432/cardlink"
```

### External Integrations
- **APIs**:
  - ADB (Android Debug Bridge) for Android phone control
  - PC/SC for smart card reader access
  - QXDM integration for Qualcomm-based IoT modem diagnostics
- **Protocols**:
  - PSK-TLS 1.2 for UICC communication
  - HTTP/HTTPS for Admin Server protocol
  - AT commands for modem interface (phones and IoT modules)
  - SMS-PP PDU for trigger messages
  - WebSocket for network simulator integration
  - TCP/IP for network simulator connectivity
- **Network Simulator Integration**:
  - Amarisoft LTE/5G network simulator support
  - WebSocket-based real-time communication
  - TCP/IP fallback connectivity
  - Simulated network event triggers
- **Authentication**: PSK (Pre-Shared Key) for TLS sessions

### Target Device Support
- **Mobile Phones**:
  - Android 8.0+ smartphones via ADB
  - USB debugging interface
  - Tested models: Google Pixel, Samsung Galaxy, OnePlus
- **IoT Modems**:
  - Quectel RG500Q-EU (5G)
  - Quectel EG25-G (LTE Cat 4)
  - Other AT command compatible modems
  - USB/Serial interface
  - QXDM diagnostic tool integration for Qualcomm chipsets

### Monitoring & Dashboard Technologies
- **Dashboard Framework**: Lightweight web framework (Flask/aiohttp) with vanilla JS or minimal frontend
- **Real-time Communication**: WebSocket for live APDU streaming, TLS events, and network simulator updates
- **Visualization**:
  - TLS handshake monitor (PSK identity, cipher suite, session info)
  - APDU communication log with hex/decoded views
  - OTA session management interface
  - Network simulator status panel
- **State Management**: Server-side session state, WebSocket push for updates
- **Interactive Features**:
  - Manual RAM command builder and executor
  - Script queue management
  - Trigger controls (SMS-PP, event-based)
  - TLS session inspection

### External Monitoring Integration (Prometheus / Grafana Alloy)
- **Metrics Endpoint**: `/metrics` endpoint exposing Prometheus-format metrics
- **Supported Collectors**:
  - Prometheus (direct scraping)
  - Grafana Alloy (OpenTelemetry-based collection)
  - Any OpenTelemetry-compatible collector
- **Exported Metrics**:
  | Metric | Type | Description |
  |--------|------|-------------|
  | `cardlink_apdu_commands_total` | Counter | Total APDU commands sent by type (SELECT, GET STATUS, etc.) |
  | `cardlink_apdu_responses_total` | Counter | Total APDU responses by status word (9000, 6A82, etc.) |
  | `cardlink_apdu_duration_seconds` | Histogram | APDU command/response latency |
  | `cardlink_sessions_total` | Counter | Total OTA sessions by status (success, failed, timeout) |
  | `cardlink_sessions_active` | Gauge | Currently active OTA sessions |
  | `cardlink_tls_handshakes_total` | Counter | TLS handshake count by result |
  | `cardlink_tls_handshake_duration_seconds` | Histogram | TLS handshake latency |
  | `cardlink_device_connections` | Gauge | Connected devices by type (phone, modem) |
  | `cardlink_test_executions_total` | Counter | Test executions by result |
  | `cardlink_bytes_transferred_total` | Counter | Total bytes sent/received |
- **Labels**: All metrics include labels for `device_id`, `card_iccid`, `session_id` for filtering
- **Configuration**:
  ```yaml
  # Enable metrics endpoint
  monitoring:
    enabled: true
    port: 9090
    path: /metrics

  # Grafana Alloy / OpenTelemetry export
  otlp:
    enabled: true
    endpoint: "http://alloy:4317"
    protocol: grpc  # or http
  ```
- **Grafana Dashboard**: Pre-built dashboard templates for:
  - OTA session overview
  - APDU command analysis
  - Error rate monitoring
  - Device connectivity status
  - Test execution trends

## Development Environment

### Build & Development Tools
- **Build System**: setuptools with pyproject.toml
- **Package Management**: pip with virtual environments (venv)
- **Development workflow**:
  - Editable install (`pip install -e ".[dev,pcsc]"`)
  - Hot reload for dashboard development
  - pytest watch mode for TDD

### Code Quality Tools
- **Static Analysis**: mypy for type checking, pylint/flake8 for linting
- **Formatting**: black for code formatting, isort for import sorting
- **Testing Framework**:
  - pytest for all test types
  - pytest-cov for coverage
  - pytest-asyncio for async tests
- **Documentation**: Sphinx or mkdocs for API documentation

### Version Control & Collaboration
- **VCS**: Git
- **Branching Strategy**: GitHub Flow (feature branches, main branch)
- **Code Review Process**: Pull requests with required reviews

### Dashboard Development
- **Live Reload**: Browser auto-refresh or WebSocket-based updates
- **Port Management**: Configurable port (default 8080 for dashboard, 8443 for PSK-TLS server)
- **Multi-Instance Support**: Single dashboard instance per server

## Deployment & Distribution

### Deployment Strategies
CardLink supports two deployment strategies to accommodate different environments and use cases:

#### 1. Native Deployment (Recommended for Device Access)
Direct installation on host machine, required when USB device access is needed.

- **Target Platform(s)**: Linux, macOS, Windows (desktop/laptop with USB)
- **Distribution Method**: PyPI package installation via pip
- **Installation Requirements**:
  - Python 3.9+
  - ADB (Android SDK Platform Tools) - for phone control
  - PC/SC Lite (pcscd on Linux) - for card provisioning
  - OpenSSL 1.1.1+
  - USB connection to target device (phone or IoT modem)
  - PC/SC smart card reader (for provisioning)
  - Serial/USB drivers for IoT modems (if applicable)
  - QXDM license (optional, for Qualcomm modem diagnostics)
- **Update Mechanism**: pip upgrade
- **Best For**: Full functionality including phone/modem control and card provisioning

#### 2. Docker Deployment (Recommended for Server-Only Mode)
Containerized deployment for the Admin Server and Dashboard components.

- **Base Image**: `python:3.11-slim`
- **Container Components**:
  - CardLink Admin Server (PSK-TLS)
  - Web Dashboard
  - Metrics endpoint (Prometheus)
  - Database (SQLite embedded or external MySQL/PostgreSQL)
- **Exposed Ports**:
  | Port | Service |
  |------|---------|
  | 8443 | PSK-TLS Admin Server |
  | 8080 | Web Dashboard |
  | 9090 | Prometheus Metrics |
- **Volume Mounts**:
  - `/data` - Database and logs persistence
  - `/config` - Configuration files
- **Best For**: Server-only deployments, CI/CD pipelines, cloud environments

### Docker Configuration

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    libpcsclite1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install CardLink
COPY . .
RUN pip install --no-cache-dir -e ".[server,monitoring]"

# Create data directory
RUN mkdir -p /data /config

# Expose ports
EXPOSE 8443 8080 9090

# Environment variables
ENV DATABASE_URL=sqlite:////data/cardlink.db
ENV CARDLINK_CONFIG=/config/cardlink.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["cardlink-server", "start", "--dashboard", "--metrics"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  cardlink-server:
    build: .
    image: cardlink:latest
    container_name: cardlink-server
    ports:
      - "8443:8443"   # PSK-TLS Admin Server
      - "8080:8080"   # Web Dashboard
      - "9090:9090"   # Prometheus Metrics
    volumes:
      - cardlink-data:/data
      - ./config:/config:ro
    environment:
      - DATABASE_URL=sqlite:////data/cardlink.db
      - CARDLINK_LOG_LEVEL=INFO
      - METRICS_ENABLED=true
    restart: unless-stopped
    networks:
      - cardlink-network

  # Optional: PostgreSQL for production
  postgres:
    image: postgres:15-alpine
    container_name: cardlink-db
    environment:
      - POSTGRES_DB=cardlink
      - POSTGRES_USER=cardlink
      - POSTGRES_PASSWORD=${DB_PASSWORD:-changeme}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - cardlink-network
    profiles:
      - production

  # Optional: Prometheus for metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: cardlink-prometheus
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - cardlink-network
    profiles:
      - monitoring

  # Optional: Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: cardlink-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    networks:
      - cardlink-network
    profiles:
      - monitoring

  # Optional: Grafana Alloy for advanced collection
  alloy:
    image: grafana/alloy:latest
    container_name: cardlink-alloy
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    volumes:
      - ./monitoring/alloy-config.river:/etc/alloy/config.river:ro
    command:
      - run
      - /etc/alloy/config.river
    networks:
      - cardlink-network
    profiles:
      - monitoring

volumes:
  cardlink-data:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  cardlink-network:
    driver: bridge
```

### Deployment Commands

#### Native Deployment
```bash
# Install from PyPI
pip install cardlink

# Or install from source
pip install -e ".[full]"

# Start server with dashboard
cardlink-server start --dashboard --metrics
```

#### Docker Deployment
```bash
# Build and start (server only)
docker-compose up -d cardlink-server

# Start with PostgreSQL database
docker-compose --profile production up -d

# Start with full monitoring stack
docker-compose --profile monitoring up -d

# Start everything
docker-compose --profile production --profile monitoring up -d

# View logs
docker-compose logs -f cardlink-server

# Stop all services
docker-compose down
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:////data/cardlink.db` | Database connection string |
| `CARDLINK_CONFIG` | `/config/cardlink.yaml` | Configuration file path |
| `CARDLINK_LOG_LEVEL` | `INFO` | Logging level |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `METRICS_PORT` | `9090` | Metrics endpoint port |
| `DASHBOARD_PORT` | `8080` | Dashboard port |
| `SERVER_PORT` | `8443` | PSK-TLS server port |
| `OTLP_ENDPOINT` | `` | OpenTelemetry collector endpoint |

## Technical Requirements & Constraints

### Performance Requirements
- **Test cycle time**: Sub-5-second end-to-end test execution
- **Server response**: Handle mobile network latency (60s socket timeout, 300s session timeout)
- **Dashboard updates**: Real-time (<100ms latency for WebSocket updates)
- **Memory**: Reasonable memory footprint for long-running server sessions

### Compatibility Requirements
- **Platform Support**:
  - Linux (Ubuntu 20.04+, Debian 11+)
  - macOS (10.15+)
  - Windows 10/11
- **Target Device Support**:
  - Android 8.0+ smartphones with USB debugging enabled
  - Quectel RG500Q-EU, EG25-G and compatible IoT modems
  - Any AT command compatible cellular modem
- **Network Simulator Support**:
  - Amarisoft Callbox (LTE/5G)
  - WebSocket API compatibility
- **Dependency Versions**:
  - Python 3.9 minimum
  - OpenSSL 1.1.1+ for PSK-TLS support
- **Standards Compliance**:
  - GlobalPlatform Card Spec v2.2 Amendment B (SCP81)
  - 3GPP TS 23.040 (SMS PDU)
  - 3GPP TS 102 223 (BIP/CAT)
  - 3GPP TS 102 225 (OTA Command Packets)
  - 3GPP TS 27.007 (AT Command Set for modems)

### Security & Compliance
- **Security Requirements**:
  - PSK-TLS for all UICC communication
  - Secure key handling (no plaintext key storage in logs)
  - ADM key protection for card provisioning
- **Compliance Standards**: GlobalPlatform certification compatibility
- **Threat Model**: Local testing environment (trusted network assumption)

### Scalability & Reliability
- **Expected Load**: Single device testing (v1.0), multi-device future
- **Availability Requirements**: Development/testing tool, no uptime requirements
- **Growth Projections**: Multi-phone parallel testing in future versions

## Technical Decisions & Rationale

### Decision Log

1. **Python 3.9+**: Chosen for rapid development, excellent library ecosystem (pyscard, sslpsk3), and cross-platform support. Trade-off: slower than native code, acceptable for test tool.

2. **PSK-TLS via sslpsk3**: Required for SCP81 compliance. Standard TLS libraries don't support PSK cipher suites natively.

3. **ADB for Phone Control**: Universal Android debugging interface, no root required for basic operations. Trade-off: Some AT command features may need root.

4. **AT Commands for IoT Modems**: Direct serial/USB communication with modems like Quectel. More reliable than ADB for dedicated cellular modules.

5. **PC/SC for Card Provisioning**: Industry-standard smart card interface. Allows same card reader to work across platforms.

6. **SQLAlchemy + Repository Pattern**: Database-backed storage for configurations, sessions, and logs. Supports SQLite (default), MySQL, and PostgreSQL. Repository pattern provides clean data access layer.

7. **WebSocket for Dashboard & Network Simulator**: Real-time bidirectional communication for live APDU streaming, TLS monitoring, and network simulator integration without polling overhead.

8. **Click for CLI**: Mature, well-documented CLI framework with good support for complex command hierarchies.

9. **Amarisoft Integration**: Industry-standard network simulator with well-documented WebSocket/TCP API. Enables controlled network environment testing.

10. **QXDM Integration**: Essential for debugging Qualcomm-based IoT modems. Provides low-level diagnostic access for troubleshooting BIP/CAT issues.

11. **Prometheus/Grafana Alloy Integration**: Industry-standard monitoring stack for metrics collection and visualization. Enables long-term communication analysis, trend identification, and alerting on anomalies. OpenTelemetry support ensures compatibility with modern observability platforms.

12. **Docker + Native Dual Deployment**: Support both containerized and native deployments. Docker for server-only mode (CI/CD, cloud), native for full device access. Docker Compose profiles enable flexible stack composition (server-only, with database, with monitoring).

## Known Limitations

- **AT Command Access**: Some phones restrict modem access without root. Document tested phone models.
- **BIP Support Varies**: Not all Android versions/phones handle BIP consistently. Fallback mechanisms needed.
- **No iOS Support (v1.0)**: iOS restrictions prevent ADB-style control. Future enhancement.
- **Single Device Focus (v1.0)**: Parallel testing deferred to future version.
- **PSK-TLS Library**: sslpsk3 may have platform-specific issues. Test thoroughly on all target platforms.
- **IoT Modem Variations**: Different modem firmware versions may have varying AT command support. Document tested firmware versions.
- **QXDM License Required**: QXDM diagnostic tool requires Qualcomm license. Optional but recommended for Qualcomm-based modems.
- **Network Simulator Cost**: Amarisoft requires commercial license. Integration designed to be optional.
- **Docker USB Limitations**: Docker containers cannot directly access USB devices without privileged mode or device passthrough. Use native deployment for phone/modem control and card provisioning.
