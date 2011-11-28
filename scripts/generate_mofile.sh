#!/bin/sh

LANGUAGES=$(ls po/*.po | sed 's/po\/\(.*\).po/\1/')

for i in $LANGUAGES; do
	mkdir po/$i/LC_MESSAGES/ --parents
	msgfmt po/$i.po --output-file=po/$i/LC_MESSAGES/gtg.mo
done
