Title: Aperi'Solve Wiki - Steganography Tools & Guides
Description: Documentation for Aperi'Solve: how the analysis works, guides for each steganography tool (zsteg, steghide, binwalk, exiftool...) and a CTF cheatsheet.
Order: 1

# Aperi'Solve Wiki

Welcome to the Aperi'Solve wiki. Aperi'Solve is a free online platform that
performs layer analysis and steganography detection on images: upload a
picture on the [home page](/) and every analyzer runs automatically.

This wiki documents how to read the results and how each underlying tool
works, so you can reproduce and extend the analysis on your own machine.

## Start here

- [Getting started](/wiki/getting-started) — how to use Aperi'Solve and read
  its results.
- [Steganography CTF Cheatsheet](/wiki/cheatsheet) — a practical checklist
  for image, audio and file-format challenges.

## Tool guides

Each analyzer that runs on your upload has its own page: what the tool does,
the exact command Aperi'Solve runs, how to interpret the output, and how to
install it locally.

- [Bit-plane decomposer](/wiki/tools/decomposer) — visualize each bit of
  each color channel.
- [zsteg](/wiki/tools/zsteg) — LSB steganography detection for PNG and BMP.
- [steghide](/wiki/tools/steghide) — extract data hidden in JPEG/BMP with a
  passphrase.
- [binwalk](/wiki/tools/binwalk) — find and extract files embedded inside
  the image.
- [exiftool](/wiki/tools/exiftool) — read metadata (EXIF, XMP, IPTC...).

More tool pages are added regularly — contributions are welcome on
[GitHub](https://github.com/Zeecka/AperiSolve).

## What is steganography analysis?

Steganography hides data inside an innocuous carrier file — for images this
means manipulating pixel bits, palette entries, metadata fields or the file
structure itself. Steganalysis is the practice of detecting such hidden data.
No single tool covers every technique, which is why Aperi'Solve runs a whole
battery of analyzers side by side and lets you compare their outputs at a
glance.
