#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
__author__ = "@Zeecka"
__copyright__ = "WTFPL"
"""

from subprocess import PIPE, Popen
import random
import os
import string


def rand_string(length=10):
    """Generate random string [a-zA-Z0-9] with size of @length."""
    charset = string.ascii_uppercase+string.ascii_lowercase+string.digits
    return ''.join((random.choice(charset) for i in range(length)))


def cmdline(cmd, shell=True):
    """Execute command @cmd and return output using Popen()."""
    process = Popen(
        args=cmd,
        stdout=PIPE,
        shell=shell
    )
    return process.communicate()[0].decode("ISO-8859-1")


def rm_ext(filename):
    """Remove filename @filename extention if exist."""
    if "." in filename:
        return '.'.join(filename.split(".")[:-1])
    return filename


def get_ext(filename):
    """Get extention from @filename file if exist."""
    return os.path.splitext(filename)[1].lower().lstrip(".")