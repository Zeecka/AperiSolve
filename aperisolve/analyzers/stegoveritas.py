"""Partial StegoVeritas: image transforms (deep only) and animated-GIF/APNG frames.

StegoVeritas' CLI is not used: it would redo the bit planes (Decomposer's job)
in an unbounded process pool, and brute-LSB, carving, steghide and exif (other
analyzers' jobs). ``docker/stegoveritas_driver.py`` calls its per-operation
functions one by one, in one process, from an isolated venv (see Dockerfile).
"""

import json
from pathlib import Path
from typing import Any, ClassVar, cast

from .base_analyzer import SubprocessAnalyzer, python_subprocess_error
from .pil_utils import MAX_IMAGE_PIXELS, PALETTE_NOTE

# Absolute paths into the isolated venv (see Dockerfile), never on PATH so its
# pip-pulled `binwalk` cannot shadow the apt binary of the binwalk analyzer.
VENV_PYTHON = Path("/opt/stegoveritas-venv/bin/python")
DRIVER = Path("/opt/stegoveritas/driver.py")

# Each frame is written at full size, so the count is capped before extraction.
MAX_FRAMES = 100


class _DriverAnalyzer(SubprocessAnalyzer):
    """Runs one mode of the StegoVeritas driver and turns its JSON into a result."""

    register = False
    driver_mode: ClassVar[str]
    make_folder = False  # the driver creates the folder it archives

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Driver command line; ``-I`` keeps the submission folder (cwd) off ``sys.path``."""
        _ = password
        return [
            str(VENV_PYTHON),
            "-I",
            str(DRIVER),
            self.driver_mode,
            str(self.input_img),
            str(self.output_dir),
            str(MAX_IMAGE_PIXELS),
            *self.extra_args(),
        ]

    def extra_args(self) -> list[str]:
        """Mode-specific trailing driver arguments."""
        return []

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Run the driver and map the image names it prints to ``/image/`` URLs."""
        _ = password
        if not VENV_PYTHON.exists() or not DRIVER.exists():
            return {"status": "error", "error": "stegoveritas is not installed"}
        data = self.run_command(self.build_cmd(), cwd=self.output_dir)
        if data.returncode != 0:
            return {
                "status": "error",
                "error": python_subprocess_error(data.stderr, "stegoveritas failed"),
            }
        try:
            parsed = cast("dict[str, Any]", json.loads(data.stdout))
        except json.JSONDecodeError:
            return {"status": "error", "error": "stegoveritas produced invalid output"}
        if parsed.get("status") != "ok":
            return {"status": "error", "error": str(parsed.get("error", "stegoveritas failed"))}

        folder = self.output_dir.name
        images = {
            group: [f"/image/{folder}/{name}" for name in names]
            for group, names in parsed.get("images", {}).items()
            if names
        }
        result: dict[str, Any] = {"status": "ok", "output": []}
        if images:
            result["images"] = images
        else:
            result["output"] = ["No output."]
        notes = [PALETTE_NOTE] if parsed.get("palette") else []
        if parsed.get("skipped"):
            notes.append(f"Not supported for this image mode: {', '.join(parsed['skipped'])}.")
        if notes:
            result["note"] = " ".join(notes)
        extracted_dir = self.get_extracted_dir()
        if self.has_archive and extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(extracted_dir)
            result["download"] = f"/download/{folder}/{self.name}"
        return result


class StegoveritasAnalyzer(_DriverAnalyzer):
    """Filters, colour planes, sharpness and ImageOps variants; deep analysis only."""

    name = "stegoveritas"
    register = True  # ``register = False`` on the base is inherited otherwise
    display_order = 25
    deep_only = True
    accepts = frozenset({"image"})
    driver_mode = "transforms"


class StegoveritasFramesAnalyzer(_DriverAnalyzer):
    """Every frame of an animated GIF or APNG, as images and as a 7z."""

    name = "stegoveritas_frames"
    register = True
    display_order = 26
    has_archive = True
    accepts = frozenset({"animated"})
    driver_mode = "frames"

    def extra_args(self) -> list[str]:
        """Frame cap: StegoVeritas' extraction loop cannot be bounded from outside."""
        return [str(MAX_FRAMES)]
