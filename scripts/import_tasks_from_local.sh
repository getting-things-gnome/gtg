#!/bin/sh
# Imports your gtg user data in the development, so that you can
# play with your tasks without fear of destroying them.
# This has to be run from the root of the repo.

./scripts/debug.sh -n

mkdir -p tmp/default/xdg/data/gtg/
mkdir -p tmp/default/xdg/config/gtg/

cp -Rf ~/.local/share/gtg/* tmp/default/xdg/data/gtg/
cp -Rf ~/.config/gtg/* tmp/default/xdg/config/gtg/

test -f tmp/default/xdg/data/gtg/projects.xml && \
    sed -i -e 's_\/home\/.*\/\.local\/share_tmp\/default\/xdg\/data_' tmp/default/xdg/data/gtg/projects.xml

rm -f tmp/default/xdg/data/gtg/gtg.pid # Remove PID file protection
