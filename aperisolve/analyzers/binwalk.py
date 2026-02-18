"""Binwalk Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class BinwalkAnalyzer(SubprocessAnalyzer):
    """Analyzer for binwalk."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the binwalk analyzer."""
        super().__init__("binwalk", input_img, output_dir, has_archive=True)
        self.cmd = ["binwalk", "--matryoshka", "-e", self.img, "--run-as=root"]
        self.make_folder = False  # Binwalk already create its own folder

    def get_extracted_dir(self) -> Path:
        """Return the binwalk extraction directory."""
        return self.output_dir / f"_{self.input_img.name}.extracted"

    def is_error(self, _returncode: int, _stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check whether binwalk execution failed."""
        return len(stderr) > 0 and not zip_exist


def analyze_binwalk(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using binwalk."""
    analyzer = BinwalkAnalyzer(input_img, output_dir)
    analyzer.analyze()
