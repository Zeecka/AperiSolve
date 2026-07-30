"""Aperi'Solve configuration variables."""

from importlib.metadata import PackageNotFoundError, version
from os import getenv
from pathlib import Path

try:
    _package_version = version("aperisolve")
except PackageNotFoundError:
    _package_version = "development"

PROJECT_VERSION = getenv("PROJECT_VERSION", _package_version)


def _int_env(name: str, default: int) -> int:
    """Integer env var, treating empty as unset.

    The release workflow writes `KEY=` lines for GitHub variables that are not
    set, and docker compose passes those through as empty strings — which must
    fall back to the default rather than crash every container on int("").
    """
    raw = getenv(name)
    return int(raw) if raw else default


REMOVAL_MIN_AGE_SECONDS = _int_env("REMOVAL_MIN_AGE_SECONDS", 300)  # 5 minutes
MAX_PENDING_TIME = _int_env("MAX_PENDING_TIME", 600)  # 10 minutes by default

# Per-subprocess wall clock. Some analyzers run two tool subprocesses in
# sequence (steghide info+extract, openstego's two algorithms) plus a 7z
# archive step, so this must stay well below MAX_PENDING_TIME for the whole
# job to fit inside JOB_TIMEOUT.
SUBPROCESS_TIMEOUT = _int_env("SUBPROCESS_TIMEOUT", max(60, MAX_PENDING_TIME // 2))

# RQ kills the analysis job after this; headroom over the analyzer budget so
# analyzers time out (and record their error) before RQ kills the job mid-write.
JOB_TIMEOUT = MAX_PENDING_TIME + 60

# Submissions still pending/running past this age are stale: their job either
# died or was killed by RQ. Must exceed JOB_TIMEOUT or cleanup could delete a
# submission whose job is still legitimately running.
STALE_SUBMISSION_CUTOFF = JOB_TIMEOUT + 60
CLEANUP_INTERVAL_SECONDS = _int_env("CLEANUP_INTERVAL_SECONDS", 900)  # 15 minutes
MAX_STORE_TIME = _int_env("MAX_STORE_TIME", 259200)  # 3 days by default
MAX_CONTENT_LENGTH = _int_env("MAX_CONTENT_LENGTH", 1048576)  # 1 MB by default
CLEAR_AT_RESTART = _int_env("CLEAR_AT_RESTART", 0)

# Recognised image file extensions. No longer the upload gate (any file type is
# accepted); this now backs the derived-image serving gate (/image/<hash>/<name>)
# and the extension fallback in aperisolve.filetype.
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]

GOOGLE_ADS_TXT = getenv("GOOGLE_ADS_TXT", "")
CUSTOM_EXTERNAL_SCRIPT = getenv("CUSTOM_EXTERNAL_SCRIPT", "")


# Public base URL (e.g. "https://www.aperisolve.com") used for canonical,
# Open Graph and sitemap absolute links. Falls back to the request host.
SITE_BASE_URL = getenv("SITE_BASE_URL", "").rstrip("/")


RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
REMOVED_IMAGES_FOLDER = Path(__file__).parent.resolve() / "removed_images"

DB_URI = getenv("DB_URI", "")
FLASK_DEBUG = bool(getenv("FLASK_DEBUG", "0") == "1")

# RQ broker connection.
REDIS_URL = getenv("REDIS_URL", "redis://redis:6379/0")

# Rate limiter storage: Redis DB 1 keeps limiter keys apart from RQ (DB 0).
RATELIMIT_STORAGE_URI = getenv("RATELIMIT_STORAGE_URI", "redis://redis:6379/1")
