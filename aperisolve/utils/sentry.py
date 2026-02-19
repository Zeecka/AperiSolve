"""Sentry initialization for Aperisolve."""

import os

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration
from sentry_sdk.utils import BadDsn

SENTRY_DSN = os.environ.get("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "development")
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
SENTRY_RELEASE = os.environ.get("SENTRY_RELEASE", "1.0.0")


def initialize_sentry() -> None:
    """Initialize Sentry SDK once, safely."""
    # No DSN → do nothing
    # Prevent double initialization (Flask + RQ, CLI, tests, etc.)
    if not SENTRY_DSN or sentry_sdk.Hub.current.client is not None:
        return

    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
                RqIntegration(),
                ThreadingIntegration(propagate_hub=True),
            ],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE,
            send_default_pii=False,
            enable_tracing=True,
        )
    except BadDsn:
        sentry_sdk.capture_message("Invalid Sentry DSN configuration", level="warning")
    except RuntimeError as exc:
        sentry_sdk.capture_exception(exc)
