"""<toolname> Analyzer for Image Submissions.

Copy this file to add a new analyzer: set the class attributes, implement
``build_cmd`` (or set ``self.cmd``), and install the tool in the Dockerfile.
Nothing else needs to change — the registry discovers the class automatically.
"""

from .base_analyzer import SubprocessAnalyzer


class TemplateAnalyzer(SubprocessAnalyzer):
    """Analyzer for <toolname>."""

    register = False  # Template only: remove this line in a real analyzer.
    name = "<toolname>"
    has_archive = True  # The tool extracts files, zipped into <toolname>.7z.
    needs_password = True  # The tool receives the submission password.
    deep_only = False  # Only run when the user requests a deep analysis.
    display_order = 1000  # Frontend rendering position (lower renders first).

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build command for a placeholder analyzer implementation."""
        if password:
            return ["<toolname>", "-p", password, "-i", self.img]
        return ["<toolname>", "-i", self.img]
