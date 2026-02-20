"""Asynchronous worker for analyzing image submissions."""

import threading
from collections.abc import Callable
from pathlib import Path

import sentry_sdk
from sqlalchemy.exc import SQLAlchemyError

from .analyzers.binwalk import analyze_binwalk
from .analyzers.color_remapping import analyze_color_remapping
from .analyzers.decomposer import analyze_decomposer
from .analyzers.exiftool import analyze_exiftool
from .analyzers.file import analyze_file
from .analyzers.foremost import analyze_foremost
from .analyzers.identify import analyze_identify
from .analyzers.jpseek import analyze_jpseek
from .analyzers.jsteg import analyze_jsteg
from .analyzers.openstego import analyze_openstego
from .analyzers.outguess import analyze_outguess
from .analyzers.pcrt import analyze_pcrt
from .analyzers.pngcheck import analyze_pngcheck
from .analyzers.steghide import analyze_steghide
from .analyzers.strings import analyze_strings
from .analyzers.zsteg import analyze_zsteg
from .app import create_app
from .config import RESULT_FOLDER
from .models import Image, Submission, db
from .utils.sentry import initialize_sentry


def analyze_image(submission_hash: str) -> None:
    """Analyze an image submission by running multiple analysis tools concurrently."""
    initialize_sentry()
    app = create_app()
    with app.app_context():
        submission = Submission.query.get(submission_hash)
        if submission is None:
            sentry_sdk.capture_message(f"Submission not found: {submission_hash}", level="warning")
            return

        image = Image.query.get_or_404(submission.image_hash)
        submission.status = "running"
        db.session.commit()

        try:
            img_path = Path(image.file)
            result_path = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            result_path.mkdir(parents=True, exist_ok=True)

            threads: list[threading.Thread] = []

            def run_analyzer(analyzer_func: Callable[..., None], *args: object) -> None:
                """Run an analyzer function in a separate thread."""
                analyzer_name = getattr(
                    analyzer_func,
                    "__name__",
                    analyzer_func.__class__.__name__,
                ).replace("analyze_", "")
                try:
                    analyzer_func(*args)
                except (RuntimeError, ValueError, OSError, TypeError) as exc:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("analyzer", analyzer_name)
                        scope.set_tag("submission_hash", submission_hash)
                        scope.set_context(
                            "analyzer_info",
                            {
                                "tool": analyzer_name,
                                "image_path": str(img_path),
                                "result_path": str(result_path),
                                "filename": submission.filename,
                                "deep_analysis": submission.deep_analysis,
                            },
                        )
                        scope.fingerprint = ["analyzer-error", analyzer_name]
                        sentry_sdk.capture_exception(exc)

            analyzers = [
                (analyze_binwalk, img_path, result_path),
                (analyze_color_remapping, img_path, result_path),
                (analyze_decomposer, img_path, result_path),
                (analyze_exiftool, img_path, result_path),
                (analyze_file, img_path, result_path),
                (analyze_foremost, img_path, result_path),
                (analyze_identify, img_path, result_path),
                (analyze_jpseek, img_path, result_path, submission.password),
                (analyze_jsteg, img_path, result_path),
                (analyze_openstego, img_path, result_path, submission.password),
                (analyze_pngcheck, img_path, result_path),
                (analyze_pcrt, img_path, result_path),
                (analyze_strings, img_path, result_path),
                (analyze_steghide, img_path, result_path, submission.password),
                (analyze_zsteg, img_path, result_path),
            ]

            if submission.deep_analysis:
                analyzers.append((analyze_outguess, img_path, result_path))

            for analyzer in analyzers:
                thread = threading.Thread(target=run_analyzer, args=analyzer)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            submission.status = "completed"
        except (RuntimeError, ValueError, OSError, TypeError, SQLAlchemyError) as exc:
            sentry_sdk.capture_exception(exc)
            submission.status = "error"
        finally:
            db.session.commit()
            sentry_sdk.flush(timeout=5)
