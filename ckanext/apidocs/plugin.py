"""The ckanext-apidocs plugin."""

from __future__ import annotations

from ckan import plugins as p
from ckan.common import CKANConfig
from ckan.plugins import toolkit as tk

from ckanext.apidocs import helpers, views


@tk.blanket.config_declarations
class ApidocsPlugin(p.SingletonPlugin):
    """Document the API of a CKAN instance with Swagger UI.

    Config options are declared in ``ckanext/apidocs/config_declaration.yaml``
    and loaded through the ``config_declarations`` blanket.
    """

    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.IClick)

    # IConfigurer

    def update_config(self, config_: CKANConfig):
        tk.add_template_directory(config_, "templates")
        tk.add_resource("assets", "apidocs")

        helpers.invalidate_cache()

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()

    # IClick

    def get_commands(self):
        from ckanext.apidocs import cli

        return cli.get_commands()
