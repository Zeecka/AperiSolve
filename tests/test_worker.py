"""Tests for analyze_image status transitions without real analyzers."""

import time
from pathlib import Path

import pytest
from flask import Flask

from aperisolve import workers
from aperisolve.models import Image, Submission, db

IMG_HASH = "a" * 32
SUB_HASH = "b" * 32


class _ExplodingAnalyzer:
    """Analyzer stand-in whose execution always fails."""

    name = "boom"

    @classmethod
    def execute(cls, _img: Path, _out: Path, _password: str | None = None) -> None:
        """Fail the way a broken tool binary would."""
        message = "tool crashed"
        raise RuntimeError(message)


def _no_analyzers(**_kwargs: object) -> list[type]:
    """Return no analyzers at all."""
    return []


def _exploding_analyzers(**_kwargs: object) -> list[type]:
    """Return a single analyzer that always raises."""
    return [_ExplodingAnalyzer]


@pytest.fixture
def worker_app(app: Flask, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Flask:
    """Wire the worker module to the test app and an isolated result folder."""
    monkeypatch.setattr(workers, "create_app", lambda: app)
    monkeypatch.setattr(workers, "RESULT_FOLDER", tmp_path)
    return app


def _seed(app: Flask, tmp_path: Path) -> None:
    """Insert an image + pending submission pair."""
    img_file = tmp_path / f"{IMG_HASH}.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    with app.app_context():
        db.session.add(Image(hash=IMG_HASH, file=str(img_file), size=8, upload_count=1))
        db.session.add(
            Submission(
                hash=SUB_HASH,
                filename="img.png",
                status="pending",
                date=time.time(),
                image_hash=IMG_HASH,
            ),
        )
        db.session.commit()


def _status(app: Flask, sub_hash: str) -> str:
    """Read back a submission's status in a fresh app context."""
    with app.app_context():
        submission = db.session.get(Submission, sub_hash)
        assert submission is not None
        return str(submission.status)


def test_no_analyzers_completes_submission(
    worker_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With zero analyzers the submission still goes pending -> completed."""
    monkeypatch.setattr(workers, "get_analyzers", _no_analyzers)
    _seed(worker_app, tmp_path)
    workers.analyze_image(SUB_HASH)
    assert _status(worker_app, SUB_HASH) == "completed"
    assert (tmp_path / IMG_HASH / SUB_HASH).is_dir()


def test_analyzer_error_still_completes_submission(
    worker_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Per-analyzer errors are captured, not fatal to the submission."""
    monkeypatch.setattr(workers, "get_analyzers", _exploding_analyzers)
    _seed(worker_app, tmp_path)
    workers.analyze_image(SUB_HASH)
    assert _status(worker_app, SUB_HASH) == "completed"


@pytest.mark.usefixtures("worker_app")
def test_unknown_submission_returns_quietly() -> None:
    """An unknown submission hash is a no-op rather than an exception."""
    workers.analyze_image("f" * 32)


def test_missing_image_marks_submission_error(worker_app: Flask) -> None:
    """A submission whose image row vanished ends in status error."""
    with worker_app.app_context():
        db.session.add(
            Submission(
                hash=SUB_HASH,
                filename="img.png",
                status="pending",
                date=time.time(),
                image_hash="d" * 32,
            ),
        )
        db.session.commit()
    workers.analyze_image(SUB_HASH)
    assert _status(worker_app, SUB_HASH) == "error"
