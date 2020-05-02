#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Aperi'Solve - Flask application.

Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"
"""

from data import app
from data import appfunct
from data import stega
from data.app import APP as appli

__all__ = [
    'app',
    'appfunct',
    'stega'
]

if __name__ == "__main__":
    appli.run()
