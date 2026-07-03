"""Translatable page routes, registered at the root and under /<lang>/."""

from flask import Blueprint, render_template

from .i18n import alternates_for, register_lang_handling
from .models import Image

pages_bp = Blueprint("pages", __name__)
register_lang_handling(pages_bp)


@pages_bp.route("/")
def index() -> str:
    """Render the main index page."""
    return render_template("index.html", alternates=alternates_for("/"))


@pages_bp.route("/show")
def show() -> str:
    """Show all active submissions."""
    db_images = Image.query.all()
    images = []
    for img in db_images:
        last_sub = img.submissions[-1]
        images.append({"file": f"/image/{img.hash}", "link": f"/{last_sub.hash}"})
    return render_template("show.html", images=images)
