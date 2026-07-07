Title: Files & Archives - Magic Bytes, Polyglots, Carving & Documents
Description: File-structure steganography: magic bytes and appended data, polyglots (mitra/truepolyglot), ZIP known-plaintext attacks (bkcrack), PDF revisions and object streams, Office VBA macros, SVG/NTFS-ADS/git tricks, pcap forensics, and carving with binwalk/foremost.
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
how these are built. To *generate* or dissect one:
[mitra](https://github.com/corkami/mitra) (`python3 mitra.py a.png b.zip` emits
every viable polyglot of a pair) and
[truepolyglot](https://github.com/ansemjo/truepolyglot)
(`truepolyglot pdfzip --input1 payload.zip --input2 doc.pdf out.pdf`).

!!! tip "One file, or one file per parser?"
    The polyglot test is simple: open the *same bytes* with a different tool —
    `unzip` a PNG, render a ZIP as a PDF. If a second tool succeeds, there is a
    second payload.

## Archives (ZIP and friends)

```console
$ zipdetails -v target.zip       # full structure
$ zipinfo target.zip
$ 7z l target.zip
```

- **Weak crypto:** ZipCrypto leaks filenames and sizes and is plaintext-
  attackable; AES-256 resists. Crack short ZipCrypto passwords with
  `fcrackzip -u -D -p rockyou.txt target.zip`.
- **Known-plaintext attack** (the bigger win): if you know ~12 contiguous bytes
  of any one entry — trivial when it is a PNG/PDF with a fixed header —
  [bkcrack](https://github.com/kimci86/bkcrack) recovers the internal keys
  **without the password** and decrypts the whole archive:

```console
$ bkcrack -C secret.zip -c inner.png -p known_prefix.bin      # recover 3 keys
$ bkcrack -C secret.zip -k <k0> <k1> <k2> -D unlocked.zip     # decrypt everything
```

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
tool other than the one its extension implies. For a macro-enabled document
(`.docm`/`.xlsm`), extract the VBA without opening Office:

```console
$ olevba --decode target.docm       # VBA source + de-obfuscation + IOCs
```

**PDF** — an object/stream container:

```console
$ pdfinfo file.pdf
$ pdfdetach -list file.pdf && pdfdetach -saveall file.pdf   # embedded attachments
$ qpdf --qdf --object-streams=disable file.pdf out.pdf      # decompress for grep
```

Three PDF-specific hiding spots the basics miss:

- **Retained earlier revisions.** More than one `%%EOF` marker means the PDF was
  incrementally updated and old (e.g. "redacted") versions are still inside.
  [pdfresurrect](https://github.com/enferex/pdfresurrect) recovers them:
  `pdfresurrect -q file.pdf` (count), then `pdfresurrect -w file.pdf`.
- **Compressed object streams** hide content from `grep`/`strings`. Expand them
  with Didier Stevens' `pdf-parser.py -O -a file.pdf`, and hunt actions with
  `pdf-parser.py --search /JS` / `--search /OpenAction` / `--search /EmbeddedFile`.
- **Optional Content Groups** (`/OCG`) are toggleable layers — one may be hidden.
  `pdf-parser.py --search /OCG file.pdf`, then enable it in a full viewer.

`peepdf` is a good interactive alternative.

## Other containers and hiding spots

- **SVG** is XML — it renders fine while hiding `<script>`, `<!-- comments -->`,
  `<metadata>`, or elements drawn outside the `viewBox`. Pretty-print and read
  it: `xmllint --format file.svg | less`, plus `exiftool`/`strings`; in Inkscape,
  *Ungroup* (Ctrl+Shift+G) and open the XML editor.
- **ICO / WebP / TIFF** — ICO can bundle several images or embed a full PNG
  (`icotool -x file.ico`); WebP is a RIFF container (`webpinfo`, appended data
  after the RIFF size is invisible); TIFF can carry extra IFDs/tags
  (`exiftool -a -u -g1 file.tif`, `tiffinfo`). `binwalk` catches appended data in
  all three.
- **NTFS Alternate Data Streams** — a file's content can hide in a named stream.
  Windows: `dir /r`, `Get-Content file -Stream secret`. From an image: Sleuth
  Kit `icat`.
- **`.git` directories** — the flag is often a *deleted* commit or a dangling
  blob: `git log --all`, `git fsck --lost-found` then `git cat-file -p <sha>`,
  and `git reflog` for rewound heads.
- **QR / barcodes** in a recovered file → `zbarimg --raw file.png` (upscale tiny
  codes first: `convert file.png -resize 400% big.png`).

## Network captures (pcap)

Forensics challenges frequently ship a `.pcap`; the hidden file or message is in
the traffic:

- **Files over HTTP/SMB/FTP** → `tshark -nr cap.pcap --export-objects http,out/`
  (or `smb`, `tftp`), or Wireshark *File → Export Objects*. When that fails,
  `tcpflow -r cap.pcap` splits each stream, then `binwalk`/`foremost` each.
- **USB HID keyboard** → `tshark -r usb.pcap -Y 'usb.capdata && usb.data_len==8'
  -T fields -e usb.capdata` piped into
  [ctf-usb-keyboard-parser](https://github.com/TeamRocketIst/ctf-usb-keyboard-parser).
- **DNS / ICMP exfiltration** → pull the payload fields
  (`tshark -r cap.pcap -Y dns.qry.name -T fields -e dns.qry.name`) and decode the
  subdomain labels (hex/base32) or ICMP `data.data`.

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
