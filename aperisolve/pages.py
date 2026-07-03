"""Translatable page routes, registered at the root and under /<lang>/."""

from flask import Blueprint, render_template

from .i18n import alternates_for, register_lang_handling
from .models import Image

pages_bp = Blueprint("pages", __name__)
register_lang_handling(pages_bp)

MAX_SHOW_IMAGES = 100


@pages_bp.route("/")
def index() -> str:
    """Render the main index page."""
    return render_template("index.html", alternates=alternates_for("/"))


@pages_bp.route("/show")
def show() -> str:
    """Show the most recent submissions (bounded: the table grows unbounded)."""
    db_images = Image.query.order_by(Image.last_submission_date.desc()).limit(MAX_SHOW_IMAGES).all()
    images = []
    for img in db_images:
        if not img.submissions:
            continue
        last_sub = img.submissions[-1]
        images.append({"file": f"/image/{img.hash}", "link": f"/{last_sub.hash}"})
    return render_template("show.html", images=images)
