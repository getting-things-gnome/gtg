#!/bin/bash
function recurse {
	py_countline
	for i in *; do
		if test -d $i && [ $i != "." ] && [ $i != ".." ] ; then
			cd $i
			recurse
			d=$(($d+1))
			cd ..
		fi
	done
}

function py_countline {
	for i in *; do
		if test -f $i && [ ${i##*.} = "py" ]; then
			l=`wc -l < $i`
			p=$(($p+$l))
			f=$(($f+1))
		fi
	done
}

d=0
f=0
p=0
recurse
echo "$p lines of python if $f .py files ($d directories)" 
