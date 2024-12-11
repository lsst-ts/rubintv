#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

# exp_checker only runs at USDF
if [ -n "${RAPID_ANALYSIS_LOCATION}" ] && [ "${RAPID_ANALYSIS_LOCATION}" = "USDF" ]; then
    cd /usr/src/rubintv
    git clone https://github.com/lsst-sitcom/rubin_exp_checker.git exp_checker
    cd exp_checker
    pip install -e .
    pip install -r requirements.txt
fi
