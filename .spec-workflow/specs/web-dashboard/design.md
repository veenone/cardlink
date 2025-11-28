# Design Document: Web Dashboard

## Technical Approach

### Overview

The Web Dashboard is implemented as a single-page application (SPA) served by the CardLink Admin Server. It uses vanilla JavaScript with a modular component architecture, WebSocket for real-time updates, and a professional design system based on CSS custom properties (design tokens).

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Web Dashboard                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Frontend (Browser)                           │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │    │
│  │  │  Header   │ │  Session  │ │   APDU    │ │  Command  │           │    │
│  │  │ Component │ │   Panel   │ │    Log    │ │  Builder  │           │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │    │
│  │  │   Alert   │ │  Metrics  │ │  Settings │ │   Toast   │           │    │
│  │  │  Banner   │ │  Overview │ │   Modal   │ │  Manager  │           │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │    │
│  │                         │                                            │    │
│  │                         ▼                                            │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │                    State Manager                             │    │    │
│  │  │  (sessions, logs, alerts, settings, connection status)       │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                         │                                            │    │
│  │           ┌─────────────┴─────────────┐                             │    │
│  │           ▼                           ▼                             │    │
│  │  ┌─────────────────┐         ┌─────────────────┐                    │    │
│  │  │  WebSocket      │         │  REST API       │                    │    │
│  │  │  Client         │         │  Client         │                    │    │
│  │  └─────────────────┘         └─────────────────┘                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
└───────────────────────────────────┼──────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Backend (Dashboard Server)                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │
│  │  Static File  │  │  REST API     │  │  WebSocket    │                    │
│  │  Server       │  │  Routes       │  │  Handler      │                    │
│  └───────────────┘  └───────────────┘  └───────────────┘                    │
│                            │                   │                             │
│                            ▼                   ▼                             │
│                     ┌─────────────────────────────────┐                     │
│                     │      Event Subscriber           │                     │
│                     │   (AdminServer EventEmitter)    │                     │
│                     └─────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Vanilla JavaScript**: No heavy frameworks to minimize bundle size and complexity. Modern ES6+ features provide sufficient structure.

2. **Component-Based Architecture**: Each UI feature is a self-contained component with its own state, rendering, and event handling.

3. **Design Tokens**: CSS custom properties for colors, spacing, typography ensure consistent styling and easy theming.

4. **WebSocket for Real-Time**: All live updates via WebSocket; REST API for initial data load and exports.

5. **Virtual Scrolling**: For APDU log with potentially thousands of entries, use virtual scrolling to maintain performance.

6. **Progressive Enhancement**: Core features work without JavaScript errors in other components.

## Component Design

### Component 1: DashboardApp

**Purpose**: Main application shell that initializes components and manages global state.

**Interface**:
```javascript
class DashboardApp {
    constructor(config) {
        // config: { apiBaseUrl, wsUrl }
    }

    async init() {
        // Initialize all components, connect WebSocket, load initial data
    }

    getState() {
        // Return current application state
    }

    subscribe(event, callback) {
        // Subscribe to state changes
    }
}
```

**Key Behaviors**:
- Initializes StateManager, WebSocketClient, APIClient
- Creates and mounts all UI components
- Handles global keyboard shortcuts
- Manages application lifecycle

### Component 2: StateManager

**Purpose**: Centralized state management with subscription-based updates.

**Interface**:
```javascript
class StateManager {
    constructor() {
        this.state = {
            sessions: [],           // Active and recent sessions
            selectedSession: null,  // Currently selected session ID
            logs: [],               // APDU log entries
            alerts: [],             // Active alerts
            metrics: {},            // Server metrics
            settings: {},           // User preferences
            connection: 'disconnected' // WebSocket status
        };
    }

    getState(path) {
        // Get state value at path (e.g., 'sessions', 'settings.theme')
    }

    setState(path, value) {
        // Update state and notify subscribers
    }

    subscribe(path, callback) {
        // Subscribe to changes at path
    }

    loadFromStorage() {
        // Load persisted settings from localStorage
    }

    persistToStorage() {
        // Save settings to localStorage
    }
}
```

**State Structure**:
```javascript
{
    sessions: [
        {
            id: 'uuid',
            pskIdentity: 'UICC_001',
            cipherSuite: 'TLS_PSK_WITH_AES_128_CBC_SHA256',
            state: 'active',
            connectedAt: '2024-01-15T10:30:00Z',
            commandCount: 42,
            lastActivity: '2024-01-15T10:35:00Z'
        }
    ],
    logs: [
        {
            id: 'uuid',
            sessionId: 'uuid',
            direction: 'received',
            timestamp: '2024-01-15T10:35:00Z',
            rawHex: '00A4040007A0000000041010',
            decoded: { cla: '00', ins: 'A4', p1: '04', p2: '00', data: '...' },
            responseTime: 45
        }
    ],
    alerts: [
        {
            id: 'uuid',
            type: 'psk_mismatch',
            message: 'PSK mismatch for identity UICC_002',
            timestamp: '2024-01-15T10:32:00Z',
            dismissed: false
        }
    ],
    metrics: {
        uptime: 3600,
        totalSessions: 150,
        activeSessions: 2,
        totalCommands: 5420
    },
    settings: {
        theme: 'light',
        hexDisplay: 'uppercase',
        timestampFormat: 'relative',
        maxLogEntries: 1000,
        autoScroll: true
    },
    connection: 'connected'
}
```

### Component 3: WebSocketClient

**Purpose**: Manages WebSocket connection with auto-reconnect and message routing.

**Interface**:
```javascript
class WebSocketClient {
    constructor(url, stateManager) {
        this.url = url;
        this.stateManager = stateManager;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 5000;
    }

    connect() {
        // Establish WebSocket connection
    }

    disconnect() {
        // Close connection gracefully
    }

    send(message) {
        // Send message to server
    }

    onMessage(handler) {
        // Register message handler
    }
}
```

**Message Types**:
| Type | Direction | Description |
|------|-----------|-------------|
| `session_created` | Server→Client | New session established |
| `session_updated` | Server→Client | Session state changed |
| `session_ended` | Server→Client | Session closed |
| `apdu_received` | Server→Client | APDU command received |
| `apdu_sent` | Server→Client | APDU response sent |
| `alert` | Server→Client | Error/warning alert |
| `metrics_update` | Server→Client | Metrics refresh |
| `send_command` | Client→Server | Manual command request |

**Key Behaviors**:
- Auto-reconnect with exponential backoff (max 5 attempts)
- Connection status updates to StateManager
- Message routing to appropriate handlers
- Heartbeat/ping to detect stale connections

### Component 4: APIClient

**Purpose**: REST API client for initial data load and exports.

**Interface**:
```javascript
class APIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async getSessions() {
        // GET /api/sessions
    }

    async getSessionLogs(sessionId, options) {
        // GET /api/sessions/{id}/logs?limit=100&offset=0
    }

    async getMetrics() {
        // GET /api/metrics
    }

    async sendCommand(sessionId, command) {
        // POST /api/sessions/{id}/commands
    }

    async exportLogs(options) {
        // GET /api/export?format=json&sessionId=...
    }
}
```

**API Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/{id}` | GET | Get session details |
| `/api/sessions/{id}/logs` | GET | Get session APDU logs |
| `/api/metrics` | GET | Get server metrics |
| `/api/sessions/{id}/commands` | POST | Send manual command |
| `/api/export` | GET | Export logs (JSON/CSV) |
| `/api/health` | GET | Health check |

### Component 5: HeaderComponent

**Purpose**: Top navigation bar with connection status, metrics summary, and settings access.

**Interface**:
```javascript
class HeaderComponent {
    constructor(container, stateManager) {
        this.container = container;
        this.stateManager = stateManager;
    }

    render() {
        // Render header HTML
    }

    update(state) {
        // Update connection indicator, metrics badges
    }
}
```

**Layout**:
```
┌────────────────────────────────────────────────────────────────────────────┐
│  🔗 CardLink Dashboard    │ ● Connected │ Sessions: 2 │ Commands: 542 │ ⚙️ │
└────────────────────────────────────────────────────────────────────────────┘
```

**Key Behaviors**:
- Connection status indicator (green=connected, red=disconnected, yellow=reconnecting)
- Real-time metrics badges
- Settings gear opens SettingsModal
- Logo/title links to documentation

### Component 6: SessionPanel

**Purpose**: Displays active and recent sessions with selection capability.

**Interface**:
```javascript
class SessionPanel {
    constructor(container, stateManager) {
        this.container = container;
        this.stateManager = stateManager;
    }

    render() {
        // Render session list
    }

    selectSession(sessionId) {
        // Update selected session in state
    }

    formatSessionCard(session) {
        // Generate HTML for session card
    }
}
```

**Session Card Layout**:
```
┌──────────────────────────────────────┐
│ 🟢 UICC_001                          │
│ TLS_PSK_WITH_AES_128_CBC_SHA256      │
│ Connected 5 min ago • 42 commands    │
└──────────────────────────────────────┘
```

**Key Behaviors**:
- Shows active sessions prominently (sorted first)
- Clicking session selects it and filters APDU log
- Visual distinction for session states (active=green, closed=gray)
- NULL cipher warning badge when applicable
- Empty state with "Waiting for connections..." message

### Component 7: APDULogComponent

**Purpose**: Displays APDU command/response log with filtering and virtual scrolling.

**Interface**:
```javascript
class APDULogComponent {
    constructor(container, stateManager) {
        this.container = container;
        this.stateManager = stateManager;
        this.virtualScroller = null;
    }

    render() {
        // Render log container with virtual scrolling
    }

    addEntry(entry) {
        // Add new log entry (with auto-scroll if enabled)
    }

    filter(criteria) {
        // Filter logs by session, command type, status word
    }

    expandEntry(entryId) {
        // Show detailed view of entry
    }

    formatEntry(entry) {
        // Generate HTML for log entry
    }
}
```

**Log Entry Layout**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ↓ 10:35:42  SELECT           00 A4 04 00 07 A0 00 00 00 04 10 10       │
│ ↑ 10:35:42  Response (45ms)  90 00                              [9000] │
└──────────────────────────────────────────────────────────────────────────┘
```

**Expanded Entry View**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Command Details                                                    [×]  │
├──────────────────────────────────────────────────────────────────────────┤
│ Type:       SELECT                                                      │
│ Timestamp:  2024-01-15 10:35:42.123 UTC                                │
│ Session:    UICC_001 (abc123...)                                       │
├──────────────────────────────────────────────────────────────────────────┤
│ Raw Hex:    00 A4 04 00 07 A0 00 00 00 04 10 10                        │
├──────────────────────────────────────────────────────────────────────────┤
│ Decoded:                                                                │
│   CLA: 00    INS: A4 (SELECT)    P1: 04    P2: 00                      │
│   Lc:  07    Data: A0 00 00 00 04 10 10 (AID)                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Response:   90 00 (Success)                                             │
│ Duration:   45ms                                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Behaviors**:
- Virtual scrolling for 10,000+ entries
- Auto-scroll to latest (unless user scrolled up)
- Color-coded by direction (blue=received, green=sent)
- Status word badges (green=9000, red=error, yellow=warning)
- Click to expand with full details
- Filter toolbar (session, command type, status word)
- Copy hex to clipboard on click

### Component 8: CommandBuilder

**Purpose**: Form for building and sending manual GP commands.

**Interface**:
```javascript
class CommandBuilder {
    constructor(container, stateManager, apiClient) {
        this.container = container;
        this.stateManager = stateManager;
        this.apiClient = apiClient;
        this.templates = this.loadTemplates();
    }

    render() {
        // Render command builder form
    }

    selectTemplate(templateName) {
        // Pre-fill form with template
    }

    buildCommand() {
        // Construct APDU from form fields
    }

    async sendCommand() {
        // Send command via API, show response
    }

    validateInput() {
        // Validate hex input, parameters
    }
}
```

**Command Templates**:
```javascript
const TEMPLATES = {
    select: {
        name: 'SELECT',
        description: 'Select application by AID',
        fields: [
            { name: 'aid', label: 'Application AID', type: 'hex', placeholder: 'A0000000041010' }
        ],
        build: (fields) => `00A40400${toHexLength(fields.aid)}${fields.aid}`
    },
    getStatus: {
        name: 'GET STATUS',
        description: 'Get card content information',
        fields: [
            { name: 'scope', label: 'Scope', type: 'select', options: [
                { value: '80', label: 'ISD' },
                { value: '40', label: 'Applications' },
                { value: '20', label: 'Load Files' }
            ]}
        ],
        build: (fields) => `80F2${fields.scope}00024F00`
    },
    // ... more templates
};
```

**Layout**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Send Command                                              [Session: ...] │
├──────────────────────────────────────────────────────────────────────────┤
│ Template: [SELECT ▼]                                                     │
│                                                                          │
│ Application AID: [A0000000041010_________]  ℹ️ 5-16 bytes hex           │
│                                                                          │
│ Raw Command: 00 A4 04 00 07 A0 00 00 00 04 10 10                        │
│                                                                          │
│                                         [Clear]  [Send Command →]        │
├──────────────────────────────────────────────────────────────────────────┤
│ Response:                                                                │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ 90 00                                                    [Success] │  │
│ └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Behaviors**:
- Disabled when no active session selected
- Template dropdown with common commands
- Dynamic form fields based on selected template
- Real-time hex preview as fields change
- Raw hex input mode for advanced users
- Input validation with helpful error messages
- Response displayed inline with status interpretation
- Keyboard shortcut: Ctrl+Enter to send

### Component 9: AlertBanner

**Purpose**: Displays error and warning alerts prominently.

**Interface**:
```javascript
class AlertBanner {
    constructor(container, stateManager) {
        this.container = container;
        this.stateManager = stateManager;
    }

    render() {
        // Render alert banner area
    }

    showAlert(alert) {
        // Display new alert with animation
    }

    dismissAlert(alertId) {
        // Mark alert as dismissed
    }

    formatAlert(alert) {
        // Generate HTML for alert
    }
}
```

**Alert Types and Styling**:
| Type | Color | Icon | Example Message |
|------|-------|------|-----------------|
| `error` | Red | ⛔ | Connection interrupted for session UICC_001 |
| `warning` | Amber | ⚠️ | NULL cipher in use - traffic unencrypted |
| `psk_mismatch` | Red | 🔑 | PSK mismatch for identity UICC_002 from 192.168.1.100 |
| `high_error_rate` | Amber | 📊 | High error rate detected: 45% failures |

**Layout**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚠️  NULL cipher negotiated - traffic is UNENCRYPTED          [Dismiss ×]│
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Behaviors**:
- Alerts stack below header
- Newest alerts at top
- Auto-dismiss info alerts after 10 seconds
- Error alerts persist until dismissed
- Dismiss button removes alert
- Click alert to see details/context

### Component 10: SettingsModal

**Purpose**: Modal dialog for dashboard configuration.

**Interface**:
```javascript
class SettingsModal {
    constructor(stateManager) {
        this.stateManager = stateManager;
    }

    open() {
        // Show modal
    }

    close() {
        // Hide modal, save settings
    }

    render() {
        // Render settings form
    }

    saveSettings() {
        // Persist to localStorage
    }
}
```

**Settings Options**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Settings                                                           [×]  │
├──────────────────────────────────────────────────────────────────────────┤
│ Display                                                                  │
│   Theme:           [Light ▼]  (Light / Dark)                            │
│   Hex Format:      [Uppercase ▼]  (Uppercase / Lowercase / Grouped)     │
│   Timestamps:      [Relative ▼]  (Relative / Local / UTC)               │
│                                                                          │
│ Behavior                                                                 │
│   Auto-scroll logs:    [✓]                                              │
│   Max log entries:     [1000____]                                       │
│                                                                          │
│ Export                                                                   │
│   Default format:      [JSON ▼]  (JSON / CSV)                           │
│                                                                          │
│                                              [Reset Defaults]  [Save]   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component 11: ToastManager

**Purpose**: Shows transient feedback messages (success, info).

**Interface**:
```javascript
class ToastManager {
    constructor() {
        this.container = this.createContainer();
    }

    show(message, type = 'info', duration = 3000) {
        // Display toast notification
    }

    success(message) {
        this.show(message, 'success');
    }

    error(message) {
        this.show(message, 'error', 5000);
    }

    info(message) {
        this.show(message, 'info');
    }
}
```

**Toast Layout**:
```
                                    ┌─────────────────────────────┐
                                    │ ✓ Command sent successfully │
                                    └─────────────────────────────┘
```

### Component 12: VirtualScroller

**Purpose**: Efficiently renders large lists by only rendering visible items.

**Interface**:
```javascript
class VirtualScroller {
    constructor(container, options) {
        // options: { itemHeight, bufferSize, renderItem }
    }

    setItems(items) {
        // Update data source
    }

    appendItems(items) {
        // Add items to end
    }

    scrollToEnd() {
        // Scroll to latest item
    }

    refresh() {
        // Re-render visible items
    }
}
```

**Key Behaviors**:
- Only renders visible items + buffer
- Maintains scroll position on data update
- Supports variable height items (with estimation)
- Smooth scrolling animation

## Data Models

### Frontend Models

```typescript
interface Session {
    id: string;
    pskIdentity: string;
    cipherSuite: string;
    state: 'handshaking' | 'connected' | 'active' | 'closed';
    connectedAt: string;  // ISO timestamp
    closedAt?: string;
    commandCount: number;
    lastActivity: string;
    isNullCipher: boolean;
}

interface APDULogEntry {
    id: string;
    sessionId: string;
    direction: 'received' | 'sent';
    timestamp: string;
    rawHex: string;
    decoded: DecodedAPDU;
    statusWord?: string;
    responseTimeMs?: number;
}

interface DecodedAPDU {
    cla: string;
    ins: string;
    insName: string;
    p1: string;
    p2: string;
    lc?: string;
    data?: string;
    le?: string;
}

interface Alert {
    id: string;
    type: 'error' | 'warning' | 'info' | 'psk_mismatch' | 'high_error_rate';
    title: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    dismissed: boolean;
}

interface Metrics {
    uptime: number;  // seconds
    totalSessions: number;
    activeSessions: number;
    totalCommands: number;
    errorRate: number;
}

interface Settings {
    theme: 'light' | 'dark';
    hexDisplay: 'uppercase' | 'lowercase' | 'grouped';
    timestampFormat: 'relative' | 'local' | 'utc';
    maxLogEntries: number;
    autoScroll: boolean;
    defaultExportFormat: 'json' | 'csv';
}
```

## Design System

### Design Tokens (CSS Custom Properties)

```css
:root {
    /* Colors - Light Theme */
    --color-primary: #2563EB;
    --color-primary-hover: #1D4ED8;
    --color-success: #16A34A;
    --color-warning: #D97706;
    --color-error: #DC2626;

    --color-bg-primary: #FFFFFF;
    --color-bg-secondary: #F9FAFB;
    --color-bg-tertiary: #F3F4F6;

    --color-text-primary: #111827;
    --color-text-secondary: #6B7280;
    --color-text-muted: #9CA3AF;

    --color-border: #E5E7EB;
    --color-border-focus: #2563EB;

    /* Typography */
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-mono: 'SF Mono', Consolas, Monaco, 'Courier New', monospace;

    --text-xs: 0.75rem;    /* 12px */
    --text-sm: 0.875rem;   /* 14px */
    --text-base: 1rem;     /* 16px */
    --text-lg: 1.25rem;    /* 20px */
    --text-xl: 1.5rem;     /* 24px */

    --font-weight-normal: 400;
    --font-weight-medium: 500;
    --font-weight-semibold: 600;

    /* Spacing */
    --space-1: 0.25rem;    /* 4px */
    --space-2: 0.5rem;     /* 8px */
    --space-3: 0.75rem;    /* 12px */
    --space-4: 1rem;       /* 16px */
    --space-6: 1.5rem;     /* 24px */
    --space-8: 2rem;       /* 32px */

    /* Border Radius */
    --radius-sm: 0.25rem;  /* 4px */
    --radius-md: 0.5rem;   /* 8px */
    --radius-lg: 0.75rem;  /* 12px */
    --radius-full: 9999px;

    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);

    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-normal: 200ms ease;
}

/* Dark Theme */
[data-theme="dark"] {
    --color-bg-primary: #111827;
    --color-bg-secondary: #1F2937;
    --color-bg-tertiary: #374151;

    --color-text-primary: #F9FAFB;
    --color-text-secondary: #D1D5DB;
    --color-text-muted: #9CA3AF;

    --color-border: #374151;
}
```

### Component CSS Classes (BEM)

```css
/* Session Card */
.session-card { }
.session-card--active { }
.session-card--closed { }
.session-card__header { }
.session-card__identity { }
.session-card__cipher { }
.session-card__meta { }
.session-card__badge { }
.session-card__badge--warning { }

/* APDU Log Entry */
.log-entry { }
.log-entry--received { }
.log-entry--sent { }
.log-entry__direction { }
.log-entry__timestamp { }
.log-entry__command { }
.log-entry__hex { }
.log-entry__status { }
.log-entry__status--success { }
.log-entry__status--error { }

/* Alert Banner */
.alert-banner { }
.alert-banner--error { }
.alert-banner--warning { }
.alert-banner__icon { }
.alert-banner__message { }
.alert-banner__dismiss { }

/* Button */
.btn { }
.btn--primary { }
.btn--secondary { }
.btn--danger { }
.btn--disabled { }
.btn--loading { }
```

## File Structure

```
src/cardlink/dashboard/
├── __init__.py
├── server.py                    # Dashboard HTTP server
├── websocket.py                 # WebSocket handler
├── routes/
│   ├── __init__.py
│   ├── api.py                   # REST API routes
│   └── export.py                # Export routes
├── static/
│   ├── index.html               # Main HTML page
│   ├── css/
│   │   ├── tokens.css           # Design tokens
│   │   ├── base.css             # Base styles, reset
│   │   ├── components.css       # Component styles
│   │   └── utilities.css        # Utility classes
│   ├── js/
│   │   ├── app.js               # DashboardApp entry point
│   │   ├── state.js             # StateManager
│   │   ├── websocket.js         # WebSocketClient
│   │   ├── api.js               # APIClient
│   │   ├── components/
│   │   │   ├── header.js        # HeaderComponent
│   │   │   ├── session-panel.js # SessionPanel
│   │   │   ├── apdu-log.js      # APDULogComponent
│   │   │   ├── command-builder.js # CommandBuilder
│   │   │   ├── alert-banner.js  # AlertBanner
│   │   │   ├── settings-modal.js # SettingsModal
│   │   │   └── toast.js         # ToastManager
│   │   ├── utils/
│   │   │   ├── hex.js           # Hex formatting utilities
│   │   │   ├── time.js          # Time formatting utilities
│   │   │   ├── apdu.js          # APDU decoding utilities
│   │   │   └── virtual-scroll.js # VirtualScroller
│   │   └── templates.js         # Command templates
│   └── assets/
│       └── icons/               # SVG icons
└── templates/                   # Jinja2 templates (if needed)
```

## Backend API Design

### REST Endpoints

```python
# routes/api.py

@router.get('/api/sessions')
async def get_sessions():
    """List all sessions (active first, then recent)."""
    return {
        'sessions': [
            {
                'id': 'uuid',
                'pskIdentity': 'UICC_001',
                'cipherSuite': 'TLS_PSK_WITH_AES_128_CBC_SHA256',
                'state': 'active',
                'connectedAt': '2024-01-15T10:30:00Z',
                'commandCount': 42,
                'lastActivity': '2024-01-15T10:35:00Z',
                'isNullCipher': False
            }
        ]
    }

@router.get('/api/sessions/{session_id}/logs')
async def get_session_logs(session_id: str, limit: int = 100, offset: int = 0):
    """Get APDU logs for a session."""
    return {
        'logs': [...],
        'total': 500,
        'hasMore': True
    }

@router.get('/api/metrics')
async def get_metrics():
    """Get server metrics."""
    return {
        'uptime': 3600,
        'totalSessions': 150,
        'activeSessions': 2,
        'totalCommands': 5420,
        'errorRate': 0.02
    }

@router.post('/api/sessions/{session_id}/commands')
async def send_command(session_id: str, body: CommandRequest):
    """Send manual APDU command."""
    # body: { commandHex: '00A4040007A0000000041010' }
    return {
        'responseHex': '9000',
        'responseTimeMs': 45
    }

@router.get('/api/export')
async def export_logs(format: str, session_id: str = None, start: str = None, end: str = None):
    """Export logs as JSON or CSV."""
    # Returns file download
```

### WebSocket Protocol

```python
# websocket.py

class DashboardWebSocket:
    """WebSocket handler for real-time updates."""

    async def handle_connection(self, websocket):
        # Subscribe to EventEmitter
        # Forward events to client

    def format_event(self, event_type: str, data: dict) -> str:
        """Format event as JSON message."""
        return json.dumps({
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        })
```

**WebSocket Message Format**:
```json
{
    "type": "apdu_received",
    "data": {
        "sessionId": "uuid",
        "rawHex": "00A4040007A0000000041010",
        "decoded": { "cla": "00", "ins": "A4", ... }
    },
    "timestamp": "2024-01-15T10:35:42.123Z"
}
```

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| StateManager | State updates, subscriptions, persistence |
| APIClient | Request formatting, response parsing, error handling |
| VirtualScroller | Scroll position, item rendering, performance |
| Hex utilities | Formatting, parsing, validation |
| APDU decoder | Command parsing, INS name lookup |

### Integration Tests

| Test | Description |
|------|-------------|
| WebSocket connection | Connect, receive events, auto-reconnect |
| Session flow | Session appears on connect, updates on activity, removes on close |
| Command sending | Build command, send, receive response |
| Export functionality | Export JSON/CSV, verify format |

### E2E Tests

| Test | Description |
|------|-------------|
| Full dashboard load | Page loads, connects, shows sessions |
| Real-time updates | APDU appears within 500ms of occurrence |
| Manual command | Send SELECT, see response |
| Settings persistence | Change theme, refresh, theme persists |

## Performance Considerations

1. **Virtual Scrolling**: APDU log uses virtual scrolling to handle 10,000+ entries without DOM bloat.

2. **Debounced Updates**: Rapid WebSocket events batched for rendering (16ms frame budget).

3. **Lazy Loading**: Session logs loaded on-demand when session selected.

4. **CSS Containment**: Use `contain: content` on list items for rendering optimization.

5. **Web Workers**: Consider Web Worker for APDU decoding if CPU-intensive.

## Accessibility Considerations

1. **Keyboard Navigation**: Tab through interactive elements, Enter to activate, Escape to close modals.

2. **ARIA Labels**: All buttons, inputs, and dynamic content have appropriate ARIA labels.

3. **Focus Management**: Modal traps focus, returns focus on close.

4. **Color Contrast**: All text meets WCAG 2.1 AA (4.5:1 ratio).

5. **Screen Reader**: Status changes announced via aria-live regions.
