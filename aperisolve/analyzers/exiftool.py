"""Exiftool Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class ExiftoolAnalyzer(SubprocessAnalyzer):
    """Analyzer for exiftool."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the exiftool analyzer."""
        super().__init__("exiftool", input_img, output_dir)
        self.cmd = ["exiftool", "-a", "-u", "-g1", self.img]

    def process_output(self, stdout: str, stderr: str) -> dict[str, str]:
        """Process the stdout into a list of lines."""
        _ = stderr
        metadata: dict[str, str] = {}
        for line in stdout.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata


def analyze_exiftool(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using exiftool."""
    analyzer = ExiftoolAnalyzer(input_img, output_dir)
    analyzer.analyze()
