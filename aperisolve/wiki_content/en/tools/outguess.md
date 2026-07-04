Title: OutGuess - Extract Hidden Data from JPEG Images
Description: How OutGuess hides data in redundant JPEG DCT coefficients, how Aperi'Solve extracts it with your password during deep analysis, and how to run it locally.
Order: 190

# OutGuess

[OutGuess](https://github.com/resurrecting-open-source-projects/outguess)
is a steganography tool by Niels Provos that embeds data in the
**redundant bits of JPEG DCT coefficients**. After embedding, it corrects
the remaining coefficients so the image's frequency statistics stay
unchanged — defeating the classic chi-square detection attack.

## What Aperi'Solve runs

OutGuess only runs when you check **deep analysis** on upload. Extraction
(`-r`) uses the password you provided, or no key at all:

```console
$ outguess -k "password" -r image.jpg outguess.data
$ outguess -r image.jpg outguess.data      # empty password
```

Embedding and extraction without `-k` use the same built-in default key,
so an empty password still recovers payloads that were hidden without
one. If `outguess.data` comes out non-empty, it is zipped and offered as
a download on the result page.

## Reading the output

OutGuess prints its progress on stderr even when it succeeds:

- `Reading image.jpg....` followed by extraction statistics and a
  download link — the payload was recovered; grab the archive.
- Errors like `Extracted datalen is too long` — the key is wrong, or
  nothing was embedded with OutGuess. The tool still writes an output
  file in this case, but an empty one; Aperi'Solve discards it and
  reports an error instead of a download.

## Installing locally

```console
$ apt install outguess
```

## Limitations

- JPEG (and PNM) only — for PNG carriers use [zsteg](/wiki/tools/zsteg).
- There is no way to *prove* absence: a wrong key and an empty carrier
  fail the same way. If you suspect OutGuess, keep hunting for the key.
- Old payloads: files embedded with the legacy OutGuess 0.13 cannot be
  extracted by modern 0.2+ builds (the formats are incompatible). Some
  old CTF challenges require compiling the historical version.

## Common CTF patterns

- Empty password — Aperi'Solve tries exactly this when you leave the
  password field blank; always attempt it first.
- The key is printed elsewhere in the challenge: image metadata (check
  [exiftool](/wiki/tools/exiftool)), the filename, the challenge text or
  a companion file.
- A JPEG that looks clean in [steghide](/wiki/tools/steghide) and
  [jsteg](/wiki/tools/jsteg) but was name-dropped as "outguessed" or
  ships with an OutGuess-era (early 2000s) theme.
- The extracted payload is another carrier: re-upload `outguess.data`.
