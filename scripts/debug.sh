#!/bin/bash
mkdir -p tmp
cp -r test/data/standard tmp/
export XDG_DATA_HOME="./tmp/standard/xdg/data"
export XDG_CACHE_HOME="./tmp/standard/xdg/cache"
export XDG_CONFIG_HOME="./tmp/standard/xdg/config"
./gtg -d
