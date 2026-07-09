"""Standalone steganography cheatsheet and full-screen decision-tree map.

The cheatsheet used to be a wiki page; it now lives here as its own page (with no
wiki sidebar) plus a near-fullscreen interactive map at ``/cheatsheet/map``.

The landing page renders markdown from ``cheatsheet_content/<lang>/cheatsheet.md``
(English fallback), reusing the wiki's markdown pipeline. The map page inlines the
committed decision-tree SVG — so hover, keyboard-focus and export handlers can
attach to it — together with its JSON model (the tooltip text). Both artifacts
are produced by ``scripts/gen_decision_tree.py``.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import markdown
from flask import Blueprint, abort, g, render_template

from .config import FLASK_DEBUG
from .i18n import DEFAULT_LANG, alternates_for, register_lang_handling
from .wiki import MARKDOWN_EXTENSION_CONFIGS, MARKDOWN_EXTENSIONS

CONTENT_DIR = Path(__file__).parent.resolve() / "cheatsheet_content"
ASSET_DIR = Path(__file__).parent.resolve() / "static" / "img" / "cheatsheet"
SVG_FILE = ASSET_DIR / "decision-tree.svg"
DATA_FILE = ASSET_DIR / "decision-tree.json"

cheatsheet_bp = Blueprint("cheatsheet", __name__)
register_lang_handling(cheatsheet_bp)


@dataclass(frozen=True)
class CheatsheetPage:
    """A rendered cheatsheet page."""

    title: str
    description: str
    html: str
    toc_html: str = ""


_page_cache: dict[str, CheatsheetPage] = {}
_asset_cache: dict[str, str] = {}


def _content_file(lang: str) -> Path | None:
    """Resolve the cheatsheet markdown for a language, or ``None``."""
    candidate = CONTENT_DIR / lang / "cheatsheet.md"
    return candidate if candidate.is_file() else None


def _load(lang: str) -> tuple[CheatsheetPage, bool]:
    """Render the cheatsheet for a language, following the English fallback."""
    path = _content_file(lang)
    is_fallback = False
    if path is None:
        path = _content_file(DEFAULT_LANG)
        is_fallback = lang != DEFAULT_LANG
    if path is None:
        abort(404)

    cache_key = path.as_posix()
    if not FLASK_DEBUG and cache_key in _page_cache:
        return _page_cache[cache_key], is_fallback

    md = markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    body = md.convert(path.read_text(encoding="utf-8"))
    meta: dict[str, list[str]] = getattr(md, "Meta", {})
    toc_tokens = getattr(md, "toc_tokens", [])

    def meta_value(key: str, default: str = "") -> str:
        values = meta.get(key, [])
        return values[0] if values else default

    page = CheatsheetPage(
        title=meta_value("title", "Cheatsheet"),
        description=meta_value("description"),
        html=body,
        toc_html=getattr(md, "toc", "") if toc_tokens else "",
    )
    _page_cache[cache_key] = page
    return page, is_fallback


def _asset(name: str, path: Path) -> str:
    """Read a committed decision-tree asset, cached in-process."""
    if not FLASK_DEBUG and name in _asset_cache:
        return _asset_cache[name]
    text = path.read_text(encoding="utf-8")
    _asset_cache[name] = text
    return text


def cheatsheet_lastmod() -> str | None:
    """ISO date of the English source's modification time, for the sitemap."""
    path = _content_file(DEFAULT_LANG)
    if path is None:
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date().isoformat()


@cheatsheet_bp.route("/cheatsheet")
def cheatsheet() -> str:
    """Render the standalone cheatsheet landing page."""
    lang = g.get("lang_code") or DEFAULT_LANG
    page, is_fallback = _load(lang)
    # Untranslated languages fall back to English and canonicalize to the
    # English URL with no hreflang, avoiding duplicate-content penalties.
    alternates = alternates_for("/cheatsheet", [DEFAULT_LANG]) if not is_fallback else None
    return render_template(
        "cheatsheet.html",
        page=page,
        is_fallback=is_fallback,
        canonical_path="/cheatsheet",
        alternates=alternates,
    )


@cheatsheet_bp.route("/cheatsheet/map")
def cheatsheet_map() -> str:
    """Render the near-fullscreen interactive decision-tree map."""
    lang = g.get("lang_code") or DEFAULT_LANG
    is_fallback = lang != DEFAULT_LANG
    return render_template(
        "map.html",
        svg_markup=_asset("svg", SVG_FILE),
        data_json=_asset("data", DATA_FILE),
        is_fallback=is_fallback,
        canonical_path="/cheatsheet/map",
        alternates=None,
    )
