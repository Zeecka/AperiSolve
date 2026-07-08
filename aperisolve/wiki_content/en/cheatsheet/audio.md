Title: Audio Steganography Cheatsheet - Spectrogram, WAV LSB, SSTV
Description: A copy-paste command checklist for audio steganography CTFs: spectrogram first, stereo/phase tricks, WAV sample LSB, SSTV/DTMF/FSK signalling decode, and password-protected containers, ordered most-common first.
NavTitle: Audio
Order: 20

# Audio cheatsheet

Command recipes for audio challenges, ordered **most-common first**. Depth on the
[Audio technique page](/wiki/techniques/audio).

**Always look at the frequency domain before the bytes.**

## Spectrogram (do this first) {: #spectrogram }

Text and QR codes are often *drawn* in the spectrogram — check above 20 kHz and
below 20 Hz too.

```console
$ sox audio.wav -n spectrogram -o spec.png        # quick spectrogram
$ sox audio.wav -n spectrogram -X 500 -y 1025 -o spec.png   # higher resolution
$ ffmpeg -i audio.wav -lavfi showspectrumpic=s=1280x720 spec.png
```

Interactive: open in [Audacity](https://www.audacityteam.org/) (*Spectrogram*
track view) or Sonic Visualiser and zoom the frequency axis.

## Waveform, channels & phase {: #waveform }

```console
$ audacity audio.wav          # eyeball the waveform for Morse on/off bursts
```

- **Stereo channel tricks** → the payload may be one channel, or the *difference*
  of the two. Isolate/subtract in Audacity, or:

```console
$ sox audio.wav left.wav remix 1        # left channel only
$ sox audio.wav right.wav remix 2       # right channel only
$ sox audio.wav mono.wav remix 1,2      # sum (a phase-cancelled payload vanishes)
```

- **Reverse / slow down** → hidden speech is often reversed or time-stretched:
  `sox audio.wav rev.wav reverse`, or change *Tempo* in Audacity.

## Sample LSB (WAV) {: #wav-lsb }

```console
$ stegolsb wavsteg -r -i audio.wav -o out.bin -n 1 -b 1000   # 1 LSB, 1000 bytes
$ file out.bin
```

WavSteg is in the `stego-lsb` package (`pip install stego-lsb`). Vary `-n`
(bits per sample) and `-b` (byte count) if the output is garbage.

## Signalling: SSTV / DTMF / FSK / Morse {: #signalling }

```console
$ multimon-ng -a MORSE_CW -a DTMF -a FSK -t wav audio.wav   # decode many at once
$ minimodem --rx 1200 < audio.wav          # Bell/FSK modem tones (try 300/1200)
```

- **SSTV** (image over audio) → decode with [QSSTV](https://www.qsl.net/on4qz/)
  (feed the audio to a virtual mic), or `pip install sstv` →
  `sstv -d audio.wav -o out.png`.
- **DTMF** (phone dial tones) → `multimon-ng -a DTMF`, or an online DTMF decoder.
- **Morse** → obvious on/off bursts in the waveform; `multimon-ng -a MORSE_CW`.

## Password-protected containers {: #containers }

```console
$ steghide extract -sf audio.wav -p ''     # steghide supports WAV/AU
```

- **DeepSound** → a Windows tool; carve/mount the container, or use community
  extractors. The magic string `DSCF` in `strings` betrays a DeepSound file.

## WAV header tricks {: #header }

- A shrunken **DataSize** in the WAV header hides samples past the declared end —
  edit the size field (or set it to `0xFFFFFFFF`) and re-open to reveal them.
- Raw import: *Audacity → File → Import → Raw Data* interprets a headerless blob
  as PCM — useful when `file` says "data".

## Related

- Tools: [steghide](/wiki/tools/steghide) · [strings](/wiki/tools/strings).
- Depth: [Audio technique page](/wiki/techniques/audio) ·
  [Encodings cheatsheet](/wiki/cheatsheet/encodings) (for a decoded payload).
