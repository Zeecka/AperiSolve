"""Jsteg Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class JstegAnalyzer(SubprocessAnalyzer):
    """Analyzer for jsteg."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the jsteg analyzer."""
        super().__init__("jsteg", input_img, output_dir)
        self.cmd = ["jsteg", "reveal", self.img]

    def process_output(self, stdout: str, stderr: str) -> str | list[str]:
        """Process the stdout into lines."""
        _ = stderr
        if stdout.strip():
            return [line for line in stdout.split("\n") if line.strip()]
        return []


def analyze_jsteg(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using jsteg."""
    analyzer = JstegAnalyzer(input_img, output_dir)
    analyzer.analyze()
