"""Shared image loading for the PIL/NumPy-based analyzers."""

from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from PIL import Image, UnidentifiedImageError

PALETTE_NOTE = "Image contains a color palette and was converted to RGB for processing."

# Hard ceiling on decoded size: a ~1 MB highly-compressible PNG can decode to
# hundreds of MB, and the decomposer then materializes dozens of full-size
# planes — enough to OOM the 2 GB worker. 64 MP (8000x8000) is far above any
# legitimate stego challenge. Checked from the header before pixel data is
# decoded; Pillow's own MAX_IMAGE_PIXELS stays as a second net.
MAX_IMAGE_PIXELS = 64_000_000


class LoadedImage(NamedTuple):
    """Decoded image array, or a ready-to-store error result."""

    array: np.ndarray | None
    converted: bool
    error: dict[str, Any] | None


def _error(message: str) -> LoadedImage:
    return LoadedImage(array=None, converted=False, error={"status": "error", "error": message})


def load_image_array(path: Path) -> LoadedImage:
    """Load an image as a NumPy array, converting palette images to RGB.

    Corrupt/polyglot uploads are expected input, not an exception worth a
    Sentry report (issue #192), so decode failures come back as an error
    result the analyzer can store as-is. Decompression bombs likewise: they
    are rejected on declared dimensions, not decoded.
    """
    try:
        with Image.open(path) as img:
            if img.width * img.height > MAX_IMAGE_PIXELS:
                return _error(
                    f"Image dimensions {img.width}x{img.height} exceed the "
                    f"{MAX_IMAGE_PIXELS // 1_000_000} megapixel processing limit.",
                )
            converted = False
            decoded = img
            if img.mode == "P":
                decoded = img.convert("RGB")
                converted = True
            array = np.array(decoded)
    except UnidentifiedImageError:
        return _error("Pillow cannot decode this file as an image.")
    except Image.DecompressionBombError:
        return _error("Image rejected: decoded size would be a decompression bomb.")
    return LoadedImage(array=array, converted=converted, error=None)
