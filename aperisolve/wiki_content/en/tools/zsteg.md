Title: zsteg - LSB Steganography Detection for PNG and BMP
Description: How zsteg detects LSB steganography in PNG and BMP images, how Aperi'Solve runs it, reading its output, and using it locally with common flags.
Order: 100

# zsteg

[zsteg](https://github.com/zed-0xff/zsteg) is a Ruby tool that detects data
hidden in the **least significant bits (LSB)** of PNG and BMP images. It is
one of the first tools to try on any PNG steganography challenge.

## What Aperi'Solve runs

```console
$ zsteg image.png
```

Without extra flags, zsteg scans the most common bit/channel combinations
and prints anything that looks like text, a known file signature or a high
entropy region.

## Reading the output

Each result line starts with the encoding it was found in, for example:

```
b1,r,lsb,xy         .. text: "hidden message"
b1,rgb,lsb,xy       .. file: Zip archive data
b2,g,msb,yx         .. text: "AAAAAAAA"
```

- `b1` — number of bits inspected per channel (1 = LSB only).
- `r`, `g`, `b`, `a`, `rgb`, `bgr` — the channel(s) the bits are read from.
- `lsb`/`msb` — least or most significant bit first.
- `xy`/`yx` — pixel iteration order.

Short repeated strings (like `AAAA`) are usually noise. Real payloads tend
to be readable sentences, flags, or `file:` matches such as Zip or PNG
signatures.

## Useful local flags

```console
$ zsteg -a image.png        # try ALL known combinations (slow, thorough)
$ zsteg -E "b1,rgb,lsb,xy" image.png > payload.bin   # extract one payload
$ zsteg --lsb image.png     # only LSB combinations
```

`-E` extracts the raw bytes of a specific combination — pipe it to a file
and inspect it with `file`, `xxd` or `binwalk`.

## Installing locally

```console
$ gem install zsteg
```

## Limitations

- PNG and BMP only. For JPEG, use [steghide](/wiki/tools/steghide), jsteg or
  outguess instead — JPEG stores DCT coefficients, not raw pixels.
- zsteg detects *simple* LSB schemes. Payloads embedded with a password-based
  pseudo-random pixel order (e.g. LSB with a PRNG seed) will not appear.

## Common CTF patterns

- A flag directly readable in `b1,rgb,lsb,xy` — the classic.
- A Zip or PNG file hidden in the LSBs: extract with `-E`, then unzip/open.
- Data only in one channel (`b1,r,lsb,xy`) — check every channel line.
- Multi-bit encodings (`b2`, `b4`) for larger payloads.
