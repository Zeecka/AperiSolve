"""Pngcheck Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class PngcheckAnalyzer(SubprocessAnalyzer):
    """Analyzer for pngcheck."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the pngcheck analyzer."""
        super().__init__("pngcheck", input_img, output_dir)
        self.cmd = ["pngcheck", "-v", self.img]

    def is_error(self, _returncode: int, stdout: str, _stderr: str, *, zip_exist: bool) -> bool:
        """Check whether the file is an unsupported format."""
        _ = zip_exist
        return "this is neither a PNG or JNG image nor a MNG stream" in stdout

    def process_error(self, stdout: str, _stderr: str) -> str:
        """Process the stderr."""
        if "this is neither a PNG or JNG image nor a MNG stream" in stdout:
            return "The file format of the file is not supported (PNG or JNG only)."
        return stdout


def analyze_pngcheck(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using pngcheck."""
    analyzer = PngcheckAnalyzer(input_img, output_dir)
    analyzer.analyze()
