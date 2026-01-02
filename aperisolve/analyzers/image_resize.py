# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Image size bruteforcer for common PNG sizes."""

from pathlib import Path
from typing import Any, List

from ..app import app
from ..models import IHDR
from .base_analyzer import SubprocessAnalyzer
from .utils import PNG


class ResizeAnalyzer(SubprocessAnalyzer):
    """Analyzer for image resize."""

    png: PNG

    def __init__(self, *args):
        super().__init__("image_resize", *args, has_archive=True)

    def _lookup_crc(self) -> List[PNG]:
        """
        Look up PNG images in the database by their CRC value.

        Returns:
            List[PNG]: A list of PNG objects with matching CRC values, reconstructed from their
                       packed representations.
        """
        with app.app_context():
            imgs = IHDR.query.filter_by(crc=self.png.crc).all()
            results = []
            for img in imgs:
                packed = img.packed
                results.append(PNG.from_packed(packed, crc=self.png.crc))
        return results

    def _search_height_crc(self) -> List[PNG]:
        """
        Search for PNG images with matching CRC by iterating through possible heights.

        This function attempts to find alternative PNG configurations that produce the same
        CRC checksum as the input PNG by systematically varying the height parameter while
        keeping all other properties constant.

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
                size=(self.png.width, height),
                bit_depth=self.png.bit_depth,
                color_type=self.png.color_type,
                interlace=self.png.interlace,
            )
            if candidate.crc == self.png.crc:
                results.append(candidate)
        return results

    def _write_recovered_png(self, png_bytes: bytearray, png_match: PNG) -> str:
        """
        Rebuilds a PNG by patching IHDR width/height and writes it to disk.
        """

        img_name = f"recovered_{png_match.width}x{png_match.height}.png"
        output_path = self.output_dir / img_name

        height_bytes = png_match.height.to_bytes(4, byteorder="big")
        width_bytes = png_match.width.to_bytes(4, byteorder="big")

        full_png_data = (
            png_bytes[:16]  # Splicing: [Start...IHDR+4] + [W] + [H] + [IHDR+12...End]
            + width_bytes
            + height_bytes
            + png_bytes[24:]
        )

        with output_path.open("wb") as out_f:
            out_f.write(full_png_data)

        return img_name

    def get_results(self, _: Optional[str] = None) -> dict[str, Any]:
        """
        Analyze a PNG image and recover resized versions based on CRC matching.

        This function attempts to find matching image dimensions for a given PNG file
        by looking up its CRC (Cyclic Redundancy Check) in a database. If matches are
        found, it recovers and saves PNG images with the matched dimensions.

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
            - The function performs a two-step lookup: first by CRC, then by height/CRC if no
              matches found.
            - Recovered images are named as "recovered_{width}x{height}.png".
            - Analysis results (logs, status, and image URLs) are persisted via update_data().
        """
        logs = []

        try:
            with self.input_img.open("rb") as image:
                img_bytes = bytearray(image.read())
                try:
                    self.png = PNG.from_bytearray(img_bytes)
                except ValueError:
                    return {
                        "status": "error",
                        "error": "IHDR chunk is not the first chunk, or PNG has invalid structure.",
                    }

            # Already correct
            if self.png.crc == self.png.compute_crc():
                return {
                    "status": "ok",
                    "note": f"PNG is already valid with dimensions "
                    f"{self.png.width}x{self.png.height} and crc 0x{self.png.crc:08x}.",
                }

            saved_img_urls = []

            # No match found
            if not (db_matches := self._lookup_crc()) and not (
                db_matches := self._search_height_crc()
            ):
                return {
                    "status": "error",
                    "error": "Failure: No matching dimensions found.",
                }

            # Match found, saving image(s)
            logs.append(f"Target CRC found: 0x{self.png.crc:08x}")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            for png_match in db_matches:
                img_name = self._write_recovered_png(img_bytes, png_match)
                logs.append(f"Image saved: {img_name}")
                # Append the formatted URL to our list
                saved_img_urls.append("/image/" + str(Path(self.output_dir.name) / img_name))

            return {
                "status": "ok",
                "output": logs,
                "png_images": saved_img_urls,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


def analyze_image_resize(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using outguess."""
    analyzer = ResizeAnalyzer(input_img, output_dir)
    analyzer.analyze()
