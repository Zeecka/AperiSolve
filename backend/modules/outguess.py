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
from shlex import quote
sys.path.append('../')
from config import DELAY_CHECK, UPLOAD_FOLDER  # noqa: E402
from module import Module  # noqa: E402
from utils import cmd  # noqa: E402

RUNNING = []


class Outguess(Module):
    def __init__(self, md5):
        Module.__init__(self, md5)

    def run(self):
        self.set_config_status("outguess", "running")
        image = self.config["image"]
        c_input = f"{self.folder}/{image}"  # image.png
        if len(self.config["password"]):
            passwd = self.config["password"]
            output = cmd(f"outguess -k {quote(passwd)} -r {c_input} "
                         f"{self.folder}/outguess.data 2>&1")
        else:
            output = cmd(f"outguess -r {c_input} "
                         f"{self.folder}/outguess.data 2>&1")
        cmd(f"7z a {self.folder}/outguess.7z {self.folder}/outguess.data")
        cmd(f"rm -r {self.folder}/outguess.data")
        with open(f"{self.folder}/outguess.txt", "w") as f:
            f.write(output)
        global RUNNING
        RUNNING.remove(self.md5)
        self.set_config_status("outguess", "finished")


if __name__ == "__main__":
    while True:
        dirs = os.listdir(UPLOAD_FOLDER)
        for d in dirs:
            try:
                folder = f"{UPLOAD_FOLDER}/{d}"
                if d in RUNNING or not os.path.isdir(folder):
                    continue
                m = Outguess(d)
                status = m.get_config_status(d)
                if status is None or status.get("outguess") is None:
                    RUNNING.append(d)
                    m.start()  # Run
            except Exception() as e:
                print(e)
                continue
        time.sleep(DELAY_CHECK)
