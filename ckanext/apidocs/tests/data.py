"""Data shared by the tests of the extension."""

from __future__ import annotations

from typing import Any


#: A minimal but valid OpenAPI document, as stored by a sysadmin.
MINIMAL_SPEC: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "Custom API", "version": "1.2.3"},
    "paths": {
        "/custom_action": {
            "post": {
                "summary": "A custom action",
                "responses": {"200": {"description": "Successful response"}},
            }
        }
    },
}

#: A document with its keys in a deliberately unhelpful order: the order a
#: sysadmin can paste, and the one ``JSONB`` gives back when it is read.
UNSORTED_SPEC: dict[str, Any] = {
    "paths": {
        "/zulu": {
            "post": {
                "summary": "Zulu",
                "responses": {"200": {"description": "Successful response"}},
            }
        },
        "/alpha": {"get": {"summary": "Alpha"}},
    },
    "openapi": "3.0.0",
    "info": {"version": "1.2.3", "title": "Custom API"},
}

#: The keys of :data:`UNSORTED_SPEC` in the canonical order.
UNSORTED_SPEC_KEYS = ["info", "openapi", "paths"]
UNSORTED_SPEC_PATHS = ["/alpha", "/zulu"]
