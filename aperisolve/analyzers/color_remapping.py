# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801,W0612
# mypy: disable-error-code=unused-awaitable
"""Color Remapping Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

from .base_analyzer import SubprocessAnalyzer


class ColorRemappingAnalyzer(SubprocessAnalyzer):
    """Analyzer for color remapping."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("color_remapping", input_img, output_dir)

    def get_results(self, _: Optional[str] = None) -> dict[str, Any]:
        """Analyze an image submission using color remapping."""
        img = Image.open(self.input_img)
        converted = False

        if img.mode == "P":
            img = img.convert("RGB")
            converted = True

        img_np = np.array(img)

        # Handle grayscale, RGB, RGBA, etc.
        if len(img_np.shape) == 2:
            channels = 1
            img_np = np.expand_dims(img_np, axis=-1)
        else:
            channels = img_np.shape[2]

        # Ensure we have at least 3 channels (RGB)
        if channels < 3:
            # Grayscale to RGB
            if channels == 1:
                img_np = np.repeat(img_np, 3, axis=2)
            # Add alpha channel if needed
            if channels == 3:
                alpha = np.full((img_np.shape[0], img_np.shape[1], 1), 255, dtype=np.uint8)
                img_np = np.concatenate([img_np, alpha], axis=2)
        elif channels == 4:
            # RGBA is fine
            pass
        else:
            # More than 4 channels, take first 3
            img_np = img_np[..., :3]

        image_json = []

        # Generate 8 random color remappings
        for i in range(8):
            # Create a random permutation of color values (0-255)
            # For each original color value, map it to a new random value
            color_map = np.random.randint(0, 256, size=256, dtype=np.uint8)

            # Apply the color remapping to each channel
            remapped = np.zeros_like(img_np)
            for c in range(min(3, channels)):  # Apply to RGB channels
                remapped[..., c] = color_map[img_np[..., c]]

            # Keep alpha channel if present
            if channels == 4:
                remapped[..., 3] = img_np[..., 3]

            # Create the remapped image
            if channels == 4:
                remapped_img = Image.fromarray(remapped.astype(np.uint8), mode="RGBA")
            else:
                remapped_img = Image.fromarray(remapped[..., :3].astype(np.uint8), mode="RGB")

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
