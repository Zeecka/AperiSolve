"""This module defines the database models for the Aperisolve application."""

from datetime import datetime, timezone
from decimal import Decimal

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, text

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
    # Optional logical batch identifier for grouping submissions
    batch_id: Column[str] = Column(String(50), index=True, nullable=True)

    # Foreign key to Image
    image_hash = Column(String, db.ForeignKey("image.hash"), nullable=False)


def init_db(app: Flask) -> None:
    """Initialize the database with the given Flask app.

    Also performs a lightweight runtime schema adjustment to add new columns
    ("batch_id") if the table already exists but the column does not.
    This keeps backward compatibility without a dedicated migration framework.
    """
    with app.app_context():
        engine = db.engine
        conn = engine.connect()
        try:
            if not engine.dialect.has_table(conn, "image"):
                print("Creating database...")
                db.create_all()
                print("Database created successfully.")
            else:
                # Lightweight check for missing batch_id column
                inspector = db.inspect(engine)
                submission_cols = {c["name"] for c in inspector.get_columns("submission")}
                if "batch_id" not in submission_cols:
                    try:
                        conn.execute(text("ALTER TABLE submission ADD COLUMN batch_id VARCHAR(50);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_submission_batch_id ON submission (batch_id);"))
                        print("Added column 'batch_id' to submission table.")
                    except Exception as exc:  # pragma: no cover - best effort
                        print(f"Warning: could not add batch_id column automatically: {exc}")
        finally:
            conn.close()
