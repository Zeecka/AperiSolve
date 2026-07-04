"""Identify Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class IdentifyAnalyzer(SubprocessAnalyzer):
    """Analyzer for GraphicMagick identify command."""

    name = "identify"
    display_order = 100

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the identify analyzer."""
        super().__init__(input_img, output_dir)
        self.cmd = ["identify", "-verbose", self.img]

    def process_output(self, stdout: str, stderr: str) -> str | list[str]:
        """Process the stdout into a list of lines."""
        _ = stderr
        return [line for line in stdout.split("\n") if line.strip()]
