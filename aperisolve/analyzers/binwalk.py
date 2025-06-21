"""Binwalk Analyzer for Image Submissions."""

import shutil
import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_binwalk(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using binwalk."""

    image_name = input_img.name
    extracted_dir = output_dir / f"_{image_name}.extracted"

    try:
        stderr = ""
        # Run binwalk
        data = subprocess.run(
            ["binwalk", "-e", "../" + str(image_name), "--run-as=root"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        stderr += data.stderr

        zip_exist = False
        if extracted_dir.exists():
            # Zip extracted files
            zip_data = subprocess.run(
                ["7z", "a", "../binwalk.7z", "*"],
                cwd=extracted_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=MAX_PENDING_TIME,
            )
            zip_exist = True
            stderr += zip_data.stderr

        if len(stderr) > 0:
            err = {
                "binwalk": {
                    "status": "error",
                    "error": stderr,
                }
            }
            update_data(output_dir, err)
            return None

        # Remove the extracted directory
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)

        output_data = {
            "binwalk": {
                "status": "ok",
                "output": data.stdout.split("\n") if data else [],
            }
        }
        if zip_exist:
            output_data["binwalk"]["download"] = f"/download/{output_dir.name}/binwalk"

        update_data(output_dir, output_data)

    except Exception as e:
        update_data(output_dir, {"binwalk": {"status": "error", "error": str(e)}})
    return None
