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
DB_NAME = "ihdr_crcs.db"
if os.path.exists("/data"):
    DB_PATH = os.path.join("/data", DB_NAME)
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)


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


def create_crc_db() -> None:
    """Creates and populates CRC lookup database with CRC, Width and Heigth tuples"""
    if os.path.exists(DB_PATH):
        print(f"Database already exists at {DB_PATH}. Skipping generation.")
        return
    db_filename = "ihdr_crcs.db"

    # Connect to database
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    # Optimization: Turn off safety checks for bulk insertion speed
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")

    # Create table
    # We store the CRC as an integer for faster indexing/storage
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ihdr (
            crc INTEGER,
            width INTEGER,
            height INTEGER
        )
    """
    )

    # Drop index if exists (rebuilding it at the end is faster)
    cursor.execute("DROP INDEX IF EXISTS idx_crc")

    max_width = 2000
    max_height = 2000
    w = range(1, max_width + 1)
    h = range(1, max_height + 1)

    # Standard PNG IHDR parameters
    bit_depth = [1, 2, 4, 8, 16]
    color_type = [0, 2, 3, 4, 6]
    compression_method = [0]  # This is always 0 according to the PNG spec
    filter_method = [0]  # This is always 0 according to the PNG spec
    interlace_method = [0, 1]

    # Create the generator
    all_combinations = itertools.product(
        w, h, bit_depth, color_type, compression_method, filter_method, interlace_method
    )

    batch_size = 100000
    batch = []
    count = 0

    for w_val, h_val, bd, ct, comp, filt, inter in all_combinations:
        # Construct IHDR chunk data
        ihdr_data = (
            w_val.to_bytes(4, "big")
            + h_val.to_bytes(4, "big")
            + bytes([bd, ct, comp, filt, inter])
        )

        # Calculate CRC
        crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF

        # Add to batch
        batch.append((crc, w_val, h_val))

        if len(batch) >= batch_size:
            cursor.executemany("INSERT INTO ihdr VALUES (?,?,?)", batch)
            conn.commit()
            batch = []
            count += batch_size
            if count % 1000000 == 0:
                print(f"Inserted {count:,} rows...")

    # Insert remaining records
    if batch:
        cursor.executemany("INSERT INTO ihdr VALUES (?,?,?)", batch)
        conn.commit()

    print("Insertion complete. Creating Index for faster lookups...")
    # Creating the index allows for faster lookups
    cursor.execute("CREATE INDEX idx_crc ON ihdr(crc)")
    conn.commit()

    conn.close()
    print("Database ready.")
