#!/usr/bin/python3
# -*- encoding: utf-8 -*-
# pylint: disable=W0703

"""Aperi'Solve - Flask application.

Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"
"""

import os
import re
import shutil
import imghdr
from shlex import quote
import numpy as np  # type: ignore
from PIL import Image  # type: ignore
from data.appfunct import rand_string, cmdline, rm_ext


def is_valid_image(filename):
    """Raise Exception / Return False if Image can't be opened with PIL."""
    try:
        Image.open(filename)
    except Exception:
        return False
    return True


def compute_layers(arr, mode, filename, folder="./"):
    """Compute each bits visual image for a given layer `arr`."""
    for i in range(8):  # 8 bits layer
        newdata = (arr >> i) % 2 * 255  # Highlighting the layer bit `i`
        if mode == 'RGBA':  # Force alpha layer (4th) to 255 if exist
            newdata[:, :, 3] = 255
        Image.fromarray(newdata, mode).save(f"{folder}{filename}_{i+1}.png")


def process_image(img, folder="./"):
    """Apply compute_layers() on each `img` layers and save images."""
    filename = rm_ext(img)
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
    compute_layers(npimg, img_pil.mode, f"{filename}_rgb", folder)  # rgb
    compute_layers(imgr, 'L', f"{filename}_r", folder)  # r
    compute_layers(imgg, 'L', f"{filename}_g", folder)  # g
    compute_layers(imgb, 'L', f"{filename}_b", folder)  # b

    # set images names
    images_name["Supperimposed"] = [f"{filename}_rgb_{i+1}.png" for i
                                    in range(8)]
    images_name["Red"] = [f"{filename}_r_{i+1}.png" for i in range(8)]
    images_name["Green"] = [f"{filename}_g_{i+1}.png" for i in range(8)]
    images_name["Blue"] = [f"{filename}_b_{i+1}.png" for i in range(8)]

    if img_pil.mode == "RGBA":  # Should be RGB or RGBA
        compute_layers(npimg[:, :, 3], 'L', f"{filename}_a", folder)  # b
        images_name["Alpha"] = [f"{filename}_a_{i+1}.png" for i in range(8)]

    return images_name


def process_zsteg(img, folder="./", allzsteg=False, zstegfiles=False):
    """Compute zsteg on a given image and return output."""
    # First, cast to PNG if not PNG/BMP (zsteg support only PNG/BMP)
    if imghdr.what(f"{folder}{img}") not in ["png", "bmp"]:
        img_pil = Image.open(f"{folder}{img}")
        img_pil = img_pil.convert('RGBA')  # Cast RGBA PNG
        img = rm_ext(img)+"_zsteg.png"  # New name
        img_pil.save(f"{folder}{img}")

    if allzsteg:
        zsteg_out = cmdline(f"zsteg {quote(folder+img)} --all")
    else:
        zsteg_out = cmdline(f"zsteg {quote(folder+img)}")

    chans = []  # Extract zsteg chans containing "file:"
    rzsteg_out = re.split("\r|\n", zsteg_out)
    for elt in rzsteg_out:
        if elt[23:28] == "file:" and "," in elt[:20]:  # , Keep channels only
            chans.append(elt[:20].strip())

    if len(chans) > 0 and zstegfiles:  # If there is files
        # Extract files to tmp folder
        tmpfolder = "aperisolve_"+rand_string()
        os.mkdir(folder+tmpfolder)
        shutil.copyfile(folder+img, folder+tmpfolder+"/"+img)
        for channel in chans:
            cmdline(f"cd {quote(folder+tmpfolder)} && "
                    f"zsteg {quote(img)} "
                    f"-E {quote(channel)} > {quote(channel)}")

        # Zip output if exist and remove tmp folder
        os.remove(folder+tmpfolder+"/"+img)  # Clean
        cmdline(f"cd {quote(folder)} && "
                f"7z a {quote(tmpfolder+'.7z')} {quote(tmpfolder)}")  # 7Zip
        shutil.rmtree(folder+tmpfolder)
        return {"Output": zsteg_out, "File": f"{folder}{tmpfolder}.7z"}
    return {"Output": zsteg_out}


def process_steghide(img, folder="./", passwd=""):
    """Compute Steghide with @passwd as password on @img image.

    Return text output and 7z file containing extracted files.
    """
    # Avoid race conditions on file upload: create tmp folder
    tmpfolder = "aperisolve_"+rand_string()
    os.mkdir(folder+tmpfolder)
    shutil.copyfile(folder+img, folder+tmpfolder+"/"+img)

    # Compute steghide
    out = cmdline(f"cd {quote(folder+tmpfolder)} && "
                  f"steghide extract -sf {quote(img)} "
                  f"-p {quote(passwd)} 2>&1")

    # Zip output if exist and remove tmp folder
    if "extracted" in out:  # Create 7z file
        os.remove(folder+tmpfolder+"/"+img)  # Clean
        cmdline(f"cd {quote(folder)} && "
                f"7z a {quote(tmpfolder+'.7z')} {quote(tmpfolder)}")  # 7Zip
        shutil.rmtree(folder+tmpfolder)
        return {"Output": out, "File": f"{folder}{tmpfolder}.7z"}

    shutil.rmtree(folder+tmpfolder)
    return {"Output": out}


def process_outguess(img, folder="./", passwd=""):
    """Compute Outguess with @passwd as password on @img image.

    Return text output and 7z file containing extracted files.
    """
    # Avoid race conditions on file upload: create tmp folder
    tmpfolder = "aperisolve_"+rand_string()
    os.mkdir(folder+tmpfolder)
    shutil.copyfile(folder+img, folder+tmpfolder+"/"+img)

    # Compute steghide

    if len(passwd) > 0:
        out = cmdline(f"cd {quote(folder+tmpfolder)} && "
                      f"outguess -k {quote(passwd)} -r {quote(img)} data 2>&1")
    else:
        out = cmdline(f"cd {quote(folder+tmpfolder)} && "
                      f"outguess -r {quote(img)} data 2>&1")

    # Zip output if exist and remove tmp folder
    if "Extracted datalen" not in out and \
       "Unknown data type" not in out:  # Create 7z file
        os.remove(folder+tmpfolder+"/"+img)  # Clean
        cmdline(f"cd {quote(folder)} && "
                f"7z a {quote(tmpfolder+'.7z')} {quote(tmpfolder)}")  # 7Zip
        shutil.rmtree(folder+tmpfolder)
        return {"Output": out, "File": f"{folder}{tmpfolder}.7z"}

    shutil.rmtree(folder+tmpfolder)
    return {"Output": out}


def process_binwalk(img, folder="./"):
    """Compute Binwalk on @img image.

    Return text output and 7z file containing extracted files.
    """
    # Avoid race conditions on file upload: create tmp folder
    tmpfolder = "aperisolve_"+rand_string()
    os.mkdir(folder+tmpfolder)
    shutil.copyfile(folder+img, folder+tmpfolder+"/"+img)

    # Compute steghide
    out = cmdline(f"cd {quote(folder+tmpfolder)} && "
                  f"binwalk --dd='.*' {quote(img)} 2>&1")

    # Zip output if exist and remove tmp folder
    if "0x" in out:  # Create 7z file
        os.remove(folder+tmpfolder+"/"+img)  # Clean
        cmdline(f"cd {quote(folder)} && "
                f"7z a {quote(tmpfolder+'.7z')} {quote(tmpfolder)}")  # 7Zip
        shutil.rmtree(folder+tmpfolder)
        return {"Output": out, "File": f"{folder}{tmpfolder}.7z"}

    shutil.rmtree(folder+tmpfolder)
    return {"Output": out}


def process_foremost(img, folder="./"):
    """Compute Foremost on @img image.

    Return text output and 7z file containing extracted files.
    """
    # Avoid race conditions on file upload: create tmp folder
    tmpfolder = "aperisolve_"+rand_string()
    os.mkdir(folder+tmpfolder)
    shutil.copyfile(folder+img, folder+tmpfolder+"/"+img)

    # Compute steghide
    out = cmdline(f"cd {quote(folder+tmpfolder)} && "
                  f"foremost {quote(img)}")

    # Zip output and remove tmp folder
    os.remove(folder+tmpfolder+"/"+img)  # Clean
    cmdline(f"cd {quote(folder)} && "
            f"7z a {quote(tmpfolder+'.7z')} {quote(tmpfolder)}")  # 7Zip
    shutil.rmtree(folder+tmpfolder)
    return {"Output": out, "File": f"{folder}{tmpfolder}.7z"}


def process_strings(img, folder="./"):
    """Compute strings on img."""
    return cmdline("strings "+quote(folder+img))


def process_exif(img, folder="./"):
    """Compute exiftool for a given image `img`."""
    return cmdline("exiftool -E -a -u -g1 "+quote(folder+img))
