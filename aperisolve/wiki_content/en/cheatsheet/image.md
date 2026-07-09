Title: Image Steganography Cheatsheet - PNG, JPEG, GIF Commands
Description: A copy-paste command checklist for image steganography CTFs: zsteg/pngcheck/bit-plane recipes for PNG and BMP, steghide/stegseek/outguess for JPEG, and frame/palette tricks for GIF and APNG, ordered most-common first.
NavTitle: Image
Order: 10

# Image cheatsheet

Copy-paste command recipes for image challenges, ordered **most-common first**.
For *why* each works, read the [Images technique page](/wiki/techniques/images);
to triage across file types, use the [decision tree](/cheatsheet#triage).

**Identify the real format first — the branch depends on it:**

```console
$ file image.*
$ identify -verbose image.png | head -n 40   # GraphicsMagick/ImageMagick
```

## PNG / BMP {: #png-bmp }

Lossless: data hides in the raw pixel bits, so LSB tools work.

```console
$ zsteg image.png                       # common bit/channel combos
$ zsteg -a image.png                     # ALL combos: every channel, bit, order
$ zsteg -E 'b1,rgb,lsb,xy' image.png > out.bin   # extract one combo to a file
$ file out.bin && binwalk out.bin        # what did we pull?
```

```console
$ pngcheck -vtp7f image.png              # structure, CRCs, text chunks
$ zlib-flate -uncompress < idat.bin      # manually inflate a raw IDAT if needed
```

- **CRC error in `IHDR`** → an edited header; a shrunken width/height hides pixel
  rows below the visible image. Repair with [PCRT](/wiki/tools/pcrt) or
  brute-force the dimensions against the stored CRC.
- **Data after `IEND`** → the PNG ends at `IEND`; anything after is appended.
  `binwalk -e image.png`, or carve the trailer by offset.
- **Bit planes / channels** → browse **all 32 planes** (R/G/B/**Alpha** × 8 bits)
  with the [bit-plane decomposer](/wiki/tools/decomposer) or Stegsolve
  (*Analyse → Data Extract*). Try **MSB**, **inverted**, and **column-major**
  order, not just RGB LSB.
- **Indexed (palette) PNG/BMP** → remap the palette with
  [color remapping](/wiki/tools/color_remapping); two near-identical palette
  entries hide a bilevel image.
- **Randomized LSB (PRNG order)** → zsteg won't see it; try
  [OpenStego](/wiki/tools/openstego) `extract -sf image.png` (with a password),
  or `stegoveritas image.png` to run the whole battery at once.

!!! tip "The 'zsteg found nothing' traps"
    Payloads in the **alpha** channel, in the **MSB**, or in **column-major**
    order are the classic misses. `zsteg -a` covers most, but confirm by
    browsing every plane visually.

## JPEG {: #jpeg }

Lossy DCT: recompression destroys pixel LSBs, so [zsteg](/wiki/tools/zsteg) does
**not** apply. These tools read the DCT coefficients instead.

```console
$ steghide info image.jpg                 # is there a steghide payload?
$ steghide extract -sf image.jpg -p ''    # ALWAYS try the empty password first
$ steghide extract -sf image.jpg -p 'guess'
```

```console
$ stegseek image.jpg /usr/share/wordlists/rockyou.txt   # cracks rockyou in seconds
$ stegseek --seed image.jpg               # detect a steghide payload w/o wordlist
```

```console
$ outguess -r image.jpg out.txt           # OutGuess payload
$ jsteg reveal image.jpg out.txt          # jsteg LSB of DCT coeffs
$ stegdetect -t opjf image.jpg            # statistical: outguess/jphide/jsteg/f5
```

- **JPHide** → extract with `jphide`/[jpseek](/wiki/tools/jpseek), or crack with
  `stegbreak -t p -f rockyou.txt image.jpg`.
- **Exotic / F5** → `java -jar f5.jar x -p password image.jpg` (Extract), or
  check the [steganalysis page](/wiki/techniques/steganalysis) for detectors.

!!! warning "Guess the passphrase before brute-forcing"
    The password is often the **filename**, the **challenge name**, the image
    **subject**, or a string already sitting in `strings` / `exiftool` output.
    Try those before rockyou. See the
    [brute-force cheatsheet](/wiki/cheatsheet/brute-force).

## GIF / APNG {: #gif }

Animations carry data in frames, timings and palettes.

```console
$ identify image.gif                      # lists every frame + delay
$ convert image.gif -coalesce out/f%03d.png   # explode to full frames
$ ffmpeg -i image.gif -vsync 0 out/f%d.png     # alternative
$ gifsicle --explode image.gif -o frame       # frame-per-file (frame.000…)
```

- **Zero-duration / hidden frames** → a frame with `0` delay flashes invisibly;
  check the `identify` delays column.
- **Message in frame durations** → the per-frame delays can encode
  morse/binary/ASCII (`identify -format "%T " image.gif`).
- **Diff consecutive frames** → `compare f000.png f001.png diff.png` — payload in
  the delta of two near-identical frames.
- **Palette tricks** → same indexed-color remapping as PNG.

## WebP / TIFF / other {: #other }

```console
$ dwebp image.webp -o image.png           # convert, then treat as PNG
$ exiftool -a -u -g1 image.tiff           # TIFF hides plenty in tags
$ magick image.bmp image.png              # normalise odd BMP variants
```

## Related

- Tools: [zsteg](/wiki/tools/zsteg) · [pngcheck](/wiki/tools/pngcheck) ·
  [PCRT](/wiki/tools/pcrt) · [decomposer](/wiki/tools/decomposer) ·
  [color remapping](/wiki/tools/color_remapping) ·
  [steghide](/wiki/tools/steghide) · [stegseek](/wiki/tools/stegseek) ·
  [OutGuess](/wiki/tools/outguess) · [jsteg](/wiki/tools/jsteg) ·
  [jpseek](/wiki/tools/jpseek) · [OpenStego](/wiki/tools/openstego).
- Depth: [Images technique page](/wiki/techniques/images) ·
  [Steganalysis](/wiki/techniques/steganalysis).
