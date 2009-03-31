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
#We do not check the following.
#We might do in the future
#C0324 : space after a comma (this one is buggy)
#C0103 : variable name should match a given regexp
#C0301  : lines too long (maybe we should care)
#C0111 : Missing docstring (we should care but later)
#R0914 : too many variable (why should we care ?)
#R0903 : class had too few methods
#R0915  : function has too many statements
#R0904 : too many public methods
#R0912 : function has too many branches
#R0201 : method could be a function
#R0913 : too many arguments
#C0323 : operator not followed by a space
#R0902 : too many attributes in the class
#W0102 : [] or {} as argument (don't understand why it's bad)
#W0232 : no __init__() (if I don't write it, I don't need it)
#W0105 : string statement has no effect(=documentation)
#C0321 : more than one statement on the same line (is that bad ?)
#W0401 : * wildcard import (yes, we use them)
#W0142 : use of * and ** arguments (yes, I find that handy)
#I0011 : Locally disabling. We don't care if we disabled locally

#pylint argument :
disabled="C0324,C0103,C0301,C0111,R0914,R0903,R0915,R0904,R0912,R0201,R0913,C0323,R0902,W0102,W0232,W0105,C0321,W0401,W0142,I0011"
args="--rcfile=/dev/null --include-ids=y --reports=n"
#grepped_out="Locally disabling"
#pylint doesn't recognize gettext _()
grepped_out="Undefined variable '_'"

echo "Running pychecker"
echo "#################"
pychecker -9 -T     -8  -# 200 --changetypes GTG/gtg.py

echo "Running pyflakes"
echo "#################"
#pyflakes triggers a false positive with import * and with gettext _()
pyflakes GTG|grep -v "import \*"|grep -v "undefined name '_'"

echo "Running pylint"
echo "#################"
pylint --rcfile=/dev/null --include-ids=y --reports=n --disable-msg=$disabled GTG/gtg.py|grep -v "$grepped_out"
for i in GTG/*; do
	if test -d $i && [ $i != "data" ]; then
		#echo $i
		pylint --rcfile=/dev/null --include-ids=y --reports=n --disable-msg=$disabled $i |grep -v "$grepped_out"
	fi
done
