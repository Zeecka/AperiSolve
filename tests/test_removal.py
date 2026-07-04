"""Tests for the /remove and /remove_password guard rails."""

import time
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from aperisolve import app as app_module
from aperisolve.config import REMOVAL_MIN_AGE_SECONDS
from aperisolve.models import Image, Submission, UploadLog, db

IMG_HASH = "1" * 32
SUB_HASH = "2" * 32
OLD_ENOUGH = REMOVAL_MIN_AGE_SECONDS + 60


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate the result and removed-images folders in a temp dir."""
    monkeypatch.setattr(app_module, "RESULT_FOLDER", tmp_path / "results")
    monkeypatch.setattr(app_module, "REMOVED_IMAGES_FOLDER", tmp_path / "removed")
    return tmp_path


def _seed(
    app: Flask,
    tmp_path: Path,
    *,
    age_seconds: float,
    ips: list[str],
    password: str | None = None,
) -> Path:
    """Insert an image + submission + upload logs; return the image file path."""
    img_file = tmp_path / f"{IMG_HASH}.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    with app.app_context():
        db.session.add(Image(hash=IMG_HASH, file=str(img_file), size=8, upload_count=len(ips)))
        db.session.add(
            Submission(
                hash=SUB_HASH,
                filename="secret.png",
                password=password,
                status="completed",
                date=time.time() - age_seconds,
                image_hash=IMG_HASH,
            ),
        )
        for ip in ips:
            db.session.add(
                UploadLog(
                    ip_address=ip,
                    image_hash=IMG_HASH,
                    submission_hash=SUB_HASH,
                    filename="secret.png",
                ),
            )
        db.session.commit()
    return img_file


@pytest.mark.usefixtures("storage")
def test_remove_young_submission_is_forbidden(
    app: Flask,
    client: FlaskClient,
    tmp_path: Path,
) -> None:
    """Submissions younger than the minimum age cannot be removed."""
    _seed(app, tmp_path, age_seconds=0, ips=["203.0.113.1"])
    response = client.post(f"/remove/{SUB_HASH}")
    assert response.status_code == 403
    assert "seconds old" in response.get_json()["error"]


@pytest.mark.usefixtures("storage")
def test_remove_with_multiple_uploader_ips_is_forbidden(
    app: Flask,
    client: FlaskClient,
    tmp_path: Path,
) -> None:
    """Images uploaded from several IPs cannot be removed by one of them."""
    _seed(app, tmp_path, age_seconds=OLD_ENOUGH, ips=["203.0.113.1", "203.0.113.2"])
    response = client.post(f"/remove/{SUB_HASH}")
    assert response.status_code == 403
    body = response.get_json()
    assert "IP" in body["error"]
    assert body["ip_count"] == 2


def test_remove_deletes_rows_and_archives_original(
    app: Flask,
    client: FlaskClient,
    storage: Path,
) -> None:
    """A single-IP, old-enough submission is removed and the image archived."""
    img_file = _seed(app, storage, age_seconds=OLD_ENOUGH, ips=["203.0.113.1"])
    response = client.post(f"/remove/{SUB_HASH}")
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Submission, SUB_HASH) is None
        assert db.session.get(Image, IMG_HASH) is None
    assert not img_file.exists()
    archived = list((storage / "removed").iterdir())
    assert len(archived) == 1
    assert archived[0].name.startswith(f"{IMG_HASH}_{SUB_HASH}_")


@pytest.mark.usefixtures("storage")
def test_remove_password_without_password_is_400(
    app: Flask,
    client: FlaskClient,
    tmp_path: Path,
) -> None:
    """Password removal on a passwordless submission is rejected."""
    _seed(app, tmp_path, age_seconds=OLD_ENOUGH, ips=["203.0.113.1"], password=None)
    response = client.post(f"/remove_password/{SUB_HASH}")
    assert response.status_code == 400
    assert "No password" in response.get_json()["error"]
