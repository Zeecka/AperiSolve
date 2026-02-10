# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""StegoVeritas Analyzer for Image / GIFs Submissions."""

import shutil
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from ..config import IMAGE_EXTENSIONS
from .base_analyzer import SubprocessAnalyzer

class StegoveritasAnalyzer(SubprocessAnalyzer):
    """Analyzer for StegoVeritas."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("stegoveritas", input_img, output_dir, has_archive=True)
        self._prepare_input()
        self.cmd = ["stegoveritas", "-imageTransform", "-extract_frames", self.img]
        self.make_folder = False  # stegoveritas creates the output folder

    def get_extracted_dir(self) -> Path:
        return self.output_dir / "results"

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        return []

    def get_results(self, password: Optional[str] = None) -> dict[str, Any]:
        extracted_dir = self.get_extracted_dir()
        cmd = list(map(str, self.build_cmd(password)))
        data = self.run_command(cmd, cwd=self.output_dir)

        image_urls: list[str] = []
        if extracted_dir.exists():
            image_urls = self._copy_images(self._collect_images(extracted_dir))

        zip_exist = False
        if extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(self.output_dir, extracted_dir)
            zip_exist = True

        if self.is_error(data.returncode, data.stdout, data.stderr, zip_exist):
            return {
                "status": "error",
                "error": self.process_error(data.stdout, data.stderr),
            }

        result: dict[str, Any] = {
            "status": "ok",
            "output": self.process_output(data.stdout, data.stderr),
        }
        if image_urls:
            result["images"] = {"Stegoveritas": image_urls}
        if zip_exist:
            result["download"] = f"/download/{self.output_dir.name}/{self.name}"
        return result

    def _prepare_input(self) -> None:
        """Convert input to RGB if needed for stegoveritas filters."""
        try:
            with Image.open(self.input_img) as img:
                if img.format == "GIF" and getattr(img, "is_animated", False):
                    # Keep the original to preserve frames for -extract_frames
                    return
                if img.mode in {"RGBA", "LA", "P"}:
                    converted = img.convert("RGB")
                    converted_path = self.output_dir / f"{self.input_img.stem}_stegoveritas_rgb.png"
                    converted.save(converted_path)
                    self.img = converted_path.name
        except Exception:
            # Fall back to the original input if conversion fails
            pass

    def _collect_images(self, extracted_dir: Path) -> list[Path]:
        allowed = {ext.lower() for ext in IMAGE_EXTENSIONS}
        return sorted(
            [
                path
                for path in extracted_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in allowed
            ],
            key=lambda p: p.name,
        )

    def _copy_images(self, image_paths: list[Path]) -> list[str]:
        urls: list[str] = []
        used_names: set[str] = set()

        for image_path in image_paths:
            base_name = f"{self.name}_{image_path.name}"
            dest_name = base_name
            counter = 1
            while dest_name in used_names or (self.output_dir / dest_name).exists():
                dest_name = f"{self.name}_{image_path.stem}_{counter}{image_path.suffix}"
                counter += 1

            used_names.add(dest_name)
            dest_path = self.output_dir / dest_name
            shutil.copy2(image_path, dest_path)
            dl_path = Path(self.output_dir.name) / dest_path.name
            urls.append("/image/" + str(dl_path))

        return urls

def analyze_stegoveritas(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using stegoveritas."""
    analyzer = StegoveritasAnalyzer(input_img, output_dir)
    analyzer.analyze()
