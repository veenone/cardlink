/**
 * HTTP Log Component for GP OTA Tester Dashboard
 *
 * Displays HTTP request/response pairs with expandable headers.
 */

import { state } from '../state.js';
import { formatTime } from '../utils/time.js';

/**
 * Creates an HTTP log component.
 * @param {Object} elements - DOM elements
 * @param {HTMLElement} elements.container - Container element
 * @param {HTMLElement} elements.emptyState - Empty state element
 * @param {HTMLElement} elements.content - Content container
 * @returns {Object} HTTP log API
 */
export function createHttpLog(elements) {
  const { container, emptyState, content } = elements;

  let httpEntries = [];

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
   * Renders a single HTTP entry.
   * @param {Object} apdu - APDU data with HTTP info
   * @param {number} index - Entry index
   * @returns {HTMLElement} Entry element
   */
  function renderHttpEntry(apdu, index) {
    const entry = document.createElement('div');
    const http = apdu.http;
    const isRequest = apdu.direction === 'response'; // Response APDU = incoming request
    const isResponse = apdu.direction === 'command'; // Command APDU = outgoing response

    entry.className = `http-log__entry http-log__entry--${isRequest ? 'request' : 'response'}`;
    entry.dataset.index = index;

    // Determine what to display based on direction
    let headerContent = '';
    let bodyContent = '';

    if (isRequest && http) {
      // Incoming HTTP request (contains R-APDU from card)
      const methodClass = http.method?.toLowerCase() === 'post' ? 'post' : 'get';
      headerContent = `
        <div class="http-log__entry-title">
          <span class="http-log__entry-method http-log__entry-method--${methodClass}">${escapeHtml(http.method || 'POST')}</span>
          <span class="http-log__entry-path">${escapeHtml(http.path || '/admin')}</span>
        </div>
        <div class="http-log__entry-meta">
          <span class="http-log__entry-time">${formatTime(apdu.timestamp, { ms: true })}</span>
          <span>${http.body_length || 0} bytes</span>
        </div>
      `;

      // Headers section
      if (http.headers && Object.keys(http.headers).length > 0) {
        bodyContent = `
          <div class="http-log__headers">
            <div class="http-log__headers-title">Request Headers</div>
            <div class="http-log__headers-list">
              ${Object.entries(http.headers).map(([name, value]) => `
                <div class="http-log__header-row">
                  <span class="http-log__header-name">${escapeHtml(name)}:</span>
                  <span class="http-log__header-value">${escapeHtml(value)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (http.body_length > 0) {
        bodyContent += `
          <div class="http-log__body-section">
            <div class="http-log__body-title">Body</div>
            <div class="http-log__body-content">${http.body_length} bytes (R-APDU: ${escapeHtml(apdu.data || '')})</div>
          </div>
        `;
      }
    } else if (isResponse && http) {
      // Outgoing HTTP response (contains C-APDU to card)
      const statusClass = http.status >= 200 && http.status < 300 ? 'success' : 'error';
      headerContent = `
        <div class="http-log__entry-title">
          <span class="http-log__entry-status http-log__entry-status--${statusClass}">${http.status || 200} ${escapeHtml(http.status_text || 'OK')}</span>
          <span class="http-log__entry-path">${escapeHtml(http.content_type || 'application/octet-stream')}</span>
        </div>
        <div class="http-log__entry-meta">
          <span class="http-log__entry-time">${formatTime(apdu.timestamp, { ms: true })}</span>
          <span>${http.body_length || 0} bytes</span>
        </div>
      `;

      if (http.body_length > 0) {
        bodyContent = `
          <div class="http-log__body-section">
            <div class="http-log__body-title">Response Body</div>
            <div class="http-log__body-content">${http.body_length} bytes (C-APDU: ${escapeHtml(apdu.data || '')})</div>
          </div>
        `;
      }
    } else {
      // No HTTP info available
      headerContent = `
        <div class="http-log__entry-title">
          <span class="http-log__entry-path">No HTTP data available</span>
        </div>
        <div class="http-log__entry-meta">
          <span class="http-log__entry-time">${formatTime(apdu.timestamp, { ms: true })}</span>
        </div>
      `;
    }

    entry.innerHTML = `
      <div class="http-log__entry-header">
        ${headerContent}
        <svg class="http-log__entry-toggle" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 6l4 4 4-4"/>
        </svg>
      </div>
      <div class="http-log__entry-body">
        ${bodyContent || '<p class="text-sm text-tertiary">No additional details</p>'}
      </div>
    `;

    // Click handler for expand/collapse
    const header = entry.querySelector('.http-log__entry-header');
    header.addEventListener('click', () => {
      entry.classList.toggle('http-log__entry--expanded');
    });

    return entry;
  }

  /**
   * Filters APDUs to only those with HTTP info.
   * @returns {Object[]} APDUs with HTTP info
   */
  function getHttpApdus() {
    const apdus = state.get('apdus') || [];
    return apdus.filter(apdu => apdu.http);
  }

  /**
   * Updates empty state visibility.
   * @param {boolean} isEmpty - Whether to show empty state
   */
  function updateEmptyState(isEmpty) {
    if (isEmpty) {
      emptyState.classList.remove('hidden');
      content.classList.add('hidden');
    } else {
      emptyState.classList.add('hidden');
      content.classList.remove('hidden');
    }
  }

  /**
   * Renders all HTTP entries.
   */
  function render() {
    httpEntries = getHttpApdus();

    if (httpEntries.length === 0) {
      updateEmptyState(true);
      return;
    }

    updateEmptyState(false);
    content.innerHTML = '';

    const fragment = document.createDocumentFragment();
    httpEntries.forEach((apdu, index) => {
      fragment.appendChild(renderHttpEntry(apdu, index));
    });

    content.appendChild(fragment);
  }

  /**
   * Clears the HTTP log.
   */
  function clear() {
    httpEntries = [];
    content.innerHTML = '';
    updateEmptyState(true);
  }

  // Subscribe to state changes
  state.subscribe('apdus', () => {
    render();
  });

  // Initial render
  render();

  return {
    render,
    clear,

    /**
     * Gets the number of HTTP entries.
     * @returns {number} Entry count
     */
    getCount() {
      return httpEntries.length;
    },

    /**
     * Refreshes the display.
     */
    refresh() {
      render();
    },
  };
}
