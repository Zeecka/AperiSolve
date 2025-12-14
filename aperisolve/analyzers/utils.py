"""Utility functions for analyzers modules."""

import fcntl
import json
import os
import threading
from pathlib import Path
from typing import Any
import itertools
import zlib
import sqlite3

_thread_lock = threading.Lock()

MAX_PENDING_TIME = int(os.getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default

# PATH CONFIGURATION
# Prioritize /data for Docker persistence, fallback to local directory for bare metal


def update_data(
    output_dir: Path, new_data: dict[Any, Any], json_filename: str = "results.json"
) -> None:
    """Thread-safe and process-safe JSON update using lock file and atomic replace."""
    json_file = Path(output_dir) / json_filename
    lock_file = json_file.with_suffix(json_file.suffix + ".lock")
    tmp_file = json_file.with_suffix(json_file.suffix + ".tmp")

    json_file.parent.mkdir(parents=True, exist_ok=True)

    with _thread_lock:  # synchronizes across threads
        with open(lock_file, "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # synchronizes across processes

            try:
                # Read existing JSON
                data: dict[Any, Any] = {}
                if json_file.exists():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}

                # Update with new data
                data.update(new_data)

                # Write safely to a temp file
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, sort_keys=False)

                os.replace(tmp_file, json_file)  # ensures file write is atomic
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def pack_ihdr(width: int, height: int, depth: int, color: int, interlace: int) -> int:
    """
    Pack IHDR fields into a single integer.

    Layout:
    width     : 16 bits
    height    : 16 bits
    depth     : 3 bits
    color     : 3 bits
    interlace : 1 bit
    """
    return (width << 23) | (height << 7) | (depth << 4) | (color << 1) | interlace


def unpack_ihdr(packed: int) -> tuple[int, int, int, int, int]:
    """
    Unpack packed IHDR integer into components:
    (width, height, depth, color, interlace)
    """

    interlace = packed & 0b1
    color = (packed >> 1) & 0b111
    depth = (packed >> 4) & 0b111
    height = (packed >> 7) & 0xFFFF
    width = (packed >> 23) & 0xFFFF

    return width, height, depth, color, interlace
