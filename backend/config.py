#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

DELAY_CHECK = 10  # Wait in seconds between checks
DELAY_GARBAGE = 60*60*12  # Garbage collector every 1/2 day
MAX_STORE_TIME = 60*60*24*2  # For non important items, keep it 48 hours
UPLOAD_FOLDER = "/app/uploads"
