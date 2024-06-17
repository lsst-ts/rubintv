#!/bin/bash

# Bash "strict mode", to help catch problems and bugs in the shell
# script. Every bash script you write should include this. See
# http://redsymbol.net/articles/unofficial-bash-strict-mode/ for
# details.
set -euo pipefail

# Display each command as it's run.
set -x

DEPLOY_BRANCH=deploy-slac

cd /usr/src/rubintv
git clone --single-branch --branch $DEPLOY_BRANCH https://github.com/lsst-sitcom/rubin_chart
git clone --single-branch --branch $DEPLOY_BRANCH https://github.com/lsst-ts/rubin_visualization ./ddv

# Base HREF must be bookended by "/".
DDV_BASE_HREF="/rubintv/ddv/"

cd ddv
flutter build web --base-href $DDV_BASE_HREF --profile --source-maps