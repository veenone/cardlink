/**
 * Simulator Panel Component for GP OTA Tester Dashboard
 *
 * Displays network simulator status and controls.
 */

import { state } from '../state.js';
import { api } from '../api.js';
import { showToast } from './toast.js';

/**
 * Creates a simulator panel component.
 * @param {HTMLElement} container - Panel container element
 * @returns {Object} Simulator panel API
 */
export function createSimulatorPanel(container) {
  let isConnecting = false;
  let isStartingCell = false;
  let isStoppingCell = false;

  /**
   * Escapes HTML special characters.
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Formats IMSI for display.
   * @param {string} imsi - IMSI string
   * @returns {string} Formatted IMSI
   */
  function formatImsi(imsi) {
    if (!imsi) return 'Unknown';
    // Format as MCC-MNC-MSIN
    if (imsi.length === 15) {
      return `${imsi.slice(0, 3)}-${imsi.slice(3, 5)}-${imsi.slice(5)}`;
    }
    return imsi;
  }

  /**
   * Gets UE status badge class.
   * @param {string} status - UE status
   * @returns {string} CSS class
   */
  function getUeStatusClass(status) {
    switch (status?.toLowerCase()) {
      case 'registered':
      case 'connected':
        return 'badge--success';
      case 'idle':
        return 'badge--warning';
      case 'detached':
      case 'disconnected':
      default:
        return 'badge--secondary';
    }
  }

  /**
   * Gets cell status badge class.
   * @param {string} status - Cell status
   * @returns {string} CSS class
   */
  function getCellStatusClass(status) {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'badge--success';
      case 'starting':
      case 'stopping':
        return 'badge--warning';
      case 'inactive':
      case 'error':
      default:
        return 'badge--secondary';
    }
  }

  /**
   * Renders the connect form.
   * @returns {string} HTML string
   */
  function renderConnectForm() {
    return `
      <div class="simulator-panel__connect">
        <div class="simulator-panel__field">
          <label for="sim-url" class="text-xs text-secondary">Simulator URL</label>
          <input
            id="sim-url"
            type="text"
            class="simulator-panel__input"
            placeholder="wss://callbox.local:9001"
            value=""
          >
        </div>
        <div class="simulator-panel__field">
          <label for="sim-type" class="text-xs text-secondary">Type</label>
          <select id="sim-type" class="simulator-panel__select">
            <option value="amarisoft">Amarisoft</option>
            <option value="generic">Generic</option>
          </select>
        </div>
        <div class="simulator-panel__field">
          <label for="sim-key" class="text-xs text-secondary">API Key (optional)</label>
          <input
            id="sim-key"
            type="password"
            class="simulator-panel__input"
            placeholder="API key"
          >
        </div>
        <button
          id="sim-connect-btn"
          class="btn btn--primary btn--sm w-full"
          type="button"
          ${isConnecting ? 'disabled' : ''}
        >
          ${isConnecting ? 'Connecting...' : 'Connect'}
        </button>
      </div>
    `;
  }

  /**
   * Renders the connected status.
   * @returns {string} HTML string
   */
  function renderConnectedStatus() {
    const sim = state.get('simulator');
    const cell = sim.cell;

    return `
      <div class="simulator-panel__status">
        <div class="simulator-panel__status-header">
          <span class="badge badge--success">Connected</span>
          <button
            id="sim-disconnect-btn"
            class="btn btn--ghost btn--xs"
            type="button"
            title="Disconnect"
          >
            Disconnect
          </button>
        </div>

        <div class="simulator-panel__info">
          <div class="simulator-panel__info-row">
            <span class="text-xs text-secondary">URL:</span>
            <span class="text-xs">${escapeHtml(sim.url)}</span>
          </div>
          <div class="simulator-panel__info-row">
            <span class="text-xs text-secondary">Type:</span>
            <span class="text-xs">${escapeHtml(sim.simulatorType)}</span>
          </div>
        </div>

        <!-- Cell Status -->
        <div class="simulator-panel__section">
          <div class="simulator-panel__section-header">
            <span class="text-xs font-medium">Cell</span>
            <span class="badge badge--sm ${getCellStatusClass(cell?.status)}">${cell?.status || 'Unknown'}</span>
          </div>
          ${cell ? `
            <div class="simulator-panel__info">
              <div class="simulator-panel__info-row">
                <span class="text-xs text-secondary">PLMN:</span>
                <span class="text-xs">${escapeHtml(cell.plmn || 'N/A')}</span>
              </div>
              <div class="simulator-panel__info-row">
                <span class="text-xs text-secondary">Freq:</span>
                <span class="text-xs">${cell.frequency ? `${cell.frequency} MHz` : 'N/A'}</span>
              </div>
            </div>
          ` : ''}
          <div class="simulator-panel__cell-actions">
            <button
              id="sim-cell-start-btn"
              class="btn btn--secondary btn--xs"
              type="button"
              ${isStartingCell || cell?.status === 'active' ? 'disabled' : ''}
            >
              ${isStartingCell ? 'Starting...' : 'Start Cell'}
            </button>
            <button
              id="sim-cell-stop-btn"
              class="btn btn--secondary btn--xs"
              type="button"
              ${isStoppingCell || cell?.status !== 'active' ? 'disabled' : ''}
            >
              ${isStoppingCell ? 'Stopping...' : 'Stop Cell'}
            </button>
          </div>
        </div>

        <!-- UE Count -->
        <div class="simulator-panel__section">
          <div class="simulator-panel__section-header">
            <span class="text-xs font-medium">UEs</span>
            <span class="badge badge--sm badge--info">${sim.ueCount}</span>
          </div>
          ${renderUEList()}
        </div>

        <!-- SMS Trigger -->
        <div class="simulator-panel__section">
          <div class="simulator-panel__section-header">
            <span class="text-xs font-medium">Send OTA Trigger</span>
          </div>
          <div class="simulator-panel__sms">
            <div class="simulator-panel__field">
              <select id="sim-sms-imsi" class="simulator-panel__select simulator-panel__select--sm">
                <option value="">Select UE...</option>
                ${sim.ues.map(ue => `
                  <option value="${escapeHtml(ue.imsi)}">${formatImsi(ue.imsi)}</option>
                `).join('')}
              </select>
            </div>
            <div class="simulator-panel__field">
              <input
                id="sim-sms-pdu"
                type="text"
                class="simulator-panel__input simulator-panel__input--sm"
                placeholder="PDU hex (optional)"
              >
            </div>
            <button
              id="sim-sms-send-btn"
              class="btn btn--secondary btn--xs"
              type="button"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Renders the UE list.
   * @returns {string} HTML string
   */
  function renderUEList() {
    const sim = state.get('simulator');

    if (!sim.ues || sim.ues.length === 0) {
      return `
        <div class="simulator-panel__empty text-xs text-tertiary">
          No UEs registered
        </div>
      `;
    }

    return `
      <div class="simulator-panel__ue-list">
        ${sim.ues.slice(0, 5).map(ue => `
          <div class="simulator-panel__ue-item">
            <span class="simulator-panel__ue-imsi text-xs">${formatImsi(ue.imsi)}</span>
            <span class="badge badge--xs ${getUeStatusClass(ue.status)}">${ue.status || 'unknown'}</span>
          </div>
        `).join('')}
        ${sim.ues.length > 5 ? `
          <div class="text-xs text-tertiary">+${sim.ues.length - 5} more</div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Renders unavailable state.
   * @returns {string} HTML string
   */
  function renderUnavailable() {
    return `
      <div class="simulator-panel__unavailable">
        <svg class="simulator-panel__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p class="text-xs text-secondary">Network simulator module not available</p>
      </div>
    `;
  }

  /**
   * Main render function.
   */
  function render() {
    const sim = state.get('simulator');
    const isOpen = state.get('ui.simulatorPanelOpen');

    container.innerHTML = `
      <div class="simulator-panel">
        <div class="simulator-panel__header" role="button" tabindex="0" aria-expanded="${isOpen}">
          <h3 class="simulator-panel__title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="14" rx="2"/>
              <path d="M6 7V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>
              <line x1="12" y1="12" x2="12" y2="17"/>
              <line x1="8" y1="12" x2="8" y2="17"/>
              <line x1="16" y1="12" x2="16" y2="17"/>
            </svg>
            Network Simulator
          </h3>
          <div class="simulator-panel__header-status">
            ${sim.connected
              ? '<span class="badge badge--sm badge--success">Online</span>'
              : '<span class="badge badge--sm badge--secondary">Offline</span>'
            }
            <svg class="simulator-panel__toggle ${isOpen ? '' : 'simulator-panel__toggle--collapsed'}" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 6l4 4 4-4"/>
            </svg>
          </div>
        </div>

        <div class="simulator-panel__body ${isOpen ? '' : 'hidden'}">
          ${!sim.available
            ? renderUnavailable()
            : sim.connected
              ? renderConnectedStatus()
              : renderConnectForm()
          }
        </div>
      </div>
    `;

    // Attach event handlers
    attachEventHandlers();
  }

  /**
   * Attaches event handlers to rendered elements.
   */
  function attachEventHandlers() {
    // Toggle panel
    const header = container.querySelector('.simulator-panel__header');
    if (header) {
      header.addEventListener('click', togglePanel);
      header.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          togglePanel();
        }
      });
    }

    // Connect button
    const connectBtn = container.querySelector('#sim-connect-btn');
    if (connectBtn) {
      connectBtn.addEventListener('click', handleConnect);
    }

    // Disconnect button
    const disconnectBtn = container.querySelector('#sim-disconnect-btn');
    if (disconnectBtn) {
      disconnectBtn.addEventListener('click', handleDisconnect);
    }

    // Cell start button
    const cellStartBtn = container.querySelector('#sim-cell-start-btn');
    if (cellStartBtn) {
      cellStartBtn.addEventListener('click', handleCellStart);
    }

    // Cell stop button
    const cellStopBtn = container.querySelector('#sim-cell-stop-btn');
    if (cellStopBtn) {
      cellStopBtn.addEventListener('click', handleCellStop);
    }

    // SMS send button
    const smsSendBtn = container.querySelector('#sim-sms-send-btn');
    if (smsSendBtn) {
      smsSendBtn.addEventListener('click', handleSendSMS);
    }
  }

  /**
   * Toggles panel open/closed state.
   */
  function togglePanel() {
    const isOpen = state.get('ui.simulatorPanelOpen');
    state.set('ui.simulatorPanelOpen', !isOpen);
  }

  /**
   * Handles connect button click.
   */
  async function handleConnect() {
    const urlInput = container.querySelector('#sim-url');
    const typeSelect = container.querySelector('#sim-type');
    const keyInput = container.querySelector('#sim-key');

    const url = urlInput?.value?.trim();
    if (!url) {
      showToast('Please enter a simulator URL', 'error');
      return;
    }

    isConnecting = true;
    render();

    try {
      const config = {
        url,
        simulator_type: typeSelect?.value || 'amarisoft',
      };

      if (keyInput?.value) {
        config.api_key = keyInput.value;
      }

      await api.connectSimulator(config);

      // Update state
      state.update({
        'simulator.connected': true,
        'simulator.url': url,
        'simulator.simulatorType': typeSelect?.value || 'amarisoft',
      });

      showToast('Connected to simulator', 'success');

      // Fetch initial status
      await refreshStatus();

    } catch (error) {
      showToast(`Connection failed: ${error.message}`, 'error');
      state.set('simulator.error', error.message);
    } finally {
      isConnecting = false;
      render();
    }
  }

  /**
   * Handles disconnect button click.
   */
  async function handleDisconnect() {
    try {
      await api.disconnectSimulator();

      state.update({
        'simulator.connected': false,
        'simulator.url': '',
        'simulator.simulatorType': '',
        'simulator.ues': [],
        'simulator.sessions': [],
        'simulator.cell': null,
      });

      showToast('Disconnected from simulator', 'info');

    } catch (error) {
      showToast(`Disconnect failed: ${error.message}`, 'error');
    }
  }

  /**
   * Handles cell start button click.
   */
  async function handleCellStart() {
    isStartingCell = true;
    render();

    try {
      await api.startSimulatorCell({ timeout: 60 });
      showToast('Cell started', 'success');
      await refreshStatus();

    } catch (error) {
      showToast(`Cell start failed: ${error.message}`, 'error');
    } finally {
      isStartingCell = false;
      render();
    }
  }

  /**
   * Handles cell stop button click.
   */
  async function handleCellStop() {
    isStoppingCell = true;
    render();

    try {
      await api.stopSimulatorCell();
      showToast('Cell stopped', 'success');
      await refreshStatus();

    } catch (error) {
      showToast(`Cell stop failed: ${error.message}`, 'error');
    } finally {
      isStoppingCell = false;
      render();
    }
  }

  /**
   * Handles send SMS button click.
   */
  async function handleSendSMS() {
    const imsiSelect = container.querySelector('#sim-sms-imsi');
    const pduInput = container.querySelector('#sim-sms-pdu');

    const imsi = imsiSelect?.value;
    if (!imsi) {
      showToast('Please select a UE', 'error');
      return;
    }

    try {
      const smsData = { imsi };

      if (pduInput?.value?.trim()) {
        smsData.pdu = pduInput.value.trim();
      } else {
        // Send default OTA trigger
        smsData.text = 'OTA_TRIGGER';
      }

      await api.sendSimulatorSMS(smsData);
      showToast('SMS sent', 'success');

      // Clear input
      if (pduInput) pduInput.value = '';

    } catch (error) {
      showToast(`SMS send failed: ${error.message}`, 'error');
    }
  }

  /**
   * Refreshes simulator status from API.
   */
  async function refreshStatus() {
    try {
      const status = await api.getSimulatorStatus();

      state.update({
        'simulator.available': status.available,
        'simulator.connected': status.connected,
        'simulator.authenticated': status.authenticated,
        'simulator.ueCount': status.ue_count || 0,
        'simulator.sessionCount': status.session_count || 0,
        'simulator.cell': status.cell,
        'simulator.error': status.error,
      });

      // If connected, fetch UE list
      if (status.connected) {
        try {
          const ues = await api.getSimulatorUEs();
          state.set('simulator.ues', ues || []);
        } catch (e) {
          console.warn('Failed to fetch UEs:', e);
        }
      }

    } catch (error) {
      console.error('Failed to refresh simulator status:', error);
    }
  }

  /**
   * Handles simulator WebSocket events.
   * @param {string} eventType - Event type
   * @param {Object} data - Event data
   */
  function handleSimulatorEvent(eventType, data) {
    switch (eventType) {
      case 'simulator.connected':
        state.update({
          'simulator.connected': true,
          'simulator.url': data.url || '',
          'simulator.simulatorType': data.simulator_type || '',
        });
        refreshStatus();
        break;

      case 'simulator.disconnected':
        state.update({
          'simulator.connected': false,
          'simulator.ues': [],
          'simulator.cell': null,
        });
        break;

      case 'simulator.ue_registered':
      case 'simulator.ue_deregistered':
        refreshStatus();
        break;

      case 'simulator.cell_started':
      case 'simulator.cell_stopped':
        refreshStatus();
        break;

      case 'simulator.sms_sent':
      case 'simulator.sms_received':
        // Could show notification
        break;

      default:
        // Add to events list
        const events = state.get('simulator.events') || [];
        events.push({
          type: eventType,
          data,
          timestamp: new Date().toISOString(),
        });
        // Keep last 100 events
        state.set('simulator.events', events.slice(-100));
        break;
    }
  }

  // Subscribe to state changes
  state.subscribe('simulator', render);
  state.subscribe('ui.simulatorPanelOpen', render);

  // Initial render
  render();

  // Load initial status
  refreshStatus();

  return {
    render,
    refreshStatus,
    handleSimulatorEvent,

    /**
     * Cleans up the component.
     */
    destroy() {
      container.innerHTML = '';
    },
  };
}
