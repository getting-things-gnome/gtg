#!/bin/bash
#Launch unit tests
#Argument is name of one existing test
export XDG_DATA_HOME="./tests/xdg/data"
export XDG_CONFIG_HOME="./tests/xdg/config"
python ./tests/$1.py
