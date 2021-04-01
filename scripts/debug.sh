#!/usr/bin/env bash

#Don't let the user execute this as root, it breaks graphical login (Changes /tmp permissions)
if [[ $UID -eq 0 ]]; then
    echo "GTG shouldn't be run as root, terminating"
    exit
fi

args=""
dataset="default"
norun=0
pydebug=0
title=""

# Create execution-time data directory if needed
mkdir -p tmp

# Interpret arguments. The ":" following the letter indicates that the opstring (optarg) needs a parameter specified. See also: https://stackoverflow.com/questions/18414054/rreading-optarg-for-optional-flags
while getopts "dwns:t:" o;
do  case "$o" in
    d)   args="$args -d";;
    w)   pydebug=1;;
    n)   norun=1;;
    s)   dataset="$OPTARG";;
    t)   title="$OPTARG";;
    [?]) cat >&2 <<EOF
Usage: $0 [-s dataset] [-t title] [-d] [-w] [-n] (-- args passed to gtg)
    -s dataset     Use the dataset located in $PWD/tmp/<dataset>
    -t title       Set a custom title/program name to use.
    -d             Enable debug mode, basically enables debug logging
    -w             Enable python warnings like deprecation warnings,
                   and other python 3.7+ development mode features.
                   Also see https://docs.python.org/3/library/devmode.html
    -n             Just generate the build system, don't actually run gtg
    -- args passed to gtg
                   These arguments are passed to the application as-is
                   Use -- --help to get help for the application
EOF
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
export XDG_DATA_HOME="$PWD/tmp/$dataset/xdg/data"
export XDG_CACHE_HOME="$PWD/tmp/$dataset/xdg/cache"
export XDG_CONFIG_HOME="$PWD/tmp/$dataset/xdg/config"
export XDG_DATA_DIRS="$PWD/.local_build/install/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

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
    if [ "$pydebug" = 1 ]; then
        # https://docs.python.org/3/library/devmode.html#devmode
        export PYTHONDEVMODE=1
    fi
    # double quoting args seems to prevent python script from picking up flag arguments correctly
    # shellcheck disable=SC2086
    ./.local_build/prefix-gtg.sh ./.local_build/install/bin/gtg ${args} -t "$title" "${extra_args[@]}" || exit $?
fi
