# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Strings Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from .base_analyzer import SubprocessAnalyzer


class ZstegAnalyzer(SubprocessAnalyzer):
    """Analyzer for zsteg."""

    def __init__(self, *args: Any) -> None:
        super().__init__("zsteg", *args)
        self.cmd = ["zsteg", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        return bool(stderr) or "PNG::NotSupported" in stdout[:100]

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        if "PNG::NotSupported" in stdout[:100]:
            return "The file format of the file is not supported (PNG only)."
        return stderr


def analyze_zsteg(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using zsteg."""
    analyzer = ZstegAnalyzer(input_img, output_dir)
    analyzer.analyze()
