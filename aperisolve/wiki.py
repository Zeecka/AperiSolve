"""Markdown-driven wiki.

Pages live in ``aperisolve/wiki_content/<lang>/<slug>.md`` with python-markdown
``meta`` frontmatter (``Title:``, ``Description:``, ``Order:``). Rendered HTML
is cached in-process; contributors add a page by dropping a markdown file.
"""

from dataclasses import dataclass
from pathlib import Path

import markdown
from flask import Blueprint, abort, g, render_template

from .config import FLASK_DEBUG
from .i18n import DEFAULT_LANG, PREFIX_LANGS, alternates_for, register_lang_handling

WIKI_CONTENT_DIR = Path(__file__).parent.resolve() / "wiki_content"
MARKDOWN_EXTENSIONS = ["meta", "toc", "attr_list", "fenced_code", "codehilite", "tables"]

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

    @property
    def path(self) -> str:
        """URL path of the page."""
        return "/wiki/" if self.slug == "index" else f"/wiki/{self.slug}"


_page_cache: dict[tuple[str, str], WikiPage] = {}


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

    md = markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)
    html = md.convert(page_file.read_text(encoding="utf-8"))
    meta: dict[str, list[str]] = getattr(md, "Meta", {})

    def meta_value(key: str, default: str = "") -> str:
        values = meta.get(key, [])
        return values[0] if values else default

    page = WikiPage(
        slug=slug,
        title=meta_value("title", slug.rsplit("/", maxsplit=1)[-1].replace("-", " ").title()),
        description=meta_value("description"),
        order=int(meta_value("order", "1000")),
        html=html,
    )
    _page_cache[cache_key] = page
    return page


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


def translated_langs(slug: str) -> list[str]:
    """Prefix languages that have a real translation of a page."""
    return [lang for lang in PREFIX_LANGS if _resolve_page_file(lang, slug) is not None]


def _wiki_nav(lang: str) -> list[WikiPage]:
    """Sidebar pages in the English order, using translated titles if available."""
    nav = []
    for en_page in wiki_pages(DEFAULT_LANG):
        localized = load_page(lang, en_page.slug) if lang != DEFAULT_LANG else None
        nav.append(localized or en_page)
    return nav


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
    return render_template(
        "wiki.html",
        page=page,
        is_fallback=is_fallback,
        canonical_path=canonical_path,
        alternates=alternates,
        nav_main=[p for p in nav if "/" not in p.slug],
        nav_tools=[p for p in nav if p.slug.startswith("tools/")],
    )


@wiki_bp.route("/wiki/")
def wiki_index() -> str:
    """Render the wiki landing page."""
    return _render("index")


@wiki_bp.route("/wiki/<path:slug>")
def wiki_page(slug: str) -> str:
    """Render a wiki page by slug."""
    return _render(slug)
