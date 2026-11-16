Title: stegoveritas - Image Transforms and GIF Frame Extraction
Description: How StegoVeritas applies image transforms and extracts GIF frames, how Aperi'Solve runs it alongside the bit-plane decomposer, and how to use it locally.
Order: 125

# stegoveritas

[stegoVeritas](https://github.com/bannsec/stegoVeritas) brute-forces common
image hiding tricks: it applies a battery of **image transforms** (color
inversions, LSB visualizations, sequential filters) and **extracts frames**
from animated GIFs. It is a good catch-all when you suspect visual
steganography but no specialized tool has hit yet.

## What Aperi'Solve runs

```console
$ stegoveritas -imageTransform -extract_frames image.png
```

- `-imageTransform` renders the transformed variants.
- `-extract_frames` dumps every frame of an animated GIF.

Results are grouped as **Transforms** and **Frames**. Per-channel bit
planes are intentionally left out here — the
[decomposer](/wiki/tools/decomposer) already renders the Red, Green, Blue
and Alpha planes, so StegoVeritas only shows the extra transforms plus GIF
frames to avoid duplicates.

When anything is extracted, the result page offers the files as a `.7z`
download.

## Reading the output

Each image in **Transforms** is one filter applied to the whole input: look
for text, QR codes or shapes that only appear under one specific transform.
Each image in **Frames** is one GIF frame — step through them for
frame-by-frame differences, hidden flashes or appended frames.

## Extracting manually

Run the same flags locally and inspect the `results/` directory:

```console
$ stegoveritas -imageTransform -extract_frames image.png
$ ls results/
```

## Installing locally

```console
$ pip install stegoveritas
$ stegoveritas_install_deps
```

## Common CTF patterns

- A message readable only after inversion or a specific color filter.
- A GIF whose hidden frame flashes for a single frame.
- Trailing data after the last frame that only frame extraction reveals.
