/**
 * State Manager for GP OTA Tester Dashboard
 *
 * Centralized state management with pub/sub pattern.
 * Supports nested state paths and batched updates.
 */

/**
 * Deep clone helper - uses structuredClone if available, falls back to JSON
 * @param {*} obj - Object to clone
 * @returns {*} Cloned object
 */
function deepClone(obj) {
  if (typeof structuredClone === 'function') {
    return structuredClone(obj);
  }
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Gets the dynamic WebSocket URL based on current page location.
 * @returns {string} WebSocket URL
 */
function getDefaultWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws`;
}

/**
 * @typedef {Object} AppState
 * @property {Object} connection - WebSocket connection state
 * @property {string} connection.status - 'disconnected' | 'connecting' | 'connected'
 * @property {string|null} connection.error - Connection error message
 * @property {number} connection.retryCount - Reconnection attempt count
 * @property {Object[]} sessions - List of test sessions
 * @property {string|null} activeSessionId - Currently selected session ID
 * @property {Object[]} apdus - APDU log entries for active session
 * @property {Object} filters - Active filters
 * @property {string} filters.search - Search query
 * @property {string} filters.direction - 'all' | 'command' | 'response'
 * @property {string} filters.status - 'all' | 'success' | 'warning' | 'error'
 * @property {Object} settings - User settings
 * @property {Object} ui - UI state
 */

/** @type {AppState} */
const initialState = {
  connection: {
    status: 'disconnected',
    error: null,
    retryCount: 0,
  },
  sessions: [],
  activeSessionId: null,
  apdus: [],
  filters: {
    search: '',
    direction: 'all',
    status: 'all',
  },
  settings: {
    wsUrl: '',  // Empty = auto-detect from page URL
    autoReconnect: true,
    showTimestamps: true,
    highlightErrors: true,
    groupPairs: true,
    alertPatterns: [],
    soundAlerts: false,
    theme: 'light',
  },
  ui: {
    autoScroll: true,
    commandBuilderOpen: true,
    selectedApduIndex: null,
    simulatorPanelOpen: true,
  },
  // Network simulator state
  simulator: {
    available: false,
    connected: false,
    authenticated: false,
    url: '',
    simulatorType: '',
    ueCount: 0,
    sessionCount: 0,
    cell: null,
    error: null,
    ues: [],
    sessions: [],
    events: [],
  },
};

/**
 * Creates a state manager instance.
 * @returns {Object} State manager API
 */
export function createStateManager() {
  let state = deepClone(initialState);
  const listeners = new Map();
  let batchUpdates = false;
  let pendingNotifications = new Set();

  /**
   * Gets nested value from object using dot notation path.
   * @param {Object} obj - Source object
   * @param {string} path - Dot notation path (e.g., 'connection.status')
   * @returns {*} Value at path
   */
  function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
  }

  /**
   * Sets nested value in object using dot notation path.
   * @param {Object} obj - Target object
   * @param {string} path - Dot notation path
   * @param {*} value - Value to set
   */
  function setNestedValue(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((current, key) => {
      if (current[key] === undefined) {
        current[key] = {};
      }
      return current[key];
    }, obj);
    target[lastKey] = value;
  }

  /**
   * Gets all parent paths for a given path.
   * @param {string} path - Full path
   * @returns {string[]} Array of paths including parents
   */
  function getPathsToNotify(path) {
    const parts = path.split('.');
    const paths = ['*']; // Global listener
    let current = '';
    for (const part of parts) {
      current = current ? `${current}.${part}` : part;
      paths.push(current);
    }
    return paths;
  }

  /**
   * Notifies listeners for a path change.
   * @param {string} path - Changed path
   */
  function notifyListeners(path) {
    if (batchUpdates) {
      pendingNotifications.add(path);
      return;
    }

    const pathsToNotify = getPathsToNotify(path);
    const notified = new Set();

    for (const p of pathsToNotify) {
      const pathListeners = listeners.get(p);
      if (pathListeners) {
        for (const callback of pathListeners) {
          if (!notified.has(callback)) {
            notified.add(callback);
            try {
              callback(state, path);
            } catch (error) {
              console.error('State listener error:', error);
            }
          }
        }
      }
    }
  }

  /**
   * Flushes pending notifications after batch update.
   */
  function flushNotifications() {
    const paths = Array.from(pendingNotifications);
    pendingNotifications.clear();

    // Deduplicate and notify
    const allPaths = new Set();
    for (const path of paths) {
      for (const p of getPathsToNotify(path)) {
        allPaths.add(p);
      }
    }

    const notified = new Set();
    for (const p of allPaths) {
      const pathListeners = listeners.get(p);
      if (pathListeners) {
        for (const callback of pathListeners) {
          if (!notified.has(callback)) {
            notified.add(callback);
            try {
              callback(state, paths);
            } catch (error) {
              console.error('State listener error:', error);
            }
          }
        }
      }
    }
  }

  return {
    /**
     * Gets the current state or a nested value.
     * @param {string} [path] - Optional dot notation path
     * @returns {*} State or nested value
     */
    get(path) {
      if (!path) {
        return state;
      }
      return getNestedValue(state, path);
    },

    /**
     * Sets a value at a path and notifies listeners.
     * @param {string} path - Dot notation path
     * @param {*} value - Value to set
     */
    set(path, value) {
      const oldValue = getNestedValue(state, path);
      if (oldValue === value) {
        return;
      }

      setNestedValue(state, path, value);
      notifyListeners(path);
    },

    /**
     * Updates multiple paths at once.
     * @param {Object} updates - Object with paths as keys
     */
    update(updates) {
      batchUpdates = true;
      try {
        for (const [path, value] of Object.entries(updates)) {
          const oldValue = getNestedValue(state, path);
          if (oldValue !== value) {
            setNestedValue(state, path, value);
            pendingNotifications.add(path);
          }
        }
      } finally {
        batchUpdates = false;
        if (pendingNotifications.size > 0) {
          flushNotifications();
        }
      }
    },

    /**
     * Subscribes to state changes.
     * @param {string} path - Path to subscribe to, or '*' for all changes
     * @param {Function} callback - Callback function(state, changedPath)
     * @returns {Function} Unsubscribe function
     */
    subscribe(path, callback) {
      if (!listeners.has(path)) {
        listeners.set(path, new Set());
      }
      listeners.get(path).add(callback);

      // Return unsubscribe function
      return () => {
        const pathListeners = listeners.get(path);
        if (pathListeners) {
          pathListeners.delete(callback);
          if (pathListeners.size === 0) {
            listeners.delete(path);
          }
        }
      };
    },

    /**
     * Resets state to initial values.
     * @param {string} [path] - Optional path to reset (resets all if omitted)
     */
    reset(path) {
      if (path) {
        const initialValue = getNestedValue(initialState, path);
        this.set(path, deepClone(initialValue));
      } else {
        state = deepClone(initialState);
        notifyListeners('*');
      }
    },

    /**
     * Adds an APDU entry to the log.
     * @param {Object} apdu - APDU entry
     */
    addApdu(apdu) {
      const apdus = [...state.apdus, apdu];
      this.set('apdus', apdus);
    },

    /**
     * Adds multiple APDU entries.
     * @param {Object[]} newApdus - Array of APDU entries
     */
    addApdus(newApdus) {
      const apdus = [...state.apdus, ...newApdus];
      this.set('apdus', apdus);
    },

    /**
     * Clears all APDU entries.
     */
    clearApdus() {
      this.set('apdus', []);
    },

    /**
     * Updates a session in the list.
     * @param {string} sessionId - Session ID
     * @param {Object} updates - Session updates
     */
    updateSession(sessionId, updates) {
      const sessions = state.sessions.map(s =>
        s.id === sessionId ? { ...s, ...updates } : s
      );
      this.set('sessions', sessions);
    },

    /**
     * Adds a new session.
     * @param {Object} session - Session object
     */
    addSession(session) {
      const sessions = [...state.sessions, session];
      this.set('sessions', sessions);
    },

    /**
     * Removes a session.
     * @param {string} sessionId - Session ID
     */
    removeSession(sessionId) {
      const sessions = state.sessions.filter(s => s.id !== sessionId);
      this.set('sessions', sessions);

      if (state.activeSessionId === sessionId) {
        this.set('activeSessionId', null);
        this.clearApdus();
      }
    },

    /**
     * Gets filtered APDUs based on current filters.
     * @returns {Object[]} Filtered APDU entries
     */
    getFilteredApdus() {
      let filtered = state.apdus;
      const { search, direction, status } = state.filters;

      // Filter by direction
      if (direction !== 'all') {
        filtered = filtered.filter(a => a.direction === direction);
      }

      // Filter by status
      if (status !== 'all') {
        filtered = filtered.filter(a => {
          if (!a.sw) return status === 'command';
          const sw = a.sw.toUpperCase();
          switch (status) {
            case 'success':
              return sw.startsWith('90') || sw.startsWith('91');
            case 'warning':
              return sw.startsWith('6') && !sw.startsWith('6A') && !sw.startsWith('6D') && !sw.startsWith('6E');
            case 'error':
              return sw.startsWith('6A') || sw.startsWith('6D') || sw.startsWith('6E') || sw.startsWith('67') || sw.startsWith('69');
            default:
              return true;
          }
        });
      }

      // Filter by search
      if (search) {
        const query = search.toLowerCase();
        filtered = filtered.filter(a =>
          a.data?.toLowerCase().includes(query) ||
          a.sw?.toLowerCase().includes(query) ||
          a.parsed?.ins?.toLowerCase().includes(query)
        );
      }

      return filtered;
    },

    /**
     * Loads settings from localStorage.
     */
    loadSettings() {
      try {
        const saved = localStorage.getItem('gp-ota-dashboard-settings');
        if (saved) {
          const settings = JSON.parse(saved);
          this.set('settings', { ...state.settings, ...settings });
        }
      } catch (error) {
        console.warn('Failed to load settings:', error);
      }
    },

    /**
     * Saves settings to localStorage.
     */
    saveSettings() {
      try {
        localStorage.setItem('gp-ota-dashboard-settings', JSON.stringify(state.settings));
      } catch (error) {
        console.warn('Failed to save settings:', error);
      }
    },
  };
}

// Export singleton instance
export const state = createStateManager();
