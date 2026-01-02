# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Pngcheck Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from .base_analyzer import SubprocessAnalyzer


class PngcheckAnalyzer(SubprocessAnalyzer):
    """Analyzer for pngcheck."""

    def __init__(self, *args: Any) -> None:
        super().__init__("pngcheck", *args)
        self.cmd = ["pngcheck", "-v", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        return "this is neither a PNG or JNG image nor a MNG stream" in stdout

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        if "this is neither a PNG or JNG image nor a MNG stream" in stdout:
            return "The file format of the file is not supported (PNG or JNG only)."
        return stdout


def analyze_pngcheck(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using pngcheck."""
    analyzer = PngcheckAnalyzer(input_img, output_dir)
    analyzer.analyze()
