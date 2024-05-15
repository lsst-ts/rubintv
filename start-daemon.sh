#!/bin/bash

# inititiate Flutter app
if ! command -v flutter &> /dev/null
then
    echo "Error: Flutter not installed" >&2
else
    if [ ! -d "rubintv_visualization" ]
    then
        echo "Error: directory rubintv_visualization doesn't exist"
    else
        cd rubintv_visualization
        echo -e "ADDRESS=<hostname>\nPORT=8080" > .env
        flutter build web
        cp build/web ../ddv
    fi
fi

run_rubintv
