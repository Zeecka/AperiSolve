"""Outguess Analyzer for Image Submissions."""

from typing import Any

from .base_analyzer import SubprocessAnalyzer


class OutguessAnalyzer(SubprocessAnalyzer):
    """Analyzer for outguess."""

    name = "outguess"
    has_archive = True
    needs_password = True
    deep_only = True
    display_order = 70
    accepts = frozenset({"jpeg"})

    def build_cmd(self, password: str | None = None) -> list[str]:
        """Build the outguess extraction command."""
        extracted_dir = self.get_extracted_dir()
        out = str(extracted_dir / "outguess.data")
        if password:
            return ["outguess", "-k", password, "-r", self.img, out]
        return ["outguess", "-r", self.img, out]

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Run outguess, treating a non-empty extracted file as success.

        outguess is chatty on stderr even when it succeeds, so the default
        ``is_error`` (stderr present) would flag every run as failed. It also
        writes an empty output file when retrieval fails ("datalen is too
        long", wrong key), which would fool the base "any file = archive"
        check. Success is therefore defined as a non-empty ``outguess.data``.
        """
        extracted_dir = self.get_extracted_dir()
        extracted_dir.mkdir(parents=True, exist_ok=True)
        cmd = self.build_cmd(password) if password else self.build_cmd()
        data = self.run_command(list(map(str, cmd)), cwd=self.output_dir)

        out_file = extracted_dir / "outguess.data"
        if out_file.exists() and out_file.stat().st_size == 0:
            out_file.unlink()

        if extracted_dir.exists() and any(extracted_dir.iterdir()):
            self.generate_archive(extracted_dir)
            return {
                "status": "ok",
                "output": [line for line in data.stderr.splitlines() if line.strip()],
                "download": f"/download/{self.output_dir.name}/{self.name}",
            }
        return {"status": "error", "error": data.stderr.strip()}
