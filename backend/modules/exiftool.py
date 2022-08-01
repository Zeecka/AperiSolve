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
sys.path.append('../')
from config import DELAY_CHECK, UPLOAD_FOLDER  # noqa: E402
from module import Module  # noqa: E402
from utils import cmd  # noqa: E402

RUNNING = []


class Exiftool(Module):
    def __init__(self, md5):
        Module.__init__(self, md5)

    def run(self):
        self.set_config_status("exiftool", "running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/exiftool.json"):
            cmd(f"cp {UPLOAD_FOLDER}/{md5_image}/exiftool.json "
                f"{self.folder}/exiftool.json")
        else:  # Else compute
            image = self.config["image"]
            c_input = f"{self.folder}/{image}"  # image.png
            c_output = f"{self.folder}/exiftool.json"  # exiftool.json
            cmd(f"exiftool -E -a -u -g1 {c_input} -j > {c_output}")
        global RUNNING
        RUNNING.remove(self.md5)
        self.set_config_status("exiftool", "finished")


if __name__ == "__main__":
    while True:
        dirs = os.listdir(UPLOAD_FOLDER)
        for d in dirs:
            try:
                folder = f"{UPLOAD_FOLDER}/{d}"
                if d in RUNNING or not os.path.isdir(folder):
                    continue
                m = Exiftool(d)
                status = m.get_config_status(d)
                if status is None or status.get("exiftool") is None:
                    RUNNING.append(d)
                    m.start()  # Run
            except Exception() as e:
                print(e)
                continue
        time.sleep(DELAY_CHECK)
