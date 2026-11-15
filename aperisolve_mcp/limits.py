"""Per-IP and global quotas for the MCP tools.

The endpoint is public and anonymous, like the website, so quotas are the only
thing standing between one agent in a retry loop and the worker pool. Three
layers protect it and this module is the middle one:

1. nginx ``limit_req`` on ``location /mcp/`` (see ``docs/deploy.md``) absorbs
   floods before Python sees them.
2. **this module**: per-tool-class quotas keyed on the client IP, plus a global
   ``analyze`` ceiling across all clients as the compute circuit breaker.
3. the web app's own ``@limiter.limit`` decorators, which still apply because
   ``AperiSolveClient`` forwards the end client's IP as ``X-Forwarded-For``.

Built on ``limits`` — the storage layer Flask-Limiter already runs in this
image — against the same Redis DB 1 the web app uses for
``RATELIMIT_STORAGE_URI``, so MCP and website quotas share one store and one
password. Every number is an ``MCP_*`` environment variable
(``.env.example``); none of them is required.
"""

from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING

from limits import parse_many
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string
from mcp.shared.exceptions import MCPError

from . import env_str

if TYPE_CHECKING:
    from collections.abc import Mapping

    from limits import RateLimitItem

logger = logging.getLogger(__name__)

# Implementation-defined JSON-RPC server error (-32000..-32099 is reserved for
# exactly this). `MCPError` is passed through unchanged by the tool dispatcher,
# so `data` reaches the client intact and an agent can read `retry_after_s`
# instead of retrying blind.
RATE_LIMITED_CODE = -32010

# Default quotas. `analyze` enqueues a job that runs ~16 analyzers at
# `cpus: 2`; the global ceiling bounds agent-triggered load to roughly one job
# every 30s at peak, whatever the number of distinct clients.
DEFAULT_ANALYZE = "5 per minute; 30 per hour"
DEFAULT_ANALYZE_GLOBAL = "120 per hour"
DEFAULT_HEAVY = "30 per minute"
DEFAULT_READ = "120 per minute"

# Mirrors `RATELIMIT_STORAGE_URI` in aperisolve/config.py (Redis DB 1, kept
# apart from the RQ queue on DB 0). `async+` selects the asyncio storage: these
# tools are async and must not block the event loop on a socket read.
DEFAULT_STORAGE_URI = "redis://redis:6379/1"
_ASYNC_PREFIX = "async+"

# Quota bucket per tool class. `analyze` is the only one that starts work.
ANALYZE = "analyze"
HEAVY = "heavy"
READ = "read"

# The global `analyze` ceiling is one shared counter, so it needs a key that no
# client IP can collide with.
_GLOBAL_KEY = "all-clients"

# How long to tell a client to back off while the quota store is down. Short
# enough that recovery is picked up quickly, long enough not to hot-loop.
_FAIL_CLOSED_RETRY_S = 30


def rate_limited(bucket: str, retry_after_s: int) -> MCPError:
    """Build the structured error returned to a client over quota."""
    message = (
        f"Rate limit exceeded for the '{bucket}' tool class on this AperiSolve MCP "
        f"endpoint. Retry in {retry_after_s}s."
    )
    return MCPError(
        RATE_LIMITED_CODE,
        message,
        {"error": "rate_limited", "bucket": bucket, "retry_after_s": retry_after_s},
    )


def client_ip(headers: Mapping[str, str] | None, peer: str | None = None) -> str:
    """Client IP for rate limiting: the rightmost ``X-Forwarded-For`` hop.

    Same rule and same reasoning as ``get_client_ip()`` in
    ``aperisolve/utils/utils.py:12``: the rightmost hop is the one appended by
    the closest reverse proxy. Taking the leftmost would let one client
    rotate spoofed IPs past every quota below.

    That rightmost hop is unforgeable only behind a trusted proxy that
    overwrites whatever the client sent — this deployment relies on the
    nginx ``location /mcp/`` block to do that (``docs/deploy.md``, which
    configures it to append ``CF-Connecting-IP``). A caller that reaches this
    service directly controls the rightmost hop itself, same as any other
    header (ZEL-457 F5): rotating ``X-Forwarded-For`` then defeats the per-IP
    quota, bounded only by the global ``analyze`` ceiling. ``peer`` (the
    socket address) is the fallback when no such header is present at all,
    and both are empty on stdio — where the single local user is the only
    client and quotas are a formality.
    """
    forwarded = (headers or {}).get("X-Forwarded-For") or (headers or {}).get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return peer or ""


class ToolLimiter:
    """Quota check for one tool call, keyed on the end client's IP."""

    def __init__(self, storage_uri: str | None = None) -> None:
        """Build a limiter over ``storage_uri`` (default ``MCP_REDIS_URL``).

        Tests pass ``memory://`` so the suite needs no Redis, exactly as
        ``tests/conftest.py`` does for the web app's limiter.
        """
        uri = storage_uri
        if uri is None:
            uri = env_str("MCP_REDIS_URL", DEFAULT_STORAGE_URI)
        if not uri.startswith(_ASYNC_PREFIX):
            uri = _ASYNC_PREFIX + uri
        self._limiter = MovingWindowRateLimiter(storage_from_string(uri))
        self._quotas: dict[str, list[RateLimitItem]] = {
            ANALYZE: parse_many(env_str("MCP_LIMIT_ANALYZE", DEFAULT_ANALYZE)),
            HEAVY: parse_many(env_str("MCP_LIMIT_HEAVY", DEFAULT_HEAVY)),
            READ: parse_many(env_str("MCP_LIMIT_READ", DEFAULT_READ)),
        }
        self._global_analyze = parse_many(
            env_str("MCP_LIMIT_ANALYZE_GLOBAL", DEFAULT_ANALYZE_GLOBAL),
        )

    async def check(self, bucket: str, ip: str) -> None:
        """Consume one unit of ``bucket`` for ``ip``, or raise the 429 error.

        Raises:
            MCPError: quota exhausted; ``data`` carries ``retry_after_s``.

        """
        scopes: list[tuple[str, list[RateLimitItem]]] = [(ip or "unknown", self._quotas[bucket])]
        if bucket == ANALYZE:
            scopes.append((_GLOBAL_KEY, self._global_analyze))

        try:
            await self._enforce(bucket, scopes)
        except MCPError:
            raise
        except Exception:
            # Redis is unreachable (or answering nonsense). `analyze` fails
            # CLOSED: it is the only tool that spends worker CPU, and an
            # unmetered public analyze endpoint is a worse outcome than a
            # temporarily unavailable one. Read tools fail OPEN: they cost one
            # proxied HTTP call, the web app still rate-limits them per IP on
            # its own, and refusing them would take the endpoint down for
            # everyone over a store that is not on the request's critical path.
            logger.exception("MCP rate-limit store unreachable (bucket=%s)", bucket)
            if bucket == ANALYZE:
                raise rate_limited(bucket, _FAIL_CLOSED_RETRY_S) from None

    async def _enforce(self, bucket: str, scopes: list[tuple[str, list[RateLimitItem]]]) -> None:
        """Test every quota before consuming any, then consume them all.

        Testing first means a call rejected by the hourly window does not also
        burn a slot in the per-minute one, so ``retry_after_s`` points at the
        window that actually blocked.
        """
        for key, items in scopes:
            for item in items:
                if not await self._limiter.test(item, bucket, key):
                    stats = await self._limiter.get_window_stats(item, bucket, key)
                    retry_after_s = max(1, math.ceil(stats.reset_time - time.time()))
                    raise rate_limited(bucket, retry_after_s)
        for key, items in scopes:
            for item in items:
                await self._limiter.hit(item, bucket, key)
