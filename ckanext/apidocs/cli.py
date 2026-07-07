import json
import click

from ckanext.apidocs import helpers


@click.group(short_help="example CLI.")
def example():
    """example CLI.
    """
    pass


@example.command()
@click.argument("name", default="example")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


@click.group(short_help="apidocs CLI.")
def apidocs():
    """Commands for the apidocs extension"""
    pass


@apidocs.command("export")
@click.argument("output", required=False, default="-")
@click.option("--format", "fmt", type=click.Choice(["yaml", "json"]), default="yaml", show_default=True)
@click.option("--base-path", default="/api/3/action", show_default=True,
              help="Base path to use for action endpoints")
@click.option("--version", default="2.11.4", show_default=True, help="CKAN version to advertise in OpenAPI info")
def export(output: str, fmt: str, base_path: str, version: str):
    """Export the generated OpenAPI spec for CKAN actions.

    If OUTPUT is '-' writes to stdout, otherwise writes to the given file path.
    """
    spec = helpers.build_openapi_spec(version=version, base_path=base_path)
    if fmt == "yaml":
        content = helpers.dump_openapi_yaml(spec)
    else:
        content = json.dumps(spec, indent=2)

    if output == "-":
        click.echo(content)
        return

    with open(output, "w", encoding="utf-8") as fh:
        fh.write(content)
    click.echo(f"Wrote spec to {output}")


def get_commands():
    return [example, apidocs]
