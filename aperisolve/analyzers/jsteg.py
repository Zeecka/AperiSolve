# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Jsteg Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class JstegAnalyzer(SubprocessAnalyzer):
    """Analyzer for jsteg."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("jsteg", input_img, output_dir)
        self.cmd = ["jsteg", "reveal", self.img]

    def process_output(self, stdout: str, stderr: str) -> str | list[str]:
        """Process the stdout into lines."""
        if stdout.strip():
            return [line for line in stdout.split("\n") if line.strip()]
        return []


def analyze_jsteg(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using jsteg."""
    analyzer = JstegAnalyzer(input_img, output_dir)
    analyzer.analyze()
