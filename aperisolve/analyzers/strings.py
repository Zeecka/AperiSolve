"""Strings Analyzer for Image Submissions."""

import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_strings(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using strings."""

    try:
        data = subprocess.run(
            ["strings", input_img],
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        if data.stderr:
            update_data(
                output_dir, {"strings": {"status": "error", "error": data.stderr}}
            )
            return

        # strings_dir = output_dir / "strings"
        # strings_dir.mkdir(parents=True, exist_ok=True)
        # with open(strings_dir / "strings.txt", "w", encoding="utf-8") as f:
        #    subprocess.run(["strings", input_img], stdout=f, check=True)

        data_strings = data.stdout.split("\n") if data else []
        data_strings = [s for s in data_strings if s]

        update_data(
            output_dir,
            {
                "strings": {
                    "status": "ok",
                    "output": data_strings,
                }
            },
        )
    except Exception as e:
        update_data(output_dir, {"strings": {"status": "error", "error": str(e)}})
