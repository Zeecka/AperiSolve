#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application
Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"

"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from appfunct import *
import stega

app = Flask(__name__)

APP_PORT = 80
APP_RM_FILE_TIME = 10  # Keep images for N minutes maximum
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 Mega per image maxi
# Supported image types
imgExts = ["jpeg", "png", "bmp", "gif", "tiff", "jpg", "jfif", "jpe", "tif"]

# Set constant from ENV

if "APP_MAX_SIZE" in os.environ:
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ['APP_MAX_SIZE'])
if "APP_RM_FILE_TIME" in os.environ:
    APP_RM_FILE_TIME = int(os.environ['APP_RM_FILE_TIME'])
if "APP_PORT" in os.environ:
    APP_PORT = int(os.environ['APP_PORT'])


@app.route('/')
def main():
    """ Upload Page """
    return render_template('index.html')


@app.errorhandler(Exception)
def error_handler(e):
    """ Error handler, mostly for wrong file """
    if "cannot identify" in str(e):  # Unknow image format
        # cannot identify image file 'uploads/xxx.jpg'
        a, *filename, b = str(e).split("'")  # Recover filename
        filename = ''.join(filename)
        os.remove(filename)  # Remove invalid file
        return jsonify({"Error": "Unknow file format."})
    return jsonify({"Error": str(e)})


@app.route('/process', methods=['POST'])
def process():
    """ Process page (upload), take 4 parameters:
    @fileup : Uploaded image (file)
    @allzsteg : Active --all option for zsteg (bool 1/0)
    @zstegfiles : Active --extract option for zsteg (bool 1/0)
    @passwdsteghide : Password for steghide
    ---
    Return JSON array with:
    Images : n * 8 images (path)
    Zsteg : Zsteg output (string)
    Exiftool : Exiftool output (string)
    Steghide : Steghide output (string)
    Error : Error message (string)
    """
    if "fileup" in request.files:
        f = request.files["fileup"]  # uploaded file
        ext = getExt(f.filename)

        if ext not in imgExts:
            return jsonify({"Error": "Invalid extension: "+str(ext)})

        newfilename = randString()+"."+ext
        newpathfile = f"uploads/{newfilename}"
        f.save(newpathfile)  # Save file with new name

        isval = stega.isValidImage(newpathfile)  # error_handler if invalid
        images = stega.processImage(newfilename, "uploads/")  # Generate Images

        allzsteg, zstegfiles = False, False
        if "allzsteg" in request.form:
            allzsteg = bool(int(request.form["allzsteg"]))
        if "zstegfiles" in request.form:
            zstegfiles = bool(int(request.form["zstegfiles"]))

        zstegoutput = stega.processZsteg(newfilename, "uploads/", allzsteg,
                                         zstegfiles)

        if len(request.form["passwdsteghide"]):
            steghideoutput = stega.processSteghide(
                newfilename, "uploads/", request.form["passwdsteghide"])
        else:
            steghideoutput = {"Output":
                              "Steghide doesn't work without password."}

        exifoutput = stega.processExif(newpathfile)  # Generate Images

        return jsonify({"Success": newfilename,
                        "Images": images,
                        "Zsteg": zstegoutput,
                        "Exiftool": exifoutput,
                        "Steghide": steghideoutput})
    return jsonify({"Error": "No file submitted."})


@app.route('/uploads/<path>')
def uploads(path):
    """ Route for uploaded/computed files
    Remove old uploaded/computed files on each requests
    """

    # First remove old files
    cmdline(f"find uploads/ -mmin +{APP_RM_FILE_TIME} " +
             "-type f -exec rm -fv {} \;")
    return send_from_directory('uploads', path)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=APP_PORT)

