#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

from threading import Thread
from mongo import db_status, get_status
from config import UPLOAD_FOLDER


class Module(Thread):
    def __init__(self, md5):
        Thread.__init__(self)
        self.md5 = md5
        self.folder = f"{UPLOAD_FOLDER}/{md5}"
        self.config = self.get_config()

    def get_config(self):
        data = list(db_status.find({"md5_full": self.md5}))
        if len(data):
            return data[0]

    def get_config_status(self, name):
        return get_status(name)

    def set_config_status(self, name, status):
        db_status.update_one({"md5_full": self.md5},
                             {"$set": {f"status.{name}": status}})
