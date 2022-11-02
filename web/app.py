#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

import glob
import hashlib
import json
import os
import re
import time
from flask import Flask, render_template, request, jsonify, \
    send_from_directory, redirect, url_for, make_response, Response
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_USERNAME']
app.config["MONGO_URI"] += ':' + os.environ['MONGODB_PASSWORD']
app.config["MONGO_URI"] += '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/'
app.config["MONGO_URI"] += os.environ['MONGODB_DATABASE']
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 Mb max
app.config['LANGUAGES'] = {
    'en': 'English',
    'fr': 'Français'
}

mongo = PyMongo(app)
db = mongo.db

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = ["jpeg", "png", "bmp",
                      "gif", "tiff", "jpg", "jfif", "jpe", "tif"]


def load_i18n(request):
    """Load languages from language folder and session."""
    languages = {}
    language_list = glob.glob("language/*.json")
    for lang in language_list:
        lang_code = lang.split('/')[1].split('.')[0]
        with open(lang) as file:
            languages[lang_code] = json.load(file)
    cookie_lang = request.cookies.get('lang')
    lang_keys = app.config['LANGUAGES'].keys()
    if cookie_lang in lang_keys:
        return languages[cookie_lang]
    header_lang = request.accept_languages.best_match(lang_keys)
    if header_lang in lang_keys:
        return languages[header_lang]
    return languages["en"]


def mencoder(o):
    if type(o) == ObjectId:
        return str(o)
    return o.__str__


@app.route('/')
def home():
    return render_template('index.html', **load_i18n(request))


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

    file = request.files["file"]  # uploaded file
    ext = str(os.path.splitext(file.filename)[1].lower().lstrip("."))
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"Error": f"Invalid extension: {ext}"})

    # Compute informations
    hash_file = str(hashlib.md5(file.read()).hexdigest())
    hash_full = hash_file
    original_name = str(file.filename)
    use_password = bool("use_password" in request.form and
                        request.form["use_password"] == "true")
    password = None
    zext_bool = bool("zsteg_ext" in request.form and
                     request.form["zsteg_ext"] == "true")
    zall_bool = bool("zsteg_all" in request.form and
                     request.form["zsteg_all"] == "true")
    if "password" in request.form:
        password = str(request.form["password"])
    if use_password:
        pwd = password.encode("utf-8")
        salt = pwd+str(zext_bool).encode("utf-8")
        salt += str(zall_bool).encode("utf-8")
        file.seek(0)
        hash_full = str(hashlib.md5(file.read()+salt).hexdigest())
    file.seek(0)
    size = len(file.read())
    file.seek(0)
    t = time.time()
    json_config = {
        "original_name": original_name,
        "submit_date": t,
        "last_submit_date": t,
        "source_ip": request.remote_addr,
        "status": {},
        "image": f"image.{ext}",
        "size": size,
        "md5_image": hash_file,
        "md5_full": hash_full,
        "zsteg_all": zall_bool,
        "zsteg_ext": zext_bool,
        "use_password": use_password,
        "password": password
    }

    # Create image if doesnt exist
    folder = f"{UPLOAD_FOLDER}/{hash_full}"
    if not os.path.isdir(folder):  # create folder / file if doesnt exist
        os.mkdir(folder)
        file.save(f"{folder}/image.{ext}")  # Save image with new name

    # Insert in DB
    db.uploads.insert_one(json_config)

    # If image did not get upload in the past
    data = list(db.status.find({"md5_full": hash_full}))
    if not len(data):
        status = {
            "md5_full": hash_full,
            "md5_image": hash_file,
            "status": {
                "foremost": None,
                "view": None,
                "exiftool": None,
                "binwalk": None,
                "zsteg": None,
                "strings": None,
                "steghide": None,
                "outguess": None
            },
            "image": f"image.{ext}",
            "zsteg_all": zall_bool,
            "zsteg_ext": zext_bool,
            "password": password
        }
        db.status.insert_one(status)

    return jsonify({"File": hash_full})


@app.route('/install.sh')
def install():
    return send_from_directory('static', 'install.sh')


@app.route('/cheatsheet')
def cheatsheet():
    return render_template('cheatsheet.html', **load_i18n(request))


@app.route('/show')
def show():
    folder = f"{UPLOAD_FOLDER}/"
    dirs = os.listdir(folder)
    return render_template('show.html', dirs=dirs, **load_i18n(request))


@app.route('/<md5_file>')
def result_file(md5_file):
    if re.findall(r"\b([a-f\d]{32}|[A-F\d]{32})\b", md5_file):
        return render_template('result.html', **load_i18n(request),
                               md5=md5_file)
    return redirect(url_for('home'))


@app.route('/info/<file>')
@app.route('/info')
def info(file=None):
    if file is not None and \
       not re.findall(r"\b([a-f\d]{32}|[A-F\d]{32})\b", file):
        return redirect(url_for('home'))
    if file is None:
        data = list(db.uploads.find())
    else:
        data = list(db.uploads.find({"md5_image": file}))
    for d in data:
        d["source_ip"] = "**redaclanguagested**"
    return Response(response=json.dumps(data, default=mencoder),
                    status=200,
                    mimetype="application/json")


@app.route('/stats')
def stats():
    data = list(db.uploads.find())
    stats, pwds, names, uploads = {}, {}, {}, {}
    n = len(data)
    for d in data:
        d["source_ip"] = "**redacted**"
        pwds[d["password"]] = pwds.get(d["password"], 0) + 1
        names[d["original_name"]] = names.get(d["original_name"], 0) + 1
        uploads[d["submit_date"]] = uploads.get(d["submit_date"], 0) + 1

    stats["total_submit"] = n
    if "" not in pwds:
        pwds[""] = 0
    stats["nb_no_passwords"] = pwds[""]
    stats["nb_passwords"] = n - stats["nb_no_passwords"]
    del pwds[""]
    stats["passwords"] = pwds
    stats["names"] = names
    stats["first_submit"] = min(uploads.keys(), default=0)
    stats["last_submit"] = max(uploads.keys(), default=0)

    return Response(response=json.dumps(stats, default=mencoder),
                    status=200,
                    mimetype="application/json")


@app.route('/stats/<file>')
def stats_file(file=None):
    if file is None or \
       not re.findall(r"\b([a-f\d]{32}|[A-F\d]{32})\b", file):
        return redirect(url_for('home'))
    data = list(db.uploads.find({"md5_full": file}))
    if not len(data):
        return redirect(url_for('home'))

    data_image = list(db.uploads.find({"md5_image": data[0]["md5_image"]}))
    data_status = list(db.status.find({"md5_full": file}))[0]

    stats, pwds, names, uploads = {}, {}, {}, {}
    n = len(data_image)
    for d in data_image:
        d["source_ip"] = "**redacted**"
        pwds[d["password"]] = pwds.get(d["password"], 0) + 1
        names[d["original_name"]] = names.get(d["original_name"], 0) + 1
        uploads[d["submit_date"]] = uploads.get(d["submit_date"], 0) + 1

    stats["size"] = d["size"]
    stats["status"] = data_status["status"]
    stats["total_submit"] = n
    if "" not in pwds:
        pwds[""] = 0
    stats["nb_no_passwords"] = pwds[""]
    stats["nb_passwords"] = n - stats["nb_no_passwords"]
    del pwds[""]
    stats["passwords"] = pwds
    stats["names"] = names
    stats["image"] = data_status["image"]
    stats["md5_image"] = data[0]["md5_image"]
    stats["first_submit"] = min(uploads.keys(), default=0)
    stats["last_submit"] = max(uploads.keys(), default=0)

    return Response(response=json.dumps(stats, default=mencoder),
                    status=200,
                    mimetype="application/json")


@app.route("/top")
def top():
    data = list(db.uploads.aggregate([
        {"$group": {"_id": "$md5_full", "count": {"$sum": 1}}}
    ]))
    stats = {}
    for d in data:
        stats[d["_id"]] = d["count"]
    sorted_stats = dict(sorted(stats.items(),
                        key=lambda item: str(item[1])+item[0],
                        reverse=True))

    return Response(response=json.dumps(sorted_stats, default=mencoder),
                    status=200,
                    mimetype="application/json")


@app.route('/lang/<lang>')
def change_lang(lang=None):
    lang_keys = app.config['LANGUAGES'].keys()
    if lang in lang_keys:
        response = make_response(redirect(request.referrer))
        response.set_cookie('lang', lang)
        return response
    return redirect(url_for('home'))


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
