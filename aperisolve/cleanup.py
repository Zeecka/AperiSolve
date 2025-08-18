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
    try:
        now = time.time()
        
        # Check if batch_id column exists
        inspector = db.inspect(db.engine)
        submission_columns = {c["name"] for c in inspector.get_columns("submission")}
        has_batch_id = "batch_id" in submission_columns
        
        # Build query based on available columns
        query = db.session.query(Submission)
        if has_batch_id:
            query = query.with_entities(
                Submission.hash,
                Submission.filename,
                Submission.password,
                Submission.deep_analysis,
                Submission.status,
                Submission.date,
                Submission.batch_id,
                Submission.image_hash
            )
        else:
            query = query.with_entities(
                Submission.hash,
                Submission.filename,
                Submission.password,
                Submission.deep_analysis,
                Submission.status,
                Submission.date,
                Submission.image_hash
            )
        
        for submission in query.all():
            if has_batch_id:
                submission_dict = {
                    "hash": submission[0],
                    "filename": submission[1],
                    "password": submission[2],
                    "deep_analysis": submission[3],
                    "status": submission[4],
                    "date": submission[5],
                    "batch_id": submission[6],
                    "image_hash": submission[7]
                }
            else:
                submission_dict = {
                    "hash": submission[0],
                    "filename": submission[1],
                    "password": submission[2],
                    "deep_analysis": submission[3],
                    "status": submission[4],
                    "date": submission[5],
                    "image_hash": submission[6]
                }
            
            result_path = (
                RESULT_FOLDER / str(submission_dict["image_hash"]) / str(submission_dict["hash"])
            )
            
            if (
                submission_dict["status"] in ("pending", "running")
                and now - submission_dict["date"] > MAX_PENDING_TIME
            ):
                # Processing took too long, delete
                Submission.query.filter_by(hash=submission_dict["hash"]).delete()
                if result_path.exists():
                    shutil.rmtree(result_path)
            elif submission_dict["status"] == "done":
                # Search for buggy results, delete
                result_file = result_path / "results.json"
                if not result_file.exists():
                    Submission.query.filter_by(hash=submission_dict["hash"]).delete()
                    if result_path.exists():
                        shutil.rmtree(result_path)

        # Delete "old" images
        for img in Image.query.all():
            if img.last_submission_date.tzinfo is None:
                img_date = img.last_submission_date.replace(tzinfo=timezone.utc)
            else:
                img_date = img.last_submission_date
            delay = datetime.now(timezone.utc) - img_date
            img_fold = RESULT_FOLDER / img.hash
            if delay.total_seconds() > MAX_STORE_TIME:
                for s in img.submissions:
                    db.session.delete(s)
                if img_fold.exists():
                    shutil.rmtree(img_fold)
                db.session.delete(img)
                
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during cleanup: {e}")
        # Re-raise to allow upper layers to handle it
        raise