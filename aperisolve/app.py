# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801,R0915
# mypy: disable-error-code=unused-awaitable
"""Aperi'Solve Flask application."""

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import sentry_sdk
from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from redis import Redis
from rq import Queue

from .utils.sentry import initialize_sentry

initialize_sentry()

from .config import (
    IMAGE_EXTENSIONS,
    REMOVAL_MIN_AGE_SECONDS,
    REMOVED_IMAGES_FOLDER,
    RESULT_FOLDER,
    WORKER_FILES,
)
from .models import Image, Submission, UploadLog, cleanup_old_entries, db


def create_app() -> Flask:
    """Create flask application with routes."""
    app = Flask(__name__)
    app.json.sort_keys = False  # type: ignore
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 1024 * 1024))
    app.config["REDIS_QUEUE"] = Queue(connection=Redis(host="redis", port=6379))
    db.init_app(app)

    @app.errorhandler(413)
    def too_large(_: Any) -> tuple[Response, int]:
        """Error Handler for Max File Size."""
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
    def not_found(_: Any) -> str:
        """Error Handler for 404 not found."""
        return render_template("error.html", message="Resource not found", statuscode=404)

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
        submission = Submission.query.get_or_404(hash_val)  # type: ignore
        Image.query.get_or_404(submission.image_hash)  # type: ignore

        return render_template("result.html", hash_val=hash_val)

    @app.route("/upload", methods=["POST"])
    def upload_image() -> tuple[Response, int]:
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

        # Compute hashes and prepare submission
        image_data = image.read()
        img_hash = hashlib.md5(image_data).hexdigest()
        image_name = img_hash + "." + image.filename.rsplit(".", maxsplit=1)[-1].lower()

        submission_data = (
            image_data
            + image.filename.encode()
            + (password.encode() if password else b"")
            + (b"deep_analysis" if deep_analysis else b"")
        )
        submission_hash = hashlib.md5(submission_data).hexdigest()
        submission_path = RESULT_FOLDER / img_hash / submission_hash

        # Log upload to database
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
        db.session.add(upload_log)  # pylint: disable=no-member
        db.session.commit()  # pylint: disable=no-member

        # Check if hash is present on the DB
        submission: Submission = Submission.query.filter_by(hash=submission_hash).first()

        # Only return if BOTH the file exists AND the DB entry exists
        if submission_path.exists() and submission is not None:
            return jsonify({"submission_hash": submission.hash}), 200

        # Self-Healing Logic
        new_img_path = RESULT_FOLDER / img_hash / image_name

        # This fixes the "Ghost File" issue (DB exists, but file is missing)
        if not new_img_path.exists():
            new_img_path.parent.mkdir(parents=True, exist_ok=True)
            with open(new_img_path, "wb") as f:
                f.write(image_data)

        # Try to find image in DB by hash
        sub_img = Image.query.filter_by(hash=img_hash).first()

        # If DB entry is missing (even if file exists on disk), create it!
        if sub_img is None:
            sub_img = Image(
                file=str(new_img_path),
                hash=img_hash,
                size=len(image_data),
                upload_count=0,
                first_submission_date=datetime.now(timezone.utc),
                last_submission_date=datetime.now(timezone.utc),
            )
            db.session.add(sub_img)  # pylint: disable=no-member
            db.session.commit()  # pylint: disable=no-member

        # Increment upload count for the image
        sub_img.upload_count += 1
        db.session.commit()  # pylint: disable=no-member

        # Create new Submission entry
        submission_path.mkdir(parents=True, exist_ok=True)

        # Only create a new submission if it does not already exist
        # New submission for new image
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
            db.session.add(submission)  # pylint: disable=no-member
            db.session.commit()  # pylint: disable=no-member

        # Re-analysis case to prevent early return
        submission.status = "pending"  # type: ignore
        db.session.commit()  # pylint: disable=no-member

        # Start the analysis jobs
        app.config["REDIS_QUEUE"].enqueue(
            "aperisolve.workers.analyze_image", submission.hash, job_timeout=300
        )

        # Return submission identifier
        return jsonify({"submission_hash": submission.hash}), 200

    @app.route("/status/<hash_val>", methods=["GET"])
    def get_status(hash_val: str) -> Response:
        """Get the processing status of a submission."""
        submission = Submission.query.get_or_404(hash_val)  # type: ignore
        return jsonify({"status": submission.status})  # type: ignore

    @app.route("/infos/<hash_val>", methods=["GET"])
    def get_infos(hash_val: str) -> Response:
        """Get the metadata and information of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore
        names = [name for name in set(sub.filename for sub in image.submissions) if name]
        passwords = [pwd for pwd in set(sub.password for sub in image.submissions) if pwd]
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
            }
        )  # type: ignore

    @app.route("/result/<hash_val>", methods=["GET"])
    def get_result(hash_val: str) -> tuple[Response, int]:
        """Get the analysis results of a submission."""
        submission = Submission.query.get_or_404(hash_val)
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore

        result_path = RESULT_FOLDER / str(image.hash) / str(submission.hash) / "results.json"

        if not result_path.exists():
            return jsonify({"error": "Results not ready yet..."}), 425

        with open(result_path, "r", encoding="utf-8") as f:
            results = json.load(f)

        return jsonify({"results": results}), 200

    @app.route("/download/<hash_val>/<tool>")
    def download_output(hash_val: str, tool: str) -> Response:
        """Download the output of a specific analyzer for a given submission hash."""

        submission = Submission.query.filter_by(hash=hash_val).first_or_404()
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore

        output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
        output_file = output_dir / f"{tool}.7z"

        if tool not in WORKER_FILES or not output_file.exists():
            abort(404, description="Tool output not found.")

        return send_file(output_file, as_attachment=True)

    @app.route("/remove/<hash_val>", methods=["POST"])
    def remove_image(hash_val: str) -> tuple[Response, int]:
        """Remove an image and associated results if criteria are met."""

        submission = Submission.query.get_or_404(hash_val)  # type: ignore
        image = Image.query.get_or_404(submission.image_hash)  # type: ignore

        # Check if image is at least 5 minutes old
        current_time = time.time()
        age_seconds = current_time - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": "Image must be at least 5 minutes old. "
                        f"Current age: {int(age_seconds)}s"
                    }
                ),
                403,
            )

        # Get all IPs that uploaded this image
        upload_logs = UploadLog.query.filter_by(image_hash=image.hash).all()
        unique_ips = set()
        for log in upload_logs:
            if log.ip_address:
                unique_ips.add(log.ip_address)

        # Check if only one IP has uploaded this image
        if len(unique_ips) > 1:
            return (
                jsonify(
                    {
                        "error": "Image uploaded from multiple IP addresses. Removal is not "
                        "allowed.",
                        "ip_count": len(unique_ips),
                    }
                ),
                403,
            )

        # Create archive directory if it doesn't exist
        REMOVED_IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)

        # Archive the original image (copy to removed_images folder with metadata)
        original_image_path = Path(image.file)
        if original_image_path.exists():
            dt = datetime.now(timezone.utc).isoformat()
            archive_filename = f"{image.hash}_{submission.hash}_{dt}{original_image_path.suffix}"
            archive_path = REMOVED_IMAGES_FOLDER / archive_filename
            try:
                shutil.copy2(original_image_path, archive_path)
            except Exception as e:
                sentry_sdk.capture_exception(e)
                return jsonify({"error": "Failed to archive image"}), 500

        # Delete the results folder
        result_path = RESULT_FOLDER / str(image.hash) / str(submission.hash)
        try:
            if result_path.exists():
                shutil.rmtree(result_path)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({"error": "Failed to delete results"}), 500

        # Delete submission from database
        try:
            db.session.delete(submission)  # pylint: disable=no-member

            # If this was the last submission for this image, delete the image entry too
            if len(image.submissions) <= 1:
                # Also delete the original image file
                if original_image_path.exists():
                    original_image_path.unlink()
                db.session.delete(image)  # pylint: disable=no-member

            db.session.commit()  # pylint: disable=no-member
        except Exception as e:
            db.session.rollback()  # pylint: disable=no-member
            sentry_sdk.capture_exception(e)
            return jsonify({"error": "Failed to update database"}), 500

        # Note: UploadLog entries are intentionally kept for audit purposes

        return jsonify({"message": "Image successfully removed"}), 200

    @app.route("/remove_password/<hash_val>", methods=["POST"])
    def remove_password(hash_val: str) -> tuple[Response, int]:
        """Remove a password from a submission if criteria are met."""

        submission = Submission.query.get_or_404(hash_val)  # type: ignore

        if not submission.password:
            return jsonify({"error": "No password to remove"}), 400

        # Check if submission is at least 5 minutes old
        current_time = time.time()
        age_seconds = current_time - submission.date
        if age_seconds < REMOVAL_MIN_AGE_SECONDS:
            return (
                jsonify(
                    {
                        "error": f"Submission must be at least 5 minutes old. "
                        f"Current age: {int(age_seconds)}s"
                    }
                ),
                403,
            )

        # Get all IPs that uploaded this specific submission (password combination)
        upload_logs = UploadLog.query.filter_by(submission_hash=submission.hash).all()
        unique_ips = set()
        for log in upload_logs:
            if log.ip_address:
                unique_ips.add(log.ip_address)

        # Check if only one IP has uploaded this submission
        if len(unique_ips) > 1:
            return (
                jsonify(
                    {
                        "error": "Submission uploaded from multiple IP addresses. "
                        "Password removal is not allowed.",
                        "ip_count": len(unique_ips),
                    }
                ),
                403,
            )

        # Remove the password
        try:
            submission.password = None
            db.session.commit()  # pylint: disable=no-member
        except Exception as e:
            db.session.rollback()  # pylint: disable=no-member
            sentry_sdk.capture_exception(e)
            return jsonify({"error": "Failed to remove password"}), 500

        return jsonify({"message": "Password successfully removed"}), 200

    @app.route("/image/<img_name>")
    @app.route("/image/<hash_val>/<img_name>")
    def get_image(hash_val: Optional[str] = None, img_name: Optional[str] = None) -> Response:
        """
        Download the image with a specific name (usually ones generated with
        decomposer) for a given submission hash.
        """

        if img_name is None:
            return abort(404, description="Image not found or unsupported format")

        if hash_val is not None:
            submission = Submission.query.filter_by(hash=hash_val).first_or_404()
            image = Image.query.get_or_404(submission.image_hash)  # type: ignore

            output_dir = RESULT_FOLDER / str(image.hash) / str(submission.hash)
            output_file = output_dir / Path(img_name).name
        else:
            hash_val = img_name.split(".")[0]  # Extract hash from the image name
            image = Image.query.filter_by(hash=hash_val).first_or_404()
            output_file = Path(image.file)  # type: ignore

        if (not output_file.exists()) or (output_file.suffix.lower() not in IMAGE_EXTENSIONS):
            return abort(404, description="Image not found or unsupported format")

        return send_file(output_file, as_attachment=True)

    @app.route("/ads.txt")
    def google_ads() -> str:
        """Google Ads required file"""
        return "google.com, pub-2324718887045017, DIRECT, f08c47fec0942fa0"

    return app


if __name__ == "__main__":
    my_app = create_app()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    my_app.run(host="0.0.0.0", port=5000, debug=debug_mode)
