/**
 * Communication Log Component for GP OTA Tester Dashboard
 *
 * Displays the APDU exchange between server and client in a visual format
 * showing the back-and-forth communication flow.
 */

import { state } from '../state.js';

/**
 * Creates a communication log component.
 * @param {Object} options - Component options
 * @param {HTMLElement} options.container - Container element for entries
 * @param {HTMLElement} options.emptyState - Empty state element
 * @param {HTMLElement} options.countEl - Element to display exchange count
 * @returns {Object} Communication log API
 */
export function createCommLog(options) {
  const { container, emptyState, countEl } = options;

  let exchanges = [];
  let currentSessionId = null;

  /**
   * Formats timestamp for display.
   * @param {number} timestamp - Unix timestamp in ms
   * @returns {string} Formatted time string
   */
  function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }) + '.' + String(date.getMilliseconds()).padStart(3, '0');
  }

  /**
   * Formats hex data for display with spacing.
   * @param {string} hex - Hex string
   * @param {number} maxLen - Maximum display length
   * @returns {string} Formatted hex string
   */
  function formatHex(hex, maxLen = 64) {
    if (!hex) return '';
    const formatted = hex.toUpperCase().replace(/(.{2})/g, '$1 ').trim();
    if (formatted.length > maxLen) {
      return formatted.substring(0, maxLen - 3) + '...';
    }
    return formatted;
  }

  /**
   * Parses APDU command details.
   * @param {string} hex - C-APDU hex string
   * @returns {Object} Parsed APDU details
   */
  function parseCommand(hex) {
    if (!hex || hex.length < 8) return { ins: 'UNKNOWN', description: '' };

    const cla = hex.substring(0, 2).toUpperCase();
    const ins = hex.substring(2, 4).toUpperCase();

    const insNames = {
      'A4': 'SELECT',
      'B0': 'READ BINARY',
      'B2': 'READ RECORD',
      'CA': 'GET DATA',
      'CB': 'GET DATA',
      'D6': 'UPDATE BINARY',
      'DC': 'UPDATE RECORD',
      'E2': 'STORE DATA',
      'F0': 'MANAGE CHANNEL',
      'F2': 'GET STATUS',
      '10': 'TERMINAL PROFILE',
      '12': 'FETCH',
      '14': 'TERMINAL RESPONSE',
      'C0': 'GET RESPONSE',
      '82': 'EXTERNAL AUTH',
      '84': 'GET CHALLENGE',
      '88': 'INTERNAL AUTH',
      '50': 'INIT UPDATE',
      '78': 'END R-MAC',
      'D8': 'PUT KEY',
      'E4': 'DELETE',
      'E6': 'INSTALL',
      'E8': 'LOAD',
    };

    return {
      cla,
      ins,
      name: insNames[ins] || `INS ${ins}`,
      description: `CLA=${cla} INS=${ins}`,
    };
  }

  /**
   * Parses status word.
   * @param {string} sw - Status word hex string (4 chars)
   * @returns {Object} Parsed status details
   */
  function parseStatus(sw) {
    if (!sw) return { status: 'unknown', description: '' };

    const swUpper = sw.toUpperCase();
    const sw1 = swUpper.substring(0, 2);

    if (swUpper === '9000') {
      return { status: 'success', description: 'Success' };
    } else if (sw1 === '91') {
      return { status: 'success', description: `Proactive command (${swUpper.substring(2, 4)} bytes)` };
    } else if (sw1 === '61') {
      return { status: 'success', description: `More data (${swUpper.substring(2, 4)} bytes)` };
    } else if (sw1 === '6C') {
      return { status: 'warning', description: `Wrong Le (expected ${swUpper.substring(2, 4)})` };
    } else if (swUpper === '6A82') {
      return { status: 'error', description: 'File not found' };
    } else if (swUpper === '6A86') {
      return { status: 'error', description: 'Incorrect P1P2' };
    } else if (swUpper === '6D00') {
      return { status: 'error', description: 'INS not supported' };
    } else if (swUpper === '6E00') {
      return { status: 'error', description: 'CLA not supported' };
    } else if (sw1 === '6A') {
      return { status: 'error', description: `Error ${swUpper}` };
    } else if (sw1.startsWith('6')) {
      return { status: 'warning', description: `Warning ${swUpper}` };
    }

    return { status: 'unknown', description: swUpper };
  }

  /**
   * Creates an exchange entry element.
   * @param {Object} exchange - Exchange data
   * @param {number} index - Exchange index
   * @returns {HTMLElement} Exchange element
   */
  function createExchangeElement(exchange, index) {
    const { command, response, timestamp } = exchange;
    const parsedCmd = parseCommand(command?.data);
    const parsedStatus = parseStatus(response?.sw);

    const el = document.createElement('div');
    el.className = 'comm-exchange';
    el.dataset.index = index;

    // Calculate response time if both timestamps available
    let responseTime = '';
    if (command?.timestamp && response?.timestamp) {
      const diff = response.timestamp - command.timestamp;
      responseTime = `${diff}ms`;
    }

    el.innerHTML = `
      <div class="comm-exchange__header">
        <span class="comm-exchange__index">#${index + 1}</span>
        <span class="comm-exchange__time">${formatTime(timestamp)}</span>
        <span class="comm-exchange__cmd-name">${parsedCmd.name}</span>
        ${responseTime ? `<span class="comm-exchange__duration">${responseTime}</span>` : ''}
      </div>

      <div class="comm-exchange__flow">
        <div class="comm-exchange__side comm-exchange__side--server">
          <div class="comm-exchange__label">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <rect x="1" y="2" width="10" height="8" rx="1"/>
            </svg>
            Server
          </div>
          <div class="comm-exchange__message comm-exchange__message--command">
            <div class="comm-exchange__data" title="${command?.data || ''}">${formatHex(command?.data)}</div>
            <div class="comm-exchange__info">${parsedCmd.description}</div>
          </div>
        </div>

        <div class="comm-exchange__arrow">
          <svg width="40" height="20" viewBox="0 0 40 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M2 10h36M34 5l4 5-4 5"/>
          </svg>
        </div>

        <div class="comm-exchange__side comm-exchange__side--client">
          <div class="comm-exchange__label">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <rect x="2" y="1" width="8" height="10" rx="1"/>
            </svg>
            Client
          </div>
        </div>
      </div>

      ${response ? `
      <div class="comm-exchange__flow comm-exchange__flow--response">
        <div class="comm-exchange__side comm-exchange__side--server"></div>

        <div class="comm-exchange__arrow comm-exchange__arrow--response">
          <svg width="40" height="20" viewBox="0 0 40 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M38 10H2M6 5l-4 5 4 5"/>
          </svg>
        </div>

        <div class="comm-exchange__side comm-exchange__side--client">
          <div class="comm-exchange__message comm-exchange__message--response comm-exchange__message--${parsedStatus.status}">
            <div class="comm-exchange__data" title="${response.data || ''}">${formatHex(response.data)}</div>
            <div class="comm-exchange__status">
              <span class="comm-exchange__sw">${response.sw || ''}</span>
              <span class="comm-exchange__status-text">${parsedStatus.description}</span>
            </div>
          </div>
        </div>
      </div>
      ` : `
      <div class="comm-exchange__pending">
        <span class="comm-exchange__spinner"></span>
        Awaiting response...
      </div>
      `}
    `;

    return el;
  }

  /**
   * Groups APDUs into command/response exchanges.
   * @param {Array} apdus - List of APDU entries
   * @returns {Array} List of exchanges
   */
  function groupIntoExchanges(apdus) {
    const result = [];
    let currentExchange = null;

    for (const apdu of apdus) {
      if (apdu.direction === 'command') {
        // Start a new exchange
        if (currentExchange) {
          result.push(currentExchange);
        }
        currentExchange = {
          id: apdu.id,
          timestamp: apdu.timestamp,
          command: apdu,
          response: null,
        };
      } else if (apdu.direction === 'response' && currentExchange) {
        // Complete the exchange
        currentExchange.response = apdu;
        result.push(currentExchange);
        currentExchange = null;
      }
    }

    // Add pending exchange if any
    if (currentExchange) {
      result.push(currentExchange);
    }

    return result;
  }

  /**
   * Renders all exchanges.
   */
  function render() {
    container.innerHTML = '';

    if (exchanges.length === 0) {
      emptyState.classList.remove('hidden');
      container.classList.add('hidden');
      countEl.textContent = '0 exchanges';
      return;
    }

    emptyState.classList.add('hidden');
    container.classList.remove('hidden');
    countEl.textContent = `${exchanges.length} exchange${exchanges.length !== 1 ? 's' : ''}`;

    const fragment = document.createDocumentFragment();
    exchanges.forEach((exchange, index) => {
      fragment.appendChild(createExchangeElement(exchange, index));
    });
    container.appendChild(fragment);
  }

  /**
   * Updates the display with current APDUs from state.
   */
  function update() {
    const apdus = state.get('apdus') || [];
    const sessionId = state.get('activeSessionId');

    // Filter APDUs for current session
    const sessionApdus = sessionId
      ? apdus.filter(a => a.sessionId === sessionId)
      : apdus;

    currentSessionId = sessionId;
    exchanges = groupIntoExchanges(sessionApdus);
    render();
  }

  /**
   * Clears all exchanges.
   */
  function clear() {
    exchanges = [];
    render();
  }

  /**
   * Adds a new APDU entry.
   * @param {Object} apdu - APDU entry
   */
  function addApdu(apdu) {
    // Only process if it matches current session
    if (currentSessionId && apdu.sessionId !== currentSessionId) {
      return;
    }

    const apdus = state.get('apdus') || [];
    const sessionApdus = currentSessionId
      ? apdus.filter(a => a.sessionId === currentSessionId)
      : apdus;

    exchanges = groupIntoExchanges(sessionApdus);
    render();

    // Scroll to bottom if auto-scroll enabled
    if (state.get('ui.autoScroll')) {
      container.scrollTop = container.scrollHeight;
    }
  }

  // Subscribe to state changes
  state.subscribe('apdus', update);
  state.subscribe('activeSessionId', update);

  // Initial render
  update();

  return {
    update,
    clear,
    addApdu,

    /**
     * Gets current exchange count.
     * @returns {number} Number of exchanges
     */
    get count() {
      return exchanges.length;
    },

    /**
     * Gets all exchanges.
     * @returns {Array} List of exchanges
     */
    get exchanges() {
      return [...exchanges];
    },
  };
}
