"""Asynchronous worker for analyzing image submissions."""

import concurrent.futures
import json
from pathlib import Path
from typing import Any

from .analyzers.binwalk import analyze_binwalk
from .analyzers.decomposer import analyze_decomposer
from .analyzers.exiftool import analyze_exiftool
from .analyzers.foremost import analyze_foremost
from .analyzers.outguess import analyze_outguess
from .analyzers.steghide import analyze_steghide
from .analyzers.strings import analyze_strings
from .analyzers.zsteg import analyze_zsteg
from .app import app, db
from .config import RESULT_FOLDER
from .models import Image, Submission
from .analyzers.utils import update_data


def analyze_image(submission_hash: str) -> None:
    """Analyze an image submission in separate threads."""
    with app.app_context():
        submission: Submission = Submission.query.get(submission_hash)  # type: ignore
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore

        if not submission or not image:  # No submission found
            return

        submission.status = "running"  # type: ignore
        db.session.commit()

        try:
            img_path: Path = Path(image.file)
            result_path: Path = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            result_path.mkdir(parents=True, exist_ok=True)

            # Initialize an empty results file so partial results can be appended safely
            try:
                update_data(result_path, {})
            except Exception:
                pass

            analyzer_list = [
                ("binwalk", analyze_binwalk, (img_path, result_path)),
                ("decomposer", analyze_decomposer, (img_path, result_path)),
                ("exiftool", analyze_exiftool, (img_path, result_path)),
                ("foremost", analyze_foremost, (img_path, result_path)),
                ("strings", analyze_strings, (img_path, result_path)),
                ("steghide", analyze_steghide, (img_path, result_path, submission.password)),
                ("zsteg", analyze_zsteg, (img_path, result_path)),
            ]

            if submission.deep_analysis:
                analyzer_list.append(("outguess", analyze_outguess, (img_path, result_path)))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for _name, analyzer_func, args in analyzer_list:
                    futures.append(executor.submit(analyzer_func, *args))

                # Ensure all analyzers finish; they write their own outputs via update_data
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        # Individual analyzers already record their own errors
                        pass

            submission.status = "completed"
        except Exception:
            submission.status = "error"
        finally:
            db.session.commit()