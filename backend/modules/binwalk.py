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


class Binwalk(Module):
    def __init__(self, md5):
        Module.__init__(self, md5)

    def run(self):
        self.set_config_status("binwalk", "running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/binwalk.7z") \
           and os.path.isfile(f"{UPLOAD_FOLDER}/{md5_image}/binwalk.txt"):
            cmd(f"cp {UPLOAD_FOLDER}/{md5_image}/binwalk.7z "
                f"{self.folder}/binwalk.7z")
            cmd(f"cp {UPLOAD_FOLDER}/{md5_image}/binwalk.txt "
                f"{self.folder}/binwalk.txt")
        else:  # Else compute
            image = self.config["image"]
            c_input = f"{self.folder}/{image}"  # image.png
            output = cmd(f"binwalk -e . -C {self.folder}/binwalk "
                         f"--dd='.*' {c_input} 2>&1")
            cmd(f"7z a {self.folder}/binwalk.7z {self.folder}/binwalk/*/*")
            cmd(f"rm -r {self.folder}/binwalk")
            with open(f"{self.folder}/binwalk.txt", "w") as f:
                f.write(output)
        global RUNNING
        RUNNING.remove(self.md5)
        self.set_config_status("binwalk", "finished")


if __name__ == "__main__":
    while True:
        dirs = os.listdir(UPLOAD_FOLDER)
        for d in dirs:
            try:
                folder = f"{UPLOAD_FOLDER}/{d}"
                if d in RUNNING or not os.path.isdir(folder):
                    continue
                m = Binwalk(d)
                status = m.get_config_status(d)
                if status is None or status.get("binwalk") is None:
                    RUNNING.append(d)
                    m.start()  # Run
            except Exception() as e:
                print(e)
                continue
        time.sleep(DELAY_CHECK)
