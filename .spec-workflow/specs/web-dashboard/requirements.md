# Requirements Document: Web Dashboard

## Introduction

The Web Dashboard is the graphical frontend component of CardLink that provides real-time monitoring, interactive testing, and log management capabilities for the PSK-TLS Admin Server. It enables testers to visualize TLS handshakes, monitor APDU exchanges, execute manual RAM commands, and export communication logs for analysis.

This component serves as the primary interface for interactive testing sessions, complementing the CLI tools with a visual representation of OTA communication flows.

## Alignment with Product Vision

This feature directly supports CardLink's core mission of providing accessible SCP81 compliance testing:

- **Protocol transparency**: Visual representation of TLS handshakes and APDU exchanges in real-time
- **Interactive testing**: Manual RAM command execution without scripting
- **Debugging support**: Detailed views of communication logs with hex/decoded formats
- **Export capabilities**: Log export for reporting and external analysis
- **Accessibility**: Web-based interface accessible from any browser without installation

## Requirements

### Requirement 1: Real-Time Session Monitoring

**User Story:** As a tester, I want to see active OTA sessions in real-time, so that I can monitor ongoing test operations and quickly identify issues.

#### Acceptance Criteria

1. WHEN a TLS connection is established THEN the dashboard SHALL display the new session within 500ms
2. WHEN viewing sessions THEN the dashboard SHALL show session ID, PSK identity, cipher suite, connection time, and status
3. WHEN a session state changes THEN the dashboard SHALL update the display immediately via WebSocket
4. WHEN viewing sessions THEN the dashboard SHALL show the number of APDU commands exchanged
5. WHEN a session ends THEN the dashboard SHALL update status and show duration

### Requirement 2: TLS Handshake Visualization

**User Story:** As a UICC developer, I want to see TLS handshake details, so that I can verify PSK negotiation is working correctly.

#### Acceptance Criteria

1. WHEN a TLS handshake starts THEN the dashboard SHALL display handshake progress indicator
2. WHEN a TLS handshake completes THEN the dashboard SHALL show:
   - PSK identity used
   - Negotiated cipher suite
   - TLS version
   - Handshake duration (ms)
3. WHEN a handshake fails THEN the dashboard SHALL display the failure reason and TLS alert code
4. WHEN NULL cipher is negotiated THEN the dashboard SHALL display a prominent warning indicator
5. WHEN viewing handshake history THEN the dashboard SHALL list recent handshakes with their outcomes

### Requirement 3: APDU Communication Log

**User Story:** As a QA engineer, I want to see all APDU commands and responses, so that I can analyze the communication between server and UICC.

#### Acceptance Criteria

1. WHEN an APDU command is received THEN the dashboard SHALL display it within 100ms
2. WHEN viewing APDU logs THEN the dashboard SHALL show:
   - Direction (received/sent)
   - Timestamp
   - Raw hex bytes
   - Decoded command (CLA, INS, P1, P2, Lc, Data, Le)
   - Status word for responses
   - Response time (ms)
3. WHEN viewing logs THEN the dashboard SHALL support filtering by session, command type, or status word
4. WHEN an APDU log entry is clicked THEN the dashboard SHALL show expanded detail view
5. WHEN new APDUs arrive THEN the dashboard SHALL auto-scroll to latest unless user has scrolled up

### Requirement 4: Manual RAM Command Interface

**User Story:** As a tester, I want to send manual GlobalPlatform commands to the UICC, so that I can perform interactive testing without scripting.

#### Acceptance Criteria

1. WHEN an active session exists THEN the dashboard SHALL enable the command interface
2. WHEN building a command THEN the dashboard SHALL provide a form with:
   - Command type selector (SELECT, GET STATUS, INSTALL, DELETE, etc.)
   - Parameter fields appropriate for selected command
   - Raw hex input option for advanced users
3. WHEN a command is submitted THEN the dashboard SHALL send it through the active session
4. WHEN a response is received THEN the dashboard SHALL display it inline with the command
5. WHEN no active session exists THEN the dashboard SHALL disable command interface with explanation

### Requirement 5: Command Builder Templates

**User Story:** As a tester, I want pre-built command templates, so that I can quickly execute common GP commands without remembering byte formats.

#### Acceptance Criteria

1. WHEN opening command builder THEN the dashboard SHALL offer templates for:
   - SELECT (by AID)
   - GET STATUS (ISD, Applications, Load Files)
   - GET DATA (various tags)
   - INITIALIZE UPDATE
2. WHEN selecting a template THEN the dashboard SHALL pre-fill appropriate parameters
3. WHEN a template has variable fields THEN the dashboard SHALL provide labeled input fields
4. WHEN submitting a templated command THEN the dashboard SHALL show both template name and raw bytes

### Requirement 6: Log Export

**User Story:** As a QA engineer, I want to export communication logs, so that I can include them in test reports or analyze them externally.

#### Acceptance Criteria

1. WHEN exporting logs THEN the dashboard SHALL support JSON format with full detail
2. WHEN exporting logs THEN the dashboard SHALL support CSV format for spreadsheet analysis
3. WHEN exporting logs THEN the dashboard SHALL allow filtering by session or time range
4. WHEN exporting THEN the dashboard SHALL include session metadata (PSK identity, cipher, duration)
5. WHEN export is requested THEN the dashboard SHALL generate downloadable file within 5 seconds

### Requirement 7: Dashboard Configuration

**User Story:** As an administrator, I want to configure dashboard behavior, so that I can adapt it to my workflow.

#### Acceptance Criteria

1. WHEN configuring display THEN the dashboard SHALL support hex/ASCII toggle for data display
2. WHEN configuring display THEN the dashboard SHALL support timestamp format selection (local/UTC)
3. WHEN configuring logs THEN the dashboard SHALL support max entries limit (default 1000)
4. WHEN configuring THEN the dashboard SHALL persist preferences in browser local storage
5. WHEN configuring THEN the dashboard SHALL support dark/light theme toggle

### Requirement 8: Connection Status

**User Story:** As a tester, I want to see the connection status to the server, so that I know when the dashboard is receiving live updates.

#### Acceptance Criteria

1. WHEN the dashboard connects to server THEN it SHALL display "Connected" status indicator
2. WHEN the WebSocket connection is lost THEN the dashboard SHALL display "Disconnected" with retry countdown
3. WHEN reconnecting THEN the dashboard SHALL automatically retry every 5 seconds
4. WHEN reconnected THEN the dashboard SHALL restore subscription to events
5. WHEN server is unreachable THEN the dashboard SHALL display helpful error message

### Requirement 9: Error and Alert Display

**User Story:** As a tester, I want to see errors and alerts prominently, so that I can quickly identify problems during testing.

#### Acceptance Criteria

1. WHEN a PSK mismatch occurs THEN the dashboard SHALL display alert with identity and source IP
2. WHEN a connection is interrupted THEN the dashboard SHALL display alert with session details
3. WHEN handshake fails THEN the dashboard SHALL display alert with failure reason
4. WHEN high error rate is detected THEN the dashboard SHALL display warning banner
5. WHEN viewing alerts THEN the dashboard SHALL show timestamp and allow dismissal

### Requirement 10: Health and Metrics Overview

**User Story:** As an administrator, I want to see server health and basic metrics, so that I can monitor system status.

#### Acceptance Criteria

1. WHEN viewing dashboard THEN it SHALL display server uptime
2. WHEN viewing dashboard THEN it SHALL display active session count
3. WHEN viewing dashboard THEN it SHALL display total sessions since start
4. WHEN viewing dashboard THEN it SHALL display total APDU commands processed
5. WHEN viewing dashboard THEN it SHALL provide link to Prometheus metrics endpoint

## Non-Functional Requirements

### User Experience (UX) Principles

The dashboard SHALL prioritize user experience with the following principles:

#### Information Architecture
- **Progressive Disclosure**: Show summary information first, reveal details on demand
- **Visual Hierarchy**: Most important information (active sessions, errors) prominently displayed
- **Contextual Information**: Display relevant help and context where users need it
- **Information Density**: Balance data richness with readability; avoid overwhelming users

#### Interaction Design
- **Immediate Feedback**: All user actions SHALL provide visual feedback within 100ms
- **Predictable Behavior**: Similar actions SHALL behave consistently across the dashboard
- **Error Prevention**: Validate inputs before submission; confirm destructive actions
- **Undo Support**: Allow users to cancel or undo actions where possible
- **Smart Defaults**: Pre-fill forms with sensible defaults to reduce input effort

#### Accessibility
- **Keyboard Navigation**: All features accessible via keyboard (Tab, Enter, Escape)
- **Focus Indicators**: Clear visual indication of focused elements
- **Color Contrast**: WCAG 2.1 AA compliant contrast ratios (4.5:1 minimum for text)
- **Screen Reader Support**: Semantic HTML and ARIA labels for assistive technology

### Professional Visual Design

The dashboard SHALL implement professional styling following these guidelines:

#### Design System
- **Consistent Typography**:
  - Primary font: System font stack (San Francisco, Segoe UI, Roboto)
  - Monospace font for hex/code: Consolas, Monaco, monospace
  - Font scale: 12px (small), 14px (body), 16px (headers), 20px (titles)
- **Color Palette**:
  - Primary: Professional blue (#2563EB) for actions and links
  - Success: Green (#16A34A) for successful operations
  - Warning: Amber (#D97706) for warnings and NULL cipher alerts
  - Error: Red (#DC2626) for errors and failures
  - Neutral: Gray scale for backgrounds and borders
- **Spacing System**: 4px base unit (4, 8, 12, 16, 24, 32, 48px)
- **Border Radius**: Consistent 4px for small elements, 8px for cards/panels

#### Component Styling
- **Cards/Panels**: Subtle shadows, clear boundaries, consistent padding (16px)
- **Tables**: Zebra striping for readability, sticky headers, hover states
- **Buttons**: Clear primary/secondary/danger hierarchy, disabled states
- **Inputs**: Visible borders, focus states, validation indicators
- **Icons**: Consistent icon set (e.g., Lucide, Heroicons) at 16px/20px/24px

#### Visual States
- **Loading States**: Skeleton loaders or spinners with context text
- **Empty States**: Helpful illustrations and guidance when no data
- **Error States**: Clear error messages with recovery suggestions
- **Success States**: Confirmation feedback with next steps

#### Layout
- **Grid System**: 12-column grid for consistent alignment
- **Responsive Breakpoints**: 1280px (desktop), 1024px (tablet landscape)
- **White Space**: Generous spacing to improve readability
- **Fixed Navigation**: Persistent header with connection status and key metrics

### Informative Content

The dashboard SHALL provide informative, actionable content:

#### Data Presentation
- **Human-Readable Formats**:
  - Timestamps as "2 minutes ago" with full date on hover
  - Durations as "1.23s" not "1234ms"
  - Byte sizes as "1.5 KB" not "1536 bytes"
- **Contextual Labels**: Every data point labeled; no unexplained numbers
- **Status Indicators**: Color-coded badges with text labels (not color-only)
- **Trends and Comparisons**: Show delta/change indicators where useful

#### Help and Documentation
- **Inline Help**: Tooltips explaining technical terms (PSK, APDU, SW, etc.)
- **Field Descriptions**: Each form field with clear label and placeholder
- **Command Documentation**: Built-in reference for GP commands and parameters
- **Error Explanations**: Technical errors translated to actionable guidance

#### Onboarding
- **First-Run Guidance**: Welcome message with quick-start steps
- **Empty State Instructions**: Clear guidance when no sessions/data
- **Feature Discovery**: Subtle hints for power-user features

### Code Architecture and Modularity

- **Separation of Concerns**: Backend API routes separate from frontend static files
- **Component-Based Frontend**: Modular JavaScript components for each feature area
- **Event-Driven Updates**: WebSocket for all real-time updates, REST for initial load and exports
- **CSS Architecture**: BEM naming convention or CSS modules for maintainable styles
- **Design Tokens**: Centralized variables for colors, spacing, typography

### Performance

- **Initial Load**: Dashboard SHALL load and be interactive within 2 seconds
- **Real-time Latency**: Events SHALL appear on dashboard within 500ms of occurrence
- **Log Capacity**: Dashboard SHALL handle display of 10,000+ log entries without degradation
- **Memory Efficiency**: Dashboard SHALL use virtual scrolling for large log lists
- **Perceived Performance**: Use optimistic updates and skeleton loaders

### Security

- **Same-Origin**: Dashboard served from same origin as Admin Server
- **No Authentication (v1.0)**: Local testing tool, authentication deferred to future version
- **XSS Prevention**: All user input and log data properly escaped before display
- **HTTPS Option**: Dashboard accessible via HTTPS when server uses TLS

### Usability

- **Responsive Design**: Dashboard usable on screens 1280px and wider
- **Keyboard Shortcuts**: Common actions accessible via keyboard (Ctrl+Enter to send, Esc to cancel)
- **Clear Feedback**: Loading states, success/error messages for all actions
- **Persistent State**: User preferences and scroll positions preserved across sessions

### Reliability

- **Graceful Degradation**: Dashboard remains usable if WebSocket fails (manual refresh)
- **State Recovery**: Dashboard recovers state on page refresh
- **Error Boundaries**: JavaScript errors in one component don't crash entire dashboard
- **Offline Awareness**: Clear indication when operating with stale data
