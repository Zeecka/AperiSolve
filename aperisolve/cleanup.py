# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
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
    """
    Clean up old and incomplete entries from the database and file system.

    This function performs two main cleanup operations:

    1. Submission cleanup:
       - Deletes submissions with "pending" or "running" status that have exceeded
         the maximum allowed processing time (MAX_PENDING_TIME).
       - Deletes completed submissions ("done" status) that have missing or buggy
         results (results.json file not found).

    2. Image cleanup:
       - Deletes images older than MAX_STORE_TIME along with all associated
         submissions and their result folders.
       - Deletes orphaned images (with no submissions) older than MAX_PENDING_TIME
         and removes their associated result folders from the file system.

    All database changes are committed at the end of the operation.

    Returns:
        None
    """
    now = time.time()
    for submission in Submission.query.all():  # type: ignore
        if (
            submission.status in ("pending", "running")  # type: ignore
            and now - submission.date > MAX_PENDING_TIME  # type: ignore
        ):
            # Processing took too long, delete
            db.session.delete(submission)  # pylint: disable=no-member
        elif submission.status == "done":  # type: ignore
            # Search for buggy results, delete
            result_path = RESULT_FOLDER / str(submission.image_hash) / str(submission.hash)
            result_file = result_path / "results.json"
            if not result_file.exists():
                db.session.delete(submission)  # pylint: disable=no-member
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
                db.session.delete(s)  # pylint: disable=no-member
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)  # pylint: disable=no-member

        # Delete Images with missing submission
        if len(img.submissions) == 0 and delay.total_seconds() > MAX_PENDING_TIME:
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)  # pylint: disable=no-member

    db.session.commit()  # pylint: disable=no-member
