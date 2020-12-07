#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import imghdr
import json
import os
import re
import time
from PIL import Image  # type: ignore
from threading import Thread
from utils import cmd_exec
from filelock import FileLock
from config import DELAY_CHECK, UPLOAD_FOLDER

RUNNING = []

class Zsteg(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["zsteg"] = status
            if self.config["zsteg_all"]:
                config["status"]["zsteg_all"] = status
            if self.config["zsteg_ext"]:
                config["status"]["zsteg_ext"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        self.set_config_status("running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/zsteg.txt") :
            cmd_exec(f"cp {UPLOAD_FOLDER}/{md5_image}/zsteg.7z {self.folder}/zsteg.7z")
            cmd_exec(f"cp {UPLOAD_FOLDER}/{md5_image}/zsteg.txt {self.folder}/zsteg.txt")
        else: # Else compute
            image = self.config["image"]
            c_input = f"{self.folder}/{image}"  # image.png
            img = c_input
            if imghdr.what(f"{c_input}") not in ["png", "bmp"]:
                img_pil = Image.open(f"{c_input}")
                img_pil = img_pil.convert('RGBA')  # Cast RGBA PNG
                img = f"{c_input}_zsteg.png"  # New name
                img_pil.save(f"{img}")
            
            if self.config["zsteg_all"]:
                output = cmd_exec(f"zsteg {img} --all")
            else:
                output = cmd_exec(f"zsteg {img}")
            with open(f"{self.folder}/zsteg.txt", "w") as f:
                f.write(output)
            
            # Extract files
            chans = []  # Extract zsteg chans containing "file:"
            rzsteg_out = re.split("\r|\n", output)
            for elt in rzsteg_out:
                if elt[23:28] == "file:" and "," in elt[:20]:  # , Keep channels only
                    chans.append(elt[:20].strip())
            
            if len(chans) > 0 and self.config["zsteg_ext"]:
                cmd_exec(f"mkdir {self.folder}/zsteg")
                for channel in chans:
                    cmd_exec(f"zsteg {img} -E {channel} > {self.folder}/zsteg/{channel.replace(',','_')}")
                
                cmd_exec(f"7z a {self.folder}/zsteg.7z {self.folder}/zsteg/*")
                cmd_exec(f"rm -r {self.folder}/zsteg")

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
            if "zsteg" not in config["status"] or \
               (config["zsteg_all"] and "zsteg_all" not in config["status"]) or \
               (config["zsteg_ext"] and "zsteg_ext" not in config["status"]):
                RUNNING.append(d)
                Zsteg(d, config).start()  # Run zsteg on folder
        except:
            continue
    time.sleep(DELAY_CHECK)