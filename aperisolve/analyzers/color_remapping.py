"""Color Remapping Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .base_analyzer import SubprocessAnalyzer

RGB_CHANNEL_COUNT = 3
RGBA_CHANNEL_COUNT = 4
RANDOM_REMAPPING_COUNT = 8
GRAYSCALE_DIMENSIONS = 2


class ColorRemappingAnalyzer(SubprocessAnalyzer):
    """Analyzer for color remapping."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the color remapping analyzer."""
        super().__init__("color_remapping", input_img, output_dir)

    def _normalize_image(self, img_np: np.ndarray) -> tuple[np.ndarray, int]:
        """Normalize image to have RGB or RGBA channels.

        Returns:
            Tuple of (normalized image array, number of channels)

        """
        if len(img_np.shape) == GRAYSCALE_DIMENSIONS:
            channels = 1
            img_np = np.expand_dims(img_np, axis=-1)
        else:
            channels = img_np.shape[2]

        if channels < RGB_CHANNEL_COUNT:
            # Grayscale to RGB
            img_np = np.repeat(img_np, RGB_CHANNEL_COUNT, axis=2)
            channels = RGB_CHANNEL_COUNT
        elif channels > RGBA_CHANNEL_COUNT:
            # More than 4 channels, take first 3
            img_np = img_np[..., :RGB_CHANNEL_COUNT]
            channels = RGB_CHANNEL_COUNT

        return img_np, channels

    def _create_remapped_image(self, img_np: np.ndarray, color_map: np.ndarray) -> Image.Image:
        """Create a single remapped image using the color map."""
        remapped = np.zeros_like(img_np)
        for c in range(min(RGB_CHANNEL_COUNT, img_np.shape[2])):  # Apply to RGB channels
            remapped[..., c] = color_map[img_np[..., c]]

        # Keep alpha channel if present
        if img_np.shape[2] == RGBA_CHANNEL_COUNT:
            remapped[..., 3] = img_np[..., 3]
            remapped_img = Image.fromarray(remapped.astype(np.uint8), mode="RGBA")
        else:
            remapped_img = Image.fromarray(
                remapped[..., :RGB_CHANNEL_COUNT].astype(np.uint8),
                mode="RGB",
            )

        return remapped_img

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Analyze an image submission using color remapping."""
        _ = password
        img = Image.open(self.input_img)
        converted = False

        if img.mode == "P":
            img = img.convert("RGB")
            converted = True

        img_np_tmp = np.array(img)
        img_np, _channels = self._normalize_image(img_np_tmp)

        image_json = []

        # Generate 8 random color remappings
        rng = np.random.default_rng()
        for i in range(RANDOM_REMAPPING_COUNT):
            # Create a random permutation of color values (0-255)
            color_map = rng.integers(0, 256, size=256, dtype=np.uint8)
            remapped_img = self._create_remapped_image(img_np, color_map)

            # Save the remapped image
            img_name = f"color_remapping_{i:02d}.png"
            out_path = self.output_dir / img_name
            dl_path = Path(self.output_dir.name) / img_name
            image_json.append("/image/" + str(dl_path))
            remapped_img.save(out_path)

        output = {
            "status": "ok",
            "images": {
                "Color Remapping": image_json,
            },
        }
        if converted:
            output["note"] = (
                "Image contains a color palette and was converted to RGB for processing."
            )

        return output


def analyze_color_remapping(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using color remapping."""
    analyzer = ColorRemappingAnalyzer(input_img, output_dir)
    analyzer.analyze()
