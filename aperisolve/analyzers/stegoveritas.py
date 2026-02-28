"""StegoVeritas Analyzer for Image / GIF Submissions."""

import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from aperisolve.config import IMAGE_EXTENSIONS

from .base_analyzer import SubprocessAnalyzer

# Regex patterns for classifying stegoveritas output filenames.
_BIT_PLANE_RE = re.compile(r"_(Red|Green|Blue|Alpha)_(\d+)\.\w+$")
_FRAME_RE = re.compile(r"^frame_\d+\.\w+$")

# Preferred display order for image groups.
_GROUP_ORDER = ("Red", "Green", "Blue", "Alpha", "Transforms", "Frames")


class StegoveritasAnalyzer(SubprocessAnalyzer):
    """Analyzer for StegoVeritas."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the stegoveritas analyzer."""
        super().__init__("stegoveritas", input_img, output_dir, has_archive=True)
        self._prepare_input()
        self.cmd = ["stegoveritas", "-imageTransform", "-extract_frames", self.img]
        self.make_folder = False  # stegoveritas creates the output folder

    def get_extracted_dir(self) -> Path:
        """Return the stegoveritas extraction directory."""
        return self.output_dir / "results"

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        """Suppress console output; images are displayed via grouped images."""
        _ = stdout, stderr
        return []

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Run stegoveritas and return grouped image results."""
        extracted_dir = self.get_extracted_dir()
        cmd = list(map(str, self.build_cmd(password)))
        data = self.run_command(cmd, cwd=self.output_dir)

        grouped_urls: dict[str, list[str]] = {}
        if extracted_dir.exists():
            grouped = self._group_images(self._collect_images(extracted_dir))
            grouped_urls = self._copy_grouped_images(grouped)

        zip_exist = False
        if extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(self.output_dir, extracted_dir)
            zip_exist = True

        if self.is_error(data.returncode, data.stdout, data.stderr, zip_exist=zip_exist):
            return {
                "status": "error",
                "error": self.process_error(data.stdout, data.stderr),
            }

        result: dict[str, Any] = {
            "status": "ok",
            "output": self.process_output(data.stdout, data.stderr),
        }
        if grouped_urls:
            result["images"] = grouped_urls
        if zip_exist:
            result["download"] = f"/download/{self.output_dir.name}/{self.name}"
        return result

    # ------------------------------------------------------------------
    # Input preparation
    # ------------------------------------------------------------------

    def _prepare_input(self) -> None:
        """Convert input to RGB if needed for stegoveritas filters.

        Animated GIFs are left untouched so ``-extract_frames`` can work.
        """
        try:
            with Image.open(self.input_img) as img:
                if img.format == "GIF" and getattr(img, "is_animated", False):
                    return
                if img.mode in {"RGBA", "LA", "P"}:
                    converted = img.convert("RGB")
                    converted_path = self.output_dir / f"{self.input_img.stem}_stegoveritas_rgb.png"
                    converted.save(converted_path)
                    self.img = converted_path.name
        except Exception:  # noqa: BLE001, S110
            pass  # Fall back to the original input if conversion fails.

    # ------------------------------------------------------------------
    # Image collection & grouping
    # ------------------------------------------------------------------

    def _collect_images(self, extracted_dir: Path) -> list[Path]:
        """Gather all image files from *extracted_dir* recursively."""
        allowed = {ext.lower() for ext in IMAGE_EXTENSIONS}
        return sorted(
            (
                path
                for path in extracted_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in allowed
            ),
            key=lambda p: p.name,
        )

    @staticmethod
    def _classify_image(filename: str) -> tuple[str, int]:
        """Return ``(group_name, sort_key)`` for an image filename.

        Bit-plane images (e.g. ``…_Red_3.png``) are grouped by channel.
        Extracted GIF frames (``frame_N.png``) go into *Frames*.
        Everything else lands in *Transforms*.
        """
        match = _BIT_PLANE_RE.search(filename)
        if match:
            return match.group(1), int(match.group(2))

        if _FRAME_RE.match(filename):
            num_match = re.search(r"(\d+)", filename)
            return "Frames", int(num_match.group(1)) if num_match else 0

        return "Transforms", 0

    def _group_images(self, image_paths: list[Path]) -> dict[str, list[Path]]:
        """Categorise images into named groups ordered for display."""
        buckets: dict[str, list[tuple[int, Path]]] = {}
        for path in image_paths:
            group, sort_key = self._classify_image(path.name)
            buckets.setdefault(group, []).append((sort_key, path))

        # Sort items within each bucket, then honour _GROUP_ORDER.
        ordered: dict[str, list[Path]] = {}
        for group in _GROUP_ORDER:
            if group in buckets:
                ordered[group] = [p for _, p in sorted(buckets.pop(group))]
        # Append any remaining groups alphabetically.
        for group in sorted(buckets):
            ordered[group] = [p for _, p in sorted(buckets[group])]
        return ordered

    # ------------------------------------------------------------------
    # Copying & URL generation
    # ------------------------------------------------------------------

    def _copy_grouped_images(
        self,
        grouped: dict[str, list[Path]],
    ) -> dict[str, list[str]]:
        """Copy images to *output_dir* and return ``{group: [url, …]}``."""
        result: dict[str, list[str]] = {}
        used_names: set[str] = set()

        for group, paths in grouped.items():
            urls: list[str] = []
            for image_path in paths:
                dest_name = self._unique_dest_name(image_path, used_names)
                used_names.add(dest_name)
                shutil.copy2(image_path, self.output_dir / dest_name)
                dl_path = Path(self.output_dir.name) / dest_name
                urls.append("/image/" + str(dl_path))
            if urls:
                result[group] = urls
        return result

    def _unique_dest_name(self, image_path: Path, used: set[str]) -> str:
        """Generate a unique destination filename inside the output dir."""
        base_name = f"{self.name}_{image_path.name}"
        dest_name = base_name
        counter = 1
        while dest_name in used or (self.output_dir / dest_name).exists():
            dest_name = f"{self.name}_{image_path.stem}_{counter}{image_path.suffix}"
            counter += 1
        return dest_name


def analyze_stegoveritas(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using stegoveritas."""
    analyzer = StegoveritasAnalyzer(input_img, output_dir)
    analyzer.analyze()
