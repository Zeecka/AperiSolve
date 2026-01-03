# Aperi'Solve

![CI](https://github.com/Zeecka/AperiSolve/actions/workflows/releases.yml/badge.svg)
![Lint](https://github.com/Zeecka/AperiSolve/actions/workflows/lint.yml/badge.svg)
![Black Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
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

Table of contents

- [Key features](#key-features)
- [Quick start (Docker)](#quick-start-docker)
- [Development](#development)
- [Configuration & environment variables](#configuration--environment-variables)
- [Architecture](#architecture)
- [Troubleshooting & tips](#troubleshooting--tips)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

## Key features

- Visualize each bit layer (LSB and other layers) per image channel (R/G/B/Alpha).
- Browse and download each bit-layer image.
- Integrates and displays outputs from:
  - [zsteg](https://github.com/zed-0xff/zsteg) (LSB text/data extraction)
  - [steghide](https://steghide.sourceforge.net/) (extraction with password)
  - [outguess](https://www.rbcafe.com/software/outguess/) (extraction with password)
  - [openstego](https://www.openstego.com/) (extraction with password)
  - [exiftool](https://exiftool.org/) (metadata and geolocation)
  - [binwalk](https://github.com/ReFirmLabs/binwalk) (embedded archives)
  - [foremost](https://foremost.sourceforge.net/) (carved files)
  - [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html)
  - [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html)
- Worker queue architecture for offloading heavy/slow analyzers (Redis + background workers).
- Results stored for later browsing and download.

## Quick start (Docker)

In case you want to host your own version of https://www.aperisolve.com/.

Recommended: Docker + Docker Compose.

Clone and start the full stack (production-like):

```bash
git clone https://github.com/Zeecka/AperiSolve.git
cd AperiSolve
cp .env.example .env
docker compose up -d
```

Default: http://localhost:5000/

## Development

Development compose:

```bash
# development environment (hot reload and local volumes)
docker compose -f compose.dev.yml up --build
```

Useful commands:

```bash
# Stop and remove containers, networks and volumes (results are stored in a volume)
docker compose down -v

# Enter web container shell
docker exec -it aperisolve-web bash

# Enter Postgres shell (from host)
docker exec -it postgres psql -U aperiuser -d aperisolve

# Backup all uploaded files
docker cp -r aperisolve-web:/aperisolve/results /path/to/backup/location

# Backup a single uploaded file
docker cp aperisolve-web:/aperisolve/results/filename.ext /path/to/backup/filename.ext
```

> [!WARNING]
> If switching between dev and production compose files, remove the `results` directory or mounted volume to avoid conflicts:
> ```bash
> rm -rf aperisolve/results
> ```

## Configuration & environment variables

The application can be configured with the `.env` file:

```shell
# Application configuration
MAX_CONTENT_LENGTH=1048576  # Max uploaded image size (bytes)
MAX_PENDING_TIME=600  # Timeout for analyzer (seconds)
MAX_STORE_TIME=259200  # Delay until deleted from server
CLEAR_AT_RESTART=1  # Reset database and results at application restart/crash
SKIP_IHDR_FILL=0  # Skip IHDR database fill (gain times at startup but reduce results)

# Flask configuration
FLASK_DEBUG=0
FLASK_ENV=development

# Redis configuration
RQ_DASHBOARD_REDIS_URL=redis://redis:6379/0

# Database configuration
POSTGRES_DB=aperisolve
POSTGRES_USER=aperiuser
POSTGRES_PASSWORD=aperipass
DB_URI=postgresql://aperiuser:aperipass@postgres:5432/aperisolve

# Sentry configuration
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_RELEASE=1.0.0
SENTRY_ENVIRONMENT=development
```

> [!NOTE]
> If using Docker Compose, defaults are set in the compose files. For production deployments, set secure secrets via your orchestrator or environment.

## Architecture

- Flask web framework
- Background workers that run analyzers (queue via Redis)
- PostgreSQL stores image metadata and job statuses
- Docker-based deployment for isolation of analyzers and services

This separation keeps heavy tools (binwalk, foremost, zsteg, etc.) isolated and avoids blocking the web worker.

## Troubleshooting & tips

- If analyzers don't produce output, check worker logs:
  ```bash
  docker compose logs -f aperisolve-worker
  ```
- To force re-analysis, remove results for the image (both file and in database) and re-submit the job.
- Ensure system packages needed by native tools (binwalk, foremost) are available in the analyzer containers or host image.

## Roadmap

- [ ] **[Bug]** Duplicate key value violates unique constraint "submission_pkey"
- [ ] **[Enhancement]** Server continuous deployment
- [ ] **[Feature]** Zsteg: full extraction (--all) and download of discovered files (mp3, etc.)
- [ ] **[Feature]** Mobile-friendly UI / test on mobile
- [ ] **[Feature]** i18n (internationalization)
- [ ] **[Feature]** Rootless / unprivileged analyzers

See [Issues](../../issues) for more!

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

> [!WARNING]
> If you discover a security issue, please report it privately to the repository owner instead of opening a public issue.

## Credits

Acknowledgements:

- Thanks to contributors and the open-source community for the tools integrated ([zsteg](https://github.com/zed-0xff/zsteg), [steghide](https://steghide.sourceforge.net/), [outguess](https://www.rbcafe.com/software/outguess/), [openstego](https://www.openstego.com/), [exiftool](https://exiftool.org/), [binwalk](https://github.com/ReFirmLabs/binwalk), [foremost](https://foremost.sourceforge.net/), [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html), [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html), ...).
