# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""OpenStego Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any, Optional

from .base_analyzer import SubprocessAnalyzer


class OpenStegoAnalyzer(SubprocessAnalyzer):
    """Analyzer for openstego."""

    def __init__(self, *args):
        super().__init__("openstego", *args, has_archive=True)
        self.algo = 0

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        """Iterator that return command for OpenStego for every algorithms"""
        if password is None:
            password = ""

        algorithms = ["AES128", "AES256"]
        algo = algorithms[self.algo]
        self.algo += 1
        cmd = ["openstego", "extract", "-a", "randomlsb", "--cryptalgo", algo, "-sf"]
        cmd += [self.img, "-xd", str(self.get_extracted_dir()), "-p", password]
        return cmd

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        return (
            len(list(self.get_extracted_dir().glob("*"))) == 0 and "Extracted file: " not in stderr
        )

    def analyze(self, password: Optional[str] = None) -> None:
        """Run the subprocess command and handle results."""
        result: dict[str, Any]
        try:
            result = self.get_results(password)
            if result["status"] == "error":  # check second algorithm if failed
                result = self.get_results(password)
            self.update_result(result)
        except Exception as e:
            self.update_result({"status": "error", "error": str(e)})

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout/stderr."""
        return stderr

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process the stderr."""
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
