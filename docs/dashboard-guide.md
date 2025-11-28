# GP OTA Tester Dashboard User Guide

Web-based dashboard for real-time APDU monitoring and test session management.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [CLI Commands](#cli-commands)
5. [Dashboard Interface](#dashboard-interface)
6. [Features](#features)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [WebSocket Events](#websocket-events)
10. [Integration](#integration)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The GP OTA Tester Dashboard provides a web-based interface for:

- **Real-time APDU Monitoring**: View command/response traffic as it happens
- **Session Management**: Create, monitor, and manage test sessions
- **Command Builder**: Construct and send APDU commands visually
- **Log Export**: Export APDU logs in JSON, CSV, or text format
- **Dark/Light Theme**: Support for both light and dark modes

The dashboard connects to a backend server via WebSocket for real-time updates and REST API for data operations.

---

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Modern Web Browser**: Chrome, Firefox, Safari, or Edge (latest versions)

### Dependencies

The dashboard requires the `rich` library for CLI output:

```bash
pip install rich
```

Or install with the full package:

```bash
pip install -e ".[all]"
```

---

## Quick Start

### 1. Start the Dashboard Server

```bash
# Start with default settings (localhost:8080)
gp-dashboard start

# Start on specific host and port
gp-dashboard start --host 0.0.0.0 --port 3000

# Start and automatically open in browser
gp-dashboard start --open
```

### 2. Access the Dashboard

Open your web browser and navigate to:

```
http://localhost:8080
```

### 3. Connect to Test Sessions

The dashboard will automatically connect via WebSocket and display available test sessions. Select a session to view its APDU traffic.

---

## CLI Commands

### gp-dashboard

Main command group for dashboard operations.

```bash
gp-dashboard [OPTIONS] COMMAND [ARGS]
```

**Global Options:**

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output with debug logging |

### gp-dashboard start

Start the dashboard web server.

```bash
gp-dashboard start [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-h, --host` | `127.0.0.1` | Host address to bind to |
| `-p, --port` | `8080` | Port to bind to |
| `--open` | `false` | Open browser automatically after starting |

**Examples:**

```bash
# Start on localhost (default)
gp-dashboard start

# Start accessible from other machines
gp-dashboard start --host 0.0.0.0

# Start on custom port with auto-open
gp-dashboard start --port 3000 --open

# Start with verbose logging
gp-dashboard -v start
```

### gp-dashboard status

Check if the dashboard server is running.

```bash
gp-dashboard status [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-h, --host` | `127.0.0.1` | Dashboard host to check |
| `-p, --port` | `8080` | Dashboard port to check |

**Example:**

```bash
$ gp-dashboard status

Dashboard is running
URL: http://127.0.0.1:8080
Sessions: 2
Clients: 1
```

### gp-dashboard open-browser

Open the dashboard in your default web browser.

```bash
gp-dashboard open-browser [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-h, --host` | `127.0.0.1` | Dashboard host |
| `-p, --port` | `8080` | Dashboard port |

---

## Dashboard Interface

### Header

The header contains:

- **Logo and Title**: GP OTA Tester branding
- **Connection Status**: Shows WebSocket connection state
  - Green: Connected
  - Yellow: Connecting/Reconnecting
  - Red: Disconnected
- **Settings Button**: Opens settings modal
- **Theme Toggle**: Switch between light and dark modes

### Session Panel (Left Sidebar)

Displays all active test sessions:

- **Session List**: Click to select a session and view its APDU log
- **Refresh Button**: Manually refresh the session list
- **Session Status**: Shows session state (idle, active, completed)

### APDU Log (Main Content)

The central area shows APDU traffic for the selected session:

- **Search Bar**: Filter APDUs by content (Ctrl+F for quick access)
- **Direction Filter**: Show all, commands only, or responses only
- **Status Filter**: Filter by response status (success, warning, error)
- **Entry Count**: Shows number of entries (filtered/total)
- **Export Button**: Export logs to file
- **Clear Button**: Clear current log display
- **Auto-Scroll Toggle**: Enable/disable automatic scrolling to new entries

**APDU Entry Display:**

Each APDU entry shows:
- Timestamp
- Direction indicator (>> for command, << for response)
- Hex data
- Status Word (SW) for responses with color coding:
  - Green (90XX): Success
  - Yellow (61XX, 6CXX): Warning/Info
  - Red (6XXX, other): Error

### Command Builder (Bottom Panel)

Visual APDU command builder with:

- **CLA/INS/P1/P2/Le Fields**: Enter command header bytes
- **Data Field**: Optional command data (hex)
- **Preview**: Shows the complete APDU being constructed
- **Template Buttons**: Quick templates for common commands:
  - SELECT
  - GET STATUS
  - GET DATA
- **Clear/Send Buttons**: Reset form or send command

---

## Features

### Real-Time Updates

The dashboard uses WebSocket for real-time updates:

- New APDUs appear instantly
- Session status changes update automatically
- Connection state is monitored with auto-reconnect

### Virtual Scrolling

The APDU log uses virtual scrolling for performance:

- Handles thousands of entries efficiently
- Smooth scrolling even with large datasets
- Memory-efficient rendering

### Export Formats

Export APDU logs in multiple formats:

**JSON:**
```json
[
  {
    "id": "abc123",
    "timestamp": 1699999999000,
    "direction": "command",
    "data": "00A4040007A0000000041010",
    "sw": null
  },
  {
    "id": "abc124",
    "timestamp": 1699999999100,
    "direction": "response",
    "data": "6F10840E315041592E5359532E4444463031",
    "sw": "9000"
  }
]
```

**CSV:**
```csv
timestamp,direction,data,sw
2024-01-15T10:30:00.000Z,command,00A4040007A0000000041010,
2024-01-15T10:30:00.100Z,response,6F10840E315041592E5359532E4444463031,9000
```

**Text:**
```
[2024-01-15T10:30:00.000Z] >> 00A4040007A0000000041010
[2024-01-15T10:30:00.100Z] << 6F10840E315041592E5359532E4444463031 [9000]
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` / `Cmd+F` | Focus search input |
| `Escape` | Clear search / Close modal |

### Theme Support

The dashboard supports light and dark themes:

- Toggle via the theme button in the header
- Preference is saved in browser local storage
- Respects system preference on first visit

---

## Configuration

### Settings Modal

Access via the settings button in the header:

**Connection Settings:**
- **WebSocket URL**: Server WebSocket endpoint
- **Auto-reconnect**: Automatically reconnect on disconnect

**Display Settings:**
- **Show timestamps**: Display timestamps for each entry
- **Highlight errors**: Visual highlighting for error responses
- **Group pairs**: Group command/response pairs together

**Alert Settings:**
- **Alert Patterns**: SW codes that trigger alerts (one per line)
- **Sound Alerts**: Play sound when alert pattern is matched

### Local Storage

Settings are persisted in browser local storage:

```javascript
// Storage key
'gp-ota-dashboard-settings'

// Stored values
{
  theme: 'light' | 'dark',
  wsUrl: 'ws://localhost:8080/ws',
  autoReconnect: true,
  showTimestamps: true,
  highlightErrors: true,
  groupPairs: true,
  alertPatterns: ['6A82', '6D00'],
  soundAlerts: false
}
```

---

## API Reference

### REST Endpoints

The dashboard server provides REST API endpoints:

#### Sessions

**GET /api/sessions**

Get all sessions.

```bash
curl http://localhost:8080/api/sessions
```

Response:
```json
[
  {
    "id": "session-uuid",
    "name": "Test Session 1",
    "status": "active",
    "createdAt": "2024-01-15T10:00:00.000Z",
    "updatedAt": "2024-01-15T10:30:00.000Z",
    "apduCount": 42,
    "metadata": {}
  }
]
```

**POST /api/sessions**

Create a new session.

```bash
curl -X POST http://localhost:8080/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "My Test Session"}'
```

**GET /api/sessions/{id}**

Get a specific session.

**PATCH /api/sessions/{id}**

Update a session.

**DELETE /api/sessions/{id}**

Delete a session.

#### APDUs

**GET /api/sessions/{id}/apdus**

Get APDUs for a session.

```bash
curl http://localhost:8080/api/sessions/session-uuid/apdus
```

**POST /api/sessions/{id}/apdus**

Add an APDU to a session.

```bash
curl -X POST http://localhost:8080/api/sessions/session-uuid/apdus \
  -H "Content-Type: application/json" \
  -d '{
    "direction": "command",
    "data": "00A4040007A0000000041010"
  }'
```

**DELETE /api/sessions/{id}/apdus**

Clear APDUs for a session.

#### Status

**GET /api/status**

Get server status.

```bash
curl http://localhost:8080/api/status
```

Response:
```json
{
  "status": "running",
  "sessions": 2,
  "clients": 3
}
```

---

## WebSocket Events

### Connection

Connect to WebSocket at: `ws://localhost:8080/ws`

### Message Format

All messages use JSON format:

```json
{
  "type": "event-type",
  "payload": { ... }
}
```

### Client to Server

**Subscribe to events:**
```json
{
  "type": "subscribe",
  "payload": { "channel": "*" }
}
```

**Ping:**
```json
{
  "type": "ping",
  "payload": {}
}
```

### Server to Client

**New APDU:**
```json
{
  "type": "apdu",
  "payload": {
    "id": "apdu-uuid",
    "sessionId": "session-uuid",
    "timestamp": 1699999999000,
    "direction": "command",
    "data": "00A4040007A0000000041010",
    "sw": null,
    "responseData": null,
    "metadata": {}
  }
}
```

**Session created:**
```json
{
  "type": "session.created",
  "payload": {
    "id": "session-uuid",
    "name": "New Session",
    "status": "idle",
    "createdAt": "2024-01-15T10:00:00.000Z"
  }
}
```

**Session updated:**
```json
{
  "type": "session.updated",
  "payload": {
    "id": "session-uuid",
    "status": "active"
  }
}
```

**Session deleted:**
```json
{
  "type": "session.deleted",
  "payload": {
    "id": "session-uuid"
  }
}
```

**Pong:**
```json
{
  "type": "pong",
  "payload": {}
}
```

---

## Integration

### Programmatic Usage

Use the dashboard server in your Python code:

```python
import asyncio
from gp_ota_tester.dashboard import DashboardServer, DashboardConfig

async def main():
    # Create configuration
    config = DashboardConfig(
        host="127.0.0.1",
        port=8080,
        debug=False
    )

    # Create server
    server = DashboardServer(config)

    # Create a test session
    session = await server.state.create_session("Test Session")
    print(f"Created session: {session.id}")

    # Start server (blocks until stopped)
    await server.start()

asyncio.run(main())
```

### Emitting APDUs

Programmatically emit APDU events to connected clients:

```python
import asyncio
from gp_ota_tester.dashboard import DashboardServer, DashboardConfig

async def test_with_dashboard():
    config = DashboardConfig(port=8080)
    server = DashboardServer(config)

    # Start server in background
    asyncio.create_task(server.start())
    await asyncio.sleep(1)  # Wait for server to start

    # Create session
    session = await server.state.create_session("APDU Test")

    # Emit APDUs
    await server.emit_apdu(
        session_id=session.id,
        direction="command",
        data="00A4040007A0000000041010"
    )

    await server.emit_apdu(
        session_id=session.id,
        direction="response",
        data="6F10840E315041592E5359532E4444463031",
        sw="9000"
    )

asyncio.run(test_with_dashboard())
```

### Integration with PSK-TLS Server

Connect the dashboard to the PSK-TLS admin server for monitoring:

```python
import asyncio
from gp_ota_tester.server import AdminServer, ServerConfig
from gp_ota_tester.dashboard import DashboardServer, DashboardConfig

async def main():
    # Start dashboard
    dashboard_config = DashboardConfig(port=8080)
    dashboard = DashboardServer(dashboard_config)
    dashboard_task = asyncio.create_task(dashboard.start())

    # Create monitoring session
    session = await dashboard.state.create_session("PSK-TLS Monitor")

    # Create server config
    server_config = ServerConfig(port=8443)

    # Hook APDU events to dashboard
    def on_apdu(direction, data, sw=None):
        asyncio.create_task(
            dashboard.emit_apdu(session.id, direction, data, sw)
        )

    # Start PSK-TLS server with hooks
    # ... server implementation with APDU callbacks

    await dashboard_task

asyncio.run(main())
```

---

## Troubleshooting

### Dashboard won't start

**Port already in use:**
```bash
# Check what's using the port
lsof -i :8080

# Use a different port
gp-dashboard start --port 3000
```

**Missing dependencies:**
```bash
pip install rich
```

### WebSocket won't connect

**Check server is running:**
```bash
gp-dashboard status
```

**Check firewall settings:**
- Ensure port 8080 is accessible
- For remote access, use `--host 0.0.0.0`

**Browser console errors:**
- Open browser developer tools (F12)
- Check Console tab for WebSocket errors

### No sessions showing

**Check connection status:**
- Look for connection indicator in header
- Green = connected, try refreshing
- Red = disconnected, check server

**Manual refresh:**
- Click refresh button in session panel

### APDUs not appearing

**Check session selection:**
- Ensure a session is selected (highlighted)

**Check filters:**
- Reset filters to "All"
- Clear search input

**Check WebSocket:**
- Verify WebSocket is connected
- Check browser console for errors

### Performance issues

**Large log files:**
- Clear logs periodically
- Use filters to reduce displayed entries
- Export and clear old sessions

**Browser memory:**
- Close and reopen browser
- Try a different browser
- Disable browser extensions

### Export not working

**Check browser permissions:**
- Allow downloads from the site
- Check download folder permissions

**Try different format:**
- If JSON fails, try CSV or text

---

## Additional Resources

- [PSK-TLS Server Guide](psk-tls-server-guide.md) - Server setup and configuration
- [User Guide](user-guide.md) - Complete project documentation

---

## License

This project is licensed under the MIT License.
