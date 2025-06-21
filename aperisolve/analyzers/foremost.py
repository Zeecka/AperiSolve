"""Foremost Analyzer for Image Submissions."""

import shutil
import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_foremost(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using foremost."""

    try:
        foremost_dir = output_dir / "foremost"
        foremost_dir.mkdir(parents=True, exist_ok=True)

        stderr = ""
        # Run foremost
        data = subprocess.run(
            ["foremost", "-o", foremost_dir, "-i", input_img],
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        # Note: foremost use stderr as standard output for results :o)
        # So we can't use it as error dectection :
        # stderr += data.stderr

        # Zip extracted files
        zip_data = subprocess.run(
            ["7z", "a", "../foremost.7z", "*"],
            cwd=foremost_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        stderr += zip_data.stderr

        # Remove the extracted directory
        shutil.rmtree(foremost_dir)

        data_strings = data.stdout.split("\n") if data else []
        data_strings = [s for s in data_strings if s]

        update_data(
            output_dir,
            {
                "foremost": {
                    "status": "ok",
                    "output": data_strings,
                    "download": f"/download/{output_dir.name}/foremost",
                }
            },
        )
    except Exception as e:
        update_data(output_dir, {"foremost": {"status": "error", "error": str(e)}})
