/**
 * Boots Swagger UI on the API documentation page.
 *
 * Works both as a CKAN module (when `ckan.js` is available) and as a plain
 * DOM ready handler, so the page keeps working on themes that do not load
 * the default CKAN assets.
 */
(function (window, document) {
  "use strict";

  function boot() {
    var container = document.getElementById("swagger-ui");

    if (!container || container.getAttribute("data-apidocs-initialized")) {
      return;
    }

    if (!window.apidocsInitializer || !window.SwaggerUIBundle) {
      window.console.error("[apidocs] Swagger UI assets are not available");
      return;
    }

    container.setAttribute("data-apidocs-initialized", "true");

    try {
      window.apidocsInitializer.initialize(container);
    } catch (err) {
      container.removeAttribute("data-apidocs-initialized");
      window.console.error("[apidocs] could not initialize Swagger UI", err);
    }
  }

  if (window.ckan && window.ckan.module) {
    window.ckan.module("apidocs-swagger", function () {
      return { initialize: boot };
    });
  }

  document.addEventListener("DOMContentLoaded", boot);
})(window, document);

