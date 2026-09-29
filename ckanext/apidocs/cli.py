"""Command line interface of ckanext-apidocs."""

from __future__ import annotations

import click

from ckanext.apidocs import helpers


@click.group(short_help="Manage the CKAN API documentation.")
def apidocs():
    """Commands for the apidocs extension."""


@apidocs.command("export")
@click.argument("output", required=False, default="-")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    show_default=True,
)
@click.option(
    "--base-path",
    default=None,
    help="Server URL prefix of the action endpoints. Defaults to the "
    "ckanext.apidocs.base_path setting.",
)
@click.option(
    "--version",
    default=None,
    help="Version advertised in the OpenAPI document. Defaults to the "
    "ckanext.apidocs.spec_version setting.",
)
@click.option(
    "--generated",
    is_flag=True,
    help="Export the document generated from the registered actions, "
    "ignoring the schema stored by a sysadmin.",
)
def export(
    output: str,
    fmt: str,
    base_path: str | None,
    version: str | None,
    generated: bool,
):
    """Export the OpenAPI specification of the actions.

    The schema stored by a sysadmin is exported when there is one, exactly
    as the documentation endpoints serve it. Use ``--generated`` (or one of
    the overrides, which imply a rebuild) to export the document generated
    from the registered actions instead.

    When OUTPUT is "-" (the default) the specification is written to
    stdout, otherwise it is written to the given file.
    """
    if generated or base_path is not None or version is not None:
        spec = helpers.build_openapi_spec(base_path=base_path, version=version)
    else:
        spec = helpers.get_openapi_spec()

    if fmt == "yaml":
        content = helpers.dump_openapi_yaml(spec)
    else:
        content = helpers.dumps_openapi_json(spec)

    if output == "-":
        click.echo(content)
        return

    try:
        with open(output, "w", encoding="utf-8") as spec_file:
            spec_file.write(content)
    except OSError as err:
        raise click.ClickException(
            f"Could not write the specification to {output}: {err}"
        ) from err

    click.echo(f"Wrote the OpenAPI specification to {output}")


def get_commands():
    return [apidocs]
