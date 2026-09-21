/* global SwaggerUIBundle, SwaggerUIStandalonePreset */
/**
 * Swagger UI initializer.
 *
 * Reads the page configuration rendered by the blueprint
 * (`#apidocs-config`), creates the Swagger UI instance and renders the
 * `x-badges` extension of the operations.
 */
(function (window, document) {
  "use strict";

  var BADGES = {
    core: "badge-core",
    chained: "badge-chained",
    "side-effect-free": "badge-side-effect-free",
  };

  function readConfig() {
    var node = document.getElementById("apidocs-config");

    if (!node) {
      return {};
    }

    try {
      return JSON.parse(node.textContent || "{}") || {};
    } catch (err) {
      window.console.warn("[apidocs] invalid page configuration", err);
      return {};
    }
  }

  function badgeClass(name) {
    var key = String(name).toLowerCase();
    return BADGES[key] || "badge-extension";
  }

  function summaryMethod(summary) {
    var match = /opblock-summary-([a-z]+)/.exec(summary.className || "");
    return match ? match[1] : null;
  }

  function summaryPath(summary) {
    var node = summary.querySelector(".opblock-summary-path");

    if (!node) {
      return null;
    }

    return (node.getAttribute("data-path") || node.textContent || "").trim();
  }

  function appendBadge(wrapper, name) {
    var badge = document.createElement("span");
    badge.className = "opblock-badge " + badgeClass(name);
    badge.textContent = name;
    wrapper.appendChild(badge);
  }

  /**
   * Copy the badges of each operation next to its path.
   *
   * Swagger UI does not render custom `x-badges` extensions, so the badges
   * are looked up in the page configuration and appended to the operation
   * summary whenever it is added to the DOM.
   */
  function decorate(root, badges) {
    var summaries = root.querySelectorAll(".opblock-summary");

    Array.prototype.forEach.call(summaries, function (summary) {
      if (summary.getAttribute("data-apidocs-badges")) {
        return;
      }

      summary.setAttribute("data-apidocs-badges", "done");

      var path = summaryPath(summary);
      var method = summaryMethod(summary);
      var entry = path && badges ? badges[path] : null;
      var values = entry && method ? entry[method] : null;

      if (!values || !values.length) {
        return;
      }

      var wrapper =
        summary.querySelector(".opblock-summary-path-description-wrapper") ||
        summary;

      values.forEach(function (name) {
        appendBadge(wrapper, name);
      });
    });
  }

  function watchBadges(container, badges) {
    if (!badges || !Object.keys(badges).length) {
      return;
    }

    decorate(container, badges);

    var observer = new MutationObserver(function () {
      decorate(container, badges);
    });

    observer.observe(container, { childList: true, subtree: true });
  }

  function initialize(container) {
    var config = readConfig();
    var options = Object.assign(
      {
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
      },
      config.ui || {},
      {
        url: config.specUrl || "ckanapi.json",
        dom_id: "#" + container.id,
      }
    );

    window.apidocsSwaggerUI = SwaggerUIBundle(options);
    watchBadges(container, config.badges || {});
  }

  window.apidocsInitializer = { initialize: initialize };
})(window, document);

