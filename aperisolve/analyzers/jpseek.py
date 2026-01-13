# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""JPSeek Analyzer for Image Submissions."""

from pathlib import Path
from typing import Optional

from .base_analyzer import SubprocessAnalyzer


class JpseekAnalyzer(SubprocessAnalyzer):
    """Analyzer for jpseek."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("jpseek", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: Optional[str] = None) -> list[str]:
        extracted_dir = self.get_extracted_dir()
        assert extracted_dir is not None  # since has_archive is True
        out = str(extracted_dir / "jpseek.out")
        jpseek_cmd = f"jpseek {self.img} {out}"
        if password is None:
            password = ""
        expect_cmd = (
            f"expect -c 'spawn {jpseek_cmd}; "
            f'expect "Passphrase:"; '
            f'send "{password}\\r"; '
            f"expect eof'"
        )
        command = ["bash", "-c", expect_cmd]
        print("Built command:", command)
        return command

    def _remove_output_artifacts(self, output: str) -> str:
        extracted_dir = self.get_extracted_dir()
        out_file = str(extracted_dir / "jpseek.out")
        o = output
        o = o.replace("jpseek, version 0.3 (c) 1998 Allan Latham <alatham@flexsys-group.com>", "")
        o = o.replace("This is licenced software but no charge is made for its use.", "")
        o = o.replace("NO WARRANTY whatsoever is offered with this product.", "")
        o = o.replace("NO LIABILITY whatsoever is accepted for its use.", "")
        o = o.replace("You are using this entirely at your OWN RISK.", "")
        o = o.replace("See the GNU Public Licence for full details.", "")
        o = o.replace("Passphrase:", "")
        o = o.replace(f"spawn jpseek {self.img} {out_file}", "")
        return o.strip()

    def is_error(self, returncode: int, stdout: str, stderr: str, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        return bool(returncode) and "File not completely recovered" not in "".join([stdout, stderr])

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process stderr."""
        output = stdout + stderr
        output = self._remove_output_artifacts(output)
        return output

    def process_output(self, stdout: str, stderr: str) -> str:
        """Process stdout."""
        output = stdout + stderr
        output = self._remove_output_artifacts(output)
        if output == "":
            output = "File completely recovered."
        return output


def analyze_jpseek(input_img: Path, output_dir: Path, password: Optional[str] = None) -> None:
    """Analyze an image submission using jpseek."""
    analyzer = JpseekAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
