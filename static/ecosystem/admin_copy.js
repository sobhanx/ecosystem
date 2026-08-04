/**
 * Copy-to-clipboard for ecosystem admin snippets (template tags, URLs).
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
    }, 1500);
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("Clipboard unavailable"));
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
    var button = event.target.closest("[data-copy], [data-copy-from]");
    if (!button) return;
    event.preventDefault();
    var text = resolveText(button);
    if (!text) return;
    copyText(text).then(function () {
      flashLabel(
        button,
        button.getAttribute("data-copied-label") || "Copied"
      );
    });
  });
})();
