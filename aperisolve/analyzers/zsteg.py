"""Zsteg Analyzer for Image Submissions."""

import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_zsteg(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using zsteg."""

    try:
        data = subprocess.run(
            ["zsteg", input_img],
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        if data.stderr or "PNG::NotSupported" in data.stdout[:100]:
            error_msg = data.stderr or data.stdout
            update_data(output_dir, {"zsteg": {"status": "error", "error": error_msg}})
            return

        # zsteg_dir = output_dir / "zsteg"
        # zsteg_dir.mkdir(parents=True, exist_ok=True)
        # with open(zsteg_dir / "zsteg.txt", "w", encoding="utf-8") as f:
        #     subprocess.run(["zsteg", input_img], stdout=f, check=True)

        update_data(
            output_dir,
            {
                "zsteg": {
                    "status": "ok",
                    "output": data.stdout.split("\n") if data else [],
                }
            },
        )
    except Exception as e:
        update_data(output_dir, {"zsteg": {"status": "error", "error": str(e)}})
