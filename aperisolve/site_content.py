"""Deployment-local site content that is not shipped in the public image.

The ``aperisolve/site_content/`` directory is excluded from the Docker build
context (see ``.dockerignore``) and bind-mounted only on the hosted deployment
(``compose.prod.yml``). Self-hosted images therefore have no such directory, so
every helper here returns ``None`` and the templates render nothing.

Currently this backs a small promotional banner shown on the home and result
pages. Content is authored as Markdown in ``site_content/promo/<lang>.md`` with
an English fallback; the rendered HTML is cached per language and re-rendered
automatically when the source file's mtime changes, so editing the file on the
server takes effect on the next request without a restart.
"""

from pathlib import Path

import markdown

from .i18n import DEFAULT_LANG

SITE_CONTENT_DIR = Path(__file__).parent.resolve() / "site_content"
PROMO_DIR = SITE_CONTENT_DIR / "promo"

# lang -> (source mtime_ns, rendered html). Keyed so an edited file on the
# server is picked up on the next request without a restart.
_promo_cache: dict[str, tuple[int, str]] = {}


def _promo_source(lang: str) -> Path | None:
    """Return the promo Markdown file for ``lang``, falling back to English."""
    for candidate in (PROMO_DIR / f"{lang}.md", PROMO_DIR / f"{DEFAULT_LANG}.md"):
        if candidate.is_file():
            return candidate
    return None


def promo_html(lang: str) -> str | None:
    """Return rendered promo HTML for ``lang``, or ``None`` when none is deployed."""
    source = _promo_source(lang)
    if source is None:
        return None
    mtime = source.stat().st_mtime_ns
    cached = _promo_cache.get(lang)
    if cached is None or cached[0] != mtime:
        text = source.read_text(encoding="utf-8").strip()
        _promo_cache[lang] = (mtime, markdown.markdown(text) if text else "")
    return _promo_cache[lang][1] or None
