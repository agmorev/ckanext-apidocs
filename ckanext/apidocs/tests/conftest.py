"""Shared fixtures for the ckanext-apidocs test suite."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import pytest
from sqlalchemy.exc import DBAPIError, UnboundExecutionError

from ckan import model

from ckanext.apidocs import helpers
from ckanext.apidocs.model import ApidocsSchema


@pytest.fixture
def clean_db(reset_db, migrate_db_for, with_plugins):
    """Clean database, including the tables of this extension.

    ``reset_db`` drops every table it knows about, which includes the tables
    of this extension, so the migrations have to be applied again afterwards.
    They need the plugin to be loaded, hence the ``with_plugins`` dependency
    (which also makes the fixture order independent of the test signatures).
    """
    reset_db()
    migrate_db_for("apidocs")


@pytest.fixture(autouse=True)
def reset_spec_cache():
    """Never let a cached or stored specification leak between tests."""
    helpers.invalidate_cache()
    yield
    helpers.invalidate_cache()
    _delete_stored_schema()


def _delete_stored_schema() -> None:
    """Remove the stored OpenAPI document, if any."""
    try:
        row = ApidocsSchema.get()
    except (DBAPIError, UnboundExecutionError):
        # no database, or the extension tables are not created yet
        model.Session.rollback()
        return

    if row is not None:
        row.delete()


@contextmanager
def _capture_records(logger_name: str) -> Iterator[list[logging.LogRecord]]:
    """Collect the records of a logger, regardless of the root logger setup.

    ``caplog`` cannot be used here: ``logging.config.fileConfig()`` is called
    by CKAN with ``disable_existing_loggers=True``, so loggers created before
    the configuration is applied (as the ones of this extension) are disabled
    and produce no records at all.
    """
    records: list[logging.LogRecord] = []

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger(logger_name)
    was_disabled = logger.disabled
    logger.disabled = False
    handler = Collector(level=logging.DEBUG)
    logger.addHandler(handler)

    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.disabled = was_disabled


@pytest.fixture
def log_capture():
    """Return a context manager collecting the records of a logger."""
    return _capture_records
