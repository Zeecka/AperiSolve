"""Translatable page routes, registered at the root and under /<lang>/."""

from pathlib import Path

from flask import Blueprint, render_template
from sqlalchemy.orm import selectinload

from .config import IMAGE_EXTENSIONS
from .i18n import alternates_for, register_lang_handling
from .limits import is_local_request, limiter
from .models import Image

pages_bp = Blueprint("pages", __name__)
register_lang_handling(pages_bp)

MAX_SHOW_IMAGES = 100

# Extensions the browse gallery previews inline. Uploads are classified cheaply
# by extension here (not via detect_file_type) to avoid a subprocess probe per
# gallery row; the values only pick a preview element, not analyzer gating.
_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".flac", ".ogg", ".m4a", ".au"})
_VIDEO_EXTENSIONS = frozenset(
    {".mp4", ".m4v", ".webm", ".avi", ".flv", ".mkv", ".mov", ".wmv", ".mpeg", ".mpg", ".ogv"},
)


def _file_icon(suffix: str) -> str:
    """Return the Font Awesome icon class for a non-image upload extension."""
    if suffix == ".pdf":
        return "fa-file-pdf"
    if suffix in _AUDIO_EXTENSIONS:
        return "fa-file-audio"
    if suffix in _VIDEO_EXTENSIONS:
        return "fa-file-video"
    return "fa-file"


@pages_bp.route("/")
def index() -> str:
    """Render the main index page."""
    return render_template("index.html", alternates=alternates_for("/"))


@pages_bp.route("/show")
@limiter.limit("30 per minute", exempt_when=is_local_request)
def show() -> str:
    """Show the most recent submissions (bounded: the table grows unbounded)."""
    db_images = (
        Image.query.options(selectinload(Image.submissions))  # one query, no N+1
        .order_by(Image.last_submission_date.desc())
        .limit(MAX_SHOW_IMAGES)
        .all()
    )
    images: list[dict[str, str]] = []
    for img in db_images:
        if not img.submissions:
            continue
        last_sub = img.submissions[-1]
        suffix = Path(str(img.file)).suffix.lower()
        row: dict[str, str] = {"file": f"/image/{img.hash}", "link": f"/{last_sub.hash}"}
        label = suffix.removeprefix(".").upper() or "FILE"
        if suffix in IMAGE_EXTENSIONS:
            row["kind"] = "image"
        elif suffix in _VIDEO_EXTENSIONS:
            row["kind"] = "video"
            row["label"] = label
        elif suffix in _AUDIO_EXTENSIONS:
            row["kind"] = "audio"
            row["label"] = label
        else:
            row["kind"] = "other"
            row["icon"] = _file_icon(suffix)
            row["label"] = label
        images.append(row)
    return render_template("show.html", images=images)
