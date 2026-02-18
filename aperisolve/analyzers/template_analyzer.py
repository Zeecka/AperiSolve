"""<toolname> Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class TemplateAnalyzer(SubprocessAnalyzer):
    """Analyzer for <toolname>."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the template analyzer."""
        super().__init__("<toolname>", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build command for a placeholder analyzer implementation."""
        if password:
            return ["<toolname>", "-p", password, "-i", self.img]
        return ["<toolname>", "-i", self.img]


def analyze_template(input_img: Path, output_dir: Path, password: str | None = None) -> None:
    """Analyze an image submission using <toolname>."""
    analyzer = TemplateAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
