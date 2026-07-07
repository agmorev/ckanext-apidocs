from typing import Any, Dict

import ckan
import ckan.plugins.toolkit as tk

from ckanext.apidocs import config, utils

APITOKEN_HEADER = tk.config.get("apitoken_header_name", "Authorization")
CKAN_VERSION = ckan.__version__.rsplit('.', 1)[0]
OPENAPI_VERSION = config.apidocs_openapi_version()


schemas: Dict[str, Any] = {
    "APIToken": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "example": "rD7p2jJ7tLXtudlv0cO9BBjPLBwSXG4-WrEwGlGJUc0"
            },
            "name": {
                "type": "string",
                "example": "testapi"
            },
            "user_id": {
                "type": "string",
                "example": "11928daa-1864-4fe9-9571-91155db317d2"
            },
            "created_at": {
                "type": "string",
                "example": "2026-01-03T20:59:47.740897"
            },
            "last_access": {
                "type": "string",
                "example": "null"
            }
        },
    },
}


spec: Dict[str, Any] = {
    "openapi": OPENAPI_VERSION,
    "info": {
        "title": "CKAN API",
        "description": f"""This is the API documentation for CKAN. CKAN’s Action API is a powerful, 
            RPC-style API that exposes all of CKAN’s core features to API clients. All of a CKAN 
            website’s core functionality (everything you can do with the web interface and more) 
            can be used by external code that calls the CKAN API.
            It provides the option of using the [OpenAPI](https://spec.openapis.org/oas/{OPENAPI_VERSION}) 
            and developed on top of the [Swagger UI](https://github.com/swagger-api/swagger-ui).""",
        "version": CKAN_VERSION,
    },
    "externalDocs": {
        "description": "Find out more about CKAN API",
        "url": f"https://docs.ckan.org/en/{CKAN_VERSION}/api/index.html#api-guide"
    },
    "servers": [{"url": config.apidocs_base_path()}],
    "tags": [
        {
            "name": method["name"],
            "description": method["description"],
            "externalDocs": {
                "description": "Find out more",
                "url": f"https://docs.ckan.org/en/{CKAN_VERSION}/api/index.html#module-ckan.logic.action.{method['name']}"
            }
        }
        for method in utils.get_api_methods()
        if method.get("name")
    ],
    "paths": {},
    "components": {
        "schemas": schemas,
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": APITOKEN_HEADER,
                "description": """Paste your CKAN API key here (found on your user profile). 
                    The key will be sent in the Authorization header without any prefix.""",
            }
        },
    },
}


operation: Dict[str, Any] = {
    "tags": [],
    "summary": "",
    "x-badges": [],
    "description": "",
    "responses": {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "help": {"type": "string"},
                            "success": {"type": "boolean"},
                            "result": {"type": "object"},
                        },
                    },
                },
            },
        },
    },
}
