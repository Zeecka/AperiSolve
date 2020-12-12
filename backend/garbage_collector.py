#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import os
from threading import Thread
import time
from utils import cmd_exec
from filelock import FileLock
from config import DELAY_GARBAGE, UPLOAD_FOLDER, MAX_STORE_TIME


def get_top_images(n=10):
    with open(f"{UPLOAD_FOLDER}/stats.json", "r") as jsonFile:
        stats = json.load(jsonFile)
    count = {}
    for img in stats["images"]:
        count[img] = stats["images"][img]["count"]
    top = {k: v for k, v in sorted(count.items(), key=lambda item: item[1])[::-1][:n]}
    return top

while True:
    dirs = os.listdir(UPLOAD_FOLDER)
    for d in dirs:
        try:
            d = f"{UPLOAD_FOLDER}/{d}"
            if not os.path.isfile(f"{d}/config.json"):
                continue
            with FileLock(f"{d}/config.json.lock"):
                with open(f"{d}/config.json", "r") as jsonFile:
                    config = json.load(jsonFile)

            top = get_top_images()
            if config["md5_full"] in top or \
               time.time() < (config["last_submit_date"] + MAX_STORE_TIME):
                print(config["md5_full"] in top)
                print(time.time() < (config["last_submit_date"] + MAX_STORE_TIME))
                continue
            else:  # Remove if too old / not in top
                cmd_exec(f"rm -rf {d}")
        except:
            continue
    time.sleep(DELAY_GARBAGE)
