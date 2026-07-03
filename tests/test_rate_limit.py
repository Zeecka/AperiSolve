"""Tests for per-route rate limiting."""

from flask.testing import FlaskClient

UPLOAD_LIMIT_PER_MINUTE = 10


def test_upload_rate_limited_with_json_429(client: FlaskClient) -> None:
    """Uploads beyond the per-minute limit get the frontend's JSON error shape."""
    env = {"REMOTE_ADDR": "203.0.113.10"}
    codes = [
        client.post("/upload", environ_base=env).status_code
        for _ in range(UPLOAD_LIMIT_PER_MINUTE + 1)
    ]
    assert codes[:UPLOAD_LIMIT_PER_MINUTE] == [400] * UPLOAD_LIMIT_PER_MINUTE  # "No image provided"
    assert codes[UPLOAD_LIMIT_PER_MINUTE] == 429

    response = client.post("/upload", environ_base=env)
    assert response.status_code == 429
    assert "error" in response.get_json()


def test_localhost_is_exempt(client: FlaskClient) -> None:
    """The compose healthcheck uploads from loopback and must never be limited."""
    codes = [client.post("/upload").status_code for _ in range(UPLOAD_LIMIT_PER_MINUTE + 5)]
    assert 429 not in codes


def test_pages_are_never_limited(client: FlaskClient) -> None:
    """Only expensive endpoints are limited; pages stay unthrottled."""
    env = {"REMOTE_ADDR": "203.0.113.11"}
    codes = {client.get("/", environ_base=env).status_code for _ in range(30)}
    assert codes == {200}


def test_remove_rate_limited(client: FlaskClient) -> None:
    """Removal endpoints are limited to 5/minute."""
    env = {"REMOTE_ADDR": "203.0.113.12"}
    codes = [client.post(f"/remove/{'c' * 32}", environ_base=env).status_code for _ in range(6)]
    assert codes[:5] == [404] * 5
    assert codes[5] == 429
