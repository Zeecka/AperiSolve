#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
__author__ = "@Zeecka"
__copyright__ = "WTFPL"
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from appfunct import get_ext, cmdline
import hashlib
import json
import os
import re
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 Mb max

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = ["jpeg", "png", "bmp",
                      "gif", "tiff", "jpg", "jfif", "jpe", "tif"]


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_image():
    """
        @file : file
        @zsteg_ext : bool
        @zsteg_all : bool
        @use_password : bool
        @password : str
    """

    # Handle Errors
    if "file" not in request.files:
        return jsonify({"Error": "File not found."})
    if "zsteg_ext" not in request.form \
        or "zsteg_all" not in request.form  \
        or "use_password" not in request.form  \
        or "password" not in request.form:
        return jsonify({"Error": "Input not found."})
    
    file = request.files["file"]  # uploaded file
    ext = str(get_ext(file.filename))
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"Error": f"Invalid extension: {ext}"})
    
    # Compute informations
    hash_file = str(hashlib.md5(file.read()).hexdigest())
    hash_full = hash_file
    original_name = str(file.filename)
    use_password = bool(request.form["use_password"] == "true")
    password = str(request.form["password"])
    if use_password:
        pwd = password.encode("utf-8")
        hash_full = str(hashlib.md5(file.read()+pwd).hexdigest())
    file.seek(0)
    size = len(file.read())
    file.seek(0)
    t = time.time()
    json_config = {
        "original_name" : original_name,
        "submit_date" : t,
        "last_submit_date" : t,
        "status" : {},
        "image" : f"image.{ext}",
        "size" : size,
        "md5_image" : hash_file,
        "md5_full" : hash_full,
        "zsteg_ext" : request.form["zsteg_ext"] == "true",
        "zsteg_all" : request.form["zsteg_all"] == "true",
        "use_password" : use_password,
        "password" : password
    }

    # Save file and config
    folder = f"{UPLOAD_FOLDER}/{hash_full}"
    if not os.path.isdir(folder):  # create folder / file if doesnt exist
        os.mkdir(folder)
        file.save(f"{folder}/image.{ext}")  # Save image with new name
        with open(f"{folder}/config.json", 'w') as fp: # Save config
            json.dump(json_config, fp)
    else:  # Update zsteg_all / exzsteg_ext if needed, update last_submit_date
        with open(f"{UPLOAD_FOLDER}/{hash_full}/config.json", "r") as jsonFile:
            data = json.load(jsonFile)
        if request.form["zsteg_all"] == "true":
            data["zsteg_all"] = True
        if request.form["zsteg_ext"] == "true":
            data["zsteg_ext"] = True
        data["last_submit_date"] = t
        with open(f"{UPLOAD_FOLDER}/{hash_full}/config.json", "w") as jsonFile:
            json.dump(data, jsonFile)

    # Stats
    # Update passwords.json
    with open(f"{UPLOAD_FOLDER}/passwords.json", "r") as jsonFile:
        data = json.load(jsonFile)
    if use_password:
        data["count_with_password"] += 1
        data["passwords"][password] = data["passwords"].get(password, 0) + 1
    else:
        data["count_without_password"] += 1
    with open(f"{UPLOAD_FOLDER}/passwords.json", "w") as jsonFile:
        json.dump(data, jsonFile)

    # Update stats.json
    with open(f"{UPLOAD_FOLDER}/stats.json", "r") as jsonFile:
        data = json.load(jsonFile)
    data["count"] = data.get("count", 0) + 1
    if hash_file not in data["images"]:
        data["images"][hash_file] = { "count" : 0, "names" : [], "passwords" : []}
    data["images"][hash_file]["count"] += 1
    if original_name not in data["images"][hash_file]["names"]:
        data["images"][hash_file]["names"].append(original_name)
    if use_password and password not in data["images"][hash_file]["passwords"]:
        data["images"][hash_file]["passwords"].append(password)
    
    with open(f"{UPLOAD_FOLDER}/stats.json", "w") as jsonFile:
        json.dump(data, jsonFile)

    return jsonify({"File": hash_full})


@app.route('/<md5_file>')
def result_file(md5_file):
    if re.findall(r"\b([a-f\d]{32}|[A-F\d]{32})\b", md5_file):
        return render_template('result.html', md5=md5_file)
    return redirect(url_for('home'))


@app.route('/show')
def show():
    return render_template('show.html')


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)
