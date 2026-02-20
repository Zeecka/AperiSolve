"""JPSeek Analyzer for Image Submissions."""

from pathlib import Path

from .base_analyzer import SubprocessAnalyzer


class JpseekAnalyzer(SubprocessAnalyzer):
    """Analyzer for jpseek."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        """Initialize the jpseek analyzer."""
        super().__init__("jpseek", input_img, output_dir, has_archive=True)

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the jpseek command wrapped with expect for password support."""
        extracted_dir = self.get_extracted_dir()
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
        return ["bash", "-c", expect_cmd]

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

    def is_error(self, returncode: int, stdout: str, stderr: str, *, zip_exist: bool) -> bool:
        """Check if the result is an error."""
        _ = zip_exist
        return bool(returncode) and "File not completely recovered" not in f"{stdout}{stderr}"

    def process_error(self, stdout: str, stderr: str) -> str:
        """Process stderr."""
        output = stdout + stderr
        return self._remove_output_artifacts(output)

    def process_output(self, stdout: str, stderr: str) -> str:
        """Process stdout."""
        output = stdout + stderr
        output = self._remove_output_artifacts(output)
        if output == "":
            output = "File completely recovered."
        return output


def analyze_jpseek(input_img: Path, output_dir: Path, password: str | None = None) -> None:
    """Analyze an image submission using jpseek."""
    analyzer = JpseekAnalyzer(input_img, output_dir)
    if password:
        analyzer.analyze(password)
    else:
        analyzer.analyze()
