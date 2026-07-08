"""Tests for the markdown wiki."""

from flask.testing import FlaskClient

from aperisolve.wiki import load_page, wiki_pages

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
    """The folder-driven sidebar renders the three top-level sections."""
    html = client.get("/wiki/").get_data(as_text=True)
    for heading in ("Wiki", "Techniques", "Tools"):
        assert f">{heading}</h2>" in html, f"missing sidebar section {heading}"


def test_sidebar_shows_on_this_page(client: FlaskClient) -> None:
    """The active page renders its H2/H3 anchors as an 'on this page' sub-nav."""
    html = client.get("/wiki/cheatsheet").get_data(as_text=True)
    assert 'class="wiki-toc' in html
    assert 'href="#triage"' in html  # an H2 anchor of the active page
    assert 'href="#png"' in html  # a nested H3 anchor
    assert 'data-toc-id="triage"' in html
    # The active sidebar link is marked and highlighted.
    assert "nav-link px-0 active fw-bold" in html


def test_sidebar_on_this_page_only_for_active(client: FlaskClient) -> None:
    """Only the active page's headings are dumped into the sidebar."""
    html = client.get("/wiki/tools/zsteg").get_data(as_text=True)
    # #triage is a cheatsheet anchor; the cheatsheet is not the active page here.
    assert 'data-toc-id="triage"' not in html


def test_cheatsheet_section_and_deep_pages(client: FlaskClient) -> None:
    """The per-medium cheatsheet split renders as its own sidebar section."""
    html = client.get("/wiki/cheatsheet").get_data(as_text=True)
    assert ">Cheatsheet</h2>" in html  # the folder-driven sidebar section
    assert client.get("/wiki/cheatsheet/image").status_code == 200
    assert client.get("/wiki/cheatsheet/network").status_code == 200
    assert client.get("/wiki/cheatsheet/brute-force").status_code == 200


def test_wiki_page_disables_animated_background(client: FlaskClient) -> None:
    """Content pages skip the Three.js background for Core Web Vitals."""
    html = client.get("/wiki/cheatsheet").get_data(as_text=True)
    assert "three-bg" not in html
    assert "background.js" not in html


def test_cheatsheet_preserves_legacy_anchors(client: FlaskClient) -> None:
    """Inbound #png/#jpg/... links must keep working after the migration."""
    html = client.get("/wiki/cheatsheet").get_data(as_text=True)
    for anchor in CHEATSHEET_ANCHORS:
        assert f'id="{anchor}"' in html, f"missing anchor {anchor}"


def test_faq_redirects_permanently(client: FlaskClient) -> None:
    """The legacy /faq URL 301s to the cheatsheet."""
    response = client.get("/faq")
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/wiki/cheatsheet")


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
    html = client.get("/wiki/cheatsheet").get_data(as_text=True)
    assert "adsbygoogle" not in html
