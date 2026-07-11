"""Tests for PNG repair, covering the bounded DOS->Unix search (GHSA fix).

A malformed IDAT chunk must not be able to force a combinatorial CRC search
(C(len(pos_list), count)) whose size is taken straight from the uploaded file.
"""

import struct
import time
import zlib

from aperisolve.utils.png import MAX_DOS2UNIX_COMBINATIONS, PNG


def _crc(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack("!I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)


def test_dos2unix_recovers_genuine_mangling() -> None:
    """A real CRLF->LF stripping is still repaired (fix must not break recovery)."""
    original = b"AB\x0d\x0aCD\x0d\x0aEF\x0d\x0aGH"
    mangled = original.replace(b"\x0d\x0a", b"\x0a")
    count = original.count(b"\x0d\x0a")

    recovered = PNG(b"")._fix_dos2unix(  # noqa: SLF001
        b"IDAT", mangled, _crc(b"IDAT", original), count,
    )

    assert recovered == original


def test_dos2unix_rejects_oversized_search_fast() -> None:
    """The PoC-shaped chunk (C(28, 11) ~ 21M) is skipped without running it."""
    chunk_data = b"\x0a" * 28 + b"AB"
    bad_crc = struct.pack("!I", 0xDEADBEEF)

    start = time.monotonic()
    result = PNG(b"")._fix_dos2unix(b"IDAT", chunk_data, bad_crc, 11)  # noqa: SLF001
    elapsed = time.monotonic() - start

    assert result is None
    assert elapsed < 1.0  # would be tens of seconds without the cap


def test_dos2unix_rejects_excessive_insertion_count() -> None:
    """A count larger than the allowed insertions is refused up front."""
    chunk_data = b"\x0a" * 200
    result = PNG(b"")._fix_dos2unix(  # noqa: SLF001
        b"IDAT", chunk_data, b"\x00\x00\x00\x00", 100,
    )
    assert result is None


def test_repair_on_malicious_idat_returns_quickly() -> None:
    """End-to-end: a tiny crafted PNG cannot pin the repair loop."""
    sig = b"\x89PNG\r\n\x1a\x0a"
    ihdr_data = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + _crc(b"IHDR", ihdr_data)

    payload = b"\x0a" * 28 + b"AB"
    declared = len(payload) - 11  # length != actual -> triggers dos2unix path
    idat = struct.pack(">I", declared) + b"IDAT" + payload + _crc(b"IDAT", payload)
    iend = struct.pack(">I", 0) + b"IEND" + _crc(b"IEND", b"")
    data = sig + ihdr + idat + iend

    start = time.monotonic()
    PNG(data).repair()
    assert time.monotonic() - start < 2.0


def test_combination_cap_is_small() -> None:
    """Guard against a future edit quietly raising the cap to an unsafe value."""
    assert MAX_DOS2UNIX_COMBINATIONS <= 1_000_000
