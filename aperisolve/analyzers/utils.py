"""Utility functions for analyzers modules."""

import fcntl
import json
import os
import threading
from pathlib import Path
from typing import Any

_thread_lock = threading.Lock()

MAX_PENDING_TIME = int(os.getenv("MAX_PENDING_TIME", "600"))  # 10 minutes by default


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
