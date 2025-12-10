# Aperi'Solve

![CI](https://github.com/Zeecka/AperiSolve/actions/workflows/releases.yml/badge.svg)
![Lint](https://github.com/Zeecka/AperiSolve/actions/workflows/lint.yml/badge.svg)
![Black Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
[![Rawsec's CyberSecurity Inventory](https://inventory.raw.pm/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.raw.pm/tools.html#Aperi'Solve)

<p align="center"><a href="https://www.aperisolve.com"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/main/examples/screenshot.png"/></a></p>

<b>Try it now: https://www.aperisolve.com</b>

<b> Support Aperi'Solve:</b>

<a href="https://buymeacoffee.com/aperisolve">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="40" />
</a>

## What is Aperi'Solve?

Aperi'Solve is a platform which performs steganalysis on images.<br/>

The platform uses *layer analysis*, "*zsteg*", "*steghide*", "*outguess*", "*exiftool*", "*binwalk*", "*foremost*" and "*strings*" for deeper steganography analysis.

<p align="center"><a href="https://www.aperisolve.com"><img src="https://i.imgur.com/qiR1mlT.gif"/></a></p>
 
### Why Aperi'Solve?

Aperi'Solve has been created in order to have an "easy to use" platform which performs common steganalysis tests such as LSB or `steghide`. The platform is also a quick alternative for people who were note able to install tools like `zsteg` (ruby gem) properly.

### Features

Aperi'Solve is based on Python3 with Flask and PIL module, the platform supports the most common image formats like`.png`, `.jpg`, `.gif`, `.bmp`, `.jpeg`, `.jfif`, `.jpe`, `.tiff`...

The platform allows you to:
- **Visualize each bit layer** of each channel for a given image (ie. LSB of Red channel).
- **Browse** and **Download each bit layer image**.
- **Visualise `zsteg` information** such as text encoded on LSB
- **Download `steghide` files** using a defined password
- **Download `outguess` files** using a defined password
- **Visualise `exiftool` information** such as geolocation or author
- **Visualise `binwalk` information**
- **Download `binwalk` files** such as ZIP file in PNG headers
- **Download `foremost` files** such as ZIP file in PNG headers
- **Visualise `pngcheck` output**
- **Visualise `strings` output**

## Installation

Even if Aperi'Solve is available at the URL https://www.aperisolve.com/, you can set up your own instance with the following command:

```bash
git clone https://github.com/Zeecka/AperiSolve.git
cd aperisolve
docker compose up -d
```

> Default will run on http://localhost:5000/

## Development

Aperi'Solve platform is a *Flask* web service (python 3.11+) with python workers performing analysis.
Jobs are stacked in a redis-queue, and image information is stored in a postgresql database.
All services run inside Docker containers.

### Adding new analyzer

Adding new analyzer is easy.

1. Copy and adapt the [template_analyzer.py](aperisolve/analyzers/template_analyzer.py) file with your name, ie. "myanalyzer.py".
2. Add this analyzer to [workers.py](aperisolve/workers.py).
    - Import your function `from .analyzers.analyzer import analyze_myanalyzer`
    - Add the function to the `analyzers` variable, like other analyzers.
3. Add your analyzer name to `TOOL_ORDER` in [aperisolve.js](aperisolve/static/js/aperisolve.js).

### Tips

Here is a batch of useful commands.

```bash
docker compose down -v  # Remove the volume containings results
docker compose -f compose.dev.yml up  # Start application in developpement mode
rm -rf aperisolve/results  # Remove results from development mode
docker exec -it postgres psql -U aperiuser -d aperisolve  # Get postgresql shell
docker exec -it aperisolve-web bash # Get a shell inside the running web app
```

> Note, if you used [compose.dev.yml](compose.dev.yml), you must remove "results" when switching to [production Docker](compose.yml) setup.

### Code quality

Python code follows the following linters:

- Black
- Flake8  (ignoring E203,E501,W503)
- Pylint (ignoring W0718,R0903,R0801)
- Mypy (ignoring unused-awaitable)

GitHub CI will alert in case of failure.

## Roadmap

- [ ] Zsteg extract / --all --> **Download `zsteg` files** such as mp3 encoded on LSB
- [ ] Test on mobile
- [ ] i18n
- [ ] Rootless analyzers ?
