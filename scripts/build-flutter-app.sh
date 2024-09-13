#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

cd /usr/src/rubintv
git clone --single-branch --branch $DDV_DEPLOY_BRANCH https://github.com/lsst-sitcom/rubin_chart
git clone --single-branch --branch $DDV_DEPLOY_BRANCH https://github.com/lsst-ts/rubintv_visualization ./ddv

# Base HREF must be bookended by "/".
DDV_CLIENT_WS_ADDRESS=${DDV_CLIENT_WS_ADDRESS:-rubintv/ws/ddv}
DDV_BASE_HREF=${DDV_BASE_HREF:-/rubintv/ddv/}

cd ddv
echo "ADDRESS=$DDV_CLIENT_WS_ADDRESS" > .env
flutter build web --base-href $DDV_BASE_HREF --profile --source-maps