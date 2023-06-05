#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

import os
import sys
import time
from collections import OrderedDict
sys.path.append('../')
from mongo import db_uploads, db_status  # noqa: E402
from utils import cmd  # noqa: E402
from config import DELAY_GARBAGE, UPLOAD_FOLDER, MAX_STORE_TIME  # noqa: E402


def get_top_images(n=10):
    data = list(db_uploads.aggregate([
        {"$group": {"_id": "$md5_full", "count": {"$sum": 1}}}
    ]))
    stats = OrderedDict()
    for d in data:
        stats[d["_id"]] = d["count"]
    sorted_stats = OrderedDict(sorted(stats.items(),
                               key=lambda item: str(item[1])+item[0],
                               reverse=True))
    return list(sorted_stats.keys())[:n]


def get_last_submit_date(filehash):
    data = list(db_uploads.find({"md5_full": filehash}))
    dates = [d["submit_date"] for d in data]
    return max(dates, default=0)


def remove_image(d):
    cmd(f"rm -rf {UPLOAD_FOLDER}/{d}")
    db_status.delete_many({"md5_full": d})


while True:
    dirs = os.listdir(UPLOAD_FOLDER)
    for d in dirs:
        try:
            top = get_top_images()
            last_submit_date = get_last_submit_date(d)
            if d in top or time.time() < (last_submit_date + MAX_STORE_TIME):
                continue
            else:  # Remove if too old / not in top
                remove_image(d)
        except Exception() as e:
            print(e)
            continue
    time.sleep(DELAY_GARBAGE)
