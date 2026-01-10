# Aperi'Solve

[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
![CI](https://github.com/Zeecka/AperiSolve/actions/workflows/release.yml/badge.svg)
![Lint](https://github.com/Zeecka/AperiSolve/actions/workflows/lint.yml/badge.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue?logo=docker)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Black Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
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
- Browse and download each bit-layer image.
- Integrates and displays outputs from:
  - [binwalk](https://github.com/ReFirmLabs/binwalk) (embedded archives)
  - [exiftool](https://exiftool.org/) (metadata and geolocation)
  - [foremost](https://foremost.sourceforge.net/) (carved files)
  - [openstego](https://www.openstego.com/) (extraction with password)
  - [outguess](https://www.rbcafe.com/software/outguess/) (extraction with password)
  - [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html)
  - [steghide](https://steghide.sourceforge.net/) (extraction with password)
  - [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html)
  - [zsteg](https://github.com/zed-0xff/zsteg) (LSB text/data extraction)
  - [file](https://www.darwinsys.com/file/) (MIME type and format detection)
- Worker queue architecture for offloading heavy/slow analyzers (Redis + background workers).
- Results stored for later browsing and download.

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

## Architecture

- Flask web framework
- Background workers that run analyzers (queue via Redis)
- PostgreSQL stores image metadata and job statuses
- Docker-based deployment for isolation of analyzers and services

This separation keeps heavy tools (binwalk, foremost, zsteg, etc.) isolated and avoids blocking the web worker.

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

Thanks to contributors:
- [Zeecka](https://www.zeecka.fr/) - **(author)**
- [aradhyacp](https://github.com/aradhyacp)
- [Philip Zimmermann](https://github.com/Philip-Zimmermann)

Thanks to the open-source community:
[binwalk](https://github.com/ReFirmLabs/binwalk), [exiftool](https://exiftool.org/), [foremost](https://foremost.sourceforge.net/), [openstego](https://www.openstego.com/), [outguess](https://www.rbcafe.com/software/outguess/), [pngcheck](https://www.libpng.org/pub/png/apps/pngcheck.html), [steghide](https://steghide.sourceforge.net/), [strings](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html), [zsteg](https://github.com/zed-0xff/zsteg), ...
