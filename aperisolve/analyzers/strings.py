"""Strings Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class StringsAnalyzer(SubprocessAnalyzer):
    """Analyzer for strings."""

    name = "strings"
    display_order = 160

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the strings analyzer."""
        super().__init__(input_img, output_dir)
        self.cmd = ["strings", self.img]


def analyze_strings(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using strings (deprecated: use ``execute``)."""
    StringsAnalyzer.execute(input_img, output_dir)
