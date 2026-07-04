"""Asynchronous worker for analyzing image submissions."""

import contextlib
import threading
from pathlib import Path

import sentry_sdk
from sqlalchemy.exc import SQLAlchemyError

from .analyzers.base_analyzer import SubprocessAnalyzer
from .analyzers.registry import get_analyzers
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

        image = Image.query.get(submission.image_hash)
        if image is None:
            sentry_sdk.capture_message(
                f"Image not found: {submission.image_hash}",
                level="warning",
            )
            submission.status = "error"
            db.session.commit()
            return

        submission.status = "running"
        # Snapshot ORM attributes before committing: the commit expires them,
        # and the analyzer threads below must never trigger lazy loads on the
        # shared, non-thread-safe session.
        password = submission.password
        filename = submission.filename
        deep_analysis = bool(submission.deep_analysis)
        img_file = str(image.file)
        img_hash = str(image.hash)
        db.session.commit()

        try:
            img_path = Path(img_file)
            result_path = RESULT_FOLDER / img_hash / submission_hash
            result_path.mkdir(parents=True, exist_ok=True)

            threads: list[threading.Thread] = []

            def run_analyzer(analyzer_cls: type[SubprocessAnalyzer]) -> None:
                """Run an analyzer class in a separate thread."""
                try:
                    analyzer_cls.execute(img_path, result_path, password)
                except (RuntimeError, ValueError, OSError, TypeError) as exc:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("analyzer", analyzer_cls.name)
                        scope.set_tag("submission_hash", submission_hash)
                        # Attach the analyzed image so errors can be
                        # reproduced from the Sentry event (issue #193).
                        with contextlib.suppress(OSError):
                            scope.add_attachment(path=str(img_path))
                        scope.set_context(
                            "analyzer_info",
                            {
                                "tool": analyzer_cls.name,
                                "image_path": str(img_path),
                                "result_path": str(result_path),
                                "filename": filename,
                                "deep_analysis": deep_analysis,
                            },
                        )
                        scope.fingerprint = ["analyzer-error", analyzer_cls.name]
                        sentry_sdk.capture_exception(exc)

            for analyzer_cls in get_analyzers(deep=deep_analysis):
                thread = threading.Thread(target=run_analyzer, args=(analyzer_cls,))
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
