"""Image size bruteforcer for common PNG sizes."""

from pathlib import Path
from typing import Any, List

from ..app import app
from ..models import IHDR
from .utils import PNG, update_data


def write_recovered_png(
    png_bytes: bytearray,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """
    Rebuilds a PNG by patching IHDR width/height and writes it to disk.
    """
    height_bytes = height.to_bytes(4, byteorder="big")
    width_bytes = width.to_bytes(4, byteorder="big")

    full_png_data = (
        png_bytes[:16]  # Splicing: [Start...IHDR+4] + [W] + [H] + [IHDR+12...End]
        + width_bytes
        + height_bytes
        + png_bytes[24:]
    )

    with output_path.open("wb") as out_f:
        out_f.write(full_png_data)


def lookup_crc(png: PNG) -> List[PNG]:
    """
    Look up PNG images in the database by their CRC value.

    Args:
        png (PNG): A PNG object containing the CRC value to search for.

    Returns:
        List[PNG]: A list of PNG objects with matching CRC values, reconstructed from their packed
                   representations.
    """
    with app.app_context():
        imgs = IHDR.query.filter_by(crc=png.crc).all()
        results = []
        for img in imgs:
            packed = img.packed
            results.append(PNG.from_packed(packed, crc=png.crc))
    return results


def search_height_crc(png: PNG) -> List[PNG]:
    """
    Search for PNG images with matching CRC by iterating through possible heights.

    This function attempts to find alternative PNG configurations that produce the same
    CRC checksum as the input PNG by systematically varying the height parameter while
    keeping all other properties constant.

    Args:
        png (PNG): The reference PNG object whose CRC checksum will be matched.

    Returns:
        List[PNG]: A list of PNG objects with matching CRC values. Returns an empty list
                   if no matches are found.

    Note:
        The function iterates through heights from 100 to 3500 (inclusive).
        This may be computationally expensive for large ranges.
    """
    results = []
    for height in range(100, 3501):
        candidate = PNG(
            size=(png.width, height),
            bit_depth=png.bit_depth,
            color_type=png.color_type,
            interlace=png.interlace,
        )
        if candidate.crc == png.crc:
            results.append(candidate)
    return results


def analyze_image_resize(input_img: Path, output_dir: Path) -> None:
    """
    Analyze a PNG image and recover resized versions based on CRC matching.

    This function attempts to find matching image dimensions for a given PNG file
    by looking up its CRC (Cyclic Redundancy Check) in a database. If matches are
    found, it recovers and saves PNG images with the matched dimensions.

    Args:
        input_img (Path): Path to the input PNG image file to analyze.
        output_dir (Path): Path to the directory where recovered PNG images will be saved.

    Returns:
        None

    Raises:
        Handles exceptions gracefully by updating output data with error status.

    Side Effects:
        - Creates output directory if it doesn't exist.
        - Saves recovered PNG images to the output directory.
        - Updates data in the output directory with analysis results via update_data().

    Notes:
        - If the PNG has invalid structure or IHDR chunk is not first, an error is logged.
        - The function performs a two-step lookup: first by CRC, then by height/CRC if no matches
          found.
        - Recovered images are named as "recovered_{width}x{height}.png".
        - Analysis results (logs, status, and image URLs) are persisted via update_data().
    """

    # 1. Setup Paths
    input_img = Path(input_img)
    output_dir = Path(output_dir)

    # 3. Initialize Logs
    logs = []

    try:
        with input_img.open("rb") as image:
            img_bytes = bytearray(image.read())
            try:
                png = PNG.from_bytearray(img_bytes)
            except ValueError:
                png = None

        if png is None:
            logs.append(
                "Failure: IHDR chunk is not the first chunk, or PNG has invalid structure."
            )
            update_data(
                output_dir,
                {
                    "image_resize": {
                        "status": "error",
                        "error": "IHDR chunk is not the first chunk, or PNG has invalid structure.",
                    }
                },
            )
            return

        logs.append(f"Target CRC found: 0x{png.crc:08x}")

        saved_img_urls = []

        db_matches = lookup_crc(png)
        if not db_matches:
            db_matches = search_height_crc(png)
        if not db_matches:
            logs.append("Failure: No matching dimensions found.")
        else:
            # Create parent directories if they don't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Iterate through ALL candidates found
            for im_match in db_matches:
                img_name = f"recovered_{im_match.width}x{im_match.height}.png"
                output_path = output_dir / img_name
                write_recovered_png(
                    img_bytes, im_match.width, im_match.height, output_path
                )

                logs.append(f"Image saved: {img_name}")
                # Append the formatted URL to our list
                saved_img_urls.append("/image/" + str(Path(output_dir.name) / img_name))

        # 4. Final Data Update
        output_data: dict[str, Any] = {
            "image_resize": {
                "status": "ok",
                "output": logs,
                "png_images": saved_img_urls,
            }
        }

        update_data(output_dir, output_data)

    except Exception as e:
        update_data(output_dir, {"image_resize": {"status": "error", "error": str(e)}})
