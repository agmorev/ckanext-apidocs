import json

from flask import Blueprint, render_template
from flask.wrappers import Response

from ckanext.apidocs import helpers


apidocs = Blueprint("apidocs", __name__, url_prefix="/api/docs/")

config = {
    "app_name": "CKAN API DOCS",
    "dom_id": "#swagger-ui",
    "layout": "StandaloneLayout",
    "deepLinking": True,
}

fields = {
    # Some fields are used directly in template
    "base_url": "/",
    "app_name": config.pop("app_name"),
    # Rest are just serialized into json string for inclusion in the .js file
    "config_json": json.dumps(config),
}


def index() -> str | Response:
    return render_template("apidocs/index.html", **fields)


def ckanapi_json() -> Response:
    spec = helpers.build_openapi_spec()
    return Response(json.dumps(spec, indent=2), mimetype="application/json")


def ckanapi_yaml() -> Response:
    spec = helpers.build_openapi_spec()
    yaml_str = helpers.dump_openapi_yaml(spec)
    return Response(yaml_str, mimetype="application/x-yaml")


apidocs.add_url_rule("/", view_func=index)
apidocs.add_url_rule("/ckanapi.yaml", view_func=ckanapi_yaml)
apidocs.add_url_rule("/ckanapi.json", view_func=ckanapi_json)


def get_blueprints():
    return [apidocs]
