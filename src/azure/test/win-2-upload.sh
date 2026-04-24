#!/bin/bash

if [ $# -eq 0 ]; then
  echo "$0 <file>"
  exit
fi

file=$1

curl -v -F "file=@$1" http://win.sandbox.npu.world:5000/upload
