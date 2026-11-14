"""PCRT (PNG Check & Repair Tool) Analyzer for Image Submissions."""

import json
import sys
from pathlib import Path
from typing import Any, cast

from aperisolve.utils.png import PNG

from .base_analyzer import SubprocessAnalyzer


class PCRTAnalyzer(SubprocessAnalyzer):
    """Analyzer for PCRT (PNG Check & Repair Tool)."""

    name = "pcrt"
    has_archive = True
    display_order = 90
    accepts = frozenset({"png"})

    def get_results(self, password: str | None = None) -> dict[str, Any]:
        """Run the PNG check/repair in a subprocess: same timeout + env scrub as the C tools."""
        _ = password
        cmd = [
            sys.executable,
            "-m",
            "aperisolve.analyzers.pcrt",
            str(self.input_img),
            str(self.output_dir),
        ]
        data = self.run_command(cmd, cwd=self.output_dir)
        if data.returncode != 0:
            return {"status": "error", "error": data.stderr.strip() or "pcrt failed"}
        try:
            return cast("dict[str, Any]", json.loads(data.stdout))
        except json.JSONDecodeError:
            return {"status": "error", "error": "pcrt produced invalid output"}

    def _write_repaired_data(self, data: bytes) -> str:
        """Write recovered image."""
        img_name = f"pcrt_recovered_{self.input_img.stem}.png"
        output_path = self.output_dir / img_name
        saved_img_url = "/image/" + str(Path(self.output_dir.name) / img_name)
        with output_path.open("wb") as f:
            f.write(data)
        return saved_img_url

    def _write_extra_data(self, data: bytes) -> None:
        """Write recovered extra data."""
        extracted_dir = self.get_extracted_dir()
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extra_path = extracted_dir / "extra_data.bin"
        with extra_path.open("wb") as f:
            f.write(data)

    def _repair(self) -> dict[str, Any]:
        """PNG check/repair logic; invoked in-process by the subprocess entry point below."""
        try:
            with self.input_img.open("rb") as f:
                data = f.read()

            png = PNG(data)
            fixed, extra_data = png.repair()

            result: dict[str, Any] = {}

            if png.errors:
                result["status"] = "error"
                result["error"] = "\n".join(png.errors)
                if png.logs:
                    result["output"] = png.logs
                return result

            result["status"] = "ok"
            result["output"] = png.logs or ["PNG appears valid, no repairs needed"]

            # Save repaired PNG if any fixes were made
            if fixed and png.repaired_data:
                url = self._write_repaired_data(bytes(png.repaired_data))
                result["note"] = "PNG was repaired and saved"
                result["png_images"] = [url]

            # Save extra data if found after IEND
            if extra_data:
                self._write_extra_data(extra_data)
                self.generate_archive()
                result["note"] = result.get("note", "") + " | Extra data found after IEND"
                result["download"] = f"/download/{self.output_dir.name}/{self.name}"

        except (ValueError, OSError, RuntimeError, TypeError) as e:
            return {"status": "error", "error": f"Analysis failed: {e!s}"}
        else:
            return result


def _main() -> None:
    """Entry point: ``python -m aperisolve.analyzers.pcrt <img> <out>``.

    Prints the repair result as JSON on stdout for the parent ``get_results``
    to parse; writes the repaired PNG / extra-data archive into ``<out>``.
    """
    analyzer = PCRTAnalyzer(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(analyzer._repair()))  # noqa: SLF001, T201


if __name__ == "__main__":
    _main()
