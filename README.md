# Aperi'Solve

[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
![CI](https://github.com/Zeecka/AperiSolve/actions/workflows/release.yml/badge.svg)
![Lint](https://github.com/Zeecka/AperiSolve/actions/workflows/lint.yml/badge.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue?logo=docker)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Ruff](https://img.shields.io/badge/lint-ruff-30173d)
![uv](https://img.shields.io/badge/package-uv-30173d)
![ty](https://img.shields.io/badge/types-ty-30173d)
![License](https://img.shields.io/github/license/Zeecka/AperiSolve)
![GitHub Issues](https://img.shields.io/github/issues/Zeecka/AperiSolve)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Zeecka/AperiSolve)
![Last Commit](https://img.shields.io/github/last-commit/Zeecka/AperiSolve)
![Contributors](https://img.shields.io/github/contributors/Zeecka/AperiSolve)
[![Rawsec's CyberSecurity Inventory](https://inventory.raw.pm/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.raw.pm/tools.html#Aperi'Solve)

<p align="center">
  <a href="https://www.aperisolve.com">
    <img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/main/examples/screenshot.png" alt="Aperi'Solve screenshot" />
  </a>
</p>

Try it now: **https://www.aperisolve.com**

Support Aperi'Solve:

<a href="https://buymeacoffee.com/aperisolve">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="40" />
</a>

---

Aperi'Solve is an open-source steganalysis web platform that performs automated analysis on images to detect and extract hidden data using common steganography tools and techniques.

## Key features

- Visualize each bit layer (LSB and other layers) per image channel (R/G/B/Alpha).
- Color remapping (random palette remaps with 8 generated variants)
- Runs 16 analyzers in parallel and displays their output, with per-tool
  success/no-result badges and one-click download of extracted files:
  - [binwalk](https://github.com/ReFirmLabs/binwalk) (embedded archives)
  - [exiftool](https://exiftool.org/) (metadata and geolocation)
  - [file](https://manned.org/file.1) (MIME type and format detection)
  - [GraphicsMagick identify](http://www.graphicsmagick.org/identify.html) (image info & properties)
  - [foremost](https://foremost.sourceforge.net/) (carved files)
  - [jsteg](https://github.com/lukechampine/jsteg) (JPEG LSB extraction)
  - [jpseek / jphide](https://github.com/h3xx/jphs) (JPEG steganography extraction, with password)
  - [openstego](https://www.openstego.com/) (extraction with password)
  - [outguess](https://www.rbcafe.com/software/outguess/) (extraction with password, deep analysis)
  - [pcrt](https://github.com/sherlly/PCRT) (PNG check & repair)
  - [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html)
  - [steghide](https://steghide.sourceforge.net/) (extraction with password)
  - [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html)
  - [zsteg](https://github.com/zed-0xff/zsteg) (LSB text/data extraction)
- **In-app wiki** ([`/wiki`](https://www.aperisolve.com/wiki/)): a steganography CTF
  cheatsheet plus a guide per analyzer, authored as Markdown.
- **Internationalization**: UI available in English, French, Spanish, German,
  Russian, Chinese and Portuguese under language-prefixed URLs (`/fr/`, `/es/`, …).
- Worker queue architecture for offloading heavy/slow analyzers (Redis + background workers).
- Content-addressed result cache, HTTP caching, and per-endpoint rate limiting.
- Results stored temporarily for later browsing and download, then cleaned up
  automatically by a scheduled job.

## Adding an analyzer

Adding an analyzer is a single file: subclass `SubprocessAnalyzer`, set a few
class attributes (`name`, `has_archive`, `needs_password`, `deep_only`,
`display_order`), and install the tool in the `Dockerfile`. The worker run
list, download allow-list, and frontend order are all derived automatically.
See [docs/adding-analyzer.md](docs/adding-analyzer.md).

## Quick start (Docker)

In case you want to host your own version of https://www.aperisolve.com/.

> Required: Docker + Docker Compose.

```bash
git clone https://github.com/Zeecka/AperiSolve.git
cd AperiSolve
cp .env.example .env
docker compose up -d
```

Then browse url: http://localhost:5000/

Ads and analytics are disabled by default; every integration (`ADSENSE_*`,
`CUSTOM_EXTERNAL_SCRIPT`, `SITE_BASE_URL`, Sentry) is opt-in via environment
variables documented in [`.env.example`](.env.example).

## Architecture

The stack runs as Docker Compose services:

- **web** — Flask app served by gunicorn (Jinja templates + vanilla JS frontend).
- **worker** — an RQ worker that runs the analyzers for each submission,
  fanning out to one thread per tool.
- **cron** — an RQ cron scheduler that runs the retention cleanup off the
  request path.
- **initdb** — a one-shot service that creates the tables and pre-fills the
  IHDR CRC recovery database.
- **postgres** — stores image metadata and submission status.
- **redis** — RQ broker (DB 0) and rate-limiter storage (DB 1).
- **rqdashboard** — queue monitoring, bound to localhost:9181.

This separation keeps heavy tools (binwalk, foremost, zsteg, etc.) isolated
and avoids blocking the web worker. Identical submissions are deduplicated by
a content hash, and derived images are cached with long-lived immutable HTTP
headers, so repeat traffic is cheap.

## Documentation

- [docs/adding-analyzer.md](docs/adding-analyzer.md) — add a new analyzer.
- [docs/deploy.md](docs/deploy.md) — the tag-driven production deploy flow.
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, tests, wiki pages, and translations.

## Testing

```bash
uv sync --extra dev
uv run pytest -q            # unit tests (no services needed)

# end-to-end analyzer tests through the running app:
docker compose -f compose.dev.yml up -d
uv run pytest tests/test_webapp_analyzers.py -v
```

## Roadmap

See [Issues](../../issues).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

> [!WARNING]
> If you discover a security issue, please report it privately to the repository owner instead of opening a public issue.

## Credits

Thanks to donors:
- [Philip Zimmermann](https://github.com/Philip-Zimmermann)
- [Ed Guillory](#)
- [Silje Hollås](#)

Thanks to contributors:
- [Zeecka](https://www.zeecka.fr/) - **(author)**
- [aradhyacp](https://github.com/aradhyacp)
- [Philip Zimmermann](https://github.com/Philip-Zimmermann)
- [abneeeees](https://github.com/abneeeees)

Thanks to the open-source community:
[binwalk](https://github.com/ReFirmLabs/binwalk), [exiftool](https://exiftool.org/), [GraphicsMagick identify](http://www.graphicsmagick.org/identify.html), [foremost](https://foremost.sourceforge.net/), [jsteg](https://github.com/lukechampine/jsteg), [jphide/jpseek](https://github.com/h3xx/jphs), [openstego](https://www.openstego.com/), [outguess](https://www.rbcafe.com/software/outguess/), [pcrt](https://github.com/sherlly/PCRT), [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html), [steghide](https://steghide.sourceforge.net/), [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html), [zsteg](https://github.com/zed-0xff/zsteg), ...
