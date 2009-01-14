#!/bin/bash
#You have to install pychecker, pyflakes and pylint
pychecker -9 -T     -8  -# 200 --changetypes main.py
#pyflakes triggers a false positive with import *
pyflakes .|grep -v "import \*"
pylint -e main.py
for i in *; do
	if test -d $i; then
		#echo $i
		#pylint trigger a false positive with XML
		pylint -e $i|grep -v firstChild
	fi
done
