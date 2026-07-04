Title: PCRT - Detect and Repair Corrupted PNG Files
Description: How Aperi'Solve's embedded PCRT port repairs broken PNG signatures, recovers zeroed IHDR dimensions by CRC brute force, and extracts data hidden after IEND.
Order: 170

# PCRT

[PCRT](https://github.com/sherlly/PCRT) (PNG Check & Repair Tool) detects
and **automatically repairs** corrupted PNG files. Aperi'Solve embeds its
own Python port, based on sherlly/PCRT and the PCRT3 forks by
[indonumberone](https://github.com/indonumberone/PCRT3) and
[Etr1x](https://github.com/Etr1x/PCRT3). Where
[pngcheck](/wiki/tools/pngcheck) only diagnoses, PCRT fixes.

## What Aperi'Solve runs

The port runs in-process (no external command). The upload must at least
contain `IHDR`, `IDAT` and `IEND` markers to be treated as a PNG; it is
then checked and rebuilt section by section:

- **Signature** — a tampered first 8 bytes is restored to
  `89 50 4E 47 0D 0A 1A 0A`.
- **IHDR** — the CRC is verified. On mismatch, the stored CRC is looked up
  in a database of known IHDR configurations (common resolutions and bit
  depths); if nothing matches, an exhaustive search recomputes the CRC for
  every width x height from 1 to 4999 (capped at 30 seconds) until it
  matches, recovering zeroed or falsified dimensions.
- **Ancillary chunks** (PLTE, tRNS, gAMA, pHYs...) — copied over with
  their CRCs validated and fixed.
- **IDAT** — a length/data mismatch triggers a DOS-to-Unix recovery
  (re-inserting `\x0d` bytes before `\x0a` candidates until the CRC
  matches); a plain CRC mismatch is recomputed.
- **IEND** — a missing or malformed trailer is replaced by the standard
  12-byte chunk, and any bytes *after* IEND are extracted.

## Reading the output

The log lists each check with offsets, for example:

```
Error IHDR CRC found at offset 0x1d
Chunk crc: 00000000, Correct crc: 575943df
Found correct dimensions via exhaustive search: 800x600
```

When any fix succeeds, the repaired image is saved as
`pcrt_recovered_<name>.png` and offered on the result page — open it to
see what the corruption was hiding. Data found after IEND is saved as
`extra_data.bin` in a downloadable archive.

## Installing locally

```console
$ git clone https://github.com/sherlly/PCRT
$ python PCRT.py -i image.png
```

The original is Python 2 era; the
[PCRT3](https://github.com/indonumberone/PCRT3) forks run on Python 3.

## Limitations

- PNG only, and the file must still contain IHDR/IDAT/IEND markers — for
  a fully mangled file, rebuild the header by hand in a hex editor.
- The exhaustive dimension search covers 1–4999 pixels per side within a
  time budget; extreme sizes may not be recovered.
- Repairing structure does not extract LSB payloads — run
  [zsteg](/wiki/tools/zsteg) on the recovered image too.

## Common CTF patterns

- **Zeroed width/height** in IHDR: the image displays as 0x0 or refuses to
  open, but the untouched CRC lets PCRT brute-force the true dimensions.
- Height shrunk to crop the flag off the bottom — the recovered image
  shows the full picture.
- Signature bytes overwritten so `file` misidentifies the upload.
- A flag or archive appended after IEND — also visible to
  [binwalk](/wiki/tools/binwalk).
