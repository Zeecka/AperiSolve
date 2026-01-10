"""
Database initialization script.
This script is meant to be run ONCE at deploy time, never from Gunicorn or runtime code.
If CLEAR_AT_RESTART is set, database will be reset at launch time.
"""

import os
from shutil import rmtree

from sqlalchemy import inspect

from ..app import create_app
from ..config import RESULT_FOLDER
from ..models import db, fill_ihdr_db


def main() -> None:
    """Database initialization main function."""
    reset = os.getenv("CLEAR_AT_RESTART") == "1"

    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if reset:

            # Delete result folder content
            if RESULT_FOLDER.exists():
                for item in RESULT_FOLDER.iterdir():
                    try:
                        if item.is_dir():
                            rmtree(item)
                        else:
                            item.unlink()
                    except Exception:
                        continue

            print("⚠️  CLEAR_AT_RESTART=1 detected")
            print("💥 Dropping all tables...")
            db.drop_all()
            print("🗄️  Recreating schema...")
            db.create_all()

        else:
            if not tables:
                print("🗄️  Creating database schema...")
                db.create_all()
            else:
                print("🗄️  Database schema already exists")

        print("📦 Filling IHDR static data...")
        fill_ihdr_db()

        print("✅ Database initialization complete")

    RESULT_FOLDER.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
