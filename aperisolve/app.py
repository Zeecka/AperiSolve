"""AperiSolve Flask application."""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from redis import Redis
from rq import Queue

from .cleanup import cleanup_old_entries
from .config import IMAGE_EXTENSIONS, RESULT_FOLDER, WORKER_FILES
from .models import Image, Submission, db, init_db

app: Flask = Flask(__name__)
app.json.sort_keys = False  # type: ignore
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_CONTENT_LENGTH", 1024 * 1024)
)
RESULT_FOLDER.mkdir(parents=True, exist_ok=True)


db.init_app(app)
init_db(app)
redis_conn = Redis(host="redis", port=6379)
queue = Queue(connection=redis_conn)


@app.errorhandler(413)
def too_large(_: Any) -> tuple[Response, int]:
    """Error Handler for Max File Size."""
    return jsonify({"error": "Image size exceeded"}), 413


@app.errorhandler(404)
def not_found(_: Any) -> str:
    """Error Handler for 404 not found."""
    return render_template("error.html", message="Ressource not found", statuscode=404)


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

    if (
        "." not in image.filename
        or Path(image.filename).suffix.lower() not in IMAGE_EXTENSIONS
    ):
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

    # If submission already exists, return submission hash
    if submission_path.exists():
        submission: Submission = Submission.query.filter_by(
            hash=submission_hash
        ).first()
        return jsonify({"submission_hash": submission.hash}), 200

    # If image is new, create a new Image entry
    new_img_path = RESULT_FOLDER / img_hash / image_name
    if not new_img_path.parent.exists():
        new_img_path.parent.mkdir(parents=True, exist_ok=True)
        with open(new_img_path, "wb") as f:  # Write file to disk
            f.write(image_data)

        new_img = Image(
            file=str(new_img_path),
            hash=img_hash,
            size=len(image_data),
            upload_count=0,
            first_submission_date=datetime.now(timezone.utc),
            last_submission_date=datetime.now(timezone.utc),
        )
        db.session.add(new_img)
        db.session.commit()

    sub_img = Image.query.filter_by(hash=img_hash).first()  # type: ignore
    sub_img.upload_count += 1
    db.session.commit()

    # Create new Submission entry
    submission_path.mkdir(parents=True, exist_ok=True)
    submission = Submission(
        filename=image.filename,
        password=password,
        deep_analysis=deep_analysis,
        hash=submission_hash,
        status="pending",
        date=time.time(),
        image_hash=sub_img.hash,  # type: ignore
    )
    db.session.add(submission)

    db.session.commit()  # Commit to save the new Image and Submission
    # Start the analysis jobs
    queue.enqueue("aperisolve.workers.analyze_image", submission.hash, job_timeout=300)

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
        }
    )  # type: ignore


@app.route("/result/<hash_val>", methods=["GET"])
def get_result(hash_val: str) -> tuple[Response, int]:
    """Get the analysis results of a submission."""
    submission = Submission.query.get_or_404(hash_val)
    image = Image.query.get_or_404(submission.image_hash)  # type: ignore

    result_path = (
        RESULT_FOLDER / str(image.hash) / str(submission.hash) / "results.json"
    )

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


@app.route("/image/<img_name>")
@app.route("/image/<hash_val>/<img_name>")
def get_image(
    hash_val: Optional[str] = None, img_name: Optional[str] = None
) -> Response:
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

    if (not output_file.exists()) or (
        output_file.suffix.lower() not in IMAGE_EXTENSIONS
    ):
        return abort(404, description="Image not found or unsupported format")

    return send_file(output_file, as_attachment=True)


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
