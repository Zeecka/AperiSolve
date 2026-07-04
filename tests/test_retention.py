"""Tests for retention: stale submissions, vanished results and expired images."""

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask

from aperisolve import models
from aperisolve.config import MAX_STORE_TIME, STALE_SUBMISSION_CUTOFF
from aperisolve.models import (
    Image,
    Submission,
    _cleanup_images,
    _cleanup_submissions,
    cleanup_old_entries,
    db,
)

IMG_HASH = "a" * 32
SUB_HASH = "b" * 32


@pytest.fixture
def result_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the cleanup code at an isolated result folder.

    ``models.py`` imported ``RESULT_FOLDER`` by value, so the module attribute
    itself must be patched.
    """
    monkeypatch.setattr(models, "RESULT_FOLDER", tmp_path)
    return tmp_path


def _naive_utcnow() -> datetime:
    """Naive UTC now, matching how cleanup compares the DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def _add_image(image_hash: str, last_submission_date: datetime | None = None) -> None:
    """Insert an image row (cleanup never reads the file path itself)."""
    when = last_submission_date or _naive_utcnow()
    db.session.add(
        Image(
            hash=image_hash,
            file=f"/nonexistent/{image_hash}.png",
            size=8,
            upload_count=1,
            first_submission_date=when,
            last_submission_date=when,
        ),
    )
    db.session.commit()


def _add_submission(sub_hash: str, image_hash: str, status: str, date: float) -> None:
    """Insert a submission row for an image."""
    db.session.add(
        Submission(
            hash=sub_hash,
            filename="img.png",
            status=status,
            date=date,
            image_hash=image_hash,
        ),
    )
    db.session.commit()


@pytest.mark.usefixtures("result_folder")
def test_fresh_rows_survive_cleanup(app: Flask) -> None:
    """Recent pending submissions and their images are left alone."""
    with app.app_context():
        _add_image(IMG_HASH)
        _add_submission(SUB_HASH, IMG_HASH, "pending", time.time())
        cleanup_old_entries()
        assert db.session.get(Submission, SUB_HASH) is not None
        assert db.session.get(Image, IMG_HASH) is not None


@pytest.mark.usefixtures("result_folder")
def test_stale_pending_submission_is_deleted(app: Flask) -> None:
    """Pending submissions older than the stale cutoff are purged."""
    with app.app_context():
        _add_image(IMG_HASH)
        _add_submission(SUB_HASH, IMG_HASH, "pending", time.time() - STALE_SUBMISSION_CUTOFF - 10)
        _cleanup_submissions(time.time())
        assert db.session.get(Submission, SUB_HASH) is None
        assert db.session.get(Image, IMG_HASH) is not None


def test_completed_submission_with_results_survives(app: Flask, result_folder: Path) -> None:
    """Completed submissions keep their row while results.json exists on disk."""
    result_dir = result_folder / IMG_HASH / SUB_HASH
    result_dir.mkdir(parents=True)
    (result_dir / "results.json").write_text("{}")
    with app.app_context():
        _add_image(IMG_HASH)
        _add_submission(SUB_HASH, IMG_HASH, "completed", time.time())
        _cleanup_submissions(time.time())
        assert db.session.get(Submission, SUB_HASH) is not None
    assert (result_dir / "results.json").exists()


def test_completed_submission_without_results_is_deleted(app: Flask, result_folder: Path) -> None:
    """Completed submissions whose results.json vanished go, result dir included."""
    result_dir = result_folder / IMG_HASH / SUB_HASH
    result_dir.mkdir(parents=True)
    (result_dir / "partial.txt").write_text("half-written output")
    with app.app_context():
        _add_image(IMG_HASH)
        _add_submission(SUB_HASH, IMG_HASH, "completed", time.time())
        _cleanup_submissions(time.time())
        assert db.session.get(Submission, SUB_HASH) is None
    assert not result_dir.exists()


def test_expired_image_removed_with_submissions_and_files(
    app: Flask,
    result_folder: Path,
) -> None:
    """Images past MAX_STORE_TIME take their submissions and result folder along."""
    result_dir = result_folder / IMG_HASH / SUB_HASH
    result_dir.mkdir(parents=True)
    (result_dir / "results.json").write_text("{}")
    expired = _naive_utcnow() - timedelta(seconds=MAX_STORE_TIME + 60)
    with app.app_context():
        _add_image(IMG_HASH, last_submission_date=expired)
        _add_submission(SUB_HASH, IMG_HASH, "completed", time.time())
        cleanup_old_entries()
        assert db.session.get(Image, IMG_HASH) is None
        assert db.session.get(Submission, SUB_HASH) is None
    assert not (result_folder / IMG_HASH).exists()


@pytest.mark.usefixtures("result_folder")
def test_orphan_image_past_stale_cutoff_is_deleted(app: Flask) -> None:
    """Images without submissions are purged once past the stale cutoff."""
    orphaned = _naive_utcnow() - timedelta(seconds=STALE_SUBMISSION_CUTOFF + 60)
    with app.app_context():
        _add_image(IMG_HASH, last_submission_date=orphaned)
        _cleanup_images()
        assert db.session.get(Image, IMG_HASH) is None
