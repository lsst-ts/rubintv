#!/bin/bash

# inititiate Flutter app
if ! command -v flutter &> /dev/null
then
    echo "Error: Flutter not installed" >&2
else
    echo -e "ADDRESS=<hostname>\nPORT=8080" > .env
    flutter build web
    cp build/web ddv
fi

run_rubintv
