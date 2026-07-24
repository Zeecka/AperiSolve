"""Tests for deployment-local site content (the promo banner).

The ``site_content/`` directory is committed but excluded from the Docker image;
on a self-hosted image the directory is absent and every helper returns ``None``
so the templates render nothing. These tests cover both states by pointing the
loader at a temporary directory. The render cache is keyed by source mtime, so a
change of file (real -> temp dir and back) is picked up without shared state
leaking between tests.
"""

import os
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from aperisolve import site_content
from aperisolve.i18n import SUPPORTED_LANGS
from aperisolve.site_content import promo_html


def test_promo_html_reads_committed_content() -> None:
    """The committed English promo renders to HTML."""
    html = promo_html("en")
    assert html is not None
    assert "VimLegends" in html
    assert "<a " in html


def test_promo_html_translated_for_every_language() -> None:
    """Every supported language ships its own committed promo (no fallback)."""
    for lang in SUPPORTED_LANGS:
        assert (site_content.PROMO_DIR / f"{lang}.md").is_file(), lang
        html = promo_html(lang)
        assert html is not None
        assert "VimLegends" in html
        assert "TmuxLegends" in html


def test_promo_html_falls_back_to_english(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A language without its own file falls back to the English promo."""
    promo_dir = tmp_path / "promo"
    promo_dir.mkdir()
    (promo_dir / "en.md").write_text("English promo", encoding="utf-8")
    monkeypatch.setattr(site_content, "PROMO_DIR", promo_dir)
    assert promo_html("de") == "<p>English promo</p>"


def test_promo_html_absent_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no content deployed (self-hosted image) the helper returns None."""
    monkeypatch.setattr(site_content, "PROMO_DIR", tmp_path / "missing")
    assert promo_html("en") is None


def test_promo_html_reflects_edits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Editing the source file is picked up without a restart (mtime-keyed cache)."""
    promo_dir = tmp_path / "promo"
    promo_dir.mkdir()
    source = promo_dir / "en.md"
    monkeypatch.setattr(site_content, "PROMO_DIR", promo_dir)

    source.write_text("First", encoding="utf-8")
    os.utime(source, ns=(1_000, 1_000))
    assert promo_html("en") == "<p>First</p>"

    # Bump mtime explicitly: same-second edits can otherwise share an mtime.
    source.write_text("Second", encoding="utf-8")
    os.utime(source, ns=(2_000, 2_000))
    assert promo_html("en") == "<p>Second</p>"


def test_home_page_renders_promo(client: FlaskClient) -> None:
    """The home page includes the promo banner when content is deployed."""
    html = client.get("/").get_data(as_text=True)
    assert "promo-banner" in html
    assert "VimLegends" in html


def test_home_page_omits_promo_when_absent(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A self-hosted image (no site_content) renders no promo banner."""
    monkeypatch.setattr(site_content, "PROMO_DIR", tmp_path / "missing")
    html = client.get("/").get_data(as_text=True)
    assert "promo-banner" not in html
