Title: Image Steganography - LSB, Bit Planes, PNG, JPEG & GIF
Description: How data is hidden in images and how to recover it: LSB and bit-plane techniques, PNG chunks and structure tricks, JPEG DCT-domain tools, GIF/APNG frames, palettes and frequency-domain analysis.
Order: 10

# Image steganography

Images are the richest carrier for hidden data. How you attack one depends
entirely on the format: **lossless** formats (PNG, BMP) preserve every pixel
bit, so data hides in the pixels themselves; **lossy** JPEG throws pixel bits
away during compression, so data hides in the DCT coefficients instead. Always
[identify the real format first](/wiki/methodology), then pick the technique.

[TOC]

## LSB, bit planes and channels

Each pixel channel (Red, Green, Blue, Alpha) is a byte — eight **bit planes**
from the least-significant bit (LSB) to the most-significant (MSB). Hiding a
message in the LSBs is nearly invisible to the eye but trivial to extract if you
look at the right plane. Variants you will meet: **LSB replacement**, **LSB
matching**, per-channel or multi-bit encodings, **alpha-channel** payloads,
**palette-index** hiding, and **pixel-value differencing (PVD)**.

**[zsteg](/wiki/tools/zsteg)** — the highest-yield single command for PNG/BMP
LSB. It reportedly cracks about half of all image challenges on its own.

```console
$ zsteg image.png            # common combinations
$ zsteg -a image.png         # every channel/bit/order combination
$ zsteg -E 'b1,rgb,lsb,xy' image.png > payload.bin   # extract one combination
```

**[Bit-plane decomposer](/wiki/tools/decomposer)** (built into Aperi'Solve) and
**Stegsolve** — browse all 32 planes visually. Look for text, a QR code, or
sharp edges appearing in a single plane.

!!! tip "The zsteg-found-nothing traps"
    When zsteg reports nothing, the payload is usually in a place it did not
    try by default: the **alpha channel**, the **most-significant** bit,
    **column-major** (`yx`) order, or a single channel. Browse every plane and
    channel by hand before moving on.

Once a plane looks structured, script the extraction with Pillow:

```python
# pip install Pillow
from PIL import Image
img = Image.open("file.png")
pixels = list(img.getdata())          # [(r, g, b), (r, g, b), ...]
bits = [px[0] & 1 for px in pixels]   # LSB of the red channel
```

**Comparison with the original.** If you can find the cover image (reverse
image search on [Google](https://images.google.com/) or
[Yandex](https://yandex.com/images/)), XOR the two in Stegsolve to isolate
exactly which pixels were altered.

![Stegsolve XOR](/static/img/cheatsheet/stegsolve_xor.png)
![Stegsolve XOR result](/static/img/cheatsheet/stegsolve_xor2.png)

## PNG structure tricks

A PNG is a sequence of **chunks**: `IHDR` (header: width, height, bit depth)
first, one or more `IDAT` (pixel data), `IEND` last, plus optional chunks like
`tEXt`/`zTXt`/`iTXt` (text), `eXIf`, `iCCP` and `PLTE` (palette). Each chunk
carries a CRC32. This structure is a playground for hiding data.

**Validate and enumerate chunks:**

```console
$ pngcheck -vtp7f file.png
$ identify -verbose file.png
```

**Data after `IEND`.** Anything past the `IEND` chunk is ignored by viewers but
survives in the file — a top hiding spot. `pngcheck` flags trailing data; carve
it with [binwalk](/wiki/tools/binwalk) or by offset.

**Corrupt CRC / edited header.** A `CRC error in IHDR` reported by
[pngcheck](/wiki/tools/pngcheck) means the header was edited. The classic trick:
a decoder stops after `height` rows and silently ignores the extra `IDAT`
bytes, so a **shrunken height hides pixels** below the visible image. You cannot
pick dimensions freely — brute-force width/height until the computed CRC matches
the stored `IHDR` CRC (e.g. with
[png-dimensions-bruteforcer](https://github.com/cjharris18/png-dimensions-bruteforcer)),
or repair the file with [PCRT](/wiki/tools/pcrt).

**[TweakPNG](http://entropymine.com/jason/tweakpng/)** edits chunks directly:
recompute CRCs, reorder chunks, or change the declared dimensions.

![TweakPNG](/static/img/cheatsheet/tweakpng.png)

**APNG** (animated PNG) can hold frames a normal viewer never shows — a
zero-duration frame, or a very long first frame. An
[APNG viewer](https://ezgif.com/apng-maker) exposes every frame, and a message
can be encoded in the per-frame durations.

## JPEG (DCT domain)

JPEG stores quantized **DCT coefficients**, not raw pixels, and recompresses on
save — so LSB-in-pixels tools like zsteg are useless here. Dedicated
DCT-domain tools take over:

| Tool | Notes |
|------|-------|
| [steghide](/wiki/tools/steghide) | JPEG/BMP/WAV/AU, password + encryption. Try the empty password. |
| [stegseek](/wiki/tools/stegseek) | Cracks a steghide passphrase against a wordlist in seconds. |
| [OutGuess](/wiki/tools/outguess) | Redundant-bit JPEG stego; `outguess -r file.jpg out.txt`. |
| [jsteg](/wiki/tools/jsteg) | JPEG DCT LSB, no encryption. |
| [jphide / jpseek](/wiki/tools/jpseek) | JPHS, DCT LSB with a password. |
| F5 / f5stegojs | Matrix encoding on DCT coefficients. |
| [OpenStego](/wiki/tools/openstego) | LSB with optional password (mainly PNG). |

```console
$ steghide info file.jpg
$ steghide extract -sf file.jpg -p ''
$ stegseek file.jpg /usr/share/wordlists/rockyou.txt
$ outguess -r file.jpg out.txt
```

For **detection**, `stegdetect` runs statistical DCT analysis (jsteg / jphide /
outguess / F5) — see [Steganalysis](/wiki/techniques/steganalysis).

## GIF

GIFs are animated and use an indexed palette of up to 256 colors, so support in
steganalysis tools is patchy — but a few tricks recur:

- **Hidden frames** with zero duration are not visible during playback.
- A message can be encoded **in the frame durations** (morse/binary/ASCII).
- Data can hide in the **color palette** or the difference between frames.

```console
$ ffmpeg -i file.gif -vsync 0 out/f%d.png       # extract frames
$ gifsicle --explode file.gif                    # alternative frame split
```

[GIF Maker](https://ezgif.com/maker) makes manual GIF manipulation easy.

![GIF Maker](/static/img/cheatsheet/gif_maker.png)

## Palette and color-index tricks

On indexed-color images (PNG-8, GIF), the pixels are indices into a **palette**.
Two near-identical palette entries can hide a second image that only appears
when you remap the colors.

**[Color remapping](/wiki/tools/color_remapping)** (built into Aperi'Solve)
generates several random palette remaps automatically. StegOnline and GIMP let
you browse and randomize the palette by hand.

## Frequency-domain analysis

Some payloads are invisible in the spatial domain but obvious in the frequency
domain. Aperi'Solve, StegOnline and
[Fourifier](https://www.ejectamenta.com/Fourifier-fullscreen/) render the FFT of
an image, where periodic patterns and hidden marks stand out.

## Related

- Drive a challenge from the [cheatsheet decision tree](/wiki/cheatsheet#image).
- Statistical detection: [Steganalysis](/wiki/techniques/steganalysis).
- Appended archives and polyglots:
  [Files & Archives](/wiki/techniques/files-archives).
