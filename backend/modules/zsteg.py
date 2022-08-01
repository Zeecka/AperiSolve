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
import re
import time
import imghdr
from PIL import Image  # type: ignore
sys.path.append('../')
from config import DELAY_CHECK, UPLOAD_FOLDER  # noqa: E402
from module import Module  # noqa: E402
from utils import cmd  # noqa: E402


RUNNING = []


class Zsteg(Module):
    def __init__(self, md5):
        Module.__init__(self, md5)

    def run(self):
        self.set_config_status("zsteg", "running")
        # First verify if we do not already compute for original image
        image = self.config["image"]
        c_input = f"{self.folder}/{image}"  # image.png
        img = c_input
        if imghdr.what(f"{c_input}") not in ["png", "bmp"]:
            img_pil = Image.open(f"{c_input}")
            img_pil = img_pil.convert('RGBA')  # Cast RGBA PNG
            img = f"{c_input}_zsteg.png"  # New name
            img_pil.save(f"{img}")

        if self.config["zsteg_all"]:
            output = cmd(f"zsteg {img} --all")
        else:
            output = cmd(f"zsteg {img}")
        with open(f"{self.folder}/zsteg.txt", "w") as f:
            f.write(output)

        # Extract files
        chans = []  # Extract zsteg chans containing "file:"
        rzsteg_out = re.split("\r|\n", output)
        for elt in rzsteg_out:
            if elt[23:28] == "file:" \
                    and "," in elt[:20]:  # , Keep channels only
                chans.append(elt[:20].strip())

        if len(chans) > 0 and self.config["zsteg_ext"]:
            cmd(f"mkdir {self.folder}/zsteg")
            for channel in chans:
                cmd(
                    f"zsteg {img} -E {channel} > "
                    f"{self.folder}/zsteg/{channel.replace(',','_')}")

            cmd(f"7z a {self.folder}/zsteg.7z {self.folder}/zsteg/*")
            cmd(f"rm -r {self.folder}/zsteg")

        global RUNNING
        RUNNING.remove(self.md5)
        self.set_config_status("zsteg", "finished")


if __name__ == "__main__":
    while True:
        dirs = os.listdir(UPLOAD_FOLDER)
        for d in dirs:
            try:
                folder = f"{UPLOAD_FOLDER}/{d}"
                if d in RUNNING or not os.path.isdir(folder):
                    continue
                m = Zsteg(d)
                status = m.get_config_status(d)
                if status is None or status.get("zsteg") is None:
                    RUNNING.append(d)
                    m.start()  # Run
            except Exception() as e:
                print(e)
                continue
        time.sleep(DELAY_CHECK)
