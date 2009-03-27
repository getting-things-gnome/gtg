#!/bin/bash
POTFILE="locales/gtg.pot"
rm $POTFILE
touch $POTFILE
find GTG/ -iname "*.glade" -exec intltool-extract --type=gettext/glade {} \;
find GTG/ \( -iname "*.py" -o -iname "*.glade.h" \) -exec xgettext -j --language=Python --keyword=_ --keyword=N_ --output=locales/gtg.pot {} \;
