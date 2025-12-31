# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""This module defines the database models for the Aperi'Solve application."""

import itertools
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from shutil import rmtree

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String

from aperisolve.analyzers.utils import PNG, get_resolutions, get_valid_depth_color_pairs

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
    """IHDR CRC lookup table"""

    iid = Column(Integer, primary_key=True, autoincrement=True)
    crc = Column(BigInteger, nullable=False)
    packed = Column(BigInteger, nullable=False)


def fill_ihdr_db() -> None:
    """
    Creates a database of common PNG IHDR (Image Header) entries by generating
    combinations of standard PNG parameters such as resolutions, bit depths,
    color types, and interlace methods. The function checks for existing entries
    in the database to avoid duplicates and inserts new entries in batches of
    5000, committing the changes to the database periodically.

    Returns:
        None
    """
    # Standard PNG IHDR parameters
    resolutions = get_resolutions()
    bit_color_pairs = get_valid_depth_color_pairs()
    interlace_methods = [0, 1]

    combinations = itertools.product(
        resolutions,
        bit_color_pairs,
        interlace_methods,
    )

    count = 0

    with db.session.no_autoflush:  # pylint: disable=no-member
        for size, (bd, ct), inter in combinations:
            p = PNG(size=size, bit_depth=bd, color_type=ct, interlace=inter)

            exists = db.session.execute(  # pylint: disable=no-member
                db.select(IHDR.iid).where(IHDR.packed == p.packed)
            ).first()

            if exists:  # Skip if already present
                continue

            db.session.add(  # pylint: disable=no-member
                IHDR(packed=p.packed, crc=p.crc)
            )
            count += 1

            if count % 5000 == 0:
                print(f"Inserted {count} common IHDR entries...")
                db.session.commit()

    db.session.commit()  # pylint: disable=no-member
    print(f"Precomputed {count} common IHDR entries.")


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
    with app.app_context():
        if getenv("CLEAR_AT_RESTART", "0") == "1":  # Force clear if CLEAR_AT_RESTART
            print("Clearing database and file system at restart...")
            db.session.remove()  # pylint: disable=no-member
            db.drop_all()
            rmtree(Path("./results"), ignore_errors=True)  # Clear results folder

        db.create_all()
        print("Database structure created successfully.")

        if getenv("SKIP_IHDR_FILL", "0") == "1":
            print("Skipping IHDR lookup table fill as per configuration.")
        else:
            print("Filling IHDR lookup table...")
            fill_ihdr_db()
            print("IHDR table filled successfully.")
