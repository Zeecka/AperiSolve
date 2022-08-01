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
import numpy as np
from PIL import Image
sys.path.append('../')
from config import DELAY_CHECK, UPLOAD_FOLDER  # noqa: E402
from module import Module  # noqa: E402
from utils import cmd  # noqa: E402


RUNNING = []


class View(Module):
    def __init__(self, md5):
        Module.__init__(self, md5)

    def compute_layers(self, arr, mode, filename):
        """Compute each bits visual image for a given layer `arr`."""
        for i in range(8):  # 8 bits layer
            newdata = (arr >> i) % 2 * 255  # Highlighting the layer bit `i`
            if mode == 'RGBA':  # Force alpha layer (4th) to 255 if exist
                newdata[:, :, 3] = 255
            Image.fromarray(newdata, mode).save(
                f"{self.folder}/view/{filename}_{i+1}.png")

    def process_image(self):
        """Apply compute_layers() on each `img` layers and save images."""
        cmd(f"mkdir {self.folder}/view")  # create view folder

        image = self.config["image"]
        c_input = f"{self.folder}/{image}"

        img_pil = Image.open(c_input)

        # Convert all in RGBA exept RGB images
        if img_pil.mode in ["P", "1", "L", "LA", "RGBX", "RGBa", "CMYK", "LAB",
                            "YCbCr", "HSV", "I", "F"]:
            img_pil = img_pil.convert('RGBA')

        # Get numpy array
        npimg = np.array(img_pil)  # rgb

        # generate images from numpy array and save
        self.compute_layers(npimg, img_pil.mode, "image_rgb")  # rgb
        self.compute_layers(npimg[:, :, 0], 'L', "image_r")  # r
        self.compute_layers(npimg[:, :, 1], 'L', "image_g")  # g
        self.compute_layers(npimg[:, :, 2], 'L', "image_b")  # b

        # set images names
        images_name = {}
        images_name["Supperimposed"] = [
            f"image_rgb_{i+1}.png" for i in range(8)]
        images_name["Red"] = [f"image_r_{i+1}.png" for i in range(8)]
        images_name["Green"] = [f"image_g_{i+1}.png" for i in range(8)]
        images_name["Blue"] = [f"image_b_{i+1}.png" for i in range(8)]

        if img_pil.mode == "RGBA":  # Should be RGB or RGBA
            self.compute_layers(npimg[:, :, 3], 'L', "image_a")  # b
            images_name["Alpha"] = [f"image_a_{i+1}.png" for i in range(8)]

        return images_name

    def run(self):
        if os.path.isdir(f"{self.folder}/view"):  # prevent multiple threads
            return
        self.set_config_status("view", "running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        dirview = f"{UPLOAD_FOLDER}/{md5_image}/view"
        if md5_image != self.md5 \
           and os.path.isdir(dirview) \
           and len([name for name in os.listdir()
                   if os.path.isfile(os.path.join(dirview, name))]) \
           in [8*4, 8*5]:
            cmd(f"cp -r {UPLOAD_FOLDER}/{md5_image}/view {self.folder}/view")
        else:  # Else compute
            self.process_image()
        global RUNNING
        RUNNING.remove(self.md5)
        self.set_config_status("view", "finished")


if __name__ == "__main__":
    while True:
        dirs = os.listdir(UPLOAD_FOLDER)
        for d in dirs:
            try:
                folder = f"{UPLOAD_FOLDER}/{d}"
                if d in RUNNING or not os.path.isdir(folder):
                    continue
                m = View(d)
                status = m.get_config_status(d)
                if status is None or status.get("view") is None:
                    RUNNING.append(d)
                    m.start()  # Run
            except Exception() as e:
                print(e)
                continue
        time.sleep(DELAY_CHECK)
