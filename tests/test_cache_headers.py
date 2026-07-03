"""Tests for HTTP caching behavior of data routes."""

import json
import time
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient

from aperisolve.config import RESULT_FOLDER
from aperisolve.models import Image, Submission, db

IMG_HASH = "a" * 32
SUB_HASH = "b" * 32


def _seed_submission(app: Flask, tmp_path: Path, status: str = "completed") -> Path:
    """Create an image + submission pair with a results.json on disk."""
    img_file = tmp_path / f"{IMG_HASH}.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    with app.app_context():
        db.session.add(
            Image(
                hash=IMG_HASH,
                file=str(img_file),
                size=8,
                upload_count=1,
            ),
        )
        db.session.add(
            Submission(
                hash=SUB_HASH,
                filename="test.png",
                status=status,
                date=time.time(),
                image_hash=IMG_HASH,
            ),
        )
        db.session.commit()
    result_dir = RESULT_FOLDER / IMG_HASH / SUB_HASH
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "results.json").write_text(json.dumps({"file": {"status": "ok"}}))
    return result_dir


def _cleanup_results() -> None:
    result_file = RESULT_FOLDER / IMG_HASH / SUB_HASH / "results.json"
    if result_file.exists():
        result_file.unlink()


def test_status_is_never_cached(app: Flask, client: FlaskClient, tmp_path: Path) -> None:
    """The 1 Hz status poll must always be fresh."""
    _seed_submission(app, tmp_path)
    try:
        response = client.get(f"/status/{SUB_HASH}")
        assert response.headers["Cache-Control"] == "no-store"
    finally:
        _cleanup_results()


def test_result_revalidates_with_etag(app: Flask, client: FlaskClient, tmp_path: Path) -> None:
    """Completed results serve 304s to unchanged polls."""
    _seed_submission(app, tmp_path)
    try:
        first = client.get(f"/result/{SUB_HASH}")
        assert first.status_code == 200
        assert first.headers["Cache-Control"] == "no-cache"
        etag = first.headers["ETag"]

        second = client.get(f"/result/{SUB_HASH}", headers={"If-None-Match": etag})
        assert second.status_code == 304
    finally:
        _cleanup_results()


def test_infos_is_briefly_private_cached(
    app: Flask,
    client: FlaskClient,
    tmp_path: Path,
) -> None:
    """Submission infos tolerate 30s of staleness."""
    _seed_submission(app, tmp_path)
    try:
        response = client.get(f"/infos/{SUB_HASH}")
        assert response.headers["Cache-Control"] == "private, max-age=30"
    finally:
        _cleanup_results()


def test_images_cache_forever(app: Flask, client: FlaskClient, tmp_path: Path) -> None:
    """Content-addressed image URLs are immutable."""
    _seed_submission(app, tmp_path)
    try:
        response = client.get(f"/image/{IMG_HASH}.png")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    finally:
        _cleanup_results()
