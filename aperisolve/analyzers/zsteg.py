"""Zsteg Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class ZstegAnalyzer(SubprocessAnalyzer):
    """Analyzer for zsteg."""

    name = "zsteg"
    display_order = 150
    accepts = frozenset({"png"})

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the zsteg analyzer."""
        super().__init__(input_img, output_dir)
        self.cmd = ["zsteg", self.img]

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check whether zsteg reported an error."""
        _ = returncode, zip_exist
        return bool(stderr) or "PNG::NotSupported" in stdout[:100]

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        if "PNG::NotSupported" in stdout[:100]:
            return "The file format of the file is not supported (PNG only)."
        return stderr
