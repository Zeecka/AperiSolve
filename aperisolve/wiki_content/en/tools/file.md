Title: file - Identify the Real File Type of an Image
Description: How the file command identifies the true type of a challenge file from its magic bytes, why extensions lie in CTFs, and how to read its output on Aperi'Solve.
Order: 240

# file

[file](https://www.darwinsys.com/file/) identifies what a file *really* is
by inspecting its **magic bytes** — the signature at the start of the file —
instead of trusting the extension. It is the very first sanity check on any
CTF challenge file.

## What Aperi'Solve runs

```console
$ file -b image.png
```

`-b` (brief) omits the filename from the output, printing only the
identification.

## Reading the output

`file` compares the first bytes against its magic database (libmagic) and
prints a human-readable description:

```
PNG image data, 800 x 600, 8-bit/color RGBA, non-interlaced
JPEG image data, JFIF standard 1.01, resolution (DPI), density 72x72
Zip archive data, at least v2.0 to extract
data
```

- **PNG/JPEG image data** — the file is what it claims; dimensions and
  color type come from the header.
- **Zip archive data**, **PDF document**, **ELF 64-bit LSB executable** —
  the "image" is actually something else entirely. Rename it and open it
  with the right tool.
- **data** — no known signature matched. The header is missing, corrupted
  or deliberately mangled.

## When the answer is "data"

A challenge PNG reported as `data` usually has a broken header: wrong magic
bytes, a corrupted chunk or bad dimensions. Diagnose it with
[pngcheck](/wiki/tools/pngcheck) and repair it with
[pcrt](/wiki/tools/pcrt) — both run automatically on Aperi'Solve.

## Installing locally

Preinstalled on virtually every Linux distribution and on macOS (the
`file` package). If missing: `apt install file`.

## Limitations

- Only the *first* matching signature is reported: data appended after a
  valid image stays invisible — that is what
  [binwalk](/wiki/tools/binwalk) and [foremost](/wiki/tools/foremost) are
  for.
- Polyglot files (valid as two formats at once) show only one identity.
- A correct header on top of corrupted data still reports a clean type.

## Common CTF patterns

- `challenge.png` is actually a Zip, PDF or ELF renamed to `.png` — `file`
  reveals it instantly.
- A polyglot (e.g. GIF+JavaScript, PNG+Zip): `file` shows the first format,
  the second hides behind it.
- Output is just `data` → corrupted magic bytes; fix the header and the
  image renders again.
