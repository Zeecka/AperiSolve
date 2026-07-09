"""Aperi'Solve Flask application."""

import hashlib
import json
import os
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import sentry_sdk
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file
from flask_babel import Babel, get_locale
from flask_babel import gettext as _
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.wrappers.response import Response as WerkzeugResponse

from .analyzers.registry import archive_tools, tool_order
from .config import (
    ADSENSE_CLIENT,
    ADSENSE_SLOT_INDEX,
    ADSENSE_SLOT_RESULT,
    ADSENSE_SLOT_WIKI_ARTICLE,
    ADSENSE_SLOT_WIKI_SIDEBAR,
    CLEANUP_INTERVAL_SECONDS,
    CUSTOM_EXTERNAL_SCRIPT,
    DB_URI,
    FLASK_DEBUG,
    GOOGLE_ADS_TXT,
    IMAGE_EXTENSIONS,
    JOB_TIMEOUT,
    MAX_CONTENT_LENGTH,
    PROJECT_VERSION,
    REDIS_URL,
    REMOVAL_MIN_AGE_SECONDS,
    REMOVED_IMAGES_FOLDER,
    RESULT_FOLDER,
    SITE_BASE_URL,
)
from .filetype import detect_file_type
from .i18n import (
    DEFAULT_LANG,
    LANG_PREFIX_RULE,
    OG_LOCALES,
    PREFIX_LANGS,
    SUPPORTED_LANGS,
    alternates_for,
    js_catalog,
    lang_prefix,
    select_locale,
)
from .limits import is_local_request, limiter
from .models import Image, Submission, UploadLog, cleanup_old_entries, db
from .pages import pages_bp
from .utils.sentry import initialize_sentry
from .utils.utils import get_client_ip
from .wiki import page_lastmod, translated_langs, wiki_bp, wiki_pages, wiki_tool_names

CLEANUP_LOCK_KEY = "aperisolve:cleanup-lock"

_is_local_request = is_local_request


def _configure_app(app: Flask) -> None:
    """Configure Flask and extension settings."""
    app.config["JSON_SORT_KEYS"] = False
    app.config["PROJECT_VERSION"] = PROJECT_VERSION
    app.config["CUSTOM_EXTERNAL_SCRIPT"] = CUSTOM_EXTERNAL_SCRIPT
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["REDIS_QUEUE"] = Queue(connection=Redis.from_url(REDIS_URL))
    app.config["TOOL_ORDER"] = tool_order()
    app.config["ADSENSE_CLIENT"] = ADSENSE_CLIENT
    app.config["ADSENSE_SLOT_WIKI_SIDEBAR"] = ADSENSE_SLOT_WIKI_SIDEBAR
    app.config["ADSENSE_SLOT_WIKI_ARTICLE"] = ADSENSE_SLOT_WIKI_ARTICLE
    app.config["ADSENSE_SLOT_INDEX"] = ADSENSE_SLOT_INDEX
    app.config["ADSENSE_SLOT_RESULT"] = ADSENSE_SLOT_RESULT
    # Static asset URLs are cache-busted with ?v=<PROJECT_VERSION> in templates.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=7)
    Babel(app, locale_selector=select_locale)
    limiter.init_app(app)
    db.init_app(app)


def _extract_unique_ips(upload_logs: list[UploadLog]) -> set[str]:
    """Return unique non-empty uploader IP addresses from logs."""
    return {str(log.ip_address) for log in upload_logs if log.ip_address}


def _archive_original_image(
    original_image_path: Path,
    image_hash: str,
    submission_hash: str,
) -> None:
    """Archive original image file before deletion."""
    if not original_image_path.exists():
        return
    REMOVED_IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)
    dt = datetime.now(UTC).isoformat()
    archive_filename = f"{image_hash}_{submission_hash}_{dt}{original_image_path.suffix}"
    archive_path = REMOVED_IMAGES_FOLDER / archive_filename
    shutil.copy2(original_image_path, archive_path)


def _remove_result_folder(image_hash: str, submission_hash: str) -> None:
    """Delete result folder for a submission if it exists."""
    result_path = RESULT_FOLDER / image_hash / submission_hash
    if result_path.exists():
        shutil.rmtree(result_path)


def _delete_submission_entities(
    submission: Submission,
    image: Image,
    original_image_path: Path,
) -> None:
    """Delete submission and related image entity if applicable."""
    db.session.delete(submission)
    if len(image.submissions) <= 1:
        if original_image_path.exists():
            original_image_path.unlink()
        db.session.delete(image)
    db.session.commit()


def _base_url() -> str:
    """Public base URL for absolute links (canonical, Open Graph, sitemap)."""
    return SITE_BASE_URL or request.url_root.rstrip("/")


def _register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers."""

    @app.context_processor
    def inject_datetime() -> dict[str, type[datetime]]:
        """Inject datetime into all templates."""
        return {"datetime": datetime}

    @app.context_processor
    def inject_base_url() -> dict[str, str]:
        """Inject the public base URL into all templates."""
        return {"base_url": _base_url()}

    @app.context_processor
    def inject_i18n() -> dict[str, Any]:
        """Inject language context: prefix, switcher targets, JS catalog."""
        switch = None
        endpoint = request.endpoint or ""
        if endpoint.startswith(("pages.", "wiki.", "pages_i18n.", "wiki_i18n.")):
            bare = request.path
            prefix = lang_prefix()
            if prefix and bare.startswith(prefix):
                bare = bare[len(prefix) :] or "/"
            switch = [
                (lang, bare if lang == DEFAULT_LANG else f"/{lang}{bare}")
                for lang in SUPPORTED_LANGS
            ]
        current = str(get_locale())
        return {
            "lang_prefix": lang_prefix(),
            "current_lang": current,
            "js_i18n": js_catalog(),
            "lang_switch": switch,
            "wiki_tools": sorted(wiki_tool_names()),
            "og_locale": OG_LOCALES.get(current, "en_US"),
            "og_locale_alternates": [v for k, v in OG_LOCALES.items() if k != current],
        }

    @app.errorhandler(413)
    def too_large(_error: object) -> tuple[Response, int]:
        """Handle max upload size errors."""
        sentry_sdk.set_context(
            "upload",
            {
                "content_length": request.content_length,
                "max_allowed": app.config["MAX_CONTENT_LENGTH"],
            },
        )
        sentry_sdk.capture_message("Upload failed: 413 Payload Too Large", level="warning")
        return jsonify({"error": _("Image size exceeded")}), 413

    @app.errorhandler(404)
    def not_found(_error: object) -> tuple[str, int]:
        """Handle not found errors."""
        return render_template("error.html", message=_("Resource not found"), statuscode=404), 404

    @app.errorhandler(429)
    def too_many_requests(_error: object) -> tuple[Response, int]:
        """Handle rate-limit errors with the JSON shape the frontend renders."""
        return jsonify({"error": _("Too many requests, please slow down.")}), 429


def _register_page_routes(app: Flask) -> None:
    """Register non-translated page routes (translated pages live in pages_bp)."""

    @app.route("/faq")
    def faq() -> WerkzeugResponse:
        """Redirect the legacy FAQ URL to the wiki cheatsheet."""
        return redirect("/wiki/cheatsheet", code=301)

    @app.route("/<string(length=32):hash_val>", methods=["GET"])
    def result_page(hash_val: str) -> str:
        """Render the result page for a given submission hash (32-hex md5)."""
        submission = Submission.query.get_or_404(hash_val)
        Image.query.get_or_404(submission.image_hash)
        return render_template("result.html", hash_val=hash_val)

    @app.route("/ads.txt")
    def google_ads() -> str:
        """Serve the Google Ads required file."""
        return GOOGLE_ADS_TXT

    @app.route("/robots.txt")
    def robots_txt() -> Response:
        """Serve crawler directives; API endpoints are not for indexing."""
        lines = [
            "User-agent: *",
            *[
                f"Disallow: {path}"
                for path in (
                    "/upload",
                    "/status/",
                    "/result/",
                    "/infos/",
                    "/image/",
                    "/download/",
                    "/remove/",
                    "/remove_password/",
                )
            ],
            "",
            f"Sitemap: {_base_url()}/sitemap.xml",
            "",
        ]
        return Response("\n".join(lines), mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml() -> Response:
        """Serve the sitemap with lastmod dates and hreflang alternates."""
        base = _base_url()
        parts = []
        for path, lastmod, alts in _sitemap_entries():
            links = "".join(
                f'<xhtml:link rel="alternate" hreflang="{code}" href="{base}{href}"/>'
                for code, href in alts
            )
            lastmod_tag = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
            parts.append(f"<url><loc>{base}{path}</loc>{lastmod_tag}{links}</url>")
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            f"{''.join(parts)}</urlset>"
        )
        return Response(xml, mimetype="application/xml")


def _sitemap_entries() -> list[tuple[str, str | None, list[tuple[str, str]]]]:
    """(path, lastmod, hreflang alternates) for every indexable URL.

    Wiki pages only list languages with a real translation; untranslated
    fallbacks canonicalize to English and stay out of the sitemap.
    """
    home_alts = alternates_for("/")
    entries: list[tuple[str, str | None, list[tuple[str, str]]]] = [("/", None, home_alts)]
    entries += [(f"/{lang}/", None, home_alts) for lang in PREFIX_LANGS]
    for page in wiki_pages():
        langs = translated_langs(page.slug)
        alts = alternates_for(page.path, [DEFAULT_LANG, *langs])
        entries.append((page.path, page_lastmod(DEFAULT_LANG, page.slug), alts))
        entries.extend(
            (f"/{lang}{page.path}", page_lastmod(lang, page.slug), alts) for lang in langs
        )
    return entries


def _acquire_cleanup_lock(app: Flask) -> bool:
    """Claim the per-interval cleanup lock. False on contention or Redis error.

    A Redis ``SET NX EX`` ensures a single process (a gunicorn worker or the
    cron scheduler) drives the sweep per interval; everyone else backs off.
    """
    redis_conn = app.config["REDIS_QUEUE"].connection
    try:
        return bool(
            redis_conn.set(
                CLEANUP_LOCK_KEY,
                "1",
                nx=True,
                ex=CLEANUP_INTERVAL_SECONDS,
            ),
        )
    except RedisError as exc:
        sentry_sdk.capture_exception(exc)
        return False


def run_cleanup_with_lock(app: Flask) -> None:
    """Run the retention sweep inline, at most once per interval, cluster-wide.

    Used by the cron worker (``aperisolve/tasks.py``), which runs off the
    request path where a long sweep cannot abort an HTTP worker.
    """
    if _acquire_cleanup_lock(app):
        cleanup_old_entries()


def schedule_cleanup(app: Flask) -> None:
    """Enqueue the retention sweep as a background job, once per interval.

    The request path calls this as a safety net for when the cron service is
    down. Running the sweep inline in a gunicorn worker risked exceeding the
    (30 s default) worker timeout on a large backlog and aborting the request
    with ``SystemExit`` (issue #191); enqueuing keeps it off the request path.
    The interval lock is claimed here so at most one job is queued per
    interval, and the job runs the sweep directly without re-claiming it.
    """
    if _acquire_cleanup_lock(app):
        try:
            app.config["REDIS_QUEUE"].enqueue(
                "aperisolve.tasks.cleanup_sweep_job",
                job_timeout=JOB_TIMEOUT,
            )
        except RedisError as exc:
            sentry_sdk.capture_exception(exc)


def _get_or_create_image(img_hash: str, new_img_path: Path, size: int) -> Image:
    """Fetch the Image row or insert it, tolerating a concurrent insert."""
    sub_img = Image.query.filter_by(hash=img_hash).first()
    if sub_img is None:
        sub_img = Image(
            file=str(new_img_path),
            hash=img_hash,
            size=size,
            upload_count=0,
            first_submission_date=datetime.now(UTC),
            last_submission_date=datetime.now(UTC),
        )
        db.session.add(sub_img)
        try:
            db.session.commit()
        except IntegrityError:
            # A concurrent identical upload won the insert race; use its row.
            db.session.rollback()
            sub_img = Image.query.filter_by(hash=img_hash).one()
    return sub_img


def _upload_image(app: Flask) -> tuple[Response, int]:
    """Handle image upload and initiate analysis."""
    # The cron service is the primary cleanup driver; this enqueue is a safety
    # net for when it is down. It runs off the request path (issue #191) and is
    # a no-op whenever the cron job already holds the interval lock.
    schedule_cleanup(app)

    if "image" not in request.files:
        return jsonify({"error": _("No image provided")}), 400

    image = request.files["image"]
    password = request.form.get("password")
    deep_analysis = request.form.get("deep") == "true"

    if image.filename is None or image.filename == "":
        return jsonify({"error": _("No image provided")}), 400

    # Any file type is accepted; only require a usable extension because storage
    # and get_image split the stored name on ".".
    if "." not in image.filename or not Path(image.filename).suffix:
        return jsonify({"error": _("Unsupported file type")}), 400

    image_data = image.read()
    img_hash = hashlib.md5(image_data, usedforsecurity=False).hexdigest()
    image_name = img_hash + "." + image.filename.rsplit(".", maxsplit=1)[-1].lower()

    submission_data = (
        image_data
        + image.filename.encode()
        + (password.encode() if password else b"")
        + (b"deep_analysis" if deep_analysis else b"")
    )
    submission_hash = hashlib.md5(submission_data, usedforsecurity=False).hexdigest()
    submission_path = RESULT_FOLDER / img_hash / submission_hash

    client_ip = get_client_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")

    upload_log = UploadLog(
        ip_address=client_ip,
        user_agent=user_agent,
        image_hash=img_hash,
        submission_hash=submission_hash,
        filename=image.filename,
    )
    db.session.add(upload_log)
    db.session.commit()

    submission = Submission.query.filter_by(hash=submission_hash).first()
    if submission_path.exists() and submission is not None:
        return jsonify({"submission_hash": submission.hash}), 200

    new_img_path = RESULT_FOLDER / img_hash / image_name
    if not new_img_path.exists():
        new_img_path.parent.mkdir(parents=True, exist_ok=True)
        with new_img_path.open("wb") as file_obj:
            file_obj.write(image_data)

    sub_img = _get_or_create_image(img_hash, new_img_path, len(image_data))

    sub_img_any = cast("Any", sub_img)
    sub_img_any.upload_count = int(sub_img_any.upload_count or 0) + 1
    db.session.commit()

    submission_path.mkdir(parents=True, exist_ok=True)
    if not submission:
        submission = Submission(
            filename=image.filename,
            password=password,
            deep_analysis=deep_analysis,
            hash=submission_hash,
            status="pending",
            date=time.time(),
            image_hash=sub_img.hash,
        )
        db.session.add(submission)
        try:
            db.session.commit()
        except IntegrityError:
            # A concurrent identical upload won the insert race; use its row.
            db.session.rollback()
            submission = Submission.query.filter_by(hash=submission_hash).one()

    submission_any = cast("Any", submission)
    submission_any.status = "pending"
    db.session.commit()

    app.config["REDIS_QUEUE"].enqueue(
        "aperisolve.workers.analyze_image",
        submission.hash,
        # Analyzer subprocess timeouts (SUBPROCESS_TIMEOUT) must fire before RQ
        # kills the job, so partial results get written and the submission
        # never sticks in "running".
        job_timeout=JOB_TIMEOUT,
    )
    return jsonify({"submission_hash": submission.hash}), 200


def _register_submission_routes(app: Flask) -> None:
    """Register upload and status routes."""

    @app.route("/upload", methods=["POST"])
    @limiter.limit("10 per minute; 100 per hour", exempt_when=_is_local_request)
    def upload_image() -> tuple[Response, int]:
        return _upload_image(app)

    @app.route("/status/<hash_val>", methods=["GET"])
    @limiter.limit("240 per minute", exempt_when=_is_local_request)
    def get_status(hash_val: str) -> Response:
        """Get the processing status of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        response = jsonify({"status": submission.status})
        response.headers["Cache-Control"] = "no-store"
        return response


def _build_result_response(result_path: Path) -> Response | tuple[Response, int]:
    """Build the /result response with an ETag over the raw results.json bytes.

    The frontend polls this endpoint while analysis runs; the ETag turns
    unchanged polls into 304s.
    """
    if not result_path.exists():
        response = jsonify({"error": _("Results not ready yet...")})
        response.headers["Cache-Control"] = "no-store"
        return response, 425

    raw = result_path.read_bytes()
    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        response = jsonify({"error": _("Results not ready yet...")})
        response.headers["Cache-Control"] = "no-store"
        return response, 425

    response = jsonify({"results": results})
    response.headers["Cache-Control"] = "no-cache"
    response.set_etag(hashlib.md5(raw, usedforsecurity=False).hexdigest())
    return cast("Response", response.make_conditional(request))


def _register_data_routes(app: Flask) -> None:
    """Register metadata, results, and download routes."""

    @app.route("/infos/<hash_val>", methods=["GET"])
    @limiter.limit("60 per minute", exempt_when=_is_local_request)
    def get_infos(hash_val: str) -> Response:
        """Get the metadata and information of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)
        names = [name for name in {sub.filename for sub in image.submissions} if name]
        passwords = [pwd for pwd in {sub.password for sub in image.submissions} if pwd]
        # detect_file_type is best-effort and never raises; kind drives the
        # frontend preview (image/audio/pdf/other) and mime is informational.
        file_type = detect_file_type(Path(image.file))
        response = jsonify(
            {
                "image_path": "image/" + str(Path(image.file).name),
                "kind": file_type.kind,
                "mime": file_type.mime,
                "names": names,
                "size": image.size,
                "first_submission_date": image.first_submission_date,
                "last_submission_date": image.last_submission_date,
                "upload_count": image.upload_count,
                "passwords": passwords,
                "removal_min_age_seconds": REMOVAL_MIN_AGE_SECONDS,
                "submission_date": submission.date,
            },
        )
        response.headers["Cache-Control"] = "private, max-age=30"
        return response

    @app.route("/result/<hash_val>", methods=["GET"])
    @limiter.limit("240 per minute", exempt_when=_is_local_request)
    def get_result(hash_val: str) -> Response | tuple[Response, int]:
        """Get the analysis results of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)
        result_path = RESULT_FOLDER / str(image.hash) / str(submission.hash) / "results.json"
        return _build_result_response(result_path)

    @app.route("/download/<hash_val>/<tool>")
    def download_output(hash_val: str, tool: str) -> Response:
        """Download output of a specific analyzer for a submission hash."""
        submission = Submission.query.filter_by(hash=hash_val).first_or_404()
        image = Image.query.get_or_404(submission.image_hash)
        output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
        output_file = output_dir / f"{tool}.7z"

        if tool not in archive_tools() or not output_file.exists():
            abort(404, description="Tool output not found.")

        response = send_file(output_file, as_attachment=True)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @app.route("/image/<img_name>")
    @app.route("/image/<hash_val>/<img_name>")
    def get_image(hash_val: str | None = None, img_name: str | None = None) -> Response:
        """Download an image for a submission hash or by direct image filename.

        Usually this serves derived images generated by the decomposer analyzer.
        """
        if img_name is None:
            return abort(404, description="Image not found or unsupported format")

        # The original upload (/image/<name>) may be any stored file type; the
        # derived sub-path (/image/<hash>/<name>) only ever serves images.
        # Capture this before the else-branch reassigns hash_val below.
        serving_original = hash_val is None
        if hash_val is not None:
            submission = Submission.query.filter_by(hash=hash_val).first_or_404()
            image = Image.query.get_or_404(submission.image_hash)
            output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            output_file = output_dir / Path(img_name).name
        else:
            hash_val = img_name.split(".")[0]
            image = Image.query.filter_by(hash=hash_val).first_or_404()
            output_file = Path(image.file)

        if not output_file.exists():
            return abort(404, description="Image not found or unsupported format")
        if not serving_original and output_file.suffix.lower() not in IMAGE_EXTENSIONS:
            return abort(404, description="Image not found or unsupported format")

        # URLs are content-addressed (md5 hashes), so responses never change:
        # the ~40 derived bit-plane images per result page cache forever.
        response = send_file(output_file, as_attachment=True)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def _register_management_routes(app: Flask) -> None:
    """Register removal and moderation routes."""

    @app.route("/remove/<hash_val>", methods=["POST"])
    @limiter.limit("5 per minute", exempt_when=_is_local_request)
    def remove_image(hash_val: str) -> tuple[Response, int]:
        """Remove an image and associated results if criteria are met."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)

        age_seconds = time.time() - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": _(
                            "Image must be at least %(min)d seconds old. Current age: %(age)ds",
                            min=REMOVAL_MIN_AGE_SECONDS,
                            age=int(age_seconds),
                        ),
                    },
                ),
                403,
            )

        upload_logs = UploadLog.query.filter_by(image_hash=image.hash).all()
        unique_ips = _extract_unique_ips(upload_logs)
        if len(unique_ips) > 1:
            return (
                jsonify(
                    {
                        "error": _(
                            "Image uploaded from multiple IP addresses. Removal is not allowed.",
                        ),
                        "ip_count": len(unique_ips),
                    },
                ),
                403,
            )

        original_image_path = Path(image.file)
        try:
            _archive_original_image(original_image_path, image.hash, submission.hash)
            _remove_result_folder(str(image.hash), str(submission.hash))
            _delete_submission_entities(submission, image, original_image_path)
        except (OSError, SQLAlchemyError) as exc:
            db.session.rollback()
            sentry_sdk.capture_exception(exc)
            return jsonify({"error": _("Failed to remove image")}), 500

        return jsonify({"message": "Image successfully removed"}), 200

    @app.route("/remove_password/<hash_val>", methods=["POST"])
    @limiter.limit("5 per minute", exempt_when=_is_local_request)
    def remove_password(hash_val: str) -> tuple[Response, int]:
        """Remove a password from a submission if criteria are met."""
        submission = Submission.query.get_or_404(hash_val)

        if not submission.password:
            return jsonify({"error": _("No password to remove")}), 400

        age_seconds = time.time() - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": _(
                            "Submission must be at least %(min)d seconds old. "
                            "Current age: %(age)ds",
                            min=REMOVAL_MIN_AGE_SECONDS,
                            age=int(age_seconds),
                        ),
                    },
                ),
                403,
            )

        upload_logs = UploadLog.query.filter_by(submission_hash=submission.hash).all()
        unique_ips = _extract_unique_ips(upload_logs)
        if len(unique_ips) > 1:
            return (
                jsonify(
                    {
                        "error": _(
                            "Submission uploaded from multiple IP addresses. "
                            "Password removal is not allowed.",
                        ),
                        "ip_count": len(unique_ips),
                    },
                ),
                403,
            )

        try:
            submission.password = None
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            sentry_sdk.capture_exception(exc)
            return jsonify({"error": _("Failed to remove password")}), 500

        return jsonify({"message": "Password successfully removed"}), 200


def create_app() -> Flask:
    """Create flask application with routes."""
    initialize_sentry()
    app = Flask(__name__)
    _configure_app(app)
    _register_error_handlers(app)
    _register_page_routes(app)
    _register_submission_routes(app)
    _register_data_routes(app)
    _register_management_routes(app)
    # Translatable pages are served at the root (English) and under a
    # language prefix (/fr/, /es/, ...) for indexable per-language URLs.
    app.register_blueprint(pages_bp)
    app.register_blueprint(pages_bp, url_prefix=LANG_PREFIX_RULE, name="pages_i18n")
    app.register_blueprint(wiki_bp)
    app.register_blueprint(wiki_bp, url_prefix=LANG_PREFIX_RULE, name="wiki_i18n")
    return app


if __name__ == "__main__":
    my_app = create_app()
    flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
    my_app.run(host=flask_host, port=5000, debug=FLASK_DEBUG)
