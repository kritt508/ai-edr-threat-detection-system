#!/bin/bash

if [ $# -eq 0 ]; then
 out=$(curl -fsSL linux.sandbox.npu.world:5000/list)
 echo $out
 echo "$0 <file>"
 exit
fi

FILENAME=$1

curl -L -G "linux.sandbox.npu.world:5000/download_pcap" \
    --data-urlencode "filename=$FILENAME" \
    --output "$FILENAME"
