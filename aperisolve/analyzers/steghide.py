"""Steghide Analyzer for Image Submissions."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .utils import MAX_PENDING_TIME, update_data


def analyze_steghide(
    input_img: Path, output_dir: Path, password: Optional[str] = None
) -> None:
    """Analyze an image submission using stehide."""

    image_name = input_img.name
    try:
        stderr = ""
        # Get embedded file information first
        cmd: list[str] = ["steghide", "info", "../" + str(image_name)]
        if password:
            cmd += ["-p", password]
        else:
            cmd += ["-p", ""]

        data = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        match = re.search(r'embedded file "([^"]+)"', data.stdout)
        embedded_filename = match.group(1) if match else None

        # if bad file format or wrong password, raise an error
        if data.returncode != 0 or embedded_filename is None:
            stderr += data.stderr.replace(f'"../{image_name}" ', "")  # hide file name
            # the file format of the file \"../foobar.png\"  is not supported.
            # become
            # the file format of the file is not supported.
            err = {
                "steghide": {
                    "status": "error",
                    "error": stderr,
                }
            }
            update_data(output_dir, err)
            return None

        # The passphrase is correct, we can extract the file
        # prevent path traversal
        embedded_file = output_dir / "steghide" / str(Path(embedded_filename).name)
        extracted_dir = embedded_file.parent
        extracted_dir.mkdir(parents=True, exist_ok=True)

        cmd_ext: list[str] = [
            "steghide",
            "extract",
            "-sf",
            "../../" + str(image_name),
            "-xf",
            str(embedded_file.name),
        ]
        if password:
            cmd_ext += ["-p", password]
        else:
            cmd_ext += ["-p", ""]

        data = subprocess.run(
            cmd_ext,
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )
        # Filter out lines that indicate success
        stdout = []
        for line in data.stderr.split("\n"):
            if line.startswith("wrote extracted data to \""):
                stdout.append(line)
            elif line:
                stderr += line + "\n"

        # Zip extracted files
        zip_data = subprocess.run(
            ["7z", "a", "../steghide.7z", "*"],
            cwd=extracted_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=MAX_PENDING_TIME,
        )

        stderr += zip_data.stderr

        if len(stderr) > 0:
            err = {
                "steghide": {
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
                "steghide": {
                    "status": "ok",
                    "output": stdout,
                    "download": f"/download/{output_dir.name}/steghide",
                }
            },
        )

    except Exception as e:
        update_data(output_dir, {"steghide": {"status": "error", "error": str(e)}})
    return None
