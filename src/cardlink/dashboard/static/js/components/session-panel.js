/**
 * Session Panel Component for GP OTA Tester Dashboard
 *
 * Displays and manages test sessions with pagination.
 */

import { state } from '../state.js';
import { formatRelative, formatRelativeWithTooltip, formatDurationCompact } from '../utils/time.js';
import { api } from '../api.js';

const SESSIONS_PER_PAGE = 10;

/**
 * Creates a session panel component.
 * @param {HTMLElement} listElement - Session list container
 * @returns {Object} Session panel API
 */
export function createSessionPanel(listElement) {
  let isLoading = false;
  let loadError = null;
  let currentPage = 0;

  /**
   * Renders a session item.
   * @param {Object} session - Session data
   * @returns {HTMLElement} Session item element
   */
  function renderSessionItem(session) {
    const item = document.createElement('div');
    item.className = 'session-item';
    item.dataset.sessionId = session.id;
    item.setAttribute('role', 'option');
    item.setAttribute('tabindex', '0');

    if (session.id === state.get('activeSessionId')) {
      item.classList.add('session-item--active');
      item.setAttribute('aria-selected', 'true');
    }

    const statusClass = getStatusClass(session.status);

    // Get display name: prefer psk_identity (ICCID), then name, then truncated ID
    const pskIdentity = session.metadata?.psk_identity || session.metadata?.pskIdentity;
    const displayName = pskIdentity || session.name || 'Session ' + session.id.slice(0, 8);

    // Format ICCID for display (show last 8 digits if too long)
    const formattedName = pskIdentity && pskIdentity.length > 20
      ? '...' + pskIdentity.slice(-12)
      : displayName;

    // Show client IP if available
    const clientInfo = session.metadata?.client_ip || session.metadata?.clientIp || '';

    item.innerHTML = `
      <div class="session-item__indicator session-item__indicator--${statusClass}" aria-hidden="true"></div>
      <div class="session-item__content">
        <div class="session-item__name" title="${escapeHtml(pskIdentity || displayName)}">${escapeHtml(formattedName)}</div>
        <div class="session-item__meta">
          <span class="session-item__count">${session.apduCount || 0} APDUs</span>
          ${clientInfo ? `<span class="session-item__client">${escapeHtml(clientInfo)}</span>` : ''}
          <span>${formatRelative(session.updatedAt || session.createdAt)}</span>
        </div>
      </div>
      <button class="session-item__close" title="Close session" aria-label="Close session">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    // Close button handler
    const closeBtn = item.querySelector('.session-item__close');
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent selecting the session
      closeSession(session.id);
    });

    // Click handler
    item.addEventListener('click', () => selectSession(session.id));

    // Keyboard handler
    item.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectSession(session.id);
      }
    });

    return item;
  }

  /**
   * Gets status class for indicator.
   * @param {string} status - Session status
   * @returns {string} Status class
   */
  function getStatusClass(status) {
    switch (status) {
      case 'active':
      case 'running':
        return 'active';
      case 'idle':
      case 'paused':
        return 'idle';
      case 'completed':
      case 'stopped':
      default:
        return 'completed';
    }
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
   * Selects a session.
   * @param {string} sessionId - Session ID
   */
  function selectSession(sessionId) {
    const currentId = state.get('activeSessionId');

    if (currentId === sessionId) {
      return; // Already selected
    }

    state.set('activeSessionId', sessionId);

    // Dispatch event for app to load session data
    window.dispatchEvent(new CustomEvent('session-select', { detail: { sessionId } }));
  }

  /**
   * Closes a session.
   * @param {string} sessionId - Session ID
   */
  async function closeSession(sessionId) {
    try {
      await api.deleteSession(sessionId);

      // Remove from state
      const sessions = state.get('sessions') || [];
      const updatedSessions = sessions.filter(s => s.id !== sessionId);
      state.set('sessions', updatedSessions);

      // Clear active session if it was the closed one
      if (state.get('activeSessionId') === sessionId) {
        state.set('activeSessionId', null);
        state.set('apdus', []);
      }

      // Dispatch event for other components
      window.dispatchEvent(new CustomEvent('session-closed', { detail: { sessionId } }));
    } catch (error) {
      console.error('Failed to close session:', error);
    }
  }

  /**
   * Renders loading skeleton.
   * @returns {string} HTML string
   */
  function renderLoadingSkeleton() {
    return `
      <div class="session-panel__loading">
        <div class="skeleton skeleton--card"></div>
        <div class="skeleton skeleton--card"></div>
        <div class="skeleton skeleton--card"></div>
      </div>
    `;
  }

  /**
   * Renders empty state.
   * @returns {string} HTML string
   */
  function renderEmptyState() {
    return `
      <div class="empty-state">
        <svg class="empty-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18"/>
          <path d="M9 21V9"/>
        </svg>
        <div class="empty-state__title">No Active Sessions</div>
        <div class="empty-state__description">
          Sessions will appear here when a modem connects or you start a test.
          Connect a device to begin monitoring APDU traffic.
        </div>
      </div>
    `;
  }

  /**
   * Renders error state.
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
        <div class="error-state__title">Failed to Load Sessions</div>
        <div class="error-state__message">${escapeHtml(message)}</div>
        <div class="error-state__suggestion">
          Check your network connection and try again.
        </div>
        <button class="btn btn--secondary btn--sm error-state__retry" data-action="retry">
          Retry
        </button>
      </div>
    `;
  }

  /**
   * Renders pagination controls.
   * @param {number} totalSessions - Total number of sessions
   * @param {number} totalPages - Total number of pages
   * @returns {HTMLElement} Pagination element
   */
  function renderPagination(totalSessions, totalPages) {
    const pagination = document.createElement('div');
    pagination.className = 'session-pagination';

    const startIdx = currentPage * SESSIONS_PER_PAGE + 1;
    const endIdx = Math.min((currentPage + 1) * SESSIONS_PER_PAGE, totalSessions);

    pagination.innerHTML = `
      <div class="session-pagination__info">
        ${startIdx}-${endIdx} of ${totalSessions}
      </div>
      <div class="session-pagination__controls">
        <button class="session-pagination__btn" data-action="prev" ${currentPage === 0 ? 'disabled' : ''} title="Previous page">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <span class="session-pagination__page">${currentPage + 1}/${totalPages}</span>
        <button class="session-pagination__btn" data-action="next" ${currentPage >= totalPages - 1 ? 'disabled' : ''} title="Next page">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    `;

    // Add event listeners
    const prevBtn = pagination.querySelector('[data-action="prev"]');
    const nextBtn = pagination.querySelector('[data-action="next"]');

    prevBtn.addEventListener('click', () => {
      if (currentPage > 0) {
        currentPage--;
        render();
      }
    });

    nextBtn.addEventListener('click', () => {
      if (currentPage < totalPages - 1) {
        currentPage++;
        render();
      }
    });

    return pagination;
  }

  /**
   * Renders all sessions.
   */
  function render() {
    const sessions = state.get('sessions');

    // Clear existing content
    listElement.innerHTML = '';

    // Show loading state
    if (isLoading) {
      listElement.innerHTML = renderLoadingSkeleton();
      return;
    }

    // Show error state
    if (loadError) {
      listElement.innerHTML = renderErrorState(loadError);
      // Attach retry handler
      const retryBtn = listElement.querySelector('[data-action="retry"]');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          loadError = null;
          window.dispatchEvent(new CustomEvent('sessions-retry'));
        });
      }
      return;
    }

    // Show empty state
    if (!sessions || sessions.length === 0) {
      listElement.innerHTML = renderEmptyState();
      return;
    }

    // Sort sessions by last updated
    const sortedSessions = [...sessions].sort((a, b) => {
      const aTime = new Date(a.updatedAt || a.createdAt).getTime();
      const bTime = new Date(b.updatedAt || b.createdAt).getTime();
      return bTime - aTime;
    });

    const totalSessions = sortedSessions.length;
    const totalPages = Math.ceil(totalSessions / SESSIONS_PER_PAGE);

    // Clamp current page to valid range
    if (currentPage >= totalPages) {
      currentPage = Math.max(0, totalPages - 1);
    }

    // Get sessions for current page
    const startIdx = currentPage * SESSIONS_PER_PAGE;
    const endIdx = startIdx + SESSIONS_PER_PAGE;
    const pageSessions = sortedSessions.slice(startIdx, endIdx);

    // Render items
    const fragment = document.createDocumentFragment();

    // Add pagination at top if more than one page
    if (totalPages > 1) {
      fragment.appendChild(renderPagination(totalSessions, totalPages));
    }

    // Create sessions container
    const sessionsContainer = document.createElement('div');
    sessionsContainer.className = 'session-list__items';

    for (const session of pageSessions) {
      sessionsContainer.appendChild(renderSessionItem(session));
    }

    fragment.appendChild(sessionsContainer);

    listElement.appendChild(fragment);
  }

  /**
   * Updates a specific session item.
   * @param {string} sessionId - Session ID
   */
  function updateSession(sessionId) {
    const item = listElement.querySelector(`[data-session-id="${sessionId}"]`);
    const session = state.get('sessions').find(s => s.id === sessionId);

    if (!item || !session) return;

    const newItem = renderSessionItem(session);
    item.replaceWith(newItem);
  }

  /**
   * Updates selection state.
   */
  function updateSelection() {
    const activeId = state.get('activeSessionId');
    const items = listElement.querySelectorAll('.session-item');

    items.forEach(item => {
      const isActive = item.dataset.sessionId === activeId;
      item.classList.toggle('session-item--active', isActive);
      item.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  // Subscribe to state changes
  state.subscribe('sessions', render);
  state.subscribe('activeSessionId', updateSelection);

  // Initial render
  render();

  return {
    render,
    updateSession,
    selectSession,

    /**
     * Refreshes the panel.
     */
    refresh() {
      render();
    },

    /**
     * Gets the currently selected session ID.
     * @returns {string|null} Session ID
     */
    getSelectedId() {
      return state.get('activeSessionId');
    },

    /**
     * Sets loading state.
     * @param {boolean} loading - Loading state
     */
    setLoading(loading) {
      isLoading = loading;
      render();
    },

    /**
     * Sets error state.
     * @param {string|null} error - Error message or null
     */
    setError(error) {
      loadError = error;
      render();
    },

    /**
     * Goes to a specific page.
     * @param {number} page - Page number (0-indexed)
     */
    goToPage(page) {
      currentPage = page;
      render();
    },

    /**
     * Gets the current page.
     * @returns {number} Current page (0-indexed)
     */
    getCurrentPage() {
      return currentPage;
    },
  };
}
