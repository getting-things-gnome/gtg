#!/usr/bin/env bash
# Imports your usual tags in the debug data, so that you can
# play with your tasks without fear of destroying them
# This has to be run from the root of the repo


./scripts/debug.sh -n

mkdir -p tmp/default/xdg/data/gtg/
mkdir -p tmp/default/xdg/config/gtg/

cp -Rf ~/.var/app/org.gnome.Gtg/data/gtg/* tmp/default/xdg/data/gtg/
cp -Rf ~/.var/app/org.gnome.Gtg/config/gtg/* tmp/default/xdg/config/gtg/
