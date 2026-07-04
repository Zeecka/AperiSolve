Title: pngcheck - Verify PNG Structure and Find Corrupt Chunks
Description: How pngcheck verifies PNG files chunk by chunk, how Aperi'Solve runs it in verbose mode, and what CRC errors and extra chunks mean in CTF challenges.
Order: 160

# pngcheck

[pngcheck](http://www.libpng.org/pub/png/apps/pngcheck.html) verifies the
integrity of PNG files: it walks the file **chunk by chunk**, checks every
CRC checksum, and validates chunk ordering and contents. When a PNG "won't
open" in a CTF, pngcheck tells you exactly which byte is wrong.

## What Aperi'Solve runs

```console
$ pngcheck -v image
```

`-v` (verbose) lists every chunk with its offset and length instead of a
single OK/error summary. Non-PNG uploads are reported as unsupported —
pngcheck only handles PNG, JNG and MNG files.

## Reading the output

```
File: image.png (54321 bytes)
  chunk IHDR at offset 0x0000c, length 13
    800 x 600 image, 32-bit RGB+alpha, non-interlaced
  chunk IDAT at offset 0x00025, length 54000
  chunk IEND at offset 0x0d33d, length 0
No errors detected in image.png (3 chunks, 77.4% compression).
```

Every chunk appears with its **byte offset** — invaluable for hex-editing.
A healthy PNG starts with `IHDR`, contains one or more `IDAT` chunks, and
ends with `IEND`. Errors look like:

```
  chunk IHDR at offset 0x0000c, length 13
    CRC error in chunk IHDR (computed 575943df, expected 12345678)
ERRORS DETECTED in image.png
```

## Errors that matter in CTFs

- **CRC error in a chunk** — someone edited the chunk data (often the
  IHDR dimensions) without recomputing the CRC. The *original* CRC still
  matches the *original* data, which is how tools recover it.
- **Wrong dimensions** — a reduced height in IHDR crops off the bottom of
  the image where the flag is drawn. Restore the real size and re-check.
- **Additional data after IEND chunk** — bytes appended after the image;
  carve them with [binwalk](/wiki/tools/binwalk) or `dd`.
- **Unknown/private chunks** — nonstandard chunk names between IHDR and
  IDAT can carry an arbitrary payload; grab their bytes at the reported
  offset.

## Installing locally

```console
$ apt install pngcheck
```

## Limitations

- PNG, JNG and MNG only — nothing to say about JPEG, GIF or BMP.
- It diagnoses structure but repairs nothing: fix the bytes yourself in a
  hex editor, or let [PCRT](/wiki/tools/pcrt) repair the file
  automatically.
- A structurally perfect PNG can still hide LSB steganography — pair it
  with [zsteg](/wiki/tools/zsteg).

## Common CTF patterns

- IHDR CRC error: dimensions were zeroed or shrunk to hide part of the
  image — recover them via the CRC (see [PCRT](/wiki/tools/pcrt)).
- A bad CRC on a `tEXt` or ancillary chunk pointing you to hand-modified
  data worth inspecting.
- Extra data after IEND holding a ZIP archive or a second image.
