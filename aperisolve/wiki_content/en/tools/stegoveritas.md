Title: stegoveritas - Image Transforms for Visual Steganography
Description: How Aperi'Solve runs StegoVeritas' image transforms (filters, colour planes, sharpness, inversions) on deep analysis, what is left out because the decomposer covers it, and how to use it locally.
Order: 125

# stegoveritas

[stegoVeritas](https://github.com/bannsec/stegoVeritas) brute-forces common
image hiding tricks. Aperi'Solve uses its **image transforms**: edge and
blur filters, single colour planes, sharpness extremes, auto-contrast,
equalisation, inversion and solarisation. It is a good catch-all when you
suspect visual steganography but no specialized tool has hit yet.

## What Aperi'Solve runs

Only on **deep analysis**, for every image. Aperi'Solve does not run the
`stegoveritas` command: it calls StegoVeritas' transform functions directly,
one after the other, in an isolated environment. That is deliberate:

- **No bit planes.** The [decomposer](/wiki/tools/decomposer) already renders
  every Red, Green, Blue and Alpha plane, so they are not computed twice.
- **No LSB brute force, carving, steghide or EXIF.** Other analyzers
  ([zsteg](/wiki/tools/zsteg), [foremost](/wiki/tools/foremost),
  [steghide](/wiki/tools/steghide), [exiftool](/wiki/tools/exiftool)) do these
  better.
- Palette images are converted to RGB first, so they get transforms too.
- Sizes above the 64 megapixel limit are refused, with an error, before the
  image is decoded.

The results are one **Transforms** gallery. Animated GIFs and APNGs are
transformed on their first frame; their frames have their own
[stegoveritas frames](/wiki/tools/stegoveritas_frames) result.

If Pillow refuses a transform for the image mode (for instance inversion on
an image with transparency), that transform is skipped and the note on the
result lists it.

## Reading the output

Each image is one filter applied to the whole input: look for text, QR codes
or shapes that only appear under one specific transform.

## Running it manually

Aperi'Solve's subset is easy to reproduce with the StegoVeritas CLI, which
also writes the bit planes:

```console
$ stegoveritas -imageTransform image.png
$ ls results/
```

## Installing locally

```console
$ pip install stegoveritas
$ stegoveritas_install_deps
```

## Common CTF patterns

- A message readable only after inversion or a specific colour filter.
- Text that appears in the sharpness-enhanced or edge-detected variant.
