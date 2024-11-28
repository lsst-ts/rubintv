#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

cd /usr/src/rubintv/lsst/ts
git clone https://github.com/lsst-sitcom/rubin_exp_checker.git ./exp_checker
pip install -r /usr/src/rubintv/python/lsst/ts/exp_checker/requirements.txt
rm -rf /usr/src/rubintv/python/lsst/ts/exp_checker/.git
