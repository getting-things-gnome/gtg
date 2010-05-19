#!/bin/bash
#Imports your usual tags in the debug  data, so that you can 
# play with your tasks without fear of destroying them
./scripts/debug.sh -n
yes|cp -Rf ~/.local/share/gtg/* tmp/default/xdg/data/gtg/
yes|cp -Rf ~/.config/gtg/* tmp/default/xdg/config/gtg/


