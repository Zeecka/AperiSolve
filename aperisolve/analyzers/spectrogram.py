"""Spectrogram/Waveform Analyzer for audio submissions.

Pure-Python (NumPy + Pillow) audio visualiser. PCM WAV is decoded directly
with the stdlib :mod:`wave`; every other container (mp3/flac/ogg/m4a) and any
non-PCM WAV is transcoded to a temporary PCM WAV with ``ffmpeg`` first.

Channels are preserved end to end (ffmpeg keeps the source channel layout), so
the analyzer renders **one annotated spectrogram per channel** plus a single
mono-mixdown waveform. Both kinds of image are drawn by hand with Pillow — no
matplotlib — as fully labelled plots: the spectrogram carries a frequency
(Hz/kHz) Y axis, a time (s) X axis and a viridis dB colorbar; the waveform
carries a time (s) X axis and a normalised amplitude Y axis with a zero
baseline. All axis text is rasterised into the PNG, so nothing here needs
translating.

Like the other NumPy analyzers there is no wall-clock guard, so run time is
bounded solely by the ``MAX_CONTENT_LENGTH`` upload cap (1 MB by default).
"""

import math
import struct
import wave
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
# ffmpeg transcode target sample rate (moderate rate — enough for a spectrogram).
# NOTE: channels are intentionally NOT collapsed (no ``-ac 1``); a stereo source
# stays stereo so each channel gets its own spectrogram.
_FFMPEG_RATE = 22050
_ERROR_MSG = "Could not decode audio (ffmpeg unavailable or unsupported format)."

# --- Spectrogram DSP ------------------------------------------------------
# Larger FFT than before (was 1024) for finer frequency resolution; the hop is a
# quarter window for good time detail. The raw STFT is resampled to a fixed plot
# area afterwards, so these only control analysis granularity, not output size.
N_FFT = 2048
HOP = N_FFT // 4
DB_FLOOR = -80.0
EPSILON = 1e-12
U8_MAX = 255.0
# Cap on STFT columns. The 1 MB upload cap already bounds this well below the
# limit for realistic audio; the cap only defends against a pathological
# high-rate/8-bit clip that would otherwise render a very wide image. When it
# bites, the time axis is labelled with the truncated span and a note is added.
MAX_COLUMNS = 8192
# Cap on rendered channels; extra channels are noted but not drawn.
MAX_CHANNELS = 6

# --- Plot geometry (pixels) ----------------------------------------------
_PLOT_W = 900
_PLOT_H = 420
_WAVE_PLOT_H = 240
_MARGIN_LEFT = 82
_MARGIN_TOP = 34
_MARGIN_BOTTOM = 60
_MARGIN_RIGHT_SPEC = 96
_MARGIN_RIGHT_WAVE = 24
_SPEC_CANVAS_W = _MARGIN_LEFT + _PLOT_W + _MARGIN_RIGHT_SPEC
_SPEC_CANVAS_H = _MARGIN_TOP + _PLOT_H + _MARGIN_BOTTOM
_WAVE_CANVAS_W = _MARGIN_LEFT + _PLOT_W + _MARGIN_RIGHT_WAVE
_WAVE_CANVAS_H = _MARGIN_TOP + _WAVE_PLOT_H + _MARGIN_BOTTOM

# Colorbar (spectrogram only), drawn to the right of the plot area.
_CBAR_GAP = 16
_CBAR_W = 18
_CBAR_TITLE_OFFSET = 44

# Tick / label metrics.
_TICK_LEN = 5
_HALF_LINE = 6
_XTITLE_GAP = 22
_YTITLE_X = 16
_CHANNEL_TITLE_Y = 10
_FREQ_TICKS = 7
_TIME_TICKS = 7
_DB_TICKS = 5
_AMP_TICKS = 5
_KHZ_THRESHOLD = 1000.0
_TICK_EPS = 1e-9
_LABEL_SIZE = 12
_TITLE_SIZE = 13

# Channel naming.
_STEREO = 2
_STEREO_NAMES = ("Left", "Right")

# Colours.
_CANVAS_BG = (255, 255, 255)
_AXIS_COLOR = (70, 70, 70)
_TEXT_COLOR = (25, 25, 25)
_ZERO_COLOR = (140, 140, 140)
_TRANSPARENT = (0, 0, 0, 0)
_WAVE_BG = 255
_WAVE_COLOR = (46, 160, 67)

# Notes surfaced to the UI when a limit bites.
_TRUNCATION_NOTE = "Spectrogram shows first {shown:.1f} s of {total:.1f} s."
_CHANNEL_CAP_NOTE = "Showing the first {cap} of {total} channels."

_LUT_MAX_INDEX = 255

# Fonts accepted by Pillow's drawing API (sized FreeType, or the bitmap
# fallback if the sized loader is ever unavailable).
_Font = ImageFont.FreeTypeFont | ImageFont.ImageFont

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
    """Decoded per-channel signal plus source metadata, or a stored error.

    ``channels`` has shape ``(n_samples, n_channels)``; a mono mixdown is just
    ``channels.mean(axis=1)``.
    """

    channels: np.ndarray | None = None
    framerate: int = 0
    n_channels: int = 0
    sampwidth: int = 0
    n_frames: int = 0
    via_ffmpeg: bool = False
    error: dict[str, Any] | None = None


class PlotBox(NamedTuple):
    """Pixel rectangle of a plot's data area on the output canvas."""

    left: int
    top: int
    width: int
    height: int


class Axis(NamedTuple):
    """A single annotated axis: data range, tick positions, labels and title."""

    vmin: float
    vmax: float
    ticks: list[float]
    labels: list[str]
    title: str


def _error_result() -> dict[str, Any]:
    """Build a fresh undecodable-audio error result."""
    return {"status": "error", "error": _ERROR_MSG}


def _pcm_to_channels(raw: bytes, sampwidth: int, n_channels: int) -> np.ndarray:
    """Decode interleaved little-endian PCM bytes to ``(n_samples, n_channels)``.

    Handles 8-bit (unsigned), 16/32-bit (signed) and 24-bit (manually
    sign-extended) samples, trims a ragged trailing partial frame, and
    de-interleaves into one column per channel. Explicit little-endian dtypes
    are used so the result is host-endianness independent.
    """
    frame_bytes = sampwidth * n_channels
    raw = raw[: (len(raw) // frame_bytes) * frame_bytes]
    if not raw:
        return np.zeros((0, n_channels), dtype=np.float32)

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

    return samples.reshape(-1, n_channels).astype(np.float32)


def _load_font(size: int) -> _Font:
    """Load a scalable default font, falling back to the bitmap default.

    Pillow 12 ships a FreeType default that accepts ``size=`` with no font
    packages in the image; the fallback keeps the analyzer from ever crashing
    on a Pillow build where the sized call is unavailable.
    """
    try:
        return ImageFont.load_default(size=size)
    except (OSError, TypeError, ValueError):
        return ImageFont.load_default()


def _fmt_num(value: float) -> str:
    """Format a tick value compactly, dropping a trailing ``.0`` / zeros."""
    if value == int(value):
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _nice_step(span: float, target: int) -> float:
    """Return a 'nice' round tick step (1/2/2.5/5 x 10^n) for a span."""
    if span <= 0:
        return 1.0
    raw = span / target
    magnitude = 10.0 ** math.floor(math.log10(raw))
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if candidate * magnitude >= raw:
            return candidate * magnitude
    return 10.0 * magnitude


def _axis_ticks(vmin: float, vmax: float, target: int) -> list[float]:
    """Generate ~``target`` nicely-spaced tick values across ``[vmin, vmax]``."""
    step = _nice_step(vmax - vmin, target)
    if step <= 0:
        return [vmin, vmax]
    start = math.ceil(vmin / step - _TICK_EPS) * step
    ticks: list[float] = []
    value = start
    while value <= vmax + step * _TICK_EPS:
        ticks.append(0.0 if abs(value) < step * _TICK_EPS else value)
        value += step
    return ticks or [vmin]


def _freq_axis(nyquist: float, *, use_khz: bool) -> Axis:
    """Build the spectrogram frequency Y axis (0..Nyquist), in Hz or kHz."""
    ticks = _axis_ticks(0.0, nyquist, _FREQ_TICKS)
    if use_khz:
        labels = [_fmt_num(t / 1000.0) for t in ticks]
        title = "Frequency (kHz)"
    else:
        labels = [_fmt_num(t) for t in ticks]
        title = "Frequency (Hz)"
    return Axis(0.0, nyquist, ticks, labels, title)


def _time_axis(duration: float) -> Axis:
    """Build a time X axis spanning ``0..duration`` seconds."""
    ticks = _axis_ticks(0.0, duration, _TIME_TICKS)
    return Axis(0.0, duration, ticks, [_fmt_num(t) for t in ticks], "Time (s)")


def _amp_axis() -> Axis:
    """Build the waveform amplitude Y axis (normalised -1..+1)."""
    ticks = _axis_ticks(-1.0, 1.0, _AMP_TICKS)
    return Axis(-1.0, 1.0, ticks, [_fmt_num(t) for t in ticks], "Amplitude")


def _db_axis() -> Axis:
    """Build the colorbar dB axis (DB_FLOOR..0)."""
    ticks = _axis_ticks(DB_FLOOR, 0.0, _DB_TICKS)
    return Axis(DB_FLOOR, 0.0, ticks, [_fmt_num(t) for t in ticks], "dB")


def _channel_title(index: int, n_channels: int) -> str:
    """Human-readable channel name: Left/Right for stereo, else 'Channel N'."""
    if n_channels == _STEREO:
        return _STEREO_NAMES[index]
    return f"Channel {index + 1}"


def _paste_vertical_text(
    canvas: Image.Image,
    text: str,
    cx: int,
    cy: int,
    font: _Font,
) -> None:
    """Draw ``text`` rotated 90 degrees, centred at ``(cx, cy)`` on ``canvas``."""
    left, top, right, bottom = font.getbbox(text)
    width = max(int(right - left), 1)
    height = max(int(bottom - top), 1)
    strip = Image.new("RGBA", (width, height), _TRANSPARENT)
    ImageDraw.Draw(strip).text((-left, -top), text, font=font, fill=_TEXT_COLOR)
    rot = strip.rotate(90, expand=True)
    canvas.paste(rot, (int(cx - rot.width / 2), int(cy - rot.height / 2)), rot)


def _draw_x_axis(draw: ImageDraw.ImageDraw, box: PlotBox, axis: Axis, font: _Font) -> None:
    """Draw ticks, numeric labels and a centred title along the bottom edge."""
    span = (axis.vmax - axis.vmin) or 1.0
    y0 = box.top + box.height
    for value, label in zip(axis.ticks, axis.labels, strict=True):
        x = box.left + int((value - axis.vmin) / span * box.width)
        draw.line([(x, y0), (x, y0 + _TICK_LEN)], fill=_AXIS_COLOR)
        text_w = draw.textlength(label, font=font)
        draw.text((x - text_w / 2, y0 + _TICK_LEN + 2), label, font=font, fill=_TEXT_COLOR)
    title_w = draw.textlength(axis.title, font=font)
    draw.text(
        (box.left + box.width / 2 - title_w / 2, y0 + _TICK_LEN + _XTITLE_GAP),
        axis.title,
        font=font,
        fill=_TEXT_COLOR,
    )


def _draw_y_axis(draw: ImageDraw.ImageDraw, box: PlotBox, axis: Axis, font: _Font) -> None:
    """Draw ticks and right-aligned numeric labels along the left edge."""
    span = (axis.vmax - axis.vmin) or 1.0
    x0 = box.left
    for value, label in zip(axis.ticks, axis.labels, strict=True):
        y = box.top + int((axis.vmax - value) / span * box.height)
        draw.line([(x0 - _TICK_LEN, y), (x0, y)], fill=_AXIS_COLOR)
        text_w = draw.textlength(label, font=font)
        draw.text(
            (x0 - _TICK_LEN - 4 - text_w, y - _HALF_LINE),
            label,
            font=font,
            fill=_TEXT_COLOR,
        )


def _draw_colorbar(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: PlotBox,
    label_font: _Font,
    title_font: _Font,
) -> None:
    """Paste the viridis LUT as a vertical strip and label it in dB."""
    cbar_left = box.left + box.width + _CBAR_GAP
    # Top of the strip is the brightest colour (0 dB), bottom is DB_FLOOR.
    grad = _VIRIDIS_LUT[np.arange(_LUT_MAX_INDEX, -1, -1)].reshape(-1, 1, 3)
    grad_img = Image.fromarray(np.ascontiguousarray(grad), "RGB").resize(
        (_CBAR_W, box.height),
        Image.Resampling.BILINEAR,
    )
    canvas.paste(grad_img, (cbar_left, box.top))
    draw.rectangle(
        [cbar_left, box.top, cbar_left + _CBAR_W, box.top + box.height],
        outline=_AXIS_COLOR,
    )
    axis = _db_axis()
    span = (axis.vmax - axis.vmin) or 1.0
    x_right = cbar_left + _CBAR_W
    for value, label in zip(axis.ticks, axis.labels, strict=True):
        y = box.top + int((axis.vmax - value) / span * box.height)
        draw.line([(x_right, y), (x_right + _TICK_LEN, y)], fill=_AXIS_COLOR)
        draw.text(
            (x_right + _TICK_LEN + 3, y - _HALF_LINE),
            label,
            font=label_font,
            fill=_TEXT_COLOR,
        )
    _paste_vertical_text(
        canvas,
        axis.title,
        x_right + _CBAR_TITLE_OFFSET,
        box.top + box.height // 2,
        title_font,
    )


def _waveform_plot(signal_norm: np.ndarray) -> np.ndarray:
    """Render a min/max envelope of a normalised signal into the plot area."""
    canvas = np.full((_WAVE_PLOT_H, _PLOT_W, 3), _WAVE_BG, dtype=np.uint8)
    n = signal_norm.size
    if n:
        edges = np.linspace(0, n, _PLOT_W + 1, dtype=np.int64)
        for x in range(_PLOT_W):
            start, end = int(edges[x]), int(edges[x + 1])
            seg = signal_norm[start:end] if end > start else signal_norm[min(start, n - 1) :][:1]
            hi = float(seg.max())
            lo = float(seg.min())
            y_hi = int((1.0 - (hi + 1.0) / 2.0) * (_WAVE_PLOT_H - 1))
            y_lo = int((1.0 - (lo + 1.0) / 2.0) * (_WAVE_PLOT_H - 1))
            canvas[y_hi : y_lo + 1, x] = _WAVE_COLOR
    return canvas


class SpectrogramAnalyzer(SubprocessAnalyzer):
    """Analyzer producing per-channel spectrograms and a waveform for audio."""

    name = "spectrogram"
    display_order = 15
    accepts = frozenset({"audio"})

    def _decode_pcm_wav(self, path: Path) -> DecodedAudio:
        """Decode a PCM WAV file to per-channel float32. Raises ``wave.Error`` if non-PCM."""
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
        channels = _pcm_to_channels(raw, sampwidth, n_channels)
        if channels.size == 0:
            return DecodedAudio(error=_error_result())
        return DecodedAudio(
            channels=channels,
            framerate=framerate,
            n_channels=n_channels,
            sampwidth=sampwidth,
            n_frames=int(channels.shape[0]),
        )

    def _decode_via_ffmpeg(self, tmp_wav: Path) -> DecodedAudio:
        """Transcode any audio to a temp PCM WAV via ffmpeg, then decode it.

        Channels are preserved (no ``-ac 1``): a stereo source stays stereo so
        every channel gets its own spectrogram.
        """
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(self.input_img),
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
        """Decode the upload to per-channel float32, via stdlib wave or ffmpeg."""
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

    def _compute_stft(self, signal: np.ndarray) -> tuple[np.ndarray, int, int]:
        """Return (heatmap, columns_rendered, columns_total) for one channel.

        ``heatmap`` is a contiguous uint8 array shaped (freq_bins, columns) with
        low frequencies at the bottom, ready to colour-map. ``columns_total`` is
        the STFT width before the ``MAX_COLUMNS`` cap, so the caller can tell
        whether (and by how much) the time axis was truncated.
        """
        sig = signal.astype(np.float32)
        if sig.size < N_FFT:
            sig = np.pad(sig, (0, N_FFT - sig.size))
        window = np.hanning(N_FFT).astype(np.float32)
        frames = np.lib.stride_tricks.sliding_window_view(sig, N_FFT)[::HOP]
        columns_total = int(frames.shape[0])
        if columns_total > MAX_COLUMNS:
            frames = frames[:MAX_COLUMNS]
        columns_rendered = int(frames.shape[0])
        spec = np.fft.rfft(frames * window, axis=1)
        mag = np.abs(spec)
        db = 20.0 * np.log10(mag / (mag.max() + EPSILON) + EPSILON)
        db = np.maximum(db, DB_FLOOR)
        norm = np.clip((db - DB_FLOOR) / (0.0 - DB_FLOOR), 0.0, 1.0)
        idx = (norm * U8_MAX).astype(np.uint8)
        heatmap = np.ascontiguousarray(np.flipud(idx.T))  # low frequencies at bottom
        return heatmap, columns_rendered, columns_total

    def _render_spectrogram(
        self,
        heatmap: np.ndarray,
        framerate: int,
        displayed_duration: float,
        title: str,
    ) -> Image.Image:
        """Compose one annotated spectrogram (heatmap + axes + colorbar + title)."""
        # Resample the raw STFT to the fixed plot area, then colour-map it.
        idx_img = Image.fromarray(heatmap, "L").resize(
            (_PLOT_W, _PLOT_H),
            Image.Resampling.BILINEAR,
        )
        plot_rgb = _VIRIDIS_LUT[np.asarray(idx_img)]

        canvas = Image.new("RGB", (_SPEC_CANVAS_W, _SPEC_CANVAS_H), _CANVAS_BG)
        canvas.paste(Image.fromarray(plot_rgb, "RGB"), (_MARGIN_LEFT, _MARGIN_TOP))
        draw = ImageDraw.Draw(canvas)
        box = PlotBox(_MARGIN_LEFT, _MARGIN_TOP, _PLOT_W, _PLOT_H)
        draw.rectangle(
            [box.left, box.top, box.left + box.width, box.top + box.height],
            outline=_AXIS_COLOR,
        )

        label_font = _load_font(_LABEL_SIZE)
        title_font = _load_font(_TITLE_SIZE)

        nyquist = framerate / 2.0
        y_axis = _freq_axis(nyquist, use_khz=nyquist >= _KHZ_THRESHOLD)
        _draw_y_axis(draw, box, y_axis, label_font)
        _paste_vertical_text(canvas, y_axis.title, _YTITLE_X, box.top + box.height // 2, title_font)

        _draw_x_axis(draw, box, _time_axis(displayed_duration), label_font)
        _draw_colorbar(canvas, draw, box, label_font, title_font)
        draw.text((box.left, _CHANNEL_TITLE_Y), title, font=title_font, fill=_TEXT_COLOR)
        return canvas

    def _save_spectrograms(
        self,
        channels: np.ndarray,
        framerate: int,
    ) -> tuple[list[str], list[str]]:
        """Render one spectrogram per channel; return (image URLs, note parts)."""
        ch_count = int(channels.shape[1])
        n_render = min(ch_count, MAX_CHANNELS)
        total_duration = channels.shape[0] / framerate
        base = Path(self.output_dir.name)
        urls: list[str] = []
        notes: list[str] = []
        truncated: str | None = None

        for i in range(n_render):
            heatmap, rendered, total_cols = self._compute_stft(channels[:, i])
            displayed = total_duration * rendered / total_cols if total_cols else total_duration
            img = self._render_spectrogram(
                heatmap,
                framerate,
                displayed,
                _channel_title(i, ch_count),
            )
            name = f"spectrogram-{i + 1}.png"
            img.save(self.output_dir / name)
            urls.append("/image/" + str(base / name))
            if rendered < total_cols and truncated is None:
                truncated = _TRUNCATION_NOTE.format(shown=displayed, total=total_duration)

        if truncated:
            notes.append(truncated)
        if ch_count > MAX_CHANNELS:
            notes.append(_CHANNEL_CAP_NOTE.format(cap=MAX_CHANNELS, total=ch_count))
        return urls, notes

    def _save_waveform(self, mono: np.ndarray, divisor: float, duration: float) -> None:
        """Compose the annotated mono waveform envelope to ``waveform.png``."""
        signal = np.clip(mono / divisor, -1.0, 1.0)
        canvas = Image.new("RGB", (_WAVE_CANVAS_W, _WAVE_CANVAS_H), _CANVAS_BG)
        canvas.paste(Image.fromarray(_waveform_plot(signal), "RGB"), (_MARGIN_LEFT, _MARGIN_TOP))
        draw = ImageDraw.Draw(canvas)
        box = PlotBox(_MARGIN_LEFT, _MARGIN_TOP, _PLOT_W, _WAVE_PLOT_H)

        zero_y = box.top + box.height // 2
        draw.line([(box.left, zero_y), (box.left + box.width, zero_y)], fill=_ZERO_COLOR)
        draw.rectangle(
            [box.left, box.top, box.left + box.width, box.top + box.height],
            outline=_AXIS_COLOR,
        )

        label_font = _load_font(_LABEL_SIZE)
        title_font = _load_font(_TITLE_SIZE)
        _draw_y_axis(draw, box, _amp_axis(), label_font)
        _paste_vertical_text(canvas, "Amplitude", _YTITLE_X, box.top + box.height // 2, title_font)
        _draw_x_axis(draw, box, _time_axis(duration), label_font)
        canvas.save(self.output_dir / "waveform.png")

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Decode the audio upload and render per-channel spectrograms + waveform."""
        _ = password
        decoded = self._decode()
        channels = decoded.channels
        if decoded.error is not None or channels is None:
            return decoded.error or _error_result()

        mono = channels.mean(axis=1).astype(np.float32)
        spec_urls, notes = self._save_spectrograms(channels, decoded.framerate)

        if decoded.via_ffmpeg:
            divisor = float(np.max(np.abs(mono))) or 1.0
        else:
            divisor = float(2 ** (decoded.sampwidth * 8 - 1))
        duration = decoded.n_frames / decoded.framerate
        self._save_waveform(mono, divisor, duration)

        wave_url = "/image/" + str(Path(self.output_dir.name) / "waveform.png")
        result: dict[str, Any] = {
            "status": "ok",
            "output": {
                "Sample rate": f"{decoded.framerate} Hz",
                "Channels": str(decoded.n_channels),
                "Bit depth": f"{decoded.sampwidth * 8}-bit",
                "Duration": f"{duration:.2f} s",
                "Frames": str(decoded.n_frames),
                "FFT size": str(N_FFT),
            },
            "images": {
                "Spectrogram": spec_urls,
                "Waveform": [wave_url],
            },
        }
        if notes:
            result["note"] = " ".join(notes)
        return result
