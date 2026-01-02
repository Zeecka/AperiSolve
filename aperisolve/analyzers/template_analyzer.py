# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""<toolname> Analyzer for Image Submissions."""

from pathlib import Path
from typing import Optional

from .base_analyzer import SubprocessAnalyzer


class TemplateAnalyze(SubprocessAnalyzer):
    """Analyzer for <toolname>."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("<toolname>", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        if password:
            return ["<toolname>", "-p", password, "-i", self.img]
        return ["<toolname>", "-i", self.img]


def analyze_template(input_img: Path, output_dir: Path, password: Optional[str] = None) -> None:
    """Analyze an image submission using <toolname>."""
    analyzer = TemplateAnalyze(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
