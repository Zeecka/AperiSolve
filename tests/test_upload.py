"""Tests for the upload happy path, deduplication and validation errors."""

import io
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from PIL import Image as PILImage
from werkzeug.test import TestResponse

from aperisolve import app as app_module
from aperisolve.config import JOB_TIMEOUT
from aperisolve.models import Image, Submission, UploadLog, db

EnqueueCall = tuple[tuple[object, ...], dict[str, object]]


def _png_bytes() -> bytes:
    """Return a tiny valid 2x2 PNG."""
    buffer = io.BytesIO()
    PILImage.new("RGB", (2, 2), color=(128, 64, 32)).save(buffer, format="PNG")
    return buffer.getvalue()


def _post_image(client: FlaskClient, data: bytes, filename: str) -> TestResponse:
    """Upload raw bytes as an image file field."""
    return client.post(
        "/upload",
        data={"image": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


@pytest.fixture
def enqueue_calls(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> list[EnqueueCall]:
    """Capture RQ enqueue calls and point RESULT_FOLDER at a temp dir."""
    monkeypatch.setattr(app_module, "RESULT_FOLDER", tmp_path)
    calls: list[EnqueueCall] = []

    def _record(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(app.config["REDIS_QUEUE"], "enqueue", _record)
    return calls


def test_upload_creates_rows_and_enqueues(
    app: Flask,
    client: FlaskClient,
    enqueue_calls: list[EnqueueCall],
) -> None:
    """A first upload persists rows, writes a log and enqueues one job."""
    response = _post_image(client, _png_bytes(), "tiny.png")
    assert response.status_code == 200
    sub_hash = response.get_json()["submission_hash"]

    with app.app_context():
        submission = db.session.get(Submission, sub_hash)
        assert submission is not None
        assert submission.status == "pending"
        image = db.session.get(Image, submission.image_hash)
        assert image is not None
        assert Path(image.file).exists()
        assert UploadLog.query.count() == 1

    assert len(enqueue_calls) == 1
    args, kwargs = enqueue_calls[0]
    assert args == ("aperisolve.workers.analyze_image", sub_hash)
    assert kwargs.get("job_timeout") == JOB_TIMEOUT


def test_duplicate_upload_returns_same_hash_without_second_enqueue(
    app: Flask,
    client: FlaskClient,
    enqueue_calls: list[EnqueueCall],
) -> None:
    """An identical re-upload is deduplicated but still logged."""
    png = _png_bytes()
    first = _post_image(client, png, "tiny.png")
    second = _post_image(client, png, "tiny.png")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["submission_hash"] == first.get_json()["submission_hash"]
    assert len(enqueue_calls) == 1
    with app.app_context():
        assert UploadLog.query.count() == 2


def test_upload_without_extension_is_rejected(
    client: FlaskClient,
    enqueue_calls: list[EnqueueCall],
) -> None:
    """Filenames without a supported extension get a 400."""
    response = _post_image(client, b"not an image", "noextension")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Unsupported file type"
    assert not enqueue_calls


def test_upload_with_empty_filename_is_rejected(
    client: FlaskClient,
    enqueue_calls: list[EnqueueCall],
) -> None:
    """An empty filename means no usable image was provided."""
    response = _post_image(client, b"not an image", "")
    assert response.status_code == 400
    assert "error" in response.get_json()
    assert not enqueue_calls
