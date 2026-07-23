"""Result-page and browse-gallery previews for video and audio uploads.

The upload can be any file type; these tests confirm the web layer classifies
video/audio submissions and renders a playable ``<video>``/``<audio>`` element
rather than a bare download card.
"""

import time
from pathlib import Path

from flask import Flask
from flask.testing import FlaskClient

from aperisolve.models import Image, Submission, db

VIDEO_IMG_HASH = "1" * 32
VIDEO_SUB_HASH = "2" * 32
AUDIO_IMG_HASH = "3" * 32
AUDIO_SUB_HASH = "4" * 32


def _seed(app: Flask, tmp_path: Path, *, img_hash: str, sub_hash: str, filename: str) -> None:
    """Insert an Image + Submission whose stored file keeps ``filename``'s suffix.

    The bytes are irrelevant to preview routing (kind is derived from the
    extension when the content is unrecognised), so a tiny placeholder suffices.
    """
    stored = tmp_path / f"{img_hash}{Path(filename).suffix}"
    stored.write_bytes(b"\x00\x01\x02\x03")
    with app.app_context():
        db.session.add(
            Image(hash=img_hash, file=str(stored), size=stored.stat().st_size, upload_count=1),
        )
        db.session.add(
            Submission(
                hash=sub_hash,
                filename=filename,
                status="completed",
                date=time.time(),
                image_hash=img_hash,
            ),
        )
        db.session.commit()


def test_infos_reports_video_kind(app: Flask, client: FlaskClient, tmp_path: Path) -> None:
    """A video upload is reported as kind 'video' with a video/* MIME."""
    _seed(app, tmp_path, img_hash=VIDEO_IMG_HASH, sub_hash=VIDEO_SUB_HASH, filename="clip.mp4")
    data = client.get(f"/infos/{VIDEO_SUB_HASH}").get_json()
    assert data["kind"] == "video", data
    assert data["mime"].startswith("video/"), data


def test_infos_reports_audio_kind(app: Flask, client: FlaskClient, tmp_path: Path) -> None:
    """An audio upload is reported as kind 'audio'."""
    _seed(app, tmp_path, img_hash=AUDIO_IMG_HASH, sub_hash=AUDIO_SUB_HASH, filename="track.mp3")
    data = client.get(f"/infos/{AUDIO_SUB_HASH}").get_json()
    assert data["kind"] == "audio", data


def test_show_renders_video_and_audio_players(
    app: Flask,
    client: FlaskClient,
    tmp_path: Path,
) -> None:
    """The browse gallery emits playable <video>/<audio> elements for media rows."""
    _seed(app, tmp_path, img_hash=VIDEO_IMG_HASH, sub_hash=VIDEO_SUB_HASH, filename="clip.webm")
    _seed(app, tmp_path, img_hash=AUDIO_IMG_HASH, sub_hash=AUDIO_SUB_HASH, filename="track.wav")
    html = client.get("/show").get_data(as_text=True)
    assert "<video" in html
    assert "<audio" in html
    # Each media element sources the original-file route for its own image hash.
    assert f"/image/{VIDEO_IMG_HASH}" in html
    assert f"/image/{AUDIO_IMG_HASH}" in html
