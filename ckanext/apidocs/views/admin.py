"""Sysadmin views for the OpenAPI document served by the documentation.

The page mounts the editor at ``/ckan-admin/apidocs``: the document is shown
as JSON and can be edited as JSON or YAML. Saving it stores the document in
the database, from where every documentation endpoint serves it instead of
the document generated from the registered actions. Removing the stored
document falls back to the generated one.
"""

from __future__ import annotations

import json
from typing import Any

from flask import Blueprint
from flask.wrappers import Response

import ckan.plugins.toolkit as tk

from ckanext.apidocs import helpers
from ckanext.apidocs.logic.validators import (
    InvalidDefinition,
    parse_definition,
)
from ckanext.apidocs.utils.ordering import canonical_definition


ADMIN_BP = "apidocs_admin"

bp = Blueprint(ADMIN_BP, __name__, url_prefix="/ckan-admin/apidocs")


def _action_context() -> dict[str, Any]:
    return {"user": tk.current_user.name, "auth_user_obj": tk.current_user}


def _sysadmin_or_403() -> None:
    try:
        tk.check_access("sysadmin", _action_context())
    except tk.NotAuthorized:
        tk.abort(403, tk._("Need to be system administrator to administer"))


bp.before_request(_sysadmin_or_403)


def index(
    data: dict[str, Any] | None = None,
    errors: dict[str, Any] | None = None,
    error_summary: dict[str, Any] | None = None,
) -> str:
    """Render the editor, prefilled with the document currently in use."""
    stored = helpers.get_stored_schema()

    if data is None:
        definition = (
            stored.canonical_definition
            if stored
            else helpers.build_openapi_spec()
        )
        data = {"definition": _dump(definition)}

    return tk.render(
        "apidocs/schema_form.html",
        {
            "data": data,
            "errors": errors or {},
            "error_summary": error_summary or {},
            "stored": stored,
        },
    )


def save() -> Any:
    """Store the posted document and make it the served one."""
    data = {"definition": tk.request.form.get("definition", "")}

    try:
        tk.get_action("apidocs_schema_update")(_action_context(), dict(data))
    except tk.ValidationError as err:
        return index(data, err.error_dict, err.error_summary)

    helpers.invalidate_cache()
    tk.h.flash_success(tk._("The API documentation schema has been updated."))

    return tk.redirect_to(f"{ADMIN_BP}.index")


def reset() -> Any:
    """Remove the stored document, serving the generated one again."""
    try:
        tk.get_action("apidocs_schema_delete")(_action_context(), {})
    except tk.ObjectNotFound:
        tk.h.flash_error(tk._("There is no stored API documentation schema."))
    else:
        helpers.invalidate_cache()
        tk.h.flash_success(
            tk._("The API documentation schema will be generated again.")
        )

    return tk.redirect_to(f"{ADMIN_BP}.index")


def generated() -> Response:
    """The document generated from the registered actions, as JSON."""
    return Response(
        _dump(helpers.build_openapi_spec()), mimetype="application/json"
    )


def format_definition() -> Any:
    """Parse a JSON or YAML document and return it as pretty printed JSON.

    The document is returned with its object keys in alphabetical order, i.e.
    in the form it is stored in, so an editor can normalize pasted YAML
    before it is saved.
    """
    try:
        definition = parse_definition(tk.request.form.get("definition", ""))
    except InvalidDefinition as err:
        return Response(
            json.dumps({"errors": err.errors}),
            status=400,
            mimetype="application/json",
        )

    return Response(
        _dump(canonical_definition(definition)), mimetype="application/json"
    )


def _dump(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False)


bp.add_url_rule("/", endpoint="index", view_func=index)
bp.add_url_rule("/save", endpoint="save", view_func=save, methods=["POST"])
bp.add_url_rule("/reset", endpoint="reset", view_func=reset, methods=["POST"])
bp.add_url_rule("/generated", endpoint="generated", view_func=generated)
bp.add_url_rule(
    "/format", endpoint="format", view_func=format_definition, methods=["POST"]
)
