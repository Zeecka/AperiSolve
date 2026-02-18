"""Strings Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class StringsAnalyzer(SubprocessAnalyzer):
    """Analyzer for strings."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the strings analyzer."""
        super().__init__("strings", input_img, output_dir)
        self.cmd = ["strings", self.img]


def analyze_strings(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using strings."""
    analyzer = StringsAnalyzer(input_img, output_dir)
    analyzer.analyze()
