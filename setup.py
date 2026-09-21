# -*- coding: utf-8 -*-
"""Minimal setup script.

Project metadata, dependencies and entry points are declared in
``pyproject.toml``. This file only keeps Babel's message extractors, which
are not supported by ``pyproject.toml``.
"""

from setuptools import setup


setup(
    message_extractors={
        "ckanext/apidocs": [
            ("**.py", "python", None),
            ("assets/js/apidocs.js", "javascript", None),
            ("templates/**.html", "ckan", None),
        ],
    },
)
