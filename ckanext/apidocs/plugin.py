import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.apidocs import views
from ckanext.apidocs.logic import action


class ApidocsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IActions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "apidocs")

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()
    
    # IActions

    def get_actions(self):
        return action.get_actions()

    # IClick

    def get_commands(self):
        from ckanext.apidocs import cli

        return cli.get_commands()
