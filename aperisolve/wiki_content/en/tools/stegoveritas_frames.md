Title: stegoveritas frames - Extract Every Frame of an Animated GIF or APNG
Description: How Aperi'Solve splits animated GIFs and APNGs into individual frames with StegoVeritas, when it runs, and how to do it locally.
Order: 126

# stegoveritas frames

Animated GIFs and APNGs can hide data in a single frame: a flash of text
that lasts one tick, a QR code, an extra frame appended after the loop.
Aperi'Solve splits the animation with
[StegoVeritas](https://github.com/bannsec/stegoVeritas)' frame extraction
and shows every frame as an image.

## When it runs

Only for **animated GIF and APNG** uploads (more than one frame). Still
images never start it, and it does not need the deep analysis option.

Animations of more than **100 frames** are refused with an error that names
the limit: every frame is written at full size, so the count is checked
before anything is extracted.

## What you get

- The **Frames** gallery, in animation order.
- A `.7z` download with all the frame files.

GIF frames are composited (what a viewer shows at that point); APNG frames
are the frame images stored in the file, so a frame can be smaller than the
canvas.

## Extracting manually

```python
from PIL import Image, ImageSequence

with Image.open("anim.gif") as im:
    for i, frame in enumerate(ImageSequence.Iterator(im)):
        frame.convert("RGBA").save(f"frame_{i}.png")
```

## Common CTF patterns

- A hidden frame that flashes for one tick of the animation.
- Frames whose pixels differ only in the low bits: send them to the
  [decomposer](/wiki/tools/decomposer) one by one.
- Data appended after the last frame: see [binwalk](/wiki/tools/binwalk).
