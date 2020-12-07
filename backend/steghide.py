#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import os
from shlex import quote
from threading import Thread
import time
from utils import cmd_exec
from filelock import FileLock
from config import DELAY_CHECK, UPLOAD_FOLDER

RUNNING = []

class Steghide(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["steghide"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        self.set_config_status("running")
        image = self.config["image"]
        c_input = f"{self.folder}/{image}"  # image.png
        fold = f"{self.folder}/steghide"
        cmd_exec(f"mkdir {fold}")
        passwd = ''
        if self.config["use_password"]:
            passwd = self.config["password"]
        output = cmd_exec(f"cd {fold} && steghide extract -sf {c_input} -p {quote(passwd)} 2>&1")
        cmd_exec(f"7z a {self.folder}/steghide.7z {fold}/*")
        cmd_exec(f"rm -r {fold}")
        with open(f"{self.folder}/steghide.txt", "w") as f:
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
            if "steghide" not in config["status"]:
                RUNNING.append(d)
                Steghide(d, config).start()  # Run steghide on folder
        except:
            continue
    time.sleep(DELAY_CHECK)