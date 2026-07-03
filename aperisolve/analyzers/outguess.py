"""Outguess Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class OutguessAnalyzer(SubprocessAnalyzer):
    """Analyzer for outguess."""

    name = "outguess"
    has_archive = True
    needs_password = True
    deep_only = True
    display_order = 70

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the outguess extraction command."""
        extracted_dir = self.get_extracted_dir()
        out = str(extracted_dir / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]


def analyze_outguess(input_img: Path, output_dir: Path, password: str | None = None) -> None:
    """Analyze an image submission using outguess (deprecated: use ``execute``)."""
    OutguessAnalyzer.execute(input_img, output_dir, password)
