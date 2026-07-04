Title: strings - Find Readable Text Inside Image Files
Description: How the strings command extracts printable text from images, how to spot flags and passwords in its output, and useful flags for CTF steganography.
Order: 250

# strings

[strings](https://www.gnu.org/software/binutils/) (part of GNU binutils)
extracts every run of **printable characters** from a binary file. On a CTF
image it surfaces metadata text, tool signatures and — surprisingly often —
a flag pasted straight into the file.

## What Aperi'Solve runs

```console
$ strings image.png
```

By default it prints every run of 4+ printable ASCII characters, in file
order.

## Reading the output

Most lines are noise: compressed image data randomly forms short printable
runs. Look for the readable islands:

```
IHDR
Adobe Photoshop 2024
XML:com.adobe.xmp
aHR0cHM6Ly9leGFtcGxlLmNvbQ==
CTF{str1ngs_f1rst_alw4ys}
```

- Chunk/segment names (`IHDR`, `IDAT`, `JFIF`, `Exif`) are normal format
  structure; editor signatures reveal how the file was made.
- Long alphanumeric blobs ending in `=` are likely **base64** — decode
  them.
- Text near the *end* of the output often sits after the image data:
  prime suspect territory.

## Useful local flags

```console
$ strings -n 8 image.png              # only runs of 8+ chars (less noise)
$ strings -e l image.png              # UTF-16LE ("wide") strings
$ strings -t x image.png              # print hex offset of each string
$ strings image.png | grep -i "ctf{"  # hunt the flag format directly
```

Grepping for the challenge's flag format (`CTF{`, `flag{`, `HTB{`...) is
the fastest first move.

## Installing locally

Preinstalled on most Linux distributions and macOS (GNU binutils).
Otherwise: `apt install binutils`.

## Limitations

- Only *contiguous printable* bytes appear: anything encoded, compressed,
  encrypted or bit-scattered (LSB steganography) is invisible — use
  [zsteg](/wiki/tools/zsteg) and [steghide](/wiki/tools/steghide) for
  those.
- ASCII-only by default: UTF-16 text needs `-e l`. And expect false leads —
  4-character runs occur by chance in compressed data.

## Common CTF patterns

- The flag in plain text near the end of the file, after the image data.
- A base64 blob that decodes to the flag, a URL or the next hint.
- URLs, usernames or passwords for another stage of the challenge (e.g.
  the passphrase for [steghide](/wiki/tools/steghide)).
