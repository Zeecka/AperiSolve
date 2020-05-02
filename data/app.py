#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Aperi'Solve - Flask application.

Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"

"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from appfunct import getExt, cmdline
import stega

app = Flask(__name__)
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

APP_PORT = int(os.getenv('APP_PORT', 80))
APP_RM_FILE_TIME = int(os.getenv('APP_RM_FILE_TIME', 10))  # Keep images for ?m
app.config['MAX_CONTENT_LENGTH'] = int(
    os.getenv('APP_MAX_SIZE', 16 * 1024 * 1024))  # 16 Mega per image maxi
# Supported image types
imgExts = ["jpeg", "png", "bmp", "gif", "tiff", "jpg", "jfif", "jpe", "tif"]


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


@app.route('/upload', methods=['POST'])
def uploadImage():
    """ Upload image on server
    @fileup: Uploaded image (file)
    ---
    Return JSON array with:
    File: New file name on server
    Error: Error if upload fail
    """

    if "fileup" in request.files:
        f = request.files["fileup"]  # uploaded file
        ext = getExt(f.filename)

        if ext not in imgExts:
            return jsonify({"Error": "Invalid extension: "+str(ext)})

        newfilename = f.filename  # randString()+"."+ext
        newpathfile = f"{DIR_PATH}/uploads/{newfilename}"
        f.save(newpathfile)  # Save file with new name

        return jsonify({"File": newfilename})

    return jsonify({"Error": "No file submitted."})


@app.route('/process', methods=['POST'])
def process():
    """ Process layers decomposition
    @filename : Uploaded image (filename)
    ---
    Return JSON array with:
    Images : n * 8 images (path)
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        images = stega.processImage(f, f"{DIR_PATH}/uploads/")  # Generate Images
        if "File" in images:
            images["File"] = images["File"].strip(DIR_PATH)

        return jsonify({"Images": images})
    return jsonify({"Error": "No filename submitted."})


@app.route('/zsteg', methods=['POST'])
def zsteg():
    """ Process zsteg analysis.
    @filename : Uploaded image (filename)
    @allzsteg : -a option for zsteg (bool)
    @zstegfiles : extract option for zsteg (bool)
    Return JSON array with:
    Zsteg : zsteg output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        allzsteg, zstegfiles = False, False
        if "allzsteg" in request.form:
            allzsteg = bool(int(request.form["allzsteg"]))
        if "zstegfiles" in request.form:
            zstegfiles = bool(int(request.form["zstegfiles"]))

        zstegoutput = stega.processZsteg(f, f"{DIR_PATH}/uploads/", allzsteg,
                                         zstegfiles)
        if "File" in zstegoutput:
            zstegoutput["File"] = zstegoutput["File"].strip(DIR_PATH)

        return jsonify({"Zsteg": zstegoutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/binwalk', methods=['POST'])
def binwalk():
    """ Process binwalk analysis.
    @filename : Uploaded image (filename)
    Return JSON array with:
    Binwalk : binwalk output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        binwalkoutput = stega.processBinwalk(f, f"{DIR_PATH}/uploads/")
        if "File" in binwalkoutput:
            binwalkoutput["File"] = binwalkoutput["File"].strip(DIR_PATH)

        return jsonify({"Binwalk": binwalkoutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/foremost', methods=['POST'])
def foremost():
    """ Process foremost analysis.
    @filename : Uploaded image (filename)
    Return JSON arr["File"]ay with:
    Binwalk : binwalk output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        foremostoutput = stega.processForemost(f, f"{DIR_PATH}/uploads/")
        if "File" in foremostoutput:
            foremostoutput["File"] = foremostoutput["File"].strip(DIR_PATH)
        return jsonify({"Foremost": foremostoutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/steghide', methods=['POST'])
def steghide():
    """ Process steghide analysis.
    @filename : Uploaded image (filename)
    @passwdsteg : Steghide passwd
    Return JSON array with:
    Steghide : Steghide output
    Error: Error if file doesnt exist / password is wrong
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        if len(request.form["passwdsteg"]):
            steghideoutput = stega.processSteghide(
                f, f"{DIR_PATH}/uploads/", request.form["passwdsteg"])
        else:
            steghideoutput = {"Error":
                              "Steghide doesn't work without password."}

        if "File" in steghideoutput:
            steghideoutput["File"] = steghideoutput["File"].strip(DIR_PATH)
        return jsonify({"Steghide": steghideoutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/outguess', methods=['POST'])
def outguess():
    """ Process outguess analysis.
    @filename : Uploaded image (filename)
    @passwdsteg : Outguess passwd
    Return JSON array with:
    Steghide : Outguess output
    Error: Error if file doesnt exist / password is wrong
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        outguessoutput = stega.processOutguess(
            f, f"{DIR_PATH}/uploads/", request.form["passwdsteg"])

        if "File" in outguessoutput:
            outguessoutput["File"] = outguessoutput["File"].strip(DIR_PATH)
        return jsonify({"Outguess": outguessoutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/exiftool', methods=['POST'])
def exiftool():
    """ Process exiftools analysis.
    @filename : Uploaded image (filename)
    Return JSON array with:
    Exiftool : Exiftool output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        exiftooloutput = stega.processExif(f, f"{DIR_PATH}/uploads/")

        if "File" in exiftooloutput:
            exiftooloutput["File"] = exiftooloutput["File"].strip(DIR_PATH)

        return jsonify({"Exiftool": exiftooloutput})
    return jsonify({"Error": "No filename submitted."})


@app.route('/strings', methods=['POST'])
def strings():
    """ Process strings analysis.
    @filename : Uploaded image (filename)
    Return JSON array with:
    Strings : Strings output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        f = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{f}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        stringsimg = stega.processStrings(f, f"{DIR_PATH}/uploads/")

        return jsonify({"Strings": stringsimg})
    return jsonify({"Error": "No filename submitted."})


@app.route('/uploads/<path>')
def uploads(path):
    """ Route for uploaded/computed files
    Remove old uploaded/computed files on each requests
    """

    # First remove old files
    cmdline(f"find {DIR_PATH}/uploads/ -mmin +{APP_RM_FILE_TIME} "
            r"-type f  \( -iname \"*\" ! -iname \".gitkeep\" \) "
            r"-exec rm -fv {} \;")
    return send_from_directory('uploads', path)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=APP_PORT)
