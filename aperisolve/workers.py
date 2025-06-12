"""Asynchronous worker for analyzing image submissions."""

import threading
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
                (analyze_steghide, img_path, result_path, submission.password),
                (analyze_zsteg, img_path, result_path),
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
            db.session.commit()
