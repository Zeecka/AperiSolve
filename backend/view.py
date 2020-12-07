#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import os
from threading import Thread
import time
from utils import cmd_exec
import numpy as np
from PIL import Image
from filelock import FileLock
from config import DELAY_CHECK, UPLOAD_FOLDER

RUNNING = []

class View(Thread):

    def __init__(self, folder, config):
        Thread.__init__(self)
        self.folder = folder
        self.config = config

    def compute_layers(self, arr, mode, filename):
        """Compute each bits visual image for a given layer `arr`."""
        for i in range(8):  # 8 bits layer
            newdata = (arr >> i) % 2 * 255  # Highlighting the layer bit `i`
            if mode == 'RGBA':  # Force alpha layer (4th) to 255 if exist
                newdata[:, :, 3] = 255
            Image.fromarray(newdata, mode).save(f"{self.folder}/view/{filename}_{i+1}.png")

    def process_image(self):
        """Apply compute_layers() on each `img` layers and save images."""
        cmd_exec(f"mkdir {self.folder}/view")  # create view folder

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
        self.compute_layers(npimg, img_pil.mode, f"image_rgb")  # rgb
        self.compute_layers(npimg[:, :, 0], 'L', f"image_r")  # r
        self.compute_layers(npimg[:, :, 1], 'L', f"image_g")  # g
        self.compute_layers(npimg[:, :, 2], 'L', f"image_b")  # b

        # set images names
        images_name = {}
        images_name["Supperimposed"] = [f"image_rgb_{i+1}.png" for i in range(8)]
        images_name["Red"] = [f"image_r_{i+1}.png" for i in range(8)]
        images_name["Green"] = [f"image_g_{i+1}.png" for i in range(8)]
        images_name["Blue"] = [f"image_b_{i+1}.png" for i in range(8)]

        if img_pil.mode == "RGBA":  # Should be RGB or RGBA
            self.compute_layers(npimg[:, :, 3], 'L', f"image_a")  # b
            images_name["Alpha"] = [f"image_a_{i+1}.png" for i in range(8)]

        return images_name

    def set_config_status(self, status):
        with FileLock(f"{self.folder}/config.json.lock"):
            with open(f"{self.folder}/config.json", "r") as jsonFile:
                config = json.load(jsonFile)
            config["status"]["view"] = status
            with open(f"{self.folder}/config.json", "w") as jsonFile:
                json.dump(config, jsonFile)

    def run(self):
        if os.path.isdir(f"{self.folder}/view"):  # prevent multiple threads
            return
        self.set_config_status("running")
        # First verify if we do not already compute for original image
        md5_image = self.config["md5_image"]
        if self.config["md5_image"] != self.config["md5_full"] \
           and os.path.isdir(f"{UPLOAD_FOLDER}/{md5_image}/view") \
           and len([name for name in os.listdir(f"{UPLOAD_FOLDER}/{md5_image}/view") if \
               os.path.isfile(os.path.join(f"{UPLOAD_FOLDER}/{md5_image}/view", name))]) in [8*4, 8*5]:
            cmd_exec(f"cp -r {UPLOAD_FOLDER}/{md5_image}/view {self.folder}/view")
        else: # Else compute
            self.process_image()
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
            if "view" not in config["status"]:
                RUNNING.append(d)
                View(d, config).start()  # Run View on folder
        except:
            continue
    time.sleep(DELAY_CHECK)