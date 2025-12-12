/**
 * APDU Log Component for GP OTA Tester Dashboard
 *
 * Displays APDU command/response pairs with virtual scrolling.
 */

import { state } from '../state.js';
import { createVirtualScroller } from '../utils/virtual-scroll.js';
import { formatTime, formatRelativeWithTooltip } from '../utils/time.js';
import { formatHex, normalizeHex } from '../utils/hex.js';
import { parseCommand, parseResponse, getStatusWordInfo, categorizeStatus } from '../utils/apdu.js';

/**
 * Creates an APDU log component.
 * @param {Object} elements - DOM elements
 * @param {HTMLElement} elements.viewport - Scrollable viewport
 * @param {HTMLElement} elements.content - Content container
 * @param {HTMLElement} elements.stateContainer - Container for states (loading, empty, error)
 * @param {HTMLElement} elements.count - Entry count element
 * @returns {Object} APDU log API
 */
export function createApduLog(elements) {
  const { viewport, content, stateContainer, count } = elements;

  const ITEM_HEIGHT = 36; // Height of each APDU entry in pixels
  let virtualScroller = null;
  let autoScroll = true;
  let selectedIndex = null;
  let isLoading = false;
  let loadError = null;

  /**
   * Renders a single APDU entry.
   * @param {number} index - Item index
   * @param {Object} apdu - APDU data
   * @returns {HTMLElement} Entry element
   */
  function renderApduEntry(index, apdu) {
    const entry = document.createElement('div');
    entry.className = 'apdu-entry';

    if (index === selectedIndex) {
      entry.classList.add('apdu-entry--selected');
    }

    // Check if manually sent APDU
    if (apdu.metadata?.manual) {
      entry.classList.add('apdu-entry--manual');
    }

    // Check for highlight patterns
    const alertPatterns = state.get('settings.alertPatterns') || [];
    if (apdu.sw && alertPatterns.some(p => normalizeHex(apdu.sw).includes(normalizeHex(p)))) {
      entry.classList.add('apdu-entry--highlight');
    }

    // Line number column
    const lineNum = document.createElement('span');
    lineNum.className = 'apdu-entry__line';
    lineNum.textContent = index + 1;

    // Time column
    const time = document.createElement('span');
    time.className = 'apdu-entry__time';
    time.textContent = formatTime(apdu.timestamp, { ms: true });

    // Direction column
    const direction = document.createElement('span');
    direction.className = `apdu-entry__direction apdu-entry__direction--${apdu.direction}`;

    if (apdu.direction === 'command') {
      direction.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M2 6h8M7 3l3 3-3 3"/>
        </svg>
        CMD
      `;
    } else {
      direction.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M10 6H2M5 3L2 6l3 3"/>
        </svg>
        RSP
      `;
    }

    // Command info column (instruction name + case for commands)
    const cmdInfoCol = document.createElement('span');
    cmdInfoCol.className = 'apdu-entry__cmd-info';

    if (apdu.direction === 'command') {
      const cmdInfo = getApduCommandInfo(apdu);
      if (cmdInfo) {
        cmdInfoCol.innerHTML = `
          <span class="apdu-entry__ins-name" title="${cmdInfo.insName}">${cmdInfo.insName}</span>
          <span class="apdu-case-badge apdu-case-badge--case${cmdInfo.apduCase}" title="${cmdInfo.apduCaseName}">C${cmdInfo.apduCase}</span>
        `;
      }
    }

    // Data column
    const data = document.createElement('span');
    data.className = 'apdu-entry__data';
    data.textContent = formatApduData(apdu);

    // SW column (for responses)
    const sw = document.createElement('span');
    sw.className = 'apdu-entry__sw';

    if (apdu.sw) {
      const category = categorizeStatus(apdu.sw);
      sw.classList.add(`apdu-entry__sw--${category}`);
      sw.textContent = apdu.sw;
      sw.title = getStatusWordInfo(apdu.sw).meaning;
    }

    // Actions column
    const actions = document.createElement('div');
    actions.className = 'apdu-entry__actions';
    actions.innerHTML = `
      <button class="btn btn--ghost btn--icon btn--sm" title="Copy" data-action="copy">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="4" y="4" width="8" height="8" rx="1"/>
          <path d="M2 10V3a1 1 0 011-1h7"/>
        </svg>
      </button>
      <button class="btn btn--ghost btn--icon btn--sm" title="Details" data-action="details">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="7" cy="7" r="6"/>
          <path d="M7 5v4M7 10h.01"/>
        </svg>
      </button>
    `;

    entry.appendChild(lineNum);
    entry.appendChild(time);
    entry.appendChild(direction);
    entry.appendChild(cmdInfoCol);
    entry.appendChild(data);
    entry.appendChild(sw);
    entry.appendChild(actions);

    // Click handlers
    entry.addEventListener('click', (e) => {
      if (e.target.closest('[data-action]')) {
        const action = e.target.closest('[data-action]').dataset.action;
        handleAction(action, apdu, index);
      } else {
        selectEntry(index);
      }
    });

    return entry;
  }

  /**
   * Formats APDU data for display.
   * @param {Object} apdu - APDU data
   * @returns {string} Formatted string
   */
  function formatApduData(apdu) {
    if (apdu.direction === 'command') {
      const parsed = parseCommand(apdu.data);
      if (parsed.valid) {
        return `${parsed.cla} ${parsed.ins} ${parsed.p1} ${parsed.p2}${parsed.data ? ' ' + formatHex(parsed.data) : ''}${parsed.le ? ' (Le:' + parsed.le + ')' : ''}`;
      }
    } else {
      if (apdu.responseData) {
        return formatHex(apdu.responseData);
      }
    }
    return formatHex(apdu.data || '');
  }

  /**
   * Gets APDU command info including case.
   * @param {Object} apdu - APDU data
   * @returns {Object} Command info with case
   */
  function getApduCommandInfo(apdu) {
    if (apdu.direction === 'command') {
      const parsed = parseCommand(apdu.data);
      if (parsed.valid) {
        return {
          insName: parsed.insName,
          apduCase: parsed.apduCase,
          apduCaseName: parsed.apduCaseName,
        };
      }
    }
    return null;
  }

  /**
   * Handles action button clicks.
   * @param {string} action - Action name
   * @param {Object} apdu - APDU data
   * @param {number} index - Entry index
   */
  function handleAction(action, apdu, index) {
    switch (action) {
      case 'copy':
        copyToClipboard(apdu);
        break;
      case 'details':
        showDetails(apdu);
        break;
    }
  }

  /**
   * Copies APDU data to clipboard.
   * @param {Object} apdu - APDU data
   */
  async function copyToClipboard(apdu) {
    const text = apdu.direction === 'command'
      ? apdu.data
      : (apdu.responseData ? apdu.responseData + apdu.sw : apdu.sw);

    try {
      await navigator.clipboard.writeText(normalizeHex(text));
      // Show toast notification
      window.dispatchEvent(new CustomEvent('toast', {
        detail: { type: 'success', message: 'Copied to clipboard' }
      }));
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }

  /**
   * Shows APDU details dialog.
   * @param {Object} apdu - APDU data
   */
  function showDetails(apdu) {
    const detail = apdu.direction === 'command'
      ? parseCommand(apdu.data)
      : parseResponse(apdu.responseData + apdu.sw);

    window.dispatchEvent(new CustomEvent('apdu-details', { detail: { apdu, parsed: detail } }));
  }

  /**
   * Selects an entry.
   * @param {number} index - Entry index
   */
  function selectEntry(index) {
    const oldSelected = selectedIndex;
    selectedIndex = index === selectedIndex ? null : index;

    state.set('ui.selectedApduIndex', selectedIndex);

    // Update visual selection
    if (oldSelected !== null) {
      virtualScroller?.updateItem(oldSelected, state.get('apdus')[oldSelected]);
    }
    if (selectedIndex !== null) {
      virtualScroller?.updateItem(selectedIndex, state.get('apdus')[selectedIndex]);
    }
  }

  /**
   * Updates the entry count display.
   * @param {number} total - Total entries
   * @param {number} [filtered] - Filtered entries (if different)
   */
  function updateCount(total, filtered) {
    if (filtered !== undefined && filtered !== total) {
      count.textContent = `${filtered} of ${total} entries`;
    } else {
      count.textContent = `${total} entries`;
    }
  }

  /**
   * Renders the loading skeleton.
   * @returns {string} HTML string
   */
  function renderLoadingState() {
    return `
      <div class="loading-state">
        <div class="loading-state__spinner">
          <div class="spinner spinner--lg"></div>
        </div>
        <div class="loading-state__text">Loading APDU logs...</div>
      </div>
    `;
  }

  /**
   * Renders the empty state.
   * @returns {string} HTML string
   */
  function renderEmptyState() {
    const activeSession = state.get('activeSessionId');
    const sessionName = activeSession
      ? 'this session'
      : 'any session';

    return `
      <div class="empty-state">
        <svg class="empty-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10,9 9,9 8,9"/>
        </svg>
        <div class="empty-state__title">No APDU Traffic</div>
        <div class="empty-state__description">
          APDU commands and responses for ${sessionName} will appear here
          as they are captured. Start a test or send a command to see traffic.
        </div>
      </div>
    `;
  }

  /**
   * Renders the error state.
   * @param {string} message - Error message
   * @returns {string} HTML string
   */
  function renderErrorState(message) {
    return `
      <div class="error-state">
        <svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div class="error-state__title">Failed to Load Logs</div>
        <div class="error-state__message">${escapeHtml(message)}</div>
        <div class="error-state__suggestion">
          Check your connection and try refreshing.
        </div>
        <button class="btn btn--secondary btn--sm error-state__retry" data-action="retry-logs">
          Retry
        </button>
      </div>
    `;
  }

  /**
   * Escapes HTML special characters.
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Updates the state container (loading, empty, error states).
   * @param {'loading'|'empty'|'error'|'hidden'} mode - State mode
   * @param {string} [errorMessage] - Error message for error state
   */
  function updateStateContainer(mode, errorMessage) {
    if (!stateContainer) return;

    switch (mode) {
      case 'loading':
        stateContainer.innerHTML = renderLoadingState();
        stateContainer.classList.remove('hidden');
        viewport.classList.add('hidden');
        break;
      case 'empty':
        stateContainer.innerHTML = renderEmptyState();
        stateContainer.classList.remove('hidden');
        viewport.classList.add('hidden');
        break;
      case 'error':
        stateContainer.innerHTML = renderErrorState(errorMessage || 'Unknown error');
        stateContainer.classList.remove('hidden');
        viewport.classList.add('hidden');
        // Attach retry handler
        const retryBtn = stateContainer.querySelector('[data-action="retry-logs"]');
        if (retryBtn) {
          retryBtn.addEventListener('click', () => {
            loadError = null;
            window.dispatchEvent(new CustomEvent('logs-retry'));
          });
        }
        break;
      case 'hidden':
      default:
        stateContainer.innerHTML = '';
        stateContainer.classList.add('hidden');
        viewport.classList.remove('hidden');
    }
  }

  /**
   * Initializes the virtual scroller.
   */
  function initScroller() {
    virtualScroller = createVirtualScroller({
      container: viewport,
      content: content,
      itemHeight: ITEM_HEIGHT,
      bufferSize: 10,
      renderItem: renderApduEntry,
      onScroll: ({ scrollTop }) => {
        // Disable auto-scroll if user scrolled up
        if (!virtualScroller.isAtBottom(100)) {
          autoScroll = false;
        }
      },
    });
  }

  /**
   * Refreshes the log with current state.
   */
  function refresh() {
    // Handle loading state
    if (isLoading) {
      updateStateContainer('loading');
      return;
    }

    // Handle error state
    if (loadError) {
      updateStateContainer('error', loadError);
      return;
    }

    const apdus = state.getFilteredApdus();
    const totalApdus = state.get('apdus').length;

    // Handle empty state
    if (totalApdus === 0) {
      updateStateContainer('empty');
      updateCount(0);
      return;
    }

    // Show content
    updateStateContainer('hidden');
    updateCount(totalApdus, apdus.length);

    if (!virtualScroller) {
      initScroller();
    }

    virtualScroller.setItems(apdus);

    if (autoScroll) {
      virtualScroller.scrollToBottom();
    }
  }

  /**
   * Appends new APDUs to the log.
   * @param {Object[]} newApdus - New APDU entries
   */
  function append(newApdus) {
    const apdus = state.getFilteredApdus();
    const totalApdus = state.get('apdus').length;

    if (totalApdus === 0) {
      updateStateContainer('empty');
    } else {
      updateStateContainer('hidden');
    }
    updateCount(totalApdus, apdus.length);

    if (!virtualScroller) {
      initScroller();
      virtualScroller.setItems(apdus);
    } else {
      virtualScroller.setItems(apdus);
    }

    if (autoScroll) {
      virtualScroller.scrollToBottom();
    }
  }

  /**
   * Clears the log.
   */
  function clear() {
    selectedIndex = null;
    state.set('ui.selectedApduIndex', null);

    if (virtualScroller) {
      virtualScroller.clear();
    }

    updateStateContainer('empty');
    updateCount(0);
  }

  // Subscribe to state changes
  state.subscribe('apdus', () => {
    refresh();
  });

  state.subscribe('filters', () => {
    refresh();
  });

  state.subscribe('settings.alertPatterns', () => {
    virtualScroller?.refresh();
  });

  // Initialize
  initScroller();
  refresh();

  return {
    refresh,
    append,
    clear,

    /**
     * Sets auto-scroll state.
     * @param {boolean} enabled - Enable auto-scroll
     */
    setAutoScroll(enabled) {
      autoScroll = enabled;
      if (enabled) {
        virtualScroller?.scrollToBottom();
      }
    },

    /**
     * Gets auto-scroll state.
     * @returns {boolean} Auto-scroll enabled
     */
    isAutoScroll() {
      return autoScroll;
    },

    /**
     * Scrolls to a specific entry.
     * @param {number} index - Entry index
     */
    scrollToEntry(index) {
      virtualScroller?.scrollToItem(index, 'center');
    },

    /**
     * Gets selected entry.
     * @returns {Object|null} Selected APDU or null
     */
    getSelected() {
      if (selectedIndex === null) return null;
      return state.get('apdus')[selectedIndex];
    },

    /**
     * Destroys the component.
     */
    destroy() {
      virtualScroller?.destroy();
    },

    /**
     * Sets loading state.
     * @param {boolean} loading - Loading state
     */
    setLoading(loading) {
      isLoading = loading;
      refresh();
    },

    /**
     * Sets error state.
     * @param {string|null} error - Error message or null
     */
    setError(error) {
      loadError = error;
      refresh();
    },
  };
}
