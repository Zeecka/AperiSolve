"""Async HTTP client for the AperiSolve web API.

One method per route the MCP tools expose, no business logic: status codes and
payload shapes are the web app's contract, and this module only transports
them. Keeping the service on HTTP (rather than importing the Flask app or
reading the results volume) is what makes it runnable against any instance and
keeps `/upload`'s own validation and rate limits in force.

Every request carries the end client's IP as ``X-Forwarded-For`` so the web
app's ``get_client_ip()`` (``aperisolve/utils/utils.py:12``, rightmost hop)
attributes the call to the agent's user rather than to this container. The
header is *set*, never appended to: the web app takes the rightmost hop, and
this service is the only proxy between the agent and the app.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import env_int, env_str

DEFAULT_API_URL = "http://web:5000"

# Generous enough for /upload on a 1 MiB file plus the enqueue, short enough
# that a wedged web container fails a tool call instead of hanging the agent.
DEFAULT_TIMEOUT_S = 30


class ApiError(Exception):
    """An AperiSolve HTTP call that failed, carrying the status and the message.

    Raised for any non-2xx response. ``status`` is 0 when the request never got
    an HTTP reply at all (DNS, connect, timeout), which the tools report
    differently from a 4xx the agent can fix.
    """

    def __init__(self, status: int, message: str) -> None:
        """Build the error from an HTTP status (0 = no reply) and a message."""
        super().__init__(message)
        self.status = status
        self.message = message


def api_url() -> str:
    """Return the base URL of the AperiSolve instance this service talks to."""
    return env_str("APERISOLVE_API_URL", DEFAULT_API_URL).rstrip("/")


def api_timeout_s() -> int:
    """Return the per-request timeout for calls to the AperiSolve instance."""
    return env_int("MCP_API_TIMEOUT_S", DEFAULT_TIMEOUT_S)


def _path_segment(value: str, label: str) -> str:
    """Reject anything that is not a single, literal path segment.

    ``hash``, ``name`` and ``tool`` are spliced straight into the outbound
    request path below, and httpx resolves ``.``/``..`` segments before
    sending. A value containing a separator or a dot-segment could steer the
    request to a different route than the one each method builds (ZEL-457
    F3) — e.g. a crafted ``name`` reaching ``/upload`` or the ungated
    ``/image/<name>``. Rejecting outright, rather than only stripping with
    ``posixpath.basename()``, is what also catches a bare ``".."``, which
    ``basename()`` leaves unchanged.
    """
    if not value or "/" in value or value in {".", ".."}:
        msg = f"{label} must be a single path segment, not {value!r}"
        raise ApiError(0, msg)
    return value


class AperiSolveClient:
    """Thin async wrapper over the AperiSolve HTTP routes used by the tools."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout_s: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Build a client against ``base_url`` (default ``APERISOLVE_API_URL``).

        ``transport`` exists for the tests, which drive the tools against an
        ``httpx.MockTransport`` so the suite needs no network and no stack.
        """
        self._client = httpx.AsyncClient(
            base_url=base_url if base_url is not None else api_url(),
            timeout=float(timeout_s if timeout_s is not None else api_timeout_s()),
            transport=transport,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        """Release the underlying connection pool."""
        await self._client.aclose()

    @staticmethod
    def _headers(client_ip: str) -> dict[str, str]:
        """Headers forwarding the end client's IP to the web app."""
        return {"X-Forwarded-For": client_ip} if client_ip else {}

    async def _request(
        self,
        method: str,
        path: str,
        client_ip: str,
        **kwargs: Any,  # noqa: ANN401 -- passed straight through to httpx
    ) -> httpx.Response:
        """Perform a request and turn any failure into ``ApiError``."""
        try:
            response = await self._client.request(
                method,
                path,
                headers=self._headers(client_ip),
                **kwargs,
            )
        except httpx.HTTPError as exc:
            # Fixed string: `self._client.base_url` is the internal compose
            # hostname (e.g. `http://web:5000`), which a tool error must not
            # echo to the client (ZEL-457 F4).
            msg = f"Cannot reach the AperiSolve API: {exc}"
            raise ApiError(0, msg) from exc
        if response.is_success:
            return response
        raise ApiError(response.status_code, _error_message(response))

    async def upload(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        password: str | None,
        deep: bool,
        client_ip: str,
    ) -> dict[str, Any]:
        """POST /upload — enqueue an analysis, returning ``{"submission_hash": ...}``."""
        form = {"deep": "true" if deep else "false"}
        if password:
            form["password"] = password
        response = await self._request(
            "POST",
            "/upload",
            client_ip,
            files={"image": (filename, file_bytes)},
            data=form,
        )
        return _as_dict(response)

    async def status(self, hash_val: str, client_ip: str) -> dict[str, Any]:
        """GET /status/<hash> — ``{"status": "pending"|"running"|"completed"|"error"}``."""
        hash_val = _path_segment(hash_val, "hash")
        return _as_dict(await self._request("GET", f"/status/{hash_val}", client_ip))

    async def infos(self, hash_val: str, client_ip: str) -> dict[str, Any]:
        """GET /infos/<hash> — file metadata, names and passwords tried."""
        hash_val = _path_segment(hash_val, "hash")
        return _as_dict(await self._request("GET", f"/infos/{hash_val}", client_ip))

    async def results(self, hash_val: str, client_ip: str) -> dict[str, Any]:
        """GET /result/<hash> — the ``{tool: result}`` mapping, unwrapped.

        The route answers 425 while ``results.json`` does not exist yet, which
        surfaces as ``ApiError(425, ...)``.
        """
        hash_val = _path_segment(hash_val, "hash")
        payload = _as_dict(await self._request("GET", f"/result/{hash_val}", client_ip))
        results = payload.get("results")
        if not isinstance(results, dict):
            msg = "The AperiSolve API returned no results object"
            raise ApiError(502, msg)
        return results

    async def download(self, hash_val: str, tool: str, client_ip: str) -> bytes:
        """GET /download/<hash>/<tool> — the raw ``<tool>.7z`` archive bytes."""
        hash_val = _path_segment(hash_val, "hash")
        tool = _path_segment(tool, "tool")
        response = await self._request("GET", f"/download/{hash_val}/{tool}", client_ip)
        return response.content

    async def image(self, hash_val: str, name: str, client_ip: str) -> bytes:
        """GET /image/<hash>/<name> — the raw bytes of one derived image."""
        hash_val = _path_segment(hash_val, "hash")
        name = _path_segment(name, "name")
        response = await self._request("GET", f"/image/{hash_val}/{name}", client_ip)
        return response.content


def _as_dict(response: httpx.Response) -> dict[str, Any]:
    """Decode a JSON object body, or fail loudly rather than return a half-value."""
    try:
        payload = response.json()
    except ValueError as exc:
        msg = f"The AperiSolve API returned a non-JSON body for {response.url.path}"
        raise ApiError(502, msg) from exc
    if not isinstance(payload, dict):
        msg = f"The AperiSolve API returned {type(payload).__name__}, expected an object"
        raise ApiError(502, msg)
    return payload


def _error_message(response: httpx.Response) -> str:
    """Best-effort human message for a non-2xx response.

    The app answers errors as ``{"error": ...}`` for JSON routes and as an HTML
    error page for ``abort()``; fall back to the status phrase rather than
    paste a page of markup into a tool result.
    """
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = payload.get("error")
        if isinstance(message, str) and message:
            return message
    return f"HTTP {response.status_code} from {response.url.path}"
