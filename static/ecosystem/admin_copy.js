/**
 * Ecosystem admin helpers: clipboard copy and confirm-before-submit.
 */
(function () {
  "use strict";

  function flashLabel(button, label) {
    if (!button || !label) return;
    var original = button.getAttribute("data-original-label") || button.textContent;
    button.setAttribute("data-original-label", original);
    button.textContent = label;
    window.setTimeout(function () {
      button.textContent =
        button.getAttribute("data-original-label") || original;
    }, 1800);
  }

  function setCopyStatus(message, isError) {
    var status = document.getElementById("eco-copy-status");
    if (!status) return;
    status.textContent = message || "";
    status.classList.toggle("eco-status-error", !!isError && !!message);
  }

  function fallbackCopy(text) {
    return new Promise(function (resolve, reject) {
      var textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "0";
      textarea.style.left = "0";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);
      var succeeded = false;
      try {
        succeeded = document.execCommand("copy");
      } catch (error) {
        succeeded = false;
      }
      document.body.removeChild(textarea);
      if (succeeded) {
        resolve();
      } else {
        reject(new Error("Clipboard unavailable"));
      }
    });
  }

  function copyText(text) {
    if (
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function" &&
      window.isSecureContext
    ) {
      return navigator.clipboard.writeText(text).catch(function () {
        return fallbackCopy(text);
      });
    }
    return fallbackCopy(text);
  }

  function resolveText(button) {
    var direct = button.getAttribute("data-copy");
    if (direct) return direct;
    var fromId = button.getAttribute("data-copy-from");
    if (!fromId) return "";
    var source = document.getElementById(fromId);
    return source ? (source.textContent || "").trim() : "";
  }

  document.addEventListener("click", function (event) {
    var confirmControl = event.target.closest("[data-confirm]");
    if (confirmControl) {
      var message = confirmControl.getAttribute("data-confirm") || "";
      if (message && !window.confirm(message)) {
        event.preventDefault();
        return;
      }
    }

    var button = event.target.closest("[data-copy], [data-copy-from]");
    if (!button) return;
    event.preventDefault();
    var text = resolveText(button);
    var failedLabel =
      button.getAttribute("data-copy-failed-label") || "Copy failed";
    if (!text) {
      flashLabel(button, failedLabel);
      setCopyStatus(failedLabel, true);
      return;
    }
    copyText(text)
      .then(function () {
        var copied =
          button.getAttribute("data-copied-label") || "Copied";
        flashLabel(button, copied);
        setCopyStatus(copied, false);
      })
      .catch(function () {
        flashLabel(button, failedLabel);
        setCopyStatus(failedLabel, true);
      });
  });
})();
