# Tasks Document: Web Dashboard
 
## Task Overview

This document breaks down the Web Dashboard implementation into actionable development tasks organized by component and functionality. The dashboard provides real-time monitoring, interactive testing, and log management for the PSK-TLS Admin Server.

## Tasks

### 1. Project Setup and Design System

- [x] 1.1. Create `src/cardlink/dashboard/` package structure with `__init__.py` and `static/` directories
  - File: src/cardlink/dashboard/__init__.py, src/cardlink/dashboard/static/
  - Create directory structure for dashboard module with static file directories
  - Purpose: Establish module foundation for dashboard component
  - _Leverage: src/cardlink/ package structure_
  - _Requirements: Code Architecture and Modularity_
  - _Prompt: Role: Python Developer specializing in package architecture | Task: Create the dashboard module structure with proper __init__.py exports and static file directories for CSS, JS, and assets | Restrictions: Follow existing package patterns, maintain clean imports | Success: Module imports correctly, static directories exist with proper organization_

- [x] 1.2. Create `tokens.css` with CSS custom properties for design tokens
  - File: src/cardlink/dashboard/static/css/tokens.css
  - Define color palette, typography scale, spacing system, and theme variables
  - Purpose: Establish consistent design language across dashboard
  - _Leverage: Design System requirements from requirements.md_
  - _Requirements: Professional Visual Design, Design System_
  - _Prompt: Role: Frontend Developer specializing in CSS architecture and design systems | Task: Create CSS custom properties for colors (primary blue #2563EB, success, warning, error), typography (system font stack, monospace), spacing (4px base unit), and dark theme overrides | Restrictions: Use CSS custom properties only, follow BEM conventions for variable naming | Success: All design tokens defined, dark theme works via data-theme attribute, consistent with specification_

- [x] 1.3. Create `base.css` with CSS reset and base element styles
  - File: src/cardlink/dashboard/static/css/base.css
  - Implement CSS reset/normalize and base styles for body, headings, links, forms
  - Purpose: Provide consistent baseline styling across browsers
  - _Leverage: tokens.css_
  - _Requirements: Professional Visual Design_
  - _Prompt: Role: Frontend Developer with expertise in cross-browser CSS | Task: Create CSS reset/normalize and base element styles using design tokens, including form elements and scrollbar styling | Restrictions: Use design tokens from tokens.css, ensure cross-browser compatibility | Success: Consistent baseline across Chrome, Firefox, Safari, Edge_

- [x] 1.4. Create `components.css` with BEM-named component styles
  - File: src/cardlink/dashboard/static/css/components.css
  - Style session cards, log entries, alert banners, buttons, modals, form controls
  - Purpose: Provide reusable component styling following design system
  - _Leverage: tokens.css, base.css_
  - _Requirements: Component Styling, Visual States_
  - _Prompt: Role: Frontend Developer specializing in CSS architecture and BEM | Task: Create BEM-named component styles for .session-card, .log-entry, .alert-banner, .btn, .modal, and form controls with all modifiers and states | Restrictions: Follow BEM naming strictly, use design tokens, support light/dark themes | Success: All components styled with proper states (hover, focus, disabled, active)_

- [x] 1.5. Create `utilities.css` with utility classes
  - File: src/cardlink/dashboard/static/css/utilities.css
  - Define text, spacing, display, and layout utility classes
  - Purpose: Provide atomic utility classes for common styling needs
  - _Leverage: tokens.css_
  - _Requirements: Layout, Spacing System_
  - _Prompt: Role: Frontend Developer with expertise in utility-first CSS | Task: Create utility classes for text (alignment, colors, sizes), spacing (margin, padding), display (flex, grid, hidden), and layout (containers, columns) | Restrictions: Use consistent naming conventions, reference design tokens | Success: Utility classes cover common use cases, work with responsive design_

- [x] 1.6. Create `index.html` with semantic structure and layout
  - File: src/cardlink/dashboard/static/index.html
  - Create main HTML page with header, main content panels, and script includes
  - Purpose: Provide semantic HTML structure for dashboard SPA
  - _Leverage: All CSS files, design document architecture_
  - _Requirements: Layout, Accessibility, Keyboard Navigation_
  - _Prompt: Role: Frontend Developer specializing in semantic HTML and accessibility | Task: Create index.html with semantic structure (header, main, panels), include all CSS/JS files, add meta tags, implement loading skeleton | Restrictions: Use semantic HTML5 elements, include proper ARIA labels, ensure keyboard accessibility | Success: Page validates as HTML5, passes basic accessibility checks, layout matches design specification_

### 2. Core JavaScript Infrastructure

- [x] 2.1. Create `state.js` with StateManager class
  - File: src/cardlink/dashboard/static/js/state.js
  - Implement centralized state management with subscriptions and localStorage persistence
  - Purpose: Provide single source of truth for dashboard state
  - _Leverage: Design document StateManager interface_
  - _Requirements: 7.4 (Persist preferences in localStorage)_
  - _Prompt: Role: JavaScript Developer specializing in state management patterns | Task: Create StateManager class with state structure (sessions, logs, alerts, metrics, settings, connection), implement getState/setState with dot notation, subscribe method, loadFromStorage/persistToStorage | Restrictions: Use vanilla JavaScript, immutable updates, no external dependencies | Success: State updates notify subscribers, settings persist across page loads, path-based access works_

- [x] 2.2. Create `websocket.js` with WebSocketClient class
  - File: src/cardlink/dashboard/static/js/websocket.js
  - Implement WebSocket connection with auto-reconnect and message routing
  - Purpose: Provide real-time communication with backend
  - _Leverage: state.js, design document WebSocket protocol_
  - _Requirements: 8.3 (Auto-retry every 5 seconds), 8.4 (Restore subscription)_
  - _Prompt: Role: JavaScript Developer with expertise in WebSocket and real-time applications | Task: Create WebSocketClient with connect(), disconnect(), send(), auto-reconnect with exponential backoff, message routing to StateManager | Restrictions: Handle all WebSocket states, implement heartbeat/ping, update connection status in state | Success: Reconnects automatically on disconnect, routes messages to correct handlers, status updates visible_

- [x] 2.3. Create `api.js` with APIClient class
  - File: src/cardlink/dashboard/static/js/api.js
  - Implement REST API client for sessions, logs, metrics, commands, and export
  - Purpose: Provide data fetching and command sending capabilities
  - _Leverage: design document API endpoints_
  - _Requirements: 6.1-6.5 (Export functionality)_
  - _Prompt: Role: JavaScript Developer with expertise in REST APIs and fetch | Task: Create APIClient class with getSessions(), getSessionLogs(), getMetrics(), sendCommand(), exportLogs() methods | Restrictions: Handle errors with meaningful messages, use fetch API, support query parameters | Success: All API methods work correctly, errors handled gracefully, export generates downloadable files_

- [x] 2.4. Create `app.js` with DashboardApp class
  - File: src/cardlink/dashboard/static/js/app.js
  - Implement main application shell that initializes components and manages lifecycle
  - Purpose: Bootstrap and coordinate all dashboard components
  - _Leverage: state.js, websocket.js, api.js, all components_
  - _Requirements: Usability (Keyboard Shortcuts)_
  - _Prompt: Role: JavaScript Developer with expertise in application architecture | Task: Create DashboardApp with init() method, initialize StateManager/WebSocketClient/APIClient, create and mount UI components, set up keyboard shortcuts, handle theme initialization | Restrictions: Clean initialization sequence, error boundaries for component failures | Success: Dashboard initializes without errors, all components mounted and connected, keyboard shortcuts work_

- [ ] 2.5. Write unit tests for core infrastructure
  - File: tests/unit/dashboard/test_state.js
  - Test StateManager state updates, subscriptions, and localStorage persistence
  - Purpose: Ensure core infrastructure reliability
  - _Leverage: tests/helpers/, state.js, websocket.js, api.js_
  - _Requirements: Reliability_
  - _Prompt: Role: QA Engineer with expertise in JavaScript testing | Task: Write unit tests for StateManager (state updates, subscriptions, persistence), APIClient (request/response handling), WebSocketClient (reconnection logic) | Restrictions: Test in isolation with mocks, cover edge cases | Success: All core methods tested, good coverage, tests run reliably_

### 3. Utility Functions

- [x] 3.1. Create `utils/hex.js` with hex formatting functions
  - File: src/cardlink/dashboard/static/js/utils/hex.js
  - Implement formatHex, parseHex, isValidHex, hexToAscii functions
  - Purpose: Provide hex manipulation utilities for APDU display
  - _Leverage: design document hex utilities_
  - _Requirements: 7.1 (Hex/ASCII toggle)_
  - _Prompt: Role: JavaScript Developer with expertise in binary data handling | Task: Create formatHex(bytes, style) for uppercase/lowercase/grouped, parseHex(string) for string to bytes, isValidHex(string) validation, hexToAscii(hex) preview | Restrictions: Handle edge cases, support all formatting options | Success: All formatting options work correctly, invalid input handled gracefully_

- [x] 3.2. Create `utils/time.js` with time formatting functions
  - File: src/cardlink/dashboard/static/js/utils/time.js
  - Implement formatRelative, formatLocal, formatUTC, formatDuration functions
  - Purpose: Provide human-readable time formatting
  - _Leverage: design document time utilities_
  - _Requirements: 7.2 (Timestamp format selection), Data Presentation_
  - _Prompt: Role: JavaScript Developer with expertise in date/time handling | Task: Create formatRelative(timestamp) for "2 minutes ago", formatLocal/formatUTC for timezone display, formatDuration(ms) for "1.23s" format | Restrictions: Handle edge cases, support all timestamp formats | Success: Times display correctly in all formats, durations human-readable_

- [x] 3.3. Create `utils/apdu.js` with APDU decoding functions
  - File: src/cardlink/dashboard/static/js/utils/apdu.js
  - Implement decodeAPDU, getINSName, getStatusWordMeaning, formatDecodedAPDU functions
  - Purpose: Parse and display APDU commands in human-readable format
  - _Leverage: design document APDU decoder, GP command reference_
  - _Requirements: 3.2 (Decoded command display)_
  - _Prompt: Role: Developer with expertise in smartcard protocols and GlobalPlatform | Task: Create decodeAPDU(hex) to parse CLA/INS/P1/P2/Lc/Data/Le, getINSName(code) for instruction names, getStatusWordMeaning(sw) for status interpretation | Restrictions: Handle malformed APDUs gracefully, cover common GP commands | Success: APDUs decode correctly, status words interpreted accurately_

- [x] 3.4. Create `utils/virtual-scroll.js` with VirtualScroller class
  - File: src/cardlink/dashboard/static/js/utils/virtual-scroll.js
  - Implement virtual scrolling for efficient log display
  - Purpose: Handle 10,000+ log entries without performance degradation
  - _Leverage: design document VirtualScroller interface_
  - _Requirements: Log Capacity (10,000+ entries), Memory Efficiency_
  - _Prompt: Role: JavaScript Developer with expertise in performance optimization and virtualization | Task: Create VirtualScroller with setItems(), appendItems(), scrollToEnd(), scroll event handling, requestAnimationFrame optimization | Restrictions: Only render visible items + buffer, maintain scroll position | Success: Handles 10,000+ items smoothly, scroll performance is 60fps_

### 4. UI Components - Header and Navigation

- [x] 4.1. Implement header with connection status indicator
  - File: src/cardlink/dashboard/static/index.html, src/cardlink/dashboard/static/js/app.js
  - Display connection status (connected/disconnected/reconnecting) and metrics badges
  - Purpose: Show connection status and key metrics at a glance
  - _Leverage: state.js, components.css_
  - _Requirements: 8.1-8.5 (Connection Status), 10.1-10.5 (Health and Metrics)_
  - _Prompt: Role: Frontend Developer specializing in UI components | Task: Implement header with connection status indicator (colored dot), metrics badges (sessions, commands), settings button | Restrictions: Subscribe to state changes for real-time updates, use semantic HTML | Success: Status updates in real-time, metrics refresh automatically_

- [x] 4.2. Create `components/toast.js` with ToastManager class
  - File: src/cardlink/dashboard/static/js/components/toast.js
  - Implement transient notification system for success/error/info messages
  - Purpose: Provide user feedback for actions
  - _Leverage: components.css_
  - _Requirements: Immediate Feedback (100ms), Clear Feedback_
  - _Prompt: Role: Frontend Developer with expertise in UI notifications | Task: Create ToastManager with show(message, type, duration), success/error/info helpers, auto-dismiss with animation, stacking support | Restrictions: Animate in/out smoothly, support multiple concurrent toasts | Success: Toasts appear and dismiss correctly, stack properly, accessible_

### 5. UI Components - Session Panel

- [x] 5.1. Create `components/session-panel.js` with SessionPanel class
  - File: src/cardlink/dashboard/static/js/components/session-panel.js
  - Implement session list with selection and state indicators
  - Purpose: Display active and recent sessions for monitoring
  - _Leverage: state.js, components.css_
  - _Requirements: 1.1-1.5 (Real-Time Session Monitoring), 2.1-2.5 (TLS Handshake Visualization)_
  - _Prompt: Role: Frontend Developer specializing in list components | Task: Create SessionPanel with render(), formatSessionCard(session), selectSession(sessionId), subscribe to sessions state changes | Restrictions: Show active sessions first, visual distinction for states, NULL cipher warning badge | Success: Sessions appear in real-time, selection works, state indicators correct_

- [x] 5.2. Implement session selection and filtering
  - File: src/cardlink/dashboard/static/js/components/session-panel.js
  - Implement selectSession method and APDU log filtering by selected session
  - Purpose: Allow users to focus on specific session's communications
  - _Leverage: state.js, apdu-log.js_
  - _Requirements: 3.3 (Filtering by session)_
  - _Prompt: Role: Frontend Developer with expertise in interactive lists | Task: Implement selectSession(sessionId) to update state, highlight selected card, trigger APDU log filtering | Restrictions: Maintain selection state across updates, clear visual feedback | Success: Clicking session filters logs, selection persists_

- [x] 5.3. Implement empty state for no sessions
  - File: src/cardlink/dashboard/static/js/components/session-panel.js
  - Display helpful message and guidance when no sessions exist
  - Purpose: Guide users when dashboard is empty
  - _Leverage: components.css, Empty States requirements_
  - _Requirements: Empty States (Helpful illustrations and guidance)_
  - _Prompt: Role: UX-focused Frontend Developer | Task: Implement empty state with "No active sessions" message, helpful illustration, guidance text for first-time users | Restrictions: Match design system, be encouraging not confusing | Success: Empty state displays correctly, provides clear next steps_

### 6. UI Components - APDU Log

- [x] 6.1. Create `components/apdu-log.js` with APDULogComponent class
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Implement APDU log display with virtual scrolling and color-coding
  - Purpose: Display communication log efficiently
  - _Leverage: state.js, virtual-scroll.js, apdu.js, hex.js_
  - _Requirements: 3.1-3.5 (APDU Communication Log)_
  - _Prompt: Role: Frontend Developer with expertise in performance-critical components | Task: Create APDULogComponent with render(), formatEntry(entry), integrate VirtualScroller, color-code by direction (blue/green), display status word badges | Restrictions: Handle 10,000+ entries, use virtual scrolling | Success: Logs render efficiently, color-coding correct, status badges display_

- [x] 6.2. Implement log entry formatting with timestamp and hex display
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Format log entries with direction icon, timestamp, command name, hex bytes, status badge
  - Purpose: Provide clear, scannable log display
  - _Leverage: time.js, hex.js, apdu.js_
  - _Requirements: 3.2 (Display direction, timestamp, raw hex, decoded command, status word)_
  - _Prompt: Role: Frontend Developer specializing in data presentation | Task: Format log entries with direction arrow, formatted timestamp, command name, hex bytes (per settings), status word badge with colors | Restrictions: Support all display settings (hex format, timestamp format) | Success: Entries display all required information, formatting matches user settings_

- [x] 6.3. Implement entry selection and action buttons
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Implement click to select, copy and details buttons on hover
  - Purpose: Allow users to interact with individual log entries
  - _Leverage: components.css_
  - _Requirements: 3.4 (Click to show expanded detail view)_
  - _Prompt: Role: Frontend Developer with expertise in interactive components | Task: Implement click handler for selection, highlight selected entry, show copy/details buttons on hover | Restrictions: Maintain keyboard accessibility, clear visual feedback | Success: Entries selectable, buttons appear on hover, actions work_

- [x] 6.4. Implement log filtering toolbar
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Add filter toolbar with direction, status, and search filters
  - Purpose: Allow users to find specific communications
  - _Leverage: state.js_
  - _Requirements: 3.3 (Filtering by session, command type, or status word)_
  - _Prompt: Role: Frontend Developer specializing in filter interfaces | Task: Add filter toolbar with direction dropdown, status filter dropdown, search input, update displayed logs via state | Restrictions: Filters combine logically, persist filter state | Success: All filters work correctly, combine as expected_

- [x] 6.5. Implement auto-scroll behavior
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Auto-scroll to new entries unless user has scrolled up, with toggle button
  - Purpose: Follow live updates while allowing history review
  - _Leverage: virtual-scroll.js, state.js_
  - _Requirements: 3.5 (Auto-scroll unless user scrolled up)_
  - _Prompt: Role: Frontend Developer with expertise in scroll behavior | Task: Implement append() for new entries, detect user scroll-up to disable auto-scroll, provide toggle button, scroll to bottom on new entries when enabled | Restrictions: Smooth scroll behavior, clear toggle state indication | Success: Auto-scroll follows new entries, pauses when user scrolls up, toggle works_

- [x] 6.6. Implement copy to clipboard functionality
  - File: src/cardlink/dashboard/static/js/components/apdu-log.js
  - Copy hex bytes to clipboard on button click with toast confirmation
  - Purpose: Allow easy extraction of APDU data
  - _Leverage: toast.js_
  - _Requirements: Usability_
  - _Prompt: Role: Frontend Developer | Task: Add click handler on copy button, copy hex to clipboard using Clipboard API, show toast "Copied to clipboard" | Restrictions: Handle clipboard API errors gracefully | Success: Clicking copy puts hex in clipboard, toast confirms_

### 7. UI Components - Command Builder

- [x] 7.1. Create `components/command-builder.js` with CommandBuilder class
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Implement command building form with APDU fields and template support
  - Purpose: Enable manual GP command execution
  - _Leverage: state.js, api.js, apdu.js_
  - _Requirements: 4.1-4.5 (Manual RAM Command Interface), 5.1-5.4 (Command Templates)_
  - _Prompt: Role: Frontend Developer with expertise in form components | Task: Create CommandBuilder with render(), APDU field inputs (CLA, INS, P1, P2, Le, Data), template buttons, send button | Restrictions: Validate hex input, disable when no active session | Success: Form renders correctly, fields validate, disabled state works_

- [x] 7.2. Implement command templates
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Define and implement templates for SELECT, GET STATUS, GET DATA, INITIALIZE UPDATE
  - Purpose: Provide quick access to common commands
  - _Leverage: design document templates_
  - _Requirements: 5.1-5.4 (Command Builder Templates)_
  - _Prompt: Role: Developer with expertise in GlobalPlatform commands | Task: Define templates for SELECT (by AID), GET STATUS (ISD, Apps, Load Files), GET DATA, implement applyTemplate(templateName) to populate form | Restrictions: Templates match GP specification, variable fields labeled | Success: Templates populate form correctly, match specified format_

- [x] 7.3. Implement hex input validation and formatting
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Validate hex input, auto-uppercase, real-time feedback
  - Purpose: Ensure valid command construction
  - _Leverage: hex.js_
  - _Requirements: Error Prevention (Validate inputs before submission)_
  - _Prompt: Role: Frontend Developer specializing in form validation | Task: Implement hex input validation, auto-uppercase on input, real-time validation feedback with error messages | Restrictions: Non-blocking validation, clear error indication | Success: Invalid hex rejected, uppercase applied, errors visible_

- [x] 7.4. Implement command preview
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Show real-time hex preview as form fields change
  - Purpose: Show constructed command before sending
  - _Leverage: hex.js_
  - _Requirements: Immediate Feedback_
  - _Prompt: Role: Frontend Developer | Task: Show real-time hex preview that updates on any field change, format hex with spaces | Restrictions: Update preview within 100ms of input | Success: Preview updates in real-time, shows formatted hex_

- [x] 7.5. Implement command sending
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Validate and send command via API, display response
  - Purpose: Execute manual commands and show results
  - _Leverage: api.js, toast.js_
  - _Requirements: 4.3-4.4 (Send through active session, display response inline)_
  - _Prompt: Role: Frontend Developer with expertise in API integration | Task: Implement submit() to validate command, call apiClient.sendCommand(), display response inline, show toast on success/error | Restrictions: Disable send during request, handle errors gracefully | Success: Commands send correctly, response displays, errors show toast_

- [x] 7.6. Implement collapsible panel
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Implement collapsible header with persisted state
  - Purpose: Save screen space when not building commands
  - _Leverage: state.js (settings persistence)_
  - _Requirements: 7.4 (Persist preferences)_
  - _Prompt: Role: Frontend Developer | Task: Implement collapsible header, toggle icon animation, persist collapsed state in settings | Restrictions: Smooth animation, keyboard accessible | Success: Panel collapses/expands, state persists across page loads_

- [x] 7.7. Implement form reset
  - File: src/cardlink/dashboard/static/js/components/command-builder.js
  - Clear button resets all form fields
  - Purpose: Allow users to start fresh
  - _Leverage: None_
  - _Requirements: Usability_
  - _Prompt: Role: Frontend Developer | Task: Add clear button that resets all form fields to defaults | Restrictions: Confirm before clearing if fields have values | Success: Clear button resets form completely_

### 8. UI Components - Alerts and Settings

- [x] 8.1. Implement alert container and banner styles
  - File: src/cardlink/dashboard/static/index.html, src/cardlink/dashboard/static/css/components.css
  - Create alert container in HTML and style alert banners
  - Purpose: Display prominent error and warning alerts
  - _Leverage: design document alert types_
  - _Requirements: 9.1-9.5 (Error and Alert Display)_
  - _Prompt: Role: Frontend Developer | Task: Create alert container in index.html, style .alert-banner with type variants (error, warning, info), icon placement, dismiss button | Restrictions: Follow design system colors, accessible contrast | Success: Alert styles match specification, dismiss button works_

- [x] 8.2. Implement toast notifications for alerts
  - File: src/cardlink/dashboard/static/js/components/toast.js
  - Use toast system for alert notifications with auto-dismiss
  - Purpose: Show transient notifications for events
  - _Leverage: components.css_
  - _Requirements: 9.5 (Show timestamp and allow dismissal)_
  - _Prompt: Role: Frontend Developer | Task: Configure toast types for alerts, auto-dismiss after configurable duration, success/error/warning/info variants | Restrictions: Error alerts persist longer, info auto-dismisses | Success: Toasts display correctly for all alert types_

- [x] 8.3. Create `components/modal.js` with Modal class and settings modal
  - File: src/cardlink/dashboard/static/js/components/modal.js, src/cardlink/dashboard/static/index.html
  - Implement modal dialog for settings with theme, display, and behavior options
  - Purpose: Allow dashboard configuration
  - _Leverage: state.js, components.css_
  - _Requirements: 7.1-7.5 (Dashboard Configuration)_
  - _Prompt: Role: Frontend Developer specializing in modal dialogs | Task: Create Modal class with open/close methods, implement settings modal with theme toggle, hex format, timestamp format, auto-scroll, max entries, export format options | Restrictions: Trap focus in modal, close on Escape, accessible | Success: Settings modal opens/closes, all options work, saves to state_

- [x] 8.4. Implement settings persistence
  - File: src/cardlink/dashboard/static/js/state.js, src/cardlink/dashboard/static/js/app.js
  - Save and load settings from localStorage
  - Purpose: Persist user preferences across sessions
  - _Leverage: state.js_
  - _Requirements: 7.4 (Persist preferences in browser local storage)_
  - _Prompt: Role: Frontend Developer | Task: Implement saveSettings() to localStorage, load settings on app init, apply theme immediately on change | Restrictions: Handle missing/corrupted localStorage gracefully | Success: Settings persist across page loads, theme applies immediately_

- [x] 8.5. Implement modal accessibility
  - File: src/cardlink/dashboard/static/js/components/modal.js
  - Implement focus trap, Escape to close, overlay click to close, focus return
  - Purpose: Ensure modal is accessible
  - _Leverage: None_
  - _Requirements: Keyboard Navigation, Focus Indicators, Screen Reader Support_
  - _Prompt: Role: Frontend Developer specializing in accessibility | Task: Trap focus within modal, close on Escape key, close on overlay click, return focus to trigger element on close | Restrictions: Follow ARIA modal patterns, maintain tab order | Success: Modal fully keyboard accessible, focus trapped correctly_

### 9. Backend - Dashboard Server

- [x] 9.1. Create `server.py` with dashboard HTTP server
  - File: src/cardlink/dashboard/server.py
  - Implement asyncio-based HTTP server with static file serving
  - Purpose: Serve dashboard frontend and API endpoints
  - _Leverage: src/cardlink/server/ patterns_
  - _Requirements: Initial Load (2 seconds)_
  - _Prompt: Role: Python Developer with expertise in asyncio and HTTP servers | Task: Create dashboard HTTP server with static file serving from static/ directory, configurable host/port, DashboardConfig dataclass | Restrictions: Use asyncio, no external web frameworks, efficient static file serving | Success: Server starts and serves static files correctly_

- [x] 9.2. Implement REST API routes
  - File: src/cardlink/dashboard/server.py
  - Implement /api/sessions, /api/sessions/{id}, /api/sessions/{id}/apdus, /api/status endpoints
  - Purpose: Provide data access for dashboard frontend
  - _Leverage: design document API endpoints_
  - _Requirements: 1.2 (Show session ID, PSK identity, cipher suite), 3.2 (APDU log data)_
  - _Prompt: Role: Python Developer with expertise in REST API design | Task: Implement GET /api/sessions, GET /api/sessions/{id}, GET /api/sessions/{id}/apdus, POST /api/sessions, POST /api/sessions/{id}/apdus, GET /api/status | Restrictions: Return JSON, proper HTTP status codes, handle errors | Success: All endpoints return correct data, errors handled_

- [x] 9.3. Implement in-memory state management
  - File: src/cardlink/dashboard/server.py
  - Create DashboardState class with thread-safe session and APDU storage
  - Purpose: Store dashboard state for API and WebSocket
  - _Leverage: None_
  - _Requirements: None (infrastructure)_
  - _Prompt: Role: Python Developer with expertise in concurrent programming | Task: Create DashboardState class with Session and APDUEntry dataclasses, thread-safe operations using asyncio locks | Restrictions: Ensure thread safety for all operations | Success: State operations are thread-safe, data structures correct_

- [x] 9.4. Implement WebSocket handler
  - File: src/cardlink/dashboard/server.py
  - Implement WebSocket upgrade, message framing, broadcast, and keepalive
  - Purpose: Provide real-time updates to connected dashboards
  - _Leverage: design document WebSocket protocol_
  - _Requirements: 1.1 (Display session within 500ms), 3.1 (Display APDU within 100ms)_
  - _Prompt: Role: Python Developer with expertise in WebSocket protocol | Task: Implement WebSocket handshake, text frame message handling, client connection management, broadcast to all clients, ping/pong keepalive | Restrictions: Handle connection errors gracefully, clean disconnect | Success: WebSocket connects, broadcasts events, handles disconnects_

- [x] 9.5. Implement CLI integration
  - File: src/cardlink/cli/dashboard.py, pyproject.toml
  - Create CLI commands for starting, checking status, and opening dashboard
  - Purpose: Provide command-line access to dashboard
  - _Leverage: src/cardlink/cli/ patterns_
  - _Requirements: None (usability)_
  - _Prompt: Role: Python Developer with expertise in CLI tools | Task: Create dashboard.py with gp-dashboard start, status, open commands, add entry point to pyproject.toml, implement emit_apdu() for external integration | Restrictions: Follow existing CLI patterns, proper argument handling | Success: CLI commands work correctly, dashboard accessible_

### 10. Data Presentation and UX

- [x] 10.1. Implement human-readable formats
  - File: src/cardlink/dashboard/static/js/utils/time.js
  - Format timestamps, durations, and byte sizes in human-readable form
  - Purpose: Improve readability of data displays
  - _Leverage: time.js_
  - _Requirements: Data Presentation (Human-Readable Formats)_
  - _Prompt: Role: Frontend Developer specializing in data presentation | Task: Format timestamps as "2 minutes ago" with full date on hover, durations as "1.23s", byte sizes as "1.5 KB", add title attributes for full values | Restrictions: Handle edge cases, maintain precision where needed | Success: All formats human-readable, full values accessible_

- [x] 10.2. Implement inline help and tooltips
  - File: src/cardlink/dashboard/static/js/utils/tooltip.js, src/cardlink/dashboard/static/index.html
  - Add tooltips for technical terms and help icons with explanations
  - Purpose: Guide users on technical concepts
  - _Leverage: components.css_
  - _Requirements: Help and Documentation (Inline Help, Field Descriptions)_
  - _Prompt: Role: UX-focused Frontend Developer | Task: Add tooltips for PSK, APDU, SW terms, field descriptions in command builder, help icons with popover explanations | Restrictions: Tooltips accessible, don't obscure content | Success: Technical terms explained on hover, help icons provide context_

- [x] 10.3. Implement loading states
  - File: src/cardlink/dashboard/static/css/components.css, src/cardlink/dashboard/static/js/components/
  - Add skeleton loaders and spinners for loading states
  - Purpose: Provide visual feedback during loading
  - _Leverage: components.css_
  - _Requirements: Loading States (Skeleton loaders or spinners)_
  - _Prompt: Role: Frontend Developer specializing in loading UX | Task: Add skeleton loaders for initial page load, spinner for command sending, loading indicator for log loading | Restrictions: Smooth transitions, appropriate sizing | Success: Loading states visible during async operations_

- [x] 10.4. Implement empty states
  - File: src/cardlink/dashboard/static/css/components.css, src/cardlink/dashboard/static/js/components/
  - Design and implement empty states for no sessions and no logs
  - Purpose: Guide users when no data exists
  - _Leverage: components.css_
  - _Requirements: Empty States (Helpful illustrations and guidance)_
  - _Prompt: Role: UX-focused Frontend Developer | Task: Design empty state for no sessions, empty state for no logs, include helpful guidance text | Restrictions: Match design system, be encouraging | Success: Empty states display correctly with clear guidance_

- [x] 10.5. Implement error states
  - File: src/cardlink/dashboard/static/css/components.css, src/cardlink/dashboard/static/js/components/
  - Show meaningful error messages with recovery suggestions
  - Purpose: Help users recover from errors
  - _Leverage: components.css_
  - _Requirements: Error States (Clear error messages with recovery suggestions)_
  - _Prompt: Role: UX-focused Frontend Developer | Task: Show meaningful error messages, include recovery suggestions, log errors to console for debugging | Restrictions: Non-technical language for users, technical details in console | Success: Errors display clearly, recovery suggestions helpful_

### 11. Testing

- [ ] 11.1. Write backend unit tests
  - File: tests/unit/dashboard/test_api.py, tests/unit/dashboard/test_export.py, tests/unit/dashboard/test_websocket.py
  - Test API routes, export formatting, WebSocket handling
  - Purpose: Ensure backend reliability
  - _Leverage: tests/helpers/, server.py_
  - _Requirements: Reliability_
  - _Prompt: Role: QA Engineer with expertise in Python testing and pytest | Task: Write unit tests for API route handlers, export formatting (JSON, CSV), WebSocket message handling | Restrictions: Mock external dependencies, test edge cases | Success: All handlers tested, good coverage, tests reliable_

- [ ] 11.2. Write frontend unit tests
  - File: tests/unit/dashboard/test_utils.js
  - Test hex utilities, time utilities, APDU decoder, VirtualScroller
  - Purpose: Ensure utility function reliability
  - _Leverage: tests/helpers/, utils/*.js_
  - _Requirements: Reliability_
  - _Prompt: Role: QA Engineer with expertise in JavaScript testing | Task: Write unit tests for hex utilities, time utilities, APDU decoder, VirtualScroller | Restrictions: Test in isolation, cover edge cases | Success: All utilities tested with good coverage_

- [ ] 11.3. Write integration tests
  - File: tests/integration/test_dashboard.py
  - Test dashboard load, WebSocket events, command flow, export
  - Purpose: Ensure components work together
  - _Leverage: tests/helpers/, server.py_
  - _Requirements: Real-time Latency (500ms)_
  - _Prompt: Role: QA Engineer with expertise in integration testing | Task: Test dashboard loads and connects, session appears on WebSocket event, command sending flow, export download | Restrictions: Test real interactions, handle async operations | Success: All integration scenarios pass, timing requirements met_

- [ ] 11.4. Write E2E tests
  - File: tests/e2e/test_dashboard_e2e.py
  - Test full page load, real-time updates, command workflow, settings persistence
  - Purpose: Validate complete user workflows
  - _Leverage: tests/helpers/_
  - _Requirements: All functional requirements_
  - _Prompt: Role: QA Automation Engineer with expertise in E2E testing | Task: Test full page load and initialization, real-time updates appear, command builder workflow, settings persistence | Restrictions: Test from user perspective, reliable selectors | Success: E2E tests cover critical paths, run reliably_

### 12. Documentation and Polish

- [ ] 12.1. Add keyboard shortcuts documentation
  - File: Documentation/help section
  - Document all keyboard shortcuts, add shortcuts help in settings
  - Purpose: Help users discover keyboard navigation
  - _Leverage: app.js keyboard shortcuts_
  - _Requirements: Keyboard Shortcuts_
  - _Prompt: Role: Technical Writer with expertise in user documentation | Task: Document all keyboard shortcuts, add shortcuts help modal or section in settings | Restrictions: Keep concise, match actual implementation | Success: All shortcuts documented, help accessible from dashboard_

- [ ] 12.2. Add onboarding experience
  - File: src/cardlink/dashboard/static/js/
  - Implement first-run welcome, quick-start steps, feature hints
  - Purpose: Guide new users through dashboard features
  - _Leverage: state.js (first-run detection)_
  - _Requirements: Onboarding (First-Run Guidance, Feature Discovery)_
  - _Prompt: Role: UX Developer specializing in onboarding flows | Task: Implement first-run welcome message with quick-start steps, show feature discovery hints on first use | Restrictions: Non-intrusive, dismissable, don't repeat | Success: New users see helpful guidance, can dismiss and not see again_

- [ ] 12.3. Performance optimization
  - File: src/cardlink/dashboard/static/js/
  - Profile and optimize render performance for large log lists
  - Purpose: Ensure smooth operation with high data volumes
  - _Leverage: virtual-scroll.js_
  - _Requirements: Log Capacity (10,000+ entries), Memory Efficiency_
  - _Prompt: Role: Performance Engineer with expertise in JavaScript optimization | Task: Profile render performance, optimize virtual scrolling for 10,000+ entries, test memory usage over long sessions | Restrictions: Maintain 60fps scrolling, prevent memory leaks | Success: 10,000+ entries scroll smoothly, memory stable_

- [ ] 12.4. Cross-browser testing
  - File: tests/e2e/
  - Test on Chrome, Firefox, Safari, Edge and fix any issues
  - Purpose: Ensure consistent experience across browsers
  - _Leverage: tests/e2e/_
  - _Requirements: Responsive Design (1280px)_
  - _Prompt: Role: QA Engineer with expertise in cross-browser testing | Task: Test on Chrome, Firefox, Safari, Edge, fix browser-specific issues, verify responsive design at 1280px | Restrictions: Document any browser-specific workarounds | Success: Dashboard works consistently across all major browsers_

## Task Dependencies

```
1 (Setup)
├── 2 (Core JS Infrastructure)
│   ├── 3 (Utilities)
│   │   ├── 4 (Header/Navigation)
│   │   ├── 5 (Session Panel)
│   │   ├── 6 (APDU Log)
│   │   └── 7 (Command Builder)
│   └── 8 (Alerts/Settings)
└── 9 (Backend Server)

10 (UX Polish) ← depends on 4-8
11 (Testing) ← depends on all components
12 (Documentation) ← depends on all components
```

## Summary

| Task Group | Tasks | Description | Status |
|------------|-------|-------------|--------|
| Task 1 | 1.1 - 1.6 | Project setup and design system | ✅ Complete |
| Task 2 | 2.1 - 2.5 | Core JavaScript infrastructure | 4/5 Complete |
| Task 3 | 3.1 - 3.4 | Utility functions | ✅ Complete |
| Task 4 | 4.1 - 4.2 | Header and navigation | ✅ Complete |
| Task 5 | 5.1 - 5.3 | Session panel | ✅ Complete |
| Task 6 | 6.1 - 6.6 | APDU log component | ✅ Complete |
| Task 7 | 7.1 - 7.7 | Command builder | ✅ Complete |
| Task 8 | 8.1 - 8.5 | Alerts and settings | ✅ Complete |
| Task 9 | 9.1 - 9.5 | Backend server | ✅ Complete |
| Task 10 | 10.1 - 10.5 | Data presentation and UX | ✅ Complete |
| Task 11 | 11.1 - 11.4 | Testing | 0/4 Complete |
| Task 12 | 12.1 - 12.4 | Documentation and polish | 0/4 Complete |

**Total: 12 task groups, 52 subtasks (43 complete, 9 pending)**
