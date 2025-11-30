/**
 * Tooltip Utility
 *
 * Provides tooltips and popovers for technical terms and help icons.
 */

/**
 * Technical term definitions for tooltips.
 */
export const TERMS = {
  // Protocol terms
  APDU: 'Application Protocol Data Unit - The communication format between a card reader and a smart card',
  SW: 'Status Word - A 2-byte response code from the smart card indicating command result',
  PSK: 'Pre-Shared Key - A symmetric key shared between client and server for TLS authentication',
  OTA: 'Over-The-Air - Remote provisioning and management of SIM cards',
  SCP81: 'Secure Channel Protocol 81 - GlobalPlatform specification for OTA communication via HTTPS',
  BIP: 'Bearer Independent Protocol - Allows smart cards to communicate over mobile data',
  UICC: 'Universal Integrated Circuit Card - The smart card used in mobile devices (SIM card)',

  // APDU fields
  CLA: 'Class byte - Identifies the type of command (ISO or proprietary)',
  INS: 'Instruction byte - Specifies the command to execute',
  P1: 'Parameter 1 - First parameter byte for the command',
  P2: 'Parameter 2 - Second parameter byte for the command',
  Lc: 'Length of command data - Number of bytes in the data field',
  Le: 'Length expected - Maximum number of response bytes expected',

  // Status words
  '9000': 'Success - Command executed successfully',
  '6A82': 'File not found - The specified file or application was not found',
  '6A86': 'Incorrect P1/P2 - Invalid parameters provided',
  '6D00': 'INS not supported - The instruction is not recognized',
  '6E00': 'CLA not supported - The class byte is not supported',
  '6700': 'Wrong length - Incorrect Lc or Le value',
  '6982': 'Security status not satisfied - Authentication required',
  '6983': 'Authentication blocked - PIN blocked or security violation',

  // Session terms
  SESSION: 'A communication session with a specific smart card or modem',
  MODEM: 'The AT modem device used to communicate with the UICC',
};

/**
 * Creates a tooltip element that follows the cursor.
 * @returns {Object} Tooltip controller
 */
export function createTooltipController() {
  let tooltipEl = null;
  let hideTimeout = null;

  function getOrCreateTooltip() {
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.className = 'tooltip';
      tooltipEl.setAttribute('role', 'tooltip');
      tooltipEl.style.cssText = `
        position: fixed;
        z-index: 10000;
        max-width: 300px;
        padding: 8px 12px;
        background: var(--color-neutral-800);
        color: var(--color-neutral-100);
        font-size: 12px;
        line-height: 1.4;
        border-radius: 4px;
        box-shadow: var(--shadow-lg);
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.15s ease;
      `;
      document.body.appendChild(tooltipEl);
    }
    return tooltipEl;
  }

  function show(target, content, position = 'top') {
    clearTimeout(hideTimeout);

    const tooltip = getOrCreateTooltip();
    tooltip.textContent = content;
    tooltip.style.opacity = '1';

    // Position tooltip
    const rect = target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let top, left;

    switch (position) {
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.right + 8;
        break;
      case 'top':
      default:
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
    }

    // Keep tooltip within viewport
    const padding = 8;
    if (left < padding) left = padding;
    if (left + tooltipRect.width > window.innerWidth - padding) {
      left = window.innerWidth - tooltipRect.width - padding;
    }
    if (top < padding) {
      top = rect.bottom + 8; // Flip to bottom
    }
    if (top + tooltipRect.height > window.innerHeight - padding) {
      top = rect.top - tooltipRect.height - 8; // Flip to top
    }

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
  }

  function hide() {
    hideTimeout = setTimeout(() => {
      if (tooltipEl) {
        tooltipEl.style.opacity = '0';
      }
    }, 100);
  }

  function destroy() {
    clearTimeout(hideTimeout);
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  return { show, hide, destroy };
}

/**
 * Creates a help icon with popover explanation.
 * @param {string} term - The term to explain
 * @param {string} [customText] - Custom explanation text
 * @returns {string} HTML string for help icon
 */
export function createHelpIcon(term, customText = null) {
  const text = customText || TERMS[term] || term;
  const escaped = text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  return `<span class="help-icon" data-tooltip="${escaped}" tabindex="0" role="button" aria-label="Help: ${term}">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  </span>`;
}

/**
 * Wraps a technical term with a tooltip.
 * @param {string} term - The term to wrap
 * @param {string} [displayText] - Text to display (defaults to term)
 * @returns {string} HTML string with tooltip
 */
export function wrapTermWithTooltip(term, displayText = null) {
  const text = TERMS[term];
  if (!text) return displayText || term;

  const display = displayText || term;
  const escaped = text.replace(/"/g, '&quot;');
  return `<span class="term-tooltip" data-tooltip="${escaped}" tabindex="0">${display}</span>`;
}

/**
 * Initializes tooltip listeners on the document.
 * @param {Object} controller - Tooltip controller
 */
export function initTooltipListeners(controller) {
  document.addEventListener('mouseover', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) {
      const content = target.getAttribute('data-tooltip');
      const position = target.getAttribute('data-tooltip-position') || 'top';
      controller.show(target, content, position);
    }
  });

  document.addEventListener('mouseout', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) {
      controller.hide();
    }
  });

  document.addEventListener('focusin', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) {
      const content = target.getAttribute('data-tooltip');
      controller.show(target, content, 'top');
    }
  });

  document.addEventListener('focusout', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) {
      controller.hide();
    }
  });
}

// Singleton controller instance
let globalController = null;

/**
 * Gets or creates the global tooltip controller.
 * @returns {Object} Tooltip controller
 */
export function getTooltipController() {
  if (!globalController) {
    globalController = createTooltipController();
    initTooltipListeners(globalController);
  }
  return globalController;
}
