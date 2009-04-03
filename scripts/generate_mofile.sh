#!/bin/sh

# TODO: We should find some way to automatically detect languages
# by listing .po files but I'm lazy :-)
LANGUAGES=$(ls locales/gtg-*.po | sed 's/locales\/gtg-\(.*\).po/\1/')

for i in $LANGUAGES; do
	mkdir locales/$i/LC_MESSAGES/ --parents
	msgfmt locales/gtg-$i.po --output-file=locales/$i/LC_MESSAGES/gtg.mo
done
