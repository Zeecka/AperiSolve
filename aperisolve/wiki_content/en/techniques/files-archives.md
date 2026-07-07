Title: Files & Archives - Magic Bytes, Polyglots, Carving & Documents
Description: File-structure steganography: magic bytes and appended data, the polyglot taxonomy (simple, parasitic, mille-feuilles, chimera, schizophrenic, Angecryption), ZIP/PDF/Office tricks, and file carving with binwalk, foremost, scalpel and photorec.
Order: 40

# Files & Archives

Before touching pixels or samples, treat the file as a **structure**. A huge
fraction of "stego" challenges are really file-format tricks: something appended
after the logical end, a second format hiding inside the first, or an archive
masquerading as an image. None of these need pixel analysis — they need you to
read the bytes.

[TOC]

## Magic bytes and appended data

Every format starts with a **magic signature**
([list of file signatures](https://en.wikipedia.org/wiki/List_of_file_signatures)).
[`file`](/wiki/tools/file) reads it to identify the type — but it only looks at
the start, so anything **appended** after the logical end is invisible to it.

```console
$ file target
$ tail -c 200 target | xxd      # inspect the trailer
$ binwalk target                # list embedded signatures
$ binwalk -e target             # auto-extract them
```

The classic: a ZIP concatenated after an image. Because `unzip` reads the
central directory at the **end** of the file, an appended ZIP often just opens:

```console
$ unzip target.png
$ 7z l target.png
```

If `binwalk` misses it, carve by header/footer with
[foremost](/wiki/tools/foremost), or manually with `dd` once you know the
offset:

```console
$ dd if=target of=payload.bin bs=1 skip=$OFFSET
```

## Polyglot files

A **polyglot** is valid under more than one format at once — an image you can
view that is *also* a runnable JAR, or a PDF that is also a ZIP. `file` reports
only one type and will not flag the trick; look for **multiple magic numbers**
and **trailing data**. The common kinds:

- **Simple** — a plain concatenation of two files.
- **Parasitic** — one file fully contained inside another's structure.
- **Mille-feuille** — layers alternated by controlling the internal structure.
- **Chimera** — one body, several heads: several formats share the same data
  block (e.g. Zlib Deflate pixels) behind different headers, so one file renders
  as JPEG *and* PNG.
- **Schizophrenic** — a single format interpreted differently by different
  readers (a PDF whose JavaScript some viewers run, or the
  [Gamma](https://carlmastrangelo.com/blog/gamma-steganography) image trick).
- **Angecryption** — encrypting or decrypting the file yields *another* valid
  file (same or different format).

![Angecryption](/static/img/cheatsheet/Angecryption.png)

Corkami's [file-format posters](http://corkami.github.io/) are the reference for
how these are built.

## Archives (ZIP and friends)

```console
$ zipdetails -v target.zip       # full structure
$ zipinfo target.zip
$ 7z l target.zip
```

- **Weak crypto:** ZipCrypto leaks filenames and sizes and is plaintext-
  attackable; AES-256 resists. Crack short ZipCrypto passwords with
  `fcrackzip -u -D -p rockyou.txt target.zip`.
- **Repair** a broken archive with `zip -FF broken.zip --out fixed.zip`.
- **Evasion tricks** (seen in modern challenges): concatenated central
  directories (7-Zip reads the first, WinRAR the last), overlapping entries,
  and local-header vs central-directory mismatches. Detect duplicate end-of-
  central-directory markers with `binwalk -R "PK\x05\x06"`.

## Documents

**Office (OOXML)** — `.docx`, `.pptx`, `.xlsx` are ZIPs of XML parts:

```console
$ 7z x report.docx -o report/
```

Inspect `word/media/` (embedded images), `word/_rels/` (relationships, external
resource pointers) and any custom XML parts. The same applies to `.jar`, `.apk`,
`.odf` — they are all valid archives, so check whether the file opens with a
tool other than the one its extension implies.

**PDF** — an object/stream container:

```console
$ pdfinfo file.pdf
$ pdfdetach -list file.pdf
$ pdfdetach -saveall file.pdf
$ qpdf --qdf --object-streams=disable file.pdf out.pdf   # decompress for grep
```

Look for embedded attachments, hidden JavaScript objects, and unusual or
oversized streams. `pdf-parser.py` and `peepdf` go deeper.

## File carving

When a disk image or blob contains many embedded files, carve them by signature:

| Tool | Notes |
|------|-------|
| [binwalk](/wiki/tools/binwalk) | Signature scan + `-e` / `-Me` recursive extract |
| [foremost](/wiki/tools/foremost) | Header/footer carving (`/etc/foremost.conf`) |
| scalpel | Config-driven carving |
| photorec | File-type-selective recovery |
| bulk_extractor | Carve URLs, emails, and embedded artifacts |

## Related

- Drive a challenge from the [cheatsheet](/wiki/cheatsheet#polyglot).
- Appended data inside a PNG specifically:
  [Images — PNG structure](/wiki/techniques/images#png-structure-tricks).
