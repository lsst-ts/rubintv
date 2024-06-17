#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

DEPLOY_BRANCH=deploy-slac

cd /usr/src/rubintv
git clone --single-branch --branch $DEPLOY_BRANCH https://github.com/lsst-sitcom/rubin_chart
git clone --single-branch --branch $DEPLOY_BRANCH https://github.com/lsst-ts/rubintv_visualization ./ddv

# Base HREF must be bookended by "/".
DDV_BASE_HREF=/rubintv/ddv/
CLIENT_WS_ADDRESS=rubintv/ws/ddv

cd ddv
echo -e "ADDRESS=$CLIENT_WS_ADDRESS" > .env
flutter build web --base-href $DDV_BASE_HREF --profile --source-maps