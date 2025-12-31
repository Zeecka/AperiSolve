# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Aperi'Solve WSGI runner."""

from .app import app as application

if __name__ == "__main__":
    application.run()
