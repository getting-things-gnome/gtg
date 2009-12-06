#!/bin/bash
# Create execution-time data directory if needed
mkdir -p tmp
# Interpret arguments
if [$# -gt 0] && [! $1 : '-d']
then
    if [ ! -d "./tmp/$1" ]
    then
        echo "Copying $1 dataset to ./tmp/"
        cp -r test/data/$1 tmp/
    fi
    echo "Setting XDG vars accordingly."
    export XDG_DATA_HOME="./tmp/$1/xdg/data"
    export XDG_CACHE_HOME="./tmp/$1/xdg/cache"
    export XDG_CONFIG_HOME="./tmp/$1/xdg/config"
else
    echo "Setting XDG vars to default value."
    export XDG_DATA_HOME="./tmp/default/xdg/data"
    export XDG_CACHE_HOME="./tmp/default/xdg/cache"
    export XDG_CONFIG_HOME="./tmp/default/xdg/config"
fi
./gtg