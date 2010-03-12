#!/bin/sh

# TODO: We should find some way to automatically detect languages
# by listing .po files but I'm lazy :-)
LANGUAGES=$(ls po/*.po | sed 's/po\/\(.*\).po/\1/')

for i in $LANGUAGES; do
	mkdir po/$i/LC_MESSAGES/ --parents
	msgfmt po/$i.po --output-file=po/$i/LC_MESSAGES/gtg.mo
done
