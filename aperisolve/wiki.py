"""Markdown-driven wiki.

Pages live in ``aperisolve/wiki_content/<lang>/<slug>.md`` with python-markdown
``meta`` frontmatter (``Title:``, ``Description:``, ``Order:``). Rendered HTML
is cached in-process; contributors add a page by dropping a markdown file.
"""

from dataclasses import dataclass
from pathlib import Path

import markdown
from flask import Blueprint, abort, render_template

from .config import FLASK_DEBUG

WIKI_CONTENT_DIR = Path(__file__).parent.resolve() / "wiki_content"
DEFAULT_LANG = "en"
MARKDOWN_EXTENSIONS = ["meta", "toc", "attr_list", "fenced_code", "codehilite", "tables"]

wiki_bp = Blueprint("wiki", __name__)


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


def _render(slug: str) -> str:
    page = load_page(DEFAULT_LANG, slug)
    if page is None:
        abort(404)
    pages = wiki_pages()
    return render_template(
        "wiki.html",
        page=page,
        nav_main=[p for p in pages if "/" not in p.slug],
        nav_tools=[p for p in pages if p.slug.startswith("tools/")],
    )


@wiki_bp.route("/wiki/")
def wiki_index() -> str:
    """Render the wiki landing page."""
    return _render("index")


@wiki_bp.route("/wiki/<path:slug>")
def wiki_page(slug: str) -> str:
    """Render a wiki page by slug."""
    return _render(slug)
