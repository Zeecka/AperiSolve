# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Steghide Analyzer for Image Submissions."""

import re
from pathlib import Path
from typing import Optional

from .base_analyzer import SubprocessAnalyzer


class SteghideAnalyzer(SubprocessAnalyzer):
    """Analyzer for steghide."""

    def __init__(self, *args):
        super().__init__("steghide", *args, has_archive=True)

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        if password is None:
            password = ""

        # First, get the embedded file name, and return the test cmd if failed
        cmd_test = ["steghide", "info", self.img, "-p", password]
        data = self.run_command(cmd_test, cwd=self.output_dir)
        err = self.is_error(data.returncode, data.stdout, data.stderr, False)
        if err:
            return cmd_test

        match = re.search(r'embedded file "([^"]+)"', data.stdout)
        assert match is not None
        hidden = match.group(1)
        cmd = ["steghide", "extract", "-sf", self.img, "-xf", hidden, "-p", password]
        return cmd

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        """Check if the result is an error."""

        match = re.search(r'embedded file "([^"]+)"', stdout)
        embedded_filename = match.group(1) if match else None

        # if bad file format or wrong password, raise an error
        return returncode != 0 or embedded_filename is None

    def process_output(self, stdout: str, stderr: str) -> str | list[str] | dict[str, str]:
        """Process the stdout into a list of lines."""
        out = []
        for line in stderr.split("\n"):
            if line.startswith('wrote extracted data to "'):
                out.append(line)
        return out

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process stderr."""
        if "the file format of the file" in stderr and "not supported" in stderr:
            return "The file format of the file is not supported (JPEG or BMP only)."
        out = ""
        for line in stderr.split("\n"):
            if line and not line.startswith('wrote extracted data to "'):
                out += line + "\n"
        return out


def analyze_steghide(input_img: Path, output_dir: Path, password: Optional[str] = None) -> None:
    """Analyze an image submission using steghide."""
    analyzer = SteghideAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
