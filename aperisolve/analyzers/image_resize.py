"""Image size bruteforcer for common PNG sizes."""

import zlib
import sqlite3
from pathlib import Path
from typing import List
from .utils import update_data, unpack_ihdr
from ..app import app
from ..models import IHDR


def write_recovered_png(
    png_bytes: bytearray,
    ihdr_offset: int,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """
    Rebuilds a PNG by patching IHDR width/height and writes it to disk.
    """
    # TODO, use depth/color later if needed
    height_bytes = height.to_bytes(4, byteorder="big")
    width_bytes = width.to_bytes(4, byteorder="big")

    # Splicing: [Start...IHDR+4] + [W] + [H] + [IHDR+12...End]
    full_png_data = (
        png_bytes[: ihdr_offset + 4]
        + width_bytes
        + height_bytes
        + png_bytes[ihdr_offset + 12 :]
    )

    with output_path.open("wb") as out_f:
        out_f.write(full_png_data)


def lookup_crc(crc_bytes: bytes) -> List[tuple[int, int, int, int, int]]:
    """
    Queries the SQLite DB for the CRC and returns a list of (width, height) tuples.
    """
    with app.app_context():
        crc_b = int.from_bytes(crc_bytes, byteorder="big")
        imgs = IHDR.query.filter_by(crc=crc_b).all()
        results = []
        for img in imgs:
            packed = img.packed
            results.append(unpack_ihdr(packed))
    return results


def analyze_image_resize(input_img: Path, output_dir: Path) -> None:
    """
    Analyze an image submission using python-based resize bruteforce.
    Strategy: Check common sizes first, then fall back to DB lookup.
    """

    # 1. Setup Paths
    input_img = Path(input_img)
    output_dir = Path(output_dir)

    # 3. Initialize Logs
    logs = []

    try:
        with input_img.open("rb") as image:
            f = image.read()

        b = bytearray(f)

        # Find IHDR start
        ihdr = b.find(b"\x49\x48\x44\x52")
        if ihdr == -1:
            logs.append("Failure: PNG header (IHDR) not found.")
            update_data(
                output_dir,
                {"image_resize": {"status": "error", "error": "PNG header not found."}},
            )
            return

        # Calculate Chunk Length (The 4 bytes BEFORE IHDR tag)
        chunk_length = int.from_bytes((b[ihdr - 4 : ihdr]), byteorder="big") + 4

        # Extract Target CRC (The 4 bytes AFTER the chunk data)
        target_crc = b[ihdr + chunk_length : ihdr + chunk_length + 4]

        logs.append(f"Target CRC found: 0x{target_crc.hex()}")

        saved_img_urls = []

        db_matches = lookup_crc(target_crc)
        if db_matches:
            # Create parent directories if they don't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Iterate through ALL candidates found
            for elt in db_matches:
                w, h, _, _, _ = elt  # TODO, use depth/color later if needed
                img_name = f"recovered_{w}x{h}.png"
                output_path = output_dir / img_name
                write_recovered_png(b, ihdr, w, h, output_path)

                logs.append(f"Image saved: {img_name}")

                # Append the formatted URL to our list
                saved_img_urls.append("/image/" + str(Path(output_dir.name) / img_name))
        else:
            logs.append("Failure: No matching dimensions found in List or DB.")

        # 4. Final Data Update
        output_data = {
            "image_resize": {
                "status": "ok",
                "output": logs,
                "png_images": saved_img_urls,
            }
        }

        update_data(output_dir, output_data)

    except Exception as e:
        update_data(output_dir, {"image_resize": {"status": "error", "error": str(e)}})
