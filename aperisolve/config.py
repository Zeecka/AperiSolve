# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""Aperi'Solve configuration variables."""

from pathlib import Path

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]
WORKER_FILES = ["binwalk", "foremost", "steghide", "zsteg", "image_resize", "openstego", "pcrt"]

RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
