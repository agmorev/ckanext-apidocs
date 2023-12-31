import os
import json

from typing import Optional

from flask import Blueprint, render_template, request

from ckan.types import Response


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


def index(path: Optional[str]=None) -> Response:
    fields["config_json"] = json.dumps(config)
    return render_template("apidocs/index.html", **fields)

apidocs.add_url_rule("/", view_func=index, methods=['GET', 'POST'])


def get_blueprints():
    return [apidocs]
