"""Aperi'Solve Flask application."""

import hashlib
import json
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import sentry_sdk
from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from redis import Redis
from rq import Queue
from sqlalchemy.exc import SQLAlchemyError

from .config import (
    CUSTOM_EXTERNAL_SCRIPT,
    DB_URI,
    FLASK_DEBUG,
    GOOGLE_ADS_TXT,
    IMAGE_EXTENSIONS,
    MAX_CONTENT_LENGTH,
    PROJECT_VERSION,
    REMOVAL_MIN_AGE_SECONDS,
    REMOVED_IMAGES_FOLDER,
    RESULT_FOLDER,
    WORKER_FILES,
)
from .models import Image, Submission, UploadLog, cleanup_old_entries, db
from .utils.sentry import initialize_sentry


def _configure_app(app: Flask) -> None:
    """Configure Flask and extension settings."""
    app.json.sort_keys = False
    app.config["PROJECT_VERSION"] = PROJECT_VERSION
    app.config["CUSTOM_EXTERNAL_SCRIPT"] = CUSTOM_EXTERNAL_SCRIPT
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["REDIS_QUEUE"] = Queue(connection=Redis(host="redis", port=6379))
    db.init_app(app)


def _extract_unique_ips(upload_logs: list[UploadLog]) -> set[str]:
    """Return unique non-empty uploader IP addresses from logs."""
    return {log.ip_address for log in upload_logs if log.ip_address}


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


def _register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers."""

    @app.context_processor
    def inject_datetime() -> dict[str, type[datetime]]:
        """Inject datetime into all templates."""
        return {"datetime": datetime}

    @app.errorhandler(413)
    def too_large(_: object) -> tuple[Response, int]:
        """Handle max upload size errors."""
        sentry_sdk.set_context(
            "upload",
            {
                "content_length": request.content_length,
                "max_allowed": app.config["MAX_CONTENT_LENGTH"],
            },
        )
        sentry_sdk.capture_message("Upload failed: 413 Payload Too Large", level="warning")
        return jsonify({"error": "Image size exceeded"}), 413

    @app.errorhandler(404)
    def not_found(_: object) -> str:
        """Handle not found errors."""
        return render_template("error.html", message="Resource not found", statuscode=404)


def _register_page_routes(app: Flask) -> None:
    """Register static page routes."""

    @app.route("/")
    def index() -> str:
        """Render the main index page."""
        return render_template("index.html")

    @app.route("/faq")
    def faq() -> str:
        """Render the FAQ page."""
        return render_template("faq.html")

    @app.route("/show")
    def show() -> str:
        """Show all active submissions."""
        db_images = Image.query.all()
        images = []
        for img in db_images:
            last_sub = img.submissions[-1]
            images.append({"file": f"/image/{img.hash}", "link": f"/{last_sub.hash}"})
        return render_template("show.html", images=images)

    @app.route("/<hash_val>", methods=["GET"])
    def result_page(hash_val: str) -> str:
        """Render the result page for a given submission hash."""
        submission = Submission.query.get_or_404(hash_val)
        Image.query.get_or_404(submission.image_hash)
        return render_template("result.html", hash_val=hash_val)

    @app.route("/ads.txt")
    def google_ads() -> str:
        """Serve the Google Ads required file."""
        return GOOGLE_ADS_TXT


def _upload_image(app: Flask) -> tuple[Response, int]:
    """Handle image upload and initiate analysis."""
    cleanup_old_entries()

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image = request.files["image"]
    password = request.form.get("password")
    deep_analysis = request.form.get("deep") == "true"

    if image.filename is None or image.filename == "":
        return jsonify({"error": "No image provided"}), 400

    if "." not in image.filename or Path(image.filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return jsonify({"error": "Unsupported file type"}), 400

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

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
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

    sub_img = Image.query.filter_by(hash=img_hash).first()
    if sub_img is None:
        sub_img = Image(
            file=str(new_img_path),
            hash=img_hash,
            size=len(image_data),
            upload_count=0,
            first_submission_date=datetime.now(UTC),
            last_submission_date=datetime.now(UTC),
        )
        db.session.add(sub_img)
        db.session.commit()

    sub_img.upload_count += 1
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
        db.session.commit()

    submission.status = "pending"
    db.session.commit()

    app.config["REDIS_QUEUE"].enqueue(
        "aperisolve.workers.analyze_image",
        submission.hash,
        job_timeout=300,
    )
    return jsonify({"submission_hash": submission.hash}), 200


def _register_submission_routes(app: Flask) -> None:
    """Register upload and status routes."""

    @app.route("/upload", methods=["POST"])
    def upload_image() -> tuple[Response, int]:
        return _upload_image(app)

    @app.route("/status/<hash_val>", methods=["GET"])
    def get_status(hash_val: str) -> Response:
        """Get the processing status of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        return jsonify({"status": submission.status})


def _register_data_routes(app: Flask) -> None:
    """Register metadata, results, and download routes."""

    @app.route("/infos/<hash_val>", methods=["GET"])
    def get_infos(hash_val: str) -> Response:
        """Get the metadata and information of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)
        names = [name for name in {sub.filename for sub in image.submissions} if name]
        passwords = [pwd for pwd in {sub.password for sub in image.submissions} if pwd]
        return jsonify(
            {
                "image_path": "image/" + str(Path(image.file).name),
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

    @app.route("/result/<hash_val>", methods=["GET"])
    def get_result(hash_val: str) -> tuple[Response, int]:
        """Get the analysis results of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)
        result_path = RESULT_FOLDER / str(image.hash) / str(submission.hash) / "results.json"

        if not result_path.exists():
            return jsonify({"error": "Results not ready yet..."}), 425

        with result_path.open(encoding="utf-8") as file_obj:
            results = json.load(file_obj)

        return jsonify({"results": results}), 200

    @app.route("/download/<hash_val>/<tool>")
    def download_output(hash_val: str, tool: str) -> Response:
        """Download output of a specific analyzer for a submission hash."""
        submission = Submission.query.filter_by(hash=hash_val).first_or_404()
        image = Image.query.get_or_404(submission.image_hash)
        output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
        output_file = output_dir / f"{tool}.7z"

        if tool not in WORKER_FILES or not output_file.exists():
            abort(404, description="Tool output not found.")

        return send_file(output_file, as_attachment=True)

    @app.route("/image/<img_name>")
    @app.route("/image/<hash_val>/<img_name>")
    def get_image(hash_val: str | None = None, img_name: str | None = None) -> Response:
        """Download an image for a submission hash or by direct image filename.

        Usually this serves derived images generated by the decomposer analyzer.
        """
        if img_name is None:
            return abort(404, description="Image not found or unsupported format")

        if hash_val is not None:
            submission = Submission.query.filter_by(hash=hash_val).first_or_404()
            image = Image.query.get_or_404(submission.image_hash)
            output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            output_file = output_dir / Path(img_name).name
        else:
            hash_val = img_name.split(".")[0]
            image = Image.query.filter_by(hash=hash_val).first_or_404()
            output_file = Path(image.file)

        if (not output_file.exists()) or (output_file.suffix.lower() not in IMAGE_EXTENSIONS):
            return abort(404, description="Image not found or unsupported format")

        return send_file(output_file, as_attachment=True)


def _register_management_routes(app: Flask) -> None:
    """Register removal and moderation routes."""

    @app.route("/remove/<hash_val>", methods=["POST"])
    def remove_image(hash_val: str) -> tuple[Response, int]:
        """Remove an image and associated results if criteria are met."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)

        age_seconds = time.time() - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": "Image must be at least 5 minutes old. "
                        f"Current age: {int(age_seconds)}s",
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
                        "error": "Image uploaded from multiple IP addresses. Removal is not "
                        "allowed.",
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
            return jsonify({"error": "Failed to remove image"}), 500

        return jsonify({"message": "Image successfully removed"}), 200

    @app.route("/remove_password/<hash_val>", methods=["POST"])
    def remove_password(hash_val: str) -> tuple[Response, int]:
        """Remove a password from a submission if criteria are met."""
        submission = Submission.query.get_or_404(hash_val)

        if not submission.password:
            return jsonify({"error": "No password to remove"}), 400

        age_seconds = time.time() - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": "Submission must be at least 5 minutes old. "
                        f"Current age: {int(age_seconds)}s",
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
                        "error": "Submission uploaded from multiple IP addresses. "
                        "Password removal is not allowed.",
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
            return jsonify({"error": "Failed to remove password"}), 500

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
    return app


if __name__ == "__main__":
    my_app = create_app()
    flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
    my_app.run(host=flask_host, port=5000, debug=FLASK_DEBUG)
