"""This module defines the database models for the Aperisolve application."""

import zlib
import itertools

from datetime import datetime, timezone
from decimal import Decimal

from aperisolve.analyzers.utils import pack_ihdr
from aperisolve.config import MAX_HEIGHT, MAX_WIDTH
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, BigInteger

db: SQLAlchemy = SQLAlchemy()


class Image(db.Model):  # type: ignore
    """Model representing an image file in the database."""

    hash: Column[str] = Column(
        String(64), primary_key=True, unique=True, nullable=False
    )
    file: Column[str] = Column(String(128), unique=True, nullable=False)
    size: Column[int] = Column(Integer, nullable=False)
    first_submission_date: Column[datetime] = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_submission_date: Column[datetime] = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    upload_count: Column[int] = Column(Integer)
    submissions = db.relationship("Submission", backref="image", lazy=True)


class Submission(db.Model):  # type: ignore
    """Model representing a file submission for analysis.
    Submissions are defined with a filename, password, image content, and analysis
    option.
    """

    hash: Column[str] = Column(
        String(128), primary_key=True, unique=True, nullable=False
    )
    filename: Column[str] = Column(String(128), nullable=False)
    password: Column[str] = Column(String(128))
    deep_analysis: Column[bool] = Column(Boolean, default=False)
    status: Column[str] = Column(String(20), default="pending")
    date: Column[Decimal] = Column(
        Float, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Foreign key to Image
    image_hash = Column(String, db.ForeignKey("image.hash"), nullable=False)


class IHDR(db.Model):  # type: ignore
    """IHDR CRC lookup table"""
    iid : Column[int] = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    crc : Column[int] = Column(BigInteger)
    packed : Column[int] = Column(Integer)


def create_crc_db() -> None:
    w = range(1, MAX_WIDTH + 1)
    h = range(1, MAX_HEIGHT + 1)

    # Standard PNG IHDR parameters
    bit_depth = [1, 2, 4, 8, 16]
    color_type = [0, 2, 3, 4, 6]
    compression_method = [0]  # This is always 0 according to the PNG spec
    filter_method = [0]  # This is always 0 according to the PNG spec
    interlace_method = [0, 1]

    # Create the generator
    all_combinations = itertools.product(
        w, h, bit_depth, color_type, compression_method, filter_method, interlace_method
    )

    count = 0
    max_count = MAX_WIDTH * MAX_HEIGHT * len(bit_depth) * len(color_type) * len(interlace_method)
    for w_val, h_val, bd, ct, comp, filt, inter in all_combinations:
        count +=1
        # Construct IHDR chunk data
        ihdr_data = (
            w_val.to_bytes(4, "big")
            + h_val.to_bytes(4, "big")
            + bytes([bd, ct, comp, filt, inter])
        )

        # Calculate CRC
        crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF

        # Compute packed
        packed = pack_ihdr(w_val, h_val, bd, ct, inter)

        # Create and add IHDR entry to database
        ihdr_entry = IHDR(crc=crc, packed=packed)
        db.session.add(ihdr_entry)

        if count % 10000 == 0:
            print(f"Inserted {count}/{max_count} ({int((count*100)/max_count)}%) IHDR entries...")
            db.session.commit()

    # Commit all entries
    db.session.commit()


def init_db(app: Flask) -> None:
    """Initialize the database with the given Flask app."""
    with app.app_context():
        if not db.engine.dialect.has_table(db.engine.connect(), "image"):
            print("Creating database...")
            db.create_all()
            print("Database structure created successfully.")
            print("Filling IHDR lookup table...")
            create_crc_db()
            print("IHDR table filled successfully.")
