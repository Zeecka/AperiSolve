# Aperi'Solve

[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.com)](https://aperisolve.com/)
[![Rawsec's CyberSecurity Inventory](https://inventory.raw.pm/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.raw.pm/tools.html#Aperi'Solve)

<p align="center"><a href="https://www.aperisolve.com"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/master/examples/screenshot.png"/></a></p>

<b>Try it now: https://www.aperisolve.com</b>

# I . What is Aperi'Solve?
Aperi'Solve is a platform which performs layer analysis on image.<br/>
The platform also uses "*zsteg*", "*steghide*", "*outguess*", "*exiftool*", "*binwalk*", "*foremost*" and "*strings*" for deeper steganography analysis.

<p align="center"><a href="https://www.aperisolve.com"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/master/examples/video.gif"/></a></p>

# II . Installation

Even if Aperi'Solve is available at the URL https://www.aperisolve.com, you can install a cli alias with the following command:
```bash
sudo sh -c"$(curl -fs https://www.aperisolve.com/install.sh)"
aperisolve image.png
```

# III . Why Aperi'Solve
Aperi'Solve has been created in order to have an "easy to use" platform which performs common steganalysis tests such as LSB or `steghide`. The platform is also a quick alternative for people who didn't manage to install `zsteg` (ruby gem) properly.

# IV . Features
Aperi'Solve is based on Python3 with Flask and PIL module, the platform currently supports the following images format: `.png`, `.jpg`, `.gif`, `.bmp`, `.jpeg`, `.jfif`, `.jpe`, `.tiff`.

The platform allow you to:
- **Visualise each bit layer** of each channel for a given image (ie. LSB of Red channel).
- **Browse** and **Download each bit layer image**.
- **Visualise `zsteg` informations** such as text encoded on LSB
- **Download `zsteg` files** such as mp3 encoded on LSB
- **Download `steghide` files** using a defined password
- **Download `outguess` files** using a defined password
- **Visualise `exiftool` informations** such as geolocation or author
- **Visualise `binwalk` informations**
- **Download `binwalk` files** such as zip in png headers
- **Download `foremost` files** such as zip in png headers
- **Visualise `strings` output**

# V . Application

The Aperi'Solve platform is a *Flask* web service (/web) (python 3.7) with backend daemons (/backend) which perform analysis.

Both of the two part has its own docker container.

# VI . Run with Docker-Compose

You can pull all the images from the GitHub Container Registry. A simple docker compose file is included in the repos. Just use:  
```bash
docker compose -f docker-compose.yml up
```

Then check your browser at [http://localhost:5000/](http://localhost:5000).

---

# TODO

- Statistics on homepage
- "Probable flag" with regex
- Implement "out of the box" png check (increase size of png) ?
- ...
