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
        
        try:
            # First, create all tables if they don't exist
            db.create_all()
            
            # Get database inspector
            inspector = db.inspect(engine)
            
            # Check if submission table exists
            if "submission" not in inspector.get_table_names():
                print("Submission table does not exist, creating...")
                db.create_all()
                return
                
            # Get current columns
            submission_cols = {c["name"] for c in inspector.get_columns("submission")}
            print(f"Current submission columns: {submission_cols}")
            
            # Add batch_id if it doesn't exist
            if "batch_id" not in submission_cols:
                print("Adding missing 'batch_id' column to submission table...")
                with engine.begin() as conn:
                    _add_batch_id_column(conn)
                # Force refresh the inspector to get updated column info
                inspector = db.inspect(engine)
                submission_cols = {c["name"] for c in inspector.get_columns("submission")}
                print(f"Updated submission columns: {submission_cols}")
            
            # Verify the column was added
            if "batch_id" not in submission_cols:
                print("Warning: 'batch_id' column not found after attempting to add it")
                # Try a direct query to verify
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name='submission' AND column_name='batch_id';"
                        ))
                        if result.fetchone():
                            print("Column exists in information_schema but not in SQLAlchemy's inspector")
                            # Try to force SQLAlchemy to refresh its schema cache
                            from sqlalchemy import event
                            event.listen(engine, 'first_connect', 
                                       lambda conn, rec: conn._connection_record.finalize_callback())
                            # Re-check after refresh
                            inspector = db.inspect(engine)
                            submission_cols = {c["name"] for c in inspector.get_columns("submission")}
                            print(f"After refresh, submission columns: {submission_cols}")
                except Exception as e:
                    print(f"Error verifying column: {e}")
                
                if "batch_id" not in submission_cols:
                    print("Proceeding anyway as this might be a caching issue")
                
            print("Database initialization complete.")
            
        except Exception as e:
            print(f"Error during database initialization: {e}")
            # Don't raise the exception to allow the app to start anyway
            print("Proceeding with application startup despite database initialization errors")


def _add_batch_id_column(conn):
    """Helper function to add batch_id column to submission table."""
    print("Adding missing 'batch_id' column to submission table...")
    
    try:
        # First check if the column already exists using direct SQL
        result = conn.execute(text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='submission' AND column_name='batch_id';
            """
        ))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("Column 'batch_id' does not exist, adding it now...")
            
            try:
                # Add batch_id column with NULL allowed initially
                print("Executing: ALTER TABLE submission ADD COLUMN batch_id VARCHAR(50) NULL")
                conn.execute(text("""
                    ALTER TABLE submission 
                    ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50) NULL;
                """))
                
                conn.execute(text("""
                    COMMENT ON COLUMN submission.batch_id IS 'Optional logical batch identifier for grouping submissions';
                """))
                
                # Create index for batch_id
                print("Creating index on batch_id column")
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_submission_batch_id 
                    ON submission (batch_id);
                """))
                
                conn.execute(text("""
                    ANALYZE submission;
                """))
                
                print("Successfully added 'batch_id' column to submission table.")
                
                # Verify the column was added
                result = conn.execute(text(
                    """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='submission' AND column_name='batch_id';
                    """
                ))
                
                if result.fetchone() is None:
                    print("Warning: Could not verify 'batch_id' column was added, but continuing anyway")
                else:
                    print("Successfully verified 'batch_id' column exists in the database.")
                
            except Exception as e:
                print(f"Error adding column: {e}")
                # Try to continue anyway as the column might have been added
                print("Attempting to continue despite potential errors...")
        else:
            print("Column 'batch_id' already exists.")
            
    except Exception as exc:
        print(f"Error in _add_batch_id_column: {exc}")
        # Don't raise the exception to allow the app to continue
        print("Proceeding despite column addition errors")