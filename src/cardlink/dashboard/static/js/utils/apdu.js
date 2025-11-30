/**
 * APDU Utility Functions
 *
 * Functions for parsing and formatting ISO 7816 APDU commands and responses.
 */

import { normalizeHex, hexLength, hexSubstring, formatHex, padHex } from './hex.js';

/**
 * Common APDU instruction codes.
 */
export const INSTRUCTIONS = {
  '04': 'DEACTIVATE FILE',
  '0E': 'ERASE BINARY',
  '10': 'TERMINAL PROFILE',
  '12': 'FETCH',
  '14': 'TERMINAL RESPONSE',
  '20': 'VERIFY',
  '22': 'MANAGE SECURITY ENVIRONMENT',
  '24': 'CHANGE REFERENCE DATA',
  '26': 'DISABLE VERIFICATION REQUIREMENT',
  '28': 'ENABLE VERIFICATION REQUIREMENT',
  '2A': 'PERFORM SECURITY OPERATION',
  '2C': 'RESET RETRY COUNTER',
  '44': 'ACTIVATE FILE',
  '46': 'GENERATE ASYMMETRIC KEY PAIR',
  '70': 'MANAGE CHANNEL',
  '82': 'EXTERNAL AUTHENTICATE',
  '84': 'GET CHALLENGE',
  '86': 'GENERAL AUTHENTICATE',
  '88': 'INTERNAL AUTHENTICATE',
  'A0': 'SEARCH BINARY',
  'A2': 'SEARCH RECORD',
  'A4': 'SELECT',
  'B0': 'READ BINARY',
  'B2': 'READ RECORD',
  'C0': 'GET RESPONSE',
  'C2': 'ENVELOPE',
  'CA': 'GET DATA',
  'CB': 'GET DATA (odd INS)',
  'D0': 'WRITE BINARY',
  'D2': 'WRITE RECORD',
  'D6': 'UPDATE BINARY',
  'DA': 'PUT DATA',
  'DB': 'PUT DATA (odd INS)',
  'DC': 'UPDATE RECORD',
  'E0': 'CREATE FILE',
  'E2': 'APPEND RECORD',
  'E4': 'DELETE FILE',
  'E6': 'TERMINATE DF',
  'E8': 'TERMINATE EF',
  'F0': 'STORE DATA',
  'F2': 'GET STATUS',
  'FE': 'TERMINATE CARD USAGE',
  // GlobalPlatform specific
  '80': 'INITIALIZE UPDATE',
  '82': 'EXTERNAL AUTHENTICATE (GP)',
  '84': 'GET CHALLENGE (GP)',
  'E4': 'DELETE (GP)',
  'E6': 'INSTALL (GP)',
  'E8': 'LOAD (GP)',
  'F0': 'SET STATUS (GP)',
};

/**
 * Status word categories and meanings.
 */
export const STATUS_WORDS = {
  // Success
  '9000': { category: 'success', meaning: 'Success' },
  '9100': { category: 'success', meaning: 'Success (proactive command pending)' },

  // Warning conditions
  '6200': { category: 'warning', meaning: 'No information given (NV-RAM unchanged)' },
  '6281': { category: 'warning', meaning: 'Part of returned data may be corrupted' },
  '6282': { category: 'warning', meaning: 'End of file/record reached before reading Le bytes' },
  '6283': { category: 'warning', meaning: 'Selected file invalidated' },
  '6284': { category: 'warning', meaning: 'FCI not formatted according to ISO 7816-4' },
  '6300': { category: 'warning', meaning: 'No information given (NV-RAM changed)' },
  '6381': { category: 'warning', meaning: 'File filled up by last write' },

  // Execution errors
  '6400': { category: 'error', meaning: 'Execution error' },
  '6401': { category: 'error', meaning: 'Immediate response required by proactive command' },
  '6581': { category: 'error', meaning: 'Memory failure' },

  // Checking errors
  '6700': { category: 'error', meaning: 'Wrong length' },
  '6800': { category: 'error', meaning: 'Function in CLA not supported' },
  '6881': { category: 'error', meaning: 'Logical channel not supported' },
  '6882': { category: 'error', meaning: 'Secure messaging not supported' },
  '6883': { category: 'error', meaning: 'Last command of chain expected' },
  '6884': { category: 'error', meaning: 'Command chaining not supported' },
  '6900': { category: 'error', meaning: 'Command not allowed' },
  '6981': { category: 'error', meaning: 'Command incompatible with file structure' },
  '6982': { category: 'error', meaning: 'Security status not satisfied' },
  '6983': { category: 'error', meaning: 'Authentication method blocked' },
  '6984': { category: 'error', meaning: 'Reference data invalidated' },
  '6985': { category: 'error', meaning: 'Conditions of use not satisfied' },
  '6986': { category: 'error', meaning: 'Command not allowed (no current EF)' },
  '6987': { category: 'error', meaning: 'Expected SM data objects missing' },
  '6988': { category: 'error', meaning: 'SM data objects incorrect' },
  '6A00': { category: 'error', meaning: 'Wrong parameter(s) P1-P2' },
  '6A80': { category: 'error', meaning: 'Incorrect parameters in command data field' },
  '6A81': { category: 'error', meaning: 'Function not supported' },
  '6A82': { category: 'error', meaning: 'File or application not found' },
  '6A83': { category: 'error', meaning: 'Record not found' },
  '6A84': { category: 'error', meaning: 'Not enough memory space in file' },
  '6A85': { category: 'error', meaning: 'Lc inconsistent with TLV structure' },
  '6A86': { category: 'error', meaning: 'Incorrect parameters P1-P2' },
  '6A87': { category: 'error', meaning: 'Lc inconsistent with P1-P2' },
  '6A88': { category: 'error', meaning: 'Referenced data not found' },
  '6A89': { category: 'error', meaning: 'File already exists' },
  '6A8A': { category: 'error', meaning: 'DF name already exists' },
  '6B00': { category: 'error', meaning: 'Wrong parameter(s) P1-P2' },
  '6C00': { category: 'error', meaning: 'Wrong Le field' },
  '6D00': { category: 'error', meaning: 'Instruction code not supported or invalid' },
  '6E00': { category: 'error', meaning: 'Class not supported' },
  '6F00': { category: 'error', meaning: 'No precise diagnosis' },
};

/**
 * Parses an APDU command.
 * @param {string} hex - Command APDU hex string
 * @returns {Object} Parsed command
 */
export function parseCommand(hex) {
  const data = normalizeHex(hex);
  const length = hexLength(data);

  if (length < 4) {
    return { valid: false, error: 'Command too short (min 4 bytes)' };
  }

  const cla = hexSubstring(data, 0, 1);
  const ins = hexSubstring(data, 1, 1);
  const p1 = hexSubstring(data, 2, 1);
  const p2 = hexSubstring(data, 3, 1);

  const result = {
    valid: true,
    cla,
    ins,
    p1,
    p2,
    insName: getInstructionName(ins, cla),
    channel: getLogicalChannel(cla),
    secureMessaging: getSecureMessaging(cla),
    commandChaining: (parseInt(cla, 16) & 0x10) !== 0,
    lc: null,
    data: null,
    le: null,
    extended: false,
  };

  if (length === 4) {
    // Case 1: No data, no Le
    return result;
  }

  const byte5 = parseInt(hexSubstring(data, 4, 1), 16);

  if (length === 5) {
    // Case 2: No data, Le present
    result.le = byte5 === 0 ? 256 : byte5;
    return result;
  }

  // Check for extended APDU (byte5 = 0 and more data follows)
  if (byte5 === 0 && length > 7) {
    result.extended = true;
    result.lc = parseInt(hexSubstring(data, 5, 2), 16);
    result.data = hexSubstring(data, 7, result.lc);

    const remaining = length - 7 - result.lc;
    if (remaining === 2) {
      result.le = parseInt(hexSubstring(data, 7 + result.lc, 2), 16);
      if (result.le === 0) result.le = 65536;
    } else if (remaining === 3 && hexSubstring(data, 7 + result.lc, 1) === '00') {
      result.le = parseInt(hexSubstring(data, 7 + result.lc + 1, 2), 16);
      if (result.le === 0) result.le = 65536;
    }
  } else {
    // Standard APDU
    result.lc = byte5;
    if (length < 5 + result.lc) {
      return { valid: false, error: 'Data length mismatch' };
    }
    result.data = hexSubstring(data, 5, result.lc);

    const remaining = length - 5 - result.lc;
    if (remaining === 1) {
      const le = parseInt(hexSubstring(data, 5 + result.lc, 1), 16);
      result.le = le === 0 ? 256 : le;
    }
  }

  return result;
}

/**
 * Parses an APDU response.
 * @param {string} hex - Response APDU hex string
 * @returns {Object} Parsed response
 */
export function parseResponse(hex) {
  const data = normalizeHex(hex);
  const length = hexLength(data);

  if (length < 2) {
    return { valid: false, error: 'Response too short (min 2 bytes)' };
  }

  const sw = hexSubstring(data, length - 2, 2);
  const sw1 = hexSubstring(data, length - 2, 1);
  const sw2 = hexSubstring(data, length - 1, 1);
  const responseData = length > 2 ? hexSubstring(data, 0, length - 2) : null;

  const swInfo = getStatusWordInfo(sw);

  return {
    valid: true,
    sw,
    sw1,
    sw2,
    data: responseData,
    dataLength: responseData ? hexLength(responseData) : 0,
    category: swInfo.category,
    meaning: swInfo.meaning,
    moreData: sw1 === '61',
    wrongLength: sw1 === '6C',
    expectedLength: sw1 === '61' || sw1 === '6C' ? parseInt(sw2, 16) : null,
  };
}

/**
 * Gets the instruction name.
 * @param {string} ins - Instruction byte
 * @param {string} [cla] - Class byte (for context)
 * @returns {string} Instruction name or 'Unknown'
 */
export function getInstructionName(ins, cla) {
  const insUpper = normalizeHex(ins);
  return INSTRUCTIONS[insUpper] || 'Unknown';
}

/**
 * Gets the logical channel from CLA.
 * @param {string} cla - Class byte
 * @returns {number} Logical channel number
 */
export function getLogicalChannel(cla) {
  const claByte = parseInt(normalizeHex(cla), 16);
  if ((claByte & 0x40) === 0) {
    // ISO 7816-4 format
    return claByte & 0x03;
  } else {
    // Extended channel format
    return (claByte & 0x0F) + 4;
  }
}

/**
 * Gets secure messaging info from CLA.
 * @param {string} cla - Class byte
 * @returns {string} Secure messaging type
 */
export function getSecureMessaging(cla) {
  const claByte = parseInt(normalizeHex(cla), 16);
  const sm = (claByte >> 2) & 0x03;

  switch (sm) {
    case 0: return 'none';
    case 1: return 'proprietary';
    case 2: return 'command-header-auth';
    case 3: return 'command-header-auth-response';
    default: return 'unknown';
  }
}

/**
 * Gets status word information.
 * @param {string} sw - Status word (2 bytes)
 * @returns {Object} Status word info
 */
export function getStatusWordInfo(sw) {
  const swUpper = normalizeHex(sw);

  // Exact match
  if (STATUS_WORDS[swUpper]) {
    return STATUS_WORDS[swUpper];
  }

  // Pattern matching for variable SW2
  const sw1 = swUpper.slice(0, 2);
  const sw2 = parseInt(swUpper.slice(2, 4), 16);

  // 61XX - More data available
  if (sw1 === '61') {
    return {
      category: 'success',
      meaning: `${sw2} more bytes available`,
    };
  }

  // 6CXX - Wrong Le
  if (sw1 === '6C') {
    return {
      category: 'error',
      meaning: `Wrong Le, exact length is ${sw2}`,
    };
  }

  // 63CX - Counter
  if (sw1 === '63' && (sw2 & 0xF0) === 0xC0) {
    return {
      category: 'warning',
      meaning: `Counter: ${sw2 & 0x0F} retries remaining`,
    };
  }

  // 9XXX - Application specific
  if (sw1[0] === '9' && sw1 !== '90') {
    return {
      category: 'success',
      meaning: `Application specific success (${swUpper})`,
    };
  }

  // Generic fallback
  const genericKey = sw1 + '00';
  if (STATUS_WORDS[genericKey]) {
    return STATUS_WORDS[genericKey];
  }

  return { category: 'unknown', meaning: `Unknown status (${swUpper})` };
}

/**
 * Builds an APDU command.
 * @param {Object} params - Command parameters
 * @param {string} params.cla - Class byte
 * @param {string} params.ins - Instruction byte
 * @param {string} params.p1 - Parameter 1
 * @param {string} params.p2 - Parameter 2
 * @param {string} [params.data] - Command data
 * @param {number} [params.le] - Expected response length
 * @returns {string} APDU hex string
 */
export function buildCommand({ cla, ins, p1, p2, data, le }) {
  let apdu = padHex(cla, 1) + padHex(ins, 1) + padHex(p1, 1) + padHex(p2, 1);

  if (data) {
    const dataHex = normalizeHex(data);
    const lc = hexLength(dataHex);
    apdu += padHex(lc, 1) + dataHex;
  }

  if (le !== undefined && le !== null) {
    apdu += padHex(le === 256 ? 0 : le, 1);
  }

  return apdu;
}

/**
 * Categorizes a status word.
 * @param {string} sw - Status word
 * @returns {'success'|'warning'|'error'|'unknown'} Category
 */
export function categorizeStatus(sw) {
  const info = getStatusWordInfo(sw);
  return info.category;
}

/**
 * Checks if status word indicates success.
 * @param {string} sw - Status word
 * @returns {boolean} True if success
 */
export function isSuccess(sw) {
  const category = categorizeStatus(sw);
  return category === 'success';
}

/**
 * Formats an APDU for display.
 * @param {string} hex - APDU hex string
 * @param {Object} [options] - Formatting options
 * @returns {string} Formatted APDU
 */
export function formatApdu(hex, options = {}) {
  const { colorize = false, separator = ' ' } = options;
  return formatHex(hex, separator);
}
