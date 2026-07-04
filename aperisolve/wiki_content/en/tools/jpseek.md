Title: JPHide/JPSeek - Extract JPHide Payloads from JPEG
Description: How JPHide spreads hidden data across JPEG DCT coefficients, how Aperi'Solve runs JPSeek with your passphrase, and how to build the jphs tools locally.
Order: 210

# JPHide / JPSeek

[JPHide and JPSeek](https://github.com/h3xx/jphs) (the *jphs* package, by
Allan Latham, 1998) are a classic pair of JPEG steganography tools:
`jphide` embeds a file, `jpseek` recovers it. JPHide uses the passphrase
to drive a Blowfish-based pseudo-random sequence that selects which **DCT
coefficients** carry payload bits, spreading them thinly across the whole
image so the payload is statistically hard to spot.

## What Aperi'Solve runs

`jpseek` has no password flag — it prompts interactively — so Aperi'Solve
drives it with `expect`, answering the prompt with the password you gave
on upload (or an empty line):

```console
$ jpseek image.jpg jpseek.out
Passphrase: <your upload password, or empty>
```

If recovery succeeds, `jpseek.out` is zipped and offered as a download on
the result page.

## Reading the output

- `File completely recovered.` — clean success; download the archive.
- `File not completely recovered` — jpseek ran out of image before the
  expected payload length. Aperi'Solve still keeps the partial
  `jpseek.out` in the archive; truncated payloads are often mostly
  readable, so check it anyway.
- Any other failure — wrong passphrase, or no JPHide payload at all.
  Like most passphrase-based tools, jpseek cannot tell the two apart.

## Installing locally

The jphs source bundles its own libjpeg (jpeg-8a), which must be built
first:

```console
$ git clone https://github.com/h3xx/jphs
$ cd jphs/jpeg-8a && ./configure && make && cd ..
$ make all      # produces ./jphide and ./jpseek
```

Aperi'Solve's Docker image builds it exactly this way, with small patches
to the Makefile and `jpseek.c` for modern toolchains.

## Limitations

- JPEG only, and only payloads embedded by `jphide` — for other JPEG
  schemes see [steghide](/wiki/tools/steghide),
  [outguess](/wiki/tools/outguess) and [jsteg](/wiki/tools/jsteg).
- Large payloads noticeably degrade the image and become detectable;
  small ones (a few percent of the file) are the intended use.

## Common CTF patterns

- Blank passphrase — Aperi'Solve sends an empty line when you leave the
  password field empty; always try that first.
- A guessable passphrase: the challenge title, the image filename, or a
  string from [exiftool](/wiki/tools/exiftool) metadata.
- `stegdetect image.jpg` flags the file as `jphide` — the strongest hint
  that jpseek is the right tool; its companion `stegbreak -t p` can then
  brute-force the passphrase from a wordlist.
