# ckanext-apidocs

This extension documents [CKAN APIs](https://docs.ckan.org/en/2.11/api/index.html#api-guide) for developers who want to write code that interacts with a CKAN site and its data.
CKAN's Action API is a powerful, RPC-style API that exposes all of CKAN's core features to API clients. All of a CKAN website's core functionality (everything you can do with the web interface and more) can be used by external code that calls the CKAN API.

The extension generates an [OpenAPI](https://spec.openapis.org/oas/v3.0.3) 3.0 document from the actions registered in your CKAN instance (core actions plus the actions of every enabled extension) and serves it through [Swagger UI](https://github.com/swagger-api/swagger-ui).

[Swagger UI](https://github.com/swagger-api/swagger-ui) allows anyone — be it your development team or your end consumers — to visualize and interact with the API's resources without having any of the implementation logic in place. It is automatically generated from the OpenAPI specification, with the visual documentation making it easy for back end implementation and client side consumption.


## Requirements

| CKAN version | Compatible? |
| ------------ | ----------- |
| 2.11         | yes         |
| 2.12         | yes         |

Python 3.10 or newer is required.


## Installation

To install ckanext-apidocs:

1. Activate your CKAN virtual environment, for example:

       . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv:

       git clone https://github.com/agmorev/ckanext-apidocs.git
       cd ckanext-apidocs
       pip install -e .

3. Add `apidocs` to the `ckan.plugins` setting in your CKAN config file (by default the config file is located at `/etc/ckan/default/ckan.ini`):

       ckan.plugins = ... apidocs

4. Create the tables storing the OpenAPI document edited by sysadmins:

       ckan -c /etc/ckan/default/ckan.ini db upgrade -p apidocs

5. Build the front-end assets if you are not running CKAN in debug mode:

       ckan -c /etc/ckan/default/ckan.ini asset build

6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

       sudo service apache2 reload

7. Optionally, add a link to the documentation to your theme:

       <a href="{{ h.url_for('apidocs.index') }}">{{ _('CKAN API') }}</a>

The documentation is available at `https://<hostname>/api/docs/`.


## Endpoints

| URL | Content |
| --- | ------- |
| `/api/docs/` | Swagger UI |
| `/api/docs/ckanapi.json` (alias `/api/docs/openapi.json`) | OpenAPI document, JSON |
| `/api/docs/ckanapi.yaml` (alias `/api/docs/openapi.yaml`) | OpenAPI document, YAML |

The JSON and YAML endpoints send an `ETag` and support conditional requests
(`If-None-Match`), so clients can poll them cheaply. The generated document is
built at most once per `ckanext.apidocs.cache_ttl` seconds; the HTTP cache
lifetime of the responses is controlled by the core `ckan.cache_expires` and
`ckan.cache_enabled` settings.


## The OpenAPI document edited by sysadmins

Sysadmins get an **API documentation** tab under `/ckan-admin/` (mounted at
`/ckan-admin/apidocs/`) showing the document that is currently served:

- While no document is stored, the tab is prefilled with the document
generated from the registered actions, so it can be used as a starting point.
- The document is edited as JSON or YAML. YAML is converted to JSON when the
schema is saved; **Format** normalizes the content without saving it and
**Load generated document** fetches the generated document without saving it.
- Saving stores the document in the `apidocs_schema` database table, where
every worker process picks it up without waiting for the cache to expire. The
stored document is then served by `/api/docs/`, `/api/docs/ckanapi.json`,
`/api/docs/ckanapi.yaml` (and their `openapi.*` aliases) instead of the
generated one.
- **Reset to generated** removes the stored document, so the documentation is
generated from the registered actions again.

Only the structural part of the specification the documentation page needs is
validated on save: the document has to be an OpenAPI 3.x mapping with `info`
(`title` and `version`) and `paths`. For a full validation, point
`ckanext.apidocs.ui.validator_url` at a Swagger UI validator.

The document is stored as JSON (a `JSONB` column), so whitespace is not
preserved. Object key order is not preserved either — `jsonb` stores the keys
sorted by length — so the extension stores and serves the document with every
object key in **alphabetical order**. Sorting `paths` is what makes the
documentation readable: the Swagger UI groups the operations into one section
per HTTP method and lists each section in the order of `paths`, so every
method section is alphabetical as well.

The same document is available to sysadmins through the Action API, with the
usual `Authorization` header:

- `apidocs_schema_show` — the stored document, or `{}` when there is none
- `apidocs_schema_update` — store a document (`definition`, JSON or YAML)
- `apidocs_schema_delete` — remove the stored document

Note that a stored document is served as is: it replaces the generated
document completely, so `IApidocs.modify_openapi_spec` implementations and the
automatically added badges are only applied to the generated document.


## Config settings

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `ckanext.apidocs.base_path` | `/api/3/action` | Server URL prefix used for the documented action endpoints (`servers` in the OpenAPI document) |
| `ckanext.apidocs.openapi_version` | `3.0.0` | OpenAPI version to advertise (`3.0.0` or `3.1.0`) |
| `ckanext.apidocs.enable_api_methods` | `GET POST PUT PATCH DELETE` | Space separated list of HTTP methods to document |
| `ckanext.apidocs.title` | `CKAN API` | Title of the documentation (`info.title`) |
| `ckanext.apidocs.description` | built-in text | Long description shown at the top of the page (`info.description`), markdown is supported |
| `ckanext.apidocs.spec_version` | CKAN version | Version of the documented API (`info.version`) |
| `ckanext.apidocs.token_header` | `apitoken_header_name` or `Authorization` | Header used to send the API token from the UI |
| `ckanext.apidocs.cache_ttl` | `300` | Seconds the generated document is cached for. `0` disables caching |
| `ckanext.apidocs.require_login` | `false` | Require an authenticated user to access the documentation and the specification |
| `ckanext.apidocs.sysadmin_only` | `false` | Only sysadmins can access the documentation. Signing in becomes mandatory, everyone else gets a `403` |
| `ckanext.apidocs.allowed_users` | *(empty)* | Space separated usernames allowed to access the documentation. Signing in becomes mandatory and everyone else gets a `403` |
| `ckanext.apidocs.include_extensions` | *(empty)* | Only document the actions of these extensions. Empty means "all of them" |
| `ckanext.apidocs.exclude_extensions` | *(empty)* | Never document the actions of these extensions |
| `ckanext.apidocs.ui.validator_url` | *(empty)* | Swagger UI validator URL. Empty disables the external validator |
| `ckanext.apidocs.ui.persist_authorization` | `true` | Keep the API token in the browser between page loads |
| `ckanext.apidocs.ui.doc_expansion` | `list` | `none`, `list` or `full` |
| `ckanext.apidocs.ui.filter` | `true` | Show the search box |
| `ckanext.apidocs.ui.try_it_out` | `true` | Enable "Try it out" requests |
| `ckanext.apidocs.ui.deep_linking` | `true` | Update the URL fragment when an operation is opened |

Example:

    ckanext.apidocs.title = Example Data Portal API
    ckanext.apidocs.require_login = true
    ckanext.apidocs.allowed_users = editor api_bot
    ckanext.apidocs.token_header = X-CKAN-API-Key
    ckanext.apidocs.exclude_extensions = datastore datapusher
    ckanext.apidocs.ui.doc_expansion = full

All settings are declared in [`ckanext/apidocs/config_declaration.yaml`](ckanext/apidocs/config_declaration.yaml) and loaded through the CKAN `config_declarations` blanket, so they are reported by `ckan config validate` and included in the configuration generated by CKAN:

    ckan -c /etc/ckan/default/ckan.ini config declaration apidocs
    ckan -c /etc/ckan/default/ckan.ini config describe apidocs --format=yaml


## Using a CKAN API key with the docs UI

The extension exposes an `ApiKeyAuth` security scheme that lets you paste your CKAN API key into the Swagger UI "Authorize" dialog, so the UI sends it in the `Authorization` header for API requests.

How to obtain your API key:

- Sign in to your CKAN site and open your user profile page.
- Look for the "API key" or "Reset your API key" control (depends on your CKAN theme/version) and copy the key.

How to use it in the UI:

1. Open the `/api/docs/` page in your browser.
2. Click the **Authorize** button (top-right of Swagger UI) and paste your API key into the prompt.
3. After authorizing, subsequent requests from the UI will include the API key in the configured header.

Security note: never share your API key, and prefer using short-lived tokens or fine-grained access control where available. If you do not want the documentation to be publicly accessible, set `ckanext.apidocs.require_login = true`; to open it only to administrators, set `ckanext.apidocs.sysadmin_only = true`; to open it only to a handful of accounts, list them in `ckanext.apidocs.allowed_users` (usernames are matched case-insensitively, and being listed is required in addition to being signed in).


## Command line interface

Export the generated specification, for example to feed another tool:

    ckan -c /etc/ckan/default/ckan.ini apidocs export - --format=json
    ckan -c /etc/ckan/default/ckan.ini apidocs export openapi.yaml
    ckan -c /etc/ckan/default/ckan.ini apidocs export --base-path=/api/3/action --version=2.11
    ckan -c /etc/ckan/default/ckan.ini apidocs export --generated

`-` (the default) writes to stdout, anything else is treated as a file path.
The stored document is exported when there is one; `--generated` (or one of
the overrides, which imply a rebuild) exports the document generated from the
registered actions instead.


## Extending the specification

Other extensions can adjust the generated document or add badges to individual
actions by implementing `IApidocs`:

    import ckan.plugins as p

    from ckanext.apidocs import interfaces


    class MyPlugin(p.SingletonPlugin):
        p.implements(interfaces.IApidocs)

        def modify_openapi_spec(self, spec):
            spec["servers"].append({"url": "https://api.example.com"})
            return spec

        def get_action_badges(self, action_name, origin):
            if action_name.startswith("myplugin_"):
                return ["myplugin"]
            return None

Badges are stored in the `x-badges` extension of each operation and rendered
next to the action path in the Swagger UI. The origin badge (`core` or the name
of the extension providing the action) and the `chained` badge are added
automatically.


## Developer installation

To install ckanext-apidocs for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/agmorev/ckanext-apidocs.git
    cd ckanext-apidocs
    pip install -e '.[dev]'


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini

To run the linters:

    ruff check .
    mypy ckanext/apidocs


## Releasing a new version of ckanext-apidocs

If ckanext-apidocs should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in `pyproject.toml`. See [PEP 440](https://peps.python.org/pep-0440/) for how to choose version numbers, and add the corresponding `CHANGELOG.md` entry.

2. Make sure you have the latest version of necessary packages:

       pip install --upgrade build twine

3. Create a source and binary distribution of the new version and check it:

       python -m build && twine check dist/*

   Verify that the wheel contains the assets, templates and license files
   (`unzip -l dist/*.whl`), then fix any errors you get.

4. Upload the distributions to PyPI:

       twine upload dist/*

5. Commit any outstanding changes, then tag the release:

       git commit -a
       git push
       git tag 0.1.0
       git push --tags


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)

The vendored Swagger UI assets are distributed under the Apache License 2.0,
see `ckanext/apidocs/assets/THIRD_PARTY_LICENSES.md`.

