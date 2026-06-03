"""Unblob Analyzer for Image Submissions."""

import json
from pathlib import Path
from typing import Any

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
            str(self.get_report_path()),
            "--extract-dir",
            str(self.get_extracted_dir()),
            self.img,
        ]

    def get_report_path(self) -> Path:
        """Return the metadata report path for the current run."""
        return self.output_dir / f"{self.name}_report.json"

    def _load_report(self) -> list[dict[str, Any]]:
        """Load unblob's JSON report if it exists."""
        report_path = self.get_report_path()
        if not report_path.exists():
            return []
        with report_path.open(encoding="utf-8") as report_file:
            data = json.load(report_file)
        return data if isinstance(data, list) else []

    def _get_report_counts(self) -> tuple[int, int, int]:
        """Count extracted files, directories, and links from the JSON report."""
        extracted_dir = str(self.get_extracted_dir())
        file_count = 0
        dir_count = 0
        link_count = 0

        for entry in self._load_report():
            reports = entry.get("reports", [])
            if not isinstance(reports, list):
                continue

            for report in reports:
                if not isinstance(report, dict):
                    continue
                path = report.get("path")
                if not isinstance(path, str) or not path.startswith(extracted_dir):
                    continue
                if report.get("is_file") is True:
                    file_count += 1
                elif report.get("is_dir") is True:
                    dir_count += 1
                elif report.get("is_link") is True:
                    link_count += 1

        return file_count, dir_count, link_count

    def _get_detected_handlers(self) -> list[str]:
        """Return handler names detected by unblob."""
        handlers: list[str] = []
        for entry in self._load_report():
            reports = entry.get("reports", [])
            if not isinstance(reports, list):
                continue

            for report in reports:
                if not isinstance(report, dict):
                    continue
                handler_name = report.get("handler_name")
                if isinstance(handler_name, str) and handler_name not in handlers:
                    handlers.append(handler_name)

        return handlers

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
        _ = stdout, stderr, zip_exist
        return bool(returncode)

    def process_output(self, stdout: str, stderr: str) -> list[str]:
        """Process stdout into displayable summary lines."""
        _ = stderr
        file_count, dir_count, link_count = self._get_report_counts()
        lines = [
            f"Extracted files: {file_count}",
            f"Extracted directories: {dir_count}",
            f"Extracted links: {link_count}",
        ]
        handlers = self._get_detected_handlers()
        if handlers:
            lines.append(f"Detected chunks: {', '.join(handlers)}")
        if file_count or dir_count or link_count:
            lines.append(f"Output path: {self.get_extracted_dir()}")
        elif not handlers:
            fallback_lines = self._clean_output_lines(stdout)
            if fallback_lines:
                return fallback_lines
        return lines

    def process_error(self, stdout: str, stderr: str) -> str:
        """Return the most useful unblob failure output."""
        output = "\n".join((*self._clean_output_lines(stdout), stderr.strip()))
        return output.strip()

    def process_note(self, stdout: str, stderr: str) -> str | None:
        """Add a note when unblob does not extract any payload."""
        _ = stdout, stderr
        file_count, dir_count, link_count = self._get_report_counts()
        if file_count == 0 and dir_count == 0 and link_count == 0:
            return "No extractable embedded content found."
        return None


def analyze_unblob(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using unblob."""
    analyzer = UnblobAnalyzer(input_img, output_dir)
    analyzer.analyze()
