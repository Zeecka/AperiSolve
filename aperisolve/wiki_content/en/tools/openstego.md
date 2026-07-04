Title: OpenStego - Extract Randomized LSB Steganography
Description: How OpenStego hides AES-encrypted data with the RandomLSB algorithm, how Aperi'Solve extracts it with your password, and how to use the GUI and CLI locally.
Order: 220

# OpenStego

[OpenStego](https://www.openstego.com/) (by Samir Vaidya) is a Java
steganography application that embeds data with its **RandomLSB**
algorithm: payload bits are scattered across pseudo-randomly chosen pixel
LSB positions, optionally encrypted with AES. That randomization is why
plain LSB scanners miss it.

## What Aperi'Solve runs

Aperi'Solve attempts extraction with the password you provided on upload,
trying both crypto algorithms OpenStego supports:

```console
$ openstego extract -a randomlsb --cryptalgo AES128 -sf image -xd extracted -p "password"
$ openstego extract -a randomlsb --cryptalgo AES256 -sf image -xd extracted -p "password"
```

The AES256 attempt only runs if the AES128 one fails. Any extracted files
are zipped and offered as a download on the result page.

## Reading the output

- `Extracted file: ...` — success; download the archive.
- `OpenStego needs a password to work.` — you left the password field
  empty and OpenStego printed its usage text instead of extracting;
  re-submit with a password.
- A wrong password on a real OpenStego file fails differently from a
  file with no payload at all (invalid-password error vs corrupt/invalid
  stego data) — the former tells you to keep guessing passwords.

## Using OpenStego locally

Running `openstego` with no arguments opens the GUI. The CLI equivalent
of what Aperi'Solve does (`randomlsb` is the default algorithm, so `-a`
can usually be omitted):

```console
$ openstego extract -sf image.png -p password -xd outdir
```

## Installing locally

Download the `.deb` or `.jar` from the
[GitHub releases](https://github.com/syvaidya/openstego/releases) — Java
is required:

```console
$ sudo dpkg -i openstego_0.8.6-1_all.deb    # or: java -jar openstego.jar
```

## Limitations

- RandomLSB needs a **lossless carrier**: OpenStego reads and writes
  PNG/BMP stego files. A JPEG upload will practically never contain an
  OpenStego payload — for JPEG try [steghide](/wiki/tools/steghide),
  [outguess](/wiki/tools/outguess) or [jpseek](/wiki/tools/jpseek).
- Without the right password, an AES-encrypted payload is unrecoverable;
  there is no fast cracker comparable to stegseek for steghide.

## Common CTF patterns

- A PNG challenge that name-drops OpenStego, or an `OPENSTEGO` marker
  showing up in `strings`/[zsteg](/wiki/tools/zsteg) LSB dumps — the
  payload header starts with that magic string.
- The password comes from the challenge context: description, metadata
  (check [exiftool](/wiki/tools/exiftool)) or a previous stage.
- Distinguish errors: invalid-password means the file *is* an OpenStego
  carrier — go hunt for the password instead of switching tools.
