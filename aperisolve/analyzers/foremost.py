# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Foremost Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from .base_analyzer import SubprocessAnalyzer


class ForemostAnalyzer(SubprocessAnalyzer):
    """Analyzer for foremost."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("foremost", input_img, output_dir, has_archive=True)
        self.cmd = ["foremost", "-o", str(self.get_extracted_dir()), "-i", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        return len(stderr) > 60

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout/stderr."""
        if "Processing" in stderr and "|*|" in stderr:
            return stderr.strip().split("\n")
        return []


def analyze_foremost(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using foremost."""
    analyzer = ForemostAnalyzer(input_img, output_dir)
    analyzer.analyze()
