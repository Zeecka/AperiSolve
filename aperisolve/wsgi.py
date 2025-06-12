"""Aperi'Solve WSGI runner."""

from .app import app as application

if __name__ == "__main__":
    application.run()
