#!/usr/bin/python3
# -*- encoding: utf-8 -*-

from subprocess import PIPE, Popen
import random
import string

def cmd_exec(cmd, shell=True):
    """Execute command @cmd and return output using Popen()."""
    print(cmd)
    process = Popen(
        args=cmd,
        stdout=PIPE,
        shell=shell
    )
    return process.communicate()[0].decode("ISO-8859-1")
