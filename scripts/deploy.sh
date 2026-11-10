#!/usr/bin/env bash
# Run on EC2 only AFTER infrastructure and deployment authorization.
set -euo pipefail
: "${APP_IMAGE:?Set immutable image tag or digest in the environment}"
case "$APP_IMAGE" in *:latest|*:local) echo 'Use a release tag or digest'; exit 1;; esac
docker compose config --quiet
docker compose pull
# Bootstrap/migrations must already have succeeded using the privileged path.
docker compose up -d --wait
bash scripts/verify.sh
