"""Aperi'Solve configuration variables."""

from os import getenv
from pathlib import Path

PROJECT_VERSION = getenv("PROJECT_VERSION", "development")

REMOVAL_MIN_AGE_SECONDS = int(getenv("REMOVAL_MIN_AGE_SECONDS", "300"))  # 5 minutes
MAX_PENDING_TIME = int(getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default
MAX_STORE_TIME = int(getenv("MAX_STORE_TIME", "259200"))  # 3 days by default
MAX_CONTENT_LENGTH = int(getenv("MAX_CONTENT_LENGTH", "1048576"))  # 1 MB by default
CLEAR_AT_RESTART = int(getenv("CLEAR_AT_RESTART", "0"))

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]
WORKER_FILES = ["binwalk", "foremost", "steghide", "stegoveritas", "zsteg", "openstego", "pcrt", "jpseek"]

GOOGLE_ADS_TXT = getenv("GOOGLE_ADS_TXT", "")
CUSTOM_EXTERNAL_SCRIPT = getenv("CUSTOM_EXTERNAL_SCRIPT", "")


RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
REMOVED_IMAGES_FOLDER = Path(__file__).parent.resolve() / "removed_images"

DB_URI = getenv("DB_URI", "")
FLASK_DEBUG = bool(getenv("FLASK_DEBUG", "0") == "1")
