Title: Steganalysis - Detecting Hidden Data Statistically
Description: The detection side of steganography: chi-square, RS and Sample Pairs analysis, blind vs targeted steganalysis, embedding domains, and the tools (StegExpose, stegdetect, Aletheia, zsteg) that flag hidden data - plus what Aperi'Solve automates.
Order: 50

# Steganalysis

Steganalysis is the flip side of steganography: deciding whether a file
**contains** hidden data, and ideally which method was used, without knowing the
secret. In CTFs you rarely need formal detection — the challenge implies data is
present — but when a file *looks* clean and every extractor fails, statistical
detectors tell you whether to keep digging.

[TOC]

## Targeted vs blind detection

- **Targeted** steganalysis assumes a specific embedding method and tests for
  its statistical fingerprint. It is precise but only finds what it looks for.
- **Blind** (universal) steganalysis trains on features that separate cover from
  stego across many methods — the basis of modern machine-learning detectors.

## Core statistical attacks

- **Chi-square attack** — LSB replacement makes pairs of values (2k, 2k+1)
  converge to the same frequency. The chi-square test measures that convergence;
  a strong signal means sequential LSB embedding.
- **RS analysis** (Regular/Singular groups) — flips LSBs in small pixel groups
  and measures how the count of "regular" vs "singular" groups changes,
  estimating the embedding rate. Robust against randomized LSB.
- **Sample Pairs / primary sets** — related estimators that infer the hidden
  message length from correlations between adjacent samples.

## Embedding domains (what is being attacked)

- **Spatial LSB** — the pixel-bit techniques on the
  [Images page](/wiki/techniques/images).
- **Transform / DCT** — JPEG methods (jsteg, F5, OutGuess) hide in frequency
  coefficients.
- **Spread-spectrum / additive noise** and **BPCS** — spread the payload to
  resist targeted tests.
- **Adaptive schemes** — S-UNIWARD (spatial) and J-UNIWARD (JPEG) minimize a
  distortion function, the current state of the art and the hardest to detect.

## Tools

| Tool | Detects | Notes |
|------|---------|-------|
| [zsteg](/wiki/tools/zsteg) | PNG/BMP LSB | Doubles as a detector — if it finds a payload, one exists |
| StegExpose | LSB in lossless PNG/BMP | Batch Chi-square + RS + Sample Pairs → probability report |
| stegdetect | JPEG (jsteg/jphide/OutGuess/F5) | Classic statistical DCT detector |
| [Aletheia](https://daniellerch.me/stego/) | Modern spatial & JPEG families | ML/DL toolkit, covers J-UNIWARD/nsF5/HStego |

```console
$ zsteg -a suspect.png
$ java -jar StegExpose.jar ./images_dir
$ stegdetect -t opjf suspect.jpg
```

## What Aperi'Solve automates

Aperi'Solve front-loads the detection steps you would otherwise run by hand:

- **Bit-plane** visualization per R/G/B/A channel
  ([decomposer](/wiki/tools/decomposer)) — the visual equivalent of browsing
  every plane in Stegsolve.
- **Color-remapping** variants ([color remapping](/wiki/tools/color_remapping))
  to expose palette-based hiding.
- **[zsteg](/wiki/tools/zsteg)** as an LSB detector/extractor for PNG/BMP.
- Metadata, structure and carving passes
  ([exiftool](/wiki/tools/exiftool), [pngcheck](/wiki/tools/pngcheck),
  [binwalk](/wiki/tools/binwalk), [foremost](/wiki/tools/foremost)).

What it does **not** do — and you must run yourself — is deep statistical
detection (StegExpose/Aletheia), audio spectrograms, and passphrase brute-force
beyond the single password you supply. Those are the manual steps in the
[cheatsheet](/wiki/cheatsheet#stuck).

## Related

- The offensive techniques these detectors target:
  [Images](/wiki/techniques/images) · [Audio](/wiki/techniques/audio).
- The full triage flow: [Methodology](/wiki/methodology).
