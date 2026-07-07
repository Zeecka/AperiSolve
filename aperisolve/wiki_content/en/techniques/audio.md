Title: Audio Steganography - Spectrograms, LSB, SSTV & DTMF
Description: How data hides in audio and how to recover it: spectrogram-drawn messages, WAV sample LSB, DTMF and SSTV signalling, Morse and FSK tones, DeepSound and MP3Stego containers, and WAV header tricks.
Order: 20

# Audio steganography

Audio carries hidden data in ways an image cannot: a message can be **drawn in
the frequency spectrum**, encoded in **sample LSBs**, or transmitted as a
**signal** (DTMF, SSTV, Morse, FSK) that needs the right decoder. When you get
an audio file, always look at the spectrogram first.

[TOC]

## Spectrogram (always first)

The most common audio trick by far: text or a QR code **painted into the
frequency domain**. It is inaudible in normal playback and invisible in the
waveform, but jumps out of a spectrogram.

- **[Audacity](https://www.audacityteam.org/)** — switch the track to
  *Spectrogram* view; adjust the frequency range, switch to log scale, and raise
  the contrast.
- **[Sonic Visualiser](https://www.sonicvisualiser.org/)** — *Layer > Add
  Spectrogram*; better color maps for faint marks.
- **CLI one-shot:**

```console
$ sox file.wav -n spectrogram -o spec.png
```

![Audacity spectrogram](/static/img/cheatsheet/audacity_1.png)

Zoom out (right-click the scale) or switch to logarithmic mode to see the whole
range.

![Audacity spectrogram, log scale](/static/img/cheatsheet/audacity_2.png)

!!! tip "Check inaudible bands"
    Messages hide **above 20 kHz** and **below 20 Hz** where you cannot hear
    them. Scan the full spectrum, not just the audible band.

## Sample LSB (WAV)

Lossless WAV samples have LSBs just like image pixels. If the spectrogram is
clean, extract the LSBs:

```console
$ stegolsb wavsteg -r -i file.wav -o out.txt -n 1 -b 1000
```

Try `-n 2` for two-bit encodings, and inspect the result with
`file out.txt` / `xxd`.

## Signalling: DTMF, SSTV, Morse, FSK

Audio is a communications channel, and CTFs reuse classic encodings:

| Encoding | What it is | Decode with |
|----------|-----------|-------------|
| **DTMF** | Phone-keypad dual tones | [dialabc](http://dialabc.com/sound/detect/), `multimon-ng` |
| **SSTV** | Slow-scan TV — images over audio | [QSSTV](https://doc.ubuntu-fr.org/qsstv), RX-SSTV |
| **Morse** | On/off tones, visible in the waveform | by ear / CW decoder / `multimon-ng` |
| **FSK / modem** | Frequency-shift keying | `minimodem -f file.wav 45` (try 300/1200/2400 baud) |

`multimon-ng` decodes several of these (DTMF, Morse, POCSAG) from a piped audio
stream.

## Password-protected containers

- **[steghide](/wiki/tools/steghide)** hides data in WAV and AU with a
  passphrase — try the empty password, then a wordlist.
- **DeepSound** is a popular Windows CTF tool that hides (AES-encrypted) data in
  WAV/FLAC/MP3/APE. Guess the key from the media, filename or challenge name.

![DeepSound](/static/img/cheatsheet/DeepSound.png)

- **MP3Stego** hides data during WAV→MP3 compression (3DES-protected).

## WAV header tricks

Like PNG, a WAV file stores its data length in the header. Shrinking or growing
the `DataSize` block with a hex editor can hide or reveal a trailing section of
the audio — check whether the declared size matches the file.

## Related

- Drive a challenge from the [cheatsheet](/wiki/cheatsheet#audio).
- Raw, headerless audio: import it into Audacity via the
  [methodology raw-data tips](/wiki/methodology).
