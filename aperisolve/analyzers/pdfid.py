"""Pdfid Analyzer for PDF submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class PdfidAnalyzer(SubprocessAnalyzer):
    """Analyzer for Didier Stevens' `pdfid` (suspicious-object triage).

    Surfaces the counts of risky PDF objects (``/JS``, ``/JavaScript``,
    ``/OpenAction``, ``/Launch``, ``/EmbeddedFile``, ...). If the binary is
    absent the subprocess launch fails and the base class records a clean error
    result rather than crashing the worker.
    """

    name = "pdfid"
    display_order = 36
    accepts = frozenset({"pdf"})

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the pdfid analyzer."""
        super().__init__(input_img, output_dir)
        self.cmd = ["pdfid", self.img]

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        """Process the stdout into a list of non-blank lines."""
        _ = stderr
        return [line for line in stdout.splitlines() if line.strip()]

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Flag an error only on a failed run that produced no output."""
        _ = stderr, zip_exist
        return returncode != 0 and not stdout.strip()
