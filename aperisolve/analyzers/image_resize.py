"""Image size bruteforcer for common PNG sizes."""

import zlib
from itertools import product
from pathlib import Path
from typing import Iterator
import numpy as np
from .utils import update_data


def generate_probable_sizes() -> Iterator[tuple[int, int]]:
    """Generator that yields probable image sizes in order of likelihood."""

    # fmt: off
    # Pre-merged high-priority candidates (squares + common ratios)
    priority_sizes = [
        # Common squares
        (16, 16), (20, 20), (24, 24), (28, 28), (32, 32), (48, 48), (64, 64), (72, 72), 
        (96, 96), (128, 128), (192, 192), (256, 256), (384, 384), (512, 512), (768, 768), 
        (1024, 1024), (1536, 1536), (2048, 2048), (4096, 4096), (300, 300), (500, 500), 
        (800, 800), (1000, 1000), (1500, 1500), (2000, 2000), (2500, 2500), (3000, 3000),
        # 16:9 (most common)
        (426, 240), (640, 360), (854, 480), (960, 540), (1280, 720), (1366, 768), 
        (1600, 900), (1920, 1080), (2560, 1440), (3200, 1800), (3440, 1935), 
        (3840, 2160), (5120, 2880), (7680, 4320), (10240, 5760),
        # 4:3
        (320, 240), (640, 480), (800, 600), (960, 720), (1024, 768), (1280, 960), 
        (1600, 1200), (2048, 1536), (2560, 1920), (3200, 2400), (4096, 3072),
        # Social media
        (1080, 1080), (1080, 1350), (1200, 628), (1200, 1200), (1200, 675), 
        (1500, 500), (1600, 500), (1920, 500), (2560, 700), (3000, 1000), (3840, 1200),
        # 16:10
        (1280, 800), (1440, 900), (1680, 1050), (1920, 1200), (2560, 1600), 
        (2880, 1800), (3840, 2400), (5120, 3200),
        # 9:16 (vertical)
        (720, 1280), (1080, 1920), (1440, 2560), (2160, 3840), (1440, 2960), 
        (1080, 2400), (1170, 2532), (1284, 2778), (1290, 2796),
        # 3:2
        (600, 400), (900, 600), (1200, 800), (1500, 1000), (1800, 1200), (2400, 1600), 
        (3000, 2000), (3600, 2400), (4500, 3000), (6000, 4000),
        # Print
        (2550, 3300), (2480, 3508), (3508, 4961), (4961, 7016), (7016, 9933)
    ]
    # fmt: on

    seen = set(priority_sizes)
    yield from priority_sizes

    # Remaining squares up to 3000x3000
    remaining_squares = ((w, w) for w in range(1, 3001) if (w, w) not in seen)
    yield from remaining_squares

    # Common aspect ratios up to 3000x3000 - vectorized with numpy
    for num, den in [(16, 9), (4, 3), (3, 2), (9, 16)]:
        widths = np.arange(1, 3001, dtype=np.int32)
        heights = (widths * den) // num
        # Filter valid heights
        valid_mask = (
            (heights >= 1) & (heights <= 3000) & (heights * num == widths * den)
        )

        for w, h in zip(widths[valid_mask], heights[valid_mask]):
            size = (int(w), int(h))
            if size not in seen:
                seen.add(size)
                yield size

    # Brute-force remaining sizes
    for size in product(range(1, 3001), repeat=2):
        if size not in seen:
            yield size


def analyze_image_resize(input_img: Path, output_dir: Path) -> None:
    """
    Analyze an image using resize bruteforce.
    Attempts to recover PNGs with modified resolutions but valid CRCs.
    """
    input_img = Path(input_img)
    output_dir = Path(output_dir)
    logs = []

    try:
        # Read entire file
        data = bytearray(input_img.read_bytes())

        # Find IHDR chunk
        ihdr_pos = data.find(b"\x49\x48\x44\x52")
        if ihdr_pos == -1:
            logs.append("Failure: PNG header (IHDR) not found.")
            update_data(
                output_dir,
                {"image_resize": {"status": "error", "error": "PNG header not found."}},
            )
            return

        # Extract chunk info
        chunk_len = int.from_bytes(data[ihdr_pos - 4 : ihdr_pos], byteorder="big") + 4
        target_crc = bytes(data[ihdr_pos + chunk_len : ihdr_pos + chunk_len + 4])

        # Pre-split IHDR for faster CRC calculation
        ihdr_type = bytes(data[ihdr_pos : ihdr_pos + 4])  # "IHDR"
        ihdr_tail = bytes(
            data[ihdr_pos + 12 : ihdr_pos + chunk_len]
        )  # Rest of IHDR data

        logs.append(f"Target CRC: 0x{target_crc.hex()}")

        # Precompute slices for faster reconstruction
        prefix = data[: ihdr_pos + 4]
        suffix = data[ihdr_pos + 12 :]

        # Pre-compute CRC base (just IHDR type)
        crc_base = zlib.crc32(ihdr_type) & 0xFFFFFFFF
        target_crc_int = int.from_bytes(target_crc, byteorder="big")

        # Brute-force dimensions with optimized CRC
        for width, height in generate_probable_sizes():
            # Incremental CRC: type -> width -> height -> tail
            w_bytes = width.to_bytes(4, byteorder="big")
            h_bytes = height.to_bytes(4, byteorder="big")

            crc = zlib.crc32(w_bytes, crc_base) & 0xFFFFFFFF
            crc = zlib.crc32(h_bytes, crc) & 0xFFFFFFFF
            crc = zlib.crc32(ihdr_tail, crc) & 0xFFFFFFFF

            if crc == target_crc_int:
                logs.append(f"Success: Match found! Dimensions: {width}x{height}")

                # Reconstruct and save PNG
                output_dir.mkdir(parents=True, exist_ok=True)
                img_name = f"recovered_{width}x{height}.png"
                output_path = output_dir / img_name

                recovered_data = prefix + w_bytes + h_bytes + suffix
                output_path.write_bytes(recovered_data)

                # Update results
                update_data(
                    output_dir,
                    {
                        "image_resize": {
                            "status": "ok",
                            "output": logs,
                            "image": f"/image/{output_dir.name}/{img_name}",
                        }
                    },
                )
                return

        # No match found
        logs.append("Failure: No matching dimensions found.")
        update_data(output_dir, {"image_resize": {"status": "ok", "output": logs}})

    except Exception as e:
        update_data(output_dir, {"image_resize": {"status": "error", "error": str(e)}})
