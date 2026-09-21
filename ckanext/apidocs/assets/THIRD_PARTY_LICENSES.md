# Third party assets

## Swagger UI

The files below are unmodified distribution builds of
[Swagger UI](https://github.com/swagger-api/swagger-ui), released under the
Apache License 2.0 (see <https://github.com/swagger-api/swagger-ui/blob/master/LICENSE>).

| File | Purpose |
| ---- | ------- |
| `js/swagger-ui-bundle.js` | `SwaggerUIBundle` (Swagger UI 5.x) |
| `js/swagger-ui-standalone-preset.js` | `SwaggerUIStandalonePreset` |
| `css/swagger-ui.css` | Swagger UI stylesheet |

Upstream does not embed the release number in the bundles, so the exact patch
version is not recorded here. When updating these files, replace all three
together with the builds from a single
[Swagger UI release](https://github.com/swagger-api/swagger-ui/releases) and
record the version in this table.

Source maps (`*.map`) are intentionally not vendored: they roughly double the
size of the assets and are of no use in production. The `sourceMappingURL`
comments have been removed from the distributed files accordingly.

The `swagger-ui.js` build is not vendored either, because it duplicates
`swagger-ui-bundle.js` (loading both registers `SwaggerUIBundle` twice).

## normalize.css

`swagger-ui.css` embeds a minified copy of
[normalize.css v7.0.0](https://github.com/necolas/normalize.css) (MIT License),
as shipped by Swagger UI.
