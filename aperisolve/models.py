# flake8: noqa: E203,E501,W503
# pylint: disable=E1101,C0413,W0212,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""This module defines the database models for the Aperi'Solve application."""

import itertools
import shutil
import struct
import time
import zlib
from datetime import datetime, timezone

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

from aperisolve.config import MAX_PENDING_TIME, MAX_STORE_TIME, RESULT_FOLDER
from aperisolve.utils.utils import get_resolutions, get_valid_depth_color_pairs

db: SQLAlchemy = SQLAlchemy()


class Image(db.Model):  # type: ignore
    """Model representing an image file in the database."""

    hash = Column(String(64), primary_key=True, unique=True, nullable=False)
    file = Column(String(128), unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    first_submission_date = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_submission_date = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    upload_count = Column(Integer)
    submissions = db.relationship("Submission", backref="image", lazy=True)


class Submission(db.Model):  # type: ignore
    """Model representing a file submission for analysis.
    Submissions are defined with a filename, password, image content, and analysis
    option.
    """

    hash = Column(String(128), primary_key=True, unique=True, nullable=False)
    filename = Column(String(128), nullable=False)
    password = Column(String(128))
    deep_analysis = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    date = Column(Float, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Foreign key to Image
    image_hash = Column(String, db.ForeignKey("image.hash"), nullable=False)


class IHDR(db.Model):  # type: ignore
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
                    0,  # compression method (always 0)
                    0,  # filter method (always 0)
                    self.interlace,
                ]
            )
        )

    @staticmethod
    def compute_crc(
        width: int, height: int, bit_depth: int, color_type: int, interlace: int
    ) -> int:
        """Compute CRC32 for IHDR chunk."""
        ihdr_data = (
            struct.pack(">I", width)
            + struct.pack(">I", height)
            + bytes([bit_depth, color_type, 0, 0, interlace])
        )
        return zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF


class UploadLog(db.Model):  # type: ignore
    """Model representing upload activity logs."""

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False)  # IPv6 max length is 45
    user_agent = Column(String(512), nullable=True)
    upload_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    image_hash = Column(String(64), nullable=False)
    submission_hash = Column(String(128), nullable=True)
    filename = Column(String(128), nullable=True)


def fill_ihdr_db() -> None:
    """
    Populate IHDR table with common PNG configurations.

    Creates entries for all combinations of:
    - Common resolutions (from get_resolutions())
    - Valid bit depth/color type pairs (from get_valid_depth_color_pairs())
    - Interlace methods (0, 1)

    Computes CRC for each combination and stores parameters directly.
    """
    try:
        # Skip if table already has entries (check before doing any work)
        count_query = db.session.query(IHDR.iid).limit(1)
        if db.session.execute(count_query).first() is not None:
            print("IHDR table already populated, skipping fill.")
            return

        resolutions = get_resolutions()
        bit_color_pairs = list(get_valid_depth_color_pairs())
        interlace_methods = [0, 1]

        combinations = itertools.product(
            resolutions,
            bit_color_pairs,
            interlace_methods,
        )
        count = 0

        with db.session.no_autoflush:
            for (width, height), (bit_depth, color_type), interlace in combinations:
                # Compute CRC directly
                crc = IHDR.compute_crc(width, height, bit_depth, color_type, interlace)

                # Add new entry
                db.session.add(
                    IHDR(
                        crc=crc,
                        width=width,
                        height=height,
                        bit_depth=bit_depth,
                        color_type=color_type,
                        interlace=interlace,
                    )
                )

                count += 1
                if count % 5000 == 0:
                    print(f"Inserted {count} IHDR entries...")
                    db.session.commit()
            print(f"Inserted {count} total IHDR entries.")

    except Exception as e:
        print(f"Error filling IHDR table: {e}")
        db.session.rollback()


def cleanup_old_entries() -> None:
    """
    Clean up old and incomplete entries from the database and file system.

    This function performs two main cleanup operations:

    1. Submission cleanup:
       - Deletes submissions with "pending" or "running" status that have exceeded
         the maximum allowed processing time (MAX_PENDING_TIME).
       - Deletes completed submissions ("done" status) that have missing or buggy
         results (results.json file not found).

    2. Image cleanup:
       - Deletes images older than MAX_STORE_TIME along with all associated
         submissions and their result folders.
       - Deletes orphaned images (with no submissions) older than MAX_PENDING_TIME
         and removes their associated result folders from the file system.

    All database changes are committed at the end of the operation.

    Returns:
        None
    """
    now = time.time()
    for submission in Submission.query.all():  # type: ignore
        if (
            submission.status in ("pending", "running")  # type: ignore
            and now - submission.date > MAX_PENDING_TIME  # type: ignore
        ):
            # Processing took too long, delete
            db.session.delete(submission)  # pylint: disable=no-member
        elif submission.status == "done":  # type: ignore
            # Search for buggy results, delete
            result_path = RESULT_FOLDER / str(submission.image_hash) / str(submission.hash)
            result_file = result_path / "results.json"
            if not result_file.exists():
                db.session.delete(submission)  # pylint: disable=no-member
                shutil.rmtree(result_path)

    # Delete "old" images
    for img in Image.query.all():  # type: ignore
        if img.last_submission_date.tzinfo is None:
            img_date = img.last_submission_date.replace(tzinfo=timezone.utc)
        else:
            img_date = img.last_submission_date
        delay = datetime.now(timezone.utc) - img_date
        img_fold = RESULT_FOLDER / img.hash
        if delay.total_seconds() > MAX_STORE_TIME:
            for s in img.submissions:
                db.session.delete(s)  # pylint: disable=no-member
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)  # pylint: disable=no-member

        # Delete Images with missing submission
        if len(img.submissions) == 0 and delay.total_seconds() > MAX_PENDING_TIME:
            if img_fold.exists():
                shutil.rmtree(img_fold)  # type: ignore
            db.session.delete(img)  # pylint: disable=no-member

    db.session.commit()  # pylint: disable=no-member
