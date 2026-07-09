"""Markdown-driven wiki.

Pages live in ``aperisolve/wiki_content/<lang>/<slug>.md`` with python-markdown
``meta`` frontmatter (``Title:``, ``Description:``, ``Order:``). Rendered HTML
is cached in-process; contributors add a page by dropping a markdown file.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import TypedDict

import markdown
from flask import Blueprint, Response, abort, g, redirect, render_template
from flask_babel import gettext as _
from werkzeug.wrappers.response import Response as WerkzeugResponse

from .config import FLASK_DEBUG
from .i18n import DEFAULT_LANG, PREFIX_LANGS, alternates_for, lang_prefix, register_lang_handling

WIKI_CONTENT_DIR = Path(__file__).parent.resolve() / "wiki_content"
MARKDOWN_EXTENSIONS = [
    "meta",
    "toc",
    "attr_list",
    "fenced_code",
    "codehilite",
    "tables",
    "admonition",
]
# ``permalink`` adds a clickable ¶ anchor to every heading (the h1 anchor is
# hidden by CSS); ``toc_depth`` only limits the generated right-rail TOC list to
# h2/h3. Do not set ``permalink_title`` here — it would need gettext at import
# time, before an app/request context exists.
MARKDOWN_EXTENSION_CONFIGS = {
    "toc": {
        "permalink": True,
        "permalink_class": "headerlink",
        "toc_depth": "2-3",
    },
}

# Sidebar sections, in display order, keyed by the top-level path segment of a
# page slug ("" is the group of top-level pages: index, getting-started, ...).
# A page under ``techniques/images`` lands in the ``techniques`` section.
SECTION_ORDER = ["", "cheatsheet", "techniques", "tools"]

wiki_bp = Blueprint("wiki", __name__)
register_lang_handling(wiki_bp)


@dataclass(frozen=True)
class WikiPage:
    """A rendered wiki page."""

    slug: str
    title: str
    description: str
    order: int
    html: str
    toc_html: str = ""
    headings: tuple[tuple[str, str], ...] = ()
    nav_title: str = ""

    @property
    def path(self) -> str:
        """URL path of the page."""
        return "/wiki/" if self.slug == "index" else f"/wiki/{self.slug}"


_page_cache: dict[tuple[str, str], WikiPage] = {}

# Search index cache, keyed by language, mirroring ``_page_cache`` (both are
# bypassed when ``FLASK_DEBUG`` so edits show up live).
_search_cache: dict[str, str] = {}
_TAG_RE = re.compile(r"<[^>]+>")
_SEARCH_BODY_CHARS = 4000


def _flatten_toc(tokens: list[dict]) -> tuple[tuple[str, str], ...]:
    """Flatten nested ``toc_tokens`` into ordered ``(anchor_id, title)`` pairs."""
    out: list[tuple[str, str]] = []

    def walk(items: list[dict]) -> None:
        for item in items:
            out.append((item["id"], item["name"]))
            walk(item.get("children", []))

    walk(tokens)
    return tuple(out)


def _resolve_page_file(lang: str, slug: str) -> Path | None:
    """Resolve a slug to a markdown file, refusing path traversal."""
    if ".." in slug.split("/") or slug.startswith("/"):
        return None
    root = (WIKI_CONTENT_DIR / lang).resolve()
    candidate = (root / f"{slug}.md").resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


def load_page(lang: str, slug: str) -> WikiPage | None:
    """Load and render a wiki page, using the in-process cache."""
    cache_key = (lang, slug)
    if not FLASK_DEBUG and cache_key in _page_cache:
        return _page_cache[cache_key]

    page_file = _resolve_page_file(lang, slug)
    if page_file is None:
        return None

    md = markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    html = md.convert(page_file.read_text(encoding="utf-8"))
    meta: dict[str, list[str]] = getattr(md, "Meta", {})
    toc_tokens = getattr(md, "toc_tokens", [])

    def meta_value(key: str, default: str = "") -> str:
        values = meta.get(key, [])
        return values[0] if values else default

    title = meta_value("title", slug.rsplit("/", maxsplit=1)[-1].replace("-", " ").title())
    # Sidebar label: an explicit ``NavTitle`` wins; otherwise drop the SEO tail
    # after the first " - " so the menu stays scannable.
    nav_title = meta_value("navtitle") or title.split(" - ", 1)[0].strip()
    page = WikiPage(
        slug=slug,
        title=title,
        description=meta_value("description"),
        order=int(meta_value("order", "1000")),
        html=html,
        # ``md.toc`` (added by the toc extension) is an empty
        # ``<div class="toc"><ul></ul></div>`` when the page has no h2/h3; gate
        # on the tokens so such pages render no rail.
        toc_html=getattr(md, "toc", "") if toc_tokens else "",
        headings=_flatten_toc(toc_tokens),
        nav_title=nav_title,
    )
    _page_cache[cache_key] = page
    return page


def wiki_tool_names() -> set[str]:
    """Analyzer names that have a ``tools/<name>`` wiki page (English source).

    Used to link analyzer result headings to their guide. Cheap directory
    listing (no markdown rendering), so it is safe to call per request.
    """
    tools_dir = WIKI_CONTENT_DIR / DEFAULT_LANG / "tools"
    if not tools_dir.is_dir():
        return set()
    return {path.stem for path in tools_dir.glob("*.md")}


def wiki_pages(lang: str = DEFAULT_LANG) -> list[WikiPage]:
    """All wiki pages of a language, sorted by ``Order`` then title."""
    root = WIKI_CONTENT_DIR / lang
    if not root.is_dir():
        return []
    pages = []
    for md_file in sorted(root.rglob("*.md")):
        slug = md_file.relative_to(root).with_suffix("").as_posix()
        page = load_page(lang, slug)
        if page is not None:
            pages.append(page)
    return sorted(pages, key=lambda page: (page.order, page.title))


def _strip_html(html_text: str) -> str:
    """Plain-text body of a rendered page, for the search index.

    Codehilite/fenced output escapes literal ``<``/``>`` to entities, so the
    tag regex only strips real markup; ``unescape`` then restores the text.
    """
    text = _TAG_RE.sub(" ", html_text)
    return " ".join(unescape(text).split())


def _search_index(lang: str) -> list[dict]:
    """Search documents for a language, following the English fallback.

    Paths are bare (``/wiki/...``); the client prepends the language prefix,
    matching the ``WIKI_TOOLS`` / ``LANG_PREFIX`` convention.
    """
    docs = []
    for en_page in wiki_pages(DEFAULT_LANG):
        page = en_page if lang == DEFAULT_LANG else (load_page(lang, en_page.slug) or en_page)
        docs.append(
            {
                "path": page.path,
                "title": page.title,
                "description": page.description,
                "text": _strip_html(page.html)[:_SEARCH_BODY_CHARS],
                "headings": [{"id": hid, "title": title} for hid, title in page.headings],
            },
        )
    return docs


def translated_langs(slug: str) -> list[str]:
    """Prefix languages that have a real translation of a page."""
    return [lang for lang in PREFIX_LANGS if _resolve_page_file(lang, slug) is not None]


def page_lastmod(lang: str, slug: str) -> str | None:
    """ISO date of a page's source-file modification time, for the sitemap."""
    path = _resolve_page_file(lang, slug)
    if path is None:
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date().isoformat()


def _wiki_nav(lang: str) -> list[WikiPage]:
    """Sidebar pages in the English order, using translated titles if available."""
    nav = []
    for en_page in wiki_pages(DEFAULT_LANG):
        localized = load_page(lang, en_page.slug) if lang != DEFAULT_LANG else None
        nav.append(localized or en_page)
    return nav


class NavGroup(TypedDict):
    """A titled sidebar section and its pages."""

    label: str
    pages: list[WikiPage]


def _section_label(segment: str) -> str:
    """Localized sidebar heading for a top-level content section."""
    labels = {
        "": _("Wiki"),
        "cheatsheet": _("Cheatsheet"),
        "techniques": _("Techniques"),
        "tools": _("Tools"),
    }
    return labels.get(segment) or segment.replace("-", " ").title()


def _nav_groups(nav: list[WikiPage]) -> list[NavGroup]:
    """Group sidebar pages by their top-level path segment, in section order.

    Pages keep the English ordering they arrive in (from ``_wiki_nav``); only
    the sections themselves are ordered, so dropping a markdown file into a new
    top-level folder adds a sidebar section without touching this code.
    """
    groups: dict[str, list[WikiPage]] = {}
    for page in nav:
        segment = page.slug.split("/", 1)[0] if "/" in page.slug else ""
        groups.setdefault(segment, []).append(page)

    def order_key(segment: str) -> tuple[int, str]:
        rank = SECTION_ORDER.index(segment) if segment in SECTION_ORDER else len(SECTION_ORDER)
        return (rank, segment)

    return [
        {"label": _section_label(segment), "pages": groups[segment]}
        for segment in sorted(groups, key=order_key)
    ]


def _render(slug: str) -> str:
    lang = g.get("lang_code") or DEFAULT_LANG
    page = load_page(lang, slug)
    is_fallback = False
    if page is None and lang != DEFAULT_LANG:
        page = load_page(DEFAULT_LANG, slug)
        is_fallback = True
    if page is None:
        abort(404)

    if lang == DEFAULT_LANG:
        canonical_path = page.path
        alternates = alternates_for(page.path, [DEFAULT_LANG, *translated_langs(slug)])
    elif is_fallback:
        # Untranslated fallback pages canonicalize to the English URL and
        # carry no hreflang, avoiding duplicate-content penalties.
        canonical_path = page.path
        alternates = None
    else:
        canonical_path = f"/{lang}{page.path}"
        alternates = alternates_for(page.path, [DEFAULT_LANG, *translated_langs(slug)])

    nav = _wiki_nav(lang)
    idx = next((i for i, nav_page in enumerate(nav) if nav_page.slug == page.slug), None)
    prev_page = nav[idx - 1] if idx not in (None, 0) else None
    next_page = nav[idx + 1] if idx is not None and idx < len(nav) - 1 else None

    return render_template(
        "wiki.html",
        page=page,
        is_fallback=is_fallback,
        canonical_path=canonical_path,
        alternates=alternates,
        nav_groups=_nav_groups(nav),
        prev_page=prev_page,
        next_page=next_page,
    )


@wiki_bp.route("/wiki/")
def wiki_index() -> str:
    """Render the wiki landing page."""
    return _render("index")


@wiki_bp.route("/wiki/search.json")
def wiki_search() -> Response:
    """Search index for the active language (bare paths; client adds prefix).

    Static rule, so Werkzeug ranks it above the ``<path:slug>`` converter.
    """
    lang = g.get("lang_code") or DEFAULT_LANG
    if FLASK_DEBUG or lang not in _search_cache:
        _search_cache[lang] = json.dumps({"pages": _search_index(lang)}, ensure_ascii=False)
    return Response(_search_cache[lang], mimetype="application/json")


@wiki_bp.route("/wiki/cheatsheet")
def wiki_cheatsheet_redirect() -> WerkzeugResponse:
    """Redirect the legacy /wiki/cheatsheet URL to the standalone cheatsheet.

    Static rule, so Werkzeug ranks it above the ``<path:slug>`` converter; the
    per-medium checklists under ``/wiki/cheatsheet/<name>`` still resolve there.
    """
    return redirect(f"{lang_prefix()}/cheatsheet", code=301)


@wiki_bp.route("/wiki/<path:slug>")
def wiki_page(slug: str) -> str:
    """Render a wiki page by slug."""
    return _render(slug)
