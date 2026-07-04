"""Tests for the request-size limit on uploads."""

import io

from flask.testing import FlaskClient

from aperisolve.config import MAX_CONTENT_LENGTH


def test_oversized_upload_returns_413_json(client: FlaskClient) -> None:
    """A body larger than MAX_CONTENT_LENGTH yields the JSON 413 shape."""
    payload = b"x" * (MAX_CONTENT_LENGTH + 4096)
    response = client.post(
        "/upload",
        data={"image": (io.BytesIO(payload), "big.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    assert "error" in response.get_json()
