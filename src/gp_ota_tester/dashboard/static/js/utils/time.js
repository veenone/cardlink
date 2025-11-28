/**
 * Time Utility Functions
 *
 * Functions for time formatting and manipulation.
 */

/**
 * Formats a timestamp for display.
 * @param {number|Date|string} timestamp - Timestamp to format
 * @param {Object} [options] - Formatting options
 * @param {boolean} [options.date=false] - Include date
 * @param {boolean} [options.ms=true] - Include milliseconds
 * @param {boolean} [options.hour12=false] - Use 12-hour format
 * @returns {string} Formatted time string
 */
export function formatTime(timestamp, options = {}) {
  const { date = false, ms = true, hour12 = false } = options;
  const d = timestamp instanceof Date ? timestamp : new Date(timestamp);

  if (isNaN(d.getTime())) {
    return '--:--:--';
  }

  const parts = [];

  if (date) {
    parts.push(d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }));
  }

  let time = d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12,
  });

  if (ms) {
    const milliseconds = d.getMilliseconds().toString().padStart(3, '0');
    time += `.${milliseconds}`;
  }

  parts.push(time);

  return parts.join(' ');
}

/**
 * Formats a timestamp in ISO format.
 * @param {number|Date|string} timestamp - Timestamp to format
 * @returns {string} ISO formatted string
 */
export function formatISO(timestamp) {
  const d = timestamp instanceof Date ? timestamp : new Date(timestamp);
  return d.toISOString();
}

/**
 * Formats a duration in human-readable format.
 * @param {number} ms - Duration in milliseconds
 * @param {boolean} [short=false] - Use short format
 * @returns {string} Formatted duration
 */
export function formatDuration(ms, short = false) {
  if (ms < 0) ms = 0;

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (short) {
    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    if (seconds > 0) return `${seconds}s`;
    return `${ms}ms`;
  }

  const parts = [];
  if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`);
  if (hours % 24 > 0) parts.push(`${hours % 24} hour${hours % 24 !== 1 ? 's' : ''}`);
  if (minutes % 60 > 0) parts.push(`${minutes % 60} minute${minutes % 60 !== 1 ? 's' : ''}`);
  if (seconds % 60 > 0) parts.push(`${seconds % 60} second${seconds % 60 !== 1 ? 's' : ''}`);

  if (parts.length === 0) {
    return `${ms} millisecond${ms !== 1 ? 's' : ''}`;
  }

  return parts.join(', ');
}

/**
 * Formats a relative time (e.g., "2 minutes ago").
 * @param {number|Date|string} timestamp - Timestamp to format
 * @returns {string} Relative time string
 */
export function formatRelative(timestamp) {
  const d = timestamp instanceof Date ? timestamp : new Date(timestamp);
  const now = Date.now();
  const diff = now - d.getTime();

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (diff < 0) {
    return 'in the future';
  }

  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds} seconds ago`;
  if (minutes === 1) return '1 minute ago';
  if (minutes < 60) return `${minutes} minutes ago`;
  if (hours === 1) return '1 hour ago';
  if (hours < 24) return `${hours} hours ago`;
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  if (weeks === 1) return '1 week ago';
  if (weeks < 4) return `${weeks} weeks ago`;
  if (months === 1) return '1 month ago';
  if (months < 12) return `${months} months ago`;
  if (years === 1) return '1 year ago';
  return `${years} years ago`;
}

/**
 * Gets the elapsed time since a timestamp.
 * @param {number|Date|string} start - Start timestamp
 * @param {number|Date|string} [end=Date.now()] - End timestamp
 * @returns {number} Elapsed time in milliseconds
 */
export function getElapsed(start, end = Date.now()) {
  const startTime = start instanceof Date ? start.getTime() : new Date(start).getTime();
  const endTime = end instanceof Date ? end.getTime() : new Date(end).getTime();
  return endTime - startTime;
}

/**
 * Creates a debounced function.
 * @param {Function} fn - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
export function debounce(fn, wait) {
  let timeout;
  return function debounced(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), wait);
  };
}

/**
 * Creates a throttled function.
 * @param {Function} fn - Function to throttle
 * @param {number} limit - Time limit in ms
 * @returns {Function} Throttled function
 */
export function throttle(fn, limit) {
  let inThrottle;
  return function throttled(...args) {
    if (!inThrottle) {
      fn.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Delays execution for specified duration.
 * @param {number} ms - Delay in milliseconds
 * @returns {Promise<void>} Promise that resolves after delay
 */
export function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Creates a stopwatch for timing operations.
 * @returns {Object} Stopwatch API
 */
export function createStopwatch() {
  let startTime = null;
  let elapsed = 0;
  let running = false;

  return {
    /**
     * Starts the stopwatch.
     */
    start() {
      if (!running) {
        startTime = Date.now() - elapsed;
        running = true;
      }
    },

    /**
     * Stops the stopwatch.
     */
    stop() {
      if (running) {
        elapsed = Date.now() - startTime;
        running = false;
      }
    },

    /**
     * Resets the stopwatch.
     */
    reset() {
      startTime = null;
      elapsed = 0;
      running = false;
    },

    /**
     * Gets elapsed time in milliseconds.
     * @returns {number} Elapsed time
     */
    getElapsed() {
      if (running) {
        return Date.now() - startTime;
      }
      return elapsed;
    },

    /**
     * Gets formatted elapsed time.
     * @param {boolean} [short=true] - Use short format
     * @returns {string} Formatted time
     */
    getFormatted(short = true) {
      return formatDuration(this.getElapsed(), short);
    },

    /**
     * Checks if stopwatch is running.
     * @returns {boolean} Running state
     */
    isRunning() {
      return running;
    },
  };
}

/**
 * Formats a timestamp for logging.
 * @param {number|Date|string} [timestamp=Date.now()] - Timestamp
 * @returns {string} Log-formatted timestamp
 */
export function logTimestamp(timestamp = Date.now()) {
  return formatTime(timestamp, { ms: true, hour12: false });
}

/**
 * Formats bytes in human-readable format.
 * @param {number} bytes - Number of bytes
 * @param {number} [decimals=1] - Decimal places
 * @returns {string} Formatted byte string (e.g., "1.5 KB")
 */
export function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return '0 B';
  if (bytes < 0) bytes = Math.abs(bytes);

  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const index = Math.min(i, units.length - 1);

  const value = bytes / Math.pow(k, index);

  // Use 0 decimals for bytes, configured decimals for larger units
  const precision = index === 0 ? 0 : decimals;
  return `${value.toFixed(precision)} ${units[index]}`;
}

/**
 * Formats a duration in compact format (e.g., "1.23s").
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Compact duration string
 */
export function formatDurationCompact(ms) {
  if (ms < 0) ms = 0;

  if (ms < 1000) {
    return `${ms}ms`;
  }

  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }

  const minutes = seconds / 60;
  if (minutes < 60) {
    return `${minutes.toFixed(1)}m`;
  }

  const hours = minutes / 60;
  if (hours < 24) {
    return `${hours.toFixed(1)}h`;
  }

  const days = hours / 24;
  return `${days.toFixed(1)}d`;
}

/**
 * Creates a span with relative time and full date tooltip.
 * @param {number|Date|string} timestamp - Timestamp to format
 * @returns {string} HTML string with title attribute
 */
export function formatRelativeWithTooltip(timestamp) {
  const d = timestamp instanceof Date ? timestamp : new Date(timestamp);
  const relative = formatRelative(timestamp);
  const full = formatTime(timestamp, { date: true, ms: true });
  return `<span class="timestamp" title="${full}">${relative}</span>`;
}

/**
 * Creates a span with compact duration and full value tooltip.
 * @param {number} ms - Duration in milliseconds
 * @returns {string} HTML string with title attribute
 */
export function formatDurationWithTooltip(ms) {
  const compact = formatDurationCompact(ms);
  const full = formatDuration(ms, false);
  return `<span class="duration" title="${full}">${compact}</span>`;
}

/**
 * Creates a span with formatted bytes and exact value tooltip.
 * @param {number} bytes - Number of bytes
 * @returns {string} HTML string with title attribute
 */
export function formatBytesWithTooltip(bytes) {
  const formatted = formatBytes(bytes);
  const exact = `${bytes.toLocaleString()} bytes`;
  return `<span class="byte-size" title="${exact}">${formatted}</span>`;
}
