"""Database models for the Aperi'Solve application."""

import itertools
import shutil
import struct
import time
import zlib
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    SmallInteger,
    String,
)
from sqlalchemy.exc import SQLAlchemyError

from aperisolve.config import MAX_PENDING_TIME, MAX_STORE_TIME, RESULT_FOLDER
from aperisolve.utils.utils import get_resolutions, get_valid_depth_color_pairs

db: SQLAlchemy = SQLAlchemy()


class Image(db.Model):  # type: ignore[reportGeneralTypeIssues]
    """Model representing an image file in the database."""

    hash = Column(String(64), primary_key=True, unique=True, nullable=False)
    file = Column(String(128), unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    first_submission_date = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_submission_date = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    upload_count = Column(Integer)
    submissions = db.relationship("Submission", backref="image", lazy=True)


class Submission(db.Model):  # type: ignore[reportGeneralTypeIssues]
    """Model representing a file submission for analysis.

    Submissions are defined with a filename, password, image content, and analysis option.
    """

    hash = Column(String(128), primary_key=True, unique=True, nullable=False)
    filename = Column(String(128), nullable=False)
    password = Column(String(128))
    deep_analysis = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    date = Column(Float, nullable=False, default=lambda: datetime.now(UTC))

    image_hash = Column(String, db.ForeignKey("image.hash"), nullable=False)


class IHDR(db.Model):  # type: ignore[reportGeneralTypeIssues]
    """IHDR CRC lookup table with direct parameter storage."""

    iid = Column(Integer, primary_key=True, autoincrement=True)
    crc = Column(BigInteger, nullable=False, index=True)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bit_depth = Column(SmallInteger, nullable=False)
    color_type = Column(SmallInteger, nullable=False)
    interlace = Column(SmallInteger, nullable=False)

    def to_ihdr_bytes(self) -> bytes:
        """Convert database record to IHDR chunk data (13 bytes)."""
        return (
            struct.pack(">I", self.width)
            + struct.pack(">I", self.height)
            + bytes(
                [
                    self.bit_depth,
                    self.color_type,
                    0,
                    0,
                    self.interlace,
                ],
            )
        )

    @staticmethod
    def compute_crc(
        width: int,
        height: int,
        bit_depth: int,
        color_type: int,
        interlace: int,
    ) -> int:
        """Compute CRC32 for IHDR chunk."""
        ihdr_data = (
            struct.pack(">I", width)
            + struct.pack(">I", height)
            + bytes([bit_depth, color_type, 0, 0, interlace])
        )
        return zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF


class UploadLog(db.Model):  # type: ignore[reportGeneralTypeIssues]
    """Model representing upload activity logs."""

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(512), nullable=True)
    upload_time = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    image_hash = Column(String(64), nullable=False)
    submission_hash = Column(String(128), nullable=True)
    filename = Column(String(128), nullable=True)


def fill_ihdr_db() -> None:
    """Populate IHDR table with common PNG configurations."""
    try:
        count_query = db.session.query(IHDR.iid).limit(1)
        if db.session.execute(count_query).first() is not None:
            return

        resolutions = get_resolutions()
        bit_color_pairs = list(get_valid_depth_color_pairs())
        interlace_methods = [0, 1]
        combinations = itertools.product(resolutions, bit_color_pairs, interlace_methods)

        count = 0
        with db.session.no_autoflush:
            for (width, height), (bit_depth, color_type), interlace in combinations:
                crc = IHDR.compute_crc(width, height, bit_depth, color_type, interlace)
                db.session.add(
                    IHDR(
                        crc=crc,
                        width=width,
                        height=height,
                        bit_depth=bit_depth,
                        color_type=color_type,
                        interlace=interlace,
                    ),
                )
                count += 1
                if count % 5000 == 0:
                    db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def _cleanup_submissions(now: float) -> None:
    """Delete stale or invalid submissions."""
    for submission in Submission.query.all():
        if submission.status in ("pending", "running") and now - submission.date > MAX_PENDING_TIME:
            db.session.delete(submission)
            continue

        if submission.status == "done":
            result_path = RESULT_FOLDER / str(submission.image_hash) / str(submission.hash)
            result_file = result_path / "results.json"
            if not result_file.exists():
                db.session.delete(submission)
                shutil.rmtree(result_path)


def _cleanup_images() -> None:
    """Delete old and orphaned images with their result folders."""
    for img in Image.query.all():
        if img.last_submission_date.tzinfo is None:
            img_date = img.last_submission_date.replace(tzinfo=UTC)
        else:
            img_date = img.last_submission_date

        delay = datetime.now(UTC) - img_date
        img_folder = RESULT_FOLDER / img.hash

        if delay.total_seconds() > MAX_STORE_TIME:
            for submission in img.submissions:
                db.session.delete(submission)
            if img_folder.exists():
                shutil.rmtree(img_folder)
            db.session.delete(img)
            continue

        if len(img.submissions) == 0 and delay.total_seconds() > MAX_PENDING_TIME:
            if img_folder.exists():
                shutil.rmtree(img_folder)
            db.session.delete(img)


def cleanup_old_entries() -> None:
    """Clean up old and incomplete entries from the database and file system."""
    now = time.time()
    _cleanup_submissions(now)
    _cleanup_images()
    db.session.commit()
