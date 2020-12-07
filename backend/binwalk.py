#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import os
from threading import Thread
import time
from filelock import FileLock
from utils import cmd_exec
from config import DELAY_CHECK, UPLOAD_FOLDER

RUNNING = []

class Binwalk(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["binwalk"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        self.set_config_status("running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/binwalk.7z") \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/binwalk.txt") :
            cmd_exec(f"cp {UPLOAD_FOLDER}/{md5_image}/binwalk.7z {self.folder}/binwalk.7z")
            cmd_exec(f"cp {UPLOAD_FOLDER}/{md5_image}/binwalk.txt {self.folder}/binwalk.txt")
        else: # Else compute
            image = self.config["image"]
            c_input = f"{self.folder}/{image}"  # image.png
            output = cmd_exec(f"binwalk -e . -C {self.folder}/binwalk --dd='.*' {c_input} 2>&1")
            cmd_exec(f"7z a {self.folder}/binwalk.7z {self.folder}/binwalk/*/*")
            cmd_exec(f"rm -r {self.folder}/binwalk")
            with open(f"{self.folder}/binwalk.txt", "w") as f:
                f.write(output)
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
            if "binwalk" not in config["status"]:
                RUNNING.append(d)
                Binwalk(d, config).start()  # Run binwalk on folder
        except:
            continue
    time.sleep(DELAY_CHECK)