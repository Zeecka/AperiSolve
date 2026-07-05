Title: Bit-Plane Decomposer - Visualize Hidden Data in Image Bits
Description: How Aperi'Solve's bit-plane decomposer splits an image into per-channel bit planes and superimposed views to reveal LSB steganography visually.
Order: 140

# Bit-plane decomposer

The decomposer is Aperi'Solve's own analyzer (pure Python, using Pillow and
NumPy). It splits the uploaded image into its **bit planes**: for every
color channel (red, green, blue, alpha — or grayscale) and every bit
position 0–7, it renders a black-and-white image where each pixel shows only
that single bit.

## Why bit planes reveal steganography

In a natural photograph, high bits (7, 6...) carry the visible structure
and low bits look like random noise. LSB steganography overwrites the low
bits with payload data — which is *not* photographic noise. When that
happens, the bit-0 plane suddenly shows:

- clean geometric shapes, text or QR codes,
- uniform regions where noise should be,
- a sharp boundary where the payload ends and true noise resumes.

## Reading the results

Aperi'Solve shows, for each bit position:

1. **Superimposed RGB planes** — the RGB channels of one bit combined into
   a color image. Fastest way to scan all bits.
2. **Per-channel planes** — Red, Green, Blue (and Alpha) separately.
   Payloads often live in a single channel, invisible in the superimposed
   view.

Look at bit 0 and bit 1 first: legitimate image content rarely produces
structure there.

Pay special attention to the **alpha plane** — a fully opaque image has a
constant alpha channel, so *any* texture in the alpha planes is
attacker-added data.

## Extracting what you see

Seeing a QR code or text in a plane is often enough (scan/read it). To
extract embedded *bytes* rather than pixels, use
[zsteg](/wiki/tools/zsteg) with the matching combination, e.g. data visible
in the red LSB plane:

```console
$ zsteg -E "b1,r,lsb,xy" image.png > payload.bin
```

## Reproducing locally

[StegSolve](https://github.com/Giotino/stegsolve) offers the same per-plane
browsing as a desktop Java app, and GIMP's channel decomposition
(`Colors > Components > Decompose`) achieves similar results.

## Common CTF patterns

- A QR code in the bit-0 plane of one channel.
- Text visible only in the alpha channel planes.
- Two images blended: one visible normally, one appearing in low bit planes.
- Payload only in the top strip of the bit plane — the message was shorter
  than the image, encode order `xy`.
