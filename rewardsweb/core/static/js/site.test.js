const {
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
  processAllMessages,
} = require("./site.js");

// JSDOM doesn't implement showModal, so we'll mock it.
HTMLDialogElement.prototype.showModal = jest.fn();
HTMLDialogElement.prototype.close = jest.fn();

describe("Toast and Message Functions", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="toast-container"></div>';
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("showToast should create and append a toast notification", () => {
    showToast("success", "Test message");
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(1);
    const toast = toastContainer.children[0];
    expect(toast.classList.contains("alert-success")).toBe(true);
    expect(toast.textContent).toBe("Test message");

    // Fast-forward time to check if the toast is removed
    jest.advanceTimersByTime(5000);
    expect(toastContainer.children.length).toBe(0);
  });

  it("showToast should handle different types", () => {
    showToast("error", "Error message");
    let toast = document.querySelector(".alert");
    expect(toast.classList.contains("alert-error")).toBe(true);
    toast.remove();

    showToast("info", "Info message");
    toast = document.querySelector(".alert");
    expect(toast.classList.contains("alert-info")).toBe(true);
    toast.remove();

    showToast("warning", "Warning message");
    toast = document.querySelector(".alert");
    expect(toast.classList.contains("alert-warning")).toBe(true);
  });

  it("showToast should not fail if container is not found", () => {
    document.body.innerHTML = ""; // No toast container
    expect(() => showToast("success", "test")).not.toThrow();
  });

  it("processDjangoMessages should show toasts and remove the container", () => {
    document.body.innerHTML += `
      <div id="django-messages">
        <div data-message="Message 1" data-message-type="success"></div>
        <div data-message="Message 2" data-message-type="error"></div>
        <div data-message="Message 3"></div>
      </div>
    `;
    processDjangoMessages();
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(3);
    expect(toastContainer.children[2].classList.contains("alert-info")).toBe(
      true
    );
    expect(document.getElementById("django-messages")).toBeNull();
  });

  it("processDjangoMessages should not fail if container is not found", () => {
    expect(() => processDjangoMessages()).not.toThrow();
  });
});

describe("Modal Functions", () => {
  it("closeModal should clear the modal container", () => {
    document.body.innerHTML = '<div id="modal-container">Some content</div>';
    closeModal();
    const modalContainer = document.getElementById("modal-container");
    expect(modalContainer.innerHTML).toBe("");
  });

  it("closeModal should not fail if container is not found", () => {
    document.body.innerHTML = "";
    expect(() => closeModal()).not.toThrow();
  });
});

describe("HTMX Progress Bar Functions", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="htmx-progress-bar" class="hidden"></div>';
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("isBlockingRequest should detect blocking conditions", () => {
    const elWithHxVals = document.createElement("div");
    elWithHxVals.setAttribute("hx-vals", '{"blocking": "true"}');
    expect(isBlockingRequest(elWithHxVals, {})).toBe(true);

    const elWithDataset = document.createElement("div");
    elWithDataset.dataset.blocking = "true";
    expect(isBlockingRequest(elWithDataset, {})).toBe(true);

    const elBoosted = document.createElement("div");
    expect(isBlockingRequest(elBoosted, { boosted: true })).toBe(true);

    const nonBlockingEl = document.createElement("div");
    expect(isBlockingRequest(nonBlockingEl, {})).toBe(false);

    expect(isBlockingRequest(null, {})).toBe(false);
  });

  it("startProgressBar should not fail if bar is not found", () => {
    document.body.innerHTML = "";
    expect(() => startProgressBar()).not.toThrow();
  });

  it("startProgressBar should show the bar and start the interval", () => {
    startProgressBar();
    const bar = document.getElementById("htmx-progress-bar");
    expect(bar.classList.contains("hidden")).toBe(false);
    expect(bar.style.width).toBe("0%");

    jest.advanceTimersByTime(250);
    expect(parseFloat(bar.style.width)).toBeGreaterThan(0);
  });

  it("startProgressBar with blocking should disable pointer events", () => {
    startProgressBar(true);
    expect(document.body.style.pointerEvents).toBe("none");
  });

  it("finishProgressBar should not fail if bar is not found", () => {
    document.body.innerHTML = "";
    expect(() => finishProgressBar()).not.toThrow();
  });

  it("finishProgressBar should complete and hide the bar", async () => {
    startProgressBar();
    const bar = document.getElementById("htmx-progress-bar");
    const promise = finishProgressBar();
    jest.advanceTimersByTime(300);
    await promise;

    expect(bar.style.width).toBe("0%");
    expect(bar.classList.contains("hidden")).toBe(true);
  });

  it("finishProgressBar with blocking should re-enable pointer events", () => {
    document.body.style.pointerEvents = "none";
    finishProgressBar(true);
    expect(document.body.style.pointerEvents).toBe("");
  });

  it("finishProgressBar should execute a callback", (done) => {
    const callback = jest.fn(() => {
      done();
    });
    finishProgressBar(false, callback);
    jest.advanceTimersByTime(300);
    expect(callback).toHaveBeenCalled();
  });
});

describe("UI Initializers", () => {
  it("processActiveNetwork should toggle button states on click", () => {
    document.body.innerHTML = `
      <div id="active-network">
        <button data-network="mainnet">Mainnet</button>
        <button data-network="testnet" disabled class="btn-disabled">Testnet</button>
      </div>
    `;
    processActiveNetwork();
    const mainnetButton = document.querySelector('[data-network="mainnet"]');
    const testnetButton = document.querySelector('[data-network="testnet"]');

    mainnetButton.click();

    expect(mainnetButton.disabled).toBe(true);
    expect(mainnetButton.classList.contains("btn-disabled")).toBe(true);
    expect(testnetButton.disabled).toBe(false);
    expect(testnetButton.classList.contains("btn-disabled")).toBe(false);

    // Click the other button to test the reverse
    testnetButton.click();

    expect(testnetButton.disabled).toBe(true);
    expect(testnetButton.classList.contains("btn-disabled")).toBe(true);
    expect(mainnetButton.disabled).toBe(false);
    expect(mainnetButton.classList.contains("btn-disabled")).toBe(false);

    // Click a non-button element
    const container = document.getElementById("active-network");
    container.click();
    expect(testnetButton.disabled).toBe(true); // State should not change
  });

  it("processActiveNetwork should not fail if container is not found", () => {
    document.body.innerHTML = "";
    expect(() => processActiveNetwork()).not.toThrow();
  });

  it("processDaisyUITheme should not fail if saved theme element is not found", () => {
    localStorage.setItem("theme", "nonexistent");
    document.body.innerHTML = `
      <input type="radio" name="theme-dropdown" value="light">
    `;
    expect(() => processDaisyUITheme()).not.toThrow();
  });

  it("processDaisyUITheme should load theme from localStorage", () => {
    localStorage.setItem("theme", "dark");
    document.body.innerHTML = `
      <input type="radio" name="theme-dropdown" value="light">
      <input type="radio" name="theme-dropdown" value="dark">
    `;
    processDaisyUITheme();
    const darkThemeInput = document.querySelector('[value="dark"]');
    expect(darkThemeInput.checked).toBe(true);
  });

  it("processDaisyUITheme should handle no theme in localStorage", () => {
    localStorage.removeItem("theme");
    document.body.innerHTML = `
      <input type="radio" name="theme-dropdown" value="light" checked>
      <input type="radio" name="theme-dropdown" value="dark">
    `;
    processDaisyUITheme();
    const lightThemeInput = document.querySelector('[value="light"]');
    expect(lightThemeInput.checked).toBe(true); // Stays at default
  });

  it("processDaisyUITheme should save theme to localStorage on change", () => {
    document.body.innerHTML = `
      <input type="radio" name="theme-dropdown" value="light" checked>
      <input type="radio" name="theme-dropdown" value="dark">
    `;
    processDaisyUITheme();
    const darkThemeInput = document.querySelector('[value="dark"]');
    darkThemeInput.click(); // Simulate user clicking the theme
    darkThemeInput.dispatchEvent(new Event("change")); // Dispatch change event

    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("processDaisyUITheme should not add listeners twice", () => {
    document.body.innerHTML = `
      <input type="radio" name="theme-dropdown" value="light">
    `;
    const input = document.querySelector("input");
    const addEventListenerSpy = jest.spyOn(input, "addEventListener");

    processDaisyUITheme();
    processDaisyUITheme(); // Call a second time

    expect(addEventListenerSpy).toHaveBeenCalledTimes(1);
  });
});

describe("processTransparencyReportForm", () => {
  beforeEach(() => {
    document.body.innerHTML = `
            <input type="radio" name="report_type" value="monthly" checked>
            <input type="radio" name="report_type" value="quarterly">
            <input type="radio" name="report_type" value="yearly">
            <input type="radio" name="report_type" value="custom">
            <div id="monthly-fields"></div>
            <div id="quarterly-fields" class="hidden"></div>
            <div id="yearly-fields" class="hidden"></div>
            <div id="custom-fields" class="hidden"></div>
        `;
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it("should not throw if form elements are not present", () => {
    document.body.innerHTML = '';
    expect(() => processTransparencyReportForm()).not.toThrow();
  });

  it("should show monthly fields and hide others by default", () => {
    processTransparencyReportForm();
    expect(document.getElementById('monthly-fields').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('quarterly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('yearly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('custom-fields').classList.contains('hidden')).toBe(true);
  });

  it("should show quarterly fields when quarterly is selected", () => {
    const quarterlyRadio = document.querySelector('input[value="quarterly"]');
    quarterlyRadio.checked = true;
    processTransparencyReportForm();
    quarterlyRadio.dispatchEvent(new Event('change'));

    expect(document.getElementById('monthly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('quarterly-fields').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('yearly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('custom-fields').classList.contains('hidden')).toBe(true);
  });

  it("should show yearly fields when yearly is selected", () => {
    const yearlyRadio = document.querySelector('input[value="yearly"]');
    yearlyRadio.checked = true;
    processTransparencyReportForm();
    yearlyRadio.dispatchEvent(new Event('change'));

    expect(document.getElementById('monthly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('quarterly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('yearly-fields').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('custom-fields').classList.contains('hidden')).toBe(true);
  });

  it("should show custom fields when custom is selected", () => {
    const customRadio = document.querySelector('input[value="custom"]');
    customRadio.checked = true;
    processTransparencyReportForm();
    customRadio.dispatchEvent(new Event('change'));

    expect(document.getElementById('monthly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('quarterly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('yearly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('custom-fields').classList.contains('hidden')).toBe(false);
  });
});

describe("processClipboardCopy", () => {
  beforeEach(() => {
    document.body.innerHTML = `
            <button id="copy-report-btn">Copy</button>
            <textarea id="report-textarea">Test content</textarea>
        `;
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(),
      },
    });
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    document.body.innerHTML = '';
  });

  it("should not throw if button is not present", () => {
    document.body.innerHTML = '';
    expect(() => processClipboardCopy()).not.toThrow();
  });

  it("should copy text to clipboard on button click", () => {
    processClipboardCopy();
    const copyBtn = document.getElementById('copy-report-btn');
    copyBtn.click();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Test content");
  });

  it("should provide user feedback on successful copy", () => {
    processClipboardCopy();
    const copyBtn = document.getElementById('copy-report-btn');
    copyBtn.click();
    expect(copyBtn.innerHTML).toContain('Copied!');
    jest.advanceTimersByTime(2500);
    expect(copyBtn.innerHTML).toBe('Copy');
  });

  it("should not fail if textarea or clipboard is not available", () => {
    document.getElementById('report-textarea').remove();
    processClipboardCopy();
    const copyBtn = document.getElementById('copy-report-btn');
    expect(() => copyBtn.click()).not.toThrow();
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });
});

describe("Global Event Listeners", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="htmx-progress-bar" class="hidden"></div>
      <div id="toast-container"></div>
      <div id="modal-container"></div>
    `;
    jest.useFakeTimers();
    jest.spyOn(global, "setTimeout");
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("DOMContentLoaded should initialize UI components", () => {
    jest.mock("./site.js", () => ({
      processActiveNetwork: jest.fn(),
      processDaisyUITheme: jest.fn(),
      processDjangoMessages: jest.fn(),
      initializeDomReadyListeners: jest.fn(() => {
        require("./site.js").processActiveNetwork();
        require("./site.js").processDaisyUITheme();
        require("./site.js").processDjangoMessages();
      }),
      htmxState: { requestBlocking: false },
    }));

    const site = require("./site.js");

    site.initializeDomReadyListeners();

    expect(site.processActiveNetwork).toHaveBeenCalled();
    expect(site.processDaisyUITheme).toHaveBeenCalled();
    expect(site.processDjangoMessages).toHaveBeenCalled();
  });

  it("htmx:configRequest should start the progress bar", () => {
    const event = new CustomEvent("htmx:configRequest", {
      detail: { elt: document.body, requestConfig: {} },
    });
    document.body.dispatchEvent(event);
    const bar = document.getElementById("htmx-progress-bar");
    expect(bar.classList.contains("hidden")).toBe(false);
  });

  it("htmx:afterSwap should trigger multiple UI updates", () => {
    const site = require("./site.js");
    site.htmxState.requestBlocking = true;

    const swapTarget = document.createElement("div");
    swapTarget.dataset.toastMessage = "Swapped!";
    swapTarget.innerHTML = `
      <input type="text">
      <dialog id="my-modal"></dialog>
    `;
    const focusSpy = jest.spyOn(swapTarget.querySelector('input'), 'focus');


    const configRequestEvent = new CustomEvent("htmx:configRequest", {
      detail: { elt: document.body, requestConfig: {} },
    });
    document.body.dispatchEvent(configRequestEvent);

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget },
    });
    document.body.dispatchEvent(event); // Dispatch on body to ensure listener catches it

    // Let the first batch of timers run (progress bar, fade-in, autofocus)
    jest.advanceTimersByTime(300);

    // Test progress bar finish
    const bar = document.getElementById("htmx-progress-bar");
    expect(bar.classList.contains("hidden")).toBe(true);
    expect(bar.style.width).toBe("0%");

    // Test fade-in
    expect(swapTarget.classList.contains("fade-in")).toBe(false);

    // Test autofocus
    expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 30);
    expect(focusSpy).toHaveBeenCalled();


    // Test toast is present
    const toast = document.querySelector(".alert");
    expect(toast).not.toBeNull();
    expect(toast.textContent).toBe("Swapped!");

    // Test modal
    const modal = swapTarget.querySelector("#my-modal");
    expect(modal.showModal).toHaveBeenCalled();

    // Now run the timer for removing the toast
    jest.advanceTimersByTime(4500);
    expect(document.querySelector(".alert")).toBeNull();
  });

  it("htmx:afterSwap should handle swapped element being a dialog", () => {
    const swapTarget = document.createElement("dialog");
    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget },
    });
    document.body.dispatchEvent(event);
    expect(swapTarget.showModal).toHaveBeenCalled();
  });

  it("htmx:afterSwap should handle no focusable inputs or dialogs", () => {
    const swapTarget = document.createElement("div");
    swapTarget.innerHTML = "<span>Some content</span>";
    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget },
    });
    expect(() => swapTarget.dispatchEvent(event)).not.toThrow();
  });

  it("htmx:afterSwap should not show toast if data-toast-message is absent", () => {
    const site = require("./site.js");
    const swapTarget = document.createElement("div");
    swapTarget.innerHTML = `<span>No toast here</span>`;
    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget },
    });
    document.body.dispatchEvent(event);
    jest.advanceTimersByTime(300); // Allow fade-in to complete
    const toast = document.querySelector(".alert");
    expect(toast).toBeNull();
  });

  it("htmx:error should finish the progress bar", () => {
    const site = require('./site.js');
    site.htmxState.requestBlocking = true;

    const event = new Event("htmx:error", { bubbles: true });
    document.body.dispatchEvent(event);

    const bar = document.getElementById("htmx-progress-bar");
    expect(bar.style.width).toBe("100%");
    expect(document.body.style.pointerEvents).toBe("");
  });
});

describe("initializeDomReadyListeners Isolation Test", () => {
  let mockProcessActiveNetwork;
  let mockProcessDaisyUITheme;
  let mockProcessDjangoMessages;

  beforeEach(() => {
    jest.resetModules(); // Ensure a clean module state for this isolated test
    const site = require("./site.js");
    mockProcessActiveNetwork = jest.spyOn(site, "processActiveNetwork").mockImplementation(() => { });
    mockProcessDaisyUITheme = jest.spyOn(site, "processDaisyUITheme").mockImplementation(() => { });
    mockProcessDjangoMessages = jest.spyOn(site, "processDjangoMessages").mockImplementation(() => { });
  });

  afterEach(() => {
    mockProcessActiveNetwork.mockRestore();
    mockProcessDaisyUITheme.mockRestore();
    mockProcessDjangoMessages.mockRestore();
  });

  it("should call all initialization functions", () => {
    const { initializeDomReadyListeners } = require("./site.js");
    initializeDomReadyListeners();

    expect(mockProcessActiveNetwork).toHaveBeenCalledTimes(1);
    expect(mockProcessDaisyUITheme).toHaveBeenCalledTimes(1);
    expect(mockProcessDjangoMessages).toHaveBeenCalledTimes(1);
  });
});

describe("HTMX Progress Bar - generate-report-btn disabled state", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="htmx-progress-bar" class="hidden"></div>
      <div id="toast-container"></div>
      <form>
        <button id="generate-report-btn">Generate Report</button>
      </form>
    `;
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("htmx:configRequest should disable generate-report-btn when its form is triggered", () => {
    const btn = document.getElementById('generate-report-btn');
    const event = new CustomEvent("htmx:configRequest", {
      detail: {
        elt: btn.form,
        requestConfig: {}
      }
    });

    expect(btn.disabled).toBe(false);
    document.body.dispatchEvent(event);
    expect(btn.disabled).toBe(true);
  });

  it("htmx:configRequest should not disable generate-report-btn when different form is triggered", () => {
    const btn = document.getElementById('generate-report-btn');
    const otherForm = document.createElement('form');
    document.body.appendChild(otherForm);

    const event = new CustomEvent("htmx:configRequest", {
      detail: {
        elt: otherForm,
        requestConfig: {}
      }
    });

    expect(btn.disabled).toBe(false);
    document.body.dispatchEvent(event);
    expect(btn.disabled).toBe(false);
  });

  it("htmx:afterSwap should not throw if generate-report-btn doesn't exist", () => {
    document.getElementById('generate-report-btn').remove();

    const event = new CustomEvent("htmx:afterSwap", {
      detail: {
        target: document.createElement('div')
      }
    });

    expect(() => document.body.dispatchEvent(event)).not.toThrow();
  });
});

describe("htmx:load listener for transparency report", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="htmx-progress-bar" class="hidden"></div>
      <div id="toast-container"></div>
    `;

    // Mock the clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(),
      },
    });

    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("htmx:load should initialize transparency form when container exists", () => {
    document.body.innerHTML += `
      <div id="transparency-report-container">
        <input type="radio" name="report_type" value="monthly" checked>
        <input type="radio" name="report_type" value="quarterly">
        <div id="monthly-fields"></div>
        <div id="quarterly-fields" class="hidden"></div>
        <div id="yearly-fields" class="hidden"></div>
        <div id="custom-fields" class="hidden"></div>
      </div>
    `;

    // Trigger htmx:load event
    const event = new CustomEvent('htmx:load', { bubbles: true });
    document.body.dispatchEvent(event);

    // Test that form functionality works (radio buttons toggle fields)
    const quarterlyRadio = document.querySelector('input[value="quarterly"]');
    quarterlyRadio.checked = true;
    quarterlyRadio.dispatchEvent(new Event('change'));

    expect(document.getElementById('monthly-fields').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('quarterly-fields').classList.contains('hidden')).toBe(false);
  });

  it("htmx:load should initialize clipboard copy when container exists", () => {
    document.body.innerHTML += `
      <div id="transparency-report-container">
        <button id="copy-report-btn">Copy</button>
        <textarea id="report-textarea">Test content</textarea>
      </div>
    `;

    // Trigger htmx:load event
    const event = new CustomEvent('htmx:load', { bubbles: true });
    document.body.dispatchEvent(event);

    // Test that clipboard functionality works
    const copyBtn = document.getElementById('copy-report-btn');
    copyBtn.click();

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Test content");
    expect(copyBtn.innerHTML).toContain('Copied!');
  });

  it("htmx:load should not initialize anything when transparency container doesn't exist", () => {
    document.body.innerHTML += `
      <div id="some-other-container">
        <input type="radio" name="report_type" value="monthly" checked>
        <div id="monthly-fields"></div>
        <button id="copy-report-btn">Copy</button>
      </div>
    `;

    // These shouldn't work since container doesn't match
    const monthlyFields = document.getElementById('monthly-fields');
    const copyBtn = document.getElementById('copy-report-btn');

    // Trigger htmx:load event
    const event = new CustomEvent('htmx:load', { bubbles: true });
    document.body.dispatchEvent(event);

    // Radio buttons in wrong container shouldn't toggle
    const quarterlyRadio = document.querySelector('input[value="quarterly"]');
    if (quarterlyRadio) {
      quarterlyRadio.checked = true;
      quarterlyRadio.dispatchEvent(new Event('change'));
      // monthly-fields should remain visible (not toggled)
      expect(monthlyFields.classList.contains('hidden')).toBe(false);
    }

    // Copy button in wrong container shouldn't work
    if (copyBtn) {
      copyBtn.click();
      expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
    }
  });

  it("htmx:load should handle empty transparency container", () => {
    document.body.innerHTML += `
      <div id="transparency-report-container">
        <!-- Empty container -->
      </div>
    `;

    const event = new CustomEvent('htmx:load', { bubbles: true });

    // Should not throw
    expect(() => document.body.dispatchEvent(event)).not.toThrow();
  });
});

describe("processAllMessages Function", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="toast-container"></div>';
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("should process Django messages, container attributes, and element attributes", () => {
    // Set up multiple message sources
    document.body.innerHTML += `
      <div id="django-messages">
        <div data-message="Django message" data-message-type="success"></div>
      </div>
      <div id="element-with-toast" data-toast-message="Element message" data-toast-type="info">
        Some content
      </div>
      <div class="another-toast" data-toast-message="Another element" data-toast-type="warning">
        More content
      </div>
    `;

    // Create a container with its own toast attributes
    const container = document.createElement('div');
    container.dataset.toastMessage = "Container message";
    container.dataset.toastType = "error";

    // Execute the function
    processAllMessages(container);

    // Check all toasts were shown - should be 4 total (Django + 2 elements + container)
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(4);

    // Verify Django message toast
    expect(toastContainer.children[0].classList.contains("alert-success")).toBe(true);
    expect(toastContainer.children[0].textContent).toBe("Django message");

    // Verify element with toast attributes were cleared
    const elementWithToast = document.getElementById("element-with-toast");
    expect(elementWithToast.dataset.toastMessage).toBeUndefined();
    expect(elementWithToast.dataset.toastType).toBeUndefined();

    // Verify another element with toast attributes were cleared
    const anotherToast = document.querySelector('.another-toast');
    expect(anotherToast.dataset.toastMessage).toBeUndefined();
    expect(anotherToast.dataset.toastType).toBeUndefined();

    // Verify container attributes were cleared
    expect(container.dataset.toastMessage).toBeUndefined();
    expect(container.dataset.toastType).toBeUndefined();

    // Verify Django messages container was removed
    expect(document.getElementById("django-messages")).toBeNull();
  });

  it("should handle empty or missing messages gracefully", () => {
    // Test with empty data attributes
    document.body.innerHTML += `
      <div data-toast-message="" data-toast-type="info"></div>
      <div data-toast-message="   "></div>
    `;

    processAllMessages();

    // Empty message should not create a toast
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(0);
  });

  it("should handle missing container parameter", () => {
    // Set up some toast elements
    document.body.innerHTML += `
      <div data-toast-message="Element message" data-toast-type="info"></div>
    `;

    // Call without container
    processAllMessages();

    // Should still process the element
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(1);
    expect(toastContainer.children[0].textContent).toBe("Element message");
  });

  it("should process container attributes when provided", () => {
    // Create a container with toast attributes
    const container = document.createElement('div');
    container.dataset.toastMessage = "Container toast message";
    container.dataset.toastType = "success";

    // Execute with container
    processAllMessages(container);

    // Verify toast was shown
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(1);
    expect(toastContainer.children[0].textContent).toBe("Container toast message");
    expect(toastContainer.children[0].classList.contains("alert-success")).toBe(true);

    // Verify container attributes were cleared
    expect(container.dataset.toastMessage).toBeUndefined();
    expect(container.dataset.toastType).toBeUndefined();
  });

  it("should prioritize container attributes over other sources", () => {
    // Set up conflicting messages
    document.body.innerHTML += `
      <div id="django-messages">
        <div data-message="Django message" data-message-type="success"></div>
      </div>
      <div data-toast-message="Element message" data-toast-type="info"></div>
    `;

    // Create container with different message
    const container = document.createElement('div');
    container.dataset.toastMessage = "Container message (should be shown)";
    container.dataset.toastType = "error";

    processAllMessages(container);

    // Should show all 3 toasts (Django, Element, and Container)
    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(3);

    // All should be processed regardless of source
    const messages = Array.from(toastContainer.children).map(el => el.textContent);
    expect(messages).toContain("Django message");
    expect(messages).toContain("Element message");
    expect(messages).toContain("Container message (should be shown)");
  });

  it("should not fail when toast container is missing", () => {
    // Remove toast container
    document.body.innerHTML = '';

    // Set up some messages
    const container = document.createElement('div');
    container.dataset.toastMessage = "Test message";

    // Should not throw
    expect(() => processAllMessages(container)).not.toThrow();
  });
  it("should use 'info' as fallback when data-toast-type is missing or empty", () => {
    // Test with missing data-toast-type
    document.body.innerHTML += `
    <div data-toast-message="Message without type"></div>
  `;

    processAllMessages();

    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(1);
    expect(toastContainer.children[0].classList.contains("alert-info")).toBe(true);
    expect(toastContainer.children[0].textContent).toBe("Message without type");
  });

  it("should handle empty data-toast-type string", () => {
    // Test with empty data-toast-type
    document.body.innerHTML += `
    <div data-toast-message="Message with empty type" data-toast-type=""></div>
  `;

    processAllMessages();

    const toastContainer = document.getElementById("toast-container");
    expect(toastContainer.children.length).toBe(1);
    expect(toastContainer.children[0].classList.contains("alert-info")).toBe(true);
  });
});

describe("Dialog Modal Auto-open", () => {
  beforeEach(() => {
    // Mock showModal for all tests
    HTMLDialogElement.prototype.showModal = jest.fn();
    HTMLDialogElement.prototype.close = jest.fn();

    // Set up necessary elements for htmx:afterSwap
    document.body.innerHTML = `
      <div id="htmx-progress-bar" class="hidden"></div>
      <div id="toast-container"></div>
    `;

    // Use fake timers to handle setTimeout in htmx:afterSwap
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("should call showModal when dialog is not open", () => {
    const swapTarget = document.createElement("div");
    const dialog = document.createElement("dialog");
    dialog.open = false; // Explicitly set to not open

    swapTarget.appendChild(dialog);

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget }
    });

    document.body.dispatchEvent(event);

    // Advance timers to run the setTimeout for fade-in removal
    jest.advanceTimersByTime(300);

    expect(dialog.showModal).toHaveBeenCalledTimes(1);
  });

  it("should NOT call showModal when dialog is already open", () => {
    const swapTarget = document.createElement("div");
    const dialog = document.createElement("dialog");
    dialog.open = true; // Dialog is already open

    swapTarget.appendChild(dialog);

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget }
    });

    document.body.dispatchEvent(event);

    // Advance timers to run the setTimeout for fade-in removal
    jest.advanceTimersByTime(300);

    expect(dialog.showModal).not.toHaveBeenCalled();
  });

  it("should handle swapped element being a dialog itself", () => {
    const swappedDialog = document.createElement("dialog");
    swappedDialog.open = false;

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swappedDialog }
    });

    document.body.dispatchEvent(event);

    // Advance timers to run the setTimeout for fade-in removal
    jest.advanceTimersByTime(300);

    // When the swapped element itself is a dialog, it should open
    expect(swappedDialog.showModal).toHaveBeenCalledTimes(1);
  });

  it("should not throw when dialogs have no showModal method", () => {
    const swapTarget = document.createElement("div");
    const dialog = document.createElement("dialog");

    // Remove showModal method
    delete dialog.showModal;

    swapTarget.appendChild(dialog);

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget }
    });

    // Should not throw even if showModal is missing
    expect(() => {
      document.body.dispatchEvent(event);
      // Advance timers
      jest.advanceTimersByTime(300);
    }).not.toThrow();
  });

  it("should handle dialog with dynamic open property", () => {
    const swapTarget = document.createElement("div");
    const dialog = document.createElement("dialog");

    // Simulate dynamic property change by using a getter
    let dialogOpen = false;
    Object.defineProperty(dialog, 'open', {
      get() { return dialogOpen; },
      set(value) { dialogOpen = value; },
      configurable: true
    });

    swapTarget.appendChild(dialog);

    const event = new CustomEvent("htmx:afterSwap", {
      bubbles: true,
      detail: { target: swapTarget }
    });

    document.body.dispatchEvent(event);

    // Advance timers to run the setTimeout for fade-in removal
    jest.advanceTimersByTime(300);

    expect(dialog.showModal).toHaveBeenCalled();
  });
});
