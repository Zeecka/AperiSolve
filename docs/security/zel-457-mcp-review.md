# ZEL-457 (B2) — security review of `aperisolve_mcp`

Independent review of the public MCP endpoint built in ZEL-456 (B1).
Reviewed tip: `d8817e8` (`ZEL-456-zel-441-b1-aperisolve_mcp-public-mcp-server-over-the-aperisolve-api-track-b-build`),
diffed against the release base `922102e` (3.8.0). Scope: `aperisolve_mcp/`
(limiter, base64/image bounds, SSRF surface, the eight tool handlers, auth and
edge assumptions) plus the `mcp` compose service.

## Ship verdict

**ship-with-fixes**

Nothing found lets a client read private data, change server state, reach a
host other than the configured API, or escape the container. The endpoint is
genuinely a client of the public HTTP API, as the package docstring claims, and
the quota design holds where it matters: the global `analyze` ceiling survives
IP rotation and `analyze` fails closed when the quota store is down. Both of
those are measured below, not assumed.

What needs fixing before this is public is one unguarded image decode in a
256 MiB container (F1/F2 — the same missing pixel guard the web app's own
`analyzers/pil_utils.py` already implements), the outbound path being
steerable by tool arguments (F3), and two spots that echo the internal
hostname to clients, which the brief forbids outright (F4).

## Reproducing

```
uv sync --extra mcp --extra dev
.venv/bin/python docs/security/zel-457-mcp-review-probe.py
```

`docs/security/zel-457-mcp-review-probe.py` (committed alongside this file)
prints `RED` for a missing control and `GREEN` for one that holds. Findings
that claim a control is absent are paired with the same probe against the
honest path, so a `RED` cannot be an artefact of the harness mis-driving the
tool. It needs no Redis, no Docker and no network: the HTTP layer is the
project's own `httpx.MockTransport` recorder from `tests/test_mcp.py` and the
quota store is `memory://`. Calls go through `MCPServer.call_tool`, the same
dispatch a real client reaches.

Baseline before the review: `.venv/bin/python -m pytest tests/test_mcp.py -q`
→ `49 passed`.

F1's kill was then confirmed on the artefact that actually ships, by running
the exact body of `_downscale_png` inside the published image under the
service's own memory limit:

```
docker run --rm -m 256m --memory-swap 256m --entrypoint python \
  -v /tmp/zel457-docker:/fix:ro ghcr.io/zeecka/aperisolve:latest \
  /fix/incontainer.py /fix/zel457-8000x8000-RGB.png
```

`/fix/incontainer.py` is that function body verbatim; the PNG fixtures are the
ones the probe writes to `$TMPDIR`.

## Findings

### F1 — `get_layer_image` decodes a full-size image inside a 256 MiB container, OOM-killing it — high (availability; blast radius confined to the `mcp` container)

`aperisolve_mcp/server.py:208` (`img.load()` before the `thumbnail` on :209),
reached from `server.py:496`. `_downscale_png` has no pixel ceiling, so the
decode cost is set by the *input* dimensions, not by `max_side`.

The web app caps analyzer input at 64 MP (`aperisolve/analyzers/pil_utils.py:16`,
`MAX_IMAGE_PIXELS = 64_000_000`). A derived image at exactly that cap is a
legitimate, non-malicious analyzer output — and decoding one already exceeds
the container's `mem_limit: 256m` (`compose.yml`). Host peak RSS by input size
(probe F3, mode RGB):

```
  GREEN  6000x6000 (36 MP)                     104898 B payload,  36 MP -> peak RSS 205 MiB
  GREEN  7000x7000 (49 MP)                     142765 B payload,  49 MP -> peak RSS 238 MiB
  RED  legitimate derived plane (64 MP cap)  186433 B payload,  64 MP -> peak RSS 303 MiB
  RED  sub-threshold bomb (144 MP)           419406 B payload, 144 MP -> peak RSS 603 MiB
```

An **186 KB** upload is enough; the budget is spent between 49 and 64 MP.
Marginal cost is ~4.7 B/pixel (3 B of RGB plus the thumbnail working copy).

**Confirmed on the shipped image, not inferred.** Running the exact body of
`_downscale_png` inside `ghcr.io/zeecka/aperisolve:latest` under the service's
own limit (`docker run -m 256m --memory-swap 256m`, same Pillow 13.0.0, same
default `MAX_IMAGE_PIXELS`):

```
6000x6000 RGB (36 MP)   -> SURVIVED -> 3129 B       exit=0
7000x7000 RGB (49 MP)   -> SURVIVED -> 3129 B       exit=0
8000x8000 RGB (64 MP)   -> killed                   exit=137  <-- the analyzers' own cap
12000x12000 RGB (144 MP)-> killed                   exit=137
20000x20000 L (400 MP)  -> DecompressionBombError   exit=1    <-- F2, in the real image
```

```
$ docker inspect --format '{{.State.OOMKilled}} {{.State.ExitCode}}' zel457oom
true 137
```

**Which derived images are the vector**, by pixel mode at the 64 MP cap:

```
8000x8000 mode=L    exit=0   survived     <- decomposer bit planes (decomposer.py:82), 1 B/px
8000x8000 mode=RGB  exit=137 OOM-KILLED   <- decomposer superimposed (decomposer.py:65), 3 B/px
8000x8000 mode=RGBA exit=137 OOM-KILLED   <- color_remapping (color_remapping.py:60), 4 B/px
```

So the individual bit planes — the common case the tool docstring describes —
are safe at the cap. The vector is the **superimposed and colour-remapped
images**, which the same analyzers produce at full original dimensions and
which `list_results` advertises in the same `images` map.

Consequence: the `mcp` container is OOM-killed by one `get_layer_image` call on
a legitimate derived plane. `restart: always` brings it back, so this is a
repeatable interruption rather than a permanent outage, and it does not touch
`web`, the worker or the database. But every tool call in flight dies with it,
the `HEAVY` quota allows 30 attempts per minute per IP, and the cost to the
attacker is one 186 KB upload plus one tool call — no bomb, no traversal, no
forged header.

The 144 MP row needs F3 to be reachable (the analyzers refuse to produce a
derived image that large); the 64 MP row needs nothing but a legitimate
8000x8000 upload.

**Fix**: set a pixel ceiling before `load()` the way `pil_utils.py:41` does,
and use `img.draft()` so Pillow downscales during JPEG decode rather than
after. A ceiling of ~16 MP is still four times the 1024px output.

### F2 — `DecompressionBombError` escapes the `except` clause in `_downscale_png` — low

`aperisolve_mcp/server.py:212` catches `(UnidentifiedImageError, OSError, ValueError)`.
`PIL.Image.DecompressionBombError` inherits directly from `Exception`:

```
  PIL.Image.DecompressionBombError MRO: ['DecompressionBombError', 'Exception', 'BaseException']
  GREEN  truncated/garbage bytes      -> ToolError: Cannot decode that image: cannot identify image file
  RED  20000x20000 bomb             -> UnexpectedToolError: Error executing tool get_layer_image
```

Above Pillow's hard threshold (2 × `MAX_IMAGE_PIXELS` = 178,956,970 px) the
client gets the SDK's generic `UnexpectedToolError` instead of the tool's own
actionable message. **No traceback or internal path reaches the client** — the
message is the bare `Error executing tool get_layer_image` — so this is a lost
error message, not an information leak, which is why it is low on its own. Its
weight is as the marker of F1: this is precisely the exception the guard would
have raised. The project already knows the quirk and names it twice:
`aperisolve/filetype.py:230-232` and `aperisolve/analyzers/pil_utils.py:54`.

**Fix**: add `PILImage.DecompressionBombError` to the tuple, with F1's ceiling.

### F3 — `hash`, `name` and `tool` steer the outbound request path — medium

`aperisolve_mcp/client.py:158` (`f"/image/{hash_val}/{name}"`) and the same
pattern at `client.py:133`, `:137`, `:145`, `:154`. The arguments are
interpolated into a URL path, and httpx resolves dot-segments before sending:

```
  GREEN  honest call                        -> outbound ['/image/dddd..dddd/Red_bit_0.png']
  RED  escape to /image/<name>            -> outbound ['/image/deadbeefcafe.png']
  RED  escape to /upload                  -> outbound ['/upload']
  RED  get_status reaches /infos          -> outbound ['/infos/dddd..dddd']
  RED  download reaches /result           -> outbound ['/result/dddd..dddd']
```

**What bounds this**: the host is pinned to `APERISOLVE_API_URL` and is not
client-influenceable, so there is no cross-host SSRF — only the path moves.
Every tool but `analyze` issues `GET`, and `analyze` posts to a constant
`/upload`, so no state-changing route (`/remove/<hash>`, POST-only) is
reachable. Most reachable routes are already public to any browser.

**What does not bound it**: `/image/<hash>/<name>` is gated on
`IMAGE_EXTENSIONS` (`aperisolve/app.py:618`) while the single-segment
`/image/<name>` is deliberately **not** — `serving_original` at
`aperisolve/app.py:612-617` serves "any stored file type". Traversing to it
bypasses that gate and hands `_downscale_png` an *original upload*, which is
subject to no pixel cap at all. That is what makes F1's 144 MP row (603 MiB,
2.4× the container limit) reachable. The attacker knows the path without any
disclosure: it is `md5(<their own file>)`.

**Fix**: reject or `posixpath.basename()` the path components. `name` is
documented as a basename already (`server.py:485`), and `hash` is a hex digest.

### F4 — tool errors echo the internal hostname `http://web:5000` — low

The brief requires that tool errors not echo internal hostnames. Two sites do:

```
  RED  get_status with web unreachable -> ToolError: Error executing tool get_status:
       Cannot reach the AperiSolve API at http://web:5000: connection refused
```

1. `aperisolve_mcp/client.py:103` interpolates `self._client.base_url` into the
   message, and `server.py:104-105` passes a status-0 `ApiError` through
   verbatim. Any upstream connect failure or timeout discloses it.
2. `public_base_url()` (`server.py:82`) falls back to `api_url()` when both
   `MCP_PUBLIC_BASE_URL` and `SITE_BASE_URL` are empty — which is the **stock
   `.env.example`**, where `SITE_BASE_URL=` is blank. Every oversize-archive
   error then hands the model an internal URL it cannot use:

```
  2097153 B archive -> ToolError: Archive is 2097153 bytes, above the 2097152-byte
       inline cap. Download it directly: http://web:5000/download/dddd..dddd/binwalk
```

Low severity: it discloses a compose service name and port on an internal
network, no credential and no reachable address. But it is cheap to fix and
the brief asks for it explicitly.

**Fix**: a fixed string for the unreachable case (the status-0 branch at
`server.py:104` already has the right shape — just do not interpolate the
URL), and suppress the hint in (2) when no public base URL is configured.

### F5 — the per-IP quota rests on nginx's header overwrite, not on the rightmost-hop rule — low (documentation)

`aperisolve_mcp/limits.py:103-106` takes the rightmost `X-Forwarded-For` hop,
documented as "the only value the client cannot forge". That is true only when
a trusted proxy appended it. For a caller that reaches `:5001` directly, the
rightmost hop *is* the client's own header, and `peer` is consulted only when
no `X-Forwarded-For` is present at all — so sending one is strictly better for
the attacker:

```
  GREEN  honest client, one IP              -> 5/12 analyses started (quota held)
  RED  same client, rotating forged XFF   -> 12/12 analyses started (quota never tripped)
  GREEN  rotating XFF vs MCP_LIMIT_ANALYZE_GLOBAL='7 per hour' -> 7/12 started
```

**On the documented deployment this does not reach the endpoint**: nginx sets
`proxy_set_header X-Forwarded-For $http_cf_connecting_ip` (`docs/deploy.md:133`),
overwriting whatever the client sent, and the port is published
loopback-only. The forged header also propagates to the web app's own limiter
(`aperisolve/utils/utils.py:22-25`, same rule), so where it does apply it
defeats layers 2 and 3 together — bounded by the global ceiling, which holds.
The residual exposure is a self-hoster who publishes `:5001`, or anyone who
reaches the origin directly with a forged `CF-Connecting-IP`. So the per-IP
quota depends on that overwrite plus origin-IP concealment, which is worth
saying out loud rather than resting on the parsing rule.

**Fix**: documentation. `docs/mcp.md` should warn that publishing the port
beyond loopback without a header-normalising proxy makes the per-IP quotas
advisory. Optionally key on `peer` when it is not a known-proxy address.

### F6 — `wait_until_done` charges one read unit for ~120 upstream polls — low

`aperisolve_mcp/server.py:324-336`. Measured at `timeout_s=4`: 4 upstream
`/status` requests for one `READ` unit. At the default and maximum
`timeout_s=120` that is ~120 upstream requests per quota unit, each call also
holding an MCP session and an nginx connection for 120 s
(`proxy_read_timeout 130s`).

**What bounds it**: the web app's own `@limiter.limit("240 per minute")` on
`/status` (`aperisolve/app.py:499`) applies, because `is_local_request`
requires a loopback `remote_addr` (`aperisolve/limits.py:12`) and the MCP
container reaches `web` over the `backend` bridge network — so the exemption
does not fire and the polls are charged to the forwarded client IP. Layer 3
absorbs this at ~2 concurrent full-length waits per IP. That verifies the
layering claim in `limits.py:11-12`, and is why this is low rather than an
amplification finding.

**Fix**: optional. Charging a read unit per poll, or keeping a per-IP cap on
concurrent waits, would make the quota reflect the cost instead of relying on
layer 3.

## Controls verified as holding

Each line is a control the brief asked about, with the probe that would fail
if it were absent.

- **base64 bound before any HTTP** — `server.py:121` checks the encoded length
  (4 chars per 3 bytes) before decoding and `:132` re-checks the decoded
  length. A 1,399,468-char payload against `MAX_CONTENT_LENGTH` 1,048,576 is
  rejected with **0 outbound requests**. The encoded pre-check is sound:
  `validate=True` rejects non-alphabet characters, so the length is a multiple
  of 4 and `len // 4 * 3` is a true upper bound. Quota is consumed before
  validation (`server.py:272`), which is the right order — validation cannot
  skip past the limiter.
- **`offset` / `limit` bounds** — `get_tool_output(offset=-5, limit=-1)` and
  `(offset=10**12, limit=10**9)` both return normally; clamped at
  `server.py:420-421`.
- **No URL input on `analyze`** — published input schema is exactly
  `['deep', 'file_base64', 'filename', 'password']`.
- **`APERISOLVE_API_URL` not client-influenceable** — environment only
  (`client.py:48`); no tool argument reaches the host or scheme. See F3 for the
  path, which is a different matter.
- **Untrusted-data framing on all 8 tools** — enforced structurally by the
  `_register` decorator (`server.py:185-200`), so a tool cannot be added
  without it; verified against the live `list_tools()` output.
- **`list_results` carries no payload** — row keys are exactly
  `['has_download', 'image_count', 'output_units', 'size_bytes', 'status', 'tool']`;
  866 B for the whole index.
- **`analyze` fails closed, reads fail open, with the store down** — probed
  against a dead Redis; `analyze` → `rate_limited`, `read` → allowed, as the
  brief requires (`limits.py:148-158`).
- **Global `analyze` ceiling holds across rotating IPs** — with
  `MCP_LIMIT_ANALYZE_GLOBAL='7 per hour'`, 7 of 12 rotated-IP calls start. This
  is the compute circuit breaker and it is the control that survives F5.
- **`download_extracted` cap** — 2 MiB default; an oversize archive is refused
  rather than inlined (the message leaks the URL, see F4).
- **`filename` is not a multipart injection vector** — httpx percent-encodes
  `"` and CRLF in the filename parameter (`filename="a%0D%0AContent-Disposition: ..."`),
  so no extra form field can be injected. The web app also derives the stored
  name from content, not the supplied string (`aperisolve/app.py:409-416`,
  `_normalize_extension`, GHSA-m5f8-qc9j-mc55).
- **Compose** — `mcp` carries `<<: *default-hardening` (`cap_drop: [ALL]`,
  `no-new-privileges:true`, `read_only: true`), `mem_limit: 256m`, `cpus: 0.5`,
  `pids_limit: 128`, `logging: *default-logging`; port published as
  `127.0.0.1:5001:5001`; networks exactly `frontend` + `backend`; **no
  `env_file: .env`** and no `DB_URI`/`POSTGRES_PASSWORD` (secrets diet holds);
  every `MCP_*` variable optional, so a stock `docker compose up` with the
  shipped `.env.example` needs none of them (`aperisolve_mcp/__init__.py:21-31`
  treats an empty value as unset, which is what makes that true).

## Open / uncertain

- **Streamable-HTTP session accounting** is the SDK's, not this package's. I
  did not measure whether many half-open sessions grow memory without bound
  before `mem_limit` bites. Settling check: run the `mcp` container under
  `docker stats` while opening a few hundred sessions that never complete.
- **Redis outage leaves reads fully unmetered.** MCP reads fail open (by
  design) *and* the web app's limiter has `swallow_errors=True`
  (`aperisolve/limits.py:21`), so layer 3 fails open on the same store at the
  same moment. nginx `limit_req` is the only remaining limit on read tools
  during an outage. Deliberate on both sides, but the two failure-open
  decisions compose into something neither comment mentions.
- **F1 is settled** (observed `OOMKilled=true` in the shipped image), but I
  proved it on `_downscale_png` in isolation rather than by driving a live
  `mcp` service end to end over HTTP. The remaining unknown is only whether a
  real derived plane from the decomposer is RGB (3 B/px, as measured) or a
  narrower mode for some analyzers, which would move the threshold up. It does
  not change the finding: `color_remapping` output is RGB, and the 144 MP case
  clears any mode. Settling check: `docker compose up mcp`, `analyze` an
  8000x8000 PNG, then `get_layer_image` on a plane from its `list_results`.
