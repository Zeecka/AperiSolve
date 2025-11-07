"""Pngcheck Analyzer for Image Submissions."""

import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_pngcheck(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using strings."""

    try:
        data = subprocess.run(
            ["pngcheck", "-v", input_img],
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        # Error based on https://github.com/pnggroup/pngcheck/issues/59
        # if data.stderr:
        #     update_data(
        #         output_dir, {"pngcheck": {"status": "error", "error": data.stderr}}
        #     )
        #     return

        data_strings = data.stdout.split("\n") if data else []
        data_strings = [s for s in data_strings if s]

        update_data(
            output_dir,
            {
                "pngcheck": {
                    "status": "ok",
                    "output": data_strings,
                }
            },
        )
    except Exception as e:
        update_data(output_dir, {"pngcheck": {"status": "error", "error": str(e)}})
