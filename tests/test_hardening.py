"""Tests for the July 2026 hardening: env parsing and decompression bombs."""

import struct
import zlib
from pathlib import Path

import pytest

from aperisolve.analyzers.pil_utils import load_image_array
from aperisolve.config import _int_env
from aperisolve.filetype import _mime_from_pillow
from aperisolve.utils.sentry import _float_env


def _png_with_declared_size(path: Path, width: int, height: int) -> Path:
    """Write a tiny PNG whose header declares arbitrary dimensions.

    Only the IHDR is honest about size; the IDAT payload is junk. Pillow reads
    dimensions lazily from the header, so the guards under test must trigger
    before any pixel decoding happens.
    """

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">II5B", width, height, 8, 2, 0, 0, 0)
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00"))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(blob)
    return path


def test_int_env_empty_string_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """The deploy writes KEY= for unset GitHub variables; int('') must not crash."""
    monkeypatch.setenv("APERI_TEST_INT", "")
    assert _int_env("APERI_TEST_INT", 42) == 42


def test_int_env_reads_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set values are parsed; missing ones fall back."""
    monkeypatch.setenv("APERI_TEST_INT", "7")
    assert _int_env("APERI_TEST_INT", 42) == 7
    monkeypatch.delenv("APERI_TEST_INT")
    assert _int_env("APERI_TEST_INT", 42) == 42


def test_float_env_empty_string_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same contract as _int_env, for the Sentry sample rates."""
    monkeypatch.setenv("APERI_TEST_FLOAT", "")
    assert _float_env("APERI_TEST_FLOAT", 0.1) == 0.1
    monkeypatch.setenv("APERI_TEST_FLOAT", "0.5")
    assert _float_env("APERI_TEST_FLOAT", 0.1) == 0.5


def test_oversized_image_rejected_before_decode(tmp_path: Path) -> None:
    """Images above the megapixel cap come back as a clean error result."""
    png = _png_with_declared_size(tmp_path / "big.png", 10_000, 10_000)
    loaded = load_image_array(png)
    assert loaded.array is None
    assert loaded.error is not None
    assert "megapixel" in loaded.error["error"]


def test_decompression_bomb_rejected(tmp_path: Path) -> None:
    """Sizes past Pillow's own bomb threshold error cleanly instead of raising."""
    png = _png_with_declared_size(tmp_path / "bomb.png", 25_000, 25_000)
    loaded = load_image_array(png)
    assert loaded.array is None
    assert loaded.error is not None


def test_filetype_probe_survives_decompression_bomb(tmp_path: Path) -> None:
    """detect_file_type's Pillow probe must not blow up the RQ job on a bomb."""
    png = _png_with_declared_size(tmp_path / "bomb.png", 25_000, 25_000)
    assert _mime_from_pillow(png) == ""
