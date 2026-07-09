"""Pdfinfo Analyzer for PDF submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class PdfinfoAnalyzer(SubprocessAnalyzer):
    """Analyzer for poppler's `pdfinfo` (PDF metadata)."""

    name = "pdfinfo"
    display_order = 35
    accepts = frozenset({"pdf"})

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the pdfinfo analyzer."""
        super().__init__(input_img, output_dir)
        self.cmd = ["pdfinfo", self.img]

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        """Process the stdout into a list of non-blank lines."""
        _ = stderr
        return [line for line in stdout.splitlines() if line.strip()]

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Flag an error only on a failed run that produced no metadata."""
        _ = stderr, zip_exist
        return returncode != 0 and not stdout.strip()
