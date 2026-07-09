Title: Aperi'Solve Wiki - Steganography & CTF Forensics Handbook
Description: An organized steganography wiki for CTF players and forensic analysts: a triage methodology, a decision-tree cheatsheet, technique pages per medium (image, audio, text, files) and a guide for every tool Aperi'Solve runs.
NavTitle: Overview
Order: 1

# Aperi'Solve Wiki

Welcome to the Aperi'Solve wiki — a practical, organized handbook for
**steganography and CTF forensics**. Upload an image on the
[home page](/) and every analyzer runs automatically; these pages explain the
techniques behind the results, how to reproduce them by hand, and how to work
through a challenge methodically.

The wiki is built like a field manual: start with a method, jump to a
decision tree when you are stuck, dive into a medium-specific technique page,
and open a tool's guide when you need the exact command.

## How this wiki is organized

- **[Methodology](/wiki/methodology)** — the triage workflow: what to run
  first, second and third on *any* file, and the rules that save the most
  time.
- **[Cheatsheet](/wiki/cheatsheet)** — a decision tree by file type, a
  Tell → Tool lookup table, and a "when stuck" checklist. This is the page to
  keep open during a CTF. It splits into per-medium command checklists:
  [image](/wiki/cheatsheet/image), [audio](/wiki/cheatsheet/audio),
  [text](/wiki/cheatsheet/text), [files & archives](/wiki/cheatsheet/files),
  [network / PCAP](/wiki/cheatsheet/network),
  [encodings & esolangs](/wiki/cheatsheet/encodings) and
  [passwords & brute-force](/wiki/cheatsheet/brute-force).
- **Techniques** — one page per medium, covering how data is hidden and how to
  recover it:
  [Images](/wiki/techniques/images) ·
  [Audio](/wiki/techniques/audio) ·
  [Video](/wiki/techniques/video) ·
  [Text & Unicode](/wiki/techniques/text) ·
  [Files & Archives](/wiki/techniques/files-archives) ·
  [Steganalysis](/wiki/techniques/steganalysis) ·
  [Encodings & obfuscation](/wiki/techniques/encodings).
- **Tools** — a reference page for every analyzer Aperi'Solve runs: what it
  does, the exact command, how to read the output, and how to install it
  locally.

## Start here

New to steganography challenges? Read the
[methodology](/wiki/methodology) once, then drive every challenge from the
[cheatsheet](/wiki/cheatsheet). New to Aperi'Solve itself? See
[getting started](/wiki/getting-started).

## Tool reference

Each analyzer that runs on your upload has its own page:

- [Bit-plane decomposer](/wiki/tools/decomposer) — visualize each bit of each
  color channel.
- [Color remapping](/wiki/tools/color_remapping) — reveal hidden data with
  palette transforms.
- [zsteg](/wiki/tools/zsteg) — LSB steganography detection for PNG and BMP.
- [steghide](/wiki/tools/steghide) — extract data hidden in JPEG/BMP with a
  passphrase.
- [stegseek](/wiki/tools/stegseek) — crack a steghide passphrase in seconds.
- [binwalk](/wiki/tools/binwalk) — find and extract files embedded inside the
  image.
- [foremost](/wiki/tools/foremost) — carve embedded files out of the image.
- [exiftool](/wiki/tools/exiftool) — read metadata (EXIF, XMP, IPTC...).
- [pngcheck](/wiki/tools/pngcheck) — verify PNG structure and find corrupt
  chunks.
- [PCRT](/wiki/tools/pcrt) — detect and repair corrupted PNG files.
- [OutGuess](/wiki/tools/outguess) — extract hidden data from JPEG images.
- [jsteg](/wiki/tools/jsteg) — extract LSB data from JPEG DCT coefficients.
- [JPHide/JPSeek](/wiki/tools/jpseek) — extract JPHide payloads from JPEG.
- [OpenStego](/wiki/tools/openstego) — extract randomized LSB steganography.
- [stegsnow](/wiki/tools/stegsnow) — hide/extract data in whitespace.
- [identify](/wiki/tools/identify) — inspect image properties with ImageMagick.
- [file](/wiki/tools/file) — identify the real file type of an upload.
- [strings](/wiki/tools/strings) — find readable text inside files.
- [Spectrogram](/wiki/tools/spectrogram) — reveal hidden images and tones in
  audio.
- [pdfinfo](/wiki/tools/pdfinfo) — read PDF metadata and structure.
- [pdfid](/wiki/tools/pdfid) — triage suspicious PDF objects.

Contributions are welcome on
[GitHub](https://github.com/Zeecka/AperiSolve).

## What is steganography analysis?

Steganography hides data inside an innocuous carrier file — for images this
means manipulating pixel bits, palette entries, metadata fields or the file
structure itself. **Steganalysis** is the practice of detecting and extracting
that hidden data. No single tool covers every technique, which is why
Aperi'Solve runs a whole battery of analyzers side by side and lets you compare
their outputs at a glance — and why this wiki teaches the manual techniques the
automated tools do not cover.
