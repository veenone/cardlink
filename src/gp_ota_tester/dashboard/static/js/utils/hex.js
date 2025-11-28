/**
 * Hex Utility Functions
 *
 * Functions for hex string manipulation and validation.
 */

/**
 * Validates a hex string.
 * @param {string} hex - Hex string to validate
 * @returns {boolean} True if valid hex string
 */
export function isValidHex(hex) {
  if (typeof hex !== 'string') return false;
  const cleaned = hex.replace(/\s+/g, '');
  return /^[0-9A-Fa-f]*$/.test(cleaned) && cleaned.length % 2 === 0;
}

/**
 * Normalizes a hex string (uppercase, no spaces).
 * @param {string} hex - Hex string to normalize
 * @returns {string} Normalized hex string
 */
export function normalizeHex(hex) {
  if (typeof hex !== 'string') return '';
  return hex.replace(/\s+/g, '').toUpperCase();
}

/**
 * Formats a hex string with spaces between bytes.
 * @param {string} hex - Hex string to format
 * @param {string} [separator=' '] - Separator between bytes
 * @returns {string} Formatted hex string
 */
export function formatHex(hex, separator = ' ') {
  const normalized = normalizeHex(hex);
  return normalized.match(/.{1,2}/g)?.join(separator) || '';
}

/**
 * Converts hex string to byte array.
 * @param {string} hex - Hex string
 * @returns {Uint8Array} Byte array
 */
export function hexToBytes(hex) {
  const normalized = normalizeHex(hex);
  const bytes = new Uint8Array(normalized.length / 2);
  for (let i = 0; i < normalized.length; i += 2) {
    bytes[i / 2] = parseInt(normalized.slice(i, i + 2), 16);
  }
  return bytes;
}

/**
 * Converts byte array to hex string.
 * @param {Uint8Array|number[]} bytes - Byte array
 * @returns {string} Hex string
 */
export function bytesToHex(bytes) {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0').toUpperCase())
    .join('');
}

/**
 * Converts hex string to ASCII string (printable chars only).
 * @param {string} hex - Hex string
 * @param {string} [placeholder='.'] - Placeholder for non-printable chars
 * @returns {string} ASCII representation
 */
export function hexToAscii(hex, placeholder = '.') {
  const bytes = hexToBytes(hex);
  return Array.from(bytes)
    .map(b => (b >= 0x20 && b <= 0x7e) ? String.fromCharCode(b) : placeholder)
    .join('');
}

/**
 * Converts ASCII string to hex string.
 * @param {string} ascii - ASCII string
 * @returns {string} Hex string
 */
export function asciiToHex(ascii) {
  return Array.from(ascii)
    .map(c => c.charCodeAt(0).toString(16).padStart(2, '0').toUpperCase())
    .join('');
}

/**
 * Calculates the length of hex data in bytes.
 * @param {string} hex - Hex string
 * @returns {number} Length in bytes
 */
export function hexLength(hex) {
  return normalizeHex(hex).length / 2;
}

/**
 * Pads a hex value to specified byte length.
 * @param {string|number} value - Value to pad
 * @param {number} bytes - Target byte length
 * @returns {string} Padded hex string
 */
export function padHex(value, bytes) {
  const hex = typeof value === 'number'
    ? value.toString(16).toUpperCase()
    : normalizeHex(String(value));
  return hex.padStart(bytes * 2, '0');
}

/**
 * XORs two hex strings.
 * @param {string} hex1 - First hex string
 * @param {string} hex2 - Second hex string
 * @returns {string} XOR result as hex string
 */
export function xorHex(hex1, hex2) {
  const bytes1 = hexToBytes(hex1);
  const bytes2 = hexToBytes(hex2);
  const length = Math.max(bytes1.length, bytes2.length);
  const result = new Uint8Array(length);

  for (let i = 0; i < length; i++) {
    result[i] = (bytes1[i] || 0) ^ (bytes2[i] || 0);
  }

  return bytesToHex(result);
}

/**
 * Extracts a substring from hex data.
 * @param {string} hex - Hex string
 * @param {number} offset - Byte offset
 * @param {number} [length] - Number of bytes (all remaining if omitted)
 * @returns {string} Extracted hex substring
 */
export function hexSubstring(hex, offset, length) {
  const normalized = normalizeHex(hex);
  const start = offset * 2;
  const end = length !== undefined ? start + length * 2 : undefined;
  return normalized.slice(start, end);
}

/**
 * Compares two hex strings for equality.
 * @param {string} hex1 - First hex string
 * @param {string} hex2 - Second hex string
 * @returns {boolean} True if equal
 */
export function hexEquals(hex1, hex2) {
  return normalizeHex(hex1) === normalizeHex(hex2);
}

/**
 * Creates a hex dump view of data.
 * @param {string} hex - Hex string
 * @param {number} [bytesPerLine=16] - Bytes per line
 * @returns {string} Formatted hex dump
 */
export function hexDump(hex, bytesPerLine = 16) {
  const bytes = hexToBytes(hex);
  const lines = [];

  for (let i = 0; i < bytes.length; i += bytesPerLine) {
    const offset = i.toString(16).padStart(8, '0').toUpperCase();
    const chunk = bytes.slice(i, i + bytesPerLine);

    // Hex portion
    const hexPart = Array.from(chunk)
      .map(b => b.toString(16).padStart(2, '0').toUpperCase())
      .join(' ')
      .padEnd(bytesPerLine * 3 - 1);

    // ASCII portion
    const asciiPart = Array.from(chunk)
      .map(b => (b >= 0x20 && b <= 0x7e) ? String.fromCharCode(b) : '.')
      .join('');

    lines.push(`${offset}  ${hexPart}  |${asciiPart}|`);
  }

  return lines.join('\n');
}

/**
 * Generates a random hex string.
 * @param {number} bytes - Number of bytes
 * @returns {string} Random hex string
 */
export function randomHex(bytes) {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return bytesToHex(array);
}
