"""Tests for the MCP server (``aperisolve_mcp``).

No Redis, no Docker, no network: the HTTP layer is an ``httpx.MockTransport``
that records every outbound request, and the quota store is the ``limits``
in-memory backend, mirroring what ``tests/conftest.py`` does for the web app's
own limiter (``RATELIMIT_STORAGE_URI=memory://``).

Tools are driven through ``MCPServer.call_tool``, which is the same dispatch
path a real client reaches over either transport: it validates the arguments
against the published input schema and converts the return value, so these
tests fail if the public tool contract drifts, not only if the body breaks.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest
from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from mcp.types import ImageContent
from PIL import Image as PILImage

from aperisolve.config import MAX_CONTENT_LENGTH
from aperisolve_mcp.__main__ import _parse_args, max_request_body_size
from aperisolve_mcp.client import AperiSolveClient
from aperisolve_mcp.limits import RATE_LIMITED_CODE, ToolLimiter, client_ip
from aperisolve_mcp.server import UNTRUSTED, build_server, public_base_url

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from mcp.server.mcpserver import MCPServer
    from mcp.types import CallToolResult

HASH = "d" * 32
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "mcp_results.json").read_text())

EXPECTED_TOOLS = [
    "analyze",
    "get_status",
    "wait_until_done",
    "get_info",
    "list_results",
    "get_tool_output",
    "download_extracted",
    "get_layer_image",
]

# A 1x1 PNG is not enough to test downscaling; this one is built per test.
SMALL_B64 = base64.b64encode(b"a tiny file").decode()


class Recorder:
    """An httpx transport that answers the AperiSolve routes and logs requests."""

    def __init__(self, *, archive: bytes = b"7z-archive", image: bytes | None = None) -> None:
        """Record requests and answer them from the canned fixtures."""
        self.requests: list[httpx.Request] = []
        self._archive = archive
        self._image = image if image is not None else _png(8, 8)
        self.status = "completed"

    def transport(self) -> httpx.MockTransport:
        """Build the transport to hand to ``AperiSolveClient``."""
        return httpx.MockTransport(self)

    def __call__(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911
        """Answer one request, recording it first (one return per route)."""
        self.requests.append(request)
        path = request.url.path
        if path == "/upload":
            return httpx.Response(200, json={"submission_hash": HASH})
        if path == f"/status/{HASH}":
            return httpx.Response(200, json={"status": self.status})
        if path == f"/infos/{HASH}":
            return httpx.Response(200, json={"size": 11, "kind": "image", "names": ["a.png"]})
        if path == f"/result/{HASH}":
            return httpx.Response(200, json={"results": FIXTURE})
        if path.startswith(f"/download/{HASH}/"):
            return httpx.Response(200, content=self._archive)
        if path.startswith(f"/image/{HASH}/"):
            return httpx.Response(200, content=self._image)
        return httpx.Response(404, json={"error": "Not found"})

    @property
    def paths(self) -> list[str]:
        """Return the paths of every request made so far, in order."""
        return [str(request.url.path) for request in self.requests]


def _png(width: int, height: int) -> bytes:
    """Encode a blank PNG of the given size."""
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), (1, 2, 3)).save(buffer, format="PNG")
    return buffer.getvalue()


def _png_with_declared_size(width: int, height: int) -> bytes:
    """Build a tiny PNG whose header declares a huge size; the IDAT is junk.

    Mirrors `tests/test_hardening.py`'s helper of the same purpose: Pillow
    reads dimensions from the header before decoding any pixel data, so this
    is enough to drive the pixel-ceiling and decompression-bomb guards
    without actually allocating the declared size.
    """

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">II5B", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00"))
        + chunk(b"IEND", b"")
    )


def ctx(forwarded_for: str | None = None, peer: str | None = None) -> Context[Any, Any]:
    """Build a request context carrying the headers an HTTP transport populates.

    ``session`` is never touched by these tools, so the dataclass gets ``None``
    rather than a real ``ServerSession``: a tool that started using the session
    would fail here loudly, which is the intent.
    """
    headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    request = SimpleNamespace(
        headers=headers,
        client=SimpleNamespace(host=peer) if peer else None,
    )
    return Context(
        request_context=ServerRequestContext(
            session=cast("Any", None),
            lifespan_context={},
            protocol_version="2025-06-18",
            method="tools/call",
            request=request,
        ),
    )


def build(
    recorder: Recorder | None = None,
    *,
    limiter: ToolLimiter | None = None,
) -> tuple[MCPServer[Any], Recorder, AperiSolveClient]:
    """Build a server wired to a recording transport and an in-memory limiter."""
    rec = recorder if recorder is not None else Recorder()
    client = AperiSolveClient("http://web:5000", transport=rec.transport())
    server = build_server(
        client=client,
        limiter=limiter if limiter is not None else ToolLimiter("memory://"),
    )
    return server, rec, client


def run(coro: Callable[[], Awaitable[Any]]) -> Any:  # noqa: ANN401 -- whatever the coro returns
    """Run one coroutine factory on a fresh event loop.

    The suite has no async plugin (no pytest-asyncio in the dev extra), so each
    test owns its loop. A factory rather than a coroutine keeps construction
    inside the loop, which ``httpx.AsyncClient`` requires.
    """
    return asyncio.run(coro())


def structured(result: CallToolResult) -> dict[str, Any]:
    """Return the structured payload of a successful tool call."""
    assert result.is_error is False, result.content
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def failure(call: Callable[[], Awaitable[Any]]) -> str:
    """Run a tool call expected to fail, returning the message the model sees.

    ``MCPServer.call_tool`` raises ``ToolError`` for an anticipated failure;
    the protocol kernel above it is what turns that into an ``is_error`` result
    carrying this message. Asserting on the message is therefore asserting on
    what the model reads.
    """
    with pytest.raises(ToolError) as excinfo:
        run(call)
    return str(excinfo.value)


# --------------------------------------------------------------------------- #
# Tool surface
# --------------------------------------------------------------------------- #


def test_every_tool_is_registered_with_the_documented_schema() -> None:
    """The eight tools exist with the inputs docs/mcp.md publishes."""

    async def go() -> list[Any]:
        server, _, client = build()
        tools = await server.list_tools()
        await client.aclose()
        return tools

    tools = run(go)
    assert [tool.name for tool in tools] == EXPECTED_TOOLS
    schemas = {tool.name: tool.input_schema for tool in tools}
    assert sorted(schemas["analyze"]["properties"]) == [
        "deep",
        "file_base64",
        "filename",
        "password",
    ]
    assert schemas["analyze"]["required"] == ["file_base64", "filename"]
    assert sorted(schemas["get_tool_output"]["properties"]) == ["hash", "limit", "offset", "tool"]
    assert sorted(schemas["get_layer_image"]["properties"]) == ["hash", "max_side", "name"]


def test_analyze_takes_no_url_input() -> None:
    """Fetching a user-supplied URL server-side is SSRF surface the web API lacks."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        tools = {tool.name: tool.input_schema for tool in await server.list_tools()}
        await client.aclose()
        return tools

    schemas = run(go)
    for name, schema in schemas.items():
        assert not [key for key in schema.get("properties", {}) if "url" in key.lower()], name


def test_every_tool_description_marks_its_output_untrusted() -> None:
    """A model must be told analyzer output is data from an attacker's file."""

    async def go() -> list[Any]:
        server, _, client = build()
        tools = await server.list_tools()
        await client.aclose()
        return tools

    for tool in run(go):
        assert UNTRUSTED in (tool.description or ""), tool.name


# --------------------------------------------------------------------------- #
# Route mapping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("tool", "arguments", "method", "path"),
    [
        ("analyze", {"file_base64": SMALL_B64, "filename": "a.png"}, "POST", "/upload"),
        ("get_status", {"hash": HASH}, "GET", f"/status/{HASH}"),
        ("wait_until_done", {"hash": HASH}, "GET", f"/status/{HASH}"),
        ("get_info", {"hash": HASH}, "GET", f"/infos/{HASH}"),
        ("list_results", {"hash": HASH}, "GET", f"/result/{HASH}"),
        ("get_tool_output", {"hash": HASH, "tool": "strings"}, "GET", f"/result/{HASH}"),
        (
            "download_extracted",
            {"hash": HASH, "tool": "steghide"},
            "GET",
            f"/download/{HASH}/steghide",
        ),
        (
            "get_layer_image",
            {"hash": HASH, "name": "Red_bit_0.png"},
            "GET",
            f"/image/{HASH}/Red_bit_0.png",
        ),
    ],
)
def test_tool_calls_its_route(
    tool: str,
    arguments: dict[str, Any],
    method: str,
    path: str,
) -> None:
    """Each tool is 1:1 with the route it wraps in aperisolve/app.py."""

    async def go() -> Recorder:
        server, rec, client = build()
        await server.call_tool(tool, arguments, context=ctx("198.51.100.7"))
        await client.aclose()
        return rec

    rec = run(go)
    assert rec.paths == [path]
    assert rec.requests[0].method == method


def test_outbound_requests_forward_the_end_client_ip() -> None:
    """``/upload``'s own 10/min must bind the agent's user, not this container.

    The web app reads the rightmost ``X-Forwarded-For`` hop
    (``aperisolve/utils/utils.py:12``), so the header is set to exactly that
    one address rather than appended to the inbound chain.
    """

    async def go() -> Recorder:
        server, rec, client = build()
        inbound = "203.0.113.9, 198.51.100.4"
        await server.call_tool(
            "analyze",
            {"file_base64": SMALL_B64, "filename": "a.png"},
            context=ctx(inbound),
        )
        await server.call_tool("list_results", {"hash": HASH}, context=ctx(inbound))
        await client.aclose()
        return rec

    rec = run(go)
    assert len(rec.requests) == 2
    for request in rec.requests:
        assert request.headers["X-Forwarded-For"] == "198.51.100.4"


def test_client_ip_takes_the_rightmost_hop() -> None:
    """Same rule as ``get_client_ip()``: the leftmost hop is client-forgeable."""
    assert client_ip({"X-Forwarded-For": "1.1.1.1, 2.2.2.2, 3.3.3.3"}) == "3.3.3.3"
    assert client_ip({"x-forwarded-for": " 9.9.9.9 "}) == "9.9.9.9"
    assert client_ip({}, peer="10.0.0.1") == "10.0.0.1"
    assert client_ip(None) == ""


def test_upload_forwards_filename_password_and_deep() -> None:
    """The multipart body carries exactly what ``/upload`` reads."""

    async def go() -> Recorder:
        server, rec, client = build()
        await server.call_tool(
            "analyze",
            {
                "file_base64": SMALL_B64,
                "filename": "secret.png",
                "password": "hunter2",
                "deep": True,
            },
            context=ctx("198.51.100.7"),
        )
        await client.aclose()
        return rec

    body = run(go).requests[0].content
    assert b'name="image"; filename="secret.png"' in body
    assert b"hunter2" in body
    assert b'name="deep"' in body
    assert b"true" in body


# --------------------------------------------------------------------------- #
# Index and paging
# --------------------------------------------------------------------------- #


def test_list_results_carries_no_output_payload() -> None:
    """The index is the point: it must stay small enough to always be safe to call."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool("list_results", {"hash": HASH}, context=ctx("1.2.3.4"))
        await client.aclose()
        return structured(result)

    payload = run(go)
    blob = json.dumps(payload)
    assert "line-00" not in blob
    assert "created with GIMP" not in blob
    assert "Red_bit_0.png" not in blob
    assert "command timed out" not in blob

    rows = {row["tool"]: row for row in payload["tools"]}
    assert sorted(rows) == sorted(FIXTURE)
    assert sorted(rows["strings"]) == [
        "has_download",
        "image_count",
        "output_units",
        "size_bytes",
        "status",
        "tool",
    ]
    assert rows["strings"]["has_download"] is True
    assert rows["strings"]["output_units"] == 7
    assert rows["decomposer"]["has_download"] is False
    assert rows["decomposer"]["image_count"] == 3
    assert rows["pcrt"]["image_count"] == 1
    assert rows["binwalk"]["status"] == "error"
    assert rows["strings"]["size_bytes"] == len(
        json.dumps(FIXTURE["strings"], separators=(",", ":")).encode(),
    )


@pytest.mark.parametrize(
    ("offset", "limit", "expected"),
    [
        (0, 3, ["line-00", "line-01", "line-02"]),
        (3, 3, ["line-03", "line-04", "line-05"]),
        (6, 3, ["line-06"]),
        (7, 3, []),
        (2, 1, ["line-02"]),
        (0, 7, [f"line-{index:02d}" for index in range(7)]),
    ],
)
def test_get_tool_output_paging_is_exact_on_a_list(
    offset: int,
    limit: int,
    expected: list[str],
) -> None:
    """Paging a list output slices elements, and ``total`` is the element count."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool(
            "get_tool_output",
            {"hash": HASH, "tool": "strings", "offset": offset, "limit": limit},
            context=ctx("1.2.3.4"),
        )
        await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload["output"] == expected
    assert payload["output_kind"] == "lines"
    assert payload["total"] == 7
    assert payload["offset"] == offset
    assert payload["limit"] == limit
    assert payload["note"] == FIXTURE["strings"]["note"]
    assert payload["has_download"] is True


def test_get_tool_output_pages_a_string_output_by_lines() -> None:
    """``file`` stores one string; a page is a line of it, not a slice of chars."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool(
            "get_tool_output",
            {"hash": HASH, "tool": "file", "offset": 1, "limit": 1},
            context=ctx("1.2.3.4"),
        )
        await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload["total"] == 3
    assert payload["output_kind"] == "lines"
    assert payload["output"] == ["resolution (DPI), density 72x72"]


def test_get_tool_output_pages_a_mapping_output_by_fields() -> None:
    """``exiftool`` stores a mapping; a page is a subset of its keys."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool(
            "get_tool_output",
            {"hash": HASH, "tool": "exiftool", "offset": 1, "limit": 2},
            context=ctx("1.2.3.4"),
        )
        await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload["output_kind"] == "fields"
    assert payload["total"] == 5
    assert payload["output"] == {"Image Width": "640", "Image Height": "480"}


def test_get_tool_output_exposes_the_image_names_to_pass_to_get_layer_image() -> None:
    """Without this the layer-image tool has no discoverable input."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool(
            "get_tool_output",
            {"hash": HASH, "tool": "decomposer"},
            context=ctx("1.2.3.4"),
        )
        await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload["images"] == {
        "Red": ["Red_bit_0.png", "Red_bit_1.png"],
        "Green": ["Green_bit_0.png"],
    }
    assert payload["total"] == 0


def test_get_tool_output_reports_an_error_entry_without_pretending_to_have_output() -> None:
    """A failed analyzer returns its error, not an empty success."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        result = await server.call_tool(
            "get_tool_output",
            {"hash": HASH, "tool": "binwalk"},
            context=ctx("1.2.3.4"),
        )
        await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload["status"] == "error"
    assert payload["error"] == FIXTURE["binwalk"]["error"]
    assert payload["output"] == []
    assert payload["total"] == 0


def test_get_tool_output_on_an_unknown_tool_lists_what_is_available() -> None:
    """A wrong tool name must cost the agent one call, not a guessing loop."""

    async def go() -> CallToolResult:
        server, _, client = build()
        try:
            return await server.call_tool(
                "get_tool_output",
                {"hash": HASH, "tool": "nope"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    message = failure(go)
    assert "nope" in message
    assert "exiftool" in message


# --------------------------------------------------------------------------- #
# analyze input validation
# --------------------------------------------------------------------------- #


def test_analyze_rejects_oversize_base64_before_any_http_call() -> None:
    """The decoded size is checked here so the upload is never attempted."""
    oversize = base64.b64encode(b"\x00" * (MAX_CONTENT_LENGTH + 1024)).decode()

    seen = Recorder()

    async def go() -> object:
        server, _, client = build(seen)
        try:
            return await server.call_tool(
                "analyze",
                {"file_base64": oversize, "filename": "big.bin"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert "too large" in failure(go).lower()
    assert seen.requests == []


@pytest.mark.parametrize("payload", ["", "not base64!!", "aGVsbG8"])
def test_analyze_rejects_a_payload_that_is_not_valid_base64(payload: str) -> None:
    """Malformed input fails loudly at the tool, never as a confusing 400."""
    seen = Recorder()

    async def go() -> object:
        server, _, client = build(seen)
        try:
            return await server.call_tool(
                "analyze",
                {"file_base64": payload, "filename": "a.png"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert failure(go)
    assert seen.requests == []


# --------------------------------------------------------------------------- #
# Quotas
# --------------------------------------------------------------------------- #


def _analyze_many(count: int, ips: list[str]) -> MCPError | None:
    """Call ``analyze`` ``count`` times over ``ips``, returning the first 429."""

    async def go() -> MCPError | None:
        server, _, client = build()
        try:
            for index in range(count):
                try:
                    await server.call_tool(
                        "analyze",
                        {"file_base64": SMALL_B64, "filename": "a.png"},
                        context=ctx(ips[index % len(ips)]),
                    )
                except MCPError as exc:
                    return exc
        finally:
            await client.aclose()
        return None

    return run(go)


def test_the_sixth_analyze_in_a_minute_from_one_ip_is_rate_limited() -> None:
    """Per-IP `analyze` is 5/min: the sixth call gets the structured 429."""
    exc = _analyze_many(6, ["203.0.113.5"])
    assert exc is not None
    assert exc.code == RATE_LIMITED_CODE
    assert exc.data == {"error": "rate_limited", "bucket": "analyze", "retry_after_s": 60}
    assert "retry in 60s" in exc.message.lower()


def test_the_first_five_analyze_calls_in_a_minute_are_not_limited() -> None:
    """The negative control: the limit must not fire one call early."""
    assert _analyze_many(5, ["203.0.113.6"]) is None


def test_the_hundred_and_twenty_first_analyze_in_an_hour_from_any_ip_is_limited() -> None:
    """The global ceiling is the compute circuit breaker: 120/hour, all clients.

    Every call comes from a different IP, so the per-IP quota (5/min, 30/hour)
    never fires and only the shared counter can reject the 121st.
    """
    ips = [f"198.18.{index // 256}.{index % 256}" for index in range(121)]
    assert _analyze_many(120, ips[:120]) is None

    exc = _analyze_many(121, ips)
    assert exc is not None
    assert exc.code == RATE_LIMITED_CODE
    assert exc.data["error"] == "rate_limited"
    assert exc.data["bucket"] == "analyze"
    assert 0 < exc.data["retry_after_s"] <= 3600


def test_read_tools_have_their_own_quota_and_are_not_spent_by_analyze() -> None:
    """An agent that exhausted `analyze` can still read the results it has."""

    async def go() -> dict[str, Any]:
        server, _, client = build()
        try:
            for _ in range(5):
                await server.call_tool(
                    "analyze",
                    {"file_base64": SMALL_B64, "filename": "a.png"},
                    context=ctx("203.0.113.8"),
                )
            result = await server.call_tool(
                "list_results",
                {"hash": HASH},
                context=ctx("203.0.113.8"),
            )
        finally:
            await client.aclose()
        return structured(result)

    assert run(go)["hash"] == HASH


class BrokenLimiter(ToolLimiter):
    """A limiter whose store is down, to pin the fail-open/fail-closed split."""

    async def _enforce(self, bucket: str, scopes: object) -> None:
        _ = bucket, scopes
        msg = "redis is unreachable"
        raise ConnectionError(msg)


def test_analyze_fails_closed_when_the_quota_store_is_unreachable() -> None:
    """An unmetered public analyze endpoint is worse than an unavailable one."""

    async def go() -> MCPError | None:
        server, rec, client = build(limiter=BrokenLimiter("memory://"))
        try:
            try:
                await server.call_tool(
                    "analyze",
                    {"file_base64": SMALL_B64, "filename": "a.png"},
                    context=ctx("1.2.3.4"),
                )
            except MCPError as exc:
                assert rec.requests == []
                return exc
        finally:
            await client.aclose()
        return None

    exc = run(go)
    assert exc is not None
    assert exc.code == RATE_LIMITED_CODE
    assert exc.data["bucket"] == "analyze"


def test_read_tools_fail_open_when_the_quota_store_is_unreachable() -> None:
    """Reads cost one proxied call and the web app still limits them per IP."""

    async def go() -> dict[str, Any]:
        server, _, client = build(limiter=BrokenLimiter("memory://"))
        try:
            result = await server.call_tool(
                "get_status",
                {"hash": HASH},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()
        return structured(result)

    assert run(go)["status"] == "completed"


# --------------------------------------------------------------------------- #
# wait_until_done, downloads, images
# --------------------------------------------------------------------------- #


def test_wait_until_done_returns_as_soon_as_the_status_is_terminal() -> None:
    """One tool call instead of one per second of analysis."""

    async def go() -> dict[str, Any]:
        server, rec, client = build()
        rec.status = "error"
        try:
            result = await server.call_tool(
                "wait_until_done",
                {"hash": HASH, "timeout_s": 120},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()
        assert len(rec.requests) == 1
        return structured(result)

    assert run(go) == {"status": "error", "timed_out": False}


def test_wait_until_done_reports_a_timeout_without_failing_the_call() -> None:
    """A still-running analysis is not an error: the agent can call again."""

    async def go() -> dict[str, Any]:
        server, rec, client = build()
        rec.status = "running"
        try:
            result = await server.call_tool(
                "wait_until_done",
                {"hash": HASH, "timeout_s": 1},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()
        return structured(result)

    payload = run(go)
    assert payload == {"status": "running", "timed_out": True}


def test_download_extracted_returns_the_archive_as_base64() -> None:
    """Small archives are inlined so the agent never needs a browser."""

    async def go() -> dict[str, Any]:
        server, _, client = build(Recorder(archive=b"PK-not-really-but-bytes"))
        try:
            result = await server.call_tool(
                "download_extracted",
                {"hash": HASH, "tool": "steghide"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()
        return structured(result)

    payload = run(go)
    assert base64.b64decode(payload["content_base64"]) == b"PK-not-really-but-bytes"
    assert payload["filename"] == "steghide.7z"
    assert payload["size_bytes"] == len(b"PK-not-really-but-bytes")


def test_download_extracted_refuses_an_oversize_archive_and_gives_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Above the cap, with a public base URL configured, the agent gets one."""
    monkeypatch.setenv("MCP_PUBLIC_BASE_URL", "https://aperisolve.example")
    oversize = b"\x00" * (3 * 1024 * 1024)

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(archive=oversize))
        try:
            return await server.call_tool(
                "download_extracted",
                {"hash": HASH, "tool": "foremost"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    message = failure(go)
    assert f"{public_base_url()}/download/{HASH}/foremost" in message
    assert str(len(oversize)) in message


def test_download_extracted_oversize_omits_the_hint_with_no_public_base_url() -> None:
    """Stock .env.example (no public base URL): no internal hostname leaks."""
    assert public_base_url() == ""
    oversize = b"\x00" * (3 * 1024 * 1024)

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(archive=oversize))
        try:
            return await server.call_tool(
                "download_extracted",
                {"hash": HASH, "tool": "foremost"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    message = failure(go)
    assert "web:5000" not in message
    assert "Download it directly" not in message
    assert str(len(oversize)) in message


def test_get_layer_image_downscales_to_max_side() -> None:
    """A 40-plane decomposition must be readable without burning the context."""

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(image=_png(1600, 900)))
        try:
            return await server.call_tool(
                "get_layer_image",
                {"hash": HASH, "name": "Red_bit_0.png", "max_side": 256},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    result = run(go)
    assert result.is_error is False
    block = result.content[0]
    assert isinstance(block, ImageContent)
    assert block.mime_type == "image/png"
    with PILImage.open(io.BytesIO(base64.b64decode(block.data))) as img:
        assert max(img.size) == 256
        assert img.size == (256, 144)


def test_get_layer_image_leaves_a_small_image_alone() -> None:
    """Upscaling would invent pixels; the cap is a ceiling, not a target."""

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(image=_png(64, 32)))
        try:
            return await server.call_tool(
                "get_layer_image",
                {"hash": HASH, "name": "Red_bit_0.png", "max_side": 1024},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    block = run(go).content[0]
    assert isinstance(block, ImageContent)
    with PILImage.open(io.BytesIO(base64.b64decode(block.data))) as img:
        assert img.size == (64, 32)


def test_get_layer_image_rejects_bytes_that_are_not_an_image() -> None:
    """A 404 HTML page must not be re-encoded into a confident-looking PNG."""

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(image=b"<html>not an image</html>"))
        try:
            return await server.call_tool(
                "get_layer_image",
                {"hash": HASH, "name": "Red_bit_0.png"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert "cannot decode" in failure(go).lower()


def test_get_layer_image_rejects_an_image_above_the_pixel_ceiling() -> None:
    """A legitimate-looking 36 MP plane must be refused, not decoded (ZEL-457 F1).

    36 MP is under the analyzers' own 64 MP cap (a real derived image could be
    this large) and under Pillow's own decompression-bomb threshold, so only
    `_downscale_png`'s own ceiling can be what stops it.
    """

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(image=_png_with_declared_size(6000, 6000)))
        try:
            return await server.call_tool(
                "get_layer_image",
                {"hash": HASH, "name": "Red_bit_0.png"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert "megapixel" in failure(go).lower()


def test_get_layer_image_rejects_a_decompression_bomb_cleanly() -> None:
    """Above Pillow's hard threshold it must not escape as `UnexpectedToolError` (F2)."""

    async def go() -> CallToolResult:
        server, _, client = build(Recorder(image=_png_with_declared_size(20_000, 20_000)))
        try:
            return await server.call_tool(
                "get_layer_image",
                {"hash": HASH, "name": "Red_bit_0.png"},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert "cannot decode" in failure(go).lower()


# --------------------------------------------------------------------------- #
# Path traversal in tool arguments (ZEL-457 F3)
# --------------------------------------------------------------------------- #


def test_path_traversal_in_hash_or_name_never_reaches_the_api() -> None:
    """`..` in `hash`/`name`/`tool` must not steer the outbound request path.

    httpx resolves dot-segments before sending, so without a guard these
    would reach `/upload`, `/infos` or the ungated single-segment
    `/image/<name>` instead of the route each method builds.
    """
    cases = [
        ("get_layer_image", {"hash": HASH, "name": "../deadbeefcafe.png"}),
        ("get_layer_image", {"hash": HASH, "name": "../../upload"}),
        ("get_status", {"hash": "../../infos/" + HASH}),
        ("download_extracted", {"hash": "..", "tool": "../../result/" + HASH}),
        ("get_layer_image", {"hash": "a/b", "name": "x.png"}),
    ]
    for tool, args in cases:
        recorder = Recorder()

        async def go(
            tool: str = tool,
            args: dict[str, str] = args,
            recorder: Recorder = recorder,
        ) -> CallToolResult:
            server, _, client = build(recorder)
            try:
                return await server.call_tool(tool, args, context=ctx("1.2.3.4"))
            finally:
                await client.aclose()

        failure(go)
        assert recorder.requests == [], (tool, args)


# --------------------------------------------------------------------------- #
# API failures
# --------------------------------------------------------------------------- #


def test_an_unknown_hash_is_reported_as_not_found() -> None:
    """A 404 from the API becomes a message the agent can act on."""

    async def go() -> CallToolResult:
        server, _, client = build()
        try:
            return await server.call_tool(
                "get_status",
                {"hash": "0" * 32},
                context=ctx("1.2.3.4"),
            )
        finally:
            await client.aclose()

    assert "not found" in failure(go).lower()


def test_results_not_ready_points_at_wait_until_done() -> None:
    """``/result`` answers 425 until results.json exists."""

    class TooEarly(Recorder):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return httpx.Response(425, json={"error": "Results not ready yet..."})

    async def go() -> CallToolResult:
        server, _, client = build(TooEarly())
        try:
            return await server.call_tool("list_results", {"hash": HASH}, context=ctx("1.2.3.4"))
        finally:
            await client.aclose()

    assert "wait_until_done" in failure(go)


def test_an_unreachable_api_is_reported_as_unreachable() -> None:
    """Pointed at a dead instance, the tool says so instead of hanging."""

    def dead(request: httpx.Request) -> httpx.Response:
        msg = "connection refused"
        raise httpx.ConnectError(msg, request=request)

    async def go() -> CallToolResult:
        client = AperiSolveClient("http://web:5000", transport=httpx.MockTransport(dead))
        server = build_server(client=client, limiter=ToolLimiter("memory://"))
        try:
            return await server.call_tool("get_status", {"hash": HASH}, context=ctx("1.2.3.4"))
        finally:
            await client.aclose()

    assert "cannot reach" in failure(go).lower()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def test_default_transport_is_streamable_http_on_5001_at_mcp() -> None:
    """The hosted shape nginx proxies to, per docs/deploy.md."""
    args = _parse_args([])
    assert args.stdio is False
    # The in-container bind; compose publishes 127.0.0.1:5001 only.
    assert (args.host, args.port, args.path) == ("0.0.0.0", 5001, "/mcp")  # noqa: S104


def test_stdio_flag_selects_the_self_host_transport() -> None:
    """Same server, no port: `python -m aperisolve_mcp --stdio`."""
    assert _parse_args(["--stdio"]).stdio is True


def test_http_body_cap_admits_the_base64_of_a_max_size_upload() -> None:
    """The SDK's own 4 MiB default would reject a legal upload at 3 MiB.

    base64 inflates a file by 4/3, so an instance configured with the
    .env.example value (MAX_CONTENT_LENGTH=3145728) needs more than 4 MiB of
    request body for an `analyze` call that the web app would accept.
    """
    encoded = len(base64.b64encode(b"\x00" * MAX_CONTENT_LENGTH))
    assert max_request_body_size() > encoded
    assert max_request_body_size() >= 4 * 1024 * 1024
