"""Shared pytest fixtures.

The environment must be configured before any ``aperisolve`` import:
``aperisolve.config`` reads environment variables at import time.
"""

import os

os.environ.setdefault("DB_URI", "sqlite://")
os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
# Loopback fails instantly (connection refused) instead of hanging on DNS.
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/0")

import pytest
from flask import Flask
from flask.testing import FlaskClient

from aperisolve.app import create_app
from aperisolve.models import db


@pytest.fixture
def app() -> Flask:
    """Flask application backed by an in-memory database."""
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for the application."""
    return app.test_client()
