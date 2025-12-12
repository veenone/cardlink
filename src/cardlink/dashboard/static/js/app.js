/**
 * GP OTA Tester Dashboard - Main Application
 *
 * Entry point that initializes all components and manages application lifecycle.
 */

import { state } from './state.js';
import { wsClient } from './websocket.js';
import { api } from './api.js';
import { createToastManager } from './components/toast.js';
import { createModal } from './components/modal.js';
import { createApduLog } from './components/apdu-log.js';
import { createHttpLog } from './components/http-log.js';
import { createSessionPanel } from './components/session-panel.js';
import { createCommandBuilder } from './components/command-builder.js';
import { createSimulatorPanel } from './components/simulator-panel.js';
import { createCommLog } from './components/comm-log.js';
import { createScriptManager } from './components/script-manager.js';
import { debounce } from './utils/time.js';
import { getTooltipController } from './utils/tooltip.js';

/**
 * Main Dashboard Application
 */
class DashboardApp {
  constructor() {
    this.components = {};
    this.initialized = false;
  }

  /**
   * Initializes the application.
   */
  async init() {
    if (this.initialized) return;

    console.log('Initializing GP OTA Dashboard...');

    // Load saved settings
    state.loadSettings();

    // Initialize theme
    this.initTheme();

    // Initialize components
    this.initComponents();

    // Set up event handlers
    this.setupEventHandlers();

    // Set up WebSocket handlers
    this.setupWebSocket();

    // Connect WebSocket
    this.connect();

    // Load initial data
    await this.loadInitialData();

    this.initialized = true;
    console.log('Dashboard initialized');
  }

  /**
   * Initializes the theme from settings.
   */
  initTheme() {
    const theme = state.get('settings.theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    this.updateThemeIcons(theme);
  }

  /**
   * Updates theme toggle icons.
   * @param {string} theme - Current theme
   */
  updateThemeIcons(theme) {
    const lightIcon = document.querySelector('.theme-icon--light');
    const darkIcon = document.querySelector('.theme-icon--dark');

    if (lightIcon && darkIcon) {
      lightIcon.classList.toggle('hidden', theme === 'dark');
      darkIcon.classList.toggle('hidden', theme === 'light');
    }
  }

  /**
   * Toggles the theme.
   */
  toggleTheme() {
    const current = state.get('settings.theme') || 'light';
    const newTheme = current === 'light' ? 'dark' : 'light';

    state.set('settings.theme', newTheme);
    state.saveSettings();

    document.documentElement.setAttribute('data-theme', newTheme);
    this.updateThemeIcons(newTheme);
  }

  /**
   * Initializes the sidebar toggle functionality.
   */
  initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');

    if (!sidebar || !toggleBtn) return;

    // Load saved sidebar state
    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (isCollapsed) {
      sidebar.classList.add('sidebar--collapsed');
    }

    // Toggle sidebar on button click
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('sidebar--collapsed');
      const collapsed = sidebar.classList.contains('sidebar--collapsed');
      localStorage.setItem('sidebar-collapsed', String(collapsed));
    });
  }

  /**
   * Initializes the view navigation system.
   */
  initNavigation() {
    const navItems = document.querySelectorAll('.sidebar__nav-item[data-view]');
    const views = document.querySelectorAll('.view[data-view]');

    if (!navItems.length || !views.length) return;

    // Store current view
    this.currentView = 'apdu-log';

    // Handle navigation clicks
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const viewName = item.dataset.view;
        this.switchView(viewName);
      });
    });

    // Load saved view from localStorage
    const savedView = localStorage.getItem('dashboard-view');
    if (savedView) {
      this.switchView(savedView);
    }
  }

  /**
   * Switches to a specific view.
   * @param {string} viewName - The view to switch to
   */
  switchView(viewName) {
    const navItems = document.querySelectorAll('.sidebar__nav-item[data-view]');
    const views = document.querySelectorAll('.view[data-view]');

    // Update navigation items
    navItems.forEach(item => {
      const isActive = item.dataset.view === viewName;
      item.classList.toggle('sidebar__nav-item--active', isActive);
      item.setAttribute('aria-current', isActive ? 'page' : 'false');
    });

    // Update views
    views.forEach(view => {
      const isActive = view.dataset.view === viewName;
      view.classList.toggle('view--active', isActive);
    });

    // Store current view
    this.currentView = viewName;
    localStorage.setItem('dashboard-view', viewName);

    // Trigger resize for components that need it
    window.dispatchEvent(new Event('resize'));
  }

  /**
   * Initializes the custom APDU sender functionality.
   */
  initCustomApduSender() {
    const input = document.getElementById('custom-apdu-input');
    const form = document.getElementById('custom-apdu-form');
    const clearBtn = document.getElementById('custom-apdu-clear');
    const lengthEl = document.getElementById('custom-apdu-length');
    const validationEl = document.getElementById('custom-apdu-validation');
    const parsedEl = document.getElementById('custom-apdu-parsed');
    const exampleBtns = document.querySelectorAll('.custom-apdu__example');
    const historyList = document.getElementById('custom-apdu-history-list');
    const clearHistoryBtn = document.getElementById('custom-apdu-clear-history');

    if (!input || !form) return;

    // Load history from localStorage
    this.customApduHistory = JSON.parse(localStorage.getItem('custom-apdu-history') || '[]');
    this.renderApduHistory();

    // Input validation and parsing on keyup
    input.addEventListener('input', () => {
      const value = input.value.replace(/\s/g, '').toUpperCase();
      const byteCount = Math.floor(value.length / 2);
      lengthEl.textContent = `Length: ${byteCount} bytes`;

      // Validate hex input
      const isValidHex = /^[0-9A-F]*$/i.test(value);
      const hasEvenLength = value.length % 2 === 0;

      if (!value) {
        validationEl.textContent = '';
        validationEl.className = 'text-xs text-secondary';
        parsedEl.innerHTML = '';
      } else if (!isValidHex) {
        validationEl.textContent = 'Invalid hex characters';
        validationEl.className = 'text-xs text-danger';
        parsedEl.innerHTML = '';
      } else if (!hasEvenLength) {
        validationEl.textContent = 'Odd number of hex digits';
        validationEl.className = 'text-xs text-warning';
        this.parseApdu(value + '0', parsedEl);
      } else if (byteCount < 4) {
        validationEl.textContent = 'APDU too short (min 4 bytes)';
        validationEl.className = 'text-xs text-warning';
        this.parseApdu(value, parsedEl);
      } else {
        validationEl.textContent = 'Valid APDU';
        validationEl.className = 'text-xs text-success';
        this.parseApdu(value, parsedEl);
      }
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const value = input.value.replace(/\s/g, '').toUpperCase();

      if (value.length < 8 || value.length % 2 !== 0) {
        this.components.toast?.warning('Invalid APDU format');
        return;
      }

      // Add to history
      this.addToApduHistory(value);

      // Send the APDU
      await this.sendApdu(value);
    });

    // Clear button
    clearBtn?.addEventListener('click', () => {
      input.value = '';
      lengthEl.textContent = 'Length: 0 bytes';
      validationEl.textContent = '';
      parsedEl.innerHTML = '';
    });

    // Example buttons
    exampleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const apdu = btn.dataset.apdu;
        if (apdu) {
          input.value = apdu;
          input.dispatchEvent(new Event('input'));
        }
      });
    });

    // Clear history
    clearHistoryBtn?.addEventListener('click', () => {
      this.customApduHistory = [];
      localStorage.removeItem('custom-apdu-history');
      this.renderApduHistory();
    });
  }

  /**
   * Parses an APDU hex string and displays the breakdown.
   * @param {string} hex - The hex string to parse
   * @param {HTMLElement} container - The container to render into
   */
  parseApdu(hex, container) {
    if (!container || hex.length < 8) {
      if (container) container.innerHTML = '';
      return;
    }

    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {
      bytes.push(hex.substr(i, 2));
    }

    const cla = bytes[0];
    const ins = bytes[1];
    const p1 = bytes[2];
    const p2 = bytes[3];
    const hasData = bytes.length > 5;
    const lc = hasData ? bytes[4] : null;
    const data = hasData ? bytes.slice(5, 5 + parseInt(lc || '0', 16)) : [];
    const le = bytes.length > 4 && !hasData ? bytes[4] : (bytes.length > 5 + data.length ? bytes[5 + data.length] : null);

    // Determine APDU Case per ETSI TS 102.221 Annex C
    // Case 1: CLA INS P1 P2 (no data, no Le)
    // Case 2: CLA INS P1 P2 Le (no data, Le present)
    // Case 3: CLA INS P1 P2 Lc Data (data present, no Le)
    // Case 4: CLA INS P1 P2 Lc Data Le (data and Le present)
    let apduCase = 1;
    let apduCaseDesc = 'No data, no response expected';
    if (!hasData && !le) {
      apduCase = 1;
      apduCaseDesc = 'No data, no response expected';
    } else if (!hasData && le) {
      apduCase = 2;
      apduCaseDesc = 'No data, response expected';
    } else if (hasData && !le) {
      apduCase = 3;
      apduCaseDesc = 'Data sent, no response expected';
    } else {
      apduCase = 4;
      apduCaseDesc = 'Data sent, response expected';
    }

    // Instruction name lookup
    const insNames = {
      'A4': 'SELECT',
      'B0': 'READ BINARY',
      'B2': 'READ RECORD',
      'C0': 'GET RESPONSE',
      'CA': 'GET DATA',
      'CB': 'GET DATA',
      'D6': 'UPDATE BINARY',
      'DC': 'UPDATE RECORD',
      'E2': 'STORE DATA',
      'E4': 'DELETE',
      'E6': 'INSTALL',
      'E8': 'LOAD',
      'F0': 'SET STATUS',
      'F2': 'GET STATUS',
      'D8': 'PUT KEY',
      '82': 'EXTERNAL AUTHENTICATE',
      '84': 'GET CHALLENGE',
      '50': 'INIT UPDATE',
    };

    const insName = insNames[ins.toUpperCase()] || 'Unknown';

    container.innerHTML = `
      <div class="custom-apdu__parsed-header">
        <span class="custom-apdu__parsed-name">${insName}</span>
        <span class="apdu-case-badge apdu-case-badge--case${apduCase}" title="${apduCaseDesc}">Case ${apduCase}</span>
      </div>
      <div class="custom-apdu__parsed-grid">
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">CLA</span>
          <span class="custom-apdu__parsed-value">${cla}</span>
        </div>
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">INS</span>
          <span class="custom-apdu__parsed-value">${ins}</span>
        </div>
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">P1</span>
          <span class="custom-apdu__parsed-value">${p1}</span>
        </div>
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">P2</span>
          <span class="custom-apdu__parsed-value">${p2}</span>
        </div>
        ${lc ? `
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">Lc</span>
          <span class="custom-apdu__parsed-value">${lc} (${parseInt(lc, 16)})</span>
        </div>` : ''}
        ${le ? `
        <div class="custom-apdu__parsed-field">
          <span class="custom-apdu__parsed-label">Le</span>
          <span class="custom-apdu__parsed-value">${le}</span>
        </div>` : ''}
      </div>
      ${data.length > 0 ? `
      <div class="custom-apdu__parsed-data">
        <span class="custom-apdu__parsed-label">Data:</span>
        <code class="custom-apdu__parsed-hex">${data.join(' ')}</code>
      </div>` : ''}
    `;
  }

  /**
   * Adds an APDU command to the history.
   * @param {string} apdu - The APDU hex string
   */
  addToApduHistory(apdu) {
    // Remove if already exists
    this.customApduHistory = this.customApduHistory.filter(h => h.apdu !== apdu);

    // Add to front
    this.customApduHistory.unshift({
      apdu,
      timestamp: Date.now()
    });

    // Keep only last 10
    if (this.customApduHistory.length > 10) {
      this.customApduHistory = this.customApduHistory.slice(0, 10);
    }

    // Save to localStorage
    localStorage.setItem('custom-apdu-history', JSON.stringify(this.customApduHistory));

    // Render
    this.renderApduHistory();
  }

  /**
   * Renders the APDU history list.
   */
  renderApduHistory() {
    const historyList = document.getElementById('custom-apdu-history-list');
    const input = document.getElementById('custom-apdu-input');

    if (!historyList) return;

    if (this.customApduHistory.length === 0) {
      historyList.innerHTML = '<p class="text-xs text-secondary">No recent commands</p>';
      return;
    }

    historyList.innerHTML = this.customApduHistory.map(item => {
      const time = new Date(item.timestamp).toLocaleTimeString();
      return `
        <button type="button" class="custom-apdu__history-item" data-apdu="${item.apdu}" title="Click to use">
          <code class="custom-apdu__history-code">${item.apdu}</code>
          <span class="custom-apdu__history-time">${time}</span>
        </button>
      `;
    }).join('');

    // Add click handlers
    historyList.querySelectorAll('.custom-apdu__history-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const apdu = btn.dataset.apdu;
        if (apdu && input) {
          input.value = apdu;
          input.dispatchEvent(new Event('input'));
        }
      });
    });
  }

  /**
   * Initializes UI components.
   */
  initComponents() {
    // Initialize sidebar and navigation first
    this.initSidebar();
    this.initNavigation();
    this.initCustomApduSender();

    // Toast manager
    const toastContainer = document.getElementById('toast-container');
    this.components.toast = createToastManager(toastContainer);

    // Modals
    const settingsModal = document.getElementById('settings-modal');
    const exportModal = document.getElementById('export-modal');
    this.components.settingsModal = createModal(settingsModal);
    this.components.exportModal = createModal(exportModal);

    // Session panel
    const sessionList = document.getElementById('session-list');
    this.components.sessionPanel = createSessionPanel(sessionList);

    // APDU log
    this.components.apduLog = createApduLog({
      viewport: document.getElementById('apdu-viewport'),
      content: document.getElementById('apdu-content'),
      stateContainer: document.getElementById('apdu-state'),
      count: document.getElementById('apdu-count'),
    });

    // Initialize tooltip controller
    this.tooltipController = getTooltipController();

    // Command builder
    this.components.commandBuilder = createCommandBuilder({
      form: document.getElementById('command-form'),
      preview: document.getElementById('cmd-preview'),
      header: document.querySelector('.command-builder__header'),
      body: document.getElementById('command-builder-body'),
    });

    // Simulator panel
    const simulatorContainer = document.getElementById('simulator-panel-container');
    if (simulatorContainer) {
      this.components.simulatorPanel = createSimulatorPanel(simulatorContainer);
    }

    // Communication log
    const commLogContainer = document.getElementById('comm-log-content');
    const commLogEmpty = document.getElementById('comm-log-empty');
    const commLogCount = document.getElementById('comm-log-count');
    if (commLogContainer && commLogEmpty && commLogCount) {
      this.components.commLog = createCommLog({
        container: commLogContainer,
        emptyState: commLogEmpty,
        countEl: commLogCount,
      });

      // Setup comm log header toggle
      const commLogHeader = document.querySelector('.comm-log__header');
      const commLogBody = document.getElementById('comm-log-body');
      const commLogToggle = document.querySelector('.comm-log__toggle');

      commLogHeader?.addEventListener('click', () => {
        const isExpanded = commLogHeader.getAttribute('aria-expanded') === 'true';
        commLogHeader.setAttribute('aria-expanded', String(!isExpanded));
        commLogBody?.classList.toggle('hidden', isExpanded);
        commLogToggle?.classList.toggle('comm-log__toggle--collapsed', isExpanded);
      });
    }

    // HTTP log
    const httpLogContainer = document.getElementById('http-log-container');
    const httpLogEmpty = document.getElementById('http-log-empty');
    const httpLogContent = document.getElementById('http-log-content');
    if (httpLogContainer && httpLogEmpty && httpLogContent) {
      this.components.httpLog = createHttpLog({
        container: httpLogContainer,
        emptyState: httpLogEmpty,
        content: httpLogContent,
      });
    }

    // Script manager
    const scriptManagerContainer = document.getElementById('script-manager-container');
    if (scriptManagerContainer) {
      this.components.scriptManager = createScriptManager(scriptManagerContainer);
    }

    // Setup tab switching for APDU/HTTP tabs
    this.setupCommLogTabs();
  }

  /**
   * Sets up tab switching for communication log tabs.
   */
  setupCommLogTabs() {
    const tabs = document.querySelectorAll('.comm-log__tab');
    const apduPanel = document.getElementById('comm-tab-apdu');
    const httpPanel = document.getElementById('comm-tab-http');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const tabType = tab.dataset.tab;

        // Update tab states
        tabs.forEach(t => {
          const isActive = t.dataset.tab === tabType;
          t.classList.toggle('comm-log__tab--active', isActive);
          t.setAttribute('aria-selected', String(isActive));
        });

        // Update panel visibility
        if (tabType === 'apdu') {
          apduPanel?.classList.remove('hidden');
          httpPanel?.classList.add('hidden');
        } else {
          apduPanel?.classList.add('hidden');
          httpPanel?.classList.remove('hidden');
          // Refresh HTTP log when switching to it
          this.components.httpLog?.refresh();
        }
      });
    });
  }

  /**
   * Sets up event handlers.
   */
  setupEventHandlers() {
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle?.addEventListener('click', () => this.toggleTheme());

    // Settings button
    const settingsBtn = document.getElementById('settings-btn');
    settingsBtn?.addEventListener('click', () => this.components.settingsModal.open());

    // Save settings
    const saveSettingsBtn = document.getElementById('save-settings');
    saveSettingsBtn?.addEventListener('click', () => this.saveSettings());

    // Refresh sessions
    const refreshBtn = document.getElementById('refresh-sessions');
    refreshBtn?.addEventListener('click', () => this.loadSessions());

    // Search input (debounced)
    const searchInput = document.getElementById('search-input');
    searchInput?.addEventListener('input', debounce((e) => {
      state.set('filters.search', e.target.value);
    }, 300));

    // Filter dropdowns
    const filterDirection = document.getElementById('filter-direction');
    filterDirection?.addEventListener('change', (e) => {
      state.set('filters.direction', e.target.value);
    });

    const filterStatus = document.getElementById('filter-status');
    filterStatus?.addEventListener('change', (e) => {
      state.set('filters.status', e.target.value);
    });

    // Export button
    const exportBtn = document.getElementById('export-btn');
    exportBtn?.addEventListener('click', () => this.components.exportModal.open());

    // Do export
    const doExportBtn = document.getElementById('do-export');
    doExportBtn?.addEventListener('click', () => this.exportLogs());

    // Clear button
    const clearBtn = document.getElementById('clear-btn');
    clearBtn?.addEventListener('click', () => this.clearLogs());

    // Auto-scroll button for APDU Log
    const autoScrollBtn = document.getElementById('auto-scroll-btn');
    autoScrollBtn?.addEventListener('click', () => {
      const current = this.components.apduLog.isAutoScroll();
      this.components.apduLog.setAutoScroll(!current);
      autoScrollBtn.setAttribute('aria-pressed', String(!current));
      autoScrollBtn.title = !current ? 'Auto-scroll enabled' : 'Auto-scroll disabled';
      autoScrollBtn.classList.toggle('btn--active', !current);
    });

    // Auto-scroll button for Communication Log
    const commAutoScrollBtn = document.getElementById('comm-auto-scroll-btn');
    commAutoScrollBtn?.addEventListener('click', () => {
      const current = this.components.commLog.isAutoScroll();
      this.components.commLog.setAutoScroll(!current);
      commAutoScrollBtn.setAttribute('aria-pressed', String(!current));
      commAutoScrollBtn.title = !current ? 'Auto-scroll enabled' : 'Auto-scroll disabled';
      commAutoScrollBtn.classList.toggle('btn--active', !current);
    });

    // Export format tabs
    document.querySelectorAll('#export-modal [data-format]').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('#export-modal [data-format]').forEach(t => {
          t.classList.remove('tabs__tab--active');
        });
        tab.classList.add('tabs__tab--active');
      });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Ctrl+F - Focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        searchInput?.focus();
      }

      // Escape - Clear search / close modal
      if (e.key === 'Escape') {
        if (searchInput === document.activeElement) {
          searchInput.value = '';
          state.set('filters.search', '');
        }
      }
    });

    // Custom events
    window.addEventListener('toast', (e) => {
      const { type, message, duration } = e.detail;
      this.components.toast[type]?.(message, duration) || this.components.toast.info(message, duration);
    });

    window.addEventListener('session-select', async (e) => {
      const { sessionId } = e.detail;
      await this.loadSessionData(sessionId);
    });

    window.addEventListener('session-closed', () => {
      // Clear session details when session is closed
      this.updateSessionDetails(null);
    });

    window.addEventListener('apdu-send', async (e) => {
      const { apdu, payloadFormat } = e.detail;
      await this.sendApdu(apdu, true, payloadFormat);
    });

    // Script manager events
    window.addEventListener('show-toast', (e) => {
      const { message, type } = e.detail;
      this.components.toast?.[type]?.(message) || this.components.toast?.info(message);
    });

    window.addEventListener('show-modal', (e) => {
      const { title, content } = e.detail;
      this.showDynamicModal(title, content);
    });

    // Retry event handlers
    window.addEventListener('sessions-retry', () => {
      this.loadSessions();
    });

    window.addEventListener('logs-retry', () => {
      const sessionId = state.get('activeSessionId');
      if (sessionId) {
        this.loadSessionData(sessionId);
      }
    });

    // Connection state changes
    state.subscribe('connection.status', (s, path) => {
      this.updateConnectionStatus(state.get('connection.status'));
    });
  }

  /**
   * Sets up WebSocket message handlers.
   */
  setupWebSocket() {
    // APDU events
    wsClient.onMessage('apdu', (payload) => {
      state.addApdu({
        id: payload.id || Date.now().toString(),
        timestamp: payload.timestamp || Date.now(),
        direction: payload.direction,
        data: payload.data,
        sw: payload.sw,
        responseData: payload.responseData,
        sessionId: payload.sessionId,
        http: payload.http || null,
      });
    });

    // Session events
    wsClient.onMessage('session.created', (payload) => {
      state.addSession(payload);
      this.components.toast.info(`New session: ${payload.name || payload.id}`);
    });

    wsClient.onMessage('session.updated', (payload) => {
      state.updateSession(payload.id, payload);
    });

    // Handle session_updated event from AdminServer (with identifiers)
    wsClient.onMessage('session_updated', (payload) => {
      // Extract session from payload (server sends {session: {...}})
      const session = payload.session || payload;
      if (session && session.id) {
        state.updateSession(session.id, session);
        // Refresh details if this is the active session
        const activeId = state.get('activeSessionId');
        if (session.id === activeId) {
          this.updateSessionDetails(session);
        }
      }
    });

    wsClient.onMessage('session.deleted', (payload) => {
      state.removeSession(payload.id);
    });

    // Simulator events
    wsClient.onMessage('simulator.connected', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.connected', payload);
    });

    wsClient.onMessage('simulator.disconnected', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.disconnected', payload);
    });

    wsClient.onMessage('simulator.ue_registered', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.ue_registered', payload);
    });

    wsClient.onMessage('simulator.ue_deregistered', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.ue_deregistered', payload);
    });

    wsClient.onMessage('simulator.cell_started', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.cell_started', payload);
    });

    wsClient.onMessage('simulator.cell_stopped', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.cell_stopped', payload);
    });

    wsClient.onMessage('simulator.sms_sent', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.sms_sent', payload);
    });

    wsClient.onMessage('simulator.sms_received', (payload) => {
      this.components.simulatorPanel?.handleSimulatorEvent('simulator.sms_received', payload);
    });

    // Connection events
    wsClient.on('open', () => {
      this.components.toast.success('Connected to server');
      this.loadSessions();
    });

    wsClient.on('close', ({ wasClean, reason }) => {
      if (!wasClean) {
        this.components.toast.warning('Connection lost. Reconnecting...');
      }
    });

    wsClient.on('error', () => {
      this.components.toast.error('Connection error');
    });
  }

  /**
   * Connects to the WebSocket server.
   */
  async connect() {
    try {
      await wsClient.connect();
    } catch (error) {
      console.error('WebSocket connection failed:', error);
    }
  }

  /**
   * Updates the connection status display.
   * @param {string} status - Connection status
   */
  updateConnectionStatus(status) {
    const statusEl = document.getElementById('connection-status');
    if (!statusEl) return;

    statusEl.className = `header__status header__status--${status}`;

    const statusText = statusEl.querySelector('.header__status-text');
    if (statusText) {
      statusText.textContent = 'WS: ' + status.charAt(0).toUpperCase() + status.slice(1);
    }
  }

  /**
   * Updates the TLS PSK server status display.
   * @param {Object} serverStatus - Server status object
   */
  updateServerStatus(serverStatus) {
    const statusEl = document.getElementById('server-status');
    if (!statusEl) return;

    const isConnected = serverStatus.connected && serverStatus.running;
    const statusClass = isConnected ? 'connected' : 'disconnected';
    statusEl.className = `header__status header__status--${statusClass}`;

    const statusText = statusEl.querySelector('.header__status-text');
    if (statusText) {
      if (!serverStatus.available) {
        statusText.textContent = 'Server: N/A';
      } else if (!serverStatus.connected) {
        statusText.textContent = 'Server: Not Connected';
      } else if (!serverStatus.running) {
        statusText.textContent = 'Server: Stopped';
      } else {
        const sessions = serverStatus.activeSessions || 0;
        statusText.textContent = `Server: ${serverStatus.host}:${serverStatus.port} (${sessions} sessions)`;
      }
    }
  }

  /**
   * Loads TLS PSK server status.
   */
  async loadServerStatus() {
    try {
      const status = await api.getServerStatus();
      this.updateServerStatus(status);
    } catch (error) {
      console.error('Failed to load server status:', error);
      this.updateServerStatus({ available: true, connected: false, running: false });
    }
  }

  /**
   * Starts polling for server status.
   */
  startServerStatusPolling() {
    // Poll every 5 seconds
    this.serverStatusInterval = setInterval(() => {
      this.loadServerStatus();
    }, 5000);
  }

  /**
   * Loads initial data.
   */
  async loadInitialData() {
    await Promise.all([
      this.loadSessions(),
      this.loadServerStatus(),
    ]);
    // Start polling for server status
    this.startServerStatusPolling();
  }

  /**
   * Loads sessions from API.
   */
  async loadSessions() {
    this.components.sessionPanel?.setLoading(true);

    try {
      const sessions = await api.getSessions();
      state.set('sessions', sessions);
      this.components.sessionPanel?.setError(null);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      this.components.sessionPanel?.setError(error.message || 'Failed to load sessions');
      // Use empty array on error
      state.set('sessions', []);
    } finally {
      this.components.sessionPanel?.setLoading(false);
    }
  }

  /**
   * Loads data for a specific session.
   * @param {string} sessionId - Session ID
   */
  async loadSessionData(sessionId) {
    this.components.apduLog?.setLoading(true);

    try {
      // Load APDUs
      const apdus = await api.getApdus(sessionId);
      state.set('apdus', apdus);
      this.components.apduLog?.setError(null);

      // Load session details and update the session details view
      const session = await api.getSession(sessionId);
      this.updateSessionDetails(session, apdus);
    } catch (error) {
      console.error('Failed to load session data:', error);
      this.components.apduLog?.setError(error.message || 'Failed to load session data');
      this.components.toast.error('Failed to load session data');
    } finally {
      this.components.apduLog?.setLoading(false);
    }
  }

  /**
   * Updates the session details view with session data.
   * @param {Object} session - Session data
   * @param {Array} apdus - APDU history
   */
  updateSessionDetails(session, apdus = []) {
    const emptyEl = document.getElementById('session-details-empty');
    const contentEl = document.getElementById('session-details-content');

    if (!session) {
      // Show empty state
      emptyEl?.classList.remove('hidden');
      contentEl?.classList.add('hidden');
      return;
    }

    // Hide empty state, show content
    emptyEl?.classList.add('hidden');
    contentEl?.classList.remove('hidden');

    // Helper to safely set text content
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value ?? '-';
    };

    // Session Information
    setText('session-detail-id', session.id || '-');
    setText('session-detail-status', this.formatStatus(session.status));
    setText('session-detail-created', this.formatDateTime(session.createdAt || session.created_at));
    setText('session-detail-last-activity', this.formatDateTime(session.updatedAt || session.updated_at));
    setText('session-detail-duration', this.formatDuration(session.createdAt || session.created_at));

    // Connection Details
    const clientAddr = session.metadata?.client_ip || session.client_ip || session.metadata?.clientIp || '-';
    const [clientIp, clientPort] = clientAddr.includes(':') ? clientAddr.split(':') : [clientAddr, '-'];
    setText('session-detail-client-ip', clientIp);
    setText('session-detail-client-port', clientPort);
    setText('session-detail-psk-identity', session.metadata?.psk_identity || session.psk_identity || session.metadata?.pskIdentity || '-');
    setText('session-detail-tls-version', session.tlsVersion || session.tls_version || session.metadata?.tls_version || '-');
    setText('session-detail-cipher', session.cipherSuite || session.cipher_suite || session.metadata?.cipher_suite || '-');

    // Statistics
    const totalCmds = apdus?.length || session.apduCount || session.apdu_count || 0;
    const successCount = apdus?.filter(a => {
      const sw = a.sw || '';
      return sw.startsWith('90') || sw.startsWith('61');
    }).length || 0;
    const errorCount = totalCmds - successCount;
    setText('session-detail-total-cmds', totalCmds.toString());
    setText('session-detail-success', successCount.toString());
    setText('session-detail-errors', errorCount.toString());
    setText('session-detail-avg-time', '-'); // Would require timing data

    // Card Information (per GP Amendment B / ETSI TS 102.226)
    // Identifiers extracted from X-Admin-From header URI
    const iccid = session.iccid || session.metadata?.iccid || '-';
    const eid = session.eid || session.metadata?.eid || '-';
    const imei = session.imei || session.metadata?.imei || '-';
    const seid = session.seid || session.metadata?.seid || '-';
    setText('session-detail-iccid', iccid);
    setText('session-detail-eid', eid);
    setText('session-detail-imei', imei);
    setText('session-detail-seid', seid);
    setText('session-detail-tar', session.metadata?.tar || '-');
  }

  /**
   * Formats session status for display.
   * @param {string} status - Status value
   * @returns {string} Formatted status
   */
  formatStatus(status) {
    if (!status) return '-';
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  }

  /**
   * Formats a date/time value for display.
   * @param {string|number|Date} value - Date value
   * @returns {string} Formatted date string
   */
  formatDateTime(value) {
    if (!value) return '-';
    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) return '-';
      return date.toLocaleString();
    } catch {
      return '-';
    }
  }

  /**
   * Formats duration from start time to now.
   * @param {string|number|Date} startTime - Start time
   * @returns {string} Formatted duration
   */
  formatDuration(startTime) {
    if (!startTime) return '-';
    try {
      const start = new Date(startTime);
      if (isNaN(start.getTime())) return '-';
      const durationMs = Date.now() - start.getTime();
      const seconds = Math.floor(durationMs / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);

      if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
      } else {
        return `${seconds}s`;
      }
    } catch {
      return '-';
    }
  }

  /**
   * Sends an APDU command.
   * @param {string} apdu - APDU hex string
   * @param {boolean} [manual=true] - Whether this is a manually sent APDU
   * @param {string} [payloadFormat='auto'] - Payload format (compact, expanded_definite, expanded_indefinite)
   */
  async sendApdu(apdu, manual = true, payloadFormat = 'auto') {
    const sessionId = state.get('activeSessionId');

    if (!sessionId) {
      this.components.toast.warning('No session selected');
      return;
    }

    try {
      await api.sendApdu(sessionId, { data: apdu, manual, payloadFormat });
      this.components.toast.success('Command sent');
    } catch (error) {
      console.error('Failed to send APDU:', error);
      this.components.toast.error('Failed to send command');
    }
  }

  /**
   * Exports logs to file.
   */
  async exportLogs() {
    const sessionId = state.get('activeSessionId');
    const format = document.querySelector('#export-modal [data-format].tabs__tab--active')?.dataset.format || 'json';
    const filename = document.getElementById('export-filename')?.value || 'apdu-log';

    try {
      let data;
      const apdus = state.getFilteredApdus();

      if (format === 'json') {
        data = JSON.stringify(apdus, null, 2);
      } else if (format === 'csv') {
        const headers = ['timestamp', 'direction', 'data', 'sw'];
        const rows = apdus.map(a => [
          new Date(a.timestamp).toISOString(),
          a.direction,
          a.data,
          a.sw || '',
        ]);
        data = [headers, ...rows].map(r => r.join(',')).join('\n');
      } else {
        data = apdus.map(a => {
          const time = new Date(a.timestamp).toISOString();
          const dir = a.direction === 'command' ? '>>' : '<<';
          return `[${time}] ${dir} ${a.data}${a.sw ? ' [' + a.sw + ']' : ''}`;
        }).join('\n');
      }

      // Download file
      const blob = new Blob([data], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}.${format === 'json' ? 'json' : format === 'csv' ? 'csv' : 'txt'}`;
      a.click();
      URL.revokeObjectURL(url);

      this.components.exportModal.close();
      this.components.toast.success('Logs exported');
    } catch (error) {
      console.error('Export failed:', error);
      this.components.toast.error('Export failed');
    }
  }

  /**
   * Clears the current log.
   */
  clearLogs() {
    state.clearApdus();
    this.components.apduLog.clear();
    this.components.commLog?.clear();
    this.components.httpLog?.clear();
    this.components.toast.info('Logs cleared');
  }

  /**
   * Shows a dynamic modal with custom content.
   * @param {string} title - Modal title
   * @param {string} content - HTML content
   */
  showDynamicModal(title, content) {
    // Create or reuse dynamic modal
    let modal = document.getElementById('dynamic-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'dynamic-modal';
      modal.className = 'modal';
      modal.innerHTML = `
        <div class="modal__overlay"></div>
        <div class="modal__container">
          <div class="modal__header">
            <h3 class="modal__title"></h3>
            <button class="modal__close" type="button" aria-label="Close modal">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3l10 10M13 3l-10 10"/>
              </svg>
            </button>
          </div>
          <div class="modal__content"></div>
        </div>
      `;
      document.body.appendChild(modal);

      // Close handlers
      const closeModal = () => modal.classList.remove('modal--active');
      modal.querySelector('.modal__overlay').addEventListener('click', closeModal);
      modal.querySelector('.modal__close').addEventListener('click', closeModal);

      // Escape key handler
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('modal--active')) {
          closeModal();
        }
      });
    }

    // Update content
    modal.querySelector('.modal__title').textContent = title;
    modal.querySelector('.modal__content').innerHTML = content;

    // Show modal
    modal.classList.add('modal--active');
  }

  /**
   * Saves settings from the modal.
   */
  saveSettings() {
    const wsUrl = document.getElementById('ws-url')?.value;
    const autoReconnect = document.getElementById('auto-reconnect')?.checked;
    const showTimestamps = document.getElementById('show-timestamps')?.checked;
    const highlightErrors = document.getElementById('highlight-errors')?.checked;
    const groupPairs = document.getElementById('group-pairs')?.checked;
    const alertPatternsText = document.getElementById('alert-patterns')?.value || '';
    const soundAlerts = document.getElementById('sound-alerts')?.checked;

    const alertPatterns = alertPatternsText
      .split('\n')
      .map(p => p.trim())
      .filter(p => p.length > 0);

    state.update({
      'settings.wsUrl': wsUrl,
      'settings.autoReconnect': autoReconnect,
      'settings.showTimestamps': showTimestamps,
      'settings.highlightErrors': highlightErrors,
      'settings.groupPairs': groupPairs,
      'settings.alertPatterns': alertPatterns,
      'settings.soundAlerts': soundAlerts,
    });

    state.saveSettings();
    wsClient.setAutoReconnect(autoReconnect);

    this.components.settingsModal.close();
    this.components.toast.success('Settings saved');
  }

  /**
   * Destroys the application.
   */
  destroy() {
    wsClient.disconnect();
    this.components.apduLog?.destroy();
  }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new DashboardApp();
  window.app.init();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
  window.app?.destroy();
});

export { DashboardApp };
