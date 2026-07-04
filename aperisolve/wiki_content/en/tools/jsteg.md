Title: jsteg - Extract LSB Data from JPEG DCT Coefficients
Description: How jsteg hides and reveals data in the least significant bits of JPEG DCT coefficients, how Aperi'Solve runs it, and how to install it with Go.
Order: 200

# jsteg

[jsteg](https://github.com/lukechampine/jsteg) is a Go tool that hides
data in the **least significant bits of quantized DCT coefficients** of
JPEG files. It is the JPEG counterpart of pixel-LSB tools like
[zsteg](/wiki/tools/zsteg): a JPEG stores frequency coefficients, not raw
pixels, so pixel-based LSB tools cannot see its payloads.

## What Aperi'Solve runs

```console
$ jsteg reveal image.jpg
```

`reveal` reads the DCT coefficients and prints any recovered payload to
stdout; Aperi'Solve shows that output line by line on the result page.
jsteg has **no password concept** — if a jsteg payload is present, this
single command recovers it.

## Reading the output

- Readable text or a flag — that is the payload, done.
- Nothing at all — no jsteg-format payload in the image.
- A short blob of garbage bytes — usually noise from a clean image, not
  a payload. Real payloads look like text or start with a known file
  signature.

## Using jsteg locally

```console
$ jsteg hide cover.jpg secret.txt out.jpg   # embed secret.txt
$ jsteg reveal out.jpg                      # print payload to stdout
$ jsteg reveal out.jpg payload.bin          # or write it to a file
```

Capacity depends on the image — roughly 10–14% of the JPEG's file size.

## Installing locally

```console
$ go install lukechampine.com/jsteg/cmd/jsteg@latest
```

Prebuilt binaries are also published on the project's GitHub releases
page. Aperi'Solve's own Docker image builds it from source with
`go build ./cmd/jsteg`.

## Limitations

- jsteg only recovers payloads embedded in **its own format**. Data
  hidden with [steghide](/wiki/tools/steghide),
  [outguess](/wiki/tools/outguess) or JPHide
  ([jpseek](/wiki/tools/jpseek)) will not appear, even though all four
  operate on DCT coefficients.
- No encryption and no password: convenient for CTFs, but it also means
  a payload cannot be protected — challenge authors who want a password
  step use steghide or OutGuess instead.

## Common CTF patterns

- A flag printed directly by `jsteg reveal` — the JPEG equivalent of the
  zsteg classic.
- A hidden file rather than text: run `jsteg reveal image.jpg out.bin`
  locally and inspect it with `file`, `xxd` or `binwalk`.
- The extracted payload is another carrier: re-upload it.
