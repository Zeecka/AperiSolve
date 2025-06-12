"""This module defines the database models for the Aperisolve application."""

from datetime import datetime, timezone
from decimal import Decimal

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

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


def init_db(app: Flask) -> None:
    """Initialize the database with the given Flask app."""
    with app.app_context():
        if not db.engine.dialect.has_table(db.engine.connect(), "image"):
            print("Creating database...")
            db.create_all()
            print("Database created successfully.")
