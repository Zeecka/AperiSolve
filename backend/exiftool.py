#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import os
from threading import Thread
import time
from utils import cmd_exec
from filelock import FileLock
from config import DELAY_CHECK, UPLOAD_FOLDER

RUNNING = []

class Exif(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["exiftool"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        self.set_config_status("running")
        image = self.config["image"]
        c_input = f"{self.folder}/{image}"  # image.png
        c_output = f"{self.folder}/exiftool.json"  # exiftool.json
        cmd_exec(f"exiftool -E -a -u -g1 {c_input} -j > {c_output}")
        global RUNNING
        RUNNING.remove(self.folder)
        self.set_config_status("finished")


while True:
    dirs = os.listdir(UPLOAD_FOLDER)
    for d in dirs:
        try:
            d = f"{UPLOAD_FOLDER}/{d}"
            if d in RUNNING or not os.path.isdir(d) or not os.path.isfile(f"{d}/config.json"):
                continue
            with open(f"{d}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            if "exiftool" not in config["status"]:
                RUNNING.append(d)
                Exif(d, config).start()  # Run exif on folder
        except:
            continue
    time.sleep(DELAY_CHECK)