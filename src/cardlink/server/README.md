# PSK-TLS Admin Server

This module provides a PSK-TLS server implementation for GlobalPlatform SCP81 Over-The-Air (OTA) UICC administration testing.

## Overview

The PSK-TLS Admin Server implements the GlobalPlatform Amendment B specification for Remote Application Management (RAM) over HTTP, using TLS 1.2 with Pre-Shared Key (PSK) authentication.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AdminServer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ TLSHandler  │  │SessionMgr   │  │  GPCommandProcessor │ │
│  │             │  │             │  │  ┌───────────────┐  │ │
│  │ PSK-TLS 1.2 │  │ State       │  │  │ SelectHandler │  │ │
│  │ Handshake   │  │ Tracking    │  │  │ InstallHandler│  │ │
│  │             │  │             │  │  │ DeleteHandler │  │ │
│  └─────────────┘  └─────────────┘  │  │ GetStatusHdlr │  │ │
│                                     │  └───────────────┘  │ │
│  ┌─────────────┐  ┌─────────────┐  └─────────────────────┘ │
│  │ HTTPHandler │  │ErrorHandler │                           │
│  │             │  │             │  ┌─────────────────────┐ │
│  │ GP Admin    │  │ Mismatch    │  │   EventEmitter      │ │
│  │ Protocol    │  │ Tracking    │  │   (pub/sub)         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Components

### AdminServer
Main server class that orchestrates all components and manages the server lifecycle.

### TLSHandler
Handles PSK-TLS 1.2 connection establishment using the sslpsk3 library.

### SessionManager
Manages OTA session lifecycle with state machine: HANDSHAKING → CONNECTED → ACTIVE → CLOSED.

### HTTPHandler
Parses HTTP requests according to GP Amendment B Admin protocol.

### GPCommandProcessor
Processes GlobalPlatform APDU commands with pluggable handlers.

### ErrorHandler
Centralized error handling with PSK mismatch tracking and error rate monitoring.

### EventEmitter
Thread-safe pub/sub system for real-time monitoring and dashboard integration.

## Quick Start

```python
from cardlink.server import (
    AdminServer,
    EventEmitter,
    FileKeyStore,
    ServerConfig,
)

# Configure server
config = ServerConfig(
    host="127.0.0.1",
    port=8443,
    session_timeout=300.0,
)

# Load PSK keys
key_store = FileKeyStore("keys.yaml")

# Create event emitter for monitoring
emitter = EventEmitter()

# Create and start server
server = AdminServer(config, key_store, emitter)
server.start()

# Server runs in background
print(f"Active sessions: {server.get_session_count()}")

# Stop when done
server.stop()
```

## CLI Usage

```bash
# Start server with defaults
gp-ota-server start

# Start on custom port with config file
gp-ota-server start --port 9443 --config server.yaml

# Start with verbose logging
gp-ota-server -v start --foreground

# Stop server
gp-ota-server stop

# Check status
gp-ota-server status
```

## Cipher Suites

The server supports the following PSK cipher suites:

### Production (Default)
- TLS_PSK_WITH_AES_128_CBC_SHA256
- TLS_PSK_WITH_AES_256_CBC_SHA384

### Legacy (Optional)
- TLS_PSK_WITH_AES_128_CBC_SHA
- TLS_PSK_WITH_AES_256_CBC_SHA

### Testing Only (Disabled by default)
- TLS_PSK_WITH_NULL_SHA (NO ENCRYPTION)
- TLS_PSK_WITH_NULL_SHA256 (NO ENCRYPTION)

## Event Types

The server emits the following events for monitoring:

| Event | Description |
|-------|-------------|
| server_started | Server has started listening |
| server_stopped | Server has stopped |
| session_started | New client session established |
| session_ended | Client session closed |
| handshake_completed | TLS handshake completed successfully |
| handshake_failed | TLS handshake failed |
| apdu_received | APDU command received from client |
| apdu_sent | APDU response sent to client |
| psk_mismatch | PSK authentication failed |
| connection_interrupted | Connection unexpectedly interrupted |
| high_error_rate | Error rate threshold exceeded |

## Supported GP Commands

| INS | Command | Description |
|-----|---------|-------------|
| 0xA4 | SELECT | Select application by AID |
| 0xE6 | INSTALL | Install applet/package |
| 0xE4 | DELETE | Delete application |
| 0xF2 | GET STATUS | Get card content status |
| 0x50 | INITIALIZE UPDATE | Start secure channel |
| 0x82 | EXTERNAL AUTHENTICATE | Complete secure channel |

## Security Considerations

1. **PSK Key Security**: Keys are never logged. Only identity strings may appear in logs.

2. **NULL Ciphers**: NULL cipher suites provide NO ENCRYPTION and should only be enabled for debugging in isolated environments.

3. **Mismatch Tracking**: Multiple PSK mismatches from the same IP are tracked and logged as potential brute-force attempts.

4. **Session Timeouts**: Sessions automatically expire after the configured timeout to prevent resource exhaustion.

## Requirements

- Python 3.9+
- sslpsk3 library for PSK-TLS support

Install with:
```bash
pip install gp-ota-tester[server]
```
