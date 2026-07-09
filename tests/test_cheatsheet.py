"""Tests for the standalone cheatsheet and the interactive decision-tree map."""

import json

from flask.testing import FlaskClient

# Inbound #png/#jpg/... links must keep working after moving out of the wiki.
CHEATSHEET_ANCHORS = [
    "triage",
    "image",
    "png",
    "jpg",
    "gif",
    "audio",
    "text",
    "polyglot",
    "tell-tool",
    "stuck",
    "more",
]


def test_cheatsheet_page_renders(client: FlaskClient) -> None:
    """The cheatsheet renders standalone (no wiki sidebar) with SEO metadata."""
    response = client.get("/cheatsheet")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="cheatsheet"' in html
    assert 'rel="canonical" href="http://localhost/cheatsheet"' in html
    assert "TechArticle" in html
    # It links to the interactive map, not to the raw SVG.
    assert "/cheatsheet/map" in html
    assert "decision-map-cta" in html
    # It is standalone: no wiki left-sidebar / search box.
    assert 'id="wiki-search"' not in html


def test_cheatsheet_preserves_legacy_anchors(client: FlaskClient) -> None:
    """Inbound #png/#jpg/... links must keep working after the migration."""
    html = client.get("/cheatsheet").get_data(as_text=True)
    for anchor in CHEATSHEET_ANCHORS:
        assert f'id="{anchor}"' in html, f"missing anchor {anchor}"


def test_cheatsheet_disables_animated_background(client: FlaskClient) -> None:
    """The cheatsheet skips the Three.js background for Core Web Vitals."""
    html = client.get("/cheatsheet").get_data(as_text=True)
    assert "three-bg" not in html
    assert "background.js" not in html


def test_cheatsheet_fallback_is_noindex(client: FlaskClient) -> None:
    """A prefixed language falls back to English and canonicalizes to it."""
    response = client.get("/fr/cheatsheet")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="robots" content="noindex"' in html
    assert 'rel="canonical" href="http://localhost/cheatsheet"' in html


def test_map_page_renders(client: FlaskClient) -> None:
    """The map page inlines the interactive SVG, its data, and export tooling."""
    response = client.get("/cheatsheet/map")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "decision-tree-svg" in html  # the inlined SVG
    assert 'class="ds-step"' in html  # interactive step overlays
    assert 'id="ds-data"' in html  # the tooltip data model
    assert "decision_map.js" in html
    assert "jspdf" in html  # the PDF export library
    assert 'id="ds-dl-png"' in html
    assert 'id="ds-dl-pdf"' in html
    # The map owns the whole viewport: no site footer chrome.
    assert "buymeacoffee" not in html


def test_map_data_is_valid_json(client: FlaskClient) -> None:
    """The inlined #ds-data payload parses and carries the branch model."""
    html = client.get("/cheatsheet/map").get_data(as_text=True)
    marker = '<script type="application/json" id="ds-data">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    data = json.loads(html[start:end])
    assert data["root"]["title"]
    assert len(data["branches"]) >= 5
    first = data["branches"][0]["steps"][0]
    assert first["cmd"]
    assert first["full"]
    assert first["href"]


def test_wiki_cheatsheet_redirects(client: FlaskClient) -> None:
    """The legacy /wiki/cheatsheet URL 301s to the standalone page, per language."""
    response = client.get("/wiki/cheatsheet")
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/cheatsheet")
    localized = client.get("/fr/wiki/cheatsheet")
    assert localized.status_code == 301
    assert localized.headers["Location"].endswith("/fr/cheatsheet")
    # The per-medium checklists under the folder still resolve.
    assert client.get("/wiki/cheatsheet/image").status_code == 200


def test_faq_redirects_to_cheatsheet(client: FlaskClient) -> None:
    """The legacy /faq URL 301s to the cheatsheet."""
    response = client.get("/faq")
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/cheatsheet")


def test_cheatsheet_in_sitemap(client: FlaskClient) -> None:
    """The standalone cheatsheet is indexable; the old wiki URL is gone."""
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/cheatsheet</loc>" in xml
    assert "/wiki/cheatsheet</loc>" not in xml
