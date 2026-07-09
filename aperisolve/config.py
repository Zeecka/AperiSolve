"""Aperi'Solve configuration variables."""

from importlib.metadata import PackageNotFoundError, version
from os import getenv
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    _package_version = version("aperisolve")
except PackageNotFoundError:
    _package_version = "development"

PROJECT_VERSION = getenv("PROJECT_VERSION", _package_version)

REMOVAL_MIN_AGE_SECONDS = int(getenv("REMOVAL_MIN_AGE_SECONDS", "300"))  # 5 minutes
MAX_PENDING_TIME = int(getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default

# Per-subprocess wall clock. Some analyzers run two tool subprocesses in
# sequence (steghide info+extract, openstego's two algorithms) plus a 7z
# archive step, so this must stay well below MAX_PENDING_TIME for the whole
# job to fit inside JOB_TIMEOUT.
SUBPROCESS_TIMEOUT = int(getenv("SUBPROCESS_TIMEOUT", str(max(60, MAX_PENDING_TIME // 2))))

# RQ kills the analysis job after this; headroom over the analyzer budget so
# analyzers time out (and record their error) before RQ kills the job mid-write.
JOB_TIMEOUT = MAX_PENDING_TIME + 60

# Submissions still pending/running past this age are stale: their job either
# died or was killed by RQ. Must exceed JOB_TIMEOUT or cleanup could delete a
# submission whose job is still legitimately running.
STALE_SUBMISSION_CUTOFF = JOB_TIMEOUT + 60
CLEANUP_INTERVAL_SECONDS = int(getenv("CLEANUP_INTERVAL_SECONDS", "900"))  # 15 minutes
MAX_STORE_TIME = int(getenv("MAX_STORE_TIME", "259200"))  # 3 days by default
MAX_CONTENT_LENGTH = int(getenv("MAX_CONTENT_LENGTH", "1048576"))  # 1 MB by default
CLEAR_AT_RESTART = int(getenv("CLEAR_AT_RESTART", "0"))

# Recognised image file extensions. No longer the upload gate (any file type is
# accepted); this now backs the derived-image serving gate (/image/<hash>/<name>)
# and the extension fallback in aperisolve.filetype.
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]

GOOGLE_ADS_TXT = getenv("GOOGLE_ADS_TXT", "")
CUSTOM_EXTERNAL_SCRIPT = getenv("CUSTOM_EXTERNAL_SCRIPT", "")


def _client_from_script_url(url: str) -> str:
    """AdSense client id embedded in the loader URL (?client=ca-pub-...)."""
    client = parse_qs(urlparse(url).query).get("client", [""])[0]
    return client if client.startswith("ca-pub-") else ""


# Manual AdSense units. All default empty: self-hosted instances render no ads.
# The client id falls back to the one already present in the
# CUSTOM_EXTERNAL_SCRIPT loader URL, so one CI variable configures both;
# individual units still render only when their slot id is set.
ADSENSE_CLIENT = getenv("ADSENSE_CLIENT", "") or _client_from_script_url(CUSTOM_EXTERNAL_SCRIPT)
ADSENSE_SLOT_WIKI = getenv("ADSENSE_SLOT_WIKI", "")
ADSENSE_SLOT_INDEX = getenv("ADSENSE_SLOT_INDEX", "")
ADSENSE_SLOT_RESULT = getenv("ADSENSE_SLOT_RESULT", "")
# Distinct wiki slots keep sidebar vs in-article reporting separate in
# AdSense; both fall back to the original single ADSENSE_SLOT_WIKI.
ADSENSE_SLOT_WIKI_SIDEBAR = getenv("ADSENSE_SLOT_WIKI_SIDEBAR", "") or ADSENSE_SLOT_WIKI
ADSENSE_SLOT_WIKI_ARTICLE = getenv("ADSENSE_SLOT_WIKI_ARTICLE", "") or ADSENSE_SLOT_WIKI

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
