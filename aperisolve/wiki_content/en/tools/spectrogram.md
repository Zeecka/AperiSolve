Title: Spectrogram - Reveal Hidden Images and Tones in Audio
Description: How Aperi'Solve turns an uploaded audio file into a spectrogram and waveform, why CTF flags are so often drawn into the spectrogram, and how to read both views.
Order: 270

# Spectrogram

When you upload an audio file (WAV, MP3, FLAC, OGG, M4A...), Aperi'Solve
renders two visualizations of the sound: a **spectrogram** (frequency
content over time) and a **waveform** (amplitude over time). Audio
steganography in CTFs is overwhelmingly visual — the flag is *drawn* into
the spectrogram — so this is the first thing to check on any audio
challenge.

## What Aperi'Solve runs

The analyzer is pure Python (NumPy + Pillow), no external DSP library:

- PCM WAV is decoded directly with the standard-library `wave` module
  (8/16/24/32-bit, mono or stereo, averaged to mono).
- Every other container, and non-PCM WAV, is transcoded to a temporary PCM
  WAV with `ffmpeg` first.
- The spectrogram is a Hann-windowed Short-Time Fourier Transform
  (`N_FFT = 1024`, hop `512`), converted to relative decibels with an
  `-80 dB` floor and colored with a viridis palette. Low frequencies are at
  the bottom, time runs left to right.
- The waveform is a min/max envelope of the signal.

## Reading the output

- **Spectrogram** — bright shapes against a dark background are energy at
  that frequency and time. Text, QR codes and simple drawings placed here
  are read directly by eye.
- **Waveform** — the overall loudness shape. Long silences, abrupt bursts
  or a signal that clips the top and bottom hint at something deliberate.
- The metadata table reports sample rate, channel count, bit depth,
  duration and frame count.

## Common CTF patterns

- **The flag is written in the spectrogram** — the classic. A tone is swept
  to spell out `flag{...}`; it is invisible in the waveform and often
  inaudible. Aperi'Solve draws it for you.
- **A hidden image or QR code** in the high frequencies of an otherwise
  ordinary song.
- **DTMF / Morse** — dial tones or short/long bursts visible as discrete
  frequency bands; decode them from the pattern.
- **Stereo tricks** — data hidden in only one channel, or in the difference
  between channels (Aperi'Solve averages to mono, so also inspect the raw
  channels in Audacity if nothing shows).

## Doing it yourself

[Audacity](https://www.audacityteam.org/) (Analyze → Spectrogram view) and
[Sonic Visualiser](https://www.sonicvisualiser.org/) give an interactive,
zoomable spectrogram with adjustable window size and color scale — useful
when the payload sits in a narrow band the fixed rendering flattens.

## Limitations

- The rendering uses a fixed FFT size and color scale; a faint payload may
  need a different window length or contrast to pop — reach for Audacity.
- Channels are averaged to mono, so purely per-channel or phase-based
  hiding will not appear here.
- Only audio is visualized; data appended after the audio stream is the job
  of [binwalk](/wiki/tools/binwalk) and [strings](/wiki/tools/strings),
  which also run on your upload.
