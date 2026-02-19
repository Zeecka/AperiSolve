"""Foremost Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer

FOREMOST_ERROR_THRESHOLD = 60


class ForemostAnalyzer(SubprocessAnalyzer):
    """Analyzer for foremost."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the foremost analyzer."""
        super().__init__("foremost", input_img, output_dir, has_archive=True)
        self.cmd = ["foremost", "-o", str(self.get_extracted_dir()), "-i", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        _ = stdout, returncode, zip_exist
        return len(stderr) > FOREMOST_ERROR_THRESHOLD

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout/stderr."""
        _ = stdout
        if "Processing" in stderr and "|*|" in stderr:
            return stderr.strip().replace("\n", "")
        return []


def analyze_foremost(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using foremost."""
    analyzer = ForemostAnalyzer(input_img, output_dir)
    analyzer.analyze()
