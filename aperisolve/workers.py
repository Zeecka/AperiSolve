"""Asynchronous worker for analyzing image submissions."""

import threading
from pathlib import Path
from typing import Any

from .analyzers.binwalk import analyze_binwalk
from .analyzers.decomposer import analyze_decomposer
from .analyzers.exiftool import analyze_exiftool
from .analyzers.foremost import analyze_foremost
from .analyzers.image_resize import analyze_image_resize
from .analyzers.openstego import analyze_openstego
from .analyzers.outguess import analyze_outguess
from .analyzers.pngcheck import analyze_pngcheck
from .analyzers.steghide import analyze_steghide
from .analyzers.strings import analyze_strings
from .analyzers.zsteg import analyze_zsteg
from .app import app, db
from .config import RESULT_FOLDER
from .models import Image, Submission


def analyze_image(submission_hash: str) -> None:
    """
    Analyze an image submission by running multiple analysis tools concurrently.

    This function retrieves a submission and its associated image from the database,
    then executes various image analysis tools in parallel threads. The analysis tools
    include binwalk, decomposer, exiftool, foremost, strings, pngcheck, steghide,
    zsteg, and image resize. If deep analysis is enabled, additional tools like
    outguess are included.

    Args:
        submission_hash (str): The unique hash identifier of the submission to analyze.

    Returns:
        None

    Raises:
        Implicitly catches and handles exceptions during analysis, setting submission
        status to "error" if an exception occurs.

    Side Effects:
        - Queries the database for the submission and associated image
        - Updates submission status in the database ("running" -> "completed" or "error")
        - Creates result directories and generates analysis output files
        - Modifies the database session and commits changes
    """
    with app.app_context():
        submission: Submission = Submission.query.get(submission_hash)  # type: ignore
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore

        if not submission or not image:  # No submission found
            return

        submission.status = "running"  # type: ignore
        db.session.commit()  # pylint: disable=no-member

        try:
            img_path: Path = Path(image.file)
            result_path: Path = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            result_path.mkdir(parents=True, exist_ok=True)

            threads: list[threading.Thread] = []

            def run_analyzer(analyzer_func: Any, *args: Any) -> None:
                """Run an analyzer function in a separate thread."""
                try:
                    analyzer_func(*args)
                except Exception as e:
                    print(f"Error in {analyzer_func.__name__}: {e}")

            analyzers = [
                (analyze_binwalk, img_path, result_path),
                (analyze_decomposer, img_path, result_path),
                (analyze_exiftool, img_path, result_path),
                (analyze_foremost, img_path, result_path),
                (analyze_strings, img_path, result_path),
                (analyze_pngcheck, img_path, result_path),
                (analyze_steghide, img_path, result_path, submission.password),
                (analyze_openstego, img_path, result_path, submission.password),
                (analyze_zsteg, img_path, result_path),
                (analyze_image_resize, img_path, result_path),
            ]

            # Deep analysis only
            if submission.deep_analysis:
                analyzers.extend(
                    [
                        (analyze_outguess, img_path, result_path),
                    ]
                )

            for analyzer in analyzers:
                thread = threading.Thread(target=run_analyzer, args=analyzer)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            submission.status = "completed"
        except Exception:
            submission.status = "error"
        finally:
            db.session.commit()  # pylint: disable=no-member
