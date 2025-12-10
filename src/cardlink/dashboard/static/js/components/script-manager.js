/**
 * Script Manager Component for GP OTA Tester Dashboard
 *
 * Provides UI for browsing, searching, and executing APDU scripts and templates.
 */

import { state } from '../state.js';
import { api } from '../api.js';
import { createScriptEditor } from './script-editor.js';
import { createTemplateBuilder } from './template-builder.js';

/**
 * Creates a script manager component.
 * @param {HTMLElement} container - Container element
 * @returns {Object} Script manager API
 */
export function createScriptManager(container) {
  let scripts = [];
  let templates = [];
  let isLoading = false;
  let loadError = null;
  let activeTab = 'scripts'; // 'scripts' or 'templates'
  let searchQuery = '';
  let selectedScriptId = null;
  let selectedTemplateId = null;
  let templateParams = {};
  let editorMode = null; // null | 'new' | 'edit'
  let editingScriptId = null;
  let scriptEditor = null;
  let templateEditorMode = null; // null | 'new' | 'edit'
  let editingTemplateId = null;
  let templateBuilder = null;

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
   * Renders the component.
   */
  function render() {
    // If in script editor mode, show the script editor
    if (editorMode) {
      container.innerHTML = '<div class="script-manager__editor-container" id="editor-container"></div>';
      initializeEditor();
      return;
    }

    // If in template editor mode, show the template builder
    if (templateEditorMode) {
      container.innerHTML = '<div class="script-manager__editor-container" id="template-editor-container"></div>';
      initializeTemplateEditor();
      return;
    }

    container.innerHTML = `
      <div class="script-manager">
        <div class="script-manager__header">
          <div class="script-manager__tabs">
            <button class="script-manager__tab ${activeTab === 'scripts' ? 'script-manager__tab--active' : ''}" data-tab="scripts">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="2" width="10" height="10" rx="1"/>
                <path d="M5 5h4M5 7h4M5 9h2"/>
              </svg>
              Scripts
            </button>
            <button class="script-manager__tab ${activeTab === 'templates' ? 'script-manager__tab--active' : ''}" data-tab="templates">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="2" width="10" height="10" rx="1"/>
                <path d="M5 5h4M5 7h4M5 9h4" stroke-dasharray="1 1"/>
              </svg>
              Templates
            </button>
          </div>
          <div class="script-manager__header-actions">
            ${activeTab === 'scripts' ? `
              <button class="btn btn--primary btn--sm" id="new-script-btn" title="Create new script">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 2v8M2 6h8"/>
                </svg>
                New
              </button>
            ` : `
              <button class="btn btn--primary btn--sm" id="new-template-btn" title="Create new template">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 2v8M2 6h8"/>
                </svg>
                New
              </button>
            `}
            <button class="btn btn--ghost btn--icon btn--sm" id="script-refresh" title="Refresh">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 7a5 5 0 11-1.2-3.2M12 2v3h-3"/>
              </svg>
            </button>
          </div>
        </div>

        <div class="script-manager__search">
          <input type="search" placeholder="Search ${activeTab}..." value="${escapeHtml(searchQuery)}" class="script-manager__search-input">
        </div>

        <div class="script-manager__content">
          ${renderContent()}
        </div>

        ${activeTab === 'templates' && selectedTemplateId ? renderTemplateForm() : ''}
      </div>
    `;

    attachEventListeners();
  }

  /**
   * Initializes the script editor component.
   */
  function initializeEditor() {
    const editorContainer = container.querySelector('#editor-container');
    if (!editorContainer) return;

    scriptEditor = createScriptEditor({
      container: editorContainer,
      onSave: () => {
        editorMode = null;
        editingScriptId = null;
        loadData();
      },
      onCancel: () => {
        editorMode = null;
        editingScriptId = null;
        render();
      },
    });

    if (editorMode === 'edit' && editingScriptId) {
      scriptEditor.loadScript(editingScriptId);
    } else {
      scriptEditor.newScript();
    }
  }

  /**
   * Initializes the template builder component.
   */
  function initializeTemplateEditor() {
    const editorContainer = container.querySelector('#template-editor-container');
    if (!editorContainer) return;

    templateBuilder = createTemplateBuilder({
      container: editorContainer,
      onSave: () => {
        templateEditorMode = null;
        editingTemplateId = null;
        loadData();
      },
      onCancel: () => {
        templateEditorMode = null;
        editingTemplateId = null;
        render();
      },
    });

    if (templateEditorMode === 'edit' && editingTemplateId) {
      templateBuilder.loadTemplate(editingTemplateId);
    } else {
      templateBuilder.newTemplate();
    }
  }

  /**
   * Renders main content based on active tab and state.
   * @returns {string} HTML string
   */
  function renderContent() {
    if (isLoading) {
      return renderLoading();
    }

    if (loadError) {
      return renderError(loadError);
    }

    if (activeTab === 'scripts') {
      return renderScriptList();
    } else {
      return renderTemplateList();
    }
  }

  /**
   * Renders loading skeleton.
   * @returns {string} HTML string
   */
  function renderLoading() {
    return `
      <div class="script-manager__loading">
        <div class="skeleton skeleton--text"></div>
        <div class="skeleton skeleton--text"></div>
        <div class="skeleton skeleton--text"></div>
      </div>
    `;
  }

  /**
   * Renders error state.
   * @param {string} message - Error message
   * @returns {string} HTML string
   */
  function renderError(message) {
    return `
      <div class="script-manager__error">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p class="text-sm">${escapeHtml(message)}</p>
        <button class="btn btn--secondary btn--sm" id="script-retry">Retry</button>
      </div>
    `;
  }

  /**
   * Renders empty state.
   * @param {string} type - 'scripts' or 'templates'
   * @returns {string} HTML string
   */
  function renderEmpty(type) {
    return `
      <div class="script-manager__empty">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="8" y="6" width="24" height="28" rx="2"/>
          <path d="M14 14h12M14 20h12M14 26h8"/>
        </svg>
        <p class="text-sm">No ${type} found</p>
        ${searchQuery ? '<p class="text-xs text-secondary">Try a different search term</p>' : ''}
      </div>
    `;
  }

  /**
   * Renders script list.
   * @returns {string} HTML string
   */
  function renderScriptList() {
    const filteredScripts = filterItems(scripts);

    if (filteredScripts.length === 0) {
      return renderEmpty('scripts');
    }

    return `
      <div class="script-manager__list" role="listbox">
        ${filteredScripts.map(script => renderScriptItem(script)).join('')}
      </div>
    `;
  }

  /**
   * Renders a script item.
   * @param {Object} script - Script data
   * @returns {string} HTML string
   */
  function renderScriptItem(script) {
    const isSelected = script.id === selectedScriptId;
    const cmdCount = script.commands?.length || 0;
    const tags = script.tags || [];

    return `
      <div class="script-manager__item ${isSelected ? 'script-manager__item--selected' : ''}"
           data-script-id="${escapeHtml(script.id)}"
           role="option"
           aria-selected="${isSelected}">
        <div class="script-manager__item-header">
          <span class="script-manager__item-name">${escapeHtml(script.name || script.id)}</span>
          <span class="script-manager__item-count">${cmdCount} cmd${cmdCount !== 1 ? 's' : ''}</span>
        </div>
        ${script.description ? `<div class="script-manager__item-desc">${escapeHtml(script.description)}</div>` : ''}
        ${tags.length > 0 ? `
          <div class="script-manager__item-tags">
            ${tags.slice(0, 3).map(tag => `<span class="script-manager__tag">${escapeHtml(tag)}</span>`).join('')}
            ${tags.length > 3 ? `<span class="script-manager__tag script-manager__tag--more">+${tags.length - 3}</span>` : ''}
          </div>
        ` : ''}
        <div class="script-manager__item-actions">
          <button class="btn btn--primary btn--xs script-execute-btn" data-script-id="${escapeHtml(script.id)}" title="Execute script">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 2l6 4-6 4V2z" fill="currentColor"/>
            </svg>
            Run
          </button>
          <button class="btn btn--ghost btn--xs script-view-btn" data-script-id="${escapeHtml(script.id)}" title="View commands">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 6s2-3 4-3 4 3 4 3-2 3-4 3-4-3-4-3z"/>
              <circle cx="6" cy="6" r="1.5"/>
            </svg>
          </button>
          <button class="btn btn--ghost btn--xs script-edit-btn" data-script-id="${escapeHtml(script.id)}" title="Edit script">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M8.5 1.5l2 2L4 10H2v-2l6.5-6.5z"/>
            </svg>
          </button>
          <button class="btn btn--ghost btn--xs script-delete-btn" data-script-id="${escapeHtml(script.id)}" title="Delete script">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 3h8M4 3V2h4v1M5 5v4M7 5v4M3 3l.5 7h5l.5-7"/>
            </svg>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Renders template list.
   * @returns {string} HTML string
   */
  function renderTemplateList() {
    const filteredTemplates = filterItems(templates);

    if (filteredTemplates.length === 0) {
      return renderEmpty('templates');
    }

    return `
      <div class="script-manager__list" role="listbox">
        ${filteredTemplates.map(template => renderTemplateItem(template)).join('')}
      </div>
    `;
  }

  /**
   * Renders a template item.
   * @param {Object} template - Template data
   * @returns {string} HTML string
   */
  function renderTemplateItem(template) {
    const isSelected = template.id === selectedTemplateId;
    const paramCount = Object.keys(template.parameters || {}).length;
    const tags = template.tags || [];

    return `
      <div class="script-manager__item ${isSelected ? 'script-manager__item--selected' : ''}"
           data-template-id="${escapeHtml(template.id)}"
           role="option"
           aria-selected="${isSelected}">
        <div class="script-manager__item-header">
          <span class="script-manager__item-name">${escapeHtml(template.name || template.id)}</span>
          <span class="script-manager__item-count">${paramCount} param${paramCount !== 1 ? 's' : ''}</span>
        </div>
        ${template.description ? `<div class="script-manager__item-desc">${escapeHtml(template.description)}</div>` : ''}
        ${tags.length > 0 ? `
          <div class="script-manager__item-tags">
            ${tags.slice(0, 3).map(tag => `<span class="script-manager__tag">${escapeHtml(tag)}</span>`).join('')}
            ${tags.length > 3 ? `<span class="script-manager__tag script-manager__tag--more">+${tags.length - 3}</span>` : ''}
          </div>
        ` : ''}
        <div class="script-manager__item-actions">
          <button class="btn btn--secondary btn--xs template-select-btn" data-template-id="${escapeHtml(template.id)}" title="Configure and run">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M6 2v8M2 6h8"/>
            </svg>
            Configure
          </button>
          <button class="btn btn--ghost btn--xs template-edit-btn" data-template-id="${escapeHtml(template.id)}" title="Edit template">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M8.5 1.5l2 2L4 10H2v-2l6.5-6.5z"/>
            </svg>
          </button>
          <button class="btn btn--ghost btn--xs template-delete-btn" data-template-id="${escapeHtml(template.id)}" title="Delete template">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 3h8M4 3V2h4v1M5 5v4M7 5v4M3 3l.5 7h5l.5-7"/>
            </svg>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Renders template parameter form.
   * @returns {string} HTML string
   */
  function renderTemplateForm() {
    const template = templates.find(t => t.id === selectedTemplateId);
    if (!template) return '';

    const params = template.parameters || {};
    const paramEntries = Object.entries(params);

    return `
      <div class="script-manager__form">
        <div class="script-manager__form-header">
          <h4 class="script-manager__form-title">${escapeHtml(template.name || template.id)}</h4>
          <button class="btn btn--ghost btn--xs" id="template-form-close" title="Close">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 2l8 8M10 2l-8 8"/>
            </svg>
          </button>
        </div>
        ${template.description ? `<p class="script-manager__form-desc">${escapeHtml(template.description)}</p>` : ''}
        <form id="template-params-form" class="script-manager__params">
          ${paramEntries.map(([name, def]) => renderParamField(name, def)).join('')}
          <div class="script-manager__form-actions">
            <button type="button" class="btn btn--ghost btn--sm" id="template-preview">Preview</button>
            <button type="submit" class="btn btn--primary btn--sm">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 2l6 4-6 4V2z" fill="currentColor"/>
              </svg>
              Run
            </button>
          </div>
        </form>
      </div>
    `;
  }

  /**
   * Renders a parameter input field.
   * @param {string} name - Parameter name
   * @param {Object} def - Parameter definition
   * @returns {string} HTML string
   */
  function renderParamField(name, def) {
    const value = templateParams[name] || def.default || '';
    const isRequired = def.required !== false;
    const placeholder = def.description || `Enter ${name}`;
    const inputType = def.type === 'string' ? 'text' : 'text';

    return `
      <div class="script-manager__param">
        <label class="script-manager__param-label" for="param-${escapeHtml(name)}">
          ${escapeHtml(name)}
          ${isRequired ? '<span class="text-danger">*</span>' : ''}
        </label>
        <input
          type="${inputType}"
          id="param-${escapeHtml(name)}"
          name="${escapeHtml(name)}"
          class="script-manager__param-input"
          value="${escapeHtml(value)}"
          placeholder="${escapeHtml(placeholder)}"
          ${isRequired ? 'required' : ''}
          ${def.type === 'hex' ? 'pattern="[0-9A-Fa-f]*"' : ''}
          ${def.min_length ? `minlength="${def.min_length * 2}"` : ''}
          ${def.max_length ? `maxlength="${def.max_length * 2}"` : ''}
        >
        ${def.description ? `<span class="script-manager__param-hint">${escapeHtml(def.description)}</span>` : ''}
      </div>
    `;
  }

  /**
   * Filters items by search query.
   * @param {Object[]} items - Items to filter
   * @returns {Object[]} Filtered items
   */
  function filterItems(items) {
    if (!searchQuery) return items;

    const query = searchQuery.toLowerCase();
    return items.filter(item => {
      const name = (item.name || '').toLowerCase();
      const id = (item.id || '').toLowerCase();
      const desc = (item.description || '').toLowerCase();
      const tags = (item.tags || []).map(t => t.toLowerCase());

      return name.includes(query) ||
             id.includes(query) ||
             desc.includes(query) ||
             tags.some(t => t.includes(query));
    });
  }

  /**
   * Attaches event listeners.
   */
  function attachEventListeners() {
    // Tab switching
    container.querySelectorAll('.script-manager__tab').forEach(tab => {
      tab.addEventListener('click', () => {
        activeTab = tab.dataset.tab;
        selectedScriptId = null;
        selectedTemplateId = null;
        templateParams = {};
        render();
      });
    });

    // Refresh button
    const refreshBtn = container.querySelector('#script-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', loadData);
    }

    // Retry button
    const retryBtn = container.querySelector('#script-retry');
    if (retryBtn) {
      retryBtn.addEventListener('click', loadData);
    }

    // Search input
    const searchInput = container.querySelector('.script-manager__search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        render();
      });
    }

    // Script items
    container.querySelectorAll('.script-manager__item[data-script-id]').forEach(item => {
      item.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
          selectedScriptId = item.dataset.scriptId;
          render();
        }
      });
    });

    // Script execute buttons
    container.querySelectorAll('.script-execute-btn').forEach(btn => {
      btn.addEventListener('click', () => executeScript(btn.dataset.scriptId));
    });

    // Script view buttons
    container.querySelectorAll('.script-view-btn').forEach(btn => {
      btn.addEventListener('click', () => viewScript(btn.dataset.scriptId));
    });

    // New script button
    const newScriptBtn = container.querySelector('#new-script-btn');
    if (newScriptBtn) {
      newScriptBtn.addEventListener('click', () => {
        editorMode = 'new';
        editingScriptId = null;
        render();
      });
    }

    // Script edit buttons
    container.querySelectorAll('.script-edit-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        editorMode = 'edit';
        editingScriptId = btn.dataset.scriptId;
        render();
      });
    });

    // Script delete buttons
    container.querySelectorAll('.script-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteScript(btn.dataset.scriptId));
    });

    // Template items
    container.querySelectorAll('.script-manager__item[data-template-id]').forEach(item => {
      item.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
          selectedTemplateId = item.dataset.templateId;
          templateParams = {};
          render();
        }
      });
    });

    // Template configure buttons
    container.querySelectorAll('.template-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedTemplateId = btn.dataset.templateId;
        templateParams = {};
        render();
      });
    });

    // New template button
    const newTemplateBtn = container.querySelector('#new-template-btn');
    if (newTemplateBtn) {
      newTemplateBtn.addEventListener('click', () => {
        templateEditorMode = 'new';
        editingTemplateId = null;
        render();
      });
    }

    // Template edit buttons
    container.querySelectorAll('.template-edit-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        templateEditorMode = 'edit';
        editingTemplateId = btn.dataset.templateId;
        render();
      });
    });

    // Template delete buttons
    container.querySelectorAll('.template-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteTemplate(btn.dataset.templateId));
    });

    // Template form close
    const closeBtn = container.querySelector('#template-form-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        selectedTemplateId = null;
        templateParams = {};
        render();
      });
    }

    // Template form submit
    const paramsForm = container.querySelector('#template-params-form');
    if (paramsForm) {
      paramsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(paramsForm);
        const params = {};
        for (const [key, value] of formData.entries()) {
          params[key] = value;
        }
        executeTemplate(selectedTemplateId, params);
      });
    }

    // Template preview
    const previewBtn = container.querySelector('#template-preview');
    if (previewBtn) {
      previewBtn.addEventListener('click', () => {
        const paramsForm = container.querySelector('#template-params-form');
        if (paramsForm) {
          const formData = new FormData(paramsForm);
          const params = {};
          for (const [key, value] of formData.entries()) {
            params[key] = value;
          }
          previewTemplate(selectedTemplateId, params);
        }
      });
    }
  }

  /**
   * Loads scripts and templates from API.
   */
  async function loadData() {
    isLoading = true;
    loadError = null;
    render();

    try {
      const [scriptsData, templatesData] = await Promise.all([
        api.getScripts(),
        api.getTemplates(),
      ]);

      scripts = scriptsData.scripts || [];
      templates = templatesData.templates || [];
      isLoading = false;
      render();
    } catch (error) {
      console.error('Failed to load scripts:', error);
      isLoading = false;
      loadError = error.message || 'Failed to load scripts';
      render();
    }
  }

  /**
   * Executes a script.
   * @param {string} scriptId - Script ID
   */
  async function executeScript(scriptId) {
    const sessionId = state.get('activeSessionId');
    if (!sessionId) {
      showToast('No active session. Select a session first.', 'warning');
      return;
    }

    try {
      const result = await api.executeScript(sessionId, scriptId);
      showToast(`Script "${scriptId}" executed successfully`, 'success');

      // Dispatch event for other components
      window.dispatchEvent(new CustomEvent('script-executed', {
        detail: { scriptId, sessionId, result }
      }));
    } catch (error) {
      console.error('Failed to execute script:', error);
      showToast(`Failed to execute script: ${error.message}`, 'error');
    }
  }

  /**
   * Views script commands.
   * @param {string} scriptId - Script ID
   */
  async function viewScript(scriptId) {
    try {
      const script = await api.getScript(scriptId);
      showScriptModal(script);
    } catch (error) {
      console.error('Failed to load script:', error);
      showToast(`Failed to load script: ${error.message}`, 'error');
    }
  }

  /**
   * Deletes a script after confirmation.
   * @param {string} scriptId - Script ID
   */
  async function deleteScript(scriptId) {
    const script = scripts.find(s => s.id === scriptId);
    const name = script?.name || scriptId;

    if (!confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    try {
      await api.deleteScript(scriptId);
      showToast(`Script "${name}" deleted`, 'success');
      loadData();
    } catch (error) {
      console.error('Failed to delete script:', error);
      showToast(`Failed to delete script: ${error.message}`, 'error');
    }
  }

  /**
   * Deletes a template after confirmation.
   * @param {string} templateId - Template ID
   */
  async function deleteTemplate(templateId) {
    const template = templates.find(t => t.id === templateId);
    const name = template?.name || templateId;

    if (!confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    try {
      await api.deleteTemplate(templateId);
      showToast(`Template "${name}" deleted`, 'success');
      loadData();
    } catch (error) {
      console.error('Failed to delete template:', error);
      showToast(`Failed to delete template: ${error.message}`, 'error');
    }
  }

  /**
   * Executes a template with parameters.
   * @param {string} templateId - Template ID
   * @param {Object} params - Template parameters
   */
  async function executeTemplate(templateId, params) {
    const sessionId = state.get('activeSessionId');
    if (!sessionId) {
      showToast('No active session. Select a session first.', 'warning');
      return;
    }

    try {
      // Render and execute
      const result = await api.renderAndExecuteTemplate(sessionId, templateId, params);
      showToast(`Template "${templateId}" executed successfully`, 'success');

      // Clear form
      selectedTemplateId = null;
      templateParams = {};
      render();

      // Dispatch event
      window.dispatchEvent(new CustomEvent('template-executed', {
        detail: { templateId, sessionId, params, result }
      }));
    } catch (error) {
      console.error('Failed to execute template:', error);
      showToast(`Failed to execute template: ${error.message}`, 'error');
    }
  }

  /**
   * Previews a rendered template.
   * @param {string} templateId - Template ID
   * @param {Object} params - Template parameters
   */
  async function previewTemplate(templateId, params) {
    try {
      const result = await api.previewTemplate(templateId, params);
      showPreviewModal(result);
    } catch (error) {
      console.error('Failed to preview template:', error);
      showToast(`Failed to preview template: ${error.message}`, 'error');
    }
  }

  /**
   * Shows a script details modal.
   * @param {Object} script - Script data
   */
  function showScriptModal(script) {
    const commands = script.commands || [];
    const content = `
      <div class="script-modal">
        <h3>${escapeHtml(script.name || script.id)}</h3>
        ${script.description ? `<p class="text-secondary">${escapeHtml(script.description)}</p>` : ''}
        <div class="script-modal__commands">
          ${commands.map((cmd, i) => `
            <div class="script-modal__command">
              <span class="script-modal__command-num">${i + 1}</span>
              <div class="script-modal__command-content">
                ${cmd.name ? `<div class="script-modal__command-name">${escapeHtml(cmd.name)}</div>` : ''}
                <code class="script-modal__command-hex">${escapeHtml(cmd.hex)}</code>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    window.dispatchEvent(new CustomEvent('show-modal', {
      detail: { title: 'Script Commands', content }
    }));
  }

  /**
   * Shows a template preview modal.
   * @param {Object} result - Preview result
   */
  function showPreviewModal(result) {
    const commands = result.commands || [];
    const content = `
      <div class="script-modal">
        <h3>Preview</h3>
        <div class="script-modal__commands">
          ${commands.map((cmd, i) => `
            <div class="script-modal__command">
              <span class="script-modal__command-num">${i + 1}</span>
              <div class="script-modal__command-content">
                ${cmd.name ? `<div class="script-modal__command-name">${escapeHtml(cmd.name)}</div>` : ''}
                <code class="script-modal__command-hex">${escapeHtml(cmd.hex)}</code>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    window.dispatchEvent(new CustomEvent('show-modal', {
      detail: { title: 'Template Preview', content }
    }));
  }

  /**
   * Shows a toast notification.
   * @param {string} message - Message
   * @param {string} type - 'success' | 'error' | 'warning' | 'info'
   */
  function showToast(message, type = 'info') {
    window.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message, type }
    }));
  }

  // Initial render
  render();

  // Load data
  loadData();

  return {
    render,
    refresh: loadData,

    /**
     * Gets current scripts.
     * @returns {Object[]} Scripts
     */
    getScripts() {
      return scripts;
    },

    /**
     * Gets current templates.
     * @returns {Object[]} Templates
     */
    getTemplates() {
      return templates;
    },

    /**
     * Switches to a tab.
     * @param {string} tab - 'scripts' or 'templates'
     */
    setTab(tab) {
      activeTab = tab;
      render();
    },

    /**
     * Sets search query.
     * @param {string} query - Search query
     */
    setSearch(query) {
      searchQuery = query;
      render();
    },
  };
}
