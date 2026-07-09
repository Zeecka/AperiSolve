"""Spectrogram/Waveform Analyzer for audio submissions.

Pure-Python (NumPy + Pillow) audio visualiser. PCM WAV is decoded directly
with the stdlib :mod:`wave`; every other container (mp3/flac/ogg/m4a) and any
non-PCM WAV is transcoded to a temporary PCM WAV with ``ffmpeg`` first. Two
PNGs are produced: a Hann-windowed STFT spectrogram and a min/max waveform
envelope.

Like the other NumPy analyzers there is no wall-clock guard, so run time is
bounded solely by the ``MAX_CONTENT_LENGTH`` upload cap (1 MB by default).
"""

import struct
import wave
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from PIL import Image

from .base_analyzer import SubprocessAnalyzer

# --- Decoding -------------------------------------------------------------
# Extensions the stdlib ``wave`` reader can open directly (fast path).
_WAV_SUFFIXES = frozenset({".wav", ".wave"})
# Sample widths in bytes (stdlib ``wave`` reports these via getsampwidth()).
_WIDTH_U8 = 1
_WIDTH_I16 = 2
_WIDTH_I24 = 3
_WIDTH_I32 = 4
# 8-bit PCM WAV is unsigned with a 128 zero point; centre it.
_U8_ZERO = 128.0
# 24-bit sign-extension: bit 23 is the sign, samples span 2**24 values.
_SIGN_BIT_24 = 0x80_0000
_SPAN_24 = 0x100_0000
# ffmpeg transcode target (mono, moderate rate — enough for a spectrogram).
_FFMPEG_RATE = 22050
_ERROR_MSG = "Could not decode audio (ffmpeg unavailable or unsupported format)."

# --- Spectrogram ----------------------------------------------------------
N_FFT = 1024
HOP = 512
DB_FLOOR = -80.0
EPSILON = 1e-12
U8_MAX = 255.0
# Cap on STFT columns. The 1 MB upload cap already bounds this well below the
# limit for realistic audio; the cap only defends against a pathological
# high-rate/8-bit clip that would otherwise render a very wide image.
MAX_COLUMNS = 8192

# --- Waveform -------------------------------------------------------------
WAVE_WIDTH = 1000
WAVE_HEIGHT = 300
_WAVE_BG = 255
_WAVE_COLOR = (46, 160, 67)

# Module-level viridis-like lookup table (256x3 uint8), built once. matplotlib
# is not a dependency, so the ramp is interpolated over a handful of anchor
# colours sampled from the viridis colormap.
_VIRIDIS_ANCHORS = np.array(
    [
        [68, 1, 84],
        [72, 35, 116],
        [64, 67, 135],
        [52, 94, 141],
        [41, 120, 142],
        [32, 144, 140],
        [34, 167, 132],
        [68, 190, 112],
        [121, 209, 81],
        [189, 222, 38],
        [253, 231, 37],
    ],
    dtype=np.float64,
)


def _build_lut() -> np.ndarray:
    """Interpolate the viridis anchors into a 256x3 uint8 colour ramp."""
    anchor_positions = np.linspace(0.0, 1.0, _VIRIDIS_ANCHORS.shape[0])
    positions = np.linspace(0.0, 1.0, 256)
    lut = np.empty((256, 3), dtype=np.uint8)
    for channel in range(3):
        lut[:, channel] = np.interp(
            positions,
            anchor_positions,
            _VIRIDIS_ANCHORS[:, channel],
        ).astype(np.uint8)
    return lut


_VIRIDIS_LUT = _build_lut()


class DecodedAudio(NamedTuple):
    """Decoded mono signal plus source metadata, or a ready-to-store error."""

    mono: np.ndarray | None = None
    framerate: int = 0
    n_channels: int = 0
    sampwidth: int = 0
    n_frames: int = 0
    via_ffmpeg: bool = False
    error: dict[str, Any] | None = None


def _error_result() -> dict[str, Any]:
    """Build a fresh undecodable-audio error result."""
    return {"status": "error", "error": _ERROR_MSG}


def _pcm_to_mono(raw: bytes, sampwidth: int, n_channels: int) -> np.ndarray:
    """Decode interleaved little-endian PCM bytes to a mono float32 signal.

    Handles 8-bit (unsigned), 16/32-bit (signed) and 24-bit (manually
    sign-extended) samples, trims a ragged trailing partial frame, and averages
    the channels down to mono. Explicit little-endian dtypes are used so the
    result is host-endianness independent.
    """
    frame_bytes = sampwidth * n_channels
    raw = raw[: (len(raw) // frame_bytes) * frame_bytes]
    if not raw:
        return np.zeros(0, dtype=np.float32)

    if sampwidth == _WIDTH_U8:
        samples = np.frombuffer(raw, dtype="<u1").astype(np.float32) - _U8_ZERO
    elif sampwidth == _WIDTH_I16:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32)
    elif sampwidth == _WIDTH_I32:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float32)
    elif sampwidth == _WIDTH_I24:
        # No native 24-bit dtype: assemble each sample from its explicit
        # little-endian byte triple (byte 0 is least significant) and
        # sign-extend the 24th bit into a full signed range.
        triples = np.frombuffer(raw, dtype="<u1").reshape(-1, 3).astype(np.int32)
        ints = triples[:, 0] | (triples[:, 1] << 8) | (triples[:, 2] << 16)
        ints = np.where(ints & _SIGN_BIT_24, ints - _SPAN_24, ints)
        samples = ints.astype(np.float32)
    else:
        msg = f"Unsupported PCM sample width: {sampwidth} bytes"
        raise ValueError(msg)

    return samples.reshape(-1, n_channels).mean(axis=1).astype(np.float32)


class SpectrogramAnalyzer(SubprocessAnalyzer):
    """Analyzer producing a spectrogram and waveform for audio uploads."""

    name = "spectrogram"
    display_order = 15
    accepts = frozenset({"audio"})

    def _decode_pcm_wav(self, path: Path) -> DecodedAudio:
        """Decode a PCM WAV file to a mono signal. Raises ``wave.Error`` if non-PCM."""
        with wave.open(str(path), "rb") as wav:
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            if wav.getcomptype() != "NONE":
                msg = "Non-PCM WAV compression"
                raise wave.Error(msg)
            raw = wav.readframes(n_frames)

        if n_frames == 0 or framerate == 0 or not raw or sampwidth == 0 or n_channels == 0:
            return DecodedAudio(error=_error_result())
        mono = _pcm_to_mono(raw, sampwidth, n_channels)
        if mono.size == 0:
            return DecodedAudio(error=_error_result())
        return DecodedAudio(
            mono=mono,
            framerate=framerate,
            n_channels=n_channels,
            sampwidth=sampwidth,
            n_frames=int(mono.size),
        )

    def _decode_via_ffmpeg(self, tmp_wav: Path) -> DecodedAudio:
        """Transcode any audio to a temp PCM WAV via ffmpeg, then decode it."""
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(self.input_img),
            "-ac",
            "1",
            "-ar",
            str(_FFMPEG_RATE),
            str(tmp_wav),
        ]
        proc = self.run_command(cmd)
        if proc.returncode != 0 or not tmp_wav.exists():
            return DecodedAudio(error=_error_result())
        decoded = self._decode_pcm_wav(tmp_wav)
        if decoded.error is not None:
            return decoded
        return decoded._replace(via_ffmpeg=True)

    def _decode(self) -> DecodedAudio:
        """Decode the upload to mono float32, via stdlib wave or ffmpeg."""
        tmp_wav = self.output_dir / "_transcode.wav"
        try:
            if self.input_img.suffix.lower() in _WAV_SUFFIXES:
                try:
                    return self._decode_pcm_wav(self.input_img)
                except wave.Error:
                    # Non-PCM WAV (float/µ-law/A-law/EXTENSIBLE): let ffmpeg try.
                    pass
            return self._decode_via_ffmpeg(tmp_wav)
        except (wave.Error, EOFError, OSError, ValueError, struct.error, RuntimeError):
            return DecodedAudio(error=_error_result())
        finally:
            if tmp_wav.exists():
                tmp_wav.unlink()

    def _save_spectrogram(self, mono: np.ndarray) -> None:
        """Render the Hann-windowed STFT spectrogram to ``spectrogram.png``."""
        signal = mono.astype(np.float32)
        if signal.size < N_FFT:
            signal = np.pad(signal, (0, N_FFT - signal.size))
        window = np.hanning(N_FFT).astype(np.float32)
        frames = np.lib.stride_tricks.sliding_window_view(signal, N_FFT)[::HOP]
        if frames.shape[0] > MAX_COLUMNS:
            frames = frames[:MAX_COLUMNS]
        spec = np.fft.rfft(frames * window, axis=1)
        mag = np.abs(spec)
        db = 20.0 * np.log10(mag / (mag.max() + EPSILON) + EPSILON)
        db = np.maximum(db, DB_FLOOR)
        norm = np.clip((db - DB_FLOOR) / (0.0 - DB_FLOOR), 0.0, 1.0)
        idx = (norm * U8_MAX).astype(np.uint8)
        img2d = np.flipud(idx.T)  # low frequencies at the bottom
        rgb = _VIRIDIS_LUT[img2d]
        Image.fromarray(rgb, "RGB").save(self.output_dir / "spectrogram.png")

    def _save_waveform(self, mono: np.ndarray, divisor: float) -> None:
        """Render a min/max waveform envelope to ``waveform.png``."""
        canvas = np.full((WAVE_HEIGHT, WAVE_WIDTH, 3), _WAVE_BG, dtype=np.uint8)
        signal = np.clip(mono / divisor, -1.0, 1.0)
        n = signal.size
        if n:
            edges = np.linspace(0, n, WAVE_WIDTH + 1, dtype=np.int64)
            for x in range(WAVE_WIDTH):
                start, end = int(edges[x]), int(edges[x + 1])
                seg = signal[start:end] if end > start else signal[min(start, n - 1) :][:1]
                hi = float(seg.max())
                lo = float(seg.min())
                y_hi = int((1.0 - (hi + 1.0) / 2.0) * (WAVE_HEIGHT - 1))
                y_lo = int((1.0 - (lo + 1.0) / 2.0) * (WAVE_HEIGHT - 1))
                canvas[y_hi : y_lo + 1, x] = _WAVE_COLOR
        Image.fromarray(canvas, "RGB").save(self.output_dir / "waveform.png")

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Decode the audio upload and render spectrogram + waveform PNGs."""
        _ = password
        decoded = self._decode()
        mono = decoded.mono
        if decoded.error is not None or mono is None:
            return decoded.error or _error_result()

        self._save_spectrogram(mono)
        if decoded.via_ffmpeg:
            divisor = float(np.max(np.abs(mono))) or 1.0
        else:
            divisor = float(2 ** (decoded.sampwidth * 8 - 1))
        self._save_waveform(mono, divisor)

        base = Path(self.output_dir.name)
        spec_url = "/image/" + str(base / "spectrogram.png")
        wave_url = "/image/" + str(base / "waveform.png")
        return {
            "status": "ok",
            "output": {
                "Sample rate": f"{decoded.framerate} Hz",
                "Channels": str(decoded.n_channels),
                "Bit depth": f"{decoded.sampwidth * 8}-bit",
                "Duration": f"{decoded.n_frames / decoded.framerate:.2f} s",
                "Frames": str(decoded.n_frames),
            },
            "images": {
                "Spectrogram": [spec_url],
                "Waveform": [wave_url],
            },
        }
