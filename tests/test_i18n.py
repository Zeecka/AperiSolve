"""Tests for internationalized routing, locale selection and wiki fallback."""

from flask.testing import FlaskClient

from aperisolve.i18n import SUPPORTED_LANGS


def test_language_prefixes_render_translated(client: FlaskClient) -> None:
    """Every prefixed language serves a translated index page."""
    # "What is this?" is a stable index-page heading that stays translated
    # regardless of copy churn on the upload controls (which now say "file").
    samples = {
        "/fr/": "Qu'est-ce que c'est ?",
        "/es/": "¿Qué es esto?",
        "/de/": "Was ist das?",
        "/ru/": "Что это?",
        "/zh/": "这是什么",
        "/pt/": "O que é isto?",
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
    response = client.get("/de/wiki/tools/zsteg")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="canonical" href="http://localhost/wiki/tools/zsteg"' in html
    assert '<meta name="robots" content="noindex">' in html


def test_wiki_index_falls_back_for_prefixed_lang(client: FlaskClient) -> None:
    """Wiki content is English-only; a language prefix falls back to English."""
    response = client.get("/fr/wiki/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'rel="canonical" href="http://localhost/wiki/"' in html
    assert '<meta name="robots" content="noindex">' in html


def test_sitemap_lists_only_real_translations(client: FlaskClient) -> None:
    """Language URLs appear in the sitemap only when content exists."""
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/fr/</loc>" in xml  # app home is translated (gettext UI strings)
    # The wiki is English-only: fallback-only language URLs stay out.
    assert "/fr/wiki/</loc>" not in xml
    assert "/fr/wiki/cheatsheet</loc>" not in xml
    assert "/fr/wiki/tools/zsteg" not in xml
    assert "/de/wiki/tools/zsteg" not in xml


def test_locale_cookie_beats_accept_language(client: FlaskClient) -> None:
    """Cookie preference wins over the Accept-Language header."""
    client.set_cookie("lang", "ru")
    html = client.get("/", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert "Что это?" in html


def test_js_catalog_injected(client: FlaskClient) -> None:
    """window.I18N carries the translated client-side strings."""
    html = client.get("/fr/").get_data(as_text=True)
    assert "window.I18N" in html
    assert "Premier envoi" in html
