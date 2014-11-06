#!/bin/bash
POTFILE="po/gtg.pot"
rm $POTFILE
touch $POTFILE
find GTG/ -iname "*.ui" -exec intltool-extract --type=gettext/glade {} \;
find GTG/ \( -iname "*.py" -o -iname "*.ui.h" \) -exec xgettext -j --language=Python --keyword=_ --keyword=N_ --from-code utf-8 --output=po/gtg.pot {} \;
