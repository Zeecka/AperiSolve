"""Shared rate limiter, importable by app and blueprints without cycles."""

from flask import request
from flask_limiter import Limiter

from .config import RATELIMIT_STORAGE_URI
from .utils.utils import get_client_ip


def is_local_request() -> bool:
    """Report whether the client is loopback (healthcheck is never limited)."""
    return request.remote_addr in ("127.0.0.1", "::1")


# No default limits: pages, static files and images are never throttled.
# Explicit per-route limits protect the expensive endpoints only.
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=RATELIMIT_STORAGE_URI,
    default_limits=[],
    swallow_errors=True,  # a limiter/Redis outage must not take uploads down
)
