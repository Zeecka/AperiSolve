# Deployment

Production deployment is **tag-driven**. Nothing deploys on a push to
`main`; publishing a git tag does everything.

## Flow

1. Merge work into `main` (CI builds the Docker image on every push as a
   smoke test, but does not publish it).
2. Create and push a tag, e.g.:

   ```console
   $ git tag 3.3.0
   $ git push origin 3.3.0
   ```

3. The `release.yml` workflow then:
   - builds the image and pushes `ghcr.io/zeecka/aperisolve:<tag>` and
     `ghcr.io/zeecka/aperisolve:latest`;
   - SSHes to the production server (`PROD_SSH_*` secrets), regenerates
     `.env` from `.env.example` plus the repository's Actions
     variables/secrets (ports, limits, ads, Sentry, database, ...);
   - runs `docker compose -f compose.yml -f compose.prod.yml
     pull && ... down && ... up -d` (never `down -v`: the volumes hold the
     database and results). The `compose.prod.yml` overlay bind-mounts
     deployment-local site content (see below); self-hosters run the stock
     `compose.yml` alone.

The compose stack runs eight services: `web` (gunicorn), `worker` (RQ),
`cron` (RQ cron scheduler driving the retention cleanup), `initdb`
(one-shot), `postgres`, `redis`, `rqdashboard` bound to
localhost:9181 (reach it via SSH tunnelling), and `sentryproxy` (a tinyproxy
forward proxy allow-listed to the Sentry ingest host only -- see
"RCE containment" below).

### RCE containment (ZEL-442, 3.8.0)

`web`, `worker` and `cron` run as a fixed non-root user (`aperisolve`, uid
10001), with every Linux capability dropped, `no-new-privileges`, an
immutable root filesystem (a `/tmp` tmpfs covers anything that needs to
write), and a `pids_limit`. `worker` and `cron` additionally sit on a
Docker network (`backend`) with `internal: true`: they have no route to the
internet at all except through `sentryproxy`, which is allow-listed to the
Sentry ingest host parsed from `SENTRY_DSN` and nothing else. A popped
analyzer tool (binwalk, jpseek, ...) therefore has no path to root, no other
container's secrets (see the secrets diet below), and no internet egress.

**New required secret**: `REDIS_PASSWORD` -- Redis now runs with
`--requirepass`, and `REDIS_URL`/`RATELIMIT_STORAGE_URI`/
`RQ_DASHBOARD_REDIS_URL` are built from it in `compose.yml` rather than read
from `.env` directly. Add a `REDIS_PASSWORD` repository secret (any
sufficiently random value) before the first deploy of 3.8.0 -- never paste
the value anywhere, including into this file or a task/issue.

**One-time manual step on upgrade** (do NOT run this automatically; it is
for the operator doing the 3.8.0 deploy, once): the `initdb` service now
`chown -R 10001:10001` the `apresults`/`apremoved` volumes and `/app` on
every start (it runs as root briefly, before web/worker/cron start as the
non-root user). On a fresh volume this is instant. On the existing
production `apresults` volume -- which can hold a large number of stored
submissions -- the first `chown -R` after upgrading may take noticeably
longer than `initdb`'s usual sub-second run, which delays `web`/`worker`
coming up (they wait on `initdb`'s `service_completed_successfully`). This
is expected on that first deploy only; it is not a hang.

Known limitation: RQ's cron scheduler (rq 3.0.0) does not honor `rq cron
--serializer` for the jobs it enqueues (confirmed from `rq.cron.CronJob.enqueue`,
which builds its own `Queue()` with no serializer argument), so the shared
`default` queue stays on RQ's default pickle serializer rather than moving to
`JSONSerializer` -- `requirepass` above is the mitigating control for that
queue instead.

## Reverse proxy

The production host runs nginx in front of the stack (it also serves unrelated
vhosts, so port 80 is not the app's to take). `WEB_APP_PORT` is therefore set to
`127.0.0.1:5000`, not a bare port: compose renders it as
`"127.0.0.1:5000:5000"`, so the container is reachable only through nginx, never
directly on the host's public address.

`/etc/nginx/sites-available/aperisolve.conf` serves `aperisolve.com`,
`aperisolve.fr` and both `www.` names from one block, proxying to
`127.0.0.1:5000`. Two details there are load-bearing:

- **`client_max_body_size` must stay above `MAX_CONTENT_LENGTH`.** nginx's 1 MiB
  default would reject valid uploads with its own 413 before the app ever sees
  them.
- **`X-Forwarded-For` is passed through, not appended to.** `get_client_ip()`
  reads the *rightmost* hop, so the usual `$proxy_add_x_forwarded_for` would make
  that hop the Cloudflare edge IP and put every visitor in a single rate-limit
  bucket. The vhost forwards `CF-Connecting-IP` instead, falling back to any
  inbound `X-Forwarded-For`.

TLS terminates at Cloudflare; the origin speaks plain HTTP on :80.

### The `/mcp/` location (MCP endpoint)

The `mcp` compose service publishes `127.0.0.1:5001` and serves the Streamable
HTTP transport at `/mcp` (see `docs/mcp.md` for the tools themselves). It needs
its own `location`, because three of its requirements differ from the app's:
responses stream, one tool blocks for up to two minutes, and the per-IP quota
inside the service reads the same rightmost `X-Forwarded-For` hop the app does.

Declare the shared zone once, in the `http {}` context (`nginx.conf`):

```nginx
# 30 requests/minute per client IP, matching MCP_LIMIT_HEAVY. The MCP server
# enforces per-tool quotas of its own; this only absorbs floods before Python
# sees them.
limit_req_zone $http_cf_connecting_ip zone=mcp:10m rate=30r/m;
```

Then, inside the `aperisolve.conf` server block:

```nginx
location /mcp {
    # No trailing slash on either side, so the URI is passed through
    # unchanged. The server answers only /mcp (measured: POST /mcp is handled,
    # POST /mcp/ 307s to /mcp, POST / is 404), so a `proxy_pass .../;` that
    # rewrote the path to `/` would 404 every request.
    proxy_pass http://127.0.0.1:5001;
    proxy_http_version 1.1;

    # The one redirect the server issues (/mcp/ -> /mcp) is built from the
    # Host header and the origin's plain-HTTP scheme; rewrite it so a client
    # that added the slash is not bounced to http://.
    proxy_redirect http://$host/ https://$host/;

    # Same rule as the main vhost: get_client_ip() and the MCP limiter both
    # read the RIGHTMOST hop, so forward Cloudflare's client IP as that hop
    # rather than using $proxy_add_x_forwarded_for, which would append the
    # edge IP and put every agent in one bucket.
    proxy_set_header X-Forwarded-For $http_cf_connecting_ip;
    proxy_set_header Host $host;

    # Streamable HTTP sends SSE; buffering would hold the stream until it ends.
    proxy_buffering off;
    proxy_cache off;

    # wait_until_done polls for up to 120s (MAX_WAIT_S), so the read timeout
    # must clear it or nginx 504s a tool call that was working correctly.
    proxy_read_timeout 130s;
    proxy_send_timeout 130s;

    # analyze carries the file base64-encoded: 4/3 of MAX_CONTENT_LENGTH plus
    # the JSON-RPC envelope. Keep this above that, as for the main location.
    client_max_body_size 8m;

    limit_req zone=mcp burst=20 nodelay;
}
```

`limit_req` is the outermost of three layers; the other two are the per-IP and
global quotas inside the service, and the web app's own `@limiter.limit`
decorators, which still apply because the MCP service forwards the end client's
IP onward to `web`. See `aperisolve_mcp/limits.py` for the split.

## Configuration

All runtime configuration is environment-driven; `.env.example` documents
every variable. Deploy-time values come from GitHub Actions variables and
secrets — to change a production setting (e.g. `MAX_CONTENT_LENGTH`,
`CUSTOM_EXTERNAL_SCRIPT`, `SITE_BASE_URL`), edit the repository's Actions
configuration and re-deploy with a tag.

## Deployment-local site content

Content that should appear on **aperisolve.com only** — not in the public
Docker image self-hosters pull — lives under `aperisolve/site_content/`.
That directory is:

- **excluded from the image** via `.dockerignore`, so the published
  `ghcr.io/zeecka/aperisolve` image never contains it;
- **bind-mounted read-only on production** via `compose.prod.yml`, which the
  deploy step layers on top of `compose.yml`.

It is committed to git, so the content reaches the server through the deploy
step's `git pull` and stays version-controlled. Self-hosted instances have no
such directory, and every loader in `aperisolve/site_content.py` returns
`None`, so their templates render nothing.

Today it backs a small promo banner on the home and result pages:
`site_content/promo/<lang>.md` (Markdown, English `en.md` fallback). The
rendered HTML is cached per language and re-rendered when the file's mtime
changes, so editing it on the server takes effect on the next request. To add
a prod-only wiki page, standalone route, etc., add a loader here and a matching
content sub-directory.

## Branches

`main` is the only long-lived branch. The historical `prod` branch is
obsolete: its hardcoded AdSense snippet and `/ads.txt` route were replaced
by the `GOOGLE_ADS_TXT`/`CUSTOM_EXTERNAL_SCRIPT` environment variables, and
its `:prod` image tags are no longer built. It can be
deleted; nothing references it.

The old `worker/*` feature branches (`worker/jphide`, `worker/jsteg`,
`worket/color_remap`, `worker/identify_graphicmagick`, `worker/file`) are
fully merged into `main` (0 commits ahead) and can be deleted.

## Local development

```console
$ docker compose -f compose.dev.yml up --build
```

The dev stack mounts `./aperisolve` into the containers and uses
`.env.example` directly. If you change translatable strings, recompile the
gettext catalogs (`pybabel compile -d aperisolve/translations`) since the
mounted source shadows the image's compiled catalogs.
