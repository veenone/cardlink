/**
 * WebSocket Client for GP OTA Tester Dashboard
 *
 * Handles WebSocket connection with automatic reconnection,
 * message queuing, and event handling.
 */

import { state } from './state.js';

/**
 * @typedef {Object} WebSocketConfig
 * @property {string} url - WebSocket URL
 * @property {boolean} autoReconnect - Enable auto-reconnection
 * @property {number} reconnectInterval - Initial reconnect interval in ms
 * @property {number} maxReconnectInterval - Maximum reconnect interval in ms
 * @property {number} reconnectDecay - Reconnect interval multiplier
 * @property {number} maxRetries - Maximum reconnection attempts (0 = unlimited)
 */

/**
 * Gets the dynamic WebSocket URL based on current page location.
 * @returns {string} WebSocket URL
 */
function getDefaultWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws`;
}

/** @type {WebSocketConfig} */
const defaultConfig = {
  url: getDefaultWebSocketUrl(),
  autoReconnect: true,
  reconnectInterval: 1000,
  maxReconnectInterval: 30000,
  reconnectDecay: 1.5,
  maxRetries: 0,
};

/**
 * Creates a WebSocket client instance.
 * @param {Partial<WebSocketConfig>} [config] - Configuration options
 * @returns {Object} WebSocket client API
 */
export function createWebSocketClient(config = {}) {
  const cfg = { ...defaultConfig, ...config };
  let ws = null;
  let reconnectTimer = null;
  let currentReconnectInterval = cfg.reconnectInterval;
  let messageQueue = [];
  const messageHandlers = new Map();
  const eventHandlers = {
    open: [],
    close: [],
    error: [],
    message: [],
  };

  /**
   * Updates connection state in the state manager.
   * @param {string} status - Connection status
   * @param {string|null} error - Error message
   */
  function updateConnectionState(status, error = null) {
    state.update({
      'connection.status': status,
      'connection.error': error,
    });
  }

  /**
   * Emits an event to registered handlers.
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  function emit(event, data) {
    const handlers = eventHandlers[event] || [];
    for (const handler of handlers) {
      try {
        handler(data);
      } catch (error) {
        console.error(`WebSocket ${event} handler error:`, error);
      }
    }
  }

  /**
   * Handles incoming WebSocket messages.
   * @param {MessageEvent} event - WebSocket message event
   */
  function handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      const { type, payload } = message;

      // Emit raw message event
      emit('message', message);

      // Handle typed message
      if (type && messageHandlers.has(type)) {
        const handlers = messageHandlers.get(type);
        for (const handler of handlers) {
          try {
            handler(payload, message);
          } catch (error) {
            console.error(`Message handler error for type "${type}":`, error);
          }
        }
      }
    } catch (error) {
      console.warn('Failed to parse WebSocket message:', error);
      emit('message', { raw: event.data });
    }
  }

  /**
   * Schedules a reconnection attempt.
   */
  function scheduleReconnect() {
    if (!cfg.autoReconnect) {
      return;
    }

    const retryCount = state.get('connection.retryCount');
    if (cfg.maxRetries > 0 && retryCount >= cfg.maxRetries) {
      updateConnectionState('disconnected', 'Max reconnection attempts reached');
      return;
    }

    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
      state.set('connection.retryCount', retryCount + 1);
      connect();
    }, currentReconnectInterval);

    // Increase interval for next attempt
    currentReconnectInterval = Math.min(
      currentReconnectInterval * cfg.reconnectDecay,
      cfg.maxReconnectInterval
    );
  }

  /**
   * Flushes queued messages after connection.
   */
  function flushQueue() {
    while (messageQueue.length > 0 && ws?.readyState === WebSocket.OPEN) {
      const message = messageQueue.shift();
      ws.send(JSON.stringify(message));
    }
  }

  /**
   * Connects to the WebSocket server.
   * @returns {Promise<void>} Resolves when connected
   */
  function connect() {
    return new Promise((resolve, reject) => {
      if (ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (ws?.readyState === WebSocket.CONNECTING) {
        // Wait for existing connection attempt
        const checkConnection = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            clearInterval(checkConnection);
            resolve();
          } else if (ws?.readyState === WebSocket.CLOSED) {
            clearInterval(checkConnection);
            reject(new Error('Connection failed'));
          }
        }, 100);
        return;
      }

      // Clean up existing connection
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        ws.onopen = null;
        ws.close();
      }

      updateConnectionState('connecting');
      const url = state.get('settings.wsUrl') || cfg.url;

      try {
        ws = new WebSocket(url);
      } catch (error) {
        updateConnectionState('disconnected', error.message);
        reject(error);
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        updateConnectionState('connected');
        state.set('connection.retryCount', 0);
        currentReconnectInterval = cfg.reconnectInterval;
        emit('open', null);
        flushQueue();
        resolve();
      };

      ws.onclose = (event) => {
        const wasConnected = state.get('connection.status') === 'connected';
        updateConnectionState('disconnected');
        emit('close', { code: event.code, reason: event.reason, wasClean: event.wasClean });

        if (wasConnected || state.get('connection.retryCount') > 0) {
          scheduleReconnect();
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        emit('error', event);
      };

      ws.onmessage = handleMessage;
    });
  }

  /**
   * Disconnects from the WebSocket server.
   * @param {number} [code=1000] - Close code
   * @param {string} [reason] - Close reason
   */
  function disconnect(code = 1000, reason = '') {
    clearTimeout(reconnectTimer);
    cfg.autoReconnect = false;

    if (ws) {
      ws.close(code, reason);
      ws = null;
    }

    updateConnectionState('disconnected');
    state.set('connection.retryCount', 0);
  }

  /**
   * Sends a message through the WebSocket.
   * @param {string} type - Message type
   * @param {Object} [payload={}] - Message payload
   * @param {boolean} [queue=true] - Queue message if disconnected
   * @returns {boolean} True if sent immediately
   */
  function send(type, payload = {}, queue = true) {
    const message = { type, payload, timestamp: Date.now() };

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      return true;
    }

    if (queue) {
      messageQueue.push(message);
    }

    return false;
  }

  /**
   * Registers a handler for a specific message type.
   * @param {string} type - Message type
   * @param {Function} handler - Handler function(payload, message)
   * @returns {Function} Unsubscribe function
   */
  function onMessage(type, handler) {
    if (!messageHandlers.has(type)) {
      messageHandlers.set(type, []);
    }
    messageHandlers.get(type).push(handler);

    return () => {
      const handlers = messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index >= 0) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Registers a handler for WebSocket events.
   * @param {'open'|'close'|'error'|'message'} event - Event name
   * @param {Function} handler - Handler function
   * @returns {Function} Unsubscribe function
   */
  function on(event, handler) {
    if (!eventHandlers[event]) {
      console.warn(`Unknown WebSocket event: ${event}`);
      return () => {};
    }

    eventHandlers[event].push(handler);

    return () => {
      const index = eventHandlers[event].indexOf(handler);
      if (index >= 0) {
        eventHandlers[event].splice(index, 1);
      }
    };
  }

  /**
   * Gets the current connection state.
   * @returns {string} Connection state
   */
  function getState() {
    if (!ws) return 'disconnected';
    switch (ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
      default:
        return 'disconnected';
    }
  }

  /**
   * Enables or disables auto-reconnection.
   * @param {boolean} enabled - Enable auto-reconnect
   */
  function setAutoReconnect(enabled) {
    cfg.autoReconnect = enabled;
    if (!enabled) {
      clearTimeout(reconnectTimer);
    }
  }

  return {
    connect,
    disconnect,
    send,
    onMessage,
    on,
    getState,
    setAutoReconnect,

    /**
     * Gets the WebSocket ready state.
     * @returns {number} WebSocket.readyState
     */
    get readyState() {
      return ws?.readyState ?? WebSocket.CLOSED;
    },

    /**
     * Checks if the connection is open.
     * @returns {boolean} True if connected
     */
    get isConnected() {
      return ws?.readyState === WebSocket.OPEN;
    },
  };
}

// Export singleton instance
export const wsClient = createWebSocketClient();
