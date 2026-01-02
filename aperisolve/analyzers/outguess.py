# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Outguess Analyzer for Image Submissions."""

from pathlib import Path
from typing import Any, Optional

from .base_analyzer import SubprocessAnalyzer


class OutguessAnalyzer(SubprocessAnalyzer):
    """Analyzer for outguess."""

    def __init__(self, *args: Any) -> None:
        super().__init__("outguess", *args, has_archive=True)

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        extracted_dir = self.get_extracted_dir()
        assert extracted_dir is not None  # since has_archive is True
        out = str(extracted_dir / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]


def analyze_outguess(input_img: Path, output_dir: Path, password: Optional[str] = None) -> None:
    """Analyze an image submission using outguess."""
    analyzer = OutguessAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
