# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Utility functions for analyzers modules."""

import binascii
import math
import struct
from typing import Iterable


def str2hex(s: bytes) -> str:
    """Convert bytes to hex string."""
    return binascii.hexlify(s).decode().upper()


def int2hex(i: int) -> str:
    """Convert int to hex string with 0x prefix."""
    return "0x" + hex(i)[2:].upper()


def get_resolutions() -> list[tuple[int, int]]:
    """
    Generate a sorted list of common display and image resolutions.

    Creates a comprehensive set of resolution tuples by combining various base widths
    with standard aspect ratios used in screens, digital displays, photography, and
    paper standards. Includes both portrait and landscape orientations.

    Base widths range from 16px to 10000px, covering:
    - Low resolution: 16-256px (16px increments)
    - Standard: 320-1024px (32px increments)
    - HD/Full HD: 1280-2560px (64px increments)
    - 4K: 3000-4096px (128px increments)
    - 5K-8K: 5120-8192px (256px increments)
    - Upper bound: 10000px

    Aspect ratios include common formats:
    - Digital screens: 1:1, 4:3, 3:2, 16:10, 16:9, 21:9
    - Photography/print: 5:4, 7:5, 2:3
    - Paper standards: ISO A-series, US Letter, Legal, Tabloid

    Returns:
        list[tuple[int, int]]: Sorted list of (width, height) resolution tuples
                               with heights constrained between 1 and 10000 pixels.
    """
    base_widths = (
        list(range(16, 257, 16))  # 16 → 256
        + list(range(320, 1025, 32))  # 320 → 1024
        + list(range(1280, 2561, 64))  # 1280 → 2560
        + list(range(3000, 4097, 128))  # 3K–4K
        + list(range(5120, 8193, 256))  # 5K–8K
        + [10000]  # upper bound
    )
    aspect_ratios = [
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
    resolutions: set[tuple[int, int]] = set()
    for w in base_widths:
        for ar_w, ar_h in aspect_ratios:
            h = math.floor(round(w * ar_h / ar_w))
            if 1 <= h <= 10000:
                resolutions.add((w, h))
                resolutions.add((h, w))  # portrait / landscape
    return sorted(resolutions)


def get_valid_depth_color_pairs() -> Iterable[tuple[int, int]]:
    """
    Generate valid combinations of color and bit depth values.

    Yields tuples of (depth, color) representing valid color mode and bit depth
    combinations. Supports grayscale (0), RGB (2, 3, 4, 6) color modes with
    appropriate bit depths (1, 2, 4, 8, 16 bits).

    Yields:
        tuple: A tuple of (depth, color) where depth is an integer representing
               bit depth and color is an integer representing the color mode.
    """
    valid_color_depth = {
        0: [1, 2, 4, 8, 16],
        2: [8, 16],
        3: [1, 2, 4, 8],
        4: [8, 16],
        6: [8, 16],
    }
    for color, depths in valid_color_depth.items():
        for depth in depths:
            yield depth, color
