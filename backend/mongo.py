#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

import pymongo
import os


def get_db():
    mongo_uri = 'mongodb://' + os.environ['MONGODB_USERNAME']
    mongo_uri += ':' + os.environ['MONGODB_PASSWORD']
    mongo_uri += '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/'
    mongo_uri += os.environ['MONGODB_DATABASE']
    myclient = pymongo.MongoClient(mongo_uri)
    return myclient[os.environ['MONGODB_DATABASE']]


mydb = get_db()
db_uploads = mydb["uploads"]
db_status = mydb["status"]


def get_status(file):
    data = list(db_status.find({"md5_full": file}))
    if len(data):
        return data[0]["status"]
