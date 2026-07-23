Title: Spectrogram - Reveal Hidden Images and Tones in Audio
Description: How Aperi'Solve turns an uploaded audio file into a spectrogram and waveform, why CTF flags are so often drawn into the spectrogram, and how to read both views.
Order: 270

# Spectrogram

When you upload an audio file (WAV, MP3, FLAC, OGG, M4A...), Aperi'Solve
renders visualizations of the sound: a **spectrogram per channel**
(frequency content over time) and a single **waveform** (amplitude over
time). Audio steganography in CTFs is overwhelmingly visual — the flag is
*drawn* into the spectrogram — so this is the first thing to check on any
audio challenge.

## What Aperi'Solve runs

The analyzer is pure Python (NumPy + Pillow), no external DSP library. Every
plot — axes, tick labels, colorbar — is drawn by hand with Pillow, so the
images are fully annotated and readable on their own:

- PCM WAV is decoded directly with the standard-library `wave` module
  (8/16/24/32-bit, mono or stereo, channels kept separate).
- Every other container, and non-PCM WAV, is transcoded to a temporary PCM
  WAV with `ffmpeg` first. The source channel layout is preserved (stereo
  stays stereo).
- Each channel gets its own Hann-windowed Short-Time Fourier Transform
  (`N_FFT = 2048`, hop `512`), converted to relative decibels with an
  `-80 dB` floor and colored with a viridis palette.
- The waveform is a min/max envelope of the mono mixdown of all channels.

## Reading the output

- **Spectrogram** — one image per channel (labelled *Left* / *Right* for
  stereo, or *Channel N*). Bright shapes against a dark background are energy
  at that frequency and time; text, QR codes and drawings placed here are
  read directly by eye. The plot is annotated:
  - the **Y axis** is frequency, from `0` to the Nyquist rate
    (`sample rate / 2`), labelled in Hz or kHz, low frequencies at the bottom;
  - the **X axis** is time in seconds, left to right;
  - the **colorbar** on the right maps colour to loudness in decibels
    (`0 dB` = loudest, down to the `-80 dB` floor).
- **Waveform** — the overall loudness shape, with a time (s) X axis and a
  normalized amplitude (`-1..+1`) Y axis around a zero baseline. Long
  silences, abrupt bursts or a signal that clips the top and bottom hint at
  something deliberate.
- The metadata table reports sample rate, channel count, bit depth,
  duration, frame count and FFT size.
- If a very long clip would overflow, only the first part is drawn and a note
  says how much of the total duration is shown. Files with more than six
  channels render the first six, also noted.

## Common CTF patterns

- **The flag is written in the spectrogram** — the classic. A tone is swept
  to spell out `flag{...}`; it is invisible in the waveform and often
  inaudible. Aperi'Solve draws it for you.
- **A hidden image or QR code** in the high frequencies of an otherwise
  ordinary song.
- **DTMF / Morse** — dial tones or short/long bursts visible as discrete
  frequency bands; decode them from the pattern.
- **Stereo tricks** — data hidden in only one channel shows up because each
  channel has its own spectrogram; compare *Left* and *Right*. Payloads in
  the *difference* between channels (phase tricks) still need Audacity.

## Doing it yourself

[Audacity](https://www.audacityteam.org/) (Analyze → Spectrogram view) and
[Sonic Visualiser](https://www.sonicvisualiser.org/) give an interactive,
zoomable spectrogram with adjustable window size and color scale — useful
when the payload sits in a narrow band the fixed rendering flattens.

## Limitations

- The rendering uses a fixed FFT size and color scale; a faint payload may
  need a different window length or contrast to pop — reach for Audacity.
- The waveform is a mono mixdown, so phase- or difference-based hiding
  between channels will not appear there (the per-channel spectrograms still
  help).
- Only audio is visualized; data appended after the audio stream is the job
  of [binwalk](/wiki/tools/binwalk) and [strings](/wiki/tools/strings),
  which also run on your upload.
