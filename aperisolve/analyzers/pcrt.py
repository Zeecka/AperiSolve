"""PCRT (PNG Check & Repair Tool) Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from aperisolve.utils.png import PNG

from .base_analyzer import SubprocessAnalyzer


class PCRTAnalyzer(SubprocessAnalyzer):
    """Analyzer for PCRT (PNG Check & Repair Tool)."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the PCRT analyzer."""
        super().__init__("pcrt", input_img, output_dir, has_archive=True)

    def _write_repaired_data(self, data: bytes) -> str:
        """Write recovered image."""
        img_name = f"pcrt_recovered_{self.input_img.stem}.png"
        output_path = self.output_dir / img_name
        saved_img_url = "/image/" + str(Path(self.output_dir.name) / img_name)
        with output_path.open("wb") as f:
            f.write(data)
        return saved_img_url

    def _write_extra_data(self, data: bytes) -> None:
        """Write recovered extra data."""
        extracted_dir = self.get_extracted_dir()
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extra_path = extracted_dir / "extra_data.bin"
        with extra_path.open("wb") as f:
            f.write(data)

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Analyze PNG and attempt repairs."""
        _ = password
        try:
            with self.input_img.open("rb") as f:
                data = f.read()

            png = PNG(data)
            fixed, extra_data = png.repair()

            result: dict[str, Any] = {}

            if png.errors:
                result["status"] = "error"
                result["error"] = "\n".join(png.errors)
                if png.logs:
                    result["output"] = png.logs
                return result

            result["status"] = "ok"
            result["output"] = png.logs or ["PNG appears valid, no repairs needed"]

            # Save repaired PNG if any fixes were made
            if fixed and png.repaired_data:
                url = self._write_repaired_data(bytes(png.repaired_data))
                result["note"] = "PNG was repaired and saved"
                result["png_images"] = [url]

            # Save extra data if found after IEND
            if extra_data:
                self._write_extra_data(extra_data)
                self.generate_archive(self.output_dir)
                result["note"] = result.get("note", "") + " | Extra data found after IEND"
                result["download"] = f"/download/{self.output_dir.name}/{self.name}"

        except (ValueError, OSError, RuntimeError, TypeError) as e:
            return {"status": "error", "error": f"Analysis failed: {e!s}"}
        else:
            return result


def analyze_pcrt(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using PCRT."""
    analyzer = PCRTAnalyzer(input_img, output_dir)
    analyzer.analyze()
