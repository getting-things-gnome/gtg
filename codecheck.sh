#!/bin/bash
#You have to install pychecker, pyflakes and pylint
pychecker -9 -T     -8  -# 200 --changetypes main.py
pyflakes .
