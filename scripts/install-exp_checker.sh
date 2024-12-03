#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

cd /usr/src/rubintv/python/lsst/ts
git clone --single-branch --branch package https://github.com/lsst-sitcom/rubin_exp_checker.git ./exp_checker
cd exp_checker
pip install -e .
pip install -r requirements.txt
