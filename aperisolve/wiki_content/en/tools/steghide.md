Title: steghide - Extract Hidden Data from JPEG and BMP
Description: How steghide hides and extracts data in JPEG, BMP, WAV and AU files, how Aperi'Solve runs it with your password, and how to crack passphrases.
Order: 110

# steghide

[steghide](https://steghide.sourceforge.net/) is a classic steganography
tool that embeds encrypted, compressed payloads in **JPEG, BMP, WAV and AU**
files. Extraction requires the passphrase used at embedding time (which may
be empty).

## What Aperi'Solve runs

Aperi'Solve first asks steghide what is embedded, then extracts it using the
password you provided on upload (or an empty one):

```console
$ steghide info image.jpg -p "password"
$ steghide extract -sf image.jpg -xf secret.txt -p "password"
```

If extraction succeeds, the embedded file is zipped and offered as a
download on the result page.

## Reading the output

- `wrote extracted data to "..."` — success; download the archive.
- `could not extract any data with that passphrase!` — either nothing is
  embedded or the password is wrong. Try an empty password first, then
  crack it (see below).
- `the file format of the file ... is not supported` — steghide only reads
  JPEG/BMP/WAV/AU; a PNG input always fails, use
  [zsteg](/wiki/tools/zsteg) instead.

## Cracking the passphrase

When you suspect a steghide payload but do not know the passphrase,
[stegseek](https://github.com/RickdeJager/stegseek) brute-forces wordlists
dramatically faster than the older `stegcracker`:

```console
$ stegseek image.jpg rockyou.txt
```

## Installing locally

```console
$ apt install steghide
```

## Common CTF patterns

- Empty passphrase — always try it first, Aperi'Solve does this by default.
- The passphrase is hidden elsewhere in the challenge (image metadata —
  check [exiftool](/wiki/tools/exiftool) —, filename, another file).
- `rockyou.txt` cracks the majority of guessable passphrases via stegseek.
- The extracted payload is itself another carrier (an image inside an
  image): re-upload the extracted file.
