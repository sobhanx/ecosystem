/**
 * Location workspace drag-and-drop ordering.
 * Sends ordered service IDs to the server; does not compute positions itself.
 */
(function () {
  "use strict";

  function getCookie(name) {
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  function getCsrfToken() {
    var input = document.querySelector('[name="csrfmiddlewaretoken"]');
    if (input && input.value) {
      return input.value;
    }
    return getCookie("csrftoken");
  }

  function setStatus(el, message, isError) {
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("eco-status-error", !!isError);
    el.classList.toggle("eco-status-ok", !isError && !!message);
  }

  function collectIds(tbody) {
    return Array.prototype.map.call(
      tbody.querySelectorAll("tr[data-service-id]"),
      function (row) {
        return parseInt(row.getAttribute("data-service-id"), 10);
      }
    );
  }

  function updateOrderLabels(tbody) {
    Array.prototype.forEach.call(
      tbody.querySelectorAll("tr[data-service-id]"),
      function (row, index) {
        var cell = row.querySelector("[data-order-label]");
        if (cell) {
          cell.textContent = String(index + 1);
        }
      }
    );
  }

  function restoreOrder(tbody, order) {
    var byId = {};
    Array.prototype.forEach.call(
      tbody.querySelectorAll("tr[data-service-id]"),
      function (row) {
        byId[row.getAttribute("data-service-id")] = row;
      }
    );
    order.forEach(function (id) {
      var row = byId[String(id)];
      if (row) {
        tbody.appendChild(row);
      }
    });
  }

  function init() {
    var root = document.getElementById("eco-sortable-services");
    if (!root || typeof Sortable === "undefined") {
      return;
    }

    var reorderUrl = root.getAttribute("data-reorder-url");
    var statusEl = document.getElementById("eco-reorder-status");
    if (!reorderUrl) {
      return;
    }

    var previousOrder = collectIds(root);
    var saving = false;

    Sortable.create(root, {
      handle: ".eco-drag-handle",
      animation: 150,
      ghostClass: "eco-sortable-ghost",
      chosenClass: "eco-sortable-chosen",
      dragClass: "eco-sortable-drag",
      onStart: function () {
        if (saving) {
          return false;
        }
        previousOrder = collectIds(root);
        setStatus(statusEl, "", false);
      },
      onEnd: function () {
        var orderedIds = collectIds(root);
        var unchanged =
          orderedIds.length === previousOrder.length &&
          orderedIds.every(function (id, index) {
            return id === previousOrder[index];
          });
        if (unchanged || saving) {
          return;
        }

        updateOrderLabels(root);
        saving = true;
        setStatus(
          statusEl,
          (statusEl && statusEl.getAttribute("data-saving-label")) || "Saving…",
          false
        );

        fetch(reorderUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken() || "",
            Accept: "application/json",
          },
          body: JSON.stringify({ ordered_ids: orderedIds }),
        })
          .then(function (response) {
            return response.json().then(function (data) {
              return { ok: response.ok, status: response.status, data: data };
            });
          })
          .then(function (result) {
            if (!result.ok || !result.data || !result.data.ok) {
              throw new Error(
                (result.data && result.data.error) ||
                  (statusEl && statusEl.getAttribute("data-error-label")) ||
                  "Reorder failed."
              );
            }
            previousOrder = orderedIds;
            setStatus(
              statusEl,
              (statusEl && statusEl.getAttribute("data-saved-label")) ||
                "Order saved.",
              false
            );
          })
          .catch(function (error) {
            restoreOrder(root, previousOrder);
            updateOrderLabels(root);
            setStatus(
              statusEl,
              error.message ||
                (statusEl && statusEl.getAttribute("data-error-label")) ||
                "Reorder failed.",
              true
            );
          })
          .then(function () {
            saving = false;
          });
      },
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
