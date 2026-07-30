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

The compose stack runs seven services: `web` (gunicorn), `worker` (RQ),
`cron` (RQ cron scheduler driving the retention cleanup), `initdb`
(one-shot), `postgres`, `redis`, plus `rqdashboard` bound to
localhost:9181 (reach it via SSH tunnelling).

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
