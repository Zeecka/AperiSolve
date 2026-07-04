Title: identify - Inspect Image Properties with ImageMagick
Description: How ImageMagick's identify -verbose exposes image format, depth, colorspace, statistics and embedded text properties where CTF challenges hide data.
Order: 230

# identify

[identify](https://imagemagick.org/script/identify.php) is ImageMagick's
inspection command: it decodes an image and reports **everything the
decoder knows** — format, geometry, bit depth, colorspace, per-channel
statistics and every embedded text property.

## What Aperi'Solve runs

```console
$ identify -verbose image
```

Aperi'Solve's container provides `identify` through GraphicsMagick's
ImageMagick compatibility layer, so the output formatting is
GraphicsMagick's — the fields are the same.

## Reading the output

```
Image: image.png
  Format: PNG (Portable Network Graphics)
  Geometry: 800x600
  Depth: 8 bits-per-pixel component
  Colorspace: sRGB
  Channel Statistics: ...
```

`-verbose` also lists resolution, interlacing, compression, the number of
unique colors, and — most interesting for CTFs — free-form text stored in
the file: comments and key/value properties (PNG `tEXt`/`zTXt` chunks,
JPEG comments).

## Fields that hide data

- **Comment / Properties** — arbitrary strings travel here; a Base64 blob
  in a `comment:` line is a classic. Cross-check with
  [exiftool](/wiki/tools/exiftool), which decodes more metadata formats.
- **Depth** — a 16-bit PNG that visually needs only 8 bits suggests a
  payload in the low bytes; inspect with the
  [bit-plane decomposer](/wiki/tools/decomposer).
- **Geometry** — compare against what pngcheck reports and against the
  file size; a mismatch hints at truncated or altered headers (see
  [pngcheck](/wiki/tools/pngcheck)).
- **Colors / statistics** — thousands of unique colors in flat pixel art,
  or channel noise statistics that differ between channels, betray
  embedded data.

## Installing locally

```console
$ apt install imagemagick
```

or, for the GraphicsMagick flavor Aperi'Solve uses:

```console
$ apt install graphicsmagick graphicsmagick-imagemagick-compat
```

## Limitations

- identify reports what the decoder sees — it does not scan for appended
  files (use [binwalk](/wiki/tools/binwalk)) or LSB payloads (use
  [zsteg](/wiki/tools/zsteg)).
- Malformed images may fail to decode at all; repair them first with
  [PCRT](/wiki/tools/pcrt).

## Common CTF patterns

- A flag or hint sitting in plain sight in the `comment` property.
- A Base64/hex string in a custom PNG `tEXt` property, invisible in normal
  viewers.
- An unusual bit depth or colorspace flagging which extraction technique
  to try next.
