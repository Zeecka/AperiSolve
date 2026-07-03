"""Tests for internationalized routing, locale selection and wiki fallback."""

from flask.testing import FlaskClient

from aperisolve.i18n import SUPPORTED_LANGS


def test_language_prefixes_render_translated(client: FlaskClient) -> None:
    """Every prefixed language serves a translated index page."""
    samples = {
        "/fr/": "Analyser l'image",
        "/es/": "Analizar imagen",
        "/de/": "Bild analysieren",
        "/ru/": "Анализировать изображение",
        "/zh/": "分析图片",
        "/pt/": "Analisar imagem",
    }
    for path, needle in samples.items():
        html = client.get(path).get_data(as_text=True)
        assert needle in html, f"{path} not translated"
        assert f'lang="{path.strip("/")}"' in html


def test_unsupported_language_prefix_is_404(client: FlaskClient) -> None:
    """Unknown prefixes are not swallowed by the language converter."""
    assert client.get("/xx/").status_code == 404


def test_hreflang_alternates_on_index(client: FlaskClient) -> None:
    """The index links every language version plus x-default."""
    html = client.get("/").get_data(as_text=True)
    for lang in SUPPORTED_LANGS:
        assert f'hreflang="{lang}"' in html
    assert 'hreflang="x-default"' in html


def test_wiki_fallback_canonicalizes_to_english(client: FlaskClient) -> None:
    """Untranslated wiki pages show English, noindex, and EN canonical."""
    response = client.get("/de/wiki/cheatsheet")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="canonical" href="http://localhost/wiki/cheatsheet"' in html
    assert '<meta name="robots" content="noindex">' in html


def test_translated_wiki_page_is_self_canonical(client: FlaskClient) -> None:
    """A real translation (fr wiki index) canonicalizes to its own URL."""
    html = client.get("/fr/wiki/").get_data(as_text=True)
    assert 'rel="canonical" href="http://localhost/fr/wiki/"' in html
    assert "Bienvenue sur le wiki" in html


def test_sitemap_lists_only_real_translations(client: FlaskClient) -> None:
    """Language URLs appear in the sitemap only when content exists."""
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/fr/</loc>" in xml
    assert "/fr/wiki/</loc>" in xml  # translated
    assert "/fr/wiki/cheatsheet" not in xml  # fallback only
    assert "/de/wiki/cheatsheet" not in xml


def test_locale_cookie_beats_accept_language(client: FlaskClient) -> None:
    """Cookie preference wins over the Accept-Language header."""
    client.set_cookie("lang", "ru")
    html = client.get("/", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert "Анализировать изображение" in html


def test_js_catalog_injected(client: FlaskClient) -> None:
    """window.I18N carries the translated client-side strings."""
    html = client.get("/fr/").get_data(as_text=True)
    assert "window.I18N" in html
    assert "Premier envoi" in html
