"""Utility functions for analyzers modules."""

import fcntl
import json
import math
import os
import struct
import threading
import zlib
from functools import cached_property
from pathlib import Path
from typing import Any, Self

_thread_lock = threading.Lock()

MAX_PENDING_TIME = int(os.getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default

# PATH CONFIGURATION
# Prioritize /data for Docker persistence, fallback to local directory for bare metal


def update_data(
    output_dir: Path, new_data: dict[Any, Any], json_filename: str = "results.json"
) -> None:
    """Thread-safe and process-safe JSON update using lock file and atomic replace."""
    json_file = Path(output_dir) / json_filename
    lock_file = json_file.with_suffix(json_file.suffix + ".lock")
    tmp_file = json_file.with_suffix(json_file.suffix + ".tmp")

    json_file.parent.mkdir(parents=True, exist_ok=True)

    with _thread_lock:  # synchronizes across threads
        with open(lock_file, "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # synchronizes across processes

            try:
                # Read existing JSON
                data: dict[Any, Any] = {}
                if json_file.exists():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}

                # Update with new data
                data.update(new_data)

                # Write safely to a temp file
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, sort_keys=False)

                os.replace(tmp_file, json_file)  # ensures file write is atomic
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def get_resolutions():
    BASE_WIDTHS = (
        list(range(16, 257, 16))  # 16 → 256
        + list(range(320, 1025, 32))  # 320 → 1024
        + list(range(1280, 2561, 64))  # 1280 → 2560
        + list(range(3000, 4097, 128))  # 3K–4K
        + list(range(5120, 8193, 256))  # 5K–8K
        + [10000]  # upper bound
    )
    ASPECT_RATIOS = [
        # Screens / digital
        (1, 1),  # square
        (4, 3),
        (3, 2),
        (16, 10),
        (16, 9),
        (21, 9),
        # Photography / print
        (5, 4),  # 8x10
        (7, 5),  # 5x7
        (3, 2),  # 4x6 (already included, kept for clarity)
        (2, 3),  # poster
        # Paper standards
        (1414, 1000),  # ISO A-series (A4, A3, A2, ...)
        (11, 85),  # US Letter
        (14, 85),  # Legal
        (17, 11),  # Tabloid
    ]
    resolutions = set()
    for w in BASE_WIDTHS:
        for ar_w, ar_h in ASPECT_RATIOS:
            h = math.floor(round(w * ar_h / ar_w))
            if 1 <= h <= 10000:
                resolutions.add((w, h))
                resolutions.add((h, w))  # portrait / landscape
    return sorted(resolutions)


def get_valid_depth_color_pairs():
    VALID_COLOR_DEPTHS = {
        0: [1, 2, 4, 8, 16],
        2: [8, 16],
        3: [1, 2, 4, 8],
        4: [8, 16],
        6: [8, 16],
    }
    for color, depths in VALID_COLOR_DEPTHS.items():
        for depth in depths:
            yield depth, color


class PNG:
    """
    A class representing a PNG image header (IHDR chunk).
    This class encapsulates the metadata from a PNG file's IHDR (Image Header) chunk,
    including image dimensions, bit depth, color type, interlacing method, and CRC checksum.
    It provides methods for parsing PNG files, packing/unpacking header data, and generating
    PNG crc if omitted.
    """

    width: int
    height: int
    bit_depth: int
    color_type: int
    crc: int
    interlace: int = 0

    def __init__(
        self,
        width: int,
        height: int,
        bit_depth: int,
        color_type: int,
        crc: int | None = None,
        interlace: int = 0,
    ):
        """Initialize a PNG IHDR (Image Header) chunk.

        Args:
            width (int): The width of the image in pixels.
            height (int): The height of the image in pixels.
            bit_depth (int): The number of bits per sample or per palette index (1, 2, 4, 8, or 16).
            color_type (int): The color type of the image (0=Grayscale, 2=RGB, 3=Indexed,
                              4=Grayscale+Alpha, 6=RGBA).
            crc (int | None, optional): CRC (Cyclic Redundancy Check) checksum for the chunk.
                                        If None, it will be calculated automatically. Defaults
                                        to None.
            interlace (int, optional): The interlace method (0=no interlace, 1=Adam7 interlace).
                                       Defaults to 0.
        """
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.color_type = color_type
        self.crc = (
            crc
            or zlib.crc32(
                b"IHDR"
                + width.to_bytes(4, "big")
                + height.to_bytes(4, "big")
                + bytes((bit_depth, color_type, 0, 0, interlace))
            )
            & 0xFFFFFFFF
        )
        self.interlace = interlace

    @classmethod
    def from_packed(cls, packed: int, crc: int | None = None) -> Self:
        """Create a PNG instance from a packed integer representation.

        Parse a packed integer containing width, height, bit depth, color type and interlace
        bits and return a PNG instance. The CRC may be supplied; if omitted it will be
        computed by the constructor.

        Args:
            packed (int): Packed integer with fields laid out as described in the `packed` property.
            crc (int | None): Optional CRC value for the IHDR chunk.

        Returns:
            Self: PNG instance with parsed fields.
        """
        interlace = packed & 0b1
        color = (packed >> 1) & 0b111
        depth = (packed >> 4) & 0b111
        height = (packed >> 7) & 0xFFFF
        width = (packed >> 23) & 0xFFFF
        return cls(
            width=width,
            height=height,
            bit_depth=depth,
            color_type=color,
            crc=crc,
            interlace=interlace,
        )

    @cached_property
    def packed(self) -> int:
        """Pack IHDR fields into a single integer.

        Returns:
            int: Packed integer encoding the IHDR fields.

        Layout:
            width     : 16 bits
            height    : 16 bits
            depth     : 3 bits
            color     : 3 bits
            interlace : 1 bit
        """
        return (
            ((self.width & 0xFFFF) << 23)
            | ((self.height & 0xFFFF) << 7)
            | ((self.bit_depth & 0b111) << 4)
            | ((self.color_type & 0b111) << 1)
            | (self.interlace & 0b1)
        )

    @classmethod
    def from_bytearray(cls, data: bytearray) -> Self:
        """Create a PNG image instance from a bytearray containing PNG file data.

        Parses the PNG signature and IHDR (Image Header) chunk to extract image metadata
        including dimensions, bit depth, color type, and interlacing information.

        Args:
            data (bytearray): A bytearray containing the complete PNG file data, starting
                with the PNG signature (8 bytes: \\x89PNG\\r\\n\\x1a\\n).

        Returns:
            Self | None: A new instance of the PNG image class with parsed IHDR metadata
                (width, height, bit_depth, color_type, crc, interlace) if the data is
                valid and contains a proper IHDR chunk. Returns None if the PNG signature
                is invalid or the IHDR chunk type is not found.

        Raises:
            struct.error: If the data is too short or malformed for unpacking IHDR fields.
            IndexError: If the bytearray is shorter than expected for the PNG structure.
        """

        PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
        if data[:8] != PNG_SIGNATURE:
            raise ValueError("Invalid PNG signature")
        offset = 8  # Read IHDR chunk
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        chunk_type = data[offset : offset + 4]
        offset += 4
        if chunk_type != b"IHDR":
            raise ValueError("IHDR chunk not found at expected position")

        ihdr_data = data[offset : offset + length]
        offset += length

        crc = struct.unpack(">I", data[offset : offset + 4])[0]

        # Unpack IHDR fields
        width, height, depth, color, _, _, interlace = struct.unpack(
            ">IIBBBBB", ihdr_data
        )

        return cls(
            width=width,
            height=height,
            bit_depth=depth,
            color_type=color,
            crc=crc,
            interlace=interlace,
        )

    def __repr__(self) -> str:
        return (
            f"PNG(width={self.width}, height={self.height}, "
            f"bit_depth={self.bit_depth}, color_type={self.color_type}, "
            f"interlace={self.interlace}, crc=0x{self.crc:08x})"
        )
