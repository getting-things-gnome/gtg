#!/bin/bash

args=""
set="default"

# Create execution-time data directory if needed
mkdir -p tmp

# Interpret arguments
while getopts ds: o
do  case "$o" in
    d)   args="-d";;
    s)   set="$OPTARG";;
    [?]) echo >&2 "Usage: $0 [-s dataset] [-d]"
         exit 1;;
    esac
done

# Copy dataset
if [  $set != "default" ]
then
    if [ ! -d "./tmp/$set" ]
    then
        echo "Copying $set dataset to ./tmp/"
        cp -r test/data/$set tmp/
    fi
    echo "Setting XDG vars to use $set dataset."
    export XDG_DATA_HOME="./tmp/$set/xdg/data"
    export XDG_CACHE_HOME="./tmp/$set/xdg/cache"
    export XDG_CONFIG_HOME="./tmp/$set/xdg/config"
else
    echo "Setting XDG vars to use default dataset."
    export XDG_DATA_HOME="./tmp/default/xdg/data"
    export XDG_CACHE_HOME="./tmp/default/xdg/cache"
    export XDG_CONFIG_HOME="./tmp/default/xdg/config"
fi

./gtg $args