/**
 * Script Editor Component for GP OTA Tester Dashboard
 *
 * Provides UI for creating and editing APDU scripts with command list editing,
 * hex validation, and tag management.
 */

import { api } from '../api.js';

/**
 * Creates a script editor component.
 * @param {Object} options - Configuration options
 * @param {HTMLElement} options.container - Container element
 * @param {Function} [options.onSave] - Callback when script is saved
 * @param {Function} [options.onCancel] - Callback when editing is cancelled
 * @returns {Object} Script editor API
 */
export function createScriptEditor(options) {
  const { container, onSave, onCancel } = options;

  let scriptId = null;
  let isNew = true;
  let isSaving = false;

  // Form data
  let formData = {
    id: '',
    name: '',
    description: '',
    tags: [],
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
   * Validates hex string.
   * @param {string} hex - Hex string to validate
   * @returns {boolean} True if valid
   */
  function isValidHex(hex) {
    if (!hex) return false;
    const cleaned = hex.replace(/\s/g, '');
    return /^[0-9A-Fa-f]*$/.test(cleaned) && cleaned.length % 2 === 0 && cleaned.length >= 8;
  }

  /**
   * Formats hex string with spaces.
   * @param {string} hex - Hex string
   * @returns {string} Formatted string
   */
  function formatHex(hex) {
    const cleaned = hex.replace(/\s/g, '').toUpperCase();
    return cleaned.match(/.{1,2}/g)?.join(' ') || '';
  }

  /**
   * Renders the editor.
   */
  function render() {
    container.innerHTML = `
      <div class="script-editor">
        <div class="script-editor__header">
          <h3 class="script-editor__title">${isNew ? 'New Script' : 'Edit Script'}</h3>
          <button class="btn btn--ghost btn--icon" id="editor-close" title="Close">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3l10 10M13 3l-10 10"/>
            </svg>
          </button>
        </div>

        <form id="script-editor-form" class="script-editor__form">
          <div class="script-editor__section">
            <div class="script-editor__field">
              <label class="script-editor__label" for="script-id">
                Script ID <span class="text-danger">*</span>
              </label>
              <input
                type="text"
                id="script-id"
                class="script-editor__input"
                value="${escapeHtml(formData.id)}"
                placeholder="e.g., my-custom-script"
                pattern="[a-z0-9\\-]+"
                ${!isNew ? 'readonly' : ''}
                required
              >
              <span class="script-editor__hint">Lowercase letters, numbers, and hyphens only</span>
            </div>

            <div class="script-editor__field">
              <label class="script-editor__label" for="script-name">
                Name <span class="text-danger">*</span>
              </label>
              <input
                type="text"
                id="script-name"
                class="script-editor__input"
                value="${escapeHtml(formData.name)}"
                placeholder="e.g., My Custom Script"
                required
              >
            </div>

            <div class="script-editor__field">
              <label class="script-editor__label" for="script-description">Description</label>
              <textarea
                id="script-description"
                class="script-editor__textarea"
                placeholder="Brief description of what this script does..."
                rows="2"
              >${escapeHtml(formData.description)}</textarea>
            </div>

            <div class="script-editor__field">
              <label class="script-editor__label" for="script-tags">Tags</label>
              <div class="script-editor__tags-input">
                <div class="script-editor__tags" id="tags-container">
                  ${formData.tags.map(tag => `
                    <span class="script-editor__tag">
                      ${escapeHtml(tag)}
                      <button type="button" class="script-editor__tag-remove" data-tag="${escapeHtml(tag)}">&times;</button>
                    </span>
                  `).join('')}
                </div>
                <input
                  type="text"
                  id="tag-input"
                  class="script-editor__tag-field"
                  placeholder="Add tag..."
                >
              </div>
              <span class="script-editor__hint">Press Enter to add tag</span>
            </div>
          </div>

          <div class="script-editor__section">
            <div class="script-editor__section-header">
              <h4 class="script-editor__section-title">Commands</h4>
              <button type="button" class="btn btn--secondary btn--sm" id="add-command">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 2v8M2 6h8"/>
                </svg>
                Add Command
              </button>
            </div>

            <div class="script-editor__commands" id="commands-list">
              ${formData.commands.length === 0 ? `
                <div class="script-editor__empty">
                  <p class="text-sm text-secondary">No commands added yet</p>
                  <p class="text-xs text-tertiary">Click "Add Command" to add APDU commands</p>
                </div>
              ` : formData.commands.map((cmd, index) => renderCommand(cmd, index)).join('')}
            </div>
          </div>

          <div class="script-editor__actions">
            <button type="button" class="btn btn--ghost" id="editor-cancel">Cancel</button>
            <button type="submit" class="btn btn--primary" ${isSaving ? 'disabled' : ''}>
              ${isSaving ? 'Saving...' : (isNew ? 'Create Script' : 'Save Changes')}
            </button>
          </div>
        </form>
      </div>
    `;

    attachEventListeners();
  }

  /**
   * Renders a command row.
   * @param {Object} cmd - Command data
   * @param {number} index - Command index
   * @returns {string} HTML string
   */
  function renderCommand(cmd, index) {
    const isValid = isValidHex(cmd.hex);
    const hexFormatted = formatHex(cmd.hex || '');

    return `
      <div class="script-editor__command" data-index="${index}">
        <div class="script-editor__command-header">
          <span class="script-editor__command-num">${index + 1}</span>
          <div class="script-editor__command-actions">
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
        <div class="script-editor__command-fields">
          <div class="script-editor__field">
            <label class="script-editor__label">Name (optional)</label>
            <input
              type="text"
              class="script-editor__input cmd-name"
              value="${escapeHtml(cmd.name || '')}"
              placeholder="e.g., SELECT AID"
            >
          </div>
          <div class="script-editor__field">
            <label class="script-editor__label">APDU Hex <span class="text-danger">*</span></label>
            <input
              type="text"
              class="script-editor__input script-editor__input--mono cmd-hex ${!isValid && cmd.hex ? 'script-editor__input--error' : ''}"
              value="${escapeHtml(hexFormatted)}"
              placeholder="e.g., 00 A4 04 00 07 A0 00 00 00 04 10 10"
              required
            >
            ${!isValid && cmd.hex ? '<span class="script-editor__error">Invalid APDU (min 4 bytes, even length)</span>' : ''}
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Attaches event listeners.
   */
  function attachEventListeners() {
    // Close button
    container.querySelector('#editor-close')?.addEventListener('click', () => {
      if (onCancel) onCancel();
    });

    // Cancel button
    container.querySelector('#editor-cancel')?.addEventListener('click', () => {
      if (onCancel) onCancel();
    });

    // Form submission
    container.querySelector('#script-editor-form')?.addEventListener('submit', handleSubmit);

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
    container.querySelectorAll('.script-editor__tag-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const tag = btn.dataset.tag;
        formData.tags = formData.tags.filter(t => t !== tag);
        render();
      });
    });

    // Command event listeners
    container.querySelectorAll('.script-editor__command').forEach(cmdEl => {
      const index = parseInt(cmdEl.dataset.index, 10);

      // Name input
      cmdEl.querySelector('.cmd-name')?.addEventListener('input', (e) => {
        formData.commands[index].name = e.target.value;
      });

      // Hex input
      cmdEl.querySelector('.cmd-hex')?.addEventListener('input', (e) => {
        const value = e.target.value.replace(/\s/g, '').toUpperCase();
        formData.commands[index].hex = value;
        // Re-render to update validation
        const cmdList = container.querySelector('#commands-list');
        cmdList.innerHTML = formData.commands.map((cmd, i) => renderCommand(cmd, i)).join('');
        attachCommandListeners();
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
    container.querySelector('#script-id')?.addEventListener('input', (e) => {
      formData.id = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
      e.target.value = formData.id;
    });

    container.querySelector('#script-name')?.addEventListener('input', (e) => {
      formData.name = e.target.value;
    });

    container.querySelector('#script-description')?.addEventListener('input', (e) => {
      formData.description = e.target.value;
    });
  }

  /**
   * Attaches listeners to command list (for re-renders).
   */
  function attachCommandListeners() {
    container.querySelectorAll('.script-editor__command').forEach(cmdEl => {
      const index = parseInt(cmdEl.dataset.index, 10);

      cmdEl.querySelector('.cmd-name')?.addEventListener('input', (e) => {
        formData.commands[index].name = e.target.value;
      });

      cmdEl.querySelector('.cmd-hex')?.addEventListener('input', (e) => {
        const value = e.target.value.replace(/\s/g, '').toUpperCase();
        formData.commands[index].hex = value;
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
   * Handles form submission.
   * @param {Event} e - Submit event
   */
  async function handleSubmit(e) {
    e.preventDefault();

    // Validate commands
    const hasInvalidCommands = formData.commands.some(cmd => !isValidHex(cmd.hex));
    if (hasInvalidCommands) {
      showToast('Please fix invalid APDU commands', 'error');
      return;
    }

    if (formData.commands.length === 0) {
      showToast('Please add at least one command', 'warning');
      return;
    }

    isSaving = true;
    render();

    try {
      // Prepare script data
      const scriptData = {
        id: formData.id,
        name: formData.name,
        description: formData.description || undefined,
        tags: formData.tags.length > 0 ? formData.tags : undefined,
        commands: formData.commands.map(cmd => ({
          hex: cmd.hex.replace(/\s/g, '').toUpperCase(),
          name: cmd.name || undefined,
        })),
      };

      if (isNew) {
        await api.createScript(scriptData);
        showToast(`Script "${formData.name}" created`, 'success');
      } else {
        await api.updateScript(scriptId, scriptData);
        showToast(`Script "${formData.name}" updated`, 'success');
      }

      if (onSave) onSave(scriptData);
    } catch (error) {
      console.error('Failed to save script:', error);
      showToast(`Failed to save script: ${error.message}`, 'error');
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
   * Loads a script for editing.
   * @param {string} id - Script ID
   */
  async function loadScript(id) {
    try {
      const script = await api.getScript(id);
      scriptId = id;
      isNew = false;
      formData = {
        id: script.id,
        name: script.name || '',
        description: script.description || '',
        tags: script.tags || [],
        commands: (script.commands || []).map(cmd => ({
          name: cmd.name || '',
          hex: cmd.hex || '',
        })),
      };
      render();
    } catch (error) {
      console.error('Failed to load script:', error);
      showToast(`Failed to load script: ${error.message}`, 'error');
    }
  }

  /**
   * Creates a new script.
   */
  function newScript() {
    scriptId = null;
    isNew = true;
    formData = {
      id: '',
      name: '',
      description: '',
      tags: [],
      commands: [],
    };
    render();
  }

  // Initial render
  render();

  return {
    render,
    loadScript,
    newScript,
    isNew: () => isNew,
    getFormData: () => ({ ...formData }),
  };
}
