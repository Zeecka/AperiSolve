"""Outguess Analyzer for Image Submissions."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .utils import MAX_PENDING_TIME, update_data


def analyze_outguess(
    input_img: Path, output_dir: Path, password: Optional[str] = None
) -> None:
    """Analyze an image submission using stehide."""

    image_name = input_img.name
    try:
        outguess_dir = output_dir / "outguess"
        outguess_dir.mkdir(parents=True, exist_ok=True)
        outguess_file = "outguess.data"
        stderr = ""
        cmd: list[str]
        if password:
            cmd = [
                "outguess",
                "-k",
                password,
                "-r",
                "../../" + str(image_name),
                outguess_file,
            ]
        else:
            cmd = ["outguess", "-r", "../../" + str(image_name), outguess_file]

        data = subprocess.run(
            cmd,
            cwd=outguess_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        if data.returncode != 0:
            stderr += data.stderr
            err = {
                "outguess": {
                    "status": "error",
                    "error": stderr,
                }
            }
            update_data(output_dir, err)
            return None

        # Zip extracted files
        zip_data = subprocess.run(
            ["7z", "a", "../outguess.7z", "*"],
            cwd=outguess_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        stderr += zip_data.stderr

        if len(stderr) > 0:
            err = {
                "outguess": {
                    "status": "error",
                    "error": stderr,
                }
            }
            update_data(output_dir, err)
            return None

        # Remove the extracted directory
        shutil.rmtree(outguess_dir)

        data_strings = data.stderr.split("\n") if data else []
        data_strings = [s for s in data_strings if s]

        update_data(
            output_dir,
            {
                "outguess": {
                    "status": "ok",
                    "output": data_strings,
                    "download": f"/download/{output_dir.name}/outguess",
                }
            },
        )

    except Exception as e:
        update_data(output_dir, {"outguess": {"status": "error", "error": str(e)}})
    return None
