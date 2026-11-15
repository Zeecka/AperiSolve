"""MCP server exposing the AperiSolve HTTP API to agent clients.

This package is deliberately a *client* of the web API and nothing else: it
never opens the database, the RQ queue or the results volume. Everything it
can do, an anonymous HTTP caller can already do, which keeps the web app the
single enforcement point for validation, storage and retention rules — and
lets the same server run against any AperiSolve instance.

Nothing LLM-related lives here: no API key, no model call, no agent loop. The
agent runs in the client.

Installed by the optional ``mcp`` extra (``pip install -e '.[mcp]'``), so a
self-hosted instance that does not want the endpoint never pulls the deps.
"""

from os import getenv

__all__ = ["env_int", "env_str"]


def env_str(name: str, default: str) -> str:
    """Return a string env var, treating an empty value as unset.

    docker compose substitutes an unset variable into ``environment:`` as an
    empty string, so every ``MCP_*`` knob must fall back to its default rather
    than configure the service with "". This is the same rule
    ``aperisolve.config._int_env`` applies, and it is what keeps a stock
    ``docker compose up`` with the unmodified ``.env.example`` working: none of
    the ``MCP_*`` variables is required.
    """
    return getenv(name) or default


def env_int(name: str, default: int) -> int:
    """Return an integer env var, treating an empty or unparsable value as unset."""
    raw = getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
