# flake8: noqa: E203,E501,W503
# pylint: disable=W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Sentry initialization for Aperisolve."""

import os

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

SENTRY_DSN = os.environ.get("SENTRY_DSN")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


def initialize_sentry() -> None:
    """Initialize Sentry SDK once, safely."""

    # No DSN → do nothing
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return

    # Prevent double initialization (Flask + RQ, CLI, tests, etc.)
    if sentry_sdk.Hub.current.client is not None:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
            RqIntegration(),
            ThreadingIntegration(propagate_hub=True),
        ],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(
            os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
        ),
        environment=os.environ.get("ENVIRONMENT", "development"),
        release=os.environ.get("SENTRY_RELEASE", "1.0.0"),
        send_default_pii=False,
        enable_tracing=True,
    )
