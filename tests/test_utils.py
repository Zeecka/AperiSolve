"""Tests for the pure-Python helpers in ``aperisolve.utils.utils``."""

from flask import Flask

from aperisolve.utils.utils import (
    MAX_RESOLUTION_SIZE,
    get_client_ip,
    get_resolutions,
    get_valid_depth_color_pairs,
    int2hex,
    str2hex,
)

# PNG-valid (bit depth, color type) combinations, mirroring the tool's own map.
VALID_DEPTHS = {1, 2, 4, 8, 16}
VALID_COLORS = {0, 2, 3, 4, 6}


def test_str2hex_uppercases_and_encodes() -> None:
    """Bytes render as an uppercase, unprefixed hex string."""
    assert str2hex(b"\x00\xff\x10") == "00FF10"
    assert str2hex(b"") == ""


def test_int2hex_prefixes_and_uppercases() -> None:
    """Integers render as ``0x``-prefixed uppercase hex."""
    assert int2hex(0) == "0x0"
    assert int2hex(255) == "0xFF"
    assert int2hex(4096) == "0x1000"


def test_get_resolutions_are_sorted_unique_and_symmetric() -> None:
    """Resolutions come back sorted, deduplicated, in bounds, and orientation-symmetric."""
    res = get_resolutions()
    assert res  # non-empty
    assert res == sorted(res)
    assert len(res) == len(set(res))

    res_set = set(res)
    for w, h in res:
        assert w >= 1
        assert 1 <= h <= MAX_RESOLUTION_SIZE
        # Every resolution has its portrait/landscape mirror.
        assert (h, w) in res_set


def test_get_valid_depth_color_pairs_are_all_valid_and_unique() -> None:
    """Every yielded pair is a real PNG depth/color combo, with no duplicates."""
    pairs = list(get_valid_depth_color_pairs())
    assert pairs
    assert len(pairs) == len(set(pairs))

    for depth, color in pairs:
        assert depth in VALID_DEPTHS
        assert color in VALID_COLORS

    # Spot-check representative combinations across color types.
    assert (8, 2) in pairs  # 8-bit truecolor
    assert (1, 0) in pairs  # 1-bit grayscale
    assert (16, 6) in pairs  # 16-bit truecolor + alpha
    assert (16, 3) not in pairs  # palette tops out at 8-bit


def test_get_client_ip_takes_rightmost_forwarded_hop() -> None:
    """The closest-proxy (rightmost) X-Forwarded-For hop is the trusted one."""
    app = Flask(__name__)
    headers = {"X-Forwarded-For": "1.1.1.1, 2.2.2.2, 3.3.3.3"}
    with app.test_request_context(headers=headers):
        assert get_client_ip() == "3.3.3.3"


def test_get_client_ip_falls_back_to_remote_addr() -> None:
    """Without the forwarded header, the socket peer address is used."""
    app = Flask(__name__)
    with app.test_request_context(environ_base={"REMOTE_ADDR": "9.9.9.9"}):
        assert get_client_ip() == "9.9.9.9"


def test_get_client_ip_empty_when_nothing_available() -> None:
    """A missing peer address degrades to an empty string, never ``None``."""
    app = Flask(__name__)
    with app.test_request_context(environ_base={"REMOTE_ADDR": ""}):
        assert get_client_ip() == ""
