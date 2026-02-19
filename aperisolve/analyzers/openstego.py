"""OpenStego Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any

from .base_analyzer import SubprocessAnalyzer


class OpenStegoAnalyzer(SubprocessAnalyzer):
    """Analyzer for openstego."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the OpenStego analyzer."""
        super().__init__("openstego", input_img, output_dir, has_archive=True)
        self.algo = 0

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Return an OpenStego extraction command for the current algorithm."""
        if password is None:
            password = ""

        algorithms = ["AES128", "AES256"]
        algo = algorithms[self.algo]
        self.algo += 1
        cmd = ["openstego", "extract", "-a", "randomlsb", "--cryptalgo", algo, "-sf"]
        cmd += [self.img, "-xd", str(self.get_extracted_dir()), "-p", password]
        return cmd

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        _ = returncode, stdout
        return not zip_exist and "Extracted file: " not in stderr

    def analyze(self, password: str | None = None) -> None:
        """Run the subprocess command and handle results."""
        result: dict[str, Any]
        try:
            result = self.get_results(password)
            if result["status"] == "error":  # check second algorithm if failed
                result = self.get_results(password)
            self.update_result(result)
        except (RuntimeError, ValueError, OSError, TimeoutError) as e:
            self.update_result({"status": "error", "error": str(e)})
            raise

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout/stderr."""
        _ = stdout
        return stderr

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
        _ = stdout
        if "OpenStego is a steganography application" in stderr:
            return "OpenStego needs a password to work."
        return stderr


def analyze_openstego(input_img: Path, output_dir: Path, password: str = "") -> None:
    """Analyze an image submission using openstego."""
    analyzer = OpenStegoAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
