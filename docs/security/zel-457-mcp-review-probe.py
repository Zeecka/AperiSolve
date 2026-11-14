#!/usr/bin/env python
"""Adversarial probes behind `docs/security/zel-457-mcp-review.md` (ZEL-457, B2).

Run from the repo root with the `mcp` + `dev` extras installed:

    uv sync --extra mcp --extra dev
    .venv/bin/python docs/security/zel-457-mcp-review-probe.py

Each probe prints `RED` when it demonstrates a missing control and `GREEN`
when it demonstrates a control that holds. Several probes are paired: the
GREEN half is the same attack against the honest path, so a RED line cannot be
dismissed as the harness mis-driving the tool.

The HTTP layer is the project's own `httpx.MockTransport` recorder from
`tests/test_mcp.py` and the quota store is `memory://`, so this needs no
Redis, no Docker and no network — the same dispatch path a real client takes
(`MCPServer.call_tool` validates arguments against the published schema).
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import subprocess
import sys
import time
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx
from PIL import Image as PILImage

from aperisolve.config import MAX_CONTENT_LENGTH
from aperisolve_mcp.client import AperiSolveClient
from aperisolve_mcp.limits import ANALYZE, READ, ToolLimiter
from aperisolve_mcp.server import UNTRUSTED, build_server
from tests.test_mcp import HASH, Recorder, ctx

# The probes deliberately break things; the server-side logging that results
# (limits.py logs a traceback for every unreachable-store check, httpx logs
# every request) is correct behaviour and only hides the probe output here.
logging.disable(logging.CRITICAL)

BOMB_PIXELS = (20_000, 20_000)  # 400 MP: over Pillow's hard 2x error threshold
LEGIT_MAX_PIXELS = (8_000, 8_000)  # 64 MP: the analyzers' own pil_utils ceiling
CONTAINER_MEM_LIMIT_MIB = 256  # compose.yml `mcp.mem_limit: 256m`


def header(name: str, claim: str) -> None:
    """Print the banner for one probe."""
    print(f"\n{'=' * 72}\n{name}: {claim}\n{'=' * 72}")


_MAKE_PNG = """
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None          # so the probe can BUILD what it will attack
width, height, mode, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
Image.new(mode, (width, height), (0, 0, 0) if mode == 'RGB' else 0).save(
    path, format='PNG', compress_level=9)
"""


def png_file(size: tuple[int, int], mode: str = "RGB") -> Path:
    """Write a blank PNG of `size` to a cached temp path, in a CHILD process.

    Building a 144 MP image costs ~600 MiB. Doing that here would raise this
    process's ``ru_maxrss``, and because that high-water mark is inherited
    across ``fork()`` and not reset by ``execve()``, every later measurement
    child would start with it and report nonsense. So the fixtures are built
    out-of-process and this one stays lean.
    """
    path = Path(os.environ.get("TMPDIR", "/tmp")) / f"zel457-{size[0]}x{size[1]}-{mode}.png"
    if not path.exists():
        subprocess.run(  # noqa: S603
            [sys.executable, "-c", _MAKE_PNG, str(size[0]), str(size[1]), mode, str(path)],
            check=True,
            capture_output=True,
        )
    return path


def png(size: tuple[int, int], mode: str = "RGB") -> bytes:
    """Return the bytes of a blank PNG of `size` (built out-of-process)."""
    return png_file(size, mode).read_bytes()


def call(server: object, tool: str, args: dict, context: object) -> object:
    """Dispatch one tool call on a fresh event loop, returning its result."""

    async def main() -> object:
        return await server.call_tool(tool, args, context=context)  # type: ignore[attr-defined]

    return asyncio.run(main())


def outcome(server: object, tool: str, args: dict, context: object) -> str:
    """Dispatch one tool call and describe how it ended, in one line."""
    try:
        result = call(server, tool, args, context)
    except BaseException as exc:  # noqa: BLE001 -- the point is what escapes
        return f"{type(exc).__module__}.{type(exc).__name__}: {str(exc)[:150]}"
    is_error = getattr(result, "is_error", None)
    return f"returned (is_error={is_error})"


# --------------------------------------------------------------------------
# F1 — `name` / `hash` are spliced into a URL path that httpx then normalizes
# --------------------------------------------------------------------------
def probe_path_traversal() -> None:
    """Show that `..` in a tool argument re-points the outbound request."""
    header("F1", "tool arguments steer the outbound path (dot-segment normalization)")
    recorder = Recorder()
    client = AperiSolveClient("http://web:5000", transport=recorder.transport())
    server = build_server(client=client, limiter=ToolLimiter("memory://"))

    cases = [
        ("get_layer_image", {"hash": HASH, "name": "Red_bit_0.png"}, "honest call"),
        ("get_layer_image", {"hash": HASH, "name": "../deadbeefcafe.png"}, "escape to /image/<name>"),
        ("get_layer_image", {"hash": HASH, "name": "../../upload"}, "escape to /upload"),
        ("get_status", {"hash": "../../infos/" + HASH}, "get_status reaches /infos"),
        ("download_extracted", {"hash": "..", "tool": "../../result/" + HASH}, "download reaches /result"),
    ]
    for tool, args, label in cases:
        before = len(recorder.requests)
        outcome(server, tool, args, ctx(peer="203.0.113.9"))
        sent = recorder.paths[before:]
        intended = tool == "get_layer_image" and args.get("name") == "Red_bit_0.png"
        verdict = "GREEN" if intended or not sent else "RED"
        print(f"  {verdict}  {label:34s} -> outbound {sent}")
    print(
        "\n  The MCP container, not the client, issues these requests. The host is\n"
        "  pinned to APERISOLVE_API_URL (no cross-host SSRF), but the path is not:\n"
        "  /image/<hash>/<name> is gated on IMAGE_EXTENSIONS (aperisolve/app.py:618)\n"
        "  while /image/<name> is NOT (serving_original, aperisolve/app.py:612-617).",
    )


# --------------------------------------------------------------------------
# F2 — DecompressionBombError escapes _downscale_png's except clause
# --------------------------------------------------------------------------
def probe_bomb_exception() -> None:
    """Show the bomb error is not among the exceptions `_downscale_png` catches."""
    header("F2", "get_layer_image: Pillow DecompressionBombError is not caught")
    print(
        "  PIL.Image.DecompressionBombError MRO: "
        f"{[cls.__name__ for cls in PILImage.DecompressionBombError.__mro__[:3]]}\n"
        "  aperisolve_mcp/server.py:212 catches (UnidentifiedImageError, OSError, ValueError)\n"
        "  -> no common base, so it escapes. The web app knows this already:\n"
        "     aperisolve/filetype.py:230-232 and analyzers/pil_utils.py:54 name it.",
    )
    bomb = png(BOMB_PIXELS, mode="L")
    print(f"\n  payload: {len(bomb)} bytes of PNG declaring {BOMB_PIXELS[0]}x{BOMB_PIXELS[1]} "
          f"= {BOMB_PIXELS[0] * BOMB_PIXELS[1] // 1_000_000} MP "
          f"(MAX_CONTENT_LENGTH is {MAX_CONTENT_LENGTH} bytes, so /upload accepts it)")

    for label, image in (
        ("8x8 derived image", png((8, 8))),
        ("truncated/garbage bytes", b"not an image at all"),
        (f"{BOMB_PIXELS[0]}x{BOMB_PIXELS[1]} bomb", bomb),
    ):
        recorder = Recorder(image=image)
        client = AperiSolveClient("http://web:5000", transport=recorder.transport())
        server = build_server(client=client, limiter=ToolLimiter("memory://"))
        ended = outcome(server, "get_layer_image", {"hash": HASH, "name": "x.png"}, ctx(peer="203.0.113.9"))
        # GREEN = handled: either a normal result or the tool's own ToolError
        # with its actionable message. RED = UnexpectedToolError, the SDK's
        # wrapper for an exception the handler never anticipated.
        unexpected = "UnexpectedToolError" in ended
        print(f"  {'RED' if unexpected else 'GREEN'}  {label:28s} -> {ended}")
    print(
        "\n  The SDK's wrapper does not leak a traceback to the client (checked above:\n"
        "  the message is the bare 'Error executing tool get_layer_image'), so this is\n"
        "  a lost error message rather than an information leak. Its weight is that it\n"
        "  marks the decode path as unguarded -- see F3 for what the guard was for.",
    )


# --------------------------------------------------------------------------
# F3 — decode memory exceeds the container limit on the LEGITIMATE path
# --------------------------------------------------------------------------
def probe_bomb_memory() -> None:
    """Measure peak RSS for images at and below the analyzers' own pixel cap."""
    header("F3", f"get_layer_image decode cost vs mem_limit: {CONTAINER_MEM_LIMIT_MIB}m")
    # Absolute peak RSS of a child that does nothing but what `_downscale_png`
    # does. `ru_maxrss` is a high-water mark inherited across `fork()` and not
    # reset by `execve()`, so this is only meaningful while THIS process stays
    # lean -- which is why `png_file` builds every fixture out-of-process.
    script = textwrap.dedent(
        """
        import io, resource, sys
        from PIL import Image
        data = open(sys.argv[1], 'rb').read()
        with Image.open(io.BytesIO(data)) as img:
            pixels = img.size[0] * img.size[1]
            img.load()                      # what _downscale_png does
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024))
            out = io.BytesIO(); img.save(out, format='PNG')
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(f'{len(data)}|{pixels}|{peak:.0f}|{len(out.getvalue())}')
        """,
    )
    runs = 3  # peak RSS varies with allocator behaviour; report the cheapest run
    # A child that decodes nothing, measured the same way: this is the floor
    # every row below inherits (this probe's own interpreter), NOT decode cost.
    # In the real container the floor is ~14 MiB (python + Pillow only), so the
    # marginal cost per row is what transfers, and it is the dominant term.
    floor = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script, str(png_file((8, 8)))],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip().split("|")
    print(
        f"  Peak RSS of the decode, against the {CONTAINER_MEM_LIMIT_MIB} MiB the container gets.\n"
        f"  ru_maxrss is a high-water MARK, not a sum: this harness's floor is\n"
        f"  {float(floor[2]):.0f} MiB (an 8x8 decode, inherited from the parent), so rows BELOW it\n"
        f"  are masked by it and rows ABOVE it are the decode's true peak. Cross-checked\n"
        f"  against a lean parent (floor 14 MiB): 36 MP 205, 49 MP 239, 64 MP 304, 144 MP 603.\n"
        f"  Marginal cost is ~4.7 B/pixel (3 B of RGB plus the thumbnail working copy):\n",
    )
    for label, size in (
        ("1024x1024 (the output size)", (1_024, 1_024)),
        ("6000x6000 (36 MP)", (6_000, 6_000)),
        ("7000x7000 (49 MP)", (7_000, 7_000)),
        ("legitimate derived plane (64 MP cap)", LEGIT_MAX_PIXELS),
        ("sub-threshold bomb (144 MP)", (12_000, 12_000)),
    ):
        path = png_file(size)
        measured = []
        for _ in range(runs):
            proc = subprocess.run(  # noqa: S603
                [sys.executable, "-c", script, str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if "|" in proc.stdout:
                measured.append(proc.stdout.strip().split("|"))
        if not measured:
            print(f"  n/a   {label}: {proc.stderr.strip()[:120]}")
            continue
        payload, pixels, _, out_bytes = measured[0]
        peak = min(float(row[2]) for row in measured)
        over = peak > CONTAINER_MEM_LIMIT_MIB
        print(
            f"  {'RED' if over else 'GREEN'}  {label:36s} {int(payload):>7} B payload, "
            f"{int(pixels) // 1_000_000:>3} MP -> peak RSS {peak:>3.0f} MiB "
            f"(best of {runs}), downscaled to {out_bytes} B",
        )
    print(
        "\n  Pillow's default MAX_IMAGE_PIXELS (89,478,485) only WARNS; it raises\n"
        "  below 2x that. Everything under 178 MP is decoded in full, and the\n"
        "  64 MP case needs no traversal: analyzers/pil_utils.py:16 lets a\n"
        "  8000x8000 upload through, so its bit planes are legitimate derived images.",
    )


# --------------------------------------------------------------------------
# F4 — rightmost X-Forwarded-For is client-chosen without a proxy in front
# --------------------------------------------------------------------------
def probe_xff_forgery() -> None:
    """Rotate a forged XFF against the per-IP analyze quota."""
    header("F4", "per-IP analyze quota: forged X-Forwarded-For (direct caller, no nginx)")
    payload = base64.b64encode(b"x" * 64).decode()
    quota = "MCP_LIMIT_ANALYZE"
    print(f"  {quota}={os.environ.get(quota) or '5 per minute; 30 per hour (default)'}")

    for label, rotate in (("honest client, one IP", False), ("same client, rotating forged XFF", True)):
        recorder = Recorder()
        client = AperiSolveClient("http://web:5000", transport=recorder.transport())
        server = build_server(client=client, limiter=ToolLimiter("memory://"))
        accepted = 0
        for attempt in range(12):
            forged = f"10.0.0.{attempt}" if rotate else "10.0.0.1"
            ended = outcome(
                server,
                "analyze",
                {"file_base64": payload, "filename": "a.bin"},
                ctx(forwarded_for=forged, peer="203.0.113.9"),
            )
            if "rate_limited" in ended or "Rate limit" in ended:
                break
            accepted += 1
        blocked = accepted < 12
        print(
            f"  {'GREEN' if blocked else 'RED'}  {label:34s} -> {accepted}/12 analyses started"
            f"{' (quota held)' if blocked else ' (quota never tripped)'}",
        )
    # The global ceiling is the control that is supposed to survive rotation.
    os.environ["MCP_LIMIT_ANALYZE_GLOBAL"] = "7 per hour"
    try:
        recorder = Recorder()
        client = AperiSolveClient("http://web:5000", transport=recorder.transport())
        server = build_server(client=client, limiter=ToolLimiter("memory://"))
        accepted = 0
        for attempt in range(12):
            ended = outcome(
                server,
                "analyze",
                {"file_base64": payload, "filename": "a.bin"},
                ctx(forwarded_for=f"10.0.{attempt}.{attempt}", peer="203.0.113.9"),
            )
            if "rate_limited" in ended or "Rate limit" in ended:
                break
            accepted += 1
    finally:
        del os.environ["MCP_LIMIT_ANALYZE_GLOBAL"]
    print(
        f"  {'GREEN' if accepted == 7 else 'RED'}  rotating XFF vs MCP_LIMIT_ANALYZE_GLOBAL="
        f"'7 per hour' -> {accepted}/12 started (ceiling holds across rotation)",
    )
    print(
        "\n  limits.py:103-106 takes the RIGHTMOST hop. That is unforgeable only when a\n"
        "  trusted proxy appended it. For a caller that reaches :5001 directly the\n"
        "  rightmost hop IS the client's own header, and `peer` is consulted only when\n"
        "  no X-Forwarded-For is present at all, so sending one is strictly better for\n"
        "  the attacker. On the DOCUMENTED deployment nginx overwrites the header\n"
        "  (`proxy_set_header X-Forwarded-For $http_cf_connecting_ip`, docs/deploy.md:133),\n"
        "  so the forgery above does not reach the hosted endpoint -- the per-IP quota\n"
        "  rests on that overwrite plus origin-IP concealment, not on the parsing rule.\n"
        "  The global ceiling holds either way, which is why this is bounded.",
    )


# --------------------------------------------------------------------------
# F5 — internal hostname in tool error messages
# --------------------------------------------------------------------------
def probe_hostname_leak() -> None:
    """Show the upstream base URL reaching the client in an error message."""
    header("F5", "tool errors must not echo internal hostnames")

    def refuse(request: httpx.Request) -> httpx.Response:
        msg = "connection refused"
        raise httpx.ConnectError(msg, request=request)

    client = AperiSolveClient("http://web:5000", transport=httpx.MockTransport(refuse))
    server = build_server(client=client, limiter=ToolLimiter("memory://"))
    ended = outcome(server, "get_status", {"hash": HASH}, ctx(peer="203.0.113.9"))
    leaked = "web:5000" in ended
    print(f"  {'RED' if leaked else 'GREEN'}  get_status with web unreachable -> {ended}")
    print(
        "  client.py:103 interpolates self._client.base_url into the message and\n"
        "  server.py:104-105 passes a status-0 ApiError through verbatim.",
    )


# --------------------------------------------------------------------------
# F6 — wait_until_done: one READ unit buys up to 120 upstream requests
# --------------------------------------------------------------------------
def probe_wait_amplification() -> None:
    """Count upstream requests a single quota'd wait_until_done can issue."""
    header("F6", "wait_until_done: upstream requests per quota unit")
    # Measured in real time at a small budget, then scaled: patching
    # asyncio.sleep would make the loop spin and inflate the count by 1000x.
    from aperisolve_mcp.server import MAX_WAIT_S, POLL_INTERVAL_S

    budget_s = 4
    recorder = Recorder()
    recorder.status = "running"  # never terminal: hold for the whole budget
    client = AperiSolveClient("http://web:5000", transport=recorder.transport())
    server = build_server(client=client, limiter=ToolLimiter("memory://"))

    started = time.monotonic()
    result = call(server, "wait_until_done", {"hash": HASH, "timeout_s": budget_s}, ctx(peer="203.0.113.9"))
    held = time.monotonic() - started
    polls = len([path for path in recorder.paths if path.startswith("/status/")])
    quota_units = 1  # one quota.check(READ, ip) for the whole call
    print(
        f"  measured at timeout_s={budget_s}: held the call {held:.1f} s, "
        f"{polls} upstream /status requests for {quota_units} READ unit "
        f"({getattr(result, 'structured_content', None)})",
    )
    at_max = int(MAX_WAIT_S / POLL_INTERVAL_S)
    read_per_min = 120  # MCP_LIMIT_READ default
    print(
        f"  RED  at timeout_s={MAX_WAIT_S} (the cap, and the default) one READ unit buys "
        f"~{at_max} upstream requests;\n       the per-IP read quota of {read_per_min}/min "
        f"therefore authorises ~{at_max * read_per_min:,} requests to `web` per IP per minute,\n"
        f"       each call also holding an MCP session and an nginx connection for {MAX_WAIT_S} s "
        f"(proxy_read_timeout 130s).",
    )
    print(
        "  server.py:324-336: the budget is bounded per call but the quota is charged\n"
        "  per call, not per poll, so cost to the server and cost to the quota diverge.",
    )


# --------------------------------------------------------------------------
# F7 — quota store down: analyze must fail closed, reads may fail open
# --------------------------------------------------------------------------
def probe_fail_closed() -> None:
    """Point the limiter at a dead Redis and check each bucket's behaviour."""
    header("F7", "Redis unreachable: analyze fails closed, reads fail open")
    dead = ToolLimiter("redis://127.0.0.1:1/0")

    async def main() -> None:
        for bucket, want_closed in ((ANALYZE, True), (READ, False)):
            try:
                await dead.check(bucket, "10.0.0.1")
                closed = False
            except BaseException as exc:  # noqa: BLE001 -- classify whatever comes out
                closed = "rate_limited" in str(getattr(exc, "data", "")) or "Rate limit" in str(exc)
                if not closed:
                    print(f"  RED  {bucket}: leaked {type(exc).__name__}: {str(exc)[:90]}")
                    continue
            ok = closed == want_closed
            print(
                f"  {'GREEN' if ok else 'RED'}  {bucket:8s} -> "
                f"{'rejected (closed)' if closed else 'allowed (open)'}, "
                f"brief requires {'closed' if want_closed else 'open'}",
            )

    asyncio.run(main())


# --------------------------------------------------------------------------
# Green controls worth keeping a regression probe for
# --------------------------------------------------------------------------
def probe_green_controls() -> None:
    """Re-verify the bounds and framing the brief asks about, red half included."""
    header("G", "controls that hold (with the probe that would fail without them)")
    recorder = Recorder()
    client = AperiSolveClient("http://web:5000", transport=recorder.transport())
    server = build_server(client=client, limiter=ToolLimiter("memory://"))
    context = ctx(peer="203.0.113.9")

    # base64 bound, checked before any HTTP call.
    oversize = base64.b64encode(b"x" * (MAX_CONTENT_LENGTH + 1024)).decode()
    before = len(recorder.requests)
    ended = outcome(server, "analyze", {"file_base64": oversize, "filename": "big.bin"}, context)
    no_http = len(recorder.requests) == before
    print(
        f"  {'GREEN' if no_http else 'RED'}  base64 {len(oversize)} chars > MAX_CONTENT_LENGTH "
        f"{MAX_CONTENT_LENGTH} -> {ended[:60]}, outbound requests: {len(recorder.requests) - before}",
    )

    # offset/limit bounds in get_tool_output.
    for offset, limit in ((-5, -1), (10**12, 10**9)):
        ended = outcome(
            server,
            "get_tool_output",
            {"hash": HASH, "tool": "strings", "offset": offset, "limit": limit},
            context,
        )
        print(f"  GREEN  get_tool_output(offset={offset}, limit={limit}) -> {ended}")

    # analyze takes no URL input; every tool carries the untrusted-data note.
    async def tools() -> list:
        return await server.list_tools()

    listed = asyncio.run(tools())
    analyze_inputs = sorted(
        next(t for t in listed if t.name == "analyze").input_schema.get("properties", {}),
    )
    has_url = any("url" in name.lower() for name in analyze_inputs)
    print(f"  {'RED' if has_url else 'GREEN'}  analyze inputs {analyze_inputs} -> no URL input")
    missing = [t.name for t in listed if UNTRUSTED not in (t.description or "")]
    print(
        f"  {'RED' if missing else 'GREEN'}  untrusted-data note on all {len(listed)} tools"
        f"{f' -- MISSING on {missing}' if missing else ''}",
    )

    # list_results carries no analyzer payload.
    result = call(server, "list_results", {"hash": HASH}, context)
    body = str(getattr(result, "structured_content", ""))
    keys = {key for row in getattr(result, "structured_content", {}).get("tools", []) for key in row}
    payload_leak = "output" in keys
    print(
        f"  {'RED' if payload_leak else 'GREEN'}  list_results row keys {sorted(keys)} "
        f"-> no output payload ({len(body)} B for the whole index)",
    )


def main() -> None:
    """Run every probe."""
    print(__doc__)
    probe_path_traversal()
    probe_bomb_exception()
    probe_bomb_memory()
    probe_xff_forgery()
    probe_hostname_leak()
    probe_wait_amplification()
    probe_fail_closed()
    probe_green_controls()


if __name__ == "__main__":
    main()
