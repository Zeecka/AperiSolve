"""Tests for deployment-local site content (the promo banner loader).

No promo content is committed today, so the repository state is the "nothing
deployed" one: every helper returns ``None`` and the templates render nothing.
That is also what a self-hosted image sees, since ``site_content/`` is excluded
from the Docker build context. The loader itself is exercised by pointing it at
a temporary directory, as the hosted deployment's bind mount would. The render
cache is keyed by source mtime, so a change of file (one temp dir to the next)
is picked up without shared state leaking between tests.
"""

import os
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from aperisolve import site_content
from aperisolve.site_content import promo_html


def test_no_promo_content_is_committed() -> None:
    """The repository ships no promo content, so nothing renders by default."""
    assert not site_content.PROMO_DIR.exists()
    assert promo_html("en") is None


def test_promo_html_reads_deployed_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Markdown dropped in the mounted directory renders to HTML."""
    promo_dir = tmp_path / "promo"
    promo_dir.mkdir()
    (promo_dir / "fr.md").write_text("Un [lien](https://example.com)", encoding="utf-8")
    monkeypatch.setattr(site_content, "PROMO_DIR", promo_dir)
    html = promo_html("fr")
    assert html is not None
    assert "<a " in html


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


def test_home_page_renders_promo(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The home page includes the promo banner when content is deployed."""
    promo_dir = tmp_path / "promo"
    promo_dir.mkdir()
    (promo_dir / "en.md").write_text("Deployed promo", encoding="utf-8")
    monkeypatch.setattr(site_content, "PROMO_DIR", promo_dir)
    html = client.get("/").get_data(as_text=True)
    assert "promo-banner" in html
    assert "Deployed promo" in html


def test_home_page_omits_promo_when_absent(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A self-hosted image (no site_content) renders no promo banner."""
    monkeypatch.setattr(site_content, "PROMO_DIR", tmp_path / "missing")
    html = client.get("/").get_data(as_text=True)
    assert "promo-banner" not in html
