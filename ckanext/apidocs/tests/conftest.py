"""Shared fixtures for the ckanext-apidocs test suite."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import pytest

from ckanext.apidocs import helpers


@pytest.fixture(autouse=True)
def reset_spec_cache():
    """Never let a cached specification leak between tests."""
    helpers.invalidate_cache()
    yield
    helpers.invalidate_cache()


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
