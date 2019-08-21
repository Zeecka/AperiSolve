#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application
Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"

"""

import re
import imghdr
import numpy as np
from shlex import quote
from PIL import Image
from appfunct import *


def isValidImage(filename):
    """ Raise Exception / Return False if Image can't be opened with PIL """
    try:
        img = Image.open(filename)
    except:
        return False
    return True


def computeLayers(arr, mode, filename, folder="./"):
    """ Compute each bits visual image for a given layer `arr` """
    for i in range(8):  # 8 bits layer
        newdata = (arr >> i) % 2 * 255  # Highlighting the layer bit `i`
        if mode == 'RGBA':  # Force alpha layer (4th) to 255 if exist
            newdata[:, :, 3] = 255
        Image.fromarray(newdata, mode).save(f"{folder}{filename}_{i+1}.png")


def processImage(img, folder="./"):
    """ Apply computeLayers() on each `img` layers and save images """
    filename = rmExt(img)
    img_pil = Image.open(folder+img)

    # Convert all in RGBA exept RGB images
    if img_pil.mode in ["P", "1", "L", "LA", "RGBX", "RGBa", "CMYK", "LAB",
                        "YCbCr", "HSV", "I", "F"]:
        img_pil = img_pil.convert('RGBA')

    images_name = {}

    # Get numpy array
    npimg = np.array(img_pil)  # rgb
    imgr = npimg[:, :, 0]  # r
    imgg = npimg[:, :, 1]  # g
    imgb = npimg[:, :, 2]  # b

    # generate images from numpy array and save
    computeLayers(npimg, img_pil.mode, f"{filename}_rgb", folder)  # rgb
    computeLayers(imgr, 'L', f"{filename}_r", folder)  # r
    computeLayers(imgg, 'L', f"{filename}_g", folder)  # g
    computeLayers(imgb, 'L', f"{filename}_b", folder)  # b

    # set images names
    images_name["Supperimposed"] = [f"{filename}_rgb_{i+1}.png" for i
                                    in range(8)]
    images_name["Red"] = [f"{filename}_r_{i+1}.png" for i in range(8)]
    images_name["Green"] = [f"{filename}_g_{i+1}.png" for i in range(8)]
    images_name["Blue"] = [f"{filename}_b_{i+1}.png" for i in range(8)]

    if img_pil.mode == "RGBA":  # Should be RGB or RGBA
        computeLayers(npimg[:, :, 3], 'L', f"{filename}_a", folder)  # b
        images_name["Alpha"] = [f"{filename}_a_{i+1}.png" for i in range(8)]

    return images_name


def processZsteg(img, folder="./", allzsteg=False, zstegfiles=False):
    """ Compute zsteg on a given image and return output. """
    # First, cast to PNG if not PNG/BMP (zsteg support only PNG/BMP)
    if imghdr.what(f"{folder}{img}") not in ["png", "bmp"]:
        img_pil = Image.open(f"{folder}{img}")
        img_pil = img_pil.convert('RGBA')  # Cast RGBA PNG
        img = rmExt(img)+"_zsteg.png"  # New name
        img_pil.save(f"{folder}{img}")

    if allzsteg:
        zstegOut = cmdline("zsteg "+quote(folder+img)+" --all")
    else:
        zstegOut = cmdline("zsteg "+quote(folder+img))

    chans = []  # Extract zsteg chans containing "file:"
    rzstegOut = re.split("\r|\n", zstegOut)
    for elt in rzstegOut:
        if elt[23:28] == "file:" and "," in elt[:20]:  # , Keep channels only
            chans.append(elt[:20].strip())

    if len(chans) and zstegfiles:  # If there is files
        # Extract files to tmp folder
        tmpfolder = "aperisolve_"+randString()
        cmdline("mkdir "+quote(folder+tmpfolder))
        cmdline("cp "+quote(folder+img)+" "+quote(folder+tmpfolder+"/"+img))
        for c in chans:
            cmdline("cd "+quote(folder+tmpfolder)+" && \
                           zsteg "+quote(img)+" \
                           -E "+quote(c)+" > "+quote(c))

        # Zip output if exist and remove tmp folder
        cmdline("rm "+quote(folder+tmpfolder+"/"+img))  # Clean
        cmdline("cd "+quote(folder)+" && 7z a "+quote(tmpfolder+".7z") +
                " "+quote(tmpfolder)+" && rm -rf "+quote(tmpfolder))  # 7Zip
        return {"Output": zstegOut, "File": f"{folder}{tmpfolder}.7z"}
    return {"Output": zstegOut}


def processExif(img):
    """ Compute exiftool for a given image `img`. """
    return cmdline("exiftool -E -a -u -g1 "+quote(img))


def processSteghide(img, folder="./", passwd=""):
    """ Compute Steghide with @passwd as password on @img image.
    Return text output and 7z file containing extracted files. """

    # Avoid race conditions on file upload: create tmp folder
    tmpfolder = "aperisolve_"+randString()
    cmdline("mkdir "+quote(folder+tmpfolder))
    cmdline("cp "+quote(folder+img)+" "+quote(folder+tmpfolder+"/"+img))

    # Compute steghide
    out = cmdline("cd "+quote(folder+tmpfolder)+" && \
                   steghide extract -sf "+quote(img)+" \
                   -p "+quote(passwd)+" 2>&1")

    # Zip output if exist and remove tmp folder
    if "extracted" in out:  # Create 7z file
        cmdline("rm "+quote(folder+tmpfolder+"/"+img))  # Clean
        cmdline("cd "+quote(folder)+" && 7z a "+quote(tmpfolder+".7z") +
                " "+quote(tmpfolder)+" && rm -rf "+quote(tmpfolder))  # 7Zip
        return {"Output": out, "File": f"{folder}{tmpfolder}.7z"}
    else:
        cmdline("rm -rf "+quote(folder+tmpfolder))
        return {"Output": out}

