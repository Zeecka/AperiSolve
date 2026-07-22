"""Smoke tests running cheap analyzers against fixture inputs."""

import json
import os
import shutil
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from aperisolve.analyzers.color_remapping import RANDOM_REMAPPING_COUNT, ColorRemappingAnalyzer
from aperisolve.analyzers.decomposer import DecomposerAnalyzer
from aperisolve.analyzers.file import FileAnalyzer
from aperisolve.analyzers.outguess import OutguessAnalyzer
from aperisolve.analyzers.pdfid import PdfidAnalyzer
from aperisolve.analyzers.pdfinfo import PdfinfoAnalyzer
from aperisolve.analyzers.pil_utils import PALETTE_NOTE
from aperisolve.analyzers.spectrogram import SpectrogramAnalyzer
from aperisolve.analyzers.strings import StringsAnalyzer
from aperisolve.filetype import detect_file_type

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_IMAGE = REPO_ROOT / "examples" / "example1.png"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
FIXTURE_PDF = FIXTURES / "sample.pdf"

# Synthetic-WAV generation parameters (kept as module constants so the writer
# stays under the argument-count lint and the numbers document themselves).
_WAV_RATE = 16000
_WAV_FRAMES = 4096
_WAV_FREQ = 440.0
_I8_PEAK = 127.0
_I8_ZERO = 128.0
_I16_PEAK = 32767
_I16_MIN = -32768
_I24_PEAK = 2**23 - 1
_I24_MIN = -(2**23)
_I32_PEAK = 2**31 - 1
_I32_MIN = -(2**31)
_LOW_THREE_BYTES = 3


def _read_results(output_dir: Path) -> dict:
    return json.loads((output_dir / "results.json").read_text(encoding="utf-8"))


def test_decomposer_produces_bit_planes(tmp_path: Path) -> None:
    """The pure-Python decomposer runs anywhere and emits images."""
    DecomposerAnalyzer.execute(EXAMPLE_IMAGE, tmp_path)
    results = _read_results(tmp_path)
    assert results["decomposer"]["status"] == "ok"
    assert results["decomposer"]["images"]


@pytest.mark.skipif(shutil.which("file") is None, reason="file binary not installed")
def test_file_identifies_png(tmp_path: Path) -> None:
    """The `file` analyzer identifies the fixture as a PNG."""
    output_dir = tmp_path / EXAMPLE_IMAGE.stem
    output_dir.mkdir()
    shutil.copy(EXAMPLE_IMAGE, tmp_path / EXAMPLE_IMAGE.name)
    FileAnalyzer.execute(tmp_path / EXAMPLE_IMAGE.name, output_dir)
    results = _read_results(output_dir)
    assert results["file"]["status"] == "ok"
    assert "PNG" in results["file"]["output"]


@pytest.mark.skipif(shutil.which("strings") is None, reason="strings binary not installed")
def test_strings_extracts_text(tmp_path: Path) -> None:
    """The strings analyzer returns lines without error."""
    output_dir = tmp_path / EXAMPLE_IMAGE.stem
    output_dir.mkdir()
    shutil.copy(EXAMPLE_IMAGE, tmp_path / EXAMPLE_IMAGE.name)
    StringsAnalyzer.execute(tmp_path / EXAMPLE_IMAGE.name, output_dir)
    results = _read_results(output_dir)
    assert results["strings"]["status"] == "ok"
    assert isinstance(results["strings"]["output"], list)


@pytest.mark.skipif(shutil.which("outguess") is None, reason="outguess binary not installed")
def test_outguess_reports_success_on_extraction(tmp_path: Path) -> None:
    """A non-empty extraction is reported ok with a download (regression guard).

    outguess is chatty on stderr even on success, so the default is_error would
    mark every run failed; the fixture carries a real payload keyed to the
    passphrase below.
    """
    fixture = FIXTURES / "outguess.jpg"
    output_dir = tmp_path / fixture.stem
    output_dir.mkdir()
    shutil.copy(fixture, tmp_path / fixture.name)
    OutguessAnalyzer.execute(tmp_path / fixture.name, output_dir, "s3cret")
    results = _read_results(output_dir)
    assert results["outguess"]["status"] == "ok", results["outguess"]
    assert results["outguess"]["download"].endswith("/outguess")


def _pack_pcm(samples: np.ndarray, sampwidth: int) -> bytes:
    """Encode float samples in [-1, 1] as interleaved little-endian PCM bytes.

    Mirrors the widths the spectrogram decoder handles: 8-bit unsigned, 16/32-bit
    signed, and 24-bit assembled from an explicit little-endian byte triple.
    """
    if sampwidth == 1:
        # 8-bit PCM WAV is unsigned around a 128 zero point.
        scaled = np.clip(np.round(samples * _I8_PEAK) + _I8_ZERO, 0, 255)
        return scaled.astype(np.uint8).tobytes()
    if sampwidth == 2:
        scaled = np.clip(np.round(samples * _I16_PEAK), _I16_MIN, _I16_PEAK)
        return scaled.astype("<i2").tobytes()
    if sampwidth == 3:
        scaled = np.clip(np.round(samples * _I24_PEAK), _I24_MIN, _I24_PEAK).astype("<i4")
        # Keep the three least-significant little-endian bytes of each sample.
        low3 = scaled.view(np.uint8).reshape(-1, 4)[:, :_LOW_THREE_BYTES]
        return np.ascontiguousarray(low3).tobytes()
    if sampwidth == 4:
        scaled = np.clip(np.round(samples * _I32_PEAK), _I32_MIN, _I32_PEAK)
        return scaled.astype("<i4").tobytes()
    msg = f"unsupported sampwidth {sampwidth}"
    raise ValueError(msg)


def _write_sine_wav(path: Path, *, sampwidth: int, n_channels: int) -> None:
    """Write a synthetic sine-tone PCM WAV of the given width and channel count."""
    t = np.arange(_WAV_FRAMES, dtype=np.float64) / _WAV_RATE
    tone = np.sin(2.0 * np.pi * _WAV_FREQ * t)
    interleaved = np.repeat(tone[:, None], n_channels, axis=1).reshape(-1)
    raw = _pack_pcm(interleaved, sampwidth)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(n_channels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(_WAV_RATE)
        wav.writeframes(raw)


@pytest.mark.parametrize("sampwidth", [1, 2, 3, 4], ids=["8bit", "16bit", "24bit", "32bit"])
@pytest.mark.parametrize("n_channels", [1, 2], ids=["mono", "stereo"])
def test_spectrogram_renders_for_pcm_wav(
    tmp_path: Path,
    sampwidth: int,
    n_channels: int,
) -> None:
    """Every PCM width and channel count yields RGB spectrogram + waveform PNGs."""
    wav = tmp_path / "tone.wav"
    _write_sine_wav(wav, sampwidth=sampwidth, n_channels=n_channels)
    SpectrogramAnalyzer.execute(wav, tmp_path)

    entry = _read_results(tmp_path)["spectrogram"]
    assert entry["status"] == "ok", entry
    assert entry["images"]["Spectrogram"], entry
    assert entry["output"]["Sample rate"] == f"{_WAV_RATE} Hz"
    assert entry["output"]["Channels"] == str(n_channels)

    for name in ("spectrogram.png", "waveform.png"):
        png = tmp_path / name
        assert png.exists(), name
        with Image.open(png) as img:
            img.load()
            assert img.mode == "RGB", (name, img.mode)


def test_spectrogram_errors_on_non_audio(tmp_path: Path) -> None:
    """Running the audio analyzer on an image records an error, never an exception."""
    SpectrogramAnalyzer.execute(FIXTURES / "openstego.png", tmp_path)
    entry = _read_results(tmp_path)["spectrogram"]
    assert entry["status"] == "error", entry


@pytest.mark.skipif(shutil.which("pdfinfo") is None, reason="pdfinfo binary not installed")
def test_pdfinfo_reports_metadata(tmp_path: Path) -> None:
    """Poppler's pdfinfo returns metadata lines for the sample PDF."""
    output_dir = tmp_path / FIXTURE_PDF.stem
    output_dir.mkdir()
    shutil.copy(FIXTURE_PDF, tmp_path / FIXTURE_PDF.name)
    PdfinfoAnalyzer.execute(tmp_path / FIXTURE_PDF.name, output_dir)
    results = _read_results(output_dir)
    assert results["pdfinfo"]["status"] == "ok", results["pdfinfo"]
    assert results["pdfinfo"]["output"]


@pytest.mark.skipif(shutil.which("pdfid") is None, reason="pdfid binary not installed")
def test_pdfid_triages_objects(tmp_path: Path) -> None:
    """Didier Stevens' pdfid returns suspicious-object counts for the sample PDF."""
    output_dir = tmp_path / FIXTURE_PDF.stem
    output_dir.mkdir()
    shutil.copy(FIXTURE_PDF, tmp_path / FIXTURE_PDF.name)
    PdfidAnalyzer.execute(tmp_path / FIXTURE_PDF.name, output_dir)
    results = _read_results(output_dir)
    assert results["pdfid"]["status"] == "ok", results["pdfid"]
    assert results["pdfid"]["output"]


def test_detect_file_type_png() -> None:
    """A PNG fixture classifies as an image carrying png + image tags."""
    ft = detect_file_type(EXAMPLE_IMAGE)
    assert ft.kind == "image"
    assert "png" in ft.tags
    assert "image" in ft.tags


def test_detect_file_type_wav() -> None:
    """The tone WAV fixture classifies as audio."""
    ft = detect_file_type(FIXTURES / "tone.wav")
    assert ft.kind == "audio"
    assert "audio" in ft.tags


def test_detect_file_type_unknown_binary(tmp_path: Path) -> None:
    """An unrecognised .bin blob degrades to kind 'other' with no gating tags."""
    blob = tmp_path / "mystery.bin"
    blob.write_bytes(os.urandom(4096))
    ft = detect_file_type(blob)
    assert ft.kind == "other"
    assert ft.tags == frozenset()


def test_detect_file_type_missing_path_never_raises() -> None:
    """Classifying a non-existent path degrades gracefully instead of raising."""
    ft = detect_file_type(Path("/nonexistent/aperisolve/does-not-exist.bin"))
    assert ft.kind == "other"
    assert ft.tags == frozenset()


def _synthetic_image(path: Path, mode: str, size: tuple[int, int] = (16, 16)) -> None:
    """Write a small deterministic image in the requested PIL ``mode``.

    A fixed ramp (rather than random noise) keeps the input reproducible; the
    remapping the analyzer applies on top is what varies.
    """
    w, h = size
    base = (np.arange(w * h, dtype=np.uint8) % 251).reshape(h, w)
    if mode == "L":
        Image.fromarray(base, "L").save(path)
        return
    green = (base + 80).astype(np.uint8)
    blue = (base + 160).astype(np.uint8)
    if mode == "RGB":
        Image.fromarray(np.dstack([base, green, blue]), "RGB").save(path)
    elif mode == "RGBA":
        alpha = np.full((h, w), 200, dtype=np.uint8)
        Image.fromarray(np.dstack([base, green, blue, alpha]), "RGBA").save(path)
    elif mode == "P":
        Image.fromarray(np.dstack([base, green, blue]), "RGB").convert("P").save(path)
    else:
        msg = f"unsupported mode {mode}"
        raise ValueError(msg)


@pytest.mark.parametrize(
    ("mode", "expected_out_mode"),
    [("L", "RGB"), ("RGB", "RGB"), ("RGBA", "RGBA"), ("P", "RGB")],
)
def test_color_remapping_supports_common_modes(
    tmp_path: Path,
    mode: str,
    expected_out_mode: str,
) -> None:
    """Grayscale, RGB, RGBA and palette inputs each yield the full set of PNGs.

    RGBA keeps its alpha channel (output stays RGBA); every other mode is
    emitted as RGB, exercising both branches of ``_create_remapped_image``.
    """
    src = tmp_path / f"{mode.lower()}.png"
    _synthetic_image(src, mode)
    ColorRemappingAnalyzer.execute(src, tmp_path)

    entry = _read_results(tmp_path)["color_remapping"]
    assert entry["status"] == "ok", entry
    assert len(entry["images"]["Color Remapping"]) == RANDOM_REMAPPING_COUNT

    for i in range(RANDOM_REMAPPING_COUNT):
        png = tmp_path / f"color_remapping_{i:02d}.png"
        assert png.exists(), png
        with Image.open(png) as img:
            img.load()
            assert img.mode == expected_out_mode, (png.name, img.mode)


def test_color_remapping_notes_palette_conversion(tmp_path: Path) -> None:
    """A palette (mode 'P') input is converted to RGB and carries the note."""
    src = tmp_path / "palette.png"
    _synthetic_image(src, "P")
    ColorRemappingAnalyzer.execute(src, tmp_path)

    entry = _read_results(tmp_path)["color_remapping"]
    assert entry["status"] == "ok", entry
    assert entry["note"] == PALETTE_NOTE


def test_color_remapping_errors_on_undecodable_input(tmp_path: Path) -> None:
    """A file Pillow cannot decode is recorded as an error, never an exception."""
    junk = tmp_path / "not-an-image.png"
    junk.write_bytes(os.urandom(2048))
    ColorRemappingAnalyzer.execute(junk, tmp_path)

    entry = _read_results(tmp_path)["color_remapping"]
    assert entry["status"] == "error", entry
