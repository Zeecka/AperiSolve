"""Aperi'Solve configuration variables."""

from importlib.metadata import PackageNotFoundError, version
from os import getenv
from pathlib import Path

try:
    _package_version = version("aperisolve")
except PackageNotFoundError:
    _package_version = "development"

PROJECT_VERSION = getenv("PROJECT_VERSION", _package_version)

REMOVAL_MIN_AGE_SECONDS = int(getenv("REMOVAL_MIN_AGE_SECONDS", "300"))  # 5 minutes
MAX_PENDING_TIME = int(getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default
CLEANUP_INTERVAL_SECONDS = int(getenv("CLEANUP_INTERVAL_SECONDS", "900"))  # 15 minutes
MAX_STORE_TIME = int(getenv("MAX_STORE_TIME", "259200"))  # 3 days by default
MAX_CONTENT_LENGTH = int(getenv("MAX_CONTENT_LENGTH", "1048576"))  # 1 MB by default
CLEAR_AT_RESTART = int(getenv("CLEAR_AT_RESTART", "0"))

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]

GOOGLE_ADS_TXT = getenv("GOOGLE_ADS_TXT", "")
CUSTOM_EXTERNAL_SCRIPT = getenv("CUSTOM_EXTERNAL_SCRIPT", "")

# Manual AdSense units. All default empty: self-hosted instances render no ads.
ADSENSE_CLIENT = getenv("ADSENSE_CLIENT", "")
ADSENSE_SLOT_WIKI = getenv("ADSENSE_SLOT_WIKI", "")
ADSENSE_SLOT_INDEX = getenv("ADSENSE_SLOT_INDEX", "")

# Public base URL (e.g. "https://www.aperisolve.com") used for canonical,
# Open Graph and sitemap absolute links. Falls back to the request host.
SITE_BASE_URL = getenv("SITE_BASE_URL", "").rstrip("/")


RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
REMOVED_IMAGES_FOLDER = Path(__file__).parent.resolve() / "removed_images"

DB_URI = getenv("DB_URI", "")
FLASK_DEBUG = bool(getenv("FLASK_DEBUG", "0") == "1")
