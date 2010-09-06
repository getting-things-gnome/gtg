#!/bin/bash
#Imports your usual tags in the debug  data, so that you can 
# play with your tasks without fear of destroying them
./scripts/debug.sh -n

mkdir -p tmp/default/xdg/data/gtg/
mkdir -p tmp/default/xdg/config/gtg/

yes|cp -Rf ~/.local/share/gtg/* tmp/default/xdg/data/gtg/
yes|cp -Rf ~/.config/gtg/* tmp/default/xdg/config/gtg/

tmpfile=$(mktemp)
cat tmp/default/xdg/data/gtg/projects.xml|
 sed -e 's/\/home\/.*\/\.local\/share/tmp\/default\/xdg\/data/' > tmpfile
cat tmpfile > tmp/default/xdg/data/gtg/projects.xml
rm tmpfile

