#!/bin/bash

# This script allows contributors to run GTG directly from the gtg directory without the need to navigate
# to the scripts folder. 
# It refers to the GTG debug script originally placed in /scripts/debug.sh.
# Makes life much easier.

exec ./scripts/debug.sh $@
