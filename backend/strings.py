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

class Strings(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["strings"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        self.set_config_status("running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/strings.txt") :
            cmd_exec(f"cp {UPLOAD_FOLDER}/{md5_image}/strings.txt {self.folder}/strings.txt")
        else: # Else compute
            image = self.config["image"]
            c_input = f"{self.folder}/{image}"  # image.png
            c_output = f"{self.folder}/strings.txt"  # strings.txt
            cmd_exec(f"strings {c_input} > {c_output}")
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
            if "strings" not in config["status"]:
                RUNNING.append(d)
                Strings(d, config).start()  # Run strings on folder
        except:
            continue
    time.sleep(DELAY_CHECK)