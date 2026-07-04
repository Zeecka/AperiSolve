"""Shared image loading for the PIL/NumPy-based analyzers."""

from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from PIL import Image, UnidentifiedImageError

PALETTE_NOTE = "Image contains a color palette and was converted to RGB for processing."


class LoadedImage(NamedTuple):
    """Decoded image array, or a ready-to-store error result."""

    array: np.ndarray | None
    converted: bool
    error: dict[str, Any] | None


def load_image_array(path: Path) -> LoadedImage:
    """Load an image as a NumPy array, converting palette images to RGB.

    Corrupt/polyglot uploads are expected input, not an exception worth a
    Sentry report (issue #192), so decode failures come back as an error
    result the analyzer can store as-is.
    """
    try:
        img = Image.open(path)
    except UnidentifiedImageError:
        return LoadedImage(
            array=None,
            converted=False,
            error={"status": "error", "error": "Pillow cannot decode this file as an image."},
        )
    converted = False
    if img.mode == "P":
        img = img.convert("RGB")
        converted = True
    return LoadedImage(array=np.array(img), converted=converted, error=None)
