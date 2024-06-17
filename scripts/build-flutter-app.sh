#!/bin/bash

# Bash "strict mode", to help catch problems and bugs in the shell
# script. Every bash script you write should include this. See
# http://redsymbol.net/articles/unofficial-bash-strict-mode/ for
# details.
set -euo pipefail

# Display each command as it's run.
set -x

DDV_BASE_HREF="/rubintv/ddv"

cd ddv
flutter build web --base-href $DDV_BASE_HREF --profile --source-maps