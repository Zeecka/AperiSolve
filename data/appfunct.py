#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application
Aperi'Solve is a web steganography plateform.

__author__ = "@Zeecka"
__copyright__ = "WTFPL"

"""

from subprocess import PIPE, Popen
import random
import os
import string


def randString(length=10):
    """ Generate random string [a-zA-Z0-9] with size of @length. """
    charset = string.ascii_uppercase+string.ascii_lowercase+string.digits
    return ''.join((random.choice(charset) for i in range(length)))


def cmdline(cmd, sh=True):
    """ Execute command @cmd and return output using Popen(). """
    process = Popen(
        args=cmd,
        stdout=PIPE,
        shell=sh
    )
    return process.communicate()[0].decode("ISO-8859-1")


def rmExt(f):
    """ Remove filename @f extention if exist. """
    if "." in f:
        return '.'.join(f.split(".")[:-1])
    return f


def getExt(f):
    """ Get extention from @f file if exist. """
    return os.path.splitext(f)[1].lower().lstrip(".")
