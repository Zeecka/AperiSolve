"""Bits Decomposer Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .base_analyzer import SubprocessAnalyzer

RGB_CHANNEL_THRESHOLD = 3
GRAYSCALE_DIMENSIONS = 2


class DecomposerAnalyzer(SubprocessAnalyzer):
    """Analyzer for bits decomposer."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the decomposer analyzer."""
        super().__init__("decomposer", input_img, output_dir)

    def get_results(self, _: str | None = None) -> dict[str, Any]:
        """Analyze an image submission using bits decomposition."""
        img = Image.open(self.input_img)
        converted = False

        if img.mode == "P":
            img = img.convert("RGB")
            converted = True

        img_np = np.array(img)

        # Handle grayscale, RGB, RGBA, etc.
        channels = 1 if len(img_np.shape) == GRAYSCALE_DIMENSIONS else img_np.shape[2]

        channel_names = ["Red", "Green", "Blue", "Alpha"] if channels > 1 else ["Grayscale"]

        image_json = {}

        # Add Superimposed RGB bit planes
        if channels >= RGB_CHANNEL_THRESHOLD:
            superimposed_json = []
            for bit in range(8):
                bit_mask = 1 << bit
                rgb_planes = [((img_np[..., c] & bit_mask) >> bit) * 255 for c in range(3)]
                rgb_image = np.stack(rgb_planes, axis=-1).astype(np.uint8)
                rgb_img = Image.fromarray(rgb_image, mode="RGB")
                img_name = f"superimposed_bit_{bit}.png"
                out_path = self.output_dir / img_name
                dl_path = Path(self.output_dir.name) / img_name
                superimposed_json.append("/image/" + str(dl_path))
                rgb_img.save(out_path)

            image_json["Superimposed"] = superimposed_json

        # Process individual channels
        for c in range(channels):
            channel_data = img_np[..., c] if channels > 1 else img_np
            channel_label = channel_names[c]
            channel_json = []
            for bit in range(8):
                bit_mask = 1 << bit
                bit_plane = ((channel_data & bit_mask) >> bit) * 255
                bit_img = Image.fromarray(bit_plane.astype(np.uint8), mode="L")
                img_name = f"{channel_label}_bit_{bit}.png"
                out_path = self.output_dir / img_name
                dl_path = Path(self.output_dir.name) / img_name
                channel_json.append("/image/" + str(dl_path))
                bit_img.save(out_path)
            image_json[channel_label] = channel_json

        output = {
            "status": "ok",
            "images": image_json,
        }
        if converted:
            output["note"] = (
                "Image contains a color palette and was converted to RGB for processing."
            )

        return output


def analyze_decomposer(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using bits decomposition."""
    analyzer = DecomposerAnalyzer(input_img, output_dir)
    analyzer.analyze()
