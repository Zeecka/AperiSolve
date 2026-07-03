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
   - runs `docker compose pull && docker compose down -v && docker compose
     up -d`.

The compose stack runs six services: `web` (gunicorn), `worker` (RQ),
`cron` (RQ cron scheduler driving the retention cleanup), `initdb`
(one-shot), `postgres`, `redis`, plus `rqdashboard` on port 9181.

## Configuration

All runtime configuration is environment-driven; `.env.example` documents
every variable. Deploy-time values come from GitHub Actions variables and
secrets — to change a production setting (e.g. `MAX_CONTENT_LENGTH`,
`ADSENSE_*`, `SITE_BASE_URL`), edit the repository's Actions configuration
and re-deploy with a tag.

## Branches

`main` is the only long-lived branch. The historical `prod` branch is
obsolete: its hardcoded AdSense snippet and `/ads.txt` route were replaced
by the `GOOGLE_ADS_TXT`/`CUSTOM_EXTERNAL_SCRIPT`/`ADSENSE_*` environment
variables, and its `:prod` image tags are no longer built. It can be
deleted; nothing references it.

Before pruning old `worker/*` feature branches, check them for unmerged
analyzer work (`worker/jphide`, `worker/jsteg`, `worket/color_remap`,
`worker/identify_graphicmagick`, `worker/file`).

## Local development

```console
$ docker compose -f compose.dev.yml up --build
```

The dev stack mounts `./aperisolve` into the containers and uses
`.env.example` directly. If you change translatable strings, recompile the
gettext catalogs (`pybabel compile -d aperisolve/translations`) since the
mounted source shadows the image's compiled catalogs.
