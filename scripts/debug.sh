#!/usr/bin/env bash

#Don't let the user execute this as root, it breaks graphical login (Changes /tmp permissions)
if [[ $UID -eq 0 ]]; then
    echo "GTG shouldn't be run as root, terminating"
    exit
fi

args=""
dataset="default"
norun=0
title=""

# Create execution-time data directory if needed
mkdir -p tmp

# Interpret arguments. The ":" following the letter indicates that the opstring (optarg) needs a parameter specified. See also: https://stackoverflow.com/questions/18414054/rreading-optarg-for-optional-flags
while getopts "bdns:t:" o;
do  case "$o" in
    b)   args="$args --boot-test";;
    d)   args="$args -d";;
    n)   norun=1;;
    s)   dataset="$OPTARG";;
    t)   title="$OPTARG";;
    [?]) echo >&2 "Usage: $0 [-s dataset] [-t title] [-b] [-d] [-n] (-- args passed to gtg)"
         exit 1;;
    esac
done
args_array=("${@}")
extra_args=("${args_array[@]:$((OPTIND-1))}")

# Copy dataset
if [[  "$dataset" != "default" && ! -d "./tmp/$dataset" ]]; then
    echo "Copying $dataset dataset to ./tmp/"
    cp -r "data/test-data/$dataset" tmp/ || exit $?
fi

echo "Running the development/debug version - using separate user directories"
echo "Your data is in the 'tmp' subdirectory with the '$dataset' dataset."
echo "-----------------------------------------------------------------------"
export XDG_DATA_HOME="./tmp/$dataset/xdg/data"
export XDG_CACHE_HOME="./tmp/$dataset/xdg/cache"
export XDG_CONFIG_HOME="./tmp/$dataset/xdg/config"

# Title has to be passed to GTG directly, not through $args
# title could be more word, and only the first word would be taken
if [[ "$title" = "" ]]; then
    title="Dev GTG: $(basename "$(pwd)")"
    if [[ "$dataset" != "default" ]]; then
        title="$title ($dataset dataset)"
    fi
fi

if [[ "$norun" -eq 0 ]]; then
    if [[ ! -d .local_build ]] || [[ ! -e .local_build/build.ninja ]]; then
        meson -Dprofile=development -Dprefix="$(pwd)"/.local_build/install .local_build || exit $?
    fi
    ninja -C .local_build install || exit $?
    # double quoting args seems to prevent python script from picking up flag arguments correctly
    # shellcheck disable=SC2086
    ./.local_build/prefix-gtg.sh ./.local_build/install/bin/gtg ${args} -t "$title" "${extra_args[@]}" || exit $?
fi
