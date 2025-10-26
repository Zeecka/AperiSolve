# Aperi'Solve

![CI](https://github.com/Zeecka/AperiSolve/actions/workflows/releases.yml/badge.svg)
![Lint](https://github.com/Zeecka/AperiSolve/actions/workflows/lint.yml/badge.svg)
![Black Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
[![Rawsec's CyberSecurity Inventory](https://inventory.raw.pm/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.raw.pm/tools.html#Aperi'Solve)

<p align="center"><a href="https://www.aperisolve.com"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/main/examples/screenshot.png"/></a></p>

<b>Try it now: https://www.aperisolve.com</b>

## What is Aperi'Solve?

Aperi'Solve is a platform which performs steganalysis on images.<br/>

The platform uses *layer analysis*, "*zsteg*", "*steghide*", "*outguess*", "*exiftool*", "*binwalk*", "*foremost*" and "*strings*" for deeper steganography analysis.

<p align="center"><a href="https://www.aperisolve.com"><img src="https://i.imgur.com/qiR1mlT.gif"/></a></p>
 
### Why Aperi'Solve?

Aperi'Solve has been created in order to have an "easy to use" platform which performs common steganalysis tests such as LSB or `steghide`. The platform is also a quick alternative for people who didn't manage to install tools like `zsteg` (ruby gem) properly.

### Features

Aperi'Solve is based on Python3 with Flask and PIL module, the platform supports the most common images formats like`.png`, `.jpg`, `.gif`, `.bmp`, `.jpeg`, `.jfif`, `.jpe`, `.tiff`...

The platform allow you to:
- **Visualise each bit layer** of each channel for a given image (ie. LSB of Red channel).
- **Browse** and **Download each bit layer image**.
- **Visualise `zsteg` informations** such as text encoded on LSB
- **Download `steghide` files** using a defined password
- **Download `outguess` files** using a defined password
- **Visualise `exiftool` informations** such as geolocation or author
- **Visualise `binwalk` informations**
- **Download `binwalk` files** such as zip in png headers
- **Download `foremost` files** such as zip in png headers
- **Visualise `strings` output**

## Installation

Even if Aperi'Solve is available at the URL https://www.aperisolve.com/, you can set-up your own instance with the following command:

```bash
git clone https://github.com/Zeecka/AperiSolve.git
cd aperisolve
docker compose up -d
```

> Default will run on http://localhost:5000/

## Development

Aperi'Solve platform is a *Flask* web service (python 3.11+) with python workers performing analysis.
Jobs can be processed asynchronously using Redis Queue (optional) or synchronously without Redis. Image information is stored in a PostgreSQL database.
All services are well contained inside Docker containers.

### Redis Configuration

Redis is **optional** and controlled by the `REDIS_URL` environment variable:

- **With Redis** (async processing): Set `REDIS_URL` environment variable (e.g., `redis://redis:6379/0`)
- **Without Redis** (sync processing): Leave `REDIS_URL` unset - suitable for free-tier deployments like Render

When running without Redis, image analysis runs synchronously in the main web process.

### Adding new analyzer

Adding new analyzer is easy.

1. Copy and addapt the [template_analyzer.py](aperisolve/analyzers/template_analyzer.py) file with you name, ie. "myanalyzer.py".
2. Add this analyzer to [workers.py](aperisolve/workers.py).
    - Import your function `from .analyzers.analyzer import analyze_myanalyzer`
    - Add the function to `analyzers` variables, like other analyzers.
3. Add your analyzer name to `TOOL_ORDER` in [aperisolve.js](aperisolve/static/js/aperisolve.js).

### Tips

Here is a batch of usefull commands.

```bash
docker compose down -v  # Remove volume containings results
docker compose -f docker-compose-dev.yml up  # Start application in developpement mode
rm -rf aperisolve/results  # Remove results from developpement mode
docker exec -it postgres psql -U aperiuser -d aperisolve  # Get postgresql shell
docker exec -it aperisolve-web bash # Get shell in running web app
```

> Note, if you used [docker-compose-dev.yml](docker-compose-dev.yml), you must remove "results" when switching to [production docker](docker-compose.yml).

### Code quality

Python code follows the following linters:

- Black
- Flake8  (ignoring E203,E501,W503)
- Pylint (ignoring W0718,R0903,R0801)
- Mypy (ignoring unused-awaitable)

GitHub CI will alert in case of failure.

## Roadmap

- [ ] PngCheck
- [ ] Zsteg extract / --all --> **Download `zsteg` files** such as mp3 encoded on LSB
- [ ] Test on mobile
- [ ] i18n
- [ ] Rootless analyzers ?
