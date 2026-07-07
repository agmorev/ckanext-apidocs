window.onload = function() {
  window.ui = SwaggerUIBundle({
    url: "ckanapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    showExtensions: false,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl,
    ],
    layout: "StandaloneLayout"
  });

  // Insert badge spans from the OpenAPI `x-badges` extension into
  // the `.opblock-summary-path-description-wrapper` element for each
  // operation once the UI has rendered.
  (function insertBadgesIntoWrappers() {
    const specUrl = "ckanapi.json";

    function addBadges(entries) {
      const maxAttempts = 20;
      let attempt = 0;

      const tryInsert = () => {
        attempt++;
        // Iterate backwards to allow removal of processed entries
        for (let i = entries.length - 1; i >= 0; i--) {
          const entry = entries[i];

          // Find matching path element by data-path and method class
          const pathEls = Array.from(document.querySelectorAll('.opblock-summary-path'))
            .filter(el => el.getAttribute('data-path') === entry.path && el.closest('.opblock-summary') && el.closest('.opblock-summary').classList.contains(`opblock-summary-${entry.method.toLowerCase()}`));

          if (!pathEls.length) continue;

          const pathEl = pathEls[0];
          const wrapper = pathEl.closest('.opblock-summary-path-description-wrapper');
          if (!wrapper) continue;

          // Insert badges
          entry.badges.forEach(b => {
            // Don't duplicate badges
            const existing = Array.from(wrapper.querySelectorAll('.opblock-badge')).some(s => s.textContent === b);
            if (existing) return;

            const span = document.createElement('span');
            span.className = 'opblock-badge';
            span.textContent = b;
            // Minimal inline styling so badges are visible without extra CSS
            span.style.marginLeft = '6px';
            span.style.padding = '2px 6px';
            span.style.borderRadius = '4px';
            if (b.toLowerCase().includes('core')) {
              span.style.backgroundColor = '#1194df';
              span.style.color = '#ffffff';
            } else if (b.toLowerCase().includes('chained')) {
              span.style.backgroundColor = '#89bf04';
              span.style.color = '#ffffff';
            } else {
              span.style.backgroundColor = '#7d8492';
              span.style.color = '#ffffff';
            }
            span.style.fontSize = '0.75rem';
            span.style.textTransform = 'none';
            wrapper.appendChild(span);
          });

          // Remove processed entry
          entries.splice(i, 1);
        }

        // Retry if there are remaining entries and attempts left
        if (entries.length && attempt < maxAttempts) {
          setTimeout(tryInsert, 200);
        }
      };

      tryInsert();
    }

    // Fetch the OpenAPI spec and extract badges
    fetch(specUrl)
      .then(r => r.json())
      .then(spec => {
        const entries = [];
        if (!spec || !spec.paths) return;
        Object.keys(spec.paths).forEach(path => {
          const methods = spec.paths[path] || {};
          Object.keys(methods).forEach(method => {
            const op = methods[method] || {};
            const badges = op['x-badges'] || [];
            if (badges && badges.length) entries.push({ path, method, badges });
          });
        });
        if (entries.length) addBadges(entries);
      })
      .catch(() => {});
  })();
};
