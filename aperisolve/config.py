# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Aperi'Solve configuration variables."""

from os import getenv
from pathlib import Path

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]
WORKER_FILES = ["binwalk", "foremost", "steghide", "zsteg", "image_resize", "openstego", "pcrt"]

RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
REMOVED_IMAGES_FOLDER = Path(__file__).parent.resolve() / "removed_images"
REMOVAL_MIN_AGE_SECONDS = int(getenv("REMOVAL_MIN_AGE_SECONDS", "300"))  # 5 minutes
MAX_PENDING_TIME = int(getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default
MAX_STORE_TIME = int(getenv("MAX_STORE_TIME", "259200"))  # 3 days by default
CLEAR_AT_RESTART = int(getenv("CLEAR_AT_RESTART", "0"))
