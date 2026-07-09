"""Tests for the markdown wiki."""

import json

from flask.testing import FlaskClient

from aperisolve.analyzers.registry import discover_analyzers
from aperisolve.wiki import load_page, wiki_pages, wiki_tool_names


def test_wiki_index_renders(client: FlaskClient) -> None:
    """The wiki landing page lists the tool guides."""
    response = client.get("/wiki/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Aperi'Solve Wiki" in html
    assert "/wiki/tools/zsteg" in html


def test_wiki_page_has_seo_meta(client: FlaskClient) -> None:
    """Wiki pages carry canonical URL and structured data."""
    response = client.get("/wiki/tools/zsteg")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="canonical"' in html
    assert "TechArticle" in html
    assert "BreadcrumbList" in html


def test_technique_page_renders(client: FlaskClient) -> None:
    """A nested techniques/ page renders with SEO metadata."""
    response = client.get("/wiki/techniques/images")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="canonical"' in html
    assert "TechArticle" in html


def test_sidebar_shows_section_groups(client: FlaskClient) -> None:
    """The folder-driven sidebar renders the top-level sections."""
    html = client.get("/wiki/").get_data(as_text=True)
    for heading in ("Wiki", "Cheatsheet", "Techniques", "Tools"):
        assert f">{heading}</h2>" in html, f"missing sidebar section {heading}"


def test_cheatsheet_section_and_deep_pages(client: FlaskClient) -> None:
    """The per-medium checklist split renders as its own sidebar section."""
    html = client.get("/wiki/cheatsheet/image").get_data(as_text=True)
    assert ">Cheatsheet</h2>" in html  # the folder-driven sidebar section
    assert client.get("/wiki/cheatsheet/image").status_code == 200
    assert client.get("/wiki/cheatsheet/network").status_code == 200
    assert client.get("/wiki/cheatsheet/brute-force").status_code == 200


def test_wiki_page_disables_animated_background(client: FlaskClient) -> None:
    """Content pages skip the Three.js background for Core Web Vitals."""
    html = client.get("/wiki/methodology").get_data(as_text=True)
    assert "three-bg" not in html
    assert "background.js" not in html


def test_unknown_page_is_404(client: FlaskClient) -> None:
    """Unknown slugs return a real 404."""
    assert client.get("/wiki/no-such-page").status_code == 404


def test_path_traversal_is_rejected() -> None:
    """Slugs cannot escape the content root."""
    assert load_page("en", "../en/index") is None
    assert load_page("en", "../../config") is None


def test_sitemap_lists_wiki_pages(client: FlaskClient) -> None:
    """Every wiki page is in the sitemap."""
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    for page in wiki_pages():
        assert page.path in xml


def test_no_ads_rendered_by_default(client: FlaskClient) -> None:
    """Self-hosted instances (no ADSENSE_* env) render no ad units."""
    html = client.get("/wiki/tools/zsteg").get_data(as_text=True)
    assert "adsbygoogle" not in html


def test_wiki_heading_permalinks(client: FlaskClient) -> None:
    """Headings get clickable ¶ permalinks wired to their ids."""
    html = client.get("/wiki/techniques/images").get_data(as_text=True)
    assert 'class="headerlink"' in html


def test_wiki_toc_rail_rendered(client: FlaskClient) -> None:
    """Pages with h2/h3 render a sticky right-rail table of contents."""
    html = client.get("/wiki/techniques/images").get_data(as_text=True)
    assert 'class="wiki-toc"' in html
    assert 'class="toc"' in html  # python-markdown's generated TOC list


def test_wiki_prev_next_navigation(client: FlaskClient) -> None:
    """Interior pages get prev/next links; the first page has no prev."""
    interior = client.get("/wiki/methodology").get_data(as_text=True)
    assert 'rel="prev"' in interior
    assert 'rel="next"' in interior
    index = client.get("/wiki/").get_data(as_text=True)
    assert 'rel="prev"' not in index


def test_wiki_search_index(client: FlaskClient) -> None:
    """The search route serves a per-language JSON index with heading anchors."""
    response = client.get("/wiki/search.json")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    pages = json.loads(response.get_data(as_text=True))["pages"]
    assert any(page["path"] == "/wiki/tools/zsteg" for page in pages)
    # The standalone cheatsheet is no longer a wiki page, so it is not indexed.
    assert not any(page["path"] == "/wiki/cheatsheet" for page in pages)
    # The route is also mounted under the language prefix (English fallback).
    assert client.get("/fr/wiki/search.json").status_code == 200


def test_every_analyzer_has_a_tool_page() -> None:
    """Each analyzer Aperi'Solve runs must have a tools/ guide to link to."""
    analyzer_names = {cls.name for cls in discover_analyzers()}
    missing = analyzer_names - wiki_tool_names()
    assert not missing, f"analyzers without a tools/ wiki page: {sorted(missing)}"


def test_index_links_every_tool_page() -> None:
    """The hand-maintained tool list on the index must not drift from tools/."""
    index_html = load_page("en", "index").html
    for name in wiki_tool_names():
        assert f"/wiki/tools/{name}" in index_html, f"index.md is missing tools/{name}"
