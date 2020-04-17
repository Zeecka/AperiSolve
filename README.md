# Aperi'Solve

[![Website](https://img.shields.io/website?url=https%3A%2F%2Faperisolve.fr)](https://aperisolve.fr/)
![Docker Cloud Automated build](https://img.shields.io/docker/cloud/automated/zeecka/aperisolve)
![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/zeecka/aperisolve)
[![Rawsec's CyberSecurity Inventory](https://inventory.rawsec.ml/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.rawsec.ml/tools.html#Aperi'Solve)

<p align="center"><a href="https://aperisolve.fr"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/master/examples/screenshot.png"/></a></p>

<b>Try it now: https://aperisolve.fr</b>

# I . What is Aperi'Solve?
Aperi'Solve is a platform which performs layer analysis on image.<br/>
The platform also uses "*zsteg*", "*steghide*", "*exiftool*", "*binwalk*" and "*strings*" for deeper steganography analysis.
<p align="center"><a href="https://aperisolve.fr"><img src="https://raw.githubusercontent.com/Zeecka/AperiSolve/master/examples/video.gif"/></a></p>

# II . Why Aperi'Solve
Aperi'Solve has been created in order to have an "easy to use" platform which performs common steganalysis tests such as LSB or `steghide`. The platform and Dockerfile are also a quick alternative for people who didn't manage to install `zsteg` (ruby gem) properly.

# III . Features
Aperi'Solve is based on Python3 with Flask and PIL module, the platform currently supports the following images format: `.png`, `.jpg`, `.gif`, `.bmp`, `.jpeg`, `.jfif`, `.jpe`, `.tiff`.

The platform allow you to:
- **Visualise each bit layer** of each channel for a given image (ie. LSB of Red channel).
- **Browse** and **Download each bit layer image**.
- **Visualise `zsteg` informations** such as text encoded on LSB
- **Download `zsteg` files** such as mp3 encoded on LSB
- **Download `steghide` files** using a defined password
- **Visualise `exiftool` informations** such as geolocation or author
- **Visualise `binwalk` informations**
- **Download `binwalk` files** such as zip in png headers
- **Visualise `strings` output**

# IV . Application
The Aperi'Solve platform is a *Flask* (python 3.7) application. The source code is located into the `/data` folder. The platform has been split as follows:
- *app.py* : Contains web routes and main application variables
- *stega.py* : Contains steganography functions. Layer decomposition is performed with numpy.
- *appfunct.py* : Contains functions used in both *app.py* and *stega.py*.
- */templates* : index.html (html view)
- */static* : Images, JavaScript and CSS
- */uploads* : Uploaded images and working directory for steganography tools

# V . Run with Docker

## Docker Run

Simply run the following command:
```bash
docker run -p 80:80 zeecka/aperisolve
```

Then check your browser at [http://localhost/](http://localhost).

If you already use port 80, feel free to run Aperi'Solve on an other port (ie. 1337):
```bash
docker run -p 1337:80 zeecka/aperisolve
```
Then check your browser at [http://localhost:1337/](http://localhost:1337/).

# VI . Manual Installation

As said in the beginning of this file, some of theses tools such as zsteg and exiftool may not be easy to install. Aperi'Solve has been created to package installation in docker container / provide a web access to the platform. If you still want to install the dependencies by yourself, here are the requirements:

- Install python and pip (version 3.7+)
```bash
apt install python3-dev
```
- Install python requirements (PIL, Numpy, ...):
```bash
cd build/flask/
pip3 install -r requirements
```
- Install `ruby` and `ruby-dev`:
```bash
apt install ruby ruby-dev
```
- Install `zsteg`:
```bash
gem install zsteg --no-ri --no-rdoc
```
- Install `steghide`:
```bash
apt install steghide
```
- Install `exiftool`:
```bash
apt install perl libimage-exiftool-perl
```
- Install `7z`:
```bash
apt install p7zip
```

Then, run:
```bash
cd data
python3 app.py
```

# TODO

- Implement Foremost ?
- Implement Outguess ?
- Implement "out of the box" png check (increase size of png)
- Implement PNGcheck ?
- Implement stegoVeritas ?
- ...
