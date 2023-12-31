import click


@click.group(short_help="apidocs CLI.")
def apidocs():
    """apidocs CLI.
    """
    pass


@apidocs.command()
@click.argument("name", default="apidocs")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [apidocs]
