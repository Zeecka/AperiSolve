#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Aperi'Solve - Flask application.
Aperi'Solve is a web steganography plateform.
"""
__author__ = "@Zeecka"
__copyright__ = "WTFPL"

from subprocess import PIPE, Popen


def cmd(cmd, shell=True):
    """Execute command @cmd and return output using Popen()."""
    print(cmd)
    process = Popen(
        args=cmd,
        stdout=PIPE,
        shell=shell
    )
    return process.communicate()[0].decode("ISO-8859-1")
