"""Outguess Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class OutguessAnalyzer(SubprocessAnalyzer):
    """Analyzer for outguess."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the outguess analyzer."""
        super().__init__("outguess", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the outguess extraction command."""
        extracted_dir = self.get_extracted_dir()
        out = str(extracted_dir / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]


def analyze_outguess(input_img: Path, output_dir: Path, password: str | None = None) -> None:
    """Analyze an image submission using outguess."""
    analyzer = OutguessAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
