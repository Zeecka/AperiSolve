"""Bits Decomposer Analyzer for Image Submissions."""

from pathlib import Path

import numpy as np
from PIL import Image

from .utils import update_data


def analyze_decomposer(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using bits decomposition."""
    img = Image.open(input_img)
    img_np = np.array(img)

    # Handle grayscale, RGB, RGBA, etc.
    if len(img_np.shape) == 2:
        channels = 1
    else:
        channels = img_np.shape[2]

    if channels > 1:
        channel_names = ["Red", "Green", "Blue", "Alpha"]
    else:
        channel_names = ["Grayscale"]

    image_json = {}

    # Add Superimposed RGB bit planes
    if channels >= 3:
        superimposed_json = []
        for bit in range(8):
            bit_mask = 1 << bit
            rgb_planes = [((img_np[..., c] & bit_mask) >> bit) * 255 for c in range(3)]
            rgb_image = np.stack(rgb_planes, axis=-1).astype(np.uint8)
            rgb_img = Image.fromarray(rgb_image, mode="RGB")
            img_name = f"superimposed_bit_{bit}.png"
            out_path = output_dir / img_name
            dl_path = Path(output_dir.name) / img_name
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
            out_path = output_dir / img_name
            dl_path = Path(output_dir.name) / img_name
            channel_json.append("/image/" + str(dl_path))
            bit_img.save(out_path)
        image_json[channel_label] = channel_json

    update_data(
        output_dir,
        {
            "decomposer": {
                "status": "ok",
                "images": image_json,
            }
        },
    )
