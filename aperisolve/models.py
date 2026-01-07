# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""This module defines the database models for the Aperi'Solve application."""

import itertools
import struct
import sys
import zlib
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from shutil import rmtree

from flask import Flask
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


def fill_ihdr_db() -> None:
    """
    Populate IHDR table with common PNG configurations.

    Creates entries for all combinations of:
    - Common resolutions (from get_resolutions())
    - Valid bit depth/color type pairs (from get_valid_depth_color_pairs())
    - Interlace methods (0, 1)

    Computes CRC for each combination and stores parameters directly.
    """

    # Skip if table already has entries
    if db.session.query(IHDR.iid).first() is not None:
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

            # Check if entry already exists
            exists = db.session.execute(
                db.select(IHDR.iid).where(
                    db.and_(
                        IHDR.crc == crc,
                        IHDR.width == width,
                        IHDR.height == height,
                        IHDR.bit_depth == bit_depth,
                        IHDR.color_type == color_type,
                        IHDR.interlace == interlace,
                    )
                )
            ).first()

            if exists:
                continue

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

        # Final commit
        if count % 5000 != 0:
            db.session.commit()
            print(f"Inserted {count} total IHDR entries.")


def init_db(app: Flask) -> None:
    """
    Initialize the database by creating tables and populating lookup data.

    This function creates the database schema if it doesn't already exist,
    and populates the CRC lookup table for PNG IHDR validation.

    Args:
        app (Flask): The Flask application instance used to establish the application context
                    for database operations.

    Returns:
        None

    Side Effects:
        - Creates all database tables if the "image" table doesn't exist
        - Populates the IHDR CRC lookup table with initial data
        - Prints status messages to console during initialization
    """
    # Detect if running as RQ worker by checking command line
    # Worker: /usr/local/bin/rq worker ...
    # Web: /usr/local/bin/flask run ... or gunicorn/wsgi
    is_worker = any("rq" in arg and "flask" not in arg for arg in sys.argv[:2])

    with app.app_context():
        # Workers should never clear the database
        if not is_worker and getenv("CLEAR_AT_RESTART", "0") == "1":
            print("Clearing database and file system at restart...")
            db.session.remove()  # pylint: disable=no-member
            db.drop_all()
            rmtree(Path("./results"), ignore_errors=True)  # Clear results folder

        # Always create tables (idempotent - safe to call multiple times)
        db.create_all()
        print("Database structure created successfully.")

        # Workers should never fill IHDR table
        if is_worker:
            print("Running as worker, skipping IHDR table fill.")
        else:
            fill_ihdr_db()
