#!/bin/bash

function batch_info_print {
  if [ [$1 -z] -a [$2 -z] ] ; then
    echo batch release_id range : '('first .. last')'
  elif [ $1 -z ] ; then
    echo batch release_id range '('$1 .. last')'
  elif [ $2 -z ] ; then
    echo batch release_id range '('first .. $2')'
  else
    echo batch release_id range '('$1 .. $2')'
  fi
}

if [ $# -eq 2 ] ; then
  start_range=$1
  end_range=$2
elif [ $# -eq 1 ] ; then
  start_range=$1
fi

nowdate=$(date + "%Y-%m-%d %H:%M:%S")

echo ${nowdate} running python3 /app/main.py ${start_range} ${end_range} >> /app/program.log 

python3 /app/main.py ${start_range} ${end_range} > /app/log/batch/main.log 2>&1 &
