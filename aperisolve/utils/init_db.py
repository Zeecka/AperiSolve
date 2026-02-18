"""Database initialization script.

This script is meant to be run ONCE at deploy time, never from Gunicorn or runtime code.
If CLEAR_AT_RESTART is set, database will be reset at launch time.
"""

import os
from shutil import rmtree

import sentry_sdk
from sqlalchemy import inspect

from aperisolve.app import create_app
from aperisolve.config import RESULT_FOLDER
from aperisolve.models import db, fill_ihdr_db


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
                    except OSError as exc:
                        sentry_sdk.capture_exception(exc)

            db.drop_all()
            db.create_all()

        elif not tables:
            db.create_all()
        else:
            pass

        fill_ihdr_db()


        RESULT_FOLDER.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
