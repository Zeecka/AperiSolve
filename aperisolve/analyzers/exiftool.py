# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Exiftool Analyzer for Image Submissions."""

import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_exiftool(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using exiftool."""

    try:
        data = subprocess.run(
            ["exiftool", input_img],
            capture_output=True,
            text=True,
            check=True,
            timeout=MAX_PENDING_TIME,
        )

        metadata: dict[str, str] = {}
        for line in data.stdout.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        if data.stderr:
            update_data(
                output_dir,
                {
                    "exiftool": {
                        "status": "error",
                        "output": metadata,
                        "error": data.stderr,
                    }
                },
            )
            return

        update_data(
            output_dir,
            {"exiftool": {"status": "ok", "output": metadata}},
        )
    except Exception as e:
        update_data(output_dir, {"exiftool": {"status": "error", "error": str(e)}})
