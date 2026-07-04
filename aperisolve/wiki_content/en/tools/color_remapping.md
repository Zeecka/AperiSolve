Title: Color Remapping - Reveal Hidden Data with Palette Transforms
Description: How Aperi'Solve's color remapping analyzer applies random 256-value lookup tables to image channels to make near-invisible steganography stand out.
Order: 150

# Color remapping

Color remapping is Aperi'Solve's own analyzer (pure Python, using Pillow
and NumPy). It replaces every color value in the image through a **random
256-entry lookup table**, so pixel values that were almost identical — and
therefore invisible to the eye — end up mapped to wildly different colors.

## What Aperi'Solve does

For each upload, the analyzer generates **8 remapped variants**
(`color_remapping_00.png` through `color_remapping_07.png`). Each variant
uses one random lookup table mapping every value 0–255 to a new random
value, applied identically to the red, green and blue channels. The alpha
channel, if present, is kept untouched.

Grayscale images are expanded to RGB first, and palette (indexed) images
are converted to RGB — the result page notes when this conversion happened.

## Why remapping reveals steganography

A classic trick hides a message by drawing it in a color *one step away*
from the background — value 254 on a 255 background, invisible on screen.
A random remap sends 254 and 255 to two unrelated colors, so the message
suddenly appears in sharp contrast.

Because each of the 8 maps is random, a pattern that stays muted in one
variant usually pops in another — scan all eight before concluding there
is nothing.

## Reading the results

- **Text, shapes or QR codes** appearing in any variant that are invisible
  in the original — that is the payload.
- **Flat regions turning noisy** (or noisy regions turning flat) hint at
  data blended into low-order values; confirm with the
  [bit-plane decomposer](/wiki/tools/decomposer) and
  [zsteg](/wiki/tools/zsteg).
- If all 8 variants look like pure static, the image is probably a photo
  with natural noise — remapping amplifies noise too.

## Reproducing locally

No external tool to install — a few lines of Python do the same thing:

```python
import numpy as np
from PIL import Image

img = np.array(Image.open("image.png").convert("RGB"))
lut = np.random.randint(0, 256, 256, dtype=np.uint8)
Image.fromarray(lut[img]).save("remapped.png")
```

Run it a few times: each run is a new random map.
[StegSolve](https://github.com/Giotino/stegsolve)'s "Random colour map"
filters (browse with the arrow buttons) offer the same idea interactively.

## Limitations

- Purely visual: it shows you where data hides but extracts nothing. Use
  [zsteg](/wiki/tools/zsteg) to pull out the actual bytes.
- Payloads spread across bits pseudo-randomly (password-seeded LSB) do not
  form visible shapes under any color map.

## Common CTF patterns

- A flag written in color 254 on a 255 background — invisible until
  remapped.
- A watermark hidden as a barely different shade inside a logo.
- A QR code drawn one gray level apart from its surroundings.
