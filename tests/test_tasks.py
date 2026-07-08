"""Tests for the background maintenance jobs and their cron registration."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from rq import cron

import aperisolve.cron  # noqa: F401  (registration runs at import; asserted below)
from aperisolve import models, tasks
from aperisolve.config import CLEANUP_INTERVAL_SECONDS, JOB_TIMEOUT, STALE_SUBMISSION_CUTOFF
from aperisolve.models import Image, db

IMG_HASH = "c" * 32


@pytest.fixture
def job_app(app: Flask, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Flask:
    """Wire the job module to the test app, a stub Sentry init and a temp folder."""
    monkeypatch.setattr(tasks, "create_app", lambda: app)
    monkeypatch.setattr(tasks, "initialize_sentry", lambda: None)
    monkeypatch.setattr(models, "RESULT_FOLDER", tmp_path)
    return app


def _add_orphan_image(when: datetime) -> None:
    """Insert an image with no submissions, dated ``when``."""
    db.session.add(
        Image(
            hash=IMG_HASH,
            file=f"/nonexistent/{IMG_HASH}.png",
            size=8,
            upload_count=1,
            first_submission_date=when,
            last_submission_date=when,
        ),
    )
    db.session.commit()


def test_cleanup_sweep_job_runs_sweep(job_app: Flask) -> None:
    """cleanup_sweep_job runs the real sweep in its own app context (#191)."""
    stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        seconds=STALE_SUBMISSION_CUTOFF + 60,
    )
    with job_app.app_context():
        _add_orphan_image(stale)

    tasks.cleanup_sweep_job()

    with job_app.app_context():
        assert db.session.get(Image, IMG_HASH) is None


@pytest.mark.usefixtures("job_app")
def test_cleanup_sweep_job_does_not_claim_the_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    """The enqueuer already holds the interval lock, so the job never re-claims it."""
    called = False

    def _record() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(tasks, "cleanup_old_entries", _record)
    tasks.cleanup_sweep_job()
    assert called, "cleanup_sweep_job must run the sweep directly"


def test_cleanup_job_delegates_to_locked_sweep(
    job_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cron job routes through the lock-guarded sweep."""
    seen: list[Flask] = []
    monkeypatch.setattr(tasks, "run_cleanup_with_lock", seen.append)
    tasks.cleanup_job()
    assert seen == [job_app]


def test_cron_registers_cleanup_job() -> None:
    """Importing the cron module registers cleanup_job with the expected schedule."""
    # rq exposes no public API for the registered cron jobs.
    registry = cron._job_data_registry  # noqa: SLF001
    entries = [e for e in registry if e["func"] is tasks.cleanup_job]
    assert entries, "cleanup_job is not registered on the cron scheduler"
    entry = entries[-1]
    assert entry["queue_name"] == "default"
    assert entry["interval"] == CLEANUP_INTERVAL_SECONDS
    assert entry["job_timeout"] == JOB_TIMEOUT
