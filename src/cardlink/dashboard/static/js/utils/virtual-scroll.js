/**
 * Virtual Scroller for GP OTA Tester Dashboard
 *
 * Efficient rendering of large lists using virtual scrolling.
 * Only renders visible items plus a buffer zone.
 */

/**
 * @typedef {Object} VirtualScrollerConfig
 * @property {HTMLElement} container - Scrollable container element
 * @property {HTMLElement} content - Content element to hold rendered items
 * @property {number} itemHeight - Fixed height of each item in pixels
 * @property {number} [bufferSize=5] - Number of items to render above/below viewport
 * @property {Function} renderItem - Function to render an item (index, data) => HTMLElement
 * @property {Function} [onScroll] - Callback on scroll
 */

/**
 * Creates a virtual scroller instance.
 * @param {VirtualScrollerConfig} config - Configuration
 * @returns {Object} Virtual scroller API
 */
export function createVirtualScroller(config) {
  const {
    container,
    content,
    itemHeight,
    bufferSize = 5,
    renderItem,
    onScroll,
  } = config;

  let items = [];
  let renderedRange = { start: 0, end: 0 };
  let scrollTop = 0;
  let containerHeight = 0;
  let rafId = null;
  let itemCache = new Map();

  /**
   * Calculates the visible range of items.
   * @returns {Object} Start and end indices
   */
  function calculateVisibleRange() {
    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - bufferSize);
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const end = Math.min(items.length, start + visibleCount + bufferSize * 2);
    return { start, end };
  }

  /**
   * Updates the content spacer height.
   */
  function updateSpacer() {
    const totalHeight = items.length * itemHeight;
    content.style.height = `${totalHeight}px`;
  }

  /**
   * Renders items in the visible range.
   */
  function renderVisibleItems() {
    const range = calculateVisibleRange();

    // Check if range changed
    if (range.start === renderedRange.start && range.end === renderedRange.end) {
      return;
    }

    // Clear items outside range
    const fragment = document.createDocumentFragment();
    const existingItems = new Set();

    // Keep items that are still in range
    for (let i = range.start; i < range.end; i++) {
      if (itemCache.has(i)) {
        existingItems.add(i);
      }
    }

    // Remove items no longer in range
    for (const [index, element] of itemCache) {
      if (!existingItems.has(index)) {
        element.remove();
        itemCache.delete(index);
      }
    }

    // Render new items
    for (let i = range.start; i < range.end; i++) {
      if (!itemCache.has(i)) {
        const element = renderItem(i, items[i]);
        element.style.position = 'absolute';
        element.style.top = `${i * itemHeight}px`;
        element.style.left = '0';
        element.style.right = '0';
        element.style.height = `${itemHeight}px`;
        element.dataset.index = i;
        fragment.appendChild(element);
        itemCache.set(i, element);
      }
    }

    if (fragment.children.length > 0) {
      content.appendChild(fragment);
    }

    renderedRange = range;
  }

  /**
   * Handles scroll events.
   */
  function handleScroll() {
    scrollTop = container.scrollTop;

    // Cancel any pending animation frame
    if (rafId) {
      cancelAnimationFrame(rafId);
    }

    // Schedule render on next animation frame
    rafId = requestAnimationFrame(() => {
      renderVisibleItems();
      if (onScroll) {
        onScroll({ scrollTop, range: renderedRange });
      }
    });
  }

  /**
   * Handles container resize.
   */
  function handleResize() {
    containerHeight = container.clientHeight;
    renderVisibleItems();
  }

  // Set up event listeners
  container.addEventListener('scroll', handleScroll, { passive: true });
  const resizeObserver = new ResizeObserver(handleResize);
  resizeObserver.observe(container);

  // Initial setup
  content.style.position = 'relative';
  containerHeight = container.clientHeight;

  return {
    /**
     * Sets the items to render.
     * @param {Array} newItems - Array of items
     */
    setItems(newItems) {
      items = newItems;
      itemCache.clear();
      content.innerHTML = '';
      updateSpacer();
      renderVisibleItems();
    },

    /**
     * Appends items to the list.
     * @param {Array} newItems - Items to append
     */
    appendItems(newItems) {
      items = [...items, ...newItems];
      updateSpacer();
      renderVisibleItems();
    },

    /**
     * Updates a specific item.
     * @param {number} index - Item index
     * @param {*} data - New item data
     */
    updateItem(index, data) {
      if (index < 0 || index >= items.length) return;

      items[index] = data;

      // Re-render if visible
      if (itemCache.has(index)) {
        const oldElement = itemCache.get(index);
        const newElement = renderItem(index, data);
        newElement.style.position = 'absolute';
        newElement.style.top = `${index * itemHeight}px`;
        newElement.style.left = '0';
        newElement.style.right = '0';
        newElement.style.height = `${itemHeight}px`;
        newElement.dataset.index = index;
        oldElement.replaceWith(newElement);
        itemCache.set(index, newElement);
      }
    },

    /**
     * Clears all items.
     */
    clear() {
      items = [];
      itemCache.clear();
      content.innerHTML = '';
      updateSpacer();
      renderedRange = { start: 0, end: 0 };
    },

    /**
     * Scrolls to a specific item.
     * @param {number} index - Item index
     * @param {string} [align='start'] - Alignment: 'start', 'center', 'end'
     */
    scrollToItem(index, align = 'start') {
      if (index < 0 || index >= items.length) return;

      let targetTop = index * itemHeight;

      switch (align) {
        case 'center':
          targetTop -= (containerHeight - itemHeight) / 2;
          break;
        case 'end':
          targetTop -= containerHeight - itemHeight;
          break;
      }

      container.scrollTop = Math.max(0, targetTop);
    },

    /**
     * Scrolls to the bottom of the list.
     */
    scrollToBottom() {
      container.scrollTop = container.scrollHeight;
    },

    /**
     * Gets the current scroll position.
     * @returns {number} Scroll top position
     */
    getScrollTop() {
      return scrollTop;
    },

    /**
     * Checks if scrolled to bottom.
     * @param {number} [threshold=50] - Threshold in pixels
     * @returns {boolean} True if at bottom
     */
    isAtBottom(threshold = 50) {
      return container.scrollHeight - container.scrollTop - containerHeight < threshold;
    },

    /**
     * Gets the total item count.
     * @returns {number} Item count
     */
    getItemCount() {
      return items.length;
    },

    /**
     * Gets an item by index.
     * @param {number} index - Item index
     * @returns {*} Item data
     */
    getItem(index) {
      return items[index];
    },

    /**
     * Gets all items.
     * @returns {Array} All items
     */
    getItems() {
      return items;
    },

    /**
     * Forces a re-render.
     */
    refresh() {
      itemCache.clear();
      content.innerHTML = '';
      updateSpacer();
      renderVisibleItems();
    },

    /**
     * Destroys the virtual scroller.
     */
    destroy() {
      container.removeEventListener('scroll', handleScroll);
      resizeObserver.disconnect();
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
      itemCache.clear();
      content.innerHTML = '';
    },

    /**
     * Gets the visible range.
     * @returns {Object} Start and end indices
     */
    getVisibleRange() {
      return { ...renderedRange };
    },
  };
}
