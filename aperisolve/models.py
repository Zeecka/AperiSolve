"""Database models for the Aperi'Solve application."""

import itertools
import shutil
import struct
import time
import zlib
from datetime import UTC, datetime, timedelta
from typing import cast

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
    and_,
    or_,
)
from sqlalchemy.exc import SQLAlchemyError

from aperisolve.config import MAX_STORE_TIME, RESULT_FOLDER, STALE_SUBMISSION_CUTOFF
from aperisolve.utils.utils import get_resolutions, get_valid_depth_color_pairs

db: SQLAlchemy = SQLAlchemy()


class Image(db.Model):
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


class Submission(db.Model):
    """Model representing a file submission for analysis.

    Submissions are defined with a filename, password, image content, and analysis option.
    """

    hash = Column(String(128), primary_key=True, unique=True, nullable=False)
    filename = Column(String(128), nullable=False)
    password = Column(String(128))
    deep_analysis = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    date = Column(Float, nullable=False, default=time.time)

    image_hash = Column(String, db.ForeignKey("image.hash"), nullable=False)


class IHDR(db.Model):
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
        bit_depth = cast("int", self.bit_depth)
        color_type = cast("int", self.color_type)
        interlace = cast("int", self.interlace)
        return (
            struct.pack(">I", self.width)
            + struct.pack(">I", self.height)
            + bytes(
                [
                    bit_depth,
                    color_type,
                    0,
                    0,
                    interlace,
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


class UploadLog(db.Model):
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
        previous_autoflush = db.session.autoflush
        db.session.autoflush = False
        try:
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
            db.session.commit()  # flush the trailing partial batch
        finally:
            db.session.autoflush = previous_autoflush
    except SQLAlchemyError:
        db.session.rollback()


def _cleanup_submissions(now: float) -> None:
    """Delete stale pending submissions and completed ones whose results vanished."""
    stale = Submission.query.filter(
        Submission.status.in_(("pending", "running")),
        Submission.date < now - STALE_SUBMISSION_CUTOFF,
    ).all()
    for submission in stale:
        db.session.delete(submission)
    db.session.commit()

    for submission in Submission.query.filter_by(status="completed").all():
        result_path = RESULT_FOLDER / str(submission.image_hash) / str(submission.hash)
        if not (result_path / "results.json").exists():
            shutil.rmtree(result_path, ignore_errors=True)
            db.session.delete(submission)
    db.session.commit()


def _cleanup_images() -> None:
    """Delete expired and orphaned images with their result folders."""
    now = datetime.now(UTC).replace(tzinfo=None)
    expired_cutoff = now - timedelta(seconds=MAX_STORE_TIME)
    orphan_cutoff = now - timedelta(seconds=STALE_SUBMISSION_CUTOFF)

    candidates = Image.query.filter(
        or_(
            Image.last_submission_date < expired_cutoff,
            and_(
                ~Image.submissions.any(),
                Image.last_submission_date < orphan_cutoff,
            ),
        ),
    ).all()

    for img in candidates:
        img_hash = str(img.hash)
        try:
            for submission in img.submissions:
                db.session.delete(submission)
            db.session.delete(img)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            continue
        # Remove files only once the DB delete is committed, so a failed
        # commit can't leave a row pointing at vanished files.
        shutil.rmtree(RESULT_FOLDER / img_hash, ignore_errors=True)


def cleanup_old_entries() -> None:
    """Clean up old and incomplete entries from the database and file system.

    Deletions are committed in small batches so one bad row cannot roll back
    the whole sweep.
    """
    try:
        _cleanup_submissions(time.time())
    except SQLAlchemyError:
        db.session.rollback()
    _cleanup_images()
