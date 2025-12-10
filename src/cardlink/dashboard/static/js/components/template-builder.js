/**
 * Template Builder Component for GP OTA Tester Dashboard
 *
 * Provides UI for creating and editing APDU templates with parameter definitions,
 * placeholder syntax, and preview functionality.
 */

import { api } from '../api.js';

/**
 * Creates a template builder component.
 * @param {Object} options - Configuration options
 * @param {HTMLElement} options.container - Container element
 * @param {Function} [options.onSave] - Callback when template is saved
 * @param {Function} [options.onCancel] - Callback when editing is cancelled
 * @returns {Object} Template builder API
 */
export function createTemplateBuilder(options) {
  const { container, onSave, onCancel } = options;

  let templateId = null;
  let isNew = true;
  let isSaving = false;
  let isPreviewing = false;
  let previewResult = null;
  let showTemplatePicker = false;
  let availableTemplates = [];
  let templatesFromFile = false; // Track if templates came from local file vs API

  // Multi-selection and queue state
  let selectedTemplates = []; // Array of { template, paramValues, order }
  let currentEditingTemplate = null; // Template currently being configured with params
  let paramValues = {}; // Current parameter values for editing template
  let showParamEditor = false; // Show parameter input form

  // Form data
  let formData = {
    id: '',
    name: '',
    description: '',
    tags: [],
    parameters: {},
    commands: [],
  };

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
   * Validates hex string with placeholders.
   * @param {string} hex - Hex string with optional ${PLACEHOLDER} syntax
   * @returns {boolean} True if valid
   */
  function isValidTemplateHex(hex) {
    if (!hex) return false;
    // Replace placeholders with dummy hex values for validation
    const cleaned = hex.replace(/\$\{[A-Z_][A-Z0-9_]*\}/gi, 'FF').replace(/\s/g, '');
    return /^[0-9A-Fa-f]*$/.test(cleaned) && cleaned.length % 2 === 0 && cleaned.length >= 8;
  }

  /**
   * Extracts placeholder names from hex string.
   * @param {string} hex - Hex string with ${PLACEHOLDER} syntax
   * @returns {string[]} List of placeholder names
   */
  function extractPlaceholders(hex) {
    const regex = /\$\{([A-Z_][A-Z0-9_]*)\}/gi;
    const placeholders = [];
    let match;
    while ((match = regex.exec(hex)) !== null) {
      if (!placeholders.includes(match[1])) {
        placeholders.push(match[1]);
      }
    }
    return placeholders;
  }

  /**
   * Formats hex string with spaces.
   * @param {string} hex - Hex string
   * @returns {string} Formatted string
   */
  function formatHex(hex) {
    if (!hex) return '';
    // Don't break placeholders
    const parts = [];
    let current = '';
    let inPlaceholder = false;

    for (let i = 0; i < hex.length; i++) {
      const char = hex[i];
      if (char === '$' && hex[i + 1] === '{') {
        if (current) parts.push(current);
        current = '${';
        inPlaceholder = true;
        i++;
      } else if (char === '}' && inPlaceholder) {
        current += '}';
        parts.push(current);
        current = '';
        inPlaceholder = false;
      } else if (inPlaceholder) {
        current += char;
      } else if (/[0-9A-Fa-f]/.test(char)) {
        current += char.toUpperCase();
        if (current.length === 2 && !inPlaceholder) {
          parts.push(current);
          current = '';
        }
      }
    }
    if (current) parts.push(current);

    return parts.join(' ');
  }

  /**
   * Renders the builder.
   */
  function render() {
    container.innerHTML = `
      <div class="template-builder">
        <div class="template-builder__header">
          <h3 class="template-builder__title">${isNew ? 'New Template' : 'Edit Template'}</h3>
          <div class="template-builder__header-actions">
            ${isNew ? `
              <button type="button" class="btn btn--secondary btn--sm" id="load-template-btn" title="Load from existing template">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M2 3h10M2 7h10M2 11h6"/>
                  <path d="M11 9l2 2-2 2"/>
                </svg>
                Load Template
              </button>
            ` : ''}
            <button class="btn btn--ghost btn--icon" id="builder-close" title="Close">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3l10 10M13 3l-10 10"/>
              </svg>
            </button>
          </div>
        </div>

        ${showTemplatePicker ? renderTemplatePicker() : ''}

        <form id="template-builder-form" class="template-builder__form">
          <div class="template-builder__main">
            <div class="template-builder__section">
              <div class="template-builder__field">
                <label class="template-builder__label" for="template-id">
                  Template ID <span class="text-danger">*</span>
                </label>
                <input
                  type="text"
                  id="template-id"
                  class="template-builder__input"
                  value="${escapeHtml(formData.id)}"
                  placeholder="e.g., select-by-aid"
                  pattern="[a-z0-9\\-]+"
                  ${!isNew ? 'readonly' : ''}
                  required
                >
                <span class="template-builder__hint">Lowercase letters, numbers, and hyphens only</span>
              </div>

              <div class="template-builder__field">
                <label class="template-builder__label" for="template-name">
                  Name <span class="text-danger">*</span>
                </label>
                <input
                  type="text"
                  id="template-name"
                  class="template-builder__input"
                  value="${escapeHtml(formData.name)}"
                  placeholder="e.g., Select by AID"
                  required
                >
              </div>

              <div class="template-builder__field">
                <label class="template-builder__label" for="template-description">Description</label>
                <textarea
                  id="template-description"
                  class="template-builder__textarea"
                  placeholder="Brief description of what this template does..."
                  rows="2"
                >${escapeHtml(formData.description)}</textarea>
              </div>

              <div class="template-builder__field">
                <label class="template-builder__label">Tags</label>
                <div class="template-builder__tags-input">
                  <div class="template-builder__tags" id="tags-container">
                    ${formData.tags.map(tag => `
                      <span class="template-builder__tag">
                        ${escapeHtml(tag)}
                        <button type="button" class="template-builder__tag-remove" data-tag="${escapeHtml(tag)}">&times;</button>
                      </span>
                    `).join('')}
                  </div>
                  <input
                    type="text"
                    id="tag-input"
                    class="template-builder__tag-field"
                    placeholder="Add tag..."
                  >
                </div>
                <span class="template-builder__hint">Press Enter to add tag</span>
              </div>
            </div>

            <div class="template-builder__section">
              <div class="template-builder__section-header">
                <h4 class="template-builder__section-title">Parameters</h4>
                <button type="button" class="btn btn--secondary btn--sm" id="add-param">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 2v8M2 6h8"/>
                  </svg>
                  Add Parameter
                </button>
              </div>
              <div class="template-builder__params" id="params-list">
                ${Object.keys(formData.parameters).length === 0 ? `
                  <div class="template-builder__empty">
                    <p class="text-sm text-secondary">No parameters defined</p>
                    <p class="text-xs text-tertiary">Parameters enable dynamic values in commands</p>
                  </div>
                ` : Object.entries(formData.parameters).map(([name, def]) => renderParam(name, def)).join('')}
              </div>
            </div>

            <div class="template-builder__section template-builder__section--commands">
              <div class="template-builder__section-header">
                <h4 class="template-builder__section-title">Commands</h4>
                <button type="button" class="btn btn--secondary btn--sm" id="add-command">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 2v8M2 6h8"/>
                  </svg>
                  Add Command
                </button>
              </div>
              <p class="text-xs text-tertiary" style="margin-bottom: var(--space-2);">
                Use <code>\${PARAM_NAME}</code> syntax to insert parameter values
              </p>
              <div class="template-builder__commands" id="commands-list">
                ${formData.commands.length === 0 ? `
                  <div class="template-builder__empty">
                    <p class="text-sm text-secondary">No commands added yet</p>
                    <p class="text-xs text-tertiary">Add commands with parameter placeholders</p>
                  </div>
                ` : formData.commands.map((cmd, index) => renderCommand(cmd, index)).join('')}
              </div>
            </div>
          </div>

          ${previewResult ? renderPreview() : ''}

          <div class="template-builder__actions">
            <button type="button" class="btn btn--ghost" id="builder-cancel">Cancel</button>
            <button type="button" class="btn btn--secondary" id="builder-preview" ${isPreviewing ? 'disabled' : ''}>
              ${isPreviewing ? 'Previewing...' : 'Preview'}
            </button>
            <button type="submit" class="btn btn--primary" ${isSaving ? 'disabled' : ''}>
              ${isSaving ? 'Saving...' : (isNew ? 'Create Template' : 'Save Changes')}
            </button>
          </div>
        </form>
      </div>
    `;

    attachEventListeners();
  }

  /**
   * Renders a parameter definition.
   * @param {string} name - Parameter name
   * @param {Object} def - Parameter definition
   * @returns {string} HTML string
   */
  function renderParam(name, def) {
    return `
      <div class="template-builder__param" data-param="${escapeHtml(name)}">
        <div class="template-builder__param-header">
          <code class="template-builder__param-name">\${${escapeHtml(name)}}</code>
          <button type="button" class="btn btn--ghost btn--icon btn--xs param-remove" title="Remove parameter">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 2l8 8M10 2l-8 8"/>
            </svg>
          </button>
        </div>
        <div class="template-builder__param-fields">
          <div class="template-builder__field template-builder__field--inline">
            <label class="template-builder__label">Type</label>
            <select class="template-builder__select param-type">
              <option value="hex" ${def.type === 'hex' ? 'selected' : ''}>Hex</option>
              <option value="string" ${def.type === 'string' ? 'selected' : ''}>String</option>
            </select>
          </div>
          <div class="template-builder__field template-builder__field--inline">
            <label class="template-builder__label">Min Length</label>
            <input
              type="number"
              class="template-builder__input template-builder__input--sm param-min"
              value="${def.min_length || ''}"
              placeholder="0"
              min="0"
            >
          </div>
          <div class="template-builder__field template-builder__field--inline">
            <label class="template-builder__label">Max Length</label>
            <input
              type="number"
              class="template-builder__input template-builder__input--sm param-max"
              value="${def.max_length || ''}"
              placeholder="256"
              min="1"
            >
          </div>
        </div>
        <div class="template-builder__field">
          <label class="template-builder__label">Description</label>
          <input
            type="text"
            class="template-builder__input param-desc"
            value="${escapeHtml(def.description || '')}"
            placeholder="Brief description of this parameter..."
          >
        </div>
      </div>
    `;
  }

  /**
   * Renders a command row.
   * @param {Object} cmd - Command data
   * @param {number} index - Command index
   * @returns {string} HTML string
   */
  function renderCommand(cmd, index) {
    const isValid = isValidTemplateHex(cmd.hex);
    const hexFormatted = formatHex(cmd.hex || '');
    const placeholders = extractPlaceholders(cmd.hex || '');

    return `
      <div class="template-builder__command" data-index="${index}">
        <div class="template-builder__command-header">
          <span class="template-builder__command-num">${index + 1}</span>
          <div class="template-builder__command-actions">
            <button type="button" class="btn btn--ghost btn--icon btn--xs cmd-move-up" title="Move up" ${index === 0 ? 'disabled' : ''}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 7l4-4 4 4"/>
              </svg>
            </button>
            <button type="button" class="btn btn--ghost btn--icon btn--xs cmd-move-down" title="Move down" ${index === formData.commands.length - 1 ? 'disabled' : ''}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 5l4 4 4-4"/>
              </svg>
            </button>
            <button type="button" class="btn btn--ghost btn--icon btn--xs cmd-remove" title="Remove">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 2l8 8M10 2l-8 8"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="template-builder__command-fields">
          <div class="template-builder__field">
            <label class="template-builder__label">Name (optional)</label>
            <input
              type="text"
              class="template-builder__input cmd-name"
              value="${escapeHtml(cmd.name || '')}"
              placeholder="e.g., SELECT by AID"
            >
          </div>
          <div class="template-builder__field">
            <label class="template-builder__label">APDU Hex <span class="text-danger">*</span></label>
            <input
              type="text"
              class="template-builder__input template-builder__input--mono cmd-hex ${!isValid && cmd.hex ? 'template-builder__input--error' : ''}"
              value="${escapeHtml(hexFormatted)}"
              placeholder="e.g., 00 A4 04 00 \${AID} 00"
              required
            >
            ${!isValid && cmd.hex ? '<span class="template-builder__error">Invalid template APDU</span>' : ''}
            ${placeholders.length > 0 ? `
              <span class="template-builder__placeholders">
                Uses: ${placeholders.map(p => `<code>\${${escapeHtml(p)}}</code>`).join(', ')}
              </span>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Renders the preview section.
   * @returns {string} HTML string
   */
  function renderPreview() {
    if (!previewResult) return '';

    const commands = previewResult.commands || [];

    return `
      <div class="template-builder__preview">
        <div class="template-builder__preview-header">
          <h4 class="template-builder__section-title">Preview Result</h4>
          <button type="button" class="btn btn--ghost btn--xs" id="close-preview">Close</button>
        </div>
        <div class="template-builder__preview-commands">
          ${commands.map((cmd, i) => `
            <div class="template-builder__preview-command">
              <span class="template-builder__preview-num">${i + 1}</span>
              <div class="template-builder__preview-content">
                ${cmd.name ? `<div class="template-builder__preview-name">${escapeHtml(cmd.name)}</div>` : ''}
                <code class="template-builder__preview-hex">${escapeHtml(cmd.hex)}</code>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  /**
   * Renders the template picker modal.
   * @returns {string} HTML string
   */
  function renderTemplatePicker() {
    const hasQueue = selectedTemplates.length > 0;

    return `
      <div class="template-builder__picker-overlay" id="picker-overlay">
        <div class="template-builder__picker ${hasQueue ? 'template-builder__picker--with-queue' : ''}">
          <div class="template-builder__picker-header">
            <h4 class="template-builder__picker-title">Select Templates</h4>
            <button type="button" class="btn btn--ghost btn--icon btn--xs" id="close-picker">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 2l10 10M12 2l-10 10"/>
              </svg>
            </button>
          </div>

          <div class="template-builder__picker-content">
            <!-- Left side: Template list -->
            <div class="template-builder__picker-body">
              <!-- File Browser Section -->
              <div class="template-builder__picker-file-section">
                <p class="text-sm text-secondary" style="margin-bottom: var(--space-2);">Load from YAML file:</p>
                <input type="file" id="template-file-input" accept=".yaml,.yml" style="display: none;">
                <button type="button" class="btn btn--secondary btn--sm" id="browse-files-btn" style="width: 100%;">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M2 4v7a1 1 0 001 1h8a1 1 0 001-1V6a1 1 0 00-1-1H7L5.5 3H3a1 1 0 00-1 1z"/>
                  </svg>
                  Browse YAML Files...
                </button>
              </div>

              <div class="template-builder__picker-divider">
                <span class="text-xs text-tertiary">click to add to queue</span>
              </div>

              ${availableTemplates.length === 0 ? `
                <div class="template-builder__picker-empty">
                  <p class="text-sm text-secondary">No templates available</p>
                  <p class="text-xs text-tertiary">Use the file browser above to load from a local file</p>
                </div>
              ` : `
                <div class="template-builder__picker-list">
                  ${availableTemplates.map(t => {
                    const paramCount = Object.keys(t.parameters || {}).length;
                    return `
                      <button type="button" class="template-builder__picker-item" data-template-id="${escapeHtml(t.id)}">
                        <div class="template-builder__picker-item-info">
                          <div class="template-builder__picker-item-name">${escapeHtml(t.name || t.id)}</div>
                          ${t.description ? `<div class="template-builder__picker-item-desc">${escapeHtml(t.description)}</div>` : ''}
                          ${paramCount > 0 ? `
                            <div class="template-builder__picker-item-params">
                              ${Object.entries(t.parameters || {}).map(([name, def]) => `
                                <span class="template-builder__picker-param">\${${escapeHtml(name)}}</span>
                              `).join('')}
                            </div>
                          ` : ''}
                        </div>
                        <div class="template-builder__picker-item-meta">
                          <span class="text-xs text-tertiary">${(t.commands || []).length} cmd${(t.commands || []).length !== 1 ? 's' : ''}</span>
                          ${paramCount > 0 ? `<span class="text-xs text-warning">${paramCount} param${paramCount !== 1 ? 's' : ''}</span>` : ''}
                        </div>
                      </button>
                    `;
                  }).join('')}
                </div>
              `}
            </div>

            <!-- Right side: Queue and param editor -->
            <div class="template-builder__picker-sidebar">
              ${showParamEditor && currentEditingTemplate ? renderParamEditor() : renderQueue()}
            </div>
          </div>

          <div class="template-builder__picker-footer">
            <button type="button" class="btn btn--ghost" id="cancel-picker">Cancel</button>
            <button type="button" class="btn btn--primary" id="apply-queue" ${selectedTemplates.length === 0 ? 'disabled' : ''}>
              Apply Queue (${selectedTemplates.length})
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Renders the parameter editor form.
   * @returns {string} HTML string
   */
  function renderParamEditor() {
    if (!currentEditingTemplate) return '';

    const params = currentEditingTemplate.parameters || {};
    const paramEntries = Object.entries(params);

    return `
      <div class="template-builder__param-editor">
        <div class="template-builder__param-editor-header">
          <h5 class="template-builder__param-editor-title">
            Configure: ${escapeHtml(currentEditingTemplate.name || currentEditingTemplate.id)}
          </h5>
        </div>
        <div class="template-builder__param-editor-body">
          ${paramEntries.map(([name, def]) => `
            <div class="template-builder__param-input-group">
              <label class="template-builder__param-input-label">
                <code>\${${escapeHtml(name)}}</code>
                ${def.description ? `<span class="text-xs text-tertiary"> - ${escapeHtml(def.description)}</span>` : ''}
              </label>
              <input
                type="text"
                class="template-builder__input template-builder__input--mono param-value-input"
                data-param="${escapeHtml(name)}"
                value="${escapeHtml(paramValues[name] || '')}"
                placeholder="${def.type === 'hex' ? 'Hex value (e.g., A0000000041010)' : 'Text value'}"
              >
              ${def.min_length || def.max_length ? `
                <span class="text-xs text-tertiary">
                  Length: ${def.min_length || '0'}-${def.max_length || '256'} bytes
                </span>
              ` : ''}
            </div>
          `).join('')}
        </div>
        <div class="template-builder__param-editor-actions">
          <button type="button" class="btn btn--ghost btn--sm" id="cancel-param-edit">Back</button>
          <button type="button" class="btn btn--primary btn--sm" id="confirm-param-edit">Add to Queue</button>
        </div>
      </div>
    `;
  }

  /**
   * Renders the selection queue.
   * @returns {string} HTML string
   */
  function renderQueue() {
    return `
      <div class="template-builder__queue">
        <div class="template-builder__queue-header">
          <h5 class="template-builder__queue-title">Execution Queue</h5>
          ${selectedTemplates.length > 0 ? `
            <button type="button" class="btn btn--ghost btn--xs" id="clear-queue">Clear All</button>
          ` : ''}
        </div>
        <div class="template-builder__queue-list">
          ${selectedTemplates.length === 0 ? `
            <div class="template-builder__queue-empty">
              <p class="text-sm text-tertiary">No templates selected</p>
              <p class="text-xs text-tertiary">Click templates on the left to add them</p>
            </div>
          ` : selectedTemplates.map((item, index) => `
            <div class="template-builder__queue-item" data-queue-index="${index}">
              <div class="template-builder__queue-item-order">${index + 1}</div>
              <div class="template-builder__queue-item-info">
                <div class="template-builder__queue-item-name">${escapeHtml(item.template.name || item.template.id)}</div>
                ${Object.keys(item.paramValues).length > 0 ? `
                  <div class="template-builder__queue-item-params">
                    ${Object.entries(item.paramValues).map(([k, v]) => `
                      <span class="template-builder__queue-param">${escapeHtml(k)}: ${escapeHtml(v.substring(0, 12))}${v.length > 12 ? '...' : ''}</span>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
              <div class="template-builder__queue-item-actions">
                <button type="button" class="btn btn--ghost btn--icon btn--xs queue-move-up" title="Move up" ${index === 0 ? 'disabled' : ''}>
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 7l4-4 4 4"/>
                  </svg>
                </button>
                <button type="button" class="btn btn--ghost btn--icon btn--xs queue-move-down" title="Move down" ${index === selectedTemplates.length - 1 ? 'disabled' : ''}>
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 5l4 4 4-4"/>
                  </svg>
                </button>
                <button type="button" class="btn btn--ghost btn--icon btn--xs queue-remove" title="Remove">
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 2l8 8M10 2l-8 8"/>
                  </svg>
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  /**
   * Attaches event listeners.
   */
  function attachEventListeners() {
    // Close button
    container.querySelector('#builder-close')?.addEventListener('click', () => {
      if (onCancel) onCancel();
    });

    // Cancel button
    container.querySelector('#builder-cancel')?.addEventListener('click', () => {
      if (onCancel) onCancel();
    });

    // Load Template button
    container.querySelector('#load-template-btn')?.addEventListener('click', handleOpenTemplatePicker);

    // Template picker events
    container.querySelector('#close-picker')?.addEventListener('click', closePickerAndReset);
    container.querySelector('#cancel-picker')?.addEventListener('click', closePickerAndReset);

    container.querySelector('#picker-overlay')?.addEventListener('click', (e) => {
      if (e.target.id === 'picker-overlay') {
        closePickerAndReset();
      }
    });

    // File browser button
    container.querySelector('#browse-files-btn')?.addEventListener('click', () => {
      const fileInput = container.querySelector('#template-file-input');
      if (fileInput) fileInput.click();
    });

    // File input change handler
    container.querySelector('#template-file-input')?.addEventListener('change', handleFileSelect);

    // Template item click - add to queue (with param editor if needed)
    container.querySelectorAll('.template-builder__picker-item').forEach(item => {
      item.addEventListener('click', () => {
        const selectedTemplateId = item.dataset.templateId;
        const template = availableTemplates.find(t => t.id === selectedTemplateId);
        if (template) {
          handleTemplateSelect(template);
        }
      });
    });

    // Apply queue button
    container.querySelector('#apply-queue')?.addEventListener('click', handleApplyQueue);

    // Clear queue button
    container.querySelector('#clear-queue')?.addEventListener('click', () => {
      selectedTemplates = [];
      render();
    });

    // Parameter editor events
    container.querySelectorAll('.param-value-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const paramName = e.target.dataset.param;
        paramValues[paramName] = e.target.value;
      });
    });

    container.querySelector('#cancel-param-edit')?.addEventListener('click', () => {
      showParamEditor = false;
      currentEditingTemplate = null;
      paramValues = {};
      render();
    });

    container.querySelector('#confirm-param-edit')?.addEventListener('click', () => {
      if (currentEditingTemplate) {
        // Validate required params have values
        const params = currentEditingTemplate.parameters || {};
        const missingParams = Object.keys(params).filter(name => !paramValues[name]);
        if (missingParams.length > 0) {
          showToast(`Please fill in: ${missingParams.join(', ')}`, 'warning');
          return;
        }

        // Add to queue
        selectedTemplates.push({
          template: currentEditingTemplate,
          paramValues: { ...paramValues },
        });

        // Reset param editor
        showParamEditor = false;
        currentEditingTemplate = null;
        paramValues = {};
        render();
      }
    });

    // Queue item actions
    container.querySelectorAll('.template-builder__queue-item').forEach(item => {
      const index = parseInt(item.dataset.queueIndex, 10);

      item.querySelector('.queue-move-up')?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (index > 0) {
          const temp = selectedTemplates[index];
          selectedTemplates[index] = selectedTemplates[index - 1];
          selectedTemplates[index - 1] = temp;
          render();
        }
      });

      item.querySelector('.queue-move-down')?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (index < selectedTemplates.length - 1) {
          const temp = selectedTemplates[index];
          selectedTemplates[index] = selectedTemplates[index + 1];
          selectedTemplates[index + 1] = temp;
          render();
        }
      });

      item.querySelector('.queue-remove')?.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedTemplates.splice(index, 1);
        render();
      });
    });

    // Form submission
    container.querySelector('#template-builder-form')?.addEventListener('submit', handleSubmit);

    // Preview button
    container.querySelector('#builder-preview')?.addEventListener('click', handlePreview);

    // Close preview
    container.querySelector('#close-preview')?.addEventListener('click', () => {
      previewResult = null;
      render();
    });

    // Add parameter button
    container.querySelector('#add-param')?.addEventListener('click', addParameter);

    // Add command button
    container.querySelector('#add-command')?.addEventListener('click', addCommand);

    // Tag input
    const tagInput = container.querySelector('#tag-input');
    tagInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const tag = tagInput.value.trim().toLowerCase();
        if (tag && !formData.tags.includes(tag)) {
          formData.tags.push(tag);
          render();
        }
        tagInput.value = '';
      }
    });

    // Tag removal
    container.querySelectorAll('.template-builder__tag-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const tag = btn.dataset.tag;
        formData.tags = formData.tags.filter(t => t !== tag);
        render();
      });
    });

    // Parameter event listeners
    container.querySelectorAll('.template-builder__param').forEach(paramEl => {
      const name = paramEl.dataset.param;

      // Type select
      paramEl.querySelector('.param-type')?.addEventListener('change', (e) => {
        formData.parameters[name].type = e.target.value;
      });

      // Min length
      paramEl.querySelector('.param-min')?.addEventListener('input', (e) => {
        formData.parameters[name].min_length = e.target.value ? parseInt(e.target.value, 10) : undefined;
      });

      // Max length
      paramEl.querySelector('.param-max')?.addEventListener('input', (e) => {
        formData.parameters[name].max_length = e.target.value ? parseInt(e.target.value, 10) : undefined;
      });

      // Description
      paramEl.querySelector('.param-desc')?.addEventListener('input', (e) => {
        formData.parameters[name].description = e.target.value || undefined;
      });

      // Remove
      paramEl.querySelector('.param-remove')?.addEventListener('click', () => {
        delete formData.parameters[name];
        render();
      });
    });

    // Command event listeners
    container.querySelectorAll('.template-builder__command').forEach(cmdEl => {
      const index = parseInt(cmdEl.dataset.index, 10);

      // Name input
      cmdEl.querySelector('.cmd-name')?.addEventListener('input', (e) => {
        formData.commands[index].name = e.target.value;
      });

      // Hex input
      cmdEl.querySelector('.cmd-hex')?.addEventListener('input', (e) => {
        const value = e.target.value.replace(/\s+/g, ' ').toUpperCase();
        formData.commands[index].hex = value.replace(/\s/g, '');
        // Update commands display only
        updateCommandsList();
      });

      // Move up
      cmdEl.querySelector('.cmd-move-up')?.addEventListener('click', () => {
        if (index > 0) {
          const temp = formData.commands[index];
          formData.commands[index] = formData.commands[index - 1];
          formData.commands[index - 1] = temp;
          render();
        }
      });

      // Move down
      cmdEl.querySelector('.cmd-move-down')?.addEventListener('click', () => {
        if (index < formData.commands.length - 1) {
          const temp = formData.commands[index];
          formData.commands[index] = formData.commands[index + 1];
          formData.commands[index + 1] = temp;
          render();
        }
      });

      // Remove
      cmdEl.querySelector('.cmd-remove')?.addEventListener('click', () => {
        formData.commands.splice(index, 1);
        render();
      });
    });

    // Form field change tracking
    container.querySelector('#template-id')?.addEventListener('input', (e) => {
      formData.id = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
      e.target.value = formData.id;
    });

    container.querySelector('#template-name')?.addEventListener('input', (e) => {
      formData.name = e.target.value;
    });

    container.querySelector('#template-description')?.addEventListener('input', (e) => {
      formData.description = e.target.value;
    });
  }

  /**
   * Updates commands list without full re-render.
   */
  function updateCommandsList() {
    const cmdList = container.querySelector('#commands-list');
    if (cmdList) {
      cmdList.innerHTML = formData.commands.map((cmd, i) => renderCommand(cmd, i)).join('');
      attachCommandListeners();
    }
  }

  /**
   * Attaches listeners to command list elements.
   */
  function attachCommandListeners() {
    container.querySelectorAll('.template-builder__command').forEach(cmdEl => {
      const index = parseInt(cmdEl.dataset.index, 10);

      cmdEl.querySelector('.cmd-name')?.addEventListener('input', (e) => {
        formData.commands[index].name = e.target.value;
      });

      cmdEl.querySelector('.cmd-hex')?.addEventListener('input', (e) => {
        const value = e.target.value.replace(/\s+/g, ' ').toUpperCase();
        formData.commands[index].hex = value.replace(/\s/g, '');
      });

      cmdEl.querySelector('.cmd-move-up')?.addEventListener('click', () => {
        if (index > 0) {
          const temp = formData.commands[index];
          formData.commands[index] = formData.commands[index - 1];
          formData.commands[index - 1] = temp;
          render();
        }
      });

      cmdEl.querySelector('.cmd-move-down')?.addEventListener('click', () => {
        if (index < formData.commands.length - 1) {
          const temp = formData.commands[index];
          formData.commands[index] = formData.commands[index + 1];
          formData.commands[index + 1] = temp;
          render();
        }
      });

      cmdEl.querySelector('.cmd-remove')?.addEventListener('click', () => {
        formData.commands.splice(index, 1);
        render();
      });
    });
  }

  /**
   * Adds a new parameter.
   */
  function addParameter() {
    // Generate a unique parameter name
    let baseName = 'PARAM';
    let counter = 1;
    let name = baseName;
    while (formData.parameters[name]) {
      name = `${baseName}_${counter}`;
      counter++;
    }

    formData.parameters[name] = {
      type: 'hex',
      description: '',
    };
    render();
  }

  /**
   * Adds a new command.
   */
  function addCommand() {
    formData.commands.push({ name: '', hex: '' });
    render();
    // Focus the new hex input
    const inputs = container.querySelectorAll('.cmd-hex');
    if (inputs.length > 0) {
      inputs[inputs.length - 1].focus();
    }
  }

  /**
   * Handles preview button click.
   */
  async function handlePreview() {
    if (formData.commands.length === 0) {
      showToast('Please add at least one command', 'warning');
      return;
    }

    // Generate sample values for preview
    const sampleParams = {};
    for (const [name, def] of Object.entries(formData.parameters)) {
      if (def.type === 'hex') {
        sampleParams[name] = 'AABBCCDD';
      } else {
        sampleParams[name] = 'sample';
      }
    }

    isPreviewing = true;
    render();

    try {
      // If template exists, use API; otherwise, render locally
      if (!isNew && templateId) {
        const result = await api.previewTemplate(templateId, sampleParams);
        previewResult = result;
      } else {
        // Local preview
        previewResult = {
          commands: formData.commands.map(cmd => {
            let hex = cmd.hex;
            for (const [name, value] of Object.entries(sampleParams)) {
              hex = hex.replace(new RegExp(`\\$\\{${name}\\}`, 'gi'), value);
            }
            return { name: cmd.name, hex };
          }),
        };
      }
    } catch (error) {
      console.error('Failed to preview template:', error);
      showToast(`Preview failed: ${error.message}`, 'error');
    } finally {
      isPreviewing = false;
      render();
    }
  }

  /**
   * Opens the template picker modal.
   */
  async function handleOpenTemplatePicker() {
    try {
      // Fetch available templates from API
      const response = await api.getTemplates();
      availableTemplates = response.templates || [];
      templatesFromFile = false; // Templates from API, not file
      showTemplatePicker = true;
      render();
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      showToast(`Failed to load templates: ${error.message}`, 'error');
    }
  }

  /**
   * Loads a template as a new template (copies data but allows new ID).
   * @param {string} sourceTemplateId - The ID of the template to load
   */
  async function loadTemplateAsNew(sourceTemplateId) {
    try {
      const template = await api.getTemplate(sourceTemplateId);

      // Copy template data but leave ID empty for new template
      formData = {
        id: '', // User needs to provide a new unique ID
        name: `${template.name} (Copy)`,
        description: template.description || '',
        tags: template.tags ? [...template.tags] : [],
        parameters: template.parameters ? { ...template.parameters } : {},
        commands: (template.commands || []).map(cmd => ({
          name: cmd.name || '',
          hex: cmd.hex || '',
        })),
      };

      // Keep as new template
      templateId = null;
      isNew = true;
      showTemplatePicker = false;
      previewResult = null;

      render();
      showToast(`Loaded "${template.name}" as base template`, 'info');

      // Focus the ID input so user can provide a new ID
      setTimeout(() => {
        const idInput = container.querySelector('#template-id');
        if (idInput) idInput.focus();
      }, 100);
    } catch (error) {
      console.error('Failed to load template:', error);
      showToast(`Failed to load template: ${error.message}`, 'error');
    }
  }

  /**
   * Handles file selection from the file browser.
   * @param {Event} e - Change event from file input
   */
  function handleFileSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file extension
    const ext = file.name.toLowerCase().split('.').pop();
    if (ext !== 'yaml' && ext !== 'yml') {
      showToast('Please select a YAML file (.yaml or .yml)', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target.result;

        // Check if js-yaml is available
        if (typeof window.jsyaml === 'undefined') {
          showToast('YAML parser not loaded. Please refresh the page.', 'error');
          return;
        }

        // Parse YAML content
        const parsed = window.jsyaml.load(content);

        // Extract templates from the parsed YAML
        let templates = [];

        if (parsed.templates && Array.isArray(parsed.templates)) {
          // Standard format with templates array
          templates = parsed.templates;
        } else if (Array.isArray(parsed)) {
          // Array of templates directly
          templates = parsed;
        } else if (parsed.id && parsed.commands) {
          // Single template object
          templates = [parsed];
        }

        if (templates.length === 0) {
          showToast('No templates found in the YAML file', 'warning');
          return;
        }

        // If there's only one template, load it directly
        if (templates.length === 1) {
          loadTemplateFromData(templates[0]);
          showToast(`Loaded template "${templates[0].name || templates[0].id}" from file`, 'success');
        } else {
          // Multiple templates - show them in the picker
          availableTemplates = templates;
          templatesFromFile = true; // Templates from file, not API
          showTemplatePicker = true;
          render();
          showToast(`Found ${templates.length} templates in file`, 'info');
        }
      } catch (error) {
        console.error('Failed to parse YAML file:', error);
        showToast(`Failed to parse YAML: ${error.message}`, 'error');
      }
    };

    reader.onerror = () => {
      showToast('Failed to read file', 'error');
    };

    reader.readAsText(file);

    // Reset file input so same file can be selected again
    e.target.value = '';
  }

  /**
   * Loads a template from parsed data object.
   * @param {Object} template - Template data object from YAML
   */
  function loadTemplateFromData(template) {
    // Parse parameters if they exist
    let parameters = {};
    if (template.parameters) {
      // Handle both object format and array format
      if (Array.isArray(template.parameters)) {
        template.parameters.forEach(param => {
          if (param.name) {
            parameters[param.name] = {
              type: param.type || 'hex',
              min_length: param.min_length,
              max_length: param.max_length,
              description: param.description,
            };
          }
        });
      } else {
        // Object format: { PARAM_NAME: { type, description, ... } }
        parameters = { ...template.parameters };
      }
    }

    // Copy template data
    formData = {
      id: '', // User needs to provide a new unique ID
      name: template.name ? `${template.name} (Copy)` : 'Loaded Template',
      description: template.description || '',
      tags: template.tags ? [...template.tags] : [],
      parameters: parameters,
      commands: (template.commands || []).map(cmd => ({
        name: cmd.name || '',
        hex: cmd.hex || '',
      })),
    };

    // Keep as new template
    templateId = null;
    isNew = true;
    showTemplatePicker = false;
    previewResult = null;

    render();

    // Focus the ID input so user can provide a new ID
    setTimeout(() => {
      const idInput = container.querySelector('#template-id');
      if (idInput) idInput.focus();
    }, 100);
  }

  /**
   * Closes the template picker and resets selection state.
   */
  function closePickerAndReset() {
    showTemplatePicker = false;
    selectedTemplates = [];
    currentEditingTemplate = null;
    paramValues = {};
    showParamEditor = false;
    render();
  }

  /**
   * Handles template selection from the picker.
   * @param {Object} template - The selected template
   */
  function handleTemplateSelect(template) {
    const params = template.parameters || {};
    const hasParams = Object.keys(params).length > 0;

    if (hasParams) {
      // Show parameter editor for this template
      currentEditingTemplate = template;
      paramValues = {};
      showParamEditor = true;
      render();
    } else {
      // No parameters - add directly to queue
      selectedTemplates.push({
        template: template,
        paramValues: {},
      });
      render();
    }
  }

  /**
   * Applies the selected templates queue to the form.
   */
  function handleApplyQueue() {
    if (selectedTemplates.length === 0) return;

    // If only one template selected, load it as a base
    if (selectedTemplates.length === 1) {
      const item = selectedTemplates[0];
      loadTemplateFromData(item.template);

      // Pre-fill parameter values if any
      if (Object.keys(item.paramValues).length > 0) {
        // Store the param values for later use in preview/execution
        // This is informational since the user may want to change them
        showToast(`Loaded template with ${Object.keys(item.paramValues).length} parameter(s) configured`, 'info');
      }
    } else {
      // Multiple templates - merge their commands into a single template
      const mergedCommands = [];
      const mergedParameters = {};

      for (const item of selectedTemplates) {
        // Render commands with provided parameter values
        for (const cmd of (item.template.commands || [])) {
          let hex = cmd.hex;
          // Replace parameters with values
          for (const [paramName, paramValue] of Object.entries(item.paramValues)) {
            hex = hex.replace(new RegExp(`\\$\\{${paramName}\\}`, 'gi'), paramValue);
          }
          mergedCommands.push({
            name: cmd.name || '',
            hex: hex,
          });
        }

        // Collect any remaining unreplaced parameters
        for (const [paramName, paramDef] of Object.entries(item.template.parameters || {})) {
          if (!item.paramValues[paramName]) {
            mergedParameters[paramName] = paramDef;
          }
        }
      }

      // Create a merged template
      formData = {
        id: '',
        name: 'Merged Template',
        description: `Combined from ${selectedTemplates.length} templates`,
        tags: [],
        parameters: mergedParameters,
        commands: mergedCommands,
      };

      templateId = null;
      isNew = true;
      previewResult = null;

      showToast(`Merged ${selectedTemplates.length} templates with ${mergedCommands.length} commands`, 'success');
    }

    // Close picker
    closePickerAndReset();

    // Focus the ID input
    setTimeout(() => {
      const idInput = container.querySelector('#template-id');
      if (idInput) idInput.focus();
    }, 100);
  }

  /**
   * Handles form submission.
   * @param {Event} e - Submit event
   */
  async function handleSubmit(e) {
    e.preventDefault();

    // Validate commands
    const hasInvalidCommands = formData.commands.some(cmd => !isValidTemplateHex(cmd.hex));
    if (hasInvalidCommands) {
      showToast('Please fix invalid template commands', 'error');
      return;
    }

    if (formData.commands.length === 0) {
      showToast('Please add at least one command', 'warning');
      return;
    }

    isSaving = true;
    render();

    try {
      // Prepare template data
      const templateData = {
        id: formData.id,
        name: formData.name,
        description: formData.description || undefined,
        tags: formData.tags.length > 0 ? formData.tags : undefined,
        parameters: Object.keys(formData.parameters).length > 0 ? formData.parameters : undefined,
        commands: formData.commands.map(cmd => ({
          hex: cmd.hex.replace(/\s/g, '').toUpperCase(),
          name: cmd.name || undefined,
        })),
      };

      if (isNew) {
        await api.createTemplate(templateData);
        showToast(`Template "${formData.name}" created`, 'success');
      } else {
        await api.updateTemplate(templateId, templateData);
        showToast(`Template "${formData.name}" updated`, 'success');
      }

      if (onSave) onSave(templateData);
    } catch (error) {
      console.error('Failed to save template:', error);
      showToast(`Failed to save template: ${error.message}`, 'error');
      isSaving = false;
      render();
    }
  }

  /**
   * Shows a toast notification.
   * @param {string} message - Message
   * @param {string} type - Toast type
   */
  function showToast(message, type = 'info') {
    window.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message, type }
    }));
  }

  /**
   * Loads a template for editing.
   * @param {string} id - Template ID
   */
  async function loadTemplate(id) {
    try {
      const template = await api.getTemplate(id);
      templateId = id;
      isNew = false;
      formData = {
        id: template.id,
        name: template.name || '',
        description: template.description || '',
        tags: template.tags || [],
        parameters: template.parameters || {},
        commands: (template.commands || []).map(cmd => ({
          name: cmd.name || '',
          hex: cmd.hex || '',
        })),
      };
      previewResult = null;
      render();
    } catch (error) {
      console.error('Failed to load template:', error);
      showToast(`Failed to load template: ${error.message}`, 'error');
    }
  }

  /**
   * Creates a new template.
   */
  function newTemplate() {
    templateId = null;
    isNew = true;
    formData = {
      id: '',
      name: '',
      description: '',
      tags: [],
      parameters: {},
      commands: [],
    };
    previewResult = null;
    render();
  }

  // Initial render
  render();

  return {
    render,
    loadTemplate,
    newTemplate,
    isNew: () => isNew,
    getFormData: () => ({ ...formData }),
  };
}
