Title: foremost - Carve Embedded Files out of Images
Description: How foremost carves hidden files out of images using header and footer signatures, how Aperi'Solve runs it, and how it complements binwalk in CTF challenges.
Order: 180

# foremost

[foremost](https://github.com/korczis/foremost) is a forensic **file
carving** tool originally developed for the US Air Force. It scans a file
byte by byte for known **headers and footers** (JPEG, PNG, ZIP, PDF, ...)
and carves out every match — ideal for files hidden inside an image.

## What Aperi'Solve runs

```console
$ foremost -o output/ -i image.png
```

- `-i` is the input image, `-o` the directory receiving carved files.
- Every carved file is sorted into a subdirectory named after its type
  (`jpg/`, `zip/`, `pdf/`, ...).

Anything carved is offered on the result page as a `foremost.7z` download.

## Reading the output

Foremost writes an `audit.txt` in the output directory summarizing what it
found:

```
Num  Name (bs=512)      Size      File Offset   Comment
0:   00000105.zip       1 KB      54187
1:   00000000.jpg       52 KB     0
```

The first entry is often the carrier image itself. Any *additional* file —
here a Zip starting at offset 54187 — is what you are after. The carved
copies live next to `audit.txt`, ready to open.

## foremost vs binwalk

Both find embedded files, but differently:

- **foremost** does pure signature carving: it matches header/footer byte
  patterns and copies everything in between, format-blind.
- **[binwalk](/wiki/tools/binwalk)** parses file structures and recurses
  into extracted archives (`--matryoshka`).

Their signature databases differ, so each can catch files the other
misses. Aperi'Solve runs both — always compare the two results.

## Installing locally

```console
$ apt install foremost
```

## Limitations

- Only formats in its signature database are carved, and footer-less
  formats rely on a maximum size guess — expect trailing junk.
- Payloads without a recognizable header (LSB steganography, encrypted
  blobs) stay invisible — try [zsteg](/wiki/tools/zsteg) for those.

## Common CTF patterns

- A Zip or JPEG appended after the PNG `IEND` chunk — foremost carves it
  directly, no manual `dd` needed.
- Several files concatenated into one blob: each shows up as its own entry
  in `audit.txt`.
- A carved archive that asks for a password → it hides elsewhere in the
  challenge (metadata, strings, another layer).
