#!/usr/bin/python3
# -*- encoding: utf-8 -*-
# pylint: disable=W0703

"""Aperi'Solve - Flask application.

Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from data.appfunct import get_ext, cmdline
from data import stega


APP = Flask(__name__)
DIR_PATH = os.path.dirname(os.path.realpath(__file__))


APP_PORT = int(os.getenv('APP_PORT', '80'))
APP_RM_FILE_TIME = int(os.getenv('APP_RM_FILE_TIME', '10'))
APP.config['MAX_CONTENT_LENGTH'] = int(
    os.getenv('APP_MAX_SIZE', str(16 * 1024 * 1024)))  # 16 Mega per image maxi
# Supported image types
IMG_EXTS = ["jpeg", "png", "bmp", "gif", "tiff", "jpg", "jfif", "jpe", "tif"]


@APP.route('/')
def main():
    """Index and Upload Page."""
    return render_template('index.html')


@APP.errorhandler(Exception)
def error_handler(flask_error):
    """Error handler, mostly for wrong file."""
    if "cannot identify" in str(flask_error):  # Unknow image format
        # cannot identify image file 'uploads/xxx.jpg'
        _, *filename, __ = str(flask_error).split("'")  # Recover filename
        filename = ''.join(filename)
        os.remove(filename)  # Remove invalid file
        return jsonify({"Error": "Unknow file format."})
    return jsonify({"Error": str(flask_error)})


@APP.route('/upload', methods=['POST'])
def upload_image():
    """Upload image on server."""
    if "fileup" in request.files:
        fileup = request.files["fileup"]  # uploaded file
        ext = get_ext(fileup.filename)
        if ext not in IMG_EXTS:
            return jsonify({"Error": "Invalid extension: "+str(ext)})
        newfilename = fileup.filename  # rand_string()+"."+ext
        newpathfile = f"{DIR_PATH}/uploads/{newfilename}"
        fileup.save(newpathfile)  # Save file with new name
        return jsonify({"File": newfilename})
    return jsonify({"Error": "No file submitted."})


@APP.route('/process', methods=['POST'])
def process():
    """Process layers decomposition.

    @filename : Uploaded image (filename)
    ---
    Return JSON array with:
    Images : n * 8 images (path)
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        # Generate Images
        images = stega.process_image(filename, f"{DIR_PATH}/uploads/")
        if "File" in images:
            images["File"] = images["File"].strip(DIR_PATH)
        return jsonify({"Images": images})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/zsteg', methods=['POST'])
def zsteg():
    """Process zsteg analysis.

    @filename : Uploaded image (filename)
    @allzsteg : -a option for zsteg (bool)
    @zstegfiles : extract option for zsteg (bool)
    Return JSON array with:
    Zsteg : zsteg output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        allzsteg, zstegfiles = False, False
        if "allzsteg" in request.form:
            allzsteg = bool(int(request.form["allzsteg"]))
        if "zstegfiles" in request.form:
            zstegfiles = bool(int(request.form["zstegfiles"]))
        zstegoutput = stega.process_zsteg(filename, f"{DIR_PATH}/uploads/",
                                          allzsteg, zstegfiles)
        if "File" in zstegoutput:
            zstegoutput["File"] = zstegoutput["File"].strip(DIR_PATH)
        return jsonify({"Zsteg": zstegoutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/binwalk', methods=['POST'])
def binwalk():
    """Process binwalk analysis.

    @filename : Uploaded image (filename)
    Return JSON array with:
    Binwalk : binwalk output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"

        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})

        binwalkoutput = stega.process_binwalk(filename, f"{DIR_PATH}/uploads/")
        if "File" in binwalkoutput:
            binwalkoutput["File"] = binwalkoutput["File"].strip(DIR_PATH)

        return jsonify({"Binwalk": binwalkoutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/foremost', methods=['POST'])
def foremost():
    """Process foremost analysis.

    @filename : Uploaded image (filename)
    Return JSON arr["File"]ay with:
    Binwalk : binwalk output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        foremostoutput = stega.process_foremost(filename,
                                                f"{DIR_PATH}/uploads/")
        if "File" in foremostoutput:
            foremostoutput["File"] = foremostoutput["File"].strip(DIR_PATH)
        return jsonify({"Foremost": foremostoutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/steghide', methods=['POST'])
def steghide():
    """Process steghide analysis.

    @filename : Uploaded image (filename)
    @passwdsteg : Steghide passwd
    Return JSON array with:
    Steghide : Steghide output
    Error: Error if file doesnt exist / password is wrong
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        if len(request.form["passwdsteg"]) > 0:
            steghideoutput = stega.process_steghide(
                filename, f"{DIR_PATH}/uploads/", request.form["passwdsteg"])
        else:
            steghideoutput = {"Error":
                              "Steghide doesn't work without password."}
        if "File" in steghideoutput:
            steghideoutput["File"] = steghideoutput["File"].strip(DIR_PATH)
        return jsonify({"Steghide": steghideoutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/outguess', methods=['POST'])
def outguess():
    """Process outguess analysis.

    @filename : Uploaded image (filename)
    @passwdsteg : Outguess passwd
    Return JSON array with:
    Steghide : Outguess output
    Error: Error if file doesnt exist / password is wrong
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        outguessoutput = stega.process_outguess(
            filename, f"{DIR_PATH}/uploads/", request.form["passwdsteg"])
        if "File" in outguessoutput:
            outguessoutput["File"] = outguessoutput["File"].strip(DIR_PATH)
        return jsonify({"Outguess": outguessoutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/exiftool', methods=['POST'])
def exiftool():
    """Process exiftools analysis.

    @filename : Uploaded image (filename)
    Return JSON array with:
    Exiftool : Exiftool output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        exiftooloutput = stega.process_exif(filename, f"{DIR_PATH}/uploads/")
        return jsonify({"Exiftool": exiftooloutput})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/strings', methods=['POST'])
def strings():
    """Process strings analysis.

    @filename : Uploaded image (filename)
    Return JSON array with:
    Strings : Strings output
    Error: Error if file doesnt exist
    """
    if "filename" in request.form:
        filename = request.form["filename"]  # already uploaded file
        pathfile = f"{DIR_PATH}/uploads/{filename}"
        if not os.path.isfile(pathfile):
            return jsonify({"Error": "File doesn't exist."})
        stringsimg = stega.process_strings(filename, f"{DIR_PATH}/uploads/")
        return jsonify({"Strings": stringsimg})
    return jsonify({"Error": "No filename submitted."})


@APP.route('/uploads/<path>')
def uploads(path):
    """Route for uploaded/computed files.

    Remove old uploaded/computed files on each requests
    """
    # First remove old files
    cmdline(f"find {DIR_PATH}/uploads/ -mmin +{APP_RM_FILE_TIME} "
            r"-type f  \( -iname \"*\" ! -iname \".gitkeep\" \) "
            r"-exec rm -fv {} \;")
    return send_from_directory('uploads', path)


if __name__ == '__main__':
    APP.run(debug=True, host='0.0.0.0', port=APP_PORT)
