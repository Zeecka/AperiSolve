# Improvement plan (July 2026 audit)

Status of the fixes identified by the 2026-07-28 repo/prod audit. Items are
ordered by priority; check them off as they land. Verification for the
deploy-affecting items happens against https://www.aperisolve.com after the
next tagged release.

## P0 — active data loss / revenue blockers

- [x] **Stop prod DB wipe on every deploy.** The `prod` GitHub environment has
  `CLEAR_AT_RESTART=1`; every tagged deploy runs `initdb` which then does
  `db.drop_all()` and clears the results folder. Flip the environment variable
  to `0`. *(GitHub env config, no code change.)*
- [x] **Safe self-host defaults.** `.env.example` ships `CLEAR_AT_RESTART=1`
  and the README quickstart copies it verbatim, so self-hosters lose all data
  on every restart. Also strip the maintainer's live AdSense client / ads.txt
  values from the example file — self-hosters must opt in with their own IDs.
- [x] **Set `SITE_BASE_URL`** in the prod environment so canonicals/sitemap
  don't depend on the request URL.
- [x] **AdSense**: resolved as *not needed*. Auto ads are enabled in the
  console, so the `CUSTOM_EXTERNAL_SCRIPT` loader (which predates this audit)
  already serves ads and Google handles placement. The manual-unit layer
  (`ADSENSE_SLOT_*`, the `ad_unit` macro and its four call sites) was dead
  configuration and has been removed. Earlier notes in this file claimed the
  site rendered no ads at all — that was wrong: it only ever meant no
  *manual* units rendered.

## P1 — deploy pipeline & robustness

- [x] **Deploy the tag, not `main`.** The server-side deploy script runs a bare
  `git pull`, so compose files/site content come from whatever `main` is at
  deploy time. Check out the pushed tag instead.
- [x] **Gate the deploy on tests.** A tag currently builds, pushes `:latest`
  and deploys with no lint/test gate.
- [x] **Replace `sleep 120`** image-propagation wait with a registry manifest
  poll.
- [x] **Tolerate empty env values.** Unset GitHub variables render as `KEY=`
  lines in the generated `.env`; `int("")` in `config.py` (and `float("")` in
  `utils/sentry.py`) would crash every container at import. Treat empty as
  unset.

## P1 — security

- [x] **Pillow decompression-bomb guard** (`analyzers/pil_utils.py`): images
  above 64 MP are rejected from their declared header dimensions before any
  pixel decoding, as a clean per-analyzer error instead of a silent thread
  death; `filetype.py`'s Pillow probe also survives `DecompressionBombError`
  (it subclasses neither `OSError` nor `ValueError`).
- [x] **Rate-limit `/download` and `/image`** — the only expensive routes
  without a limiter.
- [x] **Baseline security headers** (`X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`) via `after_request`. A strict CSP
  is deferred: it requires moving the inline scripts in `base.html` to nonces
  and adding SRI to the three CDN includes.
- [x] **UploadLog retention**: rows carry IP + User-Agent and are never
  deleted. Sweep them on the same schedule as submissions.
- [x] **Pin `rq-dashboard`** (v0.6.3) and give it only
  `RQ_DASHBOARD_REDIS_URL` instead of the full `.env` (which includes the
  Postgres password).

## P1 — ops

- [x] **Exec-form `CMD`** in the Dockerfile so gunicorn receives SIGTERM and
  drains in-flight requests on deploy.
- [x] **Log rotation** (`logging:` max-size/max-file) on all compose services.
- [x] **Memory limits** for `web`, `postgres`, `redis` (only `worker` is
  bounded today).
- [x] **Persist `removed_images`** on a volume, or stop archiving removals —
  today the copies land in the container layer and are lost on redeploy.

## P2 — deferred (tracked, not in this pass)

- [x] pybabel catalog regen + fill: all six `.po` catalogs re-synced from a
  fresh extract and fully translated (MT drafts per the standing i18n
  decision); `.mo` binaries recompiled in step.
- [ ] Re-translate the EN wiki (38 pages) into fr/es/de/ru/zh/pt.
- [ ] Port the unblob analyzer from `copilot/unblob-extractor`.
- [ ] pgdata backup/restore job + documented procedure.
- [ ] Raise the coverage floor (actual ~77% locally vs `--cov-fail-under=55`);
  cover `utils/init_db.py` (currently 0%).
- [ ] `docker-build` CI job on pushes to `main`, not just PRs.
- [ ] Split `spectrogram.py` (658 lines, 27% coverage) into plotting + DSP.
- [ ] Frontend: build result DOM into a `DocumentFragment` instead of
  repeated `innerHTML +=`; cache `discover_analyzers()`/`wiki_tool_names()`;
  worker-specific app factory.
- [ ] Non-root container user (binwalk currently runs as root, bounded).
- [ ] Remove the dead `SKIP_IHDR_FILL` knob or implement it.

## Verification protocol (against production)

1. Before the release: record baseline — response headers, `ads.txt`,
   canonical URL, absence of `data-ad-slot`, and a marker submission's
   presence in the DB.
2. Tag + release (confirmed by the owner; the tag push deploys).
3. After the deploy: the marker submission must still exist (proves
   `CLEAR_AT_RESTART=0` took effect), new headers present, canonical
   unchanged, `/download` returns 429 past the limit, gunicorn drains on the
   next deploy (no 502 burst).
