"""Identify Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class IdentifyAnalyzer(SubprocessAnalyzer):
    """Analyzer for GraphicMagick identify command."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the identify analyzer."""
        super().__init__("identify", input_img, output_dir)
        self.cmd = ["identify", "-verbose", self.img]

    def process_output(self, stdout: str, _stderr: str) -> str | list[str]:
        """Process the stdout into a list of lines."""
        return [line for line in stdout.split("\n") if line.strip()]


def analyze_identify(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using GraphicMagick identify."""
    analyzer = IdentifyAnalyzer(input_img, output_dir)
    analyzer.analyze()
