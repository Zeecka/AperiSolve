Title: Steganography CTF Cheatsheet - Decision Tree
Description: A steganography decision tree for CTF players: a by-file-type triage flow, frequency-ordered checklists for PNG, JPEG, GIF, audio, text and archives, a Tell to Tool lookup table, and a when-stuck checklist.

# Cheatsheet

<button type="button" class="wiki-print-btn" onclick="window.print()"><i class="fa fa-print"></i> Print / save as PDF</button>

## Disclaimer

This cheatsheet guides CTF players and forensic analysts through the common
cases. It is not representative of modern academic steganography/steganalysis,
and following it will not, on its own, help you *build* an interesting
challenge 😉. For the reasoning behind the order below, read the
[methodology](/wiki/methodology).

## Decision tree {: #triage }

Identify the real file type with [`file`](/wiki/tools/file), pick your branch in
the map below, then work top to bottom — each branch is ordered
**most-common first**. The detailed checklists follow the map.

[![Steganography decision tree: identify the file type, then work each branch top to bottom](/static/img/cheatsheet/decision-tree.svg)](/cheatsheet/map){: .decision-map }

[Open the full-screen interactive map](/cheatsheet/map){: .decision-map-cta }

*Hover any step on the [interactive map](/cheatsheet/map) for the full command, a
one-line explanation and a link to the tool — and download the whole tree as PNG
or PDF. Prefer to remix it? Grab the
[editable source](/static/img/cheatsheet/decision-tree.excalidraw) for
[excalidraw.com](https://excalidraw.com).*

**Run these on every file first (all file types):**

- `file target` — trust it over the extension.
- `exiftool -a -u -g1 target` — Comment/Artist/GPS fields; extract the
  thumbnail (`exiftool -b -ThumbnailImage target > thumb.jpg`).
- `strings -n 8 target` — add `-e l` / `-e b` for UTF-16 text.
- `binwalk target` — then `binwalk -e target` if it lists a second file.

## Image challenges {: #image }

Lossless formats (PNG, BMP) hide data in pixel bits; lossy JPEG hides it in DCT
coefficients — so the tools differ. **Full command checklist:**
[Image cheatsheet](/wiki/cheatsheet/image). Background:
[Images technique page](/wiki/techniques/images).

### PNG / BMP {: #png }

1. **LSB text or files** → `zsteg -a file.png`, then extract the promising line
   with `zsteg -E 'b1,rgb,lsb,xy' file.png > out.bin`.
   [zsteg](/wiki/tools/zsteg)
2. **Corrupt or edited structure** → `pngcheck -vtp7 file.png`. A CRC error in
   `IHDR` means an edited header; a shrunken width/height hides pixels below the
   visible image. Repair with [PCRT](/wiki/tools/pcrt) or brute-force the
   dimensions against the stored CRC.
3. **Visual reveal** → browse every bit plane and **every channel including
   alpha** with the [decomposer](/wiki/tools/decomposer) or Stegsolve; try
   **MSB** and column-major order, not just RGB LSB.
4. **Appended data** → data after the `IEND` chunk; `binwalk` /
   [foremost](/wiki/tools/foremost), or carve the trailer by offset.
5. **Palette tricks** (indexed PNG) → randomize/remap the palette with
   [color remapping](/wiki/tools/color_remapping).
6. **Randomized LSB** → [OpenStego](/wiki/tools/openstego) (`openstego extract`).

!!! tip "Check the alpha channel and MSB"
    zsteg reports the common combinations, but payloads hidden in the alpha
    channel, in the most-significant bit, or in column-major order are the
    classic "zsteg found nothing" traps. Browse all 32 planes.

### JPEG {: #jpg }

JPEG recompression destroys pixel LSBs, so [zsteg](/wiki/tools/zsteg) does
**not** work here.

1. **Passworded payload** → `steghide info file.jpg`, then
   `steghide extract -sf file.jpg -p ''` (try the empty password first).
   [steghide](/wiki/tools/steghide)
2. **Unknown password** → `stegseek file.jpg /usr/share/wordlists/rockyou.txt`
   (cracks rockyou in seconds). [stegseek](/wiki/tools/stegseek)
3. **Not steghide** → `outguess -r file.jpg out.txt`
   ([OutGuess](/wiki/tools/outguess)), `jsteg reveal file.jpg out.txt`
   ([jsteg](/wiki/tools/jsteg)), or JPHide ([jpseek](/wiki/tools/jpseek)).

!!! warning "Guess the password before brute-forcing"
    The passphrase is often the filename, the challenge name, the image
    subject, or a string sitting in `strings` / `exiftool` output. Try those
    before rockyou.

### GIF / APNG {: #gif }

1. **Hidden frames** → animations can carry zero-duration frames. Extract every
   frame: `ffmpeg -i file.gif -vsync 0 out/f%d.png` (or `gifsicle --explode`).
2. **Message in frame durations** → the per-frame delays can encode
   morse/binary/ASCII.
3. **Diff consecutive frames** → a payload can live in the difference between
   two near-identical frames.
4. **Palette** → same indexed-color tricks as PNG.

## Audio {: #audio }

**Full command checklist:** [Audio cheatsheet](/wiki/cheatsheet/audio).
Background: [Audio technique page](/wiki/techniques/audio).

1. **Spectrogram** (always first) → view the frequency domain in
   [Audacity](https://www.audacityteam.org/), Sonic Visualiser, or
   `sox file.wav -n spectrogram -o spec.png`. Text and QR codes are often
   *drawn* there — check above 20 kHz and below 20 Hz too.
2. **Waveform / Morse** → obvious on/off bursts in the waveform.
3. **WAV LSB** → `stegolsb wavsteg -r -i file.wav -o out.txt -n 1 -b 1000`.
4. **SSTV / DTMF / FSK** → decode images with QSSTV, phone tones with a DTMF
   decoder, modem tones with `minimodem` / `multimon-ng`.
5. **Passworded container** → [steghide](/wiki/tools/steghide) (WAV/AU) or
   DeepSound.

## Video {: #video }

Full detail: [Video technique page](/wiki/techniques/video).

1. **Count the streams** → `ffprobe file.mp4` / `mediainfo`. An extra subtitle,
   attachment or data track is often the whole trick.
2. **Extract frames** → `ffmpeg -i file.mp4 -vsync 0 out/f%05d.png`, then run the
   PNG checklist (zsteg, bit planes) on the lossless frames.
3. **Subtitle / attachment tracks** → `ffmpeg -i file.mkv -map 0:s:0 subs.srt`;
   `ffmpeg -dump_attachment:t "" -i file.mkv` for attached files.
4. **Audio track** → `ffmpeg -i file.mp4 -vn audio.wav`, then spectrogram first.
5. **Metadata & trailing data** → `exiftool`, `binwalk`, bytes past the `moov`
   atom.

## Text & Unicode {: #text }

**Full command checklists:** [Text cheatsheet](/wiki/cheatsheet/text) ·
[Encodings & esolangs cheatsheet](/wiki/cheatsheet/encodings). Background:
[Text & Unicode technique page](/wiki/techniques/text).

1. **Whitespace encoding** → trailing spaces/tabs. Reveal with `cat -A file.txt`;
   extract with `stegsnow -C file.txt`. [stegsnow](/wiki/tools/stegsnow)
2. **Zero-width characters** (U+200B/C/D) → invisible; inspect code points with
   `xxd` or a zero-width decoder. Compare `wc -c` to the visible length.
3. **Homoglyphs** (Latin `a` vs Cyrillic `а`) → an Irongeek homoglyph decoder.
4. **Encodings & esolangs** → [CyberChef](https://gchq.github.io/CyberChef/)
   *Magic*; Brainfuck/Whitespace/Piet/Malbolge via
   [esolangs.org](https://esolangs.org/wiki/Language_list).

## Files & Archives {: #polyglot }

**Full command checklists:** [Files & Archives cheatsheet](/wiki/cheatsheet/files) ·
[Passwords & brute-force cheatsheet](/wiki/cheatsheet/brute-force) ·
[Network / PCAP cheatsheet](/wiki/cheatsheet/network). Background:
[Files & Archives technique page](/wiki/techniques/files-archives).

1. **Appended archive** → `unzip file.png` / `7z l file.png` often just works;
   otherwise `binwalk -e`. [binwalk](/wiki/tools/binwalk)
2. **Polyglot** → a file valid as two formats (PDF/ZIP, JPEG/ZIP, GIF/JS).
   `file` will not flag it; check for multiple magic numbers and trailing data.
3. **Documents** → `.docx`/`.pptx`/`.jar`/`.apk` are ZIPs: `7z x file.docx`.
   PDFs: `pdfdetach -list` / `pdfdetach -saveall`, inspect streams.
4. **Password-protected ZIP** → `fcrackzip -u -D -p rockyou.txt file.zip`
   (ZipCrypto is weak; AES-256 is not).

## Tell → Tool lookup {: #tell-tool }

Jump straight to a technique from the symptom.

<input type="search" id="tell-tool-filter" class="form-control form-control-sm mb-3" placeholder="Filter symptoms and tools…" aria-label="Filter the tell-to-tool table" autocomplete="off">

| Tell (symptom)                              | Try this                                   |
|---------------------------------------------|--------------------------------------------|
| File is much bigger than it looks           | [`binwalk -e`](/wiki/tools/binwalk) · `unzip` |
| A `CTF{`-ish string in plain `strings`      | [`strings -n 8`](/wiki/tools/strings), `-e l`/`-e b` |
| Odd EXIF Comment / weird metadata           | [`exiftool -a -u -g1`](/wiki/tools/exiftool) |
| PNG/BMP, nothing in metadata                | [`zsteg -a`](/wiki/tools/zsteg)            |
| LSB plane looks like random noise           | encrypted LSB — need the tool + password ([cloacked-pixel…](/wiki/techniques/images#lsb-bit-planes-and-channels)) |
| Image won't open / looks cropped            | [`pngcheck -vtp7`](/wiki/tools/pngcheck) · [PCRT](/wiki/tools/pcrt) |
| CRC error in IHDR                           | edit header / brute-force dimensions       |
| JPEG + a password hint                      | [`steghide`](/wiki/tools/steghide) · [`stegseek rockyou`](/wiki/tools/stegseek) |
| JPEG, steghide fails                        | [`outguess`](/wiki/tools/outguess) · [`jsteg`](/wiki/tools/jsteg) |
| Static / blocks in an audio file            | spectrogram, high-res (Audacity / `sox -X -Y`) |
| Stereo audio, silent when summed to mono    | isolate / subtract channels (`sox … remix`) |
| Clean WAV, nothing in spectrogram           | `stegolsb wavsteg`                         |
| WAV LSB output is all null bytes            | skip leading zeros; try `-n 1` and `-n 2` |
| A video file (mp4/mkv/avi)                  | [`ffprobe`](/wiki/techniques/video) → extract frames · subtitle/attachment tracks |
| An ELF / PE / Mach-O executable             | [steg86](/wiki/techniques/files-archives#executables-and-binaries) · section / appended data |
| Invisible / trailing spaces in a `.txt`     | [`stegsnow -C`](/wiki/tools/stegsnow) · `cat -A` |
| Text copies "wrong" / mixed alphabets       | zero-width / homoglyph decoder             |
| Text too short / an emoji "holds" data      | tag (U+E00xx) & variation-selector decoder |
| `.docx` / `.jar` / `.apk`                   | `7z x` (it is a ZIP)                        |
| ZipCrypto zip + a known inner file          | [bkcrack](https://github.com/kimci86/bkcrack) known-plaintext |
| PDF with more than one `%%EOF`              | `pdfresurrect -w` (old revisions)          |
| A QR / barcode in a file                    | `zbarimg --raw`                            |
| Recovered a blob, not yet the flag          | [CyberChef Magic](/wiki/techniques/encodings) · [dcode.fr](https://www.dcode.fr/) |
| Nothing works, unknown blob                 | [binvis.io](http://binvis.io/) · raw import (GIMP/Audacity) |

## When stuck, check these {: #stuck }

The recurring misses, from CTF writeups:

1. Re-run `strings` with `-e l` / `-e b`, and extract the **EXIF thumbnail** —
   it sometimes shows the original, uncensored image.
2. `binwalk` / `foremost` for **appended archives**; try `unzip file.png`
   directly.
3. Browse **every** bit plane and **every** channel (R/G/B/**Alpha**), and try
   **MSB**, **inverted**, and **column-major** order — not just RGB LSB.
4. On JPEG, always try the **empty steghide password**, then `stegseek rockyou`,
   and also try the **filename / challenge name / metadata** as the passphrase.
5. `pngcheck -vtp7` — a **CRC error in IHDR** means an edited header; check for
   a **shrunken width/height** hiding pixels and brute-force the dimensions
   against the stored CRC.
6. Indexed PNG/GIF: **randomize the palette**; for GIF/APNG check
   **zero-duration frames** and **frame durations**.
7. Audio: **spectrogram first**, then waveform **Morse**, then **WAV LSB**, then
   SSTV/DTMF.
8. Text files: look for **trailing whitespace/tabs** and
   **zero-width/homoglyph** Unicode; compare `wc -c` to the visible length.
9. Reverse-image-search (Google/Yandex) for the **original cover**, then XOR the
   stego against it in Stegsolve to isolate the edits.
10. Reduce a media **header size** (WAV DataSize, PNG height) to reveal a
    cropped-out region.
11. **Match the tool to the carrier**: steghide handles JPEG/BMP/WAV but *not*
    PNG/GIF, and zsteg handles PNG/BMP but *not* JPEG — using the wrong one is
    the most common stall. Repair a broken PNG (`pngcheck -f`) before zsteg, and
    remember audio LSB payloads often **don't start at sample 0**.

## References {: #more }

- [Aperi'Kube Blog — Steganography](https://www.aperikube.fr/cat/steg/)
- [CTFtime — Steganography writeups](https://ctftime.org/writeups?tags=steg&hidden-tags=stego%2Csteganography%2Cstega%2Csteg)
- [ctf.support — Steganography](https://ctf.support/steganography/image-steganography/)
- [StegOnline CTF image checklist](https://georgeom.net/StegOnline/checklist)
- [Root-Me — Steganography challenges](https://www.root-me.org/en/Challenges/Steganography/)
- [Corkami — file-format posters](http://corkami.github.io/)
