/* Enhance the OpenAPI document textarea of the sysadmin page.
 *
 * The textarea stays the source of truth for the posted value and accepts
 * both JSON and YAML. The toolbar adds two actions:
 *
 * - "Format" sends the current content to the `format` endpoint, which parses
 *   JSON or YAML and answers with the pretty printed JSON, so a pasted YAML
 *   document is normalized before it is saved (and typos are reported).
 * - "Load generated document" fetches the document generated from the
 *   registered actions, without saving it.
 */
ckan.module('apidocs-schema-editor', function ($) {
  return {
    options: {
      formatUrl: null,
      generatedUrl: null
    },

    initialize: function () {
      $.proxyAll(this, /_on/);

      this.textarea = this.el.get(0);

      if (!this.textarea) {
        return;
      }

      this.form = this.textarea.form;
      this._buildLayout();

      this.formatButton.addEventListener('click', this._onFormat);

      if (this.options.generatedUrl) {
        this.generatedButton.addEventListener('click', this._onLoadGenerated);
      }
    },

    _buildLayout: function () {
      this.toolbar = document.createElement('div');
      this.toolbar.className = 'apidocs-schema-editor-toolbar d-flex gap-2 py-2';

      this.formatButton = document.createElement('button');
      this.formatButton.type = 'button';
      this.formatButton.className = 'btn btn-secondary btn-sm';
      this.formatButton.textContent = this._('Format');
      this.toolbar.appendChild(this.formatButton);

      if (this.options.generatedUrl) {
        this.generatedButton = document.createElement('button');
        this.generatedButton.type = 'button';
        this.generatedButton.className = 'btn btn-secondary btn-sm';
        this.generatedButton.textContent = this._('Load generated document');
        this.toolbar.appendChild(this.generatedButton);
      }

      this.errorBox = document.createElement('div');
      this.errorBox.className = 'alert alert-danger apidocs-schema-editor-errors';
      this.errorBox.hidden = true;

      var parent = this.textarea.parentNode;
      parent.insertBefore(this.toolbar, this.textarea);
      parent.insertBefore(this.errorBox, this.textarea);
    },

    _onFormat: function () {
      this._clearErrors();
      this._setBusy(true);

      var self = this;

      fetch(this.options.formatUrl, {
        method: 'POST',
        body: this._requestBody()
      })
        .then(function (response) {
          return response.text().then(function (body) {
            return {ok: response.ok, body: body};
          });
        })
        .then(function (result) {
          if (result.ok) {
            self.textarea.value = result.body;
            return;
          }
          self._showErrors(self._errorMessages(result.body));
        })
        .catch(function () {
          self._showErrors([self._('The document could not be formatted.')]);
        })
        .finally(function () {
          self._setBusy(false);
        });
    },

    _onLoadGenerated: function () {
      this._clearErrors();
      this._setBusy(true);

      var self = this;

      fetch(this.options.generatedUrl)
        .then(function (response) {
          return response.text();
        })
        .then(function (body) {
          if (self.textarea.value.trim() &&
              !window.confirm(self._(
                'The current content of the editor will be replaced by the ' +
                'document generated from the registered actions. Continue?'))) {
            return;
          }
          self.textarea.value = body;
        })
        .catch(function () {
          self._showErrors([self._('The generated document could not be loaded.')]);
        })
        .finally(function () {
          self._setBusy(false);
        });
    },

    /* The body of the request reuses the form so the CSRF token is sent. */
    _requestBody: function () {
      if (this.form) {
        return new FormData(this.form);
      }

      var body = new FormData();
      body.set('definition', this.textarea.value);

      return body;
    },

    _errorMessages: function (body) {
      try {
        var payload = JSON.parse(body);
        if (payload.errors && payload.errors.length) {
          return payload.errors;
        }
      } catch (err) {
        // not a JSON error payload, fall through to the raw body
      }

      return [body || this._('The document could not be formatted.')];
    },

    _setBusy: function (busy) {
      this.formatButton.disabled = busy;

      if (this.generatedButton) {
        this.generatedButton.disabled = busy;
      }
    },

    _showErrors: function (messages) {
      var list = document.createElement('ul');

      messages.forEach(function (message) {
        var item = document.createElement('li');
        item.textContent = message;
        list.appendChild(item);
      });

      this.errorBox.innerHTML = '';
      this.errorBox.appendChild(list);
      this.errorBox.hidden = false;
      this.errorBox.scrollIntoView({behavior: 'smooth', block: 'center'});
    },

    _clearErrors: function () {
      this.errorBox.hidden = true;
      this.errorBox.innerHTML = '';
    }
  };
});
