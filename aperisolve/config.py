"""AperiSolve configuration variables."""

from pathlib import Path

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]
WORKER_FILES = ["binwalk", "foremost", "steghide", "zsteg"]

RESULT_FOLDER = Path(__file__).parent.resolve() / "results"
