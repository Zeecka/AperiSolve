#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

DELAY_CHECK = 10  # Wait in seconds between checks
DELAY_GARBAGE = 60*60  # Garbage collector every hours
MAX_STORE_TIME = 60*60*3  # For non important items, keep it 3 hours
UPLOAD_FOLDER = "/app/uploads"
