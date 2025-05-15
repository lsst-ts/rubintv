#!/bin/bash
# Exit on error.
set -e

# Display each command as it's run.
set -x

cd /usr/src/rubintv
git clone --single-branch --branch $DDV_DEPLOY_BRANCH https://github.com/lsst-sitcom/rubin_chart
git clone --single-branch --branch $DDV_DEPLOY_BRANCH https://github.com/lsst-ts/rubintv_visualization ./ddv

# Install Flutter version for rubin_chart using fvm
cd rubin_chart
if [ -f ".fvmrc" ] || [ -f "fvm_config.json" ]; then
    fvm install
    fvm use
fi
cd ..

# Base HREF must be bookended by "/".
DDV_CLIENT_WS_ADDRESS=${DDV_CLIENT_WS_ADDRESS:-rubintv/ws/ddv}
DDV_BASE_HREF=${DDV_BASE_HREF:-/rubintv/ddv/}

cd ddv
echo "ADDRESS=$DDV_CLIENT_WS_ADDRESS" > .env

# Install and use Flutter version specified in fvm_config.json
if [ -f ".fvmrc" ] || [ -f "fvm_config.json" ]; then
    fvm install
    fvm use
    fvm flutter build web --base-href $DDV_BASE_HREF --wasm
else
    # Fallback to global flutter if no fvm config found
    flutter build web --base-href $DDV_BASE_HREF --wasm
fi
