Title: binwalk - Find Files Embedded Inside Images
Description: How binwalk scans images for embedded file signatures, how Aperi'Solve runs it with recursive extraction, and how to carve appended data locally.
Order: 120

# binwalk

[binwalk](https://github.com/ReFirmLabs/binwalk) scans a file for **embedded
file signatures** — archives, images, executables — and can extract them.
On images it excels at spotting data appended after the legitimate end of
file or concatenated polyglots.

## What Aperi'Solve runs

```console
$ binwalk --matryoshka -e image.png
```

- `-e` extracts every recognized signature.
- `--matryoshka` recurses into what was extracted (an archive inside an
  archive inside an image...).

When anything is extracted, the result page offers the files as a `.7z`
download.

## Reading the output

```
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------
0             0x0             PNG image, 800 x 600, 8-bit/color RGBA
54187         0xD3AB          Zip archive data, name: flag.txt
```

The first line is the carrier itself. Any *additional* signature is
suspicious: here a Zip archive starts at byte offset 54187.

False positives are common with short generic signatures (e.g. "Zlib
compressed data" inside PNG is usually just the image data itself) — check
extraction results before drawing conclusions.

## Extracting manually

To carve a specific region without binwalk's automation:

```console
$ dd if=image.png of=hidden.zip bs=1 skip=54187
$ unzip hidden.zip
```

[foremost](https://github.com/korczis/foremost) performs similar carving
with a different signature database — Aperi'Solve runs both, so compare the
two outputs.

## Installing locally

```console
$ apt install binwalk
```

## Common CTF patterns

- A Zip/RAR/7z appended after the image's end-of-file marker (`IEND` for
  PNG, `FFD9` for JPEG).
- Several images concatenated: the second one only appears in binwalk's
  listing.
- Password-protected archive extracted → the password hides elsewhere in
  the challenge.
