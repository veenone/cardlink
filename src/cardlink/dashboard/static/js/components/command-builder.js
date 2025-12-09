/**
 * Command Builder Component for GP OTA Tester Dashboard
 *
 * APDU command builder with templates and validation.
 */

import { state } from '../state.js';
import { normalizeHex, isValidHex, padHex, formatHex } from '../utils/hex.js';
import { buildCommand, INSTRUCTIONS } from '../utils/apdu.js';
import { TERMS, createHelpIcon } from '../utils/tooltip.js';

/**
 * Field descriptions for inline help.
 */
const FIELD_HELP = {
  cla: 'Class byte - Identifies the type of command (ISO or proprietary). Common values: 00 (ISO), 80/84 (GlobalPlatform)',
  ins: 'Instruction byte - Specifies the command to execute. Examples: A4 (SELECT), CA (GET DATA), F2 (GET STATUS)',
  p1: 'Parameter 1 - First command parameter. Meaning varies by instruction.',
  p2: 'Parameter 2 - Second command parameter. Meaning varies by instruction.',
  le: 'Length expected - Maximum number of response bytes expected. Use 00 for up to 256 bytes.',
  data: 'Command data - Hex bytes to send with the command (e.g., AID for SELECT)',
};

/**
 * APDU command templates.
 */
const TEMPLATES = {
  select: {
    name: 'SELECT',
    cla: '00',
    ins: 'A4',
    p1: '04',
    p2: '00',
    data: '',
    le: '00',
    description: 'Select application by AID',
  },
  'get-status': {
    name: 'GET STATUS',
    cla: '80',
    ins: 'F2',
    p1: '40',
    p2: '00',
    data: '4F00',
    le: '00',
    description: 'Get card status',
  },
  'get-data': {
    name: 'GET DATA',
    cla: '80',
    ins: 'CA',
    p1: '00',
    p2: '66',
    data: '',
    le: '00',
    description: 'Get card data',
  },
  'get-response': {
    name: 'GET RESPONSE',
    cla: '00',
    ins: 'C0',
    p1: '00',
    p2: '00',
    data: '',
    le: '00',
    description: 'Get remaining response data',
  },
  'initialize-update': {
    name: 'INITIALIZE UPDATE',
    cla: '80',
    ins: '50',
    p1: '00',
    p2: '00',
    data: '',
    le: '00',
    description: 'Initialize secure channel',
  },
};

/**
 * Creates a command builder component.
 * @param {Object} elements - DOM elements
 * @param {HTMLElement} elements.form - Form element
 * @param {HTMLElement} elements.preview - Preview element
 * @param {HTMLElement} elements.header - Collapsible header
 * @param {HTMLElement} elements.body - Collapsible body
 * @returns {Object} Command builder API
 */
export function createCommandBuilder(elements) {
  const { form, preview, header, body } = elements;

  const inputs = {
    cla: form.querySelector('#cmd-cla'),
    ins: form.querySelector('#cmd-ins'),
    p1: form.querySelector('#cmd-p1'),
    p2: form.querySelector('#cmd-p2'),
    le: form.querySelector('#cmd-le'),
    data: form.querySelector('#cmd-data'),
  };

  const templateButtons = form.querySelectorAll('[data-template]');
  let isOpen = state.get('ui.commandBuilderOpen') ?? true;

  /**
   * Gets current form values.
   * @returns {Object} Form values
   */
  function getValues() {
    return {
      cla: normalizeHex(inputs.cla.value) || '00',
      ins: normalizeHex(inputs.ins.value) || '00',
      p1: normalizeHex(inputs.p1.value) || '00',
      p2: normalizeHex(inputs.p2.value) || '00',
      le: inputs.le.value ? normalizeHex(inputs.le.value) : null,
      data: normalizeHex(inputs.data.value) || null,
    };
  }

  /**
   * Sets form values.
   * @param {Object} values - Form values
   */
  function setValues(values) {
    if (values.cla !== undefined) inputs.cla.value = values.cla;
    if (values.ins !== undefined) inputs.ins.value = values.ins;
    if (values.p1 !== undefined) inputs.p1.value = values.p1;
    if (values.p2 !== undefined) inputs.p2.value = values.p2;
    if (values.le !== undefined) inputs.le.value = values.le || '';
    if (values.data !== undefined) inputs.data.value = values.data || '';
    updatePreview();
  }

  /**
   * Updates the command preview.
   */
  function updatePreview() {
    const values = getValues();
    const apdu = buildCommand({
      cla: values.cla,
      ins: values.ins,
      p1: values.p1,
      p2: values.p2,
      data: values.data,
      le: values.le ? parseInt(values.le, 16) : undefined,
    });
    preview.textContent = formatHex(apdu);
  }

  /**
   * Validates a hex input.
   * @param {HTMLInputElement} input - Input element
   * @param {number} expectedLength - Expected byte length
   * @returns {boolean} Is valid
   */
  function validateInput(input, expectedLength = null) {
    const value = input.value.trim();

    if (!value && !input.required) {
      input.classList.remove('error');
      return true;
    }

    if (!isValidHex(value)) {
      input.classList.add('error');
      return false;
    }

    if (expectedLength !== null && normalizeHex(value).length !== expectedLength * 2) {
      input.classList.add('error');
      return false;
    }

    input.classList.remove('error');
    return true;
  }

  /**
   * Validates all inputs.
   * @returns {boolean} All valid
   */
  function validateAll() {
    const claValid = validateInput(inputs.cla, 1);
    const insValid = validateInput(inputs.ins, 1);
    const p1Valid = validateInput(inputs.p1, 1);
    const p2Valid = validateInput(inputs.p2, 1);
    const leValid = validateInput(inputs.le);
    const dataValid = validateInput(inputs.data);

    return claValid && insValid && p1Valid && p2Valid && leValid && dataValid;
  }

  /**
   * Applies a template.
   * @param {string} templateName - Template name
   */
  function applyTemplate(templateName) {
    const template = TEMPLATES[templateName];
    if (!template) return;

    setValues({
      cla: template.cla,
      ins: template.ins,
      p1: template.p1,
      p2: template.p2,
      le: template.le,
      data: template.data,
    });

    window.dispatchEvent(new CustomEvent('toast', {
      detail: { type: 'info', message: `Applied ${template.name} template` }
    }));
  }

  /**
   * Clears the form.
   */
  function clear() {
    form.reset();
    updatePreview();
  }

  /**
   * Submits the command.
   */
  function submit() {
    if (!validateAll()) {
      window.dispatchEvent(new CustomEvent('toast', {
        detail: { type: 'error', message: 'Invalid APDU format' }
      }));
      return;
    }

    const values = getValues();
    const apdu = buildCommand({
      cla: values.cla,
      ins: values.ins,
      p1: values.p1,
      p2: values.p2,
      data: values.data,
      le: values.le ? parseInt(values.le, 16) : undefined,
    });

    window.dispatchEvent(new CustomEvent('apdu-send', { detail: { apdu } }));
  }

  /**
   * Toggles the collapsed state.
   */
  function toggle() {
    if (!header || !body) return;

    isOpen = !isOpen;
    state.set('ui.commandBuilderOpen', isOpen);

    body.classList.toggle('command-builder__body--collapsed', !isOpen);
    header.setAttribute('aria-expanded', String(isOpen));

    const toggleIcon = header.querySelector('.command-builder__toggle');
    if (toggleIcon) {
      toggleIcon.classList.toggle('command-builder__toggle--open', isOpen);
    }
  }

  // Set up event listeners
  Object.values(inputs).forEach(input => {
    input.addEventListener('input', () => {
      validateInput(input);
      updatePreview();
    });

    // Auto-uppercase for hex inputs
    if (input.id !== 'cmd-data') {
      input.addEventListener('blur', () => {
        if (input.value) {
          input.value = input.value.toUpperCase();
        }
      });
    }
  });

  // Template buttons
  templateButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      applyTemplate(btn.dataset.template);
    });
  });

  // Form submission
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    submit();
  });

  form.addEventListener('reset', (e) => {
    setTimeout(updatePreview, 0);
  });

  // Collapsible header (only if header element exists)
  if (header) {
    header.addEventListener('click', toggle);
    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle();
      }
    });

    // Initialize state
    if (!isOpen) {
      body?.classList.add('command-builder__body--collapsed');
      header.setAttribute('aria-expanded', 'false');
    }
  }

  // Initial preview
  updatePreview();

  return {
    getValues,
    setValues,
    clear,
    submit,
    toggle,
    applyTemplate,
    validateAll,

    /**
     * Gets the built APDU command.
     * @returns {string} APDU hex string
     */
    getApdu() {
      const values = getValues();
      return buildCommand({
        cla: values.cla,
        ins: values.ins,
        p1: values.p1,
        p2: values.p2,
        data: values.data,
        le: values.le ? parseInt(values.le, 16) : undefined,
      });
    },

    /**
     * Gets available templates.
     * @returns {Object} Templates
     */
    getTemplates() {
      return { ...TEMPLATES };
    },

    /**
     * Checks if the builder is open.
     * @returns {boolean} Is open
     */
    isOpen() {
      return isOpen;
    },
  };
}
