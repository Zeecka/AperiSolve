# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Strings Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from .base_analyzer import SubprocessAnalyzer


class StringsAnalyzer(SubprocessAnalyzer):
    """Analyzer for strings."""

    def __init__(self, input_img, output_dir: Any) -> None:
        super().__init__("strings", input_img, output_dir)
        self.cmd = ["strings", self.img]


def analyze_strings(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using strings."""
    analyzer = StringsAnalyzer(input_img, output_dir)
    analyzer.analyze()
