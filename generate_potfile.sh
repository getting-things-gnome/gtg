#!/bin/bash
POTFILE="locales/gtg.pot"
rm $POTFILE
touch $POTFILE
find GTG/ -iname "*.py" -exec xgettext -j --language=Python --keyword=_ --output=locales/gtg.pot {} \;
