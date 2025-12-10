/**
 * API Client for GP OTA Tester Dashboard
 *
 * HTTP client for REST API interactions with the backend.
 */

/**
 * @typedef {Object} APIConfig
 * @property {string} baseUrl - Base URL for API requests
 * @property {number} timeout - Request timeout in ms
 * @property {Object} headers - Default headers
 */

/** @type {APIConfig} */
const defaultConfig = {
  baseUrl: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Custom API error class.
 */
export class APIError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Creates an API client instance.
 * @param {Partial<APIConfig>} [config] - Configuration options
 * @returns {Object} API client
 */
export function createAPIClient(config = {}) {
  const cfg = { ...defaultConfig, ...config };

  /**
   * Makes an HTTP request.
   * @param {string} method - HTTP method
   * @param {string} path - API path
   * @param {Object} [options={}] - Request options
   * @returns {Promise<*>} Response data
   */
  async function request(method, path, options = {}) {
    const url = `${cfg.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || cfg.timeout);

    const fetchOptions = {
      method,
      headers: { ...cfg.headers, ...options.headers },
      signal: controller.signal,
    };

    if (options.body && method !== 'GET') {
      fetchOptions.body = JSON.stringify(options.body);
    }

    try {
      const response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);

      // Handle non-JSON responses
      const contentType = response.headers.get('Content-Type');
      let data;

      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else if (contentType?.includes('text/')) {
        data = await response.text();
      } else {
        data = await response.blob();
      }

      if (!response.ok) {
        throw new APIError(
          data?.error || data?.message || `HTTP ${response.status}`,
          response.status,
          data
        );
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new APIError('Request timeout', 408);
      }

      if (error instanceof APIError) {
        throw error;
      }

      throw new APIError(error.message, 0);
    }
  }

  return {
    /**
     * GET request.
     * @param {string} path - API path
     * @param {Object} [options] - Request options
     * @returns {Promise<*>} Response data
     */
    get(path, options) {
      return request('GET', path, options);
    },

    /**
     * POST request.
     * @param {string} path - API path
     * @param {Object} [body] - Request body
     * @param {Object} [options] - Request options
     * @returns {Promise<*>} Response data
     */
    post(path, body, options) {
      return request('POST', path, { ...options, body });
    },

    /**
     * PUT request.
     * @param {string} path - API path
     * @param {Object} [body] - Request body
     * @param {Object} [options] - Request options
     * @returns {Promise<*>} Response data
     */
    put(path, body, options) {
      return request('PUT', path, { ...options, body });
    },

    /**
     * DELETE request.
     * @param {string} path - API path
     * @param {Object} [options] - Request options
     * @returns {Promise<*>} Response data
     */
    delete(path, options) {
      return request('DELETE', path, options);
    },

    /**
     * PATCH request.
     * @param {string} path - API path
     * @param {Object} [body] - Request body
     * @param {Object} [options] - Request options
     * @returns {Promise<*>} Response data
     */
    patch(path, body, options) {
      return request('PATCH', path, { ...options, body });
    },

    // =========================================================================
    // Session Endpoints
    // =========================================================================

    /**
     * Gets all sessions.
     * @returns {Promise<Object[]>} Sessions
     */
    getSessions() {
      return this.get('/sessions');
    },

    /**
     * Gets a specific session.
     * @param {string} sessionId - Session ID
     * @returns {Promise<Object>} Session
     */
    getSession(sessionId) {
      return this.get(`/sessions/${sessionId}`);
    },

    /**
     * Creates a new session.
     * @param {Object} data - Session data
     * @returns {Promise<Object>} Created session
     */
    createSession(data) {
      return this.post('/sessions', data);
    },

    /**
     * Updates a session.
     * @param {string} sessionId - Session ID
     * @param {Object} data - Update data
     * @returns {Promise<Object>} Updated session
     */
    updateSession(sessionId, data) {
      return this.patch(`/sessions/${sessionId}`, data);
    },

    /**
     * Deletes a session.
     * @param {string} sessionId - Session ID
     * @returns {Promise<void>}
     */
    deleteSession(sessionId) {
      return this.delete(`/sessions/${sessionId}`);
    },

    // =========================================================================
    // APDU Endpoints
    // =========================================================================

    /**
     * Gets APDUs for a session.
     * @param {string} sessionId - Session ID
     * @param {Object} [params] - Query parameters
     * @returns {Promise<Object[]>} APDU entries
     */
    getApdus(sessionId, params = {}) {
      const query = new URLSearchParams(params).toString();
      const path = `/sessions/${sessionId}/apdus${query ? `?${query}` : ''}`;
      return this.get(path);
    },

    /**
     * Sends an APDU command.
     * @param {string} sessionId - Session ID
     * @param {Object} apdu - APDU data
     * @returns {Promise<Object>} Response
     */
    sendApdu(sessionId, apdu) {
      return this.post(`/sessions/${sessionId}/apdus`, apdu);
    },

    /**
     * Clears APDUs for a session.
     * @param {string} sessionId - Session ID
     * @returns {Promise<void>}
     */
    clearApdus(sessionId) {
      return this.delete(`/sessions/${sessionId}/apdus`);
    },

    // =========================================================================
    // Export Endpoints
    // =========================================================================

    /**
     * Exports APDUs in specified format.
     * @param {string} sessionId - Session ID
     * @param {string} format - Export format (json, csv, txt)
     * @param {Object} [options] - Export options
     * @returns {Promise<Blob>} Export data
     */
    async exportApdus(sessionId, format, options = {}) {
      const params = new URLSearchParams({ format, ...options }).toString();
      const response = await fetch(`${cfg.baseUrl}/sessions/${sessionId}/export?${params}`);

      if (!response.ok) {
        throw new APIError('Export failed', response.status);
      }

      return response.blob();
    },

    // =========================================================================
    // Modem Endpoints
    // =========================================================================

    /**
     * Gets connected modems.
     * @returns {Promise<Object[]>} Modems
     */
    getModems() {
      return this.get('/modems');
    },

    /**
     * Gets modem info.
     * @param {string} port - Modem port
     * @returns {Promise<Object>} Modem info
     */
    getModemInfo(port) {
      return this.get(`/modems/${encodeURIComponent(port)}`);
    },

    /**
     * Sends AT command to modem.
     * @param {string} port - Modem port
     * @param {string} command - AT command
     * @returns {Promise<Object>} Response
     */
    sendAtCommand(port, command) {
      return this.post(`/modems/${encodeURIComponent(port)}/at`, { command });
    },

    // =========================================================================
    // System Endpoints
    // =========================================================================

    /**
     * Gets system status.
     * @returns {Promise<Object>} Status
     */
    getStatus() {
      return this.get('/status');
    },

    /**
     * Gets server configuration.
     * @returns {Promise<Object>} Configuration
     */
    getConfig() {
      return this.get('/config');
    },

    // =========================================================================
    // Network Simulator Endpoints
    // =========================================================================

    /**
     * Gets simulator status.
     * @returns {Promise<Object>} Simulator status
     */
    getSimulatorStatus() {
      return this.get('/simulator/status');
    },

    /**
     * Connects to network simulator.
     * @param {Object} config - Connection configuration
     * @param {string} config.url - Simulator URL (ws:// or tcp://)
     * @param {string} [config.simulator_type] - Simulator type (amarisoft, generic)
     * @param {string} [config.api_key] - API key for authentication
     * @param {Object} [config.tls] - TLS configuration
     * @returns {Promise<Object>} Connection result
     */
    connectSimulator(config) {
      return this.post('/simulator/connect', config);
    },

    /**
     * Disconnects from network simulator.
     * @returns {Promise<Object>} Disconnection result
     */
    disconnectSimulator() {
      return this.post('/simulator/disconnect');
    },

    /**
     * Gets list of UEs from simulator.
     * @returns {Promise<Object[]>} UE list
     */
    getSimulatorUEs() {
      return this.get('/simulator/ues');
    },

    /**
     * Gets list of data sessions from simulator.
     * @returns {Promise<Object[]>} Session list
     */
    getSimulatorSessions() {
      return this.get('/simulator/sessions');
    },

    /**
     * Gets simulator event history.
     * @returns {Promise<Object[]>} Event list
     */
    getSimulatorEvents() {
      return this.get('/simulator/events');
    },

    /**
     * Starts the simulated cell.
     * @param {Object} [options] - Start options
     * @param {number} [options.timeout] - Timeout in seconds
     * @returns {Promise<Object>} Start result
     */
    startSimulatorCell(options = {}) {
      return this.post('/simulator/cell/start', options);
    },

    /**
     * Stops the simulated cell.
     * @returns {Promise<Object>} Stop result
     */
    stopSimulatorCell() {
      return this.post('/simulator/cell/stop');
    },

    /**
     * Sends SMS via simulator.
     * @param {Object} smsData - SMS data
     * @param {string} smsData.imsi - Target IMSI
     * @param {string} [smsData.pdu] - SMS PDU in hex (for OTA)
     * @param {string} [smsData.text] - Plain text message
     * @returns {Promise<Object>} Send result
     */
    sendSimulatorSMS(smsData) {
      return this.post('/simulator/sms/send', smsData);
    },

    // =========================================================================
    // TLS PSK Server Endpoints
    // =========================================================================

    /**
     * Gets TLS PSK server status.
     * @returns {Promise<Object>} Server status including running state, host, port, session counts
     */
    getServerStatus() {
      return this.get('/server/status');
    },

    /**
     * Gets sessions from TLS PSK server.
     * @returns {Promise<Object[]>} Server sessions with state, PSK identity, client address
     */
    getServerSessions() {
      return this.get('/server/sessions');
    },

    /**
     * Gets TLS PSK server configuration.
     * @returns {Promise<Object>} Server configuration including cipher config
     */
    getServerConfig() {
      return this.get('/server/config');
    },

    // =========================================================================
    // Script Endpoints
    // =========================================================================

    /**
     * Gets all scripts.
     * @returns {Promise<Object>} Scripts list
     */
    getScripts() {
      return this.get('/scripts');
    },

    /**
     * Gets a specific script.
     * @param {string} scriptId - Script ID
     * @returns {Promise<Object>} Script
     */
    getScript(scriptId) {
      return this.get(`/scripts/${encodeURIComponent(scriptId)}`);
    },

    /**
     * Creates a new script.
     * @param {Object} script - Script data
     * @returns {Promise<Object>} Created script
     */
    createScript(script) {
      return this.post('/scripts', script);
    },

    /**
     * Updates a script.
     * @param {string} scriptId - Script ID
     * @param {Object} script - Script data
     * @returns {Promise<Object>} Updated script
     */
    updateScript(scriptId, script) {
      return this.put(`/scripts/${encodeURIComponent(scriptId)}`, script);
    },

    /**
     * Deletes a script.
     * @param {string} scriptId - Script ID
     * @returns {Promise<void>}
     */
    deleteScript(scriptId) {
      return this.delete(`/scripts/${encodeURIComponent(scriptId)}`);
    },

    /**
     * Executes a script for a session.
     * @param {string} sessionId - Session ID
     * @param {string} scriptId - Script ID
     * @returns {Promise<Object>} Execution result
     */
    executeScript(sessionId, scriptId) {
      return this.post(`/scripts/${encodeURIComponent(scriptId)}/execute`, { sessionId });
    },

    // =========================================================================
    // Template Endpoints
    // =========================================================================

    /**
     * Gets all templates.
     * @returns {Promise<Object>} Templates list
     */
    getTemplates() {
      return this.get('/templates');
    },

    /**
     * Gets a specific template.
     * @param {string} templateId - Template ID
     * @returns {Promise<Object>} Template
     */
    getTemplate(templateId) {
      return this.get(`/templates/${encodeURIComponent(templateId)}`);
    },

    /**
     * Creates a new template.
     * @param {Object} template - Template data
     * @returns {Promise<Object>} Created template
     */
    createTemplate(template) {
      return this.post('/templates', template);
    },

    /**
     * Updates a template.
     * @param {string} templateId - Template ID
     * @param {Object} template - Template data
     * @returns {Promise<Object>} Updated template
     */
    updateTemplate(templateId, template) {
      return this.put(`/templates/${encodeURIComponent(templateId)}`, template);
    },

    /**
     * Deletes a template.
     * @param {string} templateId - Template ID
     * @returns {Promise<void>}
     */
    deleteTemplate(templateId) {
      return this.delete(`/templates/${encodeURIComponent(templateId)}`);
    },

    /**
     * Renders a template with parameters.
     * @param {string} templateId - Template ID
     * @param {Object} params - Template parameters
     * @returns {Promise<Object>} Rendered commands
     */
    renderTemplate(templateId, params) {
      return this.post(`/templates/${encodeURIComponent(templateId)}/render`, { params });
    },

    /**
     * Previews a rendered template.
     * @param {string} templateId - Template ID
     * @param {Object} params - Template parameters
     * @returns {Promise<Object>} Preview result
     */
    previewTemplate(templateId, params) {
      return this.post(`/templates/${encodeURIComponent(templateId)}/preview`, { params });
    },

    /**
     * Renders and executes a template for a session.
     * @param {string} sessionId - Session ID
     * @param {string} templateId - Template ID
     * @param {Object} params - Template parameters
     * @returns {Promise<Object>} Execution result
     */
    renderAndExecuteTemplate(sessionId, templateId, params) {
      return this.post(`/templates/${encodeURIComponent(templateId)}/render`, {
        sessionId,
        params,
        execute: true,
      });
    },
  };
}

// Export singleton instance
export const api = createAPIClient();
