#!/bin/bash

#Don't let the user execute this as root, it breaks graphical login (Changes /tmp permissions)
if [ $UID -eq 0 ]; then
    echo "GTG shouldn't be run as root, terminating"
    exit
fi

args="--no-crash-handler"
dataset="default"
norun=0
profile=0
title=""

# Create execution-time data directory if needed
mkdir -p tmp

# Interpret arguments
while getopts bdlnps: o
do  case "$o" in
    b)   args="$args --boot-test";;
    d)   args="$args -d";;
    # Request usage local liblarch if it is possible
    l)   args="$args -l"
         liblarchArgs="$liblarchArgs -l"
        ;;
    n)   norun=1;;
    p)   profile=1;;
    s)   dataset="$OPTARG";;
    t)   title="$OPTARG";;
    [?]) echo >&2 "Usage: $0 [-s dataset] [-t title] [-b] [-d] [-l] [-n] [-p]"
         exit 1;;
    esac
done

# Copy dataset
if [  $dataset != "default" -a ! -d "./tmp/$dataset" ]
then
    echo "Copying $dataset dataset to ./tmp/"
    cp -r test/data/$dataset tmp/
fi

echo "Setting XDG vars to use $dataset dataset."
export XDG_DATA_HOME="./tmp/$dataset/xdg/data"
export XDG_CACHE_HOME="./tmp/$dataset/xdg/cache"
export XDG_CONFIG_HOME="./tmp/$dataset/xdg/config"

# Title has to be passed to GTG directly, not through $args
# title could be more word, and only the first word would be taken
if [ "$title" = "" ]
then
    title="Dev GTG: $(basename `pwd`)"
    if [ "$dataset" != "default" ]
    then
        title="$title ($dataset dataset)"
    fi
fi

if [ $norun -eq 0 ]; then
    # Check for liblarch
    if ! ./GTG/tools/import_liblarch.py $liblarchArgs; then
        echo
        echo -n "Download latest liblarch? [y/N] "
        read answer
        if [ "$answer" = "y" -o "$answer" = "Y" -o "$answer" = "yes" ]; then
            git clone https://github.com/liblarch/liblarch ../liblarch
        else
            exit 1
        fi
    fi

    if [ $profile -eq 1 ]; then
        python -m cProfile -o gtg.prof ./gtg $args -t "$title"
        python ./scripts/profile_interpret.sh
    else
	./gtg $args -t "$title"
    fi
fi

