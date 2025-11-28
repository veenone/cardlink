/**
 * Toast Manager for GP OTA Tester Dashboard
 *
 * Manages toast notifications.
 */

/**
 * Creates a toast manager instance.
 * @param {HTMLElement} container - Toast container element
 * @returns {Object} Toast manager API
 */
export function createToastManager(container) {
  const toasts = new Map();
  let idCounter = 0;

  /**
   * Creates a toast element.
   * @param {Object} options - Toast options
   * @returns {HTMLElement} Toast element
   */
  function createToastElement(options) {
    const { id, type, message, duration } = options;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.dataset.toastId = id;
    toast.setAttribute('role', 'alert');

    const iconSvg = getIconSvg(type);

    toast.innerHTML = `
      <span class="toast__icon toast__icon--${type}" aria-hidden="true">
        ${iconSvg}
      </span>
      <div class="toast__content">
        <p class="toast__message">${escapeHtml(message)}</p>
      </div>
      <button class="toast__close btn btn--ghost btn--icon btn--sm" aria-label="Dismiss">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M4 4l8 8M12 4L4 12"/>
        </svg>
      </button>
    `;

    // Close button handler
    const closeBtn = toast.querySelector('.toast__close');
    closeBtn.addEventListener('click', () => dismiss(id));

    return toast;
  }

  /**
   * Gets SVG icon for toast type.
   * @param {string} type - Toast type
   * @returns {string} SVG markup
   */
  function getIconSvg(type) {
    switch (type) {
      case 'success':
        return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 10l3 3 5-6"/>
          <circle cx="10" cy="10" r="8"/>
        </svg>`;
      case 'error':
        return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="10" cy="10" r="8"/>
          <path d="M10 6v4M10 14h.01"/>
        </svg>`;
      case 'warning':
        return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10 3l8 14H2L10 3z"/>
          <path d="M10 9v2M10 14h.01"/>
        </svg>`;
      case 'info':
      default:
        return `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="10" cy="10" r="8"/>
          <path d="M10 9v4M10 6h.01"/>
        </svg>`;
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
   * Shows a toast notification.
   * @param {Object} options - Toast options
   * @param {string} options.message - Toast message
   * @param {string} [options.type='info'] - Toast type (info, success, warning, error)
   * @param {number} [options.duration=5000] - Auto-dismiss duration in ms (0 = no auto-dismiss)
   * @returns {number} Toast ID
   */
  function show(options) {
    const id = ++idCounter;
    const { message, type = 'info', duration = 5000 } = options;

    const element = createToastElement({ id, type, message, duration });
    container.appendChild(element);

    const toastData = { id, element, type, message };

    if (duration > 0) {
      toastData.timeout = setTimeout(() => dismiss(id), duration);
    }

    toasts.set(id, toastData);

    return id;
  }

  /**
   * Dismisses a toast.
   * @param {number} id - Toast ID
   */
  function dismiss(id) {
    const toast = toasts.get(id);
    if (!toast) return;

    if (toast.timeout) {
      clearTimeout(toast.timeout);
    }

    toast.element.classList.add('toast--exiting');

    // Remove after animation
    setTimeout(() => {
      toast.element.remove();
      toasts.delete(id);
    }, 300);
  }

  /**
   * Dismisses all toasts.
   */
  function dismissAll() {
    for (const [id] of toasts) {
      dismiss(id);
    }
  }

  return {
    show,
    dismiss,
    dismissAll,

    /**
     * Shows a success toast.
     * @param {string} message - Message
     * @param {number} [duration] - Duration
     * @returns {number} Toast ID
     */
    success(message, duration) {
      return show({ message, type: 'success', duration });
    },

    /**
     * Shows an error toast.
     * @param {string} message - Message
     * @param {number} [duration] - Duration
     * @returns {number} Toast ID
     */
    error(message, duration = 8000) {
      return show({ message, type: 'error', duration });
    },

    /**
     * Shows a warning toast.
     * @param {string} message - Message
     * @param {number} [duration] - Duration
     * @returns {number} Toast ID
     */
    warning(message, duration) {
      return show({ message, type: 'warning', duration });
    },

    /**
     * Shows an info toast.
     * @param {string} message - Message
     * @param {number} [duration] - Duration
     * @returns {number} Toast ID
     */
    info(message, duration) {
      return show({ message, type: 'info', duration });
    },
  };
}
