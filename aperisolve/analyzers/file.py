"""File Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class FileAnalyzer(SubprocessAnalyzer):
    """Analyzer for the `file` command."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the file analyzer."""
        super().__init__("file", input_img, output_dir)
        self.cmd = ["file", "-b", self.img]

    def process_output(self, stdout: str, _stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout into a list of lines."""
        return stdout


def analyze_file(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using `file`."""
    analyzer = FileAnalyzer(input_img, output_dir)
    analyzer.analyze()
