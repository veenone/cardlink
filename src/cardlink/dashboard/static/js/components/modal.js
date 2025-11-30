/**
 * Modal Component for GP OTA Tester Dashboard
 *
 * Manages modal dialogs with keyboard navigation and focus trapping.
 */

/**
 * Creates a modal controller.
 * @param {HTMLElement} modalElement - Modal container element
 * @returns {Object} Modal controller API
 */
export function createModal(modalElement) {
  let isOpen = false;
  let previousActiveElement = null;
  let closeHandlers = [];

  const backdrop = modalElement.querySelector('.modal-backdrop');
  const modal = modalElement.querySelector('.modal');
  const closeButtons = modalElement.querySelectorAll('[data-close-modal]');

  // Focus trap selectors
  const focusableSelector = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  /**
   * Gets focusable elements within modal.
   * @returns {HTMLElement[]} Focusable elements
   */
  function getFocusableElements() {
    return Array.from(modal.querySelectorAll(focusableSelector));
  }

  /**
   * Handles keyboard events.
   * @param {KeyboardEvent} event - Keyboard event
   */
  function handleKeydown(event) {
    if (!isOpen) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }

    if (event.key === 'Tab') {
      const focusable = getFocusableElements();
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }

      const firstElement = focusable[0];
      const lastElement = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }

  /**
   * Opens the modal.
   */
  function open() {
    if (isOpen) return;

    previousActiveElement = document.activeElement;
    isOpen = true;

    modalElement.classList.remove('hidden');
    modalElement.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Add event listeners
    document.addEventListener('keydown', handleKeydown);

    // Focus first focusable element
    requestAnimationFrame(() => {
      const focusable = getFocusableElements();
      if (focusable.length > 0) {
        focusable[0].focus();
      } else {
        modal.focus();
      }
    });
  }

  /**
   * Closes the modal.
   */
  function close() {
    if (!isOpen) return;

    isOpen = false;

    modalElement.classList.add('hidden');
    modalElement.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    // Remove event listeners
    document.removeEventListener('keydown', handleKeydown);

    // Restore focus
    if (previousActiveElement) {
      previousActiveElement.focus();
    }

    // Call close handlers
    for (const handler of closeHandlers) {
      try {
        handler();
      } catch (error) {
        console.error('Modal close handler error:', error);
      }
    }
  }

  /**
   * Toggles the modal.
   */
  function toggle() {
    if (isOpen) {
      close();
    } else {
      open();
    }
  }

  // Set up close button handlers
  for (const btn of closeButtons) {
    btn.addEventListener('click', close);
  }

  // Set up backdrop click to close
  if (backdrop) {
    backdrop.addEventListener('click', close);
  }

  return {
    open,
    close,
    toggle,

    /**
     * Checks if modal is open.
     * @returns {boolean} Open state
     */
    isOpen() {
      return isOpen;
    },

    /**
     * Registers a close handler.
     * @param {Function} handler - Handler function
     * @returns {Function} Unsubscribe function
     */
    onClose(handler) {
      closeHandlers.push(handler);
      return () => {
        const index = closeHandlers.indexOf(handler);
        if (index >= 0) {
          closeHandlers.splice(index, 1);
        }
      };
    },

    /**
     * Gets the modal element.
     * @returns {HTMLElement} Modal element
     */
    getElement() {
      return modalElement;
    },
  };
}

/**
 * Creates a confirmation dialog.
 * @param {Object} options - Dialog options
 * @param {string} options.title - Dialog title
 * @param {string} options.message - Dialog message
 * @param {string} [options.confirmText='Confirm'] - Confirm button text
 * @param {string} [options.cancelText='Cancel'] - Cancel button text
 * @param {string} [options.type='info'] - Dialog type (info, warning, danger)
 * @returns {Promise<boolean>} Resolves to true if confirmed
 */
export function confirm(options) {
  const {
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    type = 'info',
  } = options;

  return new Promise((resolve) => {
    // Create modal element
    const modalEl = document.createElement('div');
    modalEl.className = 'confirm-dialog';
    modalEl.setAttribute('role', 'dialog');
    modalEl.setAttribute('aria-modal', 'true');
    modalEl.setAttribute('aria-labelledby', 'confirm-title');

    const btnClass = type === 'danger' ? 'btn--danger' : 'btn--primary';

    modalEl.innerHTML = `
      <div class="modal-backdrop" data-close-modal></div>
      <div class="modal" style="max-width: 400px;">
        <div class="modal__header">
          <h2 id="confirm-title" class="modal__title">${escapeHtml(title)}</h2>
          <button class="modal__close btn btn--ghost btn--icon" type="button" aria-label="Close" data-close-modal>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M5 5l10 10M15 5L5 15"/>
            </svg>
          </button>
        </div>
        <div class="modal__body">
          <p class="text-secondary">${escapeHtml(message)}</p>
        </div>
        <div class="modal__footer">
          <button type="button" class="btn btn--secondary" data-action="cancel">${escapeHtml(cancelText)}</button>
          <button type="button" class="btn ${btnClass}" data-action="confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>
    `;

    document.body.appendChild(modalEl);
    const modal = createModal(modalEl);

    // Handle button clicks
    const confirmBtn = modalEl.querySelector('[data-action="confirm"]');
    const cancelBtn = modalEl.querySelector('[data-action="cancel"]');

    function cleanup(result) {
      modal.close();
      setTimeout(() => modalEl.remove(), 300);
      resolve(result);
    }

    confirmBtn.addEventListener('click', () => cleanup(true));
    cancelBtn.addEventListener('click', () => cleanup(false));
    modal.onClose(() => cleanup(false));

    modal.open();
  });
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
