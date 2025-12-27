"""OpenStego Analyzer for Image Submissions."""

import shutil
import subprocess
from pathlib import Path

from .utils import MAX_PENDING_TIME, update_data


def analyze_openstego(input_img: Path, output_dir: Path, password: str = "") -> None:
    """Analyze an image submission using openstego."""

    image_name = input_img.name
    try:
        stderr = ""
        # Try to extract the embedded file
        extracted_dir = output_dir / "openstego"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        for algo in ["AES128", "AES256"]:
            cmd: list[str] = [
                "openstego",
                "extract",
                "-a",
                "randomlsb",
                "--cryptalgo",
                algo,
                "-sf",
                "../" + str(image_name),
                "-xd",
                str(extracted_dir),
                "-p",
                password,
            ]

            data = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=MAX_PENDING_TIME,
            )

            # Check if extraction was successful
            if data.returncode != 0:
                stderr += data.stderr.replace(
                    f'"../{image_name}" ', ""
                )  # hide file name
                err = {
                    "openstego": {
                        "status": "error",
                        "error": stderr,
                    }
                }
                update_data(output_dir, err)
                return None

        # Find the extracted file
        extracted_files = list(extracted_dir.glob("*"))
        if not extracted_files:
            err = {
                "openstego": {
                    "status": "error",
                    "error": "No file extracted, password may be incorrect.",
                }
            }
            update_data(output_dir, err)
            return None

        # Filter stdout for success messages
        stdout = []
        for f in extracted_files:
            stdout.append(f"Recovered file: {f.name}")

        # Zip extracted files
        zip_data = subprocess.run(
            ["7z", "a", "../openstego.7z", "*"],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        stderr += zip_data.stderr

        if len(stderr) > 0:
            err = {
                "openstego": {
                    "status": "error",
                    "error": stderr,
                }
            }
            update_data(output_dir, err)
            return None

        # Remove the extracted directory
        shutil.rmtree(extracted_dir)

        update_data(
            output_dir,
            {
                "openstego": {
                    "status": "ok",
                    "output": stdout,
                    "download": f"/download/{output_dir.name}/openstego",
                }
            },
        )

    except Exception as e:
        update_data(output_dir, {"openstego": {"status": "error", "error": str(e)}})
    return None
