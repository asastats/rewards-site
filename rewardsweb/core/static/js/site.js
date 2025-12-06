/******************************************************************************
 *
 *  Toast Notifications & Django Messages
 *
 *****************************************************************************/

/**
 * Displays a toast notification using DaisyUI alert classes.
 * @param {'success' | 'error' | 'info' | 'warning'} type - The type of toast (determines the color).
 * @param {string} text - The message to display in the toast.
 */
function showToast(type, text) {
  const toastContainer = document.getElementById("toast-container");
  if (!toastContainer) return;

  const toast = document.createElement("div");
  toast.className = `alert alert-${type} shadow-lg`;

  const span = document.createElement("span");
  span.textContent = text;
  toast.appendChild(span);

  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

/**
 * Finds and displays Django messages as toast notifications upon page load.
 * The messages are embedded in the HTML with data attributes.
 */
function processDjangoMessages() {
  const messageContainer = document.getElementById("django-messages");
  if (messageContainer) {
    const messages = messageContainer.querySelectorAll("[data-message]");
    messages.forEach((element) => {
      const type = element.getAttribute("data-message-type") || "info";
      const text = element.getAttribute("data-message");
      showToast(type, text);
    });
    messageContainer.remove(); // Clean up the container after processing
  }
}

/******************************************************************************
 *
 *  Modal Management
 *
 *****************************************************************************/

/**
 * Closes any active modal by clearing the contents of the modal container.
 */
function closeModal() {
  const modalContainer = document.getElementById("modal-container");
  if (modalContainer) {
    modalContainer.innerHTML = "";
  }
}

/******************************************************************************
 *
 *  HTMX Progress Bar
 *
 *****************************************************************************/

var progressInterval = null;
var htmxState = { requestBlocking: false };

/**
 * Determines if an HTMX request should be "blocking," meaning it disables
 * pointer events during the request to prevent user interaction.
 * @param {HTMLElement} el - The element triggering the HTMX request.
 * @param {object} requestConfig - The configuration object for the request.
 * @returns {boolean} - True if the request should be blocking.
 */
function isBlockingRequest(el, requestConfig) {
  return (
    el?.getAttribute("hx-vals")?.includes('"blocking": "true"') ||
    el?.dataset.blocking === "true" ||
    requestConfig?.boosted === true // Boosted navigation links are blocking
  );
}

/**
 * Starts the HTMX progress bar animation.
 * @param {boolean} blocking - If true, disables pointer events on the body.
 */
function startProgressBar(blocking = false) {
  const bar = document.getElementById("htmx-progress-bar");
  if (!bar) return;

  bar.classList.remove("hidden");
  bar.style.width = "0%";

  if (blocking) {
    document.body.style.pointerEvents = "none";
  }

  let width = 0;
  progressInterval = setInterval(() => {
    width = Math.min(width + Math.random() * 15, 90);
    bar.style.width = `${width}%`;
  }, 200);
}

/**
 * Completes and hides the HTMX progress bar.
 * @param {boolean} blocking - If true, re-enables pointer events on the body.
 */
function finishProgressBar(blocking = false, callback) {
  const bar = document.getElementById("htmx-progress-bar");
  if (!bar) return;

  clearInterval(progressInterval);
  bar.style.width = "100%";

  if (blocking) {
    document.body.style.pointerEvents = "";
  }

  setTimeout(() => {
    bar.classList.add("hidden");
    bar.style.width = "0%";
    if (callback) {
      callback();
    }
  }, 300);
}

/******************************************************************************
 *
 *  UI Initializers & Event Handlers
 *
 *****************************************************************************/

/**
 * Sets up the toggle functionality for the active network buttons.
 */
function processActiveNetwork() {
  const networkContainer = document.getElementById("active-network");
  if (!networkContainer) return;

  const [button1, button2] =
    networkContainer.querySelectorAll("button[data-network]");

  networkContainer.addEventListener("click", function (e) {
    const clicked = e.target.closest("button[data-network]");
    if (!clicked) return;

    const other = clicked === button1 ? button2 : button1;

    clicked.disabled = true;
    clicked.classList.add("btn-disabled");

    other.disabled = false;
    other.classList.remove("btn-disabled");
  });
}

/**
 * Manages DaisyUI theme persistence in localStorage.
 * It loads the saved theme on init and saves the theme on change.
 */
function processDaisyUITheme() {
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    const selected = document.querySelector(
      `input[name='theme-dropdown'][value='${savedTheme}']`
    );
    if (selected) selected.checked = true;
  }

  document.querySelectorAll("input[name='theme-dropdown']").forEach((input) => {
    if (input.dataset.listener !== "true") {
      input.dataset.listener = "true";
      input.addEventListener("change", () => {
        const theme = input.value;
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
      });
    }
  });
}

/**
 * Sets up the copy to clipboard functionality for the transparency report.
 */
function processClipboardCopy() {
  const copyBtn = document.getElementById('copy-report-btn');
  if (!copyBtn) return;

  copyBtn.addEventListener('click', () => {
    const reportTextarea = document.getElementById('report-textarea');
    if (reportTextarea && navigator.clipboard) {
      navigator.clipboard.writeText(reportTextarea.value);
      const originalText = copyBtn.innerHTML;
      copyBtn.innerHTML = '<i class="fas fa-check mr-2"></i> Copied!';
      setTimeout(() => {
        copyBtn.innerHTML = originalText;
      }, 2000);
    }
  });
}

/**
 * Sets up the toggle functionality for the transparency report form.
 */

function processTransparencyReportForm() {
  const reportTypeRadios = document.querySelectorAll('input[name="report_type"]');
  if (!reportTypeRadios.length) return;

  const monthlyFields = document.getElementById('monthly-fields');
  const quarterlyFields = document.getElementById('quarterly-fields');
  const yearlyFields = document.getElementById('yearly-fields');
  const customFields = document.getElementById('custom-fields');

  function toggleFields() {
    const selectedValue = document.querySelector('input[name="report_type"]:checked').value;
    monthlyFields.classList.toggle('hidden', selectedValue !== 'monthly');
    quarterlyFields.classList.toggle('hidden', selectedValue !== 'quarterly');
    yearlyFields.classList.toggle('hidden', selectedValue !== 'yearly');
    customFields.classList.toggle('hidden', selectedValue !== 'custom');
  }

  reportTypeRadios.forEach(radio => radio.addEventListener('change', toggleFields));
  toggleFields();
}

/******************************************************************************
 *
 *  Global Event Listeners
 *
 *****************************************************************************/

/**
 * Initializes UI components when the DOM is fully loaded.
 */
/* istanbul ignore next */
function initializeDomReadyListeners() {
  processActiveNetwork();
  processDaisyUITheme();
  processDjangoMessages();
}

/**
 * Initializes UI components when the DOM is fully loaded.
 */
document.addEventListener("DOMContentLoaded", initializeDomReadyListeners);

/**
 * HTMX listener: Fired before a request is sent.
 * Starts the progress bar.
 */
document.body.addEventListener("htmx:configRequest", (event) => {
  htmxState.requestBlocking = isBlockingRequest(
    event.detail.elt,
    event.detail.requestConfig
  );
  startProgressBar(htmxState.requestBlocking);

  const btn = document.getElementById('generate-report-btn');
  if (btn && event.detail.elt === btn.form) {
    btn.disabled = true;
  }
});

/**
 * HTMX listener: Fired after new content is swapped into the DOM.
 * Handles post-swap UI updates like animations, focus, toasts, and modals.
 */
document.body.addEventListener("htmx:afterSwap", (event) => {
  finishProgressBar(htmxState.requestBlocking);

  const generateReportBtn = document.getElementById('generate-report-btn');
  if (generateReportBtn) {
    generateReportBtn.disabled = false;
  }

  const swappedEl = event.detail.target;

  // Fade-in animation for the new content
  swappedEl.classList.add("fade-in");
  setTimeout(() => swappedEl.classList.remove("fade-in"), 300);

  // Autofocus on the first input in the new content
  const firstInput = swappedEl.querySelector(
    "input:not([type=hidden]), textarea, select"
  );
  if (firstInput) setTimeout(() => firstInput.focus(), 30);

  // Show toast notifications if specified in the response
  if (swappedEl.dataset.toastMessage) {
    showToast(
      swappedEl.dataset.toastType || "success",
      swappedEl.dataset.toastMessage
    );
  }

  // Auto-open any dialogs in the swapped content
  const dialogs = swappedEl.querySelectorAll("dialog");
  dialogs.forEach((dialog) => {
    /* istanbul ignore next */
    if (!dialog.open) dialog.showModal();
  });
  if (swappedEl.tagName === "DIALOG" && !swappedEl.open) {
    swappedEl.showModal();
  }

  // Re-apply theme logic if theme-related elements were swapped
  processDaisyUITheme();
});


/**
 * 
 * 
 */
document.body.addEventListener('htmx:load', function () {
  const transparencyContainer = document.getElementById('transparency-report-container');
  if (transparencyContainer) {
    processTransparencyReportForm();
    processClipboardCopy();
  }
});


/**
 * HTMX listener: Fired on a request error.
 * Ensures the progress bar and blocking state are always reset.
 */
document.body.addEventListener("htmx:error", () => {
  finishProgressBar(htmxState.requestBlocking);
});

/******************************************************************************
 *
 *  Module Exports (for testing)
 *
 *****************************************************************************/

/* istanbul ignore next */
if (typeof exports !== "undefined") {
  module.exports = {
    showToast,
    processDjangoMessages,
    closeModal,
    isBlockingRequest,
    startProgressBar,
    finishProgressBar,
    processActiveNetwork,
    processDaisyUITheme,
    processTransparencyReportForm,
    processClipboardCopy,
    htmxState,
    initializeDomReadyListeners,
  };
}
