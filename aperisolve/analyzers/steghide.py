"""Steghide Analyzer for Image Submissions."""

import re
from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class SteghideAnalyzer(SubprocessAnalyzer):
    """Analyzer for steghide."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the steghide analyzer."""
        super().__init__("steghide", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the steghide command for info or extraction."""
        if password is None:
            password = ""

        # First, get the embedded file name, and return the test cmd if failed
        cmd_test = ["steghide", "info", self.img, "-p", password]
        data = self.run_command(cmd_test, cwd=self.output_dir)
        err = self.is_error(data.returncode, data.stdout, data.stderr, zip_exist=False)
        if err:
            return cmd_test

        match = re.search(r'embedded file "([^"]+)"', data.stdout)
        if match is None:
            return cmd_test
        hidden_file = match.group(1)
        safe_hidden_file = Path(hidden_file).name
        outfile = str(self.get_extracted_dir() / safe_hidden_file)
        return ["steghide", "extract", "-sf", self.img, "-xf", outfile, "-p", password]

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        _ = returncode, zip_exist
        match = re.search(r'embedded file "([^"]+)".*', stdout + stderr)
        embedded_filename = match.group(1) if match else None

        match = re.search(r'wrote extracted data to "([^"]+)".*', stdout + stderr)
        extracted_filename = match.group(1) if match else None

        # if bad file format or wrong password, raise an error
        return embedded_filename is None and extracted_filename is None

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout into a list of lines."""
        _ = stdout
        return [line for line in stderr.split("\n") if "wrote extracted data to" in line]

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process stderr."""
        _ = stdout
        if "the file format of the file" in stderr and "not supported" in stderr:
            return "The file format of the file is not supported (JPEG or BMP only)."
        return stderr


def analyze_steghide(input_img: Path, output_dir: Path, password: str | None = None) -> None:
    """Analyze an image submission using steghide."""
    analyzer = SteghideAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
