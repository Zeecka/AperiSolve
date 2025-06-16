"""Cleanup old entries in the database and file system."""

import shutil
import time
from datetime import datetime, timezone
from os import getenv
from pathlib import Path

from .models import Image, Submission, db

RESULT_FOLDER = Path("./results")
MAX_PENDING_TIME = int(getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default
MAX_STORE_TIME = int(getenv("MAX_STORE_TIME", "259200"))  # 3 days by default


def cleanup_old_entries() -> None:
    """Clean up old entries in the database and file system."""
    now = time.time()
    for submission in Submission.query.all():  # type: ignore
        if (
            submission.status in ("pending", "running")  # type: ignore
            and now - submission.date > MAX_PENDING_TIME  # type: ignore
        ):
            # Processing took too long, delete
            db.session.delete(submission)  # type: ignore
        elif submission.status == "done":  # type: ignore
            # Search for buggy results, delete
            result_path = (
                RESULT_FOLDER / str(submission.image_hash) / str(submission.hash)
            )
            result_file = result_path / "results.json"
            if not result_file.exists():
                db.session.delete(submission)  # type: ignore
                shutil.rmtree(result_path)

    # Delete "old" images
    for img in Image.query.all():  # type: ignore
        if img.last_submission_date.tzinfo is None:
            img_date = img.last_submission_date.replace(tzinfo=timezone.utc)
        else:
            img_date = img.last_submission_date
        delay = datetime.now(timezone.utc) - img_date
        img_fold = RESULT_FOLDER / img.hash
        if delay.total_seconds() > MAX_STORE_TIME:
            for s in img.submissions:
                db.session.delete(s)  # type: ignore
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)

        # Delete Images with missing submission
        if len(img.submissions) == 0 and delay.total_seconds() > MAX_PENDING_TIME:
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)

    db.session.commit()
