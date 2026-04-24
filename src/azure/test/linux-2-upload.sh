#!/bin/bash

if [ $# -eq 0 ]; then
  echo "$0 <file>"
  exit
fi

file=$1

curl -F "file=@$1" http://linux.sandbox.npu.world:5000/upload
