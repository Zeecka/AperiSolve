"""Unblob Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class UnblobAnalyzer(SubprocessAnalyzer):
    """Analyzer for unblob."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the unblob analyzer."""
        super().__init__("unblob", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the unblob extraction command."""
        _ = password
        return [
            "unblob",
            "--report",
            str(self.output_dir / f"{self.name}_report.json"),
            "--extract-dir",
            str(self.get_extracted_dir()),
            self.img,
        ]

    def _clean_output_lines(self, output: str) -> list[str]:
        """Normalize unblob's box-formatted summary output."""
        lines: list[str] = []
        for line in output.splitlines():
            cleaned = line.strip().strip("│").strip()
            if not cleaned or line.lstrip().startswith(("╭", "╰")):
                continue
            lines.append(cleaned)
        return lines

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check whether unblob execution failed."""
        _ = stdout, zip_exist
        return bool(returncode) or len(stderr) > 0

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        """Process stdout into displayable summary lines."""
        _ = stderr
        return self._clean_output_lines(stdout)

    def process_error(self, stdout: str, stderr: str) -> str:
        """Return the most useful unblob failure output."""
        output = "\n".join((*self._clean_output_lines(stdout), stderr.strip()))
        return output.strip()

    def process_note(self, stdout: str, stderr: str) -> str | None:
        """Add a note when unblob does not extract any payload."""
        _ = stderr
        output_lines = self._clean_output_lines(stdout)
        if "Extracted files: 0" in output_lines and "Extracted directories: 0" in output_lines:
            return "No extractable embedded content found."
        return None


def analyze_unblob(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using unblob."""
    analyzer = UnblobAnalyzer(input_img, output_dir)
    analyzer.analyze()
