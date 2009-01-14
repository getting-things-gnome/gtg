#!/bin/bash
#You have to install pychecker, pyflakes and pylint
#
#This script will only check for important error
#To a more in-depth check, launch "pylint folder_name" on any folder
#
#It will give you a list of error(E), warning(W),coding style rules(C)
#And programing rules (R).
#At the end, you will have statistics with the ID of each error.
#Use,for example, pylint --help-msg=W0613 to get information about
#This error
#If this is a false positive, in the code add the following comment
#at the error line : #pylint: disable-msg=W0613
#
#
pychecker -9 -T     -8  -# 200 --changetypes main.py
#pyflakes triggers a false positive with import *
pyflakes .|grep -v "import \*"
pylint -e main.py
for i in *; do
	if test -d $i; then
		#echo $i
		#pylint trigger a false positive with XML
		pylint -e $i
	fi
done
