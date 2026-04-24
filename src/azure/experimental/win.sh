#!/bin/bash

TIME=2

./vm-control-api.sh start win
./win-1-status.sh
./win-2-upload.sh ping8.exe
./win-analysis ping8.exe $TIME
./vm-control-api.sh stop win
